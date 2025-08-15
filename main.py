# Chargement des variables d’environnement
from dotenv import load_dotenv
load_dotenv()

import os
import openai
import requests
import base64
import tempfile
import logging
from flask import Flask, request, jsonify
from pydub import AudioSegment

# Configuration du logging
logging.basicConfig(level=logging.INFO)

# Récupération des clés API
openai.api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")

# Initialisation de Flask
app = Flask(__name__)

@app.route('/neo', methods=['POST'])
def neo_voice_agent():
    try:
        logging.info("➡️ Nouvelle requête reçue sur /neo")

        # 1. Récupération de l’audio Twilio
        audio_url = request.form['RecordingUrl'] + '.wav'
        logging.info(f"🎙️ Téléchargement audio depuis : {audio_url}")
        audio_data = requests.get(audio_url)
        if audio_data.status_code != 200:
            logging.error("❌ Échec du téléchargement de l'audio")
            return jsonify({'error': 'Erreur lors du téléchargement de l’audio'}), 400

        # 2. Sauvegarde temporaire de l'audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
            temp.write(audio_data.content)
            wav_path = temp.name
        logging.info(f"✅ Audio sauvegardé temporairement : {wav_path}")

        # 3. Transcription Deepgram
        dg_response = requests.post(
            "https://api.deepgram.com/v1/listen",
            headers={"Authorization": f"Token {deepgram_api_key}"},
            files={"file": open(wav_path, "rb")},
            data={"model": "nova", "language": "fr"}
        )
        dg_response.raise_for_status()
        transcription = dg_response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
        logging.info(f"✍️ Transcription : {transcription}")

        # 4. Réponse GPT
        gpt_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es Neo, l’agent IA téléphonique d’un hôtel."},
                {"role": "user", "content": transcription}
            ]
        )
        reply_text = gpt_response["choices"][0]["message"]["content"]
        logging.info(f"🤖 Réponse de GPT : {reply_text}")

        # 5. Synthèse vocale ElevenLabs
        tts_response = requests.post(
            "https://api.elevenlabs.io/v1/text-to-speech/kENkNtk0xyzG09WW40xE",  # ID de la voix à personnaliser
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
            logging.error(f"❌ Erreur ElevenLabs : {tts_response.text}")
            return jsonify({'error': 'Erreur ElevenLabs'}), 500

        # 6. Sauvegarde MP3
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_mp3:
            temp_mp3.write(tts_response.content)
            mp3_path = temp_mp3.name

        # 7. Conversion MP3 en WAV
        final_wav = mp3_path.replace(".mp3", ".wav")
        sound = AudioSegment.from_mp3(mp3_path)
        sound.export(final_wav, format="wav")
        logging.info("🎧 Conversion MP3 > WAV terminée")

        # 8. Encodage Base64 pour retour
        with open(final_wav, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")

        logging.info("✅ Envoi de l’audio encodé en base64 à Twilio")
        return jsonify({"audio_base64": audio_base64})

    except Exception as e:
        logging.exception("❌ Une erreur est survenue dans le traitement de la requête")
        return jsonify({"error": str(e)}), 500

# ⚠️ Ne surtout pas ajouter app.run() ici pour Railway
app = app
