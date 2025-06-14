from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
import openai
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Charger le prompt depuis le fichier texte
with open("neo_prompt.txt", "r") as f:
    neo_prompt = f.read()

# Créer l'application Flask
app = Flask(__name__)

@app.route("/voice", methods=["POST"])
def voice():
    """Gère les appels entrants via Twilio + OpenAI"""

    user_input = "Bonjour"  # Remplacé plus tard par Deepgram

    response_ai = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": neo_prompt},
            {"role": "user", "content": user_input}
        ]
    )

    text = response_ai["choices"][0]["message"]["content"]

    response = VoiceResponse()
    response.say(text, language="fr-FR", voice="alice")

    return Response(str(response), mimetype="text/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
