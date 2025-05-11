from youtube_transcript_api import YouTubeTranscriptApi

video_id = "FollBLGldGg"

try:
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    print(f"Found transcripts for video {video_id}:")
    
    # Convert generator to list to check if it's empty and iterate multiple times if needed
    available_transcripts_info = list(transcript_list)

    if not available_transcripts_info:
        print(f"No transcripts found for video {video_id}.")
    else:
        for transcript_obj_info in available_transcripts_info:
            print(f"  Language: {transcript_obj_info.language}, Language Code: {transcript_obj_info.language_code}")
            if transcript_obj_info.is_generated:
                print("    This transcript is auto-generated.")
            else:
                print("    This transcript is manually created.")

        fetched_successfully = False
        try:
            # Re-create TranscriptList object to use its methods like find_generated_transcript
            # This is necessary because the original transcript_list generator might be exhausted
            # Alternatively, iterate available_transcripts_info to find the desired one manually
            # For simplicity, we'll re-fetch the list for find_generated_transcript
            current_transcript_list_obj = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript_to_fetch = current_transcript_list_obj.find_generated_transcript(['es', 'en'])
            # We could also try find_manually_created_transcript or find_transcript
            
            print(f"\nFetching transcript in {transcript_to_fetch.language_code} (preferred)...")
            full_transcript_segments = transcript_to_fetch.fetch()
            
            print("\nTranscript fetched successfully (preferred):")
            if not full_transcript_segments:
                print("  Transcript is empty.")
            else:
                for i, segment in enumerate(full_transcript_segments[:5]):
                    text = segment['text']
                    start = segment['start']
                    duration = segment['duration']
                    print(f"  {start:.2f}s - {start + duration:.2f}s: {text}")
                print(f"Total segments: {len(full_transcript_segments)}")
            fetched_successfully = True

        except Exception as e_pref: # Catches if find_generated_transcript fails or if fetch/processing fails
            print(f"Could not fetch or process preferred transcript. Error: {e_pref}")
            # The original error was "'FetchedTranscriptSnippet' object is not subscriptable"
            # This indicates 'segment' was not a dict. The library docs say it should be.
            # If the error persists, it means the structure of 'segment' is indeed not a dict.
            # For now, assuming the standard dict structure as per docs for the primary attempt.

        if not fetched_successfully:
            print("\nAttempting to fetch the first available transcript as fallback...")
            try:
                if not available_transcripts_info: # Should not happen if we reached here from the else block above
                    print("No transcripts available for this video (fallback check).")
                else:
                    # Use the first transcript object from the initially fetched list
                    first_transcript_obj_to_fetch = available_transcripts_info[0]
                    print(f"Fetching transcript in {first_transcript_obj_to_fetch.language_code} (first available)...")
                    # To fetch, we need a Transcript object, not just the info. 
                    # We need to get it from a new list_transcripts call or by constructing it if the API allows.
                    # Easiest is to re-list and pick by language code, or just fetch from the object if it's already a full Transcript object.
                    # The objects from list_transcripts() are indeed Transcript objects.
                    full_transcript_segments = first_transcript_obj_to_fetch.fetch()
                    
                    print("\nTranscript fetched successfully (first available):")
                    if not full_transcript_segments:
                        print("  Transcript is empty.")
                    else:
                        for i, segment in enumerate(full_transcript_segments[:5]):
                            text = segment['text']
                            start = segment['start']
                            duration = segment['duration']
                            print(f"  {start:.2f}s - {start + duration:.2f}s: {text}")
                        print(f"Total segments: {len(full_transcript_segments)}")
            except Exception as e_any:
                print(f"Could not fetch or process any transcript (fallback). Error: {e_any}")

except Exception as e_main:
    print(f"An error occurred with video {video_id}: {e_main}")

