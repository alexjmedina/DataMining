from youtube_transcript_api import YouTubeTranscriptApi

video_id = "FollBLGldGg"

try:
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    print(f"Found transcripts for video {video_id}:")
    for transcript_obj in transcript_list:
        print(f"  Language: {transcript_obj.language}, Language Code: {transcript_obj.language_code}")
        if transcript_obj.is_generated:
            print("    This transcript is auto-generated.")
        else:
            print("    This transcript is manually created.")

    # Try to fetch the first available transcript (or a specific language if needed)
    # For example, to get a Spanish transcript if available, or fallback to English
    try:
        transcript = transcript_list.find_generated_transcript(['es', 'en'])
        print(f"\nFetching transcript in {transcript.language_code}...")
        full_transcript = transcript.fetch()
        print("\nTranscript fetched successfully:")
        # Print first 5 segments as a sample
        for i, segment in enumerate(full_transcript[:5]):
            print(f"  {segment['start']:.2f}s - {segment['start'] + segment['duration']:.2f}s: {segment['text']}")
        print(f"Total segments: {len(full_transcript)}")

    except Exception as e:
        print(f"Could not fetch a preferred transcript: {e}")
        # If preferred languages are not found, try fetching any available transcript
        try:
            print("\nAttempting to fetch the first available transcript...")
            first_transcript_obj = list(transcript_list)[0]
            print(f"Fetching transcript in {first_transcript_obj.language_code}...")
            full_transcript = first_transcript_obj.fetch()
            print("\nTranscript fetched successfully:")
            for i, segment in enumerate(full_transcript[:5]):
                print(f"  {segment['start']:.2f}s - {segment['start'] + segment['duration']:.2f}s: {segment['text']}")
            print(f"Total segments: {len(full_transcript)}")
        except Exception as e_any:
            print(f"Could not fetch any transcript: {e_any}")

except Exception as e:
    print(f"An error occurred with video {video_id}: {e}")

