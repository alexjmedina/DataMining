from youtube_transcript_api import YouTubeTranscriptApi

video_id = "FollBLGldGg"

try:
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    print(f"Found transcripts for video {video_id}:")
    
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

        # Attempt to fetch the first available transcript for inspection
        print("\nAttempting to fetch the first available transcript for inspection...")
        try:
            if not available_transcripts_info:
                print("No transcripts available for this video (inspection check).")
            else:
                first_transcript_obj_to_fetch = available_transcripts_info[0]
                print(f"Fetching transcript in {first_transcript_obj_to_fetch.language_code} (first available)...")
                full_transcript_segments = first_transcript_obj_to_fetch.fetch()
                
                print("\nTranscript fetched successfully (first available for inspection):")
                if not full_transcript_segments:
                    print("  Transcript is empty.")
                else:
                    print(f"Total segments: {len(full_transcript_segments)}")
                    if len(full_transcript_segments) > 0:
                        first_segment = full_transcript_segments[0]
                        print(f"Type of a segment: {type(first_segment)}")
                        print(f"Attributes of a segment: {dir(first_segment)}")
                        # Try to print common attributes if they exist, otherwise it will error and we'll see it
                        try:
                            print(f"Segment as dict (if applicable): {first_segment.__dict__}")
                        except AttributeError:
                            print("Segment does not have __dict__ attribute.")
                        
                        # Based on the error, 'FetchedTranscriptSnippet' is the type.
                        # Let's try to access attributes directly if it's an object
                        # Common names might be 'text', 'start', 'duration'
                        # This part is for debugging, the actual fix will use the correct attributes
                        print("\nAttempting to access common attributes directly (for debugging):")
                        for attr in ["text", "start", "duration", "tStartMs", "dDurationMs"]:
                            if hasattr(first_segment, attr):
                                print(f"  Segment.{attr}: {getattr(first_segment, attr)}")
                            else:
                                print(f"  Segment does not have attribute: {attr}")
                        
                        print("\nIterating through first 5 segments with corrected access (assuming attributes text, start, duration):")
                        for i, segment in enumerate(full_transcript_segments[:5]):
                            # This is a guess, will confirm after seeing dir(segment)
                            # The previous error indicates this is where the problem is.
                            # The library's documentation or source code would be the definitive guide.
                            # For now, let's assume the structure is an object with these attributes.
                            # If 'text', 'start', 'duration' are not the correct attribute names, this will fail.
                            # The output of dir(segment) will guide the correction.
                            # The error was 'FetchedTranscriptSnippet' object is not subscriptable, so it's not a dict.
                            # It's an object, and we need to find its attributes.
                            # The library's own examples or source code would show how to access these.
                            # A common pattern is segment.text, segment.start, segment.duration.
                            try:
                                text = segment.text
                                start = segment.start
                                duration = segment.duration
                                print(f"  {start:.2f}s - {start + duration:.2f}s: {text}")
                            except AttributeError as ae:
                                print(f"Error accessing attributes for segment {i}: {ae}. Segment details: {segment}")
                                break # Stop if one segment fails, as others likely will too

        except Exception as e_any:
            print(f"Could not fetch or process any transcript for inspection. Error: {e_any}")

except Exception as e_main:
    print(f"An error occurred with video {video_id}: {e_main}")

