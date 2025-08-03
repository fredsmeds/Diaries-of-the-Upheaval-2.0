# app.py

import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from langdetect import detect, LangDetectException

# --- Import Project-Specific Modules ---
from src.agent.zelda_agent import get_zelda_response
from src.audio_processing.handler import text_to_speech, speech_to_text

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO)

# --- Initialize Flask App ---
# We specify the static folder to be 'assets' so Flask can serve images from there.
app = Flask(__name__, template_folder='templates', static_folder='assets')
CORS(app)

# --- Define Directories ---
AUDIO_FILES_DIR = os.path.join(os.getcwd(), 'generated_audio')
os.makedirs(AUDIO_FILES_DIR, exist_ok=True)


# --- Core Routes ---

@app.route('/')
def index():
    """
    Serves the main HTML page for the chat interface.
    """
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """
    Handles text-based chat messages.
    """
    try:
        data = request.get_json()
        user_message = data.get('message')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # --- Language Detection ---
        try:
            lang = detect(user_message)
            logging.info(f"Detected language: {lang}")
        except LangDetectException:
            lang = 'en'
            logging.warning("Language detection failed, defaulting to English.")

        # --- Get Response from Agent ---
        zelda_response = get_zelda_response(user_message, lang=lang)

        return jsonify({'response': zelda_response})

    except Exception as e:
        logging.error(f"Error in /chat route: {e}")
        return jsonify({'error': 'An internal error occurred.'}), 500

@app.route('/audio', methods=['POST'])
def audio():
    """
    Handles audio-based input.
    """
    try:
        # This handles the case where the frontend sends text to be converted to speech
        if 'text_for_tts' in request.get_json():
             text = request.get_json().get('text_for_tts')
             audio_output_path = text_to_speech(text)
             if audio_output_path:
                 return jsonify({'audio_url': f"/audio_files/{os.path.basename(audio_output_path)}"})
             else:
                 return jsonify({'error': 'TTS failed'}), 500

        if 'audio_data' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = request.files['audio_data']
        
        # --- Speech-to-Text ---
        transcribed_text = speech_to_text(audio_file)
        if not transcribed_text:
            return jsonify({'error': 'Could not understand audio'}), 400

        # --- Language Detection ---
        try:
            lang = detect(transcribed_text)
        except LangDetectException:
            lang = 'en'
        
        # --- Get Response from Agent ---
        zelda_response_text = get_zelda_response(transcribed_text, lang=lang)

        # --- Text-to-Speech ---
        audio_output_path = text_to_speech(zelda_response_text)
        
        return jsonify({
            'response': zelda_response_text,
            'audio_url': f"/audio_files/{os.path.basename(audio_output_path)}" if audio_output_path else None
        })

    except Exception as e:
        logging.error(f"Error in /audio route: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred.'}), 500


# --- Routes for Serving Generated Files ---

@app.route('/generated_maps/<path:filename>')
def serve_generated_map(filename):
    """
    Serves map images from the 'generated_maps' directory.
    """
    return send_from_directory(os.path.join(os.getcwd(), 'generated_maps'), filename)

@app.route('/audio_files/<path:filename>')
def serve_audio_file(filename):
    """
    Serves TTS audio files from the 'generated_audio' directory.
    """
    return send_from_directory(AUDIO_FILES_DIR, filename)

# --- NEW ROUTE TO SERVE ASSETS ---
@app.route('/assets/<path:filename>')
def serve_asset(filename):
    """
    Serves static files like background images from the 'assets' directory.
    """
    return send_from_directory(os.path.join(os.getcwd(), 'assets'), filename)


# --- Main Execution Block ---

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
