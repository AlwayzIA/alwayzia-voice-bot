from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
import openai
import os
import requests
import base64

# Clés API
openai.api_key = os.getenv("OPENAI_API_KEY")
deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")

# Charger le prompt système Neo
with open("neo_prompt.txt", "r") as f:
    neo_prompt = f.read()

# Initialiser l’app Flask
app = Flask(__name__)

@app.route("/voice", methods=["POST"])
def voice():
    response = VoiceResponse()

    try:
        # Récupération de l'audio de l’appel Twilio
        recording_url = request.form.get("RecordingUrl")
        if not recording_url:
            raise ValueError("Aucun enregistrement trouvé dans l’appel.")

        # Ajouter l'extension du fichier audio
        recording_url += ".wav"

        # Télécharger l’audio depuis Twilio
        audio_data = requests.get(recording_url).content

        # Envoyer l’audio à Deepgram pour transcription
        dg_response = requests.post(
            "https://api.deepgram.com/v1/listen",
            headers={
                "Authorization": f"Token {deepgram_api_key}",
                "Content-Type": "audio/wav"
            },
            data=audio_data
        )

        transcription = dg_response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]

        print("[Transcription Deepgram] :", transcription)

        # Envoyer à GPT
        gpt_response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": neo_prompt},
                {"role": "user", "content": transcription}
            ]
        )

        text = gpt_response.choices[0].message.content

    except Exception as e:
        print("[ERREUR GPT/Deepgram]", e)
        text = "Désolé, une erreur est survenue dans notre système d'assistance."

    response.say(text, language="fr-FR", voice="alice")
    return Response(str(response), mimetype="text/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
