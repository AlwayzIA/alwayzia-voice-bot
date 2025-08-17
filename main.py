# ────────────────────────────────────────────────────────────────
# 🚀 Script principal pour Neo, l'agent vocal IA – AlwayzIA
# API Flask avec transcription Deepgram, réponse GPT-4 et voix ElevenLabs
# ────────────────────────────────────────────────────────────────

from dotenv import load_dotenv
load_dotenv()

import os
import openai
import requests
import base64
import tempfile
import logging
import subprocess
from flask import Flask, request, jsonify

# ──────────────── Configuration logging ────────────────
logging.basicConfig(level=logging.INFO)

# ──────────────── Récupération des clés API ────────────────
openai.api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")

# ──────────────── Initialisation de Flask ────────────────
app = Flask(__name__)

def convert_mp3_to_wav_ffmpeg(mp3_path, wav_path):
    """Convertit MP3 vers WAV en utilisant ffmpeg directement"""
    try:
        subprocess.run([
            'ffmpeg', '-i', mp3_path, '-ar', '8000', '-ac', '1', 
            '-acodec', 'pcm_mulaw', '-f', 'wav', wav_path, '-y'
        ], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Erreur ffmpeg: {e}")
        return False
    except FileNotFoundError:
        logging.error("ffmpeg non trouvé sur le système")
        return False

@app.route('/neo', methods=['POST'])
def neo_voice_agent():
    try:
        logging.info("📞 Nouvelle requête reçue sur /neo")

        # 1. Récupération de l'audio Twilio
        audio_url = request.form['RecordingUrl'] + '.wav'
        logging.info(f"🔊 Téléchargement de l'audio depuis : {audio_url}")
        audio_data = requests.get(audio_url)
        if audio_data.status_code != 200:
            logging.error("❌ Erreur de téléchargement de l'audio Twilio")
            return jsonify({'error': 'Erreur lors du téléchargement de l\'audio'}), 400

        # 2. Sauvegarde temporaire du fichier audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
            temp.write(audio_data.content)
            wav_path = temp.name
        logging.info("✅ Audio sauvegardé localement pour transcription")

        # 3. Transcription Deepgram
        with open(wav_path, "rb") as audio_file:
            dg_response = requests.post(
                "https://api.deepgram.com/v1/listen",
                headers={"Authorization": f"Token {deepgram_api_key}"},
                files={"file": audio_file},
                data={"model": "nova", "language": "fr"}
            )
        
        if dg_response.status_code != 200:
            logging.error(f"Erreur Deepgram: {dg_response.text}")
            return jsonify({'error': 'Erreur Deepgram'}), 500
            
        transcription = dg_response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
        logging.info(f"📝 Transcription : {transcription}")

        # 4. Appel à OpenAI (GPT-4) - VERSION CORRIGÉE
        client = openai.OpenAI(api_key=openai.api_key)
        gpt_response = client.chat.completions.create(
            model="gpt-4o-mini",  # Modèle optimisé pour votre clé sk-proj-
            messages=[
                {"role": "system", "content": "Tu es Neo, l'agent IA téléphonique d'un hôtel. Réponds de manière concise et professionnelle."},
                {"role": "user", "content": transcription}
            ],
            max_tokens=150,
            temperature=0.7
        )
        reply_text = gpt_response.choices[0].message.content
        logging.info(f"🤖 Réponse GPT : {reply_text}")

        # 5. Synthèse vocale avec ElevenLabs
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
            logging.error(f"❌ Erreur ElevenLabs: {tts_response.text}")
            return jsonify({'error': 'Erreur ElevenLabs'}), 500

        # 6. Sauvegarde du MP3 temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_mp3:
            temp_mp3.write(tts_response.content)
            mp3_path = temp_mp3.name

        # 7. Conversion MP3 ➝ WAV avec ffmpeg direct (SANS pydub)
        final_wav = mp3_path.replace(".mp3", "_final.wav")
        if not convert_mp3_to_wav_ffmpeg(mp3_path, final_wav):
            logging.error("❌ Échec conversion audio")
            return jsonify({'error': 'Erreur conversion audio'}), 500
        
        logging.info("🎵 Conversion en WAV terminée")

        # 8. Encodage base64 pour retour API
        with open(final_wav, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")

        # 9. Nettoyage des fichiers temporaires
        try:
            os.unlink(wav_path)
            os.unlink(mp3_path) 
            os.unlink(final_wav)
        except:
            pass

        return jsonify({"audio_base64": audio_base64})

    except Exception as e:
        logging.exception("⚠️ Exception dans le traitement de la requête")
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    """Route de vérification de santé"""
    return "Neo Voice Agent is running! 🚀"

if __name__ == "__main__":
    logging.info("🚀 Démarrage de Neo...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
