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
from twilio.twiml.voice_response import VoiceResponse, Gather

# ==================== Configuration ====================
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration des clés API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_VOICE_ID = "kENkNtk0xyzG09WW40xE"
PORT = int(os.environ.get("PORT", 5000))

# Client OpenAI (nouvelle version)
client = openai.OpenAI(api_key=OPENAI_API_KEY)

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
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info("✅ Conversion audio réussie")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur conversion audio : {e}")
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
            
            if response.status_code != 200:
                logger.error(f"Erreur Deepgram: {response.text}")
                return None
                
            transcript = response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
            logger.info(f"📝 Transcription: {transcript}")
            return transcript
        except Exception as e:
            logger.error(f"❌ Erreur transcription : {e}")
            return None

class ChatService:
    @staticmethod
    def generate_response(user_input: str) -> Optional[str]:
        try:
            # NOUVELLE API OpenAI
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # ou "gpt-4" si vous avez accès
                messages=[
                    {
                        "role": "system", 
                        "content": "Tu es Neo, l'assistant vocal IA d'AlwayzIA. Tu es professionnel, concis et serviable. Tes réponses sont claires et adaptées au contexte téléphonique. Limite tes réponses à 2-3 phrases maximum."
                    },
                    {"role": "user", "content": user_input}
                ],
                max_tokens=150,
                temperature=0.7
            )
            reply = response.choices[0].message.content
            logger.info(f"🤖 Réponse: {reply}")
            return reply
        except Exception as e:
            logger.error(f"❌ Erreur génération réponse : {e}")
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
            
            if response.status_code != 200:
                logger.error(f"Erreur ElevenLabs: {response.text}")
                return None
                
            logger.info("🎵 Synthèse vocale réussie")
            return response.content
        except Exception as e:
            logger.error(f"❌ Erreur synthèse vocale : {e}")
            return None

# ==================== Flask App ====================

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health_check():
    """Vérification de santé"""
    return "🚀 Neo Voice Agent est opérationnel - AlwayzIA"

@app.route("/status", methods=["GET"])
def status():
    """Statut détaillé"""
    return jsonify({
        "service": "Neo Voice Agent",
        "status": "operational",
        "configs": {
            "openai": bool(OPENAI_API_KEY),
            "elevenlabs": bool(ELEVENLABS_API_KEY),
            "deepgram": bool(DEEPGRAM_API_KEY)
        }
    })

@app.route("/voice", methods=["POST"])
def voice_webhook():
    """
    Webhook principal pour Twilio - Gère l'appel initial
    """
    try:
        logger.info("📞 Nouvel appel reçu")
        
        # Créer une réponse TwiML
        response = VoiceResponse()
        
        # Message de bienvenue
        response.say(
            "Bonjour, je suis Neo, votre assistant vocal. Comment puis-je vous aider?",
            voice="Polly.Lea",
            language="fr-FR"
        )
        
        # Enregistrer la réponse de l'utilisateur
        response.record(
            action="/process_recording",
            method="POST",
            max_length=10,
            finish_on_key="#",
            transcribe=False
        )
        
        # Si l'utilisateur ne dit rien
        response.say("Je n'ai pas entendu de réponse.", voice="Polly.Lea", language="fr-FR")
        
        return Response(str(response), mimetype='text/xml')
        
    except Exception as e:
        logger.error(f"Erreur dans voice_webhook: {e}")
        response = VoiceResponse()
        response.say("Désolé, une erreur s'est produite.", voice="Polly.Lea", language="fr-FR")
        return Response(str(response), mimetype='text/xml')

@app.route("/process_recording", methods=["POST"])
def process_recording():
    """
    Traite l'enregistrement et génère une réponse
    """
    try:
        logger.info("🎤 Traitement de l'enregistrement")
        
        # Récupérer l'URL de l'enregistrement
        recording_url = request.form.get("RecordingUrl")
        
        if not recording_url:
            logger.error("Pas d'URL d'enregistrement")
            response = VoiceResponse()
            response.say("Je n'ai pas pu recevoir votre message.", voice="Polly.Lea", language="fr-FR")
            return Response(str(response), mimetype='text/xml')
        
        # Télécharger et traiter l'audio
        audio_url = f"{recording_url}.wav"
        logger.info(f"📥 Téléchargement depuis: {audio_url}")
        
        audio_response = requests.get(audio_url)
        if audio_response.status_code != 200:
            raise Exception("Impossible de télécharger l'audio")
        
        # Sauvegarder temporairement
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
            temp_wav.write(audio_response.content)
            wav_path = temp_wav.name
        
        # Transcrire
        transcript = TranscriptionService.transcribe(wav_path)
        
        # Générer une réponse
        if transcript:
            ai_response = ChatService.generate_response(transcript)
        else:
            ai_response = "Je n'ai pas pu comprendre votre message. Pouvez-vous répéter?"
        
        # Nettoyer
        try:
            os.remove(wav_path)
        except:
            pass
        
        # Répondre avec TwiML
        response = VoiceResponse()
        response.say(ai_response or "Désolé, je n'ai pas pu générer une réponse.", 
                    voice="Polly.Lea", language="fr-FR")
        
        # Proposer de continuer
        gather = Gather(num_digits=1, action="/continue_conversation", method="POST")
        gather.say("Appuyez sur 1 pour poser une autre question, ou raccrochez.", 
                  voice="Polly.Lea", language="fr-FR")
        response.append(gather)
        
        return Response(str(response), mimetype='text/xml')
        
    except Exception as e:
        logger.error(f"Erreur dans process_recording: {e}")
        response = VoiceResponse()
        response.say("Désolé, une erreur s'est produite lors du traitement.", 
                    voice="Polly.Lea", language="fr-FR")
        return Response(str(response), mimetype='text/xml')

@app.route("/continue_conversation", methods=["POST"])
def continue_conversation():
    """
    Continue la conversation si l'utilisateur appuie sur 1
    """
    digit = request.form.get("Digits")
    
    response = VoiceResponse()
    
    if digit == "1":
        response.say("Je vous écoute.", voice="Polly.Lea", language="fr-FR")
        response.record(
            action="/process_recording",
            method="POST",
            max_length=10,
            finish_on_key="#"
        )
    else:
        response.say("Merci d'avoir utilisé Neo. Au revoir!", voice="Polly.Lea", language="fr-FR")
        response.hangup()
    
    return Response(str(response), mimetype='text/xml')

# Pour Railway uniquement (pas nécessaire avec Gunicorn)
if __name__ == "__main__":
    logger.info("🚀 Démarrage de Neo Voice Agent")
    app.run(host="0.0.0.0", port=PORT)
