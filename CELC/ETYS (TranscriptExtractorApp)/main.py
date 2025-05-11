# Remember to activate venv: source venv/bin/activate
# And install dependencies: pip install -r requirements.txt
# To run: flask run --host=0.0.0.0

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, request, jsonify, render_template
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from youtube_transcript_api._errors import CouldNotRetrieveTranscript # Import specific error for parsing issues
from pytube import YouTube
from pytube.exceptions import PytubeError
import re
import datetime
from deepmultilingualpunctuation import PunctuationModel
import xml.etree.ElementTree as ET # For more specific XML parsing error handling if needed

app = Flask(__name__, static_folder='static', template_folder='static')

# Initialize the punctuation model. 
punct_model = None
try:
    punct_model = PunctuationModel()
    app.logger.info("Punctuation model loaded successfully.")
except Exception as e:
    app.logger.error(f"Failed to load PunctuationModel: {e}. Punctuation restoration will be basic.")
    punct_model = None

def extract_video_id(url):
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([^&]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([^&]+)',
        r'(?:https?://)?youtu\.be/([^&?]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([^&?]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def format_duration(seconds):
    if seconds is None:
        return "N/A"
    delta = datetime.timedelta(seconds=seconds)
    return str(delta)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_transcript', methods=['POST'])
def get_transcript_route():
    data = request.get_json()
    youtube_url = data.get('youtube_url')

    if not youtube_url:
        return jsonify({'error': 'No YouTube URL provided'}), 400

    video_id = extract_video_id(youtube_url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL or could not extract video ID'}), 400

    video_title = f'Video ID: {video_id}'
    video_duration_str = "N/A"
    video_publish_date_str = "N/A"

    try:
        yt = YouTube(youtube_url)
        video_title = yt.title
        video_duration_str = format_duration(yt.length)
        if yt.publish_date:
            video_publish_date_str = yt.publish_date.strftime("%Y-%m-%d")
        app.logger.info(f"Successfully fetched metadata for {video_id} using pytube.")
    except PytubeError as pe:
        app.logger.error(f"Pytube error for {youtube_url}: {str(pe)}")
        # Continue, as metadata is not strictly critical for transcript if transcript API works
    except Exception as e_meta:
        app.logger.error(f"Generic error fetching metadata for {youtube_url}: {str(e_meta)}")

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript_obj = None
        try:
            transcript_obj = transcript_list.find_transcript(['es', 'en'])
        except NoTranscriptFound:
            try:
                transcript_obj = transcript_list.find_generated_transcript(['es', 'en'])
            except NoTranscriptFound:
                available_transcripts = list(transcript_list)
                if available_transcripts:
                    transcript_obj = available_transcripts[0] # Fallback to the first available
                else:
                    return jsonify({'error': 'No transcripts found for this video (manual, generated, or any other language).'}), 404
        
        raw_transcript_segments = transcript_obj.fetch()
        
        if not raw_transcript_segments: # Check if fetch returned empty list
             app.logger.warning(f"Fetched transcript segments are empty for {video_id}. Title: {video_title}")
             return jsonify({'error': f'Transcript data is empty for this video. Title: {video_title}'}), 404

        unpunctuated_text = " ".join([segment.text for segment in raw_transcript_segments if segment.text is not None])
        unpunctuated_text = re.sub(r'\s+', ' ', unpunctuated_text).strip()

        if not unpunctuated_text:
            app.logger.warning(f"Joined transcript text is empty after processing for {video_id}. Title: {video_title}")
            return jsonify({'error': f'No text content found in the transcript for this video. Title: {video_title}'}), 404

        improved_text = unpunctuated_text
        if punct_model:
            try:
                improved_text = punct_model.restore_punctuation(unpunctuated_text)
                app.logger.info(f"Punctuation restored for video {video_id}.")
            except Exception as e_punct:
                app.logger.error(f"Error during punctuation restoration for {video_id}: {e_punct}. Using unpunctuated text.")
                improved_text = unpunctuated_text 
        else:
            app.logger.warning(f"Punctuation model not available. Serving text without advanced punctuation restoration for {video_id}.")
            improved_text = re.sub(r'\s+', ' ', unpunctuated_text).strip()

        metadata = {
            'title': video_title,
            'publish_date': video_publish_date_str,
            'duration': video_duration_str,
            'word_count': len(improved_text.split()),
            'is_auto_generated': transcript_obj.is_generated,
            'language': transcript_obj.language,
            'language_code': transcript_obj.language_code
        }

        return jsonify({'transcript': improved_text, 'metadata': metadata}), 200

    except NoTranscriptFound:
        return jsonify({'error': f'No transcript found for video ID {video_id}. Video Title: {video_title}'}), 404
    except TranscriptsDisabled:
        return jsonify({'error': f'Transcripts are disabled for this video. Video Title: {video_title}'}), 403
    except CouldNotRetrieveTranscript as e_retrieve: # Catch specific error for fetching/parsing issues
        app.logger.error(f"Could not retrieve/parse transcript for {video_id} (Title: {video_title}): {str(e_retrieve)}")
        return jsonify({'error': f'Failed to retrieve or parse transcript for this video. It might be unavailable or in an unsupported format. Video Title: {video_title}'}), 502 # 502 Bad Gateway or 422 Unprocessable Entity
    except ET.ParseError as e_xml: # Catch XML parsing errors specifically
        app.logger.error(f"XML ParseError for {video_id} (Title: {video_title}): {str(e_xml)}")
        return jsonify({'error': f'Error parsing transcript data (XML). The video might not have a valid transcript. Video Title: {video_title}'}), 502
    except Exception as e:
        app.logger.error(f"General error processing transcript for {video_id} (Title: {video_title}): {str(e)}")
        return jsonify({'error': f'An unexpected error occurred while processing the transcript. Video Title: {video_title}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

