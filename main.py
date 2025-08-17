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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Config:
    """Configuration centralisée"""
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

def validate_config() -> None:
    required_keys = {
        "OPENAI_API_KEY": Config.OPENAI_API_KEY,
        "ELEVENLABS_API_KEY": Config.ELEVENLABS_API_KEY,
        "DEEPGRAM_API_KEY": Config.DEEPGRAM_API_KEY
    }
    missing = [k for k, v in required_keys.items() if not v]
    if missing:
        raise ValueError(f"Clés API manquantes : {', '.join(missing)}")

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
                '-f', 'wav',
                wav_path, '-y'
            ]
            subprocess.run(cmd, check=True)
            logger.info("✅ Conversion audio réussie")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur conversion ffmpeg : {e}")
            return False

class TranscriptionService:
    @staticmethod
    def transcribe(audio_path: str) -> Optional[str]:
        try:
            with open(audio_path, "rb") as f:
                response = requests.post(
                    "https://api.deepgram.com/v1/listen",
                    headers={
                        "Authorization": f"Token {Config.DEEPGRAM_API_KEY}",
                        "Content-Type": "audio/wav"
                    },
                    files={"file": f},
                    data={"model": "nova", "language": "fr", "punctuate": True}
                )
            if response.status_code != 200:
                logger.error(f"❌ Deepgram: {response.status_code} - {response.text}")
                return None
            return response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
        except Exception as e:
            logger.error(f"❌ Erreur transcription : {e}")
            return None

class ChatService:
    SYSTEM_PROMPT = (
        "Tu es Neo, l'assistant vocal IA d'AlwayzIA. "
        "Tu es professionnel, concis et serviable. "
        "Réponds toujours en 2 à 3 phrases maximum."
    )

    @staticmethod
    def generate_response(user_message: str) -> Optional[str]:
        try:
            client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[
                    {"role": "system", "content": ChatService.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"❌ Erreur GPT : {e}")
            return None

class TextToSpeechService:
    @staticmethod
    def synthesize(text: str) -> Optional[bytes]:
        try:
            response = requests.post(
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
            if response.status_code != 200:
                logger.error(f"❌ Erreur ElevenLabs: {response.text}")
                return None
            return response.content
        except Exception as e:
            logger.error(f"❌ Synthèse vocale erreur : {e}")
            return None

class AudioPipeline:
    @staticmethod
    def process_request(audio_url: str) -> Tuple[Optional[str], Optional[str]]:
        temp_files = []
        try:
            logger.info(f"🔊 Téléchargement de l’audio : {audio_url}")
            r = requests.get(audio_url)
            if r.status_code != 200:
                return None, "Erreur téléchargement audio"

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(r.content)
                wav_path = tmp.name
                temp_files.append(wav_path)

            transcript = TranscriptionService.transcribe(wav_path)
            if not transcript:
                return None, "Erreur transcription"

            reply = ChatService.generate_response(transcript)
            if not reply:
                return None, "Erreur génération réponse"

            mp3_data = TextToSpeechService.synthesize(reply)
            if not mp3_data:
                return None, "Erreur synthèse vocale"

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mp3:
                mp3.write(mp3_data)
                mp3_path = mp3.name
                temp_files.append(mp3_path)

            final_wav = mp3_path.replace(".mp3", "_final.wav")
            temp_files.append(final_wav)
            if not AudioConverter.mp3_to_wav(mp3_path, final_wav):
                return None, "Erreur conversion WAV"

            with open(final_wav, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return encoded, None
        except Exception as e:
            logger.error(f"❌ Pipeline erreur : {e}")
            return None, str(e)
        finally:
            for file in temp_files:
                try:
                    os.remove(file)
                except:
                    pass

# ==================== Routes ====================

@app.route('/neo', methods=['POST'])
def neo_voice_agent() -> Response:
    try:
        logger.info("📞 Requête reçue sur /neo")
        recording_url = request.form.get('RecordingUrl')
        if not recording_url:
            return jsonify({'error': 'URL d\'enregistrement manquante'}), 400
        audio_url = f"{recording_url}.wav"
        audio_b64, error = AudioPipeline.process_request(audio_url)
        if error:
            return jsonify({'error': error}), 500
        return jsonify({'success': True, 'audio_base64': audio_b64})
    except Exception as e:
        logger.error(f"❌ Erreur serveur : {e}")
        return jsonify({'error': 'Erreur interne'}), 500

@app.route('/', methods=['GET'])
def root():
    return "🚀 Neo Voice Agent est opérationnel - AlwayzIA"

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'service': 'Neo Voice Agent',
        'version': '1.0.0',
        'status': 'operational',
        'configs': {
            'openai_configured': bool(Config.OPENAI_API_KEY),
            'elevenlabs_configured': bool(Config.ELEVENLABS_API_KEY),
            'deepgram_configured': bool(Config.DEEPGRAM_API_KEY)
        }
    })

# ==================== Lancement ====================
if __name__ == "__main__":
    try:
        validate_config()
        logger.info("=" * 50)
        logger.info("🚀 Démarrage de Neo Voice Agent")
        logger.info(f"📡 Port: {Config.PORT}")
        logger.info("=" * 50)
        app.run(host="0.0.0.0", port=Config.PORT, debug=False)
    except Exception as e:
        logger.error(f"❌ Erreur au démarrage : {e}")
        exit(1)
