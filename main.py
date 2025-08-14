from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
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
    """Déclenché lors d’un appel entrant via Twilio"""

    response = VoiceResponse()

    # Démarrer l’enregistrement vocal manuellement
    response.record(
        timeout=10,  # délai sans parole avant fin auto
        transcribe=False,
        max_length=60,  # durée max en secondes
        play_beep=True,
        recording_status_callback="/recording"
    )

    return Response(str(response), mimetype="text/xml")


@app.route("/recording", methods=["POST"])
def recording():
    """Callback Twilio quand l’enregistrement est prêt"""

    recording_url = request.form.get("RecordingUrl")

    if not recording_url:
        print("[ERREUR GPT/Deepgram] Aucun enregistrement trouvé dans l’appel.")
        return Response("Aucun enregistrement trouvé", status=400)

    print(f"[INFO] Enregistrement vocal disponible : {recording_url}")

    # Tu pourras ici envoyer ce fichier à Deepgram pour transcription
    # Exemple : transcription_deepgram(recording_url) → à faire ensemble

    return Response("Enregistrement reçu", status=200)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8080)
