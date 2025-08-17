import os
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import openai
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configurer la clé API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route("/voice", methods=["POST"])
def voice():
    """Répond à un appel avec un message généré par l'IA."""
    try:
        # Extraire le message vocal de l'utilisateur depuis la transcription Twilio
        user_input = request.form.get("SpeechResult", "Bonjour")

        # Appeler l’API OpenAI
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un assistant vocal pour un hôtel."},
                {"role": "user", "content": user_input}
            ]
        )

        ai_response = completion.choices[0].message["content"]

        # Répondre à l'appel avec la réponse générée
        response = VoiceResponse()
        response.say(ai_response, voice='alice', language='fr-FR')
        return str(response)
    except Exception as e:
        response = VoiceResponse()
        response.say("Une erreur est survenue. Merci de rappeler plus tard.", voice='alice', language='fr-FR')
        print("Erreur:", e)
        return str(response)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
