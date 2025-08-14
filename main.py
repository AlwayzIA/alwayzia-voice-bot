from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
import openai
import os

# Récupération de la clé API depuis Railway
openai.api_key = os.getenv("OPENAI_API_KEY")

# Charger le prompt système Neo
with open("neo_prompt.txt", "r") as f:
    neo_prompt = f.read()

# Initialiser l’app Flask
app = Flask(__name__)

@app.route("/voice", methods=["POST"])
def voice():
    """Gestion de l’appel entrant via Twilio + génération vocale IA"""

    response = VoiceResponse()

    try:
        # Simulation temporaire de l'entrée utilisateur (à remplacer par Deepgram)
        user_input = "Bonjour"

        # Appel à OpenAI avec gpt-4o
        response_ai = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": neo_prompt},
                {"role": "user", "content": user_input}
            ]
        )

        text = response_ai.choices[0].message.content
        print("Réponse GPT :", text)

    except Exception as e:
        print("[ERREUR GPT]", e)
        text = "Désolé, une erreur est survenue dans notre système d'assistance."

    # Créer un bloc Gather (même si pour l’instant il ne capte rien)
    gather = Gather(input='speech', timeout=3, language="fr-FR")
    gather.say(text, language="fr-FR", voice="alice")
    response.append(gather)

    # Si rien n’est dit au bout de 3 secondes, on répond par défaut (optionnel)
    response.say("Je n'ai rien entendu. N'hésitez pas à rappeler plus tard.", language="fr-FR", voice="alice")

    return Response(str(response), mimetype="text/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
