"""
Neo Voice Agent - AlwayzIA
API Flask pour agent vocal IA avec transcription Deepgram, GPT-4 et synthèse ElevenLabs
"""

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

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Variables d'environnement
class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    ELEVENLABS_VOICE_ID = "kENkNtk0xyzG09WW40xE"
    GPT_MODEL = "gpt-4o-mini"
    PORT = int(os.environ.get("PORT", 5000))
    TTS_STABILITY = 0.4
    TTS_SIMILARITY_BOOST = 0.8
    AUDIO_SAMPLE_RATE = 8000
    AUDIO_CHANNELS = 1

# Validation des clés API
def validate_config():
    required_keys = {
        "OPENAI_API_KEY": Config.OPENAI_API_KEY,
        "ELEVENLABS_API_KEY": Config.ELEVENLABS_API_KEY,
        "DEEPGRAM_API_KEY": Config.DEEPGRAM_API_KEY
    }
    missing = [key for key, val in required_keys.items() if not val]
    if missing:
        raise ValueError(f"Clés API manquantes: {', '.join(missing)}")

# ==================== Application Flask ====================
app = Flask(__name__)
openai.api_key = Config.OPENAI_API_KEY

# ==================== Services ====================
class AudioConverter:
    @staticmethod
    def mp3_to_wav(mp3_path: str, wav_path: str) -> bool:
        try:
            cmd = [
                'ffmpeg', '-i', mp3_path,
                '-ar', str(Config.AUDIO_SAMPLE_RATE),
                '-ac', str(Config.AUDIO_CHANNELS),
                '-acodec', 'pcm_mulaw',
                '-f', 'wav', wav_path, '-y'
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("✅ Conversion MP3 -> WAV réussie")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur de conversion audio : {e}")
            return False

class TranscriptionService:
    @staticmethod
    def transcribe(wav_path: str) -> Optional[str]:
        try:
            with open(wav_path, "rb") as audio_file:
                res = requests.post(
                    "https://api.deepgram.com/v1/listen",
                    headers={
                        "Authorization": f"Token {Config.DEEPGRAM_API_KEY}",
                        "Content-Type": "audio/wav"
                    },
                    files={"file": audio_file},
                    data={"model": "nova", "language": "fr", "punctuate": True}
                )
            if res.status_code != 200:
                logger.error(f"Deepgram: {res.status_code} - {res.text}")
                return None
            transcript = res.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
            logger.info(f"📝 Transcription: {transcript}")
            return transcript
        except Exception as e:
            logger.error(f"❌ Transcription échouée : {e}")
            return None

class ChatService:
    SYSTEM_PROMPT = """Tu es Neo, assistant IA d’AlwayzIA.
Tu es concis, professionnel et amical.
Ne réponds jamais plus de 3 phrases. Adapte-toi au contexte hôtelier."""

    @staticmethod
    def generate_response(user_input: str) -> Optional[str]:
        try:
            client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[
                    {"role": "system", "content": ChatService.SYSTEM_PROMPT},
                    {"role": "user", "content": user_input}
                ]
            )
            answer = response.choices[0].message.content
            logger.info(f"🤖 Réponse IA : {answer}")
            return answer
        except Exception as e:
            logger.error(f"❌ Erreur OpenAI : {e}")
            return None

class TextToSpeechService:
    @staticmethod
    def synthesize(text: str) -> Optional[bytes]:
        try:
            res = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{Config.ELEVENLABS_VOICE_ID}",
                headers={
                    "xi-api-key": Config.ELEVENLABS_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": Config.TTS_STABILITY,
                        "similarity_boost": Config.TTS_SIMILARITY_BOOST
                    }
                }
            )
            if res.status_code != 200:
                logger.error(f"ElevenLabs: {res.status_code} - {res.text}")
                return None
            return res.content
        except Exception as e:
            logger.error(f"❌ Synthèse vocale échouée : {e}")
            return None

class AudioPipeline:
    @staticmethod
    def process(audio_url: str) -> Tuple[Optional[str], Optional[str]]:
        temp_files = []
        try:
            # 1. Télécharger
            audio = requests.get(f"{audio_url}.wav")
            if audio.status_code != 200:
                return None, "Erreur de téléchargement de l'audio"
            
            # 2. Écriture WAV
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(audio.content)
                wav_path = f.name
                temp_files.append(wav_path)

            # 3. Transcrire
            text = TranscriptionService.transcribe(wav_path)
            if not text:
                return None, "Erreur transcription"

            # 4. Réponse IA
            answer = ChatService.generate_response(text)
            if not answer:
                return None, "Erreur IA"

            # 5. Synthèse
            audio_mp3 = TextToSpeechService.synthesize(answer)
            if not audio_mp3:
                return None, "Erreur synthèse vocale"

            # 6. MP3 → WAV
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                f.write(audio_mp3)
                mp3_path = f.name
                temp_files.append(mp3_path)

            final_wav = mp3_path.replace(".mp3", "_final.wav")
            temp_files.append(final_wav)

            if not AudioConverter.mp3_to_wav(mp3_path, final_wav):
                return None, "Conversion audio échouée"

            with open(final_wav, "rb") as f:
                base64_audio = base64.b64encode(f.read()).decode("utf-8")

            return base64_audio, None

        except Exception as e:
            logger.exception("⚠️ Pipeline échoué")
            return None, str(e)
        finally:
            for path in temp_files:
                try:
                    os.unlink(path)
                except:
                    pass

# ==================== Routes ====================
@app.route("/neo", methods=["POST"])
def neo_handler():
    try:
        logger.info("📞 Appel entrant reçu")
        url = request.form.get("RecordingUrl")
        if not url:
            return jsonify({"error": "RecordingUrl manquant"}), 400

        audio_b64, err = AudioPipeline.process(url)
        if err:
            return jsonify({"error": err}), 500

        return jsonify({"success": True, "audio_base64": audio_b64})

    except Exception as e:
        logger.exception("Erreur inconnue")
        return jsonify({"error": "Erreur serveur interne"}), 500

@app.route("/", methods=["GET"])
def index():
    return "✅ Neo Voice Agent - AlwayzIA actif"

@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "status": "ok",
        "openai": bool(Config.OPENAI_API_KEY),
        "deepgram": bool(Config.DEEPGRAM_API_KEY),
        "elevenlabs": bool(Config.ELEVENLABS_API_KEY)
    })

# ==================== Entrée ====================
if __name__ == "__main__":
    validate_config()
    logger.info("🚀 Démarrage de Neo Voice Agent")
    app.run(host="0.0.0.0", port=Config.PORT)
