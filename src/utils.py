# src/utils.py (or src/config.py)
import os
from dotenv import load_dotenv

# Call load_dotenv() to load variables from your .env file into environment variables
# It's good practice to call this early in your application's lifecycle.
# If your .env file is in the project root (where you run python from, or where app.py is),
# load_dotenv() should find it automatically.
# If it's elsewhere, you might need to provide the path: load_dotenv(dotenv_path='/path/to/.env')
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY") # For LangSmith, if used
# GOOGLE_APPLICATION_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_PATH")
# In case of need

# Optional: Add checks to see if keys were loaded, for debugging
if not OPENAI_API_KEY:
    print("⚠️ Warning: OPENAI_API_KEY not found. Check your .env file and its location.")
if not ELEVEN_LABS_API_KEY:
    print("⚠️ Warning: ELEVEN_LABS_API_KEY not found.")
# Add similar checks for other essential keys as needed