import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# 🔁 Chargement des variables d'environnement
load_dotenv()

# ⚙️ Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🚀 Initialisation de l'app Flask
app = Flask(__name__)

# 📌 Route de test GET
@app.route("/", methods=["GET"])
def index():
    return "✅ Neo Voice Agent est en ligne !"

# 📞 Route principale POST (à adapter selon ton besoin)
@app.route("/voice", methods=["POST"])
def voice_handler():
    logger.info("📞 Requête reçue sur /voice")
    data = request.json or {}
    return jsonify({
        "message": "Réponse de l’agent vocal Neo.",
        "data_reçue": data
    })

# ✅ Lancement local uniquement
if __name__ == "__main__":
    logger.info("🚀 Démarrage local de Neo Voice Agent")
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
