from flask import Flask, request, jsonify
import requests
import os
from twilio.twiml.voice_response import VoiceResponse
from openai import OpenAI
from dotenv import load_dotenv
import uuid
import time  # ← ajout pour temporisation

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"service": "Neo Voice Agent", "status": "operational"})

@app.route("/voice", methods=["POST"])
def voice():
    response = VoiceResponse()
    response.say("Bonjour et bienvenue. Veuillez laisser votre message après le bip.", language="fr-FR", voice="Polly.Celine")
    response.record(maxLength=10, action="/process_recording", method="POST")
    return str(response)

@app.route("/process_recording", methods=["POST"])
def process_recording():
    try:
        print("🔔 Nouvel appel reçu")
        print("📥 Traitement de l'enregistrement")

        recording_url = request.form["RecordingUrl"]
        print(f"🔗 URL brute retournée par Twilio : {recording_url}")

        TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
        TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

        # 🔁 Attendre 1 seconde pour que Twilio finalise l’upload du fichier
        time.sleep(1)

        # Télécharger l'enregistrement avec authentification
        audio_response = requests.get(recording_url, auth=(TWILIO_SID, TWILIO_TOKEN))

        if audio_response.status_code != 200:
            print(f"❌ Erreur HTTP: {audio_response.status_code}")
            return "Erreur lors du téléchargement", 500

        filename = f"/tmp/{uuid.uuid4()}.wav"
        with open(filename, "wb") as f:
            f.write(audio_response.content)

        print(f"✅ Audio sauvegardé localement : {filename}")

        # Transcription simulée
        transcript = "Transcription simulée..."
        print(f"📝 Transcription : {transcript}")

        response = VoiceResponse()
        response.say(f"Vous avez dit : {transcript}", language="fr-FR", voice="Polly.Celine")
        return str(response)

    except Exception as e:
        print(f"🚨 ERREUR : {str(e)}")
        return "Erreur interne", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
