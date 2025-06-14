with open("neo_prompt.txt", "r") as f:
    neo_prompt = f.read()

from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
import openai
import os
from neo_prompt import neo_prompt
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route("/voice", methods=["POST"])
def voice():
    """Gère les appels entrants via Twilio avec OpenAI"""

    user_input = "Bonjour"  # plus tard remplacé par Deepgram

    response_ai = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": neo_prompt},
            {"role": "user", "content": user_input}
        ]
    )

    text = response_ai['choices'][0]['message']['content']

    response = VoiceResponse()
    response.say(text, language="fr-FR", voice="alice")

    return Response(str(response), mimetype="text/xml")
