"""
Neo Voice Agent - AlwayzIA
API Flask pour agent vocal IA avec transcription Deepgram, GPT-4 et synthèse ElevenLabs
"""

import os
import base64
import logging
import tempfile
import subprocess
from typing import Optional, Tuple, Dict, Any

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
    """Configuration centralisée de l'application"""
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    ELEVENLABS_VOICE_ID = "kENkNtk0xyzG09WW40xE"
    GPT_MODEL = "gpt-4o-mini"
    PORT = int(os.environ.get("PORT", 5000))
    
    # Paramètres de synthèse vocale
    TTS_STABILITY = 0.4
    TTS_SIMILARITY_BOOST = 0.8
    
    # Paramètres audio
    AUDIO_SAMPLE_RATE = 8000
    AUDIO_CHANNELS = 1

# Validation des clés API
def validate_config() -> None:
    """Valide que toutes les clés API nécessaires sont présentes"""
    required_keys = {
        "OPENAI_API_KEY": Config.OPENAI_API_KEY,
        "ELEVENLABS_API_KEY": Config.ELEVENLABS_API_KEY,
        "DEEPGRAM_API_KEY": Config.DEEPGRAM_API_KEY
    }
    
    missing_keys = [key for key, value in required_keys.items() if not value]
    
    if missing_keys:
        error_msg = f"Clés API manquantes: {', '.join(missing_keys)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

# ==================== Application Flask ====================
app = Flask(__name__)

# Configuration OpenAI
openai.api_key = Config.OPENAI_API_KEY

# ==================== Services ====================

class AudioConverter:
    """Service de conversion audio"""
    
    @staticmethod
    def mp3_to_wav(mp3_path: str, wav_path: str) -> bool:
        """
        Convertit un fichier MP3 en WAV format Twilio
        
        Args:
            mp3_path: Chemin du fichier MP3 source
            wav_path: Chemin de destination du fichier WAV
            
        Returns:
            bool: True si la conversion réussit, False sinon
        """
        try:
            cmd = [
                'ffmpeg', '-i', mp3_path,
                '-ar', str(Config.AUDIO_SAMPLE_RATE),
                '-ac', str(Config.AUDIO_CHANNELS),
                '-acodec', 'pcm_mulaw',
                '-f', 'wav',
                wav_path, '-y'
            ]
            
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            
            logger.info("✅ Conversion audio réussie")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Erreur ffmpeg: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("❌ ffmpeg non trouvé sur le système")
            return False


class TranscriptionService:
    """Service de transcription audio avec Deepgram"""
    
    @staticmethod
    def transcribe(audio_path: str) -> Optional[str]:
        """
        Transcrit un fichier audio en texte
        
        Args:
            audio_path: Chemin du fichier audio
            
        Returns:
            str: Transcription du texte ou None si erreur
        """
        try:
            with open(audio_path, "rb") as audio_file:
                response = requests.post(
                    "https://api.deepgram.com/v1/listen",
                    headers={
                        "Authorization": f"Token {Config.DEEPGRAM_API_KEY}",
                        "Content-Type": "audio/wav"
                    },
                    files={"file": audio_file},
                    data={
                        "model": "nova",
                        "language": "fr",
                        "punctuate": True
                    }
                )
            
            if response.status_code != 200:
                logger.error(f"❌ Erreur Deepgram ({response.status_code}): {response.text}")
                return None
            
            result = response.json()
            transcription = result["results"]["channels"][0]["alternatives"][0]["transcript"]
            logger.info(f"📝 Transcription: {transcription}")
            return transcription
            
        except Exception as e:
            logger.error(f"❌ Erreur transcription: {str(e)}")
            return None


class ChatService:
    """Service de génération de réponse avec OpenAI"""
    
    SYSTEM_PROMPT = """Tu es Neo, l'assistant vocal IA d'AlwayzIA.
    Tu es professionnel, concis et serviable.
    Tes réponses sont claires et adaptées au contexte téléphonique.
    Limite tes réponses à 2-3 phrases maximum."""
    
    @staticmethod
    def generate_response(user_message: str) -> Optional[str]:
        """
        Génère une réponse basée sur le message utilisateur
        
        Args:
            user_message: Message de l'utilisateur
            
        Returns:
            str: Réponse générée ou None si erreur
        """
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
            
            reply = response.choices[0].message.content
            logger.info(f"🤖 Réponse: {reply}")
            return reply
            
        except Exception as e:
            logger.error(f"❌ Erreur OpenAI: {str(e)}")
            return None


class TextToSpeechService:
    """Service de synthèse vocale avec ElevenLabs"""
    
    @staticmethod
    def synthesize(text: str) -> Optional[bytes]:
        """
        Convertit du texte en audio
        
        Args:
            text: Texte à convertir
            
        Returns:
            bytes: Contenu audio MP3 ou None si erreur
        """
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
                logger.error(f"❌ Erreur ElevenLabs ({response.status_code}): {response.text}")
                return None
            
            logger.info("🎵 Synthèse vocale réussie")
            return response.content
            
        except Exception as e:
            logger.error(f"❌ Erreur synthèse vocale: {str(e)}")
            return None


class AudioPipeline:
    """Pipeline de traitement audio complet"""
    
    @staticmethod
    def process_request(audio_url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Traite une requête audio complète
        
        Args:
            audio_url: URL de l'audio à traiter
            
        Returns:
            Tuple[str, str]: (audio_base64, message_erreur)
        """
        temp_files = []
        
        try:
            # 1. Téléchargement de l'audio
            logger.info(f"🔊 Téléchargement: {audio_url}")
            audio_response = requests.get(audio_url)
            
            if audio_response.status_code != 200:
                return None, "Impossible de télécharger l'audio"
            
            # 2. Sauvegarde temporaire
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
                temp_wav.write(audio_response.content)
                wav_path = temp_wav.name
                temp_files.append(wav_path)
            
            # 3. Transcription
            transcription = TranscriptionService.transcribe(wav_path)
            if not transcription:
                return None, "Erreur lors de la transcription"
            
            # 4. Génération de la réponse
            response_text = ChatService.generate_response(transcription)
            if not response_text:
                return None, "Erreur lors de la génération de la réponse"
            
            # 5. Synthèse vocale
            audio_mp3 = TextToSpeechService.synthesize(response_text)
            if not audio_mp3:
                return None, "Erreur lors de la synthèse vocale"
            
            # 6. Sauvegarde MP3 temporaire
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_mp3:
                temp_mp3.write(audio_mp3)
                mp3_path = temp_mp3.name
                temp_files.append(mp3_path)
            
            # 7. Conversion en WAV
            final_wav_path = mp3_path.replace(".mp3", "_final.wav")
            temp_files.append(final_wav_path)
            
            if not AudioConverter.mp3_to_wav(mp3_path, final_wav_path):
                return None, "Erreur lors de la conversion audio"
            
            # 8. Encodage base64
            with open(final_wav_path, "rb") as f:
                audio_base64 = base64.b64encode(f.read()).decode("utf-8")
            
            return audio_base64, None
            
        except Exception as e:
            logger.exception("⚠️ Erreur dans le pipeline audio")
            return None, str(e)
            
        finally:
            # Nettoyage des fichiers temporaires
            for file_path in temp_files:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    logger.warning(f"Impossible de supprimer {file_path}: {e}")


# ==================== Routes ====================

@app.route('/neo', methods=['POST'])
def neo_voice_agent() -> Response:
    """
    Endpoint principal pour le traitement des appels vocaux
    
    Returns:
        Response: Réponse JSON avec l'audio en base64 ou erreur
    """
    try:
        logger.info("📞 Nouvelle requête reçue sur /neo")
        
        # Récupération de l'URL audio depuis Twilio
        recording_url = request.form.get('RecordingUrl')
        if not recording_url:
            return jsonify({'error': 'URL d\'enregistrement manquante'}), 400
        
        audio_url = f"{recording_url}.wav"
        
        # Traitement de la requête
        audio_base64, error = AudioPipeline.process_request(audio_url)
        
        if error:
            logger.error(f"❌ Erreur: {error}")
            return jsonify({'error': error}), 500
        
        logger.info("✅ Requête traitée avec succès")
        return jsonify({
            'success': True,
            'audio_base64': audio_base64
        })
        
    except Exception as e:
        logger.exception("⚠️ Exception non gérée")
        return jsonify({'error': 'Erreur serveur interne'}), 500


@app.route('/', methods=['GET'])
def health_check() -> str:
    """
    Endpoint de vérification de santé
    
    Returns:
        str: Message de statut
    """
    return "🚀 Neo Voice Agent est opérationnel - AlwayzIA"


@app.route('/status', methods=['GET'])
def status() -> Response:
    """
    Endpoint de statut détaillé
    
    Returns:
        Response: JSON avec les informations de statut
    """
    status_info = {
        'service': 'Neo Voice Agent',
        'version': '1.0.0',
        'status': 'operational',
        'configs': {
            'openai_configured': bool(Config.OPENAI_API_KEY),
            'elevenlabs_configured': bool(Config.ELEVENLABS_API_KEY),
            'deepgram_configured': bool(Config.DEEPGRAM_API_KEY)
        }
    }
    return jsonify(status_info)


# ==================== Point d'entrée ====================

if __name__ == "__main__":
    try:
        # Validation de la configuration
        validate_config()
        
        logger.info("=" * 50)
        logger.info("🚀 Démarrage de Neo Voice Agent")
        logger.info(f"📡 Port: {Config.PORT}")
        logger.info("=" * 50)
        
        # Démarrage du serveur
        app.run(
            host="0.0.0.0",
            port=Config.PORT,
            debug=False  # Ne jamais activer debug en production
        )
        
    except Exception as e:
        logger.error(f"❌ Impossible de démarrer l'application: {e}")
        exit(1)
