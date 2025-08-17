import os
import base64
import logging
import tempfile
import subprocess
from typing import Optional, Tuple

import openai
import requests
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv

# ==================== Configuration ====================
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_VOICE_ID = "kENkNtk0xyzG09WW40xE"
PORT = int(os.environ.get("PORT", 5000))

# ==================== Services ====================

class AudioConverter:
    @staticmethod
    def mp3_to_wav(mp3_path: str, wav_path: str) -> bool:
        try:
            cmd = [
                'ffmpeg', '-i', mp3_path,
                '-ar', '8000',
                '-ac', '1',
                '-acodec', 'pcm_mulaw',
                '-f', 'wav', wav_path, '-y'
            ]
            subprocess.run(cmd, check=True)
            return True
        except Exception as e:
            logger.error(f"Erreur conversion audio : {e}")
            return False

class TranscriptionService:
    @staticmethod
    def transcribe(audio_path: str) -> Optional[str]:
        try:
            with open(audio_path, "rb") as f:
                response = requests.post(
                    "https://api.deepgram.com/v1/listen",
                    headers={
                        "Authorization": f"Token {DEEPGRAM_API_KEY}",
                        "Content-Type": "audio/wav"
                    },
                    files={"file": f},
                    data={"model": "nova", "language": "fr", "punctuate": True}
                )
            return response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
        except Exception as e:
            logger.error(f"Erreur transcription : {e}")
            return None

class ChatService:
    @staticmethod
    def generate_response(user_input: str) -> Optional[str]:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Tu es Neo, l'assistant vocal IA d'AlwayzIA. Tu es professionnel, concis et serviable. Tes réponses sont claires et adaptées au contexte téléphonique. Limite tes réponses à 2-3 phrases maximum."},
                    {"role": "user", "content": user_input}
                ],
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message["content"]
        except Exception as e:
            logger.error(f"Erreur génération réponse : {e}")
            return None

class TextToSpeechService:
    @staticmethod
    def synthesize(text: str) -> Optional[bytes]:
        try:
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.4, "similarity_boost": 0.8}
                }
            )
            return response.content if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Erreur synthèse vocale : {e}")
            return None

class AudioPipeline:
    @staticmethod
    def process(audio_url: str) -> Tuple[Optional[str], Optional[str]]:
        temp_files = []
        try:
            response = requests.get(audio_url)
            if response.status_code != 200:
                return None, "Échec téléchargement audio"

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
                temp_wav.write(response.content)
                wav_path = temp_wav.name
                temp_files.append(wav_path)

            text = TranscriptionService.transcribe(wav_path)
            if not text:
                return None, "Erreur transcription"

            reply = ChatService.generate_response(text)
            if not reply:
                return None, "Erreur génération réponse"

            audio = TextToSpeechService.synthesize(reply)
            if not audio:
                return None, "Erreur synthèse vocale"

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_mp3:
                temp_mp3.write(audio)
                mp3_path = temp_mp3.name
                temp_files.append(mp3_path)

            final_wav = mp3_path.replace(".mp3", "_final.wav")
            if not AudioConverter.mp3_to_wav(mp3_path, final_wav):
                return None, "Erreur conversion audio"

            with open(final_wav, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8"), None
        except Exception as e:
            return None, str(e)
        finally:
            for file in temp_files:
                try:
                    os.remove(file)
                except:
                    pass

# ==================== Flask App ====================

app = Flask(__name__)

@app.route("/neo", methods=["POST"])
def neo():
    recording_url = request.form.get("RecordingUrl")
    if not recording_url:
        return jsonify({"error": "RecordingUrl manquant"}), 400

    audio_b64, error = AudioPipeline.process(f"{recording_url}.wav")
    if error:
        return jsonify({"error": error}), 500
