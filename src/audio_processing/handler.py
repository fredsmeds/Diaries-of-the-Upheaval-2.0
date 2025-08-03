# src/audio_processing/handler.py

import os
import whisper
import logging
from elevenlabs import play, save
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# --- Load Environment Variables ---
# This ensures the ELEVEN_API_KEY is available for the client.
load_dotenv()

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO)

# --- Initialize Clients and Models ---
try:
    # Initialize the ElevenLabs client with the API key from your .env file
    eleven_client = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
    logging.info("ElevenLabs client initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize ElevenLabs client: {e}")
    eleven_client = None

try:
    # Load the Whisper model. 'base' is a good balance of speed and accuracy.
    # The model will be downloaded on the first run.
    logging.info("Loading Whisper model...")
    whisper_model = whisper.load_model("base")
    logging.info("Whisper model loaded successfully.")
except Exception as e:
    logging.error(f"Failed to load Whisper model: {e}")
    whisper_model = None

# Define the directory to save generated audio files.
AUDIO_FILES_DIR = os.path.join(os.getcwd(), 'generated_audio')
os.makedirs(AUDIO_FILES_DIR, exist_ok=True)


def text_to_speech(text: str) -> str | None:
    """
    Converts a string of text into a spoken audio file using the ElevenLabs API.

    Args:
        text (str): The text to be converted to speech.

    Returns:
        str | None: The file path of the generated MP3 file, or None if an error occurred.
    """
    if not eleven_client:
        logging.error("ElevenLabs client is not initialized. Cannot perform text-to-speech.")
        return None
    if not text:
        logging.warning("Text-to-speech called with empty text.")
        return None

    try:
        # Generate the audio from the text using a pre-selected voice.
        # "Rachel" is a good default voice, but this can be changed.
        audio = eleven_client.generate(
            text=text,
            voice="Rachel", 
            model="eleven_multilingual_v2"
        )

        # Create a unique filename to avoid overwriting files.
        output_filename = f"response_{hash(text)}.mp3"
        output_path = os.path.join(AUDIO_FILES_DIR, output_filename)

        # Save the generated audio to the specified file path.
        save(audio, output_path)
        logging.info(f"Audio file saved successfully to {output_path}")
        
        return output_path

    except Exception as e:
        logging.error(f"An error occurred during text-to-speech generation: {e}")
        return None


def speech_to_text(audio_file) -> str | None:
    """
    Transcribes spoken audio from a file into text using the Whisper model.

    Args:
        audio_file: A file-like object containing the audio data.

    Returns:
        str | None: The transcribed text, or None if an error occurred.
    """
    if not whisper_model:
        logging.error("Whisper model is not loaded. Cannot perform speech-to-text.")
        return None

    try:
        # Save the incoming audio file temporarily to disk, as Whisper works with file paths.
        temp_audio_path = os.path.join(AUDIO_FILES_DIR, "temp_input_audio.webm")
        audio_file.save(temp_audio_path)
        
        # Transcribe the audio file.
        result = whisper_model.transcribe(temp_audio_path)
        transcribed_text = result["text"]
        
        logging.info(f"Transcribed text: {transcribed_text}")
        
        # Clean up the temporary file.
        os.remove(temp_audio_path)
        
        return transcribed_text

    except Exception as e:
        logging.error(f"An error occurred during speech-to-text transcription: {e}")
        # Clean up the temp file even if an error occurs
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        return None

