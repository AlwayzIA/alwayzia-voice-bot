from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
import openai
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Charger le prompt système
try:
    with open("neo_prompt.txt", "r", encoding="utf-8") as f:
        neo_prompt = f.read()
except FileNotFoundError:
    neo_prompt = "Vous êtes un assistant vocal intelligent et serviable."
    print("Fichier neo_prompt.txt non trouvé, utilisation d'un prompt par défaut")

# Créer l'application Flask
app = Flask(__name__)

@app.route("/voice", methods=["POST"])
def voice():
    """Gère les appels entrants via Twilio avec OpenAI"""
    user_input = "Bonjour"
    
    try:
        client = openai.OpenAI(api_key=openai.api_key)
        response_ai = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": neo_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=150,
            temperature=0.7
        )
        text = response_ai.choices[0].message.content
        print(f"[INFO] Réponse IA générée : {text}")
        
    except Exception as e:
        print(f"[ERREUR GPT] Error code: {e}")
        text = "Désolé, une erreur est survenue dans notre système d'assistance."
    
    # Créer la réponse TwiML
    response = VoiceResponse()
    response.say(text, language="fr-FR", voice="alice")
    
    print(f"[INFO] TwiML généré : {str(response)}")
    return Response(str(response), mimetype="text/xml")

@app.route("/", methods=["GET"])
def health_check():
    """Route de vérification de santé"""
    return "Neo Voice Agent is running!"

if __name__ == "__main__":
    print("Démarrage du serveur Neo Voice Agent...")
    print(f"OpenAI API Key configurée : {'Oui' if openai.api_key else 'Non'}")
    app.run(host="0.0.0.0", port=8080, debug=False)
