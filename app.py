# app.py

import os
import tempfile
import traceback # Import traceback to get detailed error info
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

# Import the agent creation function from our src folder
from src.agent.zelda_agent import create_zelda_agent, detect_language, get_base_prompt
# Import the audio processing functions
from src.audio_processing.handler import transcribe_audio, generate_speech

# --- Load Environment Variables ---
load_dotenv()

# --- Flask App Initialization ---
app = Flask(__name__, static_folder='assets')
CORS(app, resources={r"/*": {"origins": "*"}})

# --- Agent Initialization ---
print("Initializing Zelda Agent for the server...")
zelda_agent_executor = create_zelda_agent()
print("Zelda Agent is ready.")

# --- API Routes ---

@app.route('/')
def serve_index():
    """Serves the main HTML chat page."""
    return send_from_directory('.', 'index.html')

@app.route('/assets/<path:path>')
def serve_assets(path):
    """Serves static files like background GIFs from the assets folder."""
    return send_from_directory('assets', path)


@app.route('/chat', methods=['POST'])
def chat():
    """
    Handles TEXT-BASED chat requests from the frontend.
    """
    print("Received request for /chat endpoint")
    try:
        data = request.get_json()
        user_input = data.get('input')
        incoming_history = data.get('chat_history', [])

        if not user_input:
            return jsonify({"error": "No input provided"}), 400

        langchain_history = []
        for msg in incoming_history:
            if msg.get('type') == 'human':
                langchain_history.append(HumanMessage(content=msg.get('content')))
            elif msg.get('type') == 'ai':
                langchain_history.append(AIMessage(content=msg.get('content')))

        lang_code = detect_language(user_input)
        base_prompt_text = get_base_prompt(lang_code)

        response = zelda_agent_executor.invoke({
            "input": user_input,
            "base_prompt": base_prompt_text,
            "chat_history": langchain_history,
        })
        
        ai_response = response['output']

        updated_history = incoming_history + [
            {'type': 'human', 'content': user_input},
            {'type': 'ai', 'content': ai_response}
        ]

        print(f"Agent responded to /chat: {ai_response[:50]}...")
        return jsonify({
            "output": ai_response,
            "chat_history": updated_history
        })

    except Exception as e:
        print(f"An error occurred in /chat endpoint: {e}")
        traceback.print_exc() # Print the full traceback
        return jsonify({"error": "An internal error occurred."}), 500

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """
    Receives an audio file, transcribes it, and returns the text.
    """
    print("Received request for /transcribe endpoint")
    if 'audio_data' not in request.files:
        print("--> Error: No 'audio_data' file part in request.")
        return jsonify({"error": "No audio file part"}), 400
    
    audio_file = request.files['audio_data']
    print(f"--> Received audio file: {audio_file.filename} ({audio_file.content_type})")
    
    temp_path = ""
    try:
        # Use a temporary file to store the audio data
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            audio_file.save(temp_audio.name)
            temp_path = temp_audio.name
            print(f"--> Saved temporary audio file to: {temp_path}")

        # **MODIFIED CODE: Added a detailed try-except block here**
        # This will catch the specific error during transcription
        print("--> Attempting to transcribe audio...")
        transcribed_text = transcribe_audio(temp_path)
        print(f"--> Transcription result: '{transcribed_text}'")

        if transcribed_text and transcribed_text.strip():
            print("--> Successfully transcribed audio.")
            return jsonify({"transcription": transcribed_text})
        else:
            # This case is now more specific: transcription returned nothing.
            print("--> Transcription resulted in empty text. No speech detected?")
            return jsonify({"error": "Failed to transcribe audio or no speech detected"}), 500

    except Exception as e:
        # **MODIFIED CODE: This is the crucial new part**
        # If any error happens above, it will be caught and printed here.
        print("\n" + "="*50)
        print("--> CRITICAL ERROR in /transcribe endpoint!")
        print(f"--> Error Type: {type(e).__name__}")
        print(f"--> Error Details: {e}")
        traceback.print_exc() # This prints the full error stack trace
        print("="*50 + "\n")
        return jsonify({"error": f"An internal server error occurred during transcription: {e}"}), 500

    finally:
        # Ensure the temporary file is always deleted
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"--> Cleaned up temporary file: {temp_path}")


@app.route('/synthesize', methods=['POST'])
def synthesize():
    """
    Receives text, converts it to speech, and returns the audio file.
    """
    print("Received request for /synthesize endpoint")
    try:
        data = request.get_json()
        text_to_speak = data.get('text')

        if not text_to_speak:
            return jsonify({"error": "No text provided"}), 400

        audio_file_path = generate_speech(text_to_speak)

        if audio_file_path:
            print(f"--> Successfully generated speech file: {audio_file_path}")
            return send_file(
                audio_file_path,
                mimetype="audio/mpeg",
                as_attachment=True,
                download_name="response.mp3"
            )
        else:
            print("--> Failed to generate speech file.")
            return jsonify({"error": "Failed to generate speech"}), 500
    except Exception as e:
        print(f"An error occurred in /synthesize endpoint: {e}")
        traceback.print_exc()
        return jsonify({"error": "An internal error occurred during synthesis."}), 500

# --- Main Execution Block ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
