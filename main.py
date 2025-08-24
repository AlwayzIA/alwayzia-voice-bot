import os
import time
import requests
import logging
import uuid
import json
from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse
import openai
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
import tempfile

# Configuration de base
logging.basicConfig(level=logging.INFO)
load_dotenv()

# Clés API et variables d'environnement
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
PORT = int(os.getenv("PORT", 8080))

# Initialisation des clients externes
# Configuration OpenAI (ancienne syntaxe stable)
openai.api_key = OPENAI_API_KEY

# Initialisation de Flask
app = Flask(__name__)

def get_hotel_config(twilio_number):
    """Récupère la configuration de l'hôtel depuis Google Sheets selon le numéro Twilio appelé"""
    try:
        if not GOOGLE_CREDENTIALS_JSON:
            logging.warning("⚠️ Google Credentials manquantes, utilisation config par défaut")
            return get_default_hotel_config()
        
        # Connexion à Google Sheets
        credentials_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        credentials = Credentials.from_service_account_info(credentials_dict)
        gc = gspread.authorize(credentials)
        
        # Ouverture du tableur principal
        sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1
        
        # Recherche de l'hôtel par numéro Twilio
        records = sheet.get_all_records()
        
        for record in records:
            if record.get('numero_twilio') == twilio_number:
                logging.info(f"✅ Configuration trouvée pour {record.get('nom_hotel', 'Hôtel')}")
                return record
        
        logging.warning(f"⚠️ Aucune config trouvée pour {twilio_number}, utilisation par défaut")
        return get_default_hotel_config()
        
    except Exception as e:
        logging.error("❌ Erreur Google Sheets, utilisation config par défaut")
        return get_default_hotel_config()

def get_default_hotel_config():
    """Configuration par défaut pour les tests (Hôtel Beau-Rivage)"""
    return {
        'nom_hotel': 'Hôtel Beau-Rivage',
        'pays': 'Suisse',
        'langue_principale': 'français',
        'formule': 'Pro',
        'voix_genre': 'femme',
        'voix_prenom': 'Élise',
        'ton_vocal': 'formel',
        'horaires_reception': '08h00 à 18h00',
        'check_in': '14h00',
        'check_out': '12h00',
        'petit_dejeuner': '07h30 à 10h30',
        'transfert_humain': True,
        'email_contact': 'alwayzia.ops@gmail.com',
        'numero_twilio': '+41 21 539 18 06',
        'services': ['WiFi gratuit', 'Parking', 'Vue lac'],
        'chambres_types': ['Standard', 'Supérieure', 'Suite'],
        'recommandations_locales': True
    }

@app.route("/", methods=["GET"])
def home():
    """Page d'accueil pour vérifier que l'API fonctionne"""
    return jsonify({
        "status": "✅ Neo - Agent IA Téléphonique AlwayzIA - En ligne",
        "version": "2.0.0",
        "agent": "Neo",
        "company": "AlwayzIA",
        "services": {
            "transcription": "AssemblyAI + Whisper",
            "ai": "OpenAI GPT-4",
            "voice": "ElevenLabs + Twilio",
            "telephony": "Twilio"
        },
        "endpoints": [
            "/voice - Webhook Twilio pour appels entrants",
            "/conversation - Gestion conversation interactive",
            "/status - Statut de l'API",
            "/test - Test de configuration"
        ]
    })

@app.route("/status", methods=["GET"])
def status():
    """Endpoint de statut pour le monitoring"""
    return jsonify({
        "status": "healthy",
        "agent": "Neo",
        "company": "AlwayzIA",
        "service": "Agent IA Téléphonique",
        "timestamp": str(uuid.uuid4()),
        "apis_configured": {
            "twilio": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN),
            "openai": bool(OPENAI_API_KEY),
            "elevenlabs": bool(ELEVENLABS_API_KEY),
            "assemblyai": bool(ASSEMBLYAI_API_KEY)
        }
    })

@app.route("/voice", methods=["POST"])
def voice():
    """Webhook principal pour recevoir les appels Twilio - CONVERSATION INTERACTIVE"""
    try:
        logging.info("📞 Nouvel appel reçu sur le webhook Neo")
        
        # Récupération des informations de l'appel
        caller_number = request.form.get("From", "Numéro inconnu")
        called_number = request.form.get("To", "Numéro inconnu")
        call_sid = request.form.get("CallSid", "SID inconnu")
        
        logging.info(f"🔢 De: {caller_number} | Vers: {called_number}")
        logging.info(f"🆔 Call SID: {call_sid}")
        
        # Récupération de la configuration de l'hôtel
        hotel_config = get_hotel_config(called_number)
        
        logging.info(f"🏨 Hôtel détecté: {hotel_config['nom_hotel']}")
        logging.info(f"🎭 Voix: {hotel_config['voix_prenom']} ({hotel_config['voix_genre']})")
        
        # Création de la réponse TwiML pour CONVERSATION
        response = VoiceResponse()
        
        # Message d'accueil dynamique selon la config de l'hôtel
        import datetime
        current_hour = datetime.datetime.now().hour
        
        if 6 <= current_hour <= 17:
            welcome_message = f"Bonjour et bienvenue au {hotel_config['nom_hotel']}. {hotel_config['voix_prenom']} à votre service, comment puis-je vous aider aujourd'hui ?"
        else:
            welcome_message = f"Bonsoir et bienvenue au {hotel_config['nom_hotel']}. {hotel_config['voix_prenom']} à votre service, comment puis-je vous aider ce soir ?"
        
        # CONVERSATION INTERACTIVE avec Gather (SANS BIP !)
        gather = response.gather(
            input="speech",
            language="fr-FR",
            speech_timeout="auto",
            timeout=10,
            action="/conversation",
            method="POST"
        )
        
        # Message d'accueil dans le Gather avec meilleure voix
        gather.say(welcome_message, language="fr-FR", voice="Polly.Lea-Neural")
        
        # Si pas de réponse après timeout
        response.say("Je n'ai pas bien entendu. Pouvez-vous répéter s'il vous plaît ?", language="fr-FR", voice="Polly.Lea-Neural")
        
        # Donner une autre chance SANS se re-présenter
        gather_retry = response.gather(
            input="speech",
            language="fr-FR",
            speech_timeout="auto",
            timeout=15,
            action="/conversation",
            method="POST"
        )
        
        # Si toujours pas de réponse, terminer poliment
        response.say("Je vous remercie pour votre appel. N'hésitez pas à nous rappeler. Au revoir !", language="fr-FR", voice="Polly.Lea-Neural")
        
        logging.info("✅ Réponse TwiML CONVERSATION générée - Neo")
        return str(response)
        
    except Exception as e:
        logging.error("🚨 ERREUR dans voice webhook")
        response = VoiceResponse()
        response.say(
            "Désolé, une erreur technique s'est produite. Veuillez rappeler plus tard.",
            language="fr-FR",
            voice="Polly.Lea-Neural"
        )
        return str(response)

@app.route("/conversation", methods=["POST"])
def conversation():
    """Gère la conversation interactive avec le client"""
    try:
        # Récupération de ce que le client a dit
        speech_result = request.form.get("SpeechResult", "")
        confidence = request.form.get("Confidence", "0")
        caller_number = request.form.get("From", "Numéro inconnu")
        called_number = request.form.get("To", "")
        
        logging.info(f"🎤 Client a dit: '{speech_result}' (confiance: {confidence})")
        
        # Récupération de la configuration de l'hôtel
        hotel_config = get_hotel_config(called_number)
        
        response = VoiceResponse()
        
        if speech_result and len(speech_result.strip()) > 2:
            # Génération de réponse avec GPT-4
            logging.info("🤖 Neo génère une réponse avec GPT-4...")
            ai_response = generate_gpt4_response(speech_result, caller_number, hotel_config)
            
            logging.info(f"💭 Réponse Neo: {ai_response}")
            
            # Déterminer le timeout selon le contexte de la réponse
            if any(word in ai_response.lower() for word in ["nom", "prénom", "téléphone", "email", "coordonnées", "rappel"]):
                # Si Neo demande des coordonnées, laisser plus de temps (30s)
                timeout_duration = 30
                logging.info("⏰ Timeout étendu (30s) pour collecter les coordonnées")
            else:
                # Conversation normale (15s)
                timeout_duration = 15
            
            # CONTINUER LA CONVERSATION avec timeout adaptatif
            gather = response.gather(
                input="speech",
                language="fr-FR", 
                speech_timeout="auto",
                timeout=timeout_duration,  # Timeout adaptatif !
                action="/conversation",
                method="POST"
            )
            
            # Répondre ET continuer à écouter avec meilleure voix
            gather.say(ai_response, language="fr-FR", voice="Polly.Lea-Neural")
            
            # Ne pas ajouter de question supplémentaire si Neo demande déjà des infos
            if not any(word in ai_response.lower() for word in ["nom", "prénom", "téléphone", "email", "coordonnées"]):
                gather.say("Y a-t-il autre chose que je puisse faire pour vous ?", language="fr-FR", voice="Polly.Lea-Neural")
            
            # Si pas de réponse après le timeout
            response.say("Merci infiniment pour votre appel. Très belle journée à vous !", language="fr-FR", voice="Polly.Lea-Neural")
            
        else:
            # Pas compris, redemander SANS se re-présenter
            gather = response.gather(
                input="speech",
                language="fr-FR",
                speech_timeout="auto", 
                timeout=15,
                action="/conversation",
                method="POST"
            )
            
            gather.say("Je n'ai pas bien saisi votre demande. Pouvez-vous reformuler s'il vous plaît ?", language="fr-FR", voice="Polly.Lea-Neural")
            
            # Si toujours pas compris, terminer poliment
            response.say("Je vous remercie pour votre appel. Au revoir !", language="fr-FR", voice="Polly.Lea-Neural")
        
        return str(response)
        
    except Exception as e:
        logging.error("❌ Erreur conversation")
        response = VoiceResponse()
        response.say("Désolé, j'ai un problème technique. Au revoir !", language="fr-FR", voice="Polly.Lea-Neural")
        return str(response)

def generate_gpt4_response(transcript, caller_number="", hotel_config=None):
    """Génère une réponse intelligente avec GPT-4 selon la config de l'hôtel"""
    try:
        if not hotel_config:
            hotel_config = get_default_hotel_config()
        
        # Construction du prompt système personnalisé pour cet hôtel
        services_list = ", ".join(hotel_config.get('services', []))
        chambres_list = ", ".join(hotel_config.get('chambres_types', []))
        
        system_prompt = f"""Tu es un assistant téléphonique intelligent pour le {hotel_config['nom_hotel']} en {hotel_config['pays']}.

Tu t'es DÉJÀ présenté au début de l'appel comme {hotel_config['voix_prenom']}. 
NE TE PRÉSENTE PLUS JAMAIS - la conversation a déjà commencé.

INFORMATIONS DE L'ÉTABLISSEMENT :
- Nom : {hotel_config['nom_hotel']}
- Horaires réception : {hotel_config['horaires_reception']}
- Check-in : {hotel_config['check_in']}
- Check-out : {hotel_config['check_out']}
- Petit-déjeuner : {hotel_config['petit_dejeuner']}
- Services disponibles : {services_list}
- Types de chambres : {chambres_list}
- Ton à adopter : {hotel_config['ton_vocal']}

RÈGLES CRITIQUES :
- Tu ne communiques QUE les informations listées ci-dessus
- Tu ne confirmes JAMAIS une réservation
- Tu collectes : nom, prénom, téléphone, email, demande, moyen de recontact
- Tu vouvoies TOUJOURS le client
- Ton {hotel_config['ton_vocal']} et professionnel
- NE TE PRÉSENTE PLUS - c'est déjà fait !

GESTION DES INFORMATIONS MANQUANTES :
Si une information n'est pas disponible :
"Je suis désolé, je n'ai malheureusement pas cette information. Souhaitez-vous que je transmette votre demande à la réception afin qu'un membre de l'équipe vous rappelle ou vous contacte par email avec la réponse exacte ?"

STYLE :
- Réponses concises (2-3 phrases max)
- Patience et bienveillance
- Représente l'excellence du {hotel_config['nom_hotel']}
- Conversation naturelle SANS répéter l'accueil

Tu es EN COURS de conversation avec le client."""
        
        # Appel à l'API OpenAI GPT-4 avec optimisations latence
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Message de l'appelant : {transcript}"}
            ],
            max_tokens=100,  # Réduit pour des réponses plus rapides
            temperature=0.5,  # Réduit pour plus de consistance et rapidité
            stream=False
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        if ai_response:
            return ai_response
        else:
            return f"Merci pour votre message. Notre équipe du {hotel_config['nom_hotel']} a bien pris note de votre demande et vous rappellera dans les plus brefs délais."
            
    except Exception as e:
        logging.error("❌ Erreur GPT-4")
        hotel_name = hotel_config['nom_hotel'] if hotel_config else "notre établissement"
        return f"Merci pour votre appel. L'équipe de {hotel_name} a bien reçu votre message et vous rappellera dans les plus brefs délais."

def transcribe_with_whisper(wav_url):
    """Fallback avec OpenAI Whisper"""
    try:
        logging.info("🔄 Tentative avec OpenAI Whisper...")
        
        # Télécharger l'audio depuis Twilio
        audio_response = requests.get(
            wav_url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=30
        )
        
        if audio_response.status_code != 200:
            logging.error("❌ Erreur téléchargement pour Whisper")
            return None
        
        audio_data = audio_response.content
        logging.info(f"✅ Audio téléchargé pour Whisper: {len(audio_data)} bytes")
        
        # Sauvegarder temporairement
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        # Transcription avec OpenAI Whisper
        with open(temp_path, "rb") as audio_file:
            transcript_response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language="fr",
                prompt="Transcription d'un appel téléphonique en français pour un hôtel"
            )
        
        # Nettoyage
        os.unlink(temp_path)
        
        transcript = transcript_response.get("text", "").strip()
        if transcript:
            logging.info(f"✅ Transcription Whisper réussie: {transcript}")
            return transcript
        else:
            logging.warning("⚠️ Transcription Whisper vide")
            return None
            
    except Exception as e:
        logging.error("❌ Erreur Whisper")
        return None

@app.route("/test", methods=["GET"])
def test():
    """Endpoint de test pour vérifier la configuration"""
    config_status = {
        "twilio_sid": "✅ Configuré" if TWILIO_ACCOUNT_SID else "❌ Manquant",
        "twilio_token": "✅ Configuré" if TWILIO_AUTH_TOKEN else "❌ Manquant", 
        "openai_key": "✅ Configuré" if OPENAI_API_KEY else "❌ Manquant",
        "elevenlabs_key": "✅ Configuré" if ELEVENLABS_API_KEY else "❌ Manquant",
        "assemblyai_key": "✅ Configuré" if ASSEMBLYAI_API_KEY else "❌ Manquant"
    }
    
    # Test rapide des APIs
    test_results = {}
    
    # Test AssemblyAI
    try:
        if ASSEMBLYAI_API_KEY:
            test_response = requests.get(
                "https://api.assemblyai.com/v2/transcript",
                headers={"authorization": ASSEMBLYAI_API_KEY},
                timeout=10
            )
            if test_response.status_code in [200, 401]:
                test_results["assemblyai"] = "✅ Connexion OK"
            else:
                test_results["assemblyai"] = "⚠️ Erreur de connexion"
        else:
            test_results["assemblyai"] = "❌ Clé manquante"
    except:
        test_results["assemblyai"] = "⚠️ Erreur de connexion"
    
    # Test OpenAI
    try:
        if OPENAI_API_KEY:
            test_results["openai"] = "✅ Clé valide"
        else:
            test_results["openai"] = "❌ Clé manquante"
    except:
        test_results["openai"] = "⚠️ Erreur de connexion"
    
    return jsonify({
        "agent": "Neo",
        "company": "AlwayzIA",
        "service": "Agent IA Téléphonique",
        "status": "Test endpoint",
        "configuration": config_status,
        "connectivity_tests": test_results,
        "webhook_url": f"{request.host_url}voice",
        "ready_for_calls": all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, OPENAI_API_KEY])
    })

@app.route("/demo", methods=["POST"])
def demo():
    """Endpoint de démonstration pour tester Neo sans appel téléphonique"""
    try:
        data = request.get_json()
        test_message = data.get("message", "Bonjour, je voudrais faire une réservation pour ce soir.")
        
        # Test de la chaîne complète (sans audio)
        hotel_config = get_default_hotel_config()
        response_text = generate_gpt4_response(test_message, "", hotel_config)
        
        return jsonify({
            "agent": "Neo",
            "company": "AlwayzIA",
            "hotel": hotel_config['nom_hotel'],
            "input": test_message,
            "neo_response": response_text,
            "status": "✅ Test réussi"
        })
        
    except Exception as e:
        return jsonify({
            "agent": "Neo",
            "company": "AlwayzIA", 
            "status": "❌ Test échoué"
        })

# Point d'entrée principal
if __name__ == "__main__":
    logging.info("🚀 Démarrage de Neo - Agent IA Téléphonique AlwayzIA v2.0")
    logging.info("🤖 Neo (Élise) est maintenant en ligne pour l'Hôtel Beau-Rivage")
    logging.info("🏢 Société: AlwayzIA")
    logging.info("📋 Prompt: v1.2 (06.06.2025) - Maxime Maadoune Meloni")
    logging.info("🧠 GPT-4 pour l'intelligence artificielle")
    logging.info("🎤 AssemblyAI + Whisper pour la transcription")
    logging.info("🔊 ElevenLabs + Twilio Neural pour la synthèse vocale")
    logging.info("📞 Twilio pour la téléphonie")
    logging.info("📡 Neo est prêt à recevoir les appels pour l'Hôtel Beau-Rivage...")
    
    # Configuration du port pour développement local uniquement
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
