from flask import Flask, request, Response
import os
from dotenv import load_dotenv
from twilio.twiml.voice_response import VoiceResponse
import openai
import requests

# Chargement des variables d'environnement
load_dotenv()

# Clés API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialisation de Flask
app = Flask(__name__)

@app.route("/voice", methods=["POST"])
def voice():
    """Répond à un appel vocal Twilio avec une réponse générée par GPT"""
    response = VoiceResponse()

    # Message d’intro (Neo)
    intro = "Bonjour et bienvenue. Que puis-je faire pour vous aujourd’hui ?"
    response.say(intro, voice="alice", language="fr-FR")

    return Response(str(response), mimetype="application/xml")

@app.route("/")
def index():
    return "Neo Voice Agent est en ligne ✅"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
