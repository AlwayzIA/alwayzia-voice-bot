import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
import requests

# Chargement des variables d’environnement
load_dotenv()

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de Flask
app = Flask(__name__)

# Configuration de l’API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Chargement du prompt depuis le fichier
with open("neo_prompt.txt", "r", encoding="utf-8") as file:
    SYSTEM_PROMPT = file.read()

@app.route("/", methods=["GET"])
def home():
    return "Neo Voice Agent est opérationnel."

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        logger.info(f"📩 Données reçues : {data}")

        # Vérification du champ "transcript"
        transcript = data.get("transcript", "").strip()
        if not transcript:
            logger.warning("❗ Aucun transcript fourni.")
            return jsonify({"error": "Le champ 'transcript' est requis."}), 400

        # Appel à l’API OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript}
            ],
            temperature=0.6,
            max_tokens=500
        )

        reply = response.choices[0].message["content"]
        logger.info(f"🧠 Réponse générée : {reply}")

        return jsonify({"reply": reply})

    except Exception as e:
        logger.error(f"💥 Erreur serveur : {e}")
        return jsonify({"error": str(e)}), 500
