import os
from flask import Flask, request, Response
from openai import OpenAI
from twilio.twiml.voice_response import VoiceResponse
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)

# Initialisation du client OpenAI (pas de proxies ici !)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Création de l'app Flask
app = Flask(__name__)

@app.route("/neo", methods=["POST"])
def neo_voice():
    try:
        user_input = request.form.get("SpeechResult") or request.form.get("Digits") or "Bonjour"
        logging.info(f"Input Twilio : {user_input}")

        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es Neo, un assistant vocal pour les hôtels."},
                {"role": "user", "content": user_input}
            ]
        )

        reply = completion.choices[0].message.content.strip()
        logging.info(f"Réponse GPT : {reply}")

        response = VoiceResponse()
        response.say(reply, voice="alice", language="fr-FR")
        return Response(str(response), mimetype="application/xml")

    except Exception as e:
        logging.error(f"Erreur : {e}")
        response = VoiceResponse()
        response.say("Désolé, une erreur est survenue.", voice="alice", language="fr-FR")
        return Response(str(response), mimetype="application/xml")

@app.route("/", methods=["GET"])
def home():
    return "Neo est en ligne ✅", 200
