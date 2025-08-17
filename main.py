import os
from flask import Flask, request, Response
from openai import OpenAI
from twilio.twiml.voice_response import VoiceResponse
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO)

# Chargement de l'API Key OpenAI
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# Initialisation de Flask
app = Flask(__name__)

@app.route("/neo", methods=["POST"])
def neo_voice():
    """Endpoint Twilio Voice → déclenchement de Neo"""
    try:
        # Transcription automatique de Twilio (optionnel)
        user_input = request.form.get("SpeechResult") or request.form.get("Digits") or "Bonjour"

        logging.info(f"Message reçu : {user_input}")

        # Envoi à l’API OpenAI (GPT-4-turbo)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es Neo, un assistant vocal pour un hôtel. Sois clair, utile et poli."},
                {"role": "user", "content": user_input}
            ]
        )

        assistant_reply = response.choices[0].message.content.strip()
        logging.info(f"Réponse de Neo : {assistant_reply}")

        # Réponse vocale avec Twilio (voix par défaut Alice)
        twilio_response = VoiceResponse()
        twilio_response.say(assistant_reply, voice="alice", language="fr-FR")

        return Response(str(twilio_response), mimetype="application/xml")

    except Exception as e:
        logging.error(f"Erreur : {e}")
        error_response = VoiceResponse()
        error_response.say("Désolé, une erreur est survenue.", voice="alice", language="fr-FR")
        return Response(str(error_response), mimetype="application/xml")

@app.route("/", methods=["GET"])
def home():
    return "Neo Voice Agent is live!", 200
