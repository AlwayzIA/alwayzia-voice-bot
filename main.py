import os
import time
import requests
import logging
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from openai import OpenAI
from dotenv import load_dotenv

# Configuration de base
logging.basicConfig(level=logging.INFO)
load_dotenv()

# Clés API et variables d'environnement
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 8080))

# Initialisation des clients externes
deepgram = DeepgramClient(DEEPGRAM_API_KEY)
openai = OpenAI(api_key=OPENAI_API_KEY)

# Initialisation de Flask
app = Flask(__name__)

@app.route("/voice", methods=["POST"])
def voice():
    """Traite un appel entrant avec Twilio et répond avec un message d'accueil."""
    response = VoiceResponse()
    response.say("Bonjour et bienvenue, merci de laisser votre message après le bip.", language='fr-FR')
    response.record(maxLength=30, timeout=5, action="/process_recording", method="POST")
    response.hangup()
    return str(response)

@app.route("/process_recording", methods=["POST"])
def process_recording():
    """Récupère l'enregistrement, le transcrit avec Deepgram, puis le traite avec OpenAI."""
    recording_url = request.form.get("RecordingUrl")
    if not recording_url:
        return "Aucun enregistrement reçu", 400

    logging.info(f"📎 URL brute retournée par Twilio : {recording_url}")
    wav_url = f"{recording_url}.wav"
    logging.info(f"🎯 URL utilisée pour la transcription : {wav_url}")

    try:
        source: FileSource = {"url": wav_url}
        options: PrerecordedOptions = PrerecordedOptions(model="nova")
        response = deepgram.listen.prerecorded.v(
