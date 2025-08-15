# Chargement des variables d’environnement
from dotenv import load_dotenv
load_dotenv()

import os
import openai
import requests
import base64
import tempfile
from flask import Flask, request, jsonify
from pydub import AudioSegment

# Configuration des clés API
openai.api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")

# Initialisation de Flask
app = Flask(__name__)

@app.route('/neo', methods=['POST'])
def neo_voice_agent():
    try:
        # 1. Récupération de l’audio Twilio
        audio_url = request.form['RecordingUrl'] + '.wav'
        audio_data = requests.get(audio_url)
        if audio_data.status_code != 200:
            return jsonify({'error': 'Erreur lors du téléchargement de l’audio'}), 400

        # 2. Sauvegarde temporaire de l'audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
            temp.write(audio_data.content)
            wav_path = temp.name

        # 3. Transcription Deepgram
        dg_response = requests.post(
            "https://api.deepgram.com/v1/listen",
            headers={"Authorization": f"Token {deepgram_api_key}"},
            files={"file": open(wav_path, "rb")},
            data={"model": "nova", "language": "fr"}
        )
        transcription = dg_response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]

        # 4. Réponse GPT
        gpt_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es Neo, l’agent IA téléphonique d’un hôtel."},
                {"role": "user", "content": transcription}
            ]
        )
        reply_text = gpt_response["choices"][0]["message"]["content"]

        # 5. Synthèse vocale ElevenLabs
        tts_response = requests.post(
            "https://api.elevenlabs.io/v1/text-to-speech/kENkNtk0xyzG09WW40xE",
            headers={
                "xi-api-key": elevenlabs_api_key,
                "Content-Type": "application/json"
            },
            json={
                "text": reply_text,
                "voice_settings": {
                    "stability": 0.4,
                    "similarity_boost": 0.8
                }
            }
        )
        if tts_response.status_code != 200:
            return jsonify({'error': 'Erreur ElevenLabs'}), 500

        # 6. Sauvegarde MP3
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_mp3:
            temp_mp3.write(tts_response.content)
            mp3_path = temp_mp3.name

        # 7. Conversion MP3 en WAV
        final_wav = mp3_path.replace(".mp3", ".wav")
        sound = AudioSegment.from_mp3(mp3_path)
        sound.export(final_wav, format="wav")

        # 8. Encodage pour retour API
        with open(final_wav, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")

        return jsonify({"audio_base64": audio_base64})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ IMPORTANT pour Gunicorn sur Railway
app = app
