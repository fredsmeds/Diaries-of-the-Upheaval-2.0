# app.py

import os
import tempfile
import re # <-- Import the regular expression module
import traceback
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
        
        ai_response_raw = response['output']
        
        # Clean the response for the UI by removing the tags
        ai_response_for_ui = ai_response_raw.replace("|||SPEAK|||", "").replace("|||NOSPEAK|||", "")

        updated_history = incoming_history + [
            {'type': 'human', 'content': user_input},
            {'type': 'ai', 'content': ai_response_for_ui} # Use the cleaned response for history
        ]

        print(f"Agent responded to /chat: {ai_response_for_ui[:50]}...")
        return jsonify({
            # Send the raw response with tags to the frontend
            "output": ai_response_raw, 
            "chat_history": updated_history
        })

    except Exception as e:
        print(f"An error occurred in /chat endpoint: {e}")
        traceback.print_exc()
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
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            audio_file.save(temp_audio.name)
            temp_path = temp_audio.name
        
        transcribed_text = transcribe_audio(temp_path)

        if transcribed_text and transcribed_text.strip():
            return jsonify({"transcription": transcribed_text})
        else:
            return jsonify({"error": "Failed to transcribe audio or no speech detected"}), 500

    except Exception as e:
        print(f"An error occurred in /transcribe endpoint: {e}")
        traceback.print_exc()
        return jsonify({"error": f"An internal server error occurred during transcription: {e}"}), 500

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/synthesize', methods=['POST'])
def synthesize():
    """
    Receives text, converts it to speech, and returns the audio file.
    This now handles special tags to control which parts of the text are spoken.
    """
    print("Received request for /synthesize endpoint")
    data = request.get_json()
    full_text = data.get('text')

    if not full_text:
        return jsonify({"error": "No text provided"}), 400

    # --- NEW LOGIC TO HANDLE SPEECH TAGS ---
    text_to_speak = full_text
    if "|||SPEAK|||" in full_text:
        # Find all occurrences of the text between the SPEAK tags
        speakable_parts = re.findall(r'\|\|\|SPEAK\|\|\|(.*?)\|\|\|NOSPEAK\|\|\|', full_text, re.DOTALL)
        # Join them together with a space
        text_to_speak = " ".join([part.strip() for part in speakable_parts])
        print(f"--> Extracted speakable text: '{text_to_speak}'")
    
    if not text_to_speak.strip():
        print("--> No speakable text found after processing tags, nothing to synthesize.")
        return jsonify({"status": "no audio generated"}), 204 # 204 No Content

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


# --- Main Execution Block ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)