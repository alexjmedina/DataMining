# Remember to activate venv: source venv/bin/activate
# And install dependencies: pip install -r requirements.txt
# To run: flask run --host=0.0.0.0

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, request, jsonify, render_template
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from pytube import YouTube
from pytube.exceptions import PytubeError
import re
import datetime
from deepmultilingualpunctuation import PunctuationModel

app = Flask(__name__, static_folder='static', template_folder='static')

# Initialize the punctuation model. 
# This might take some time on first run as it downloads the model.
# It's better to initialize it once when the app starts.
# Supported languages: en, fr, it, es, de
punct_model = None
try:
    # Attempt to load the model that supports multiple languages including Spanish.
    # If a specific Spanish model exists and is preferred, its name would be used here.
    # The default model should handle Spanish as per library description.
    punct_model = PunctuationModel()
    app.logger.info("Punctuation model loaded successfully.")
except Exception as e:
    app.logger.error(f"Failed to load PunctuationModel: {e}. Punctuation restoration will be basic.")
    punct_model = None # Ensure it's None if loading failed

def extract_video_id(url):
    """Extracts YouTube video ID from various URL formats."""
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

    video_title = f'Video ID: {video_id}' # Default title
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
    except Exception as e_meta:
        app.logger.error(f"Generic error fetching metadata for {youtube_url}: {str(e_meta)}")

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript_obj = None
        try:
            # Prefer Spanish or English
            transcript_obj = transcript_list.find_transcript(['es', 'en'])
        except NoTranscriptFound:
            try:
                transcript_obj = transcript_list.find_generated_transcript(['es', 'en'])
            except NoTranscriptFound:
                available_transcripts = list(transcript_list)
                if available_transcripts:
                    transcript_obj = available_transcripts[0]
                else:
                    return jsonify({'error': 'No transcripts found for this video (after checking all options).'}), 404
        
        raw_transcript_segments = transcript_obj.fetch()
        
        # Concatenate text segments before punctuation restoration
        unpunctuated_text = " ".join([segment['text'] for segment in raw_transcript_segments])
        unpunctuated_text = re.sub(r'\s+', ' ', unpunctuated_text).strip()

        improved_text = unpunctuated_text
        if punct_model:
            try:
                # The library expects a list of texts, but can process a single string too.
                # For very long texts, it might be better to split them, but for shorts, one go should be fine.
                # The library documentation implies it handles various languages including Spanish with the default model.
                improved_text = punct_model.restore_punctuation(unpunctuated_text)
                app.logger.info(f"Punctuation restored for video {video_id}.")
            except Exception as e_punct:
                app.logger.error(f"Error during punctuation restoration for {video_id}: {e_punct}. Using unpunctuated text.")
                # Fallback to unpunctuated text if model fails
                improved_text = unpunctuated_text # Ensure it falls back
        else:
            app.logger.warning(f"Punctuation model not available. Serving text without advanced punctuation restoration for {video_id}.")
            # Basic cleanup if model is not available
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
        return jsonify({'error': f'No transcript found for video ID {video_id}. Pytube title: {video_title}'}), 404
    except TranscriptsDisabled:
        return jsonify({'error': f'Transcripts are disabled for this video. Pytube title: {video_title}'}), 403
    except Exception as e:
        app.logger.error(f"Error processing transcript for {video_id}: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    # (cd /home/ubuntu/youtube_transcript_extractor && source venv/bin/activate && pip install youtube-transcript-api pytube deepmultilingualpunctuation)
    # Note: deepmultilingualpunctuation installs torch, which can be large.
    app.run(debug=True, host='0.0.0.0', port=5000)

