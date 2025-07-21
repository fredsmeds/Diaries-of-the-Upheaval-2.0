# check_version.py
import youtube_transcript_api

print("--- Checking youtube_transcript_api version ---")
try:
    # This attribute holds the version number
    version = youtube_transcript_api.__version__
    print(f"Version found: {version}")

    # This attribute shows the exact file path being used
    path = youtube_transcript_api.__file__
    print(f"Library path: {path}")

except Exception as e:
    print(f"Could not determine version. Error: {e}")