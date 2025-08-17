import os
from flask import Flask, request, Response
from openai import OpenAI
from twilio.twiml.voice_response import VoiceResponse
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)

# Initialisation client OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialisation de Flask
app = Flask(__name__)

@app.route("/neo", methods=["POST"])
def neo_voice():
    """Réponse de Neo à un appel Twilio"""
    try:
        user_input = request.form.get("SpeechResult") or request.form.get("Digits") or "Bonjour"

        logging.info(f"Texte reçu depuis Twilio : {user_input}")

        # Appel à l'API OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es Neo, un assistant vocal pour les hôtels. Réponds de façon naturelle, professionnelle et utile."},
                {"role": "user", "content": user_input}
            ]
        )

        reply = response.choices[0].message.content.strip()
        logging.info(f"Réponse générée par Neo : {reply}")

        # Réponse vocale avec Twilio
        twilio_response = VoiceResponse()
        twilio_response.say(reply, voice="alice", language="fr-FR")

        return Response(str(twilio_response), mimetype="application/xml")

    except Exception as e:
        logging.error(f"Erreur pendant le traitement : {e}")
        error_response = VoiceResponse()
        error_response.say("Une erreur est survenue. Merci de rappeler plus tard.", voice="alice", language="fr-FR")
        return Response(str(error_response), mimetype="application/xml")

@app.route("/", methods=["GET"])
def home():
    return "Neo Voice Agent is up and running 🚀", 200
