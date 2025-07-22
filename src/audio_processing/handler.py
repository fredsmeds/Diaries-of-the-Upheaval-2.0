# src/audio_processing/handler.py

import os
import tempfile
import traceback
import whisper
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()

# --- Initialization ---

# Initialize the ElevenLabs client
try:
    api_key = os.getenv("ELEVEN_LABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVEN_LABS_API_KEY not found in environment variables.")
    
    elevenlabs_client = ElevenLabs(api_key=api_key)
    print("ElevenLabs client initialized successfully.")

except Exception as e:
    print(f"Error initializing ElevenLabs client: {e}")
    elevenlabs_client = None

# Load the Whisper model
try:
    print("Loading Whisper model...")
    whisper_model = whisper.load_model("base")
    print("Whisper model loaded successfully.")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    whisper_model = None

# Define the voice ID for Princess Zelda
ZELDA_VOICE_ID = "21m00Tcm4TlvDq8ikWAM" # Voice ID for "Rachel" (free voice)

# --- Core Functions ---

def transcribe_audio(audio_file_path: str) -> str | None:
    """
    Transcribes audio from a file path to text using the local Whisper model.
    It now handles the conversion from .webm to a compatible format.
    """
    if not whisper_model:
        print("Whisper model is not loaded. Cannot transcribe audio.")
        return None
    
    print(f"Starting transcription for: {audio_file_path}")
    
    # --- START OF THE FIX ---
    # Convert .webm file sent from the browser to .mp3 before transcription
    try:
        print("Attempting to convert .webm to .mp3 for Whisper compatibility...")
        audio = AudioSegment.from_file(audio_file_path, format="webm")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_mp3:
            audio.export(temp_mp3.name, format="mp3")
            mp3_path = temp_mp3.name
        
        print(f"Conversion successful. Transcribing MP3 at: {mp3_path}")
        result = whisper_model.transcribe(mp3_path)
        transcribed_text = result["text"]
        print(f"Transcription result: '{transcribed_text}'")
        
        os.remove(mp3_path)
        print(f"Cleaned up temporary file: {mp3_path}")
        
        return transcribed_text

    except (FileNotFoundError, CouldntDecodeError) as e:
        # This is the most likely error if FFmpeg is not installed.
        print("\n" + "="*80)
        print("--> CRITICAL ERROR: Could not process audio file. This is almost always")
        print("--> because FFmpeg is not installed or not available in your system's PATH.")
        print("--> Please ensure FFmpeg is installed correctly to fix this.")
        print("--> For installation instructions, see: https://ffmpeg.org/download.html")
        print("="*80 + "\n")
        traceback.print_exc()
        return None
        
    except Exception as e:
        print(f"An unexpected error occurred during transcription: {e}")
        traceback.print_exc()
        return None
    # --- END OF THE FIX ---


def generate_speech(text: str) -> str | None:
    """
    Converts text to speech using the ElevenLabs API and saves it to a temporary file.
    """
    if not elevenlabs_client:
        print("ElevenLabs client is not initialized. Cannot generate speech.")
        return None

    try:
        print(f"Generating speech for text: '{text[:50]}...'")
        
        audio_data = elevenlabs_client.text_to_speech.convert(
            voice_id=ZELDA_VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2"
        )

        # Create a temporary file to hold the audio data
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", mode='wb') as temp_audio_file:
            for chunk in audio_data:
                temp_audio_file.write(chunk)
            
            print(f"Speech saved to temporary file: {temp_audio_file.name}")
            # Return the path to the temporary file
            return temp_audio_file.name

    except Exception as e:
        print("\n" + "="*80)
        print("--> CRITICAL ERROR: Speech generation failed.")
        print("--> This could be due to an invalid ElevenLabs API key,")
        print("--> network issues, or a problem with the selected voice ID.")
        print("="*80 + "\n")
        traceback.print_exc()
        return None

