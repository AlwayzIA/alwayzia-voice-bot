from flask import Flask, request, jsonify
import requests
import os
from twilio.twiml.voice_response import VoiceResponse
from openai import OpenAI
from dotenv import load_dotenv
import uuid
import httpx

# Charger les variables d'environnement
load_dotenv()

# Configuration de l'application Flask
app = Flask(__name__)

# Initialisation de l'API OpenAI
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Définir un endpoint de santé
@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "service": "Neo Voice Agent",
        "status": "operational",
        "configs": {
            "openai": True,
            "elevenlabs": True,
            "deepgram": True
        }
    })

# Point d'entrée pour les appels vocaux
@app.route("/voice", methods=["POST"])
def voice():
    response = VoiceResponse()
    response.say("Bonjour et bienvenue. Veuillez laisser votre message après le bip.", language="fr-FR", voice="Polly.Celine")
    response.record(maxLength=10, action="/process_recording", method="POST")
    return str(response)

# Traitement de l'enregistrement vocal
@app.route("/process_recording", methods=["POST"])
def process_recording():
    try:
        print("🔔 Nouvel appel reçu")
        print("📥 Traitement de l'enregistrement")

        # Télécharger l'enregistrement depuis Twilio avec authentification
        recording_url = request.form["RecordingUrl"] + "/media"
        print(f"📥 Téléchargement depuis: {recording_url}")

        TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
        TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

        audio_response = requests.get(recording_url, auth=(TWILIO_SID, TWILIO_TOKEN))

        if audio_response.status_code != 200:
            print(f"❌ Erreur HTTP: {audio_response.status_code}")
            return "Erreur dans process_recording"

        # Sauvegarder temporairement le fichier audio
        filename = f"/tmp/{uuid.uuid4()}.wav"
        with open(filename, "wb") as f:
            f.write(audio_response.content)

        print(f"✅ Audio sauvegardé localement : {filename}")

        # Traitement avec OpenAI Whisper (ou autre si implémenté)
        transcript = "Transcription simulée..."  # À remplacer par un appel réel
        print(f"📝 Transcription : {transcript}")

        # Répondre à l'appelant
        response = VoiceResponse()
        response.say(f"Vous avez dit : {transcript}", language="fr-FR", voice="Polly.Celine")
        return str(response)

    except Exception as e:
        print(f"ERROR:main:Erreur dans process_recording: {str(e)}")
        return "Erreur interne", 500

# Lancement de l'application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
