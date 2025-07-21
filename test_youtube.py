from youtube_transcript_api import YouTubeTranscriptApi

# A known-good video ID to test with
test_video_id = 'JuhBs44odO0' 

print(f"Attempting to fetch transcript for video ID: {test_video_id}")

try:
    # Attempt to fetch the transcript
    transcript = YouTubeTranscriptApi.get_transcript(test_video_id, languages=['en', 'en-GB'])
    
    # If successful, print a success message and a snippet
    print("\n--- SUCCESS! ---")
    print("Successfully fetched the transcript.")
    print("\nTranscript snippet:")
    # Print the first 3 lines of the transcript data
    for i, line in enumerate(transcript):
        if i < 3:
            print(line)
        else:
            break

except Exception as e:
    # If it fails, print a detailed error message
    print("\n--- FAILURE! ---")
    print(f"An error occurred: {e}")
    print("\nThis indicates a problem with the library or your network connection to YouTube's services.")