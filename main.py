import os
from flask import Flask, request, Response
from dotenv import load_dotenv
from openai import OpenAI
import requests

# Charger les variables d'environnement
load_dotenv()

# Initialiser le client OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Créer l'application Flask
app = Flask(__name__)

# Lire le prompt depuis un fichier
with open("neo_prompt.txt", "r") as f:
    SYSTEM_PROMPT = f.read()

@app.route("/twilio", methods=["POST"])
def voice():
    """Route principale appelée par Twilio lors d’un appel entrant"""
    from twilio.twiml.voice_response import VoiceResponse, Gather

    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/response",
        method="POST",
        speech_timeout="auto",
        language="fr-FR"
    )
    gather.say("Bonjour, je suis Neo, l'agent IA de votre établissement. Que puis-je faire pour vous aujourd'hui ?")
    response.append(gather)
    response.redirect("/twilio")  # Relance l'écoute si rien n'est dit
    return Response(str(response), mimetype="application/xml")

@app.route("/response", methods=["POST"])
def generate_response():
    """Répond à l’utilisateur avec l’API OpenAI"""
    from twilio.twiml.voice_response import VoiceResponse

    user_input = request.form.get("SpeechResult")
    if not user_input:
        return Response("<Response><Say>Je n'ai pas compris. Pouvez-vous répéter ?</Say><Redirect>/twilio</Redirect></Response>", mimetype="application/xml")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]

    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7
        )
        ai_response = completion.choices[0].message.content
    except Exception as e:
        ai_response = "Désolé, une erreur s'est produite. Veuillez réessayer plus tard."
        print(f"Erreur OpenAI: {e}")

    response = VoiceResponse()
    response.say(ai_response, language="fr-FR")
    response.redirect("/twilio")
    return Response(str(response), mimetype="application/xml")
