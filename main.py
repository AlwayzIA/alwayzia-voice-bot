from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse

app = Flask(__name__)

@app.route("/voice", methods=['POST'])
def voice():
    """Gère les appels entrants de Twilio"""
    # Crée une réponse vocale
    response = VoiceResponse()
    response.say("Bonjour et bienvenue chez votre hôtel. Merci de patienter, un agent va vous assister.", language="fr-FR", voice="alice")

    return Response(str(response), mimetype="text/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
