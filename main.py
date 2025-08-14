from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
import openai
import os
from dotenv import load_dotenv

# Charger les variables d’environnement
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Charger le prompt système
with open("neo_prompt.txt", "r", encoding="utf-8") as f:
    neo_prompt = f.read()

# Créer l'application Flask
app = Flask(__name__)

@app.route("/voice", methods=["POST"])
def voice():
    """Gère les appels entrants via Twilio avec OpenAI"""

    user_input = "Bonjour"

    try:
        client = openai.OpenAI(api_key=openai.api_key)

        response_ai = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": neo_prompt},
                {"role": "user", "content": user_input}
            ]
        )

        text = response_ai.choices[0].message.content

    except Exception as e:
        print(f"[ERREUR GPT] {e}")
        text = "Désolé, une erreur est survenue dans notre système d’assistance."

    response = VoiceResponse()
    response.say(text, language="fr-FR", voice="alice")

    return Response(str(response), mimetype="text/xml")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
