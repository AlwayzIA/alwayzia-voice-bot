import os
import time
import requests
import logging
import uuid
import json
from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
import openai
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# Configuration de base
logging.basicConfig(level=logging.INFO)
load_dotenv()

# Clés API et variables d'environnement
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
PORT = int(os.getenv("PORT", 8080))

# Initialisation des clients externes
deepgram = DeepgramClient(DEEPGRAM_API_KEY)

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
        logging.error(f"❌ Erreur Google Sheets: {str(e)}")
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
            "transcription": "Deepgram",
            "ai": "OpenAI GPT-4",
            "voice": "ElevenLabs",
            "telephony": "Twilio"
        },
        "endpoints": [
            "/voice - Webhook Twilio pour appels entrants",
            "/process_recording - Traitement des enregistrements",
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
            "deepgram": bool(DEEPGRAM_API_KEY)
        }
    })

@app.route("/voice", methods=["POST"])
def voice():
    """Webhook principal pour recevoir les appels Twilio"""
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
        
        # Création de la réponse TwiML
        response = VoiceResponse()
        
        # Message d'accueil dynamique selon la config de l'hôtel
        import datetime
        current_hour = datetime.datetime.now().hour
        
        if 6 <= current_hour <= 17:
            welcome_message = f"Bonjour et bienvenue au {hotel_config['nom_hotel']}. {hotel_config['voix_prenom']} à votre service, que puis-je faire pour vous aujourd'hui ?"
        else:
            welcome_message = f"Bonsoir et bienvenue au {hotel_config['nom_hotel']}. {hotel_config['voix_prenom']} à votre service, que puis-je faire pour vous ce soir ?"
        
        # Message d'accueil avec Twilio TTS
        response.say(welcome_message, language="fr-FR", voice="Polly.Celine")
        
        # Enregistrement du message
        response.record(
            max_length=60,  # 1 minute max
            finish_on_key="#",
            play_beep=True,
            timeout=5,
            transcribe=False,
            action="/process_recording",
            method="POST"
        )
        
        # Message de fallback si pas d'enregistrement
        fallback_msg = "Je n'ai pas reçu votre message. Merci de rappeler ou d'appuyer sur dièse pour terminer votre appel."
        response.say(fallback_msg, language="fr-FR", voice="Polly.Celine")
        
        logging.info("✅ Réponse TwiML générée - Neo")
        return str(response)
        
    except Exception as e:
        logging.error(f"🚨 ERREUR dans voice webhook: {str(e)}")
        response = VoiceResponse()
        response.say(
            "Désolé, une erreur technique s'est produite. Veuillez rappeler plus tard.",
            language="fr-FR",
            voice="Polly.Celine"
        )
        return str(response)

@app.route("/process_recording", methods=["POST"])
def process_recording():
    """Récupère l'enregistrement, le transcrit avec Deepgram, puis le traite avec OpenAI"""
    try:
        logging.info("🔔 Neo traite l'enregistrement en cours...")
        
        # Récupération de l'URL d'enregistrement
        recording_url = request.form.get("RecordingUrl")
        recording_sid = request.form.get("RecordingSid", "SID inconnu")
        call_sid = request.form.get("CallSid", "SID inconnu")
        caller_number = request.form.get("From", "Numéro inconnu")
        called_number = request.form.get("To", "Numéro inconnu")
        
        logging.info(f"🎧 URL d'enregistrement: {recording_url}")
        logging.info(f"🆔 Recording SID: {recording_sid}")
        logging.info(f"📞 Appelant: {caller_number}")
        
        if not recording_url:
            logging.error("❌ Aucune URL d'enregistrement fournie")
            response = VoiceResponse()
            response.say(
                "Désolé, je n'ai pas pu récupérer votre enregistrement.",
                language="fr-FR",
                voice="Polly.Celine"
            )
            return str(response)
        
        # Récupération de la configuration de l'hôtel
        hotel_config = get_hotel_config(called_number)
        logging.info(f"🏨 Traitement pour: {hotel_config['nom_hotel']}")
        
        # Construction de l'URL correcte pour télécharger l'audio
        # Twilio donne l'URL de métadonnées, il faut construire l'URL du fichier WAV
        if recording_url.endswith('.json'):
            # Si l'URL se termine par .json, remplacer par .wav
            wav_url = recording_url.replace('.json', '.wav')
        else:
            # Sinon, ajouter .wav à la fin
            wav_url = f"{recording_url}.wav"
        
        logging.info(f"🎯 URL audio à transcrire: {wav_url}")
        
        # Transcription avec Deepgram (avec téléchargement et auth Twilio)
        logging.info("🎤 Neo transcrit avec Deepgram...")
        transcript = transcribe_with_deepgram(wav_url)
        
        if not transcript:
            logging.error("❌ Échec de la transcription")
            response = VoiceResponse()
            response.say(
                "Désolé, je n'ai pas pu comprendre votre message. Pouvez-vous rappeler ?",
                language="fr-FR",
                voice="Polly.Celine"
            )
            return str(response)
        
        logging.info(f"📝 Transcription Neo: {transcript}")
        
        # Génération de réponse avec GPT-4
        logging.info("🤖 Neo génère une réponse avec GPT-4...")
        ai_response = generate_gpt4_response(transcript, caller_number, hotel_config)
        
        logging.info(f"💭 Réponse Neo: {ai_response}")
        
        # Création de la réponse TwiML
        response = VoiceResponse()
        response.say(ai_response, language="fr-FR", voice="Polly.Celine")
        
        # Message de fin personnalisé selon l'hôtel
        end_message = f"Merci infiniment pour votre appel. Toute l'équipe du {hotel_config['nom_hotel']} reste à votre disposition. Très belle journée à vous !"
        response.say(end_message, language="fr-FR", voice="Polly.Celine")
        
        logging.info("✅ Neo a terminé le traitement avec succès")
        return str(response)
        
    except Exception as e:
        logging.error(f"🚨 ERREUR dans process_recording Neo: {str(e)}")
        response = VoiceResponse()
        response.say(
            "Désolé, une erreur s'est produite lors du traitement de votre message.",
            language="fr-FR",
            voice="Polly.Celine"
        )
        return str(response)

def transcribe_with_deepgram(wav_url):
    """Transcrit l'audio avec Deepgram depuis une URL avec authentification Twilio"""
    try:
        # Attendre quelques secondes que l'enregistrement soit disponible
        import time
        time.sleep(3)
        
        # Téléchargement du fichier audio avec authentification Twilio
        logging.info(f"🔗 Téléchargement depuis: {wav_url}")
        
        response = requests.get(
            wav_url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=30
        )
        
        logging.info(f"📡 Status téléchargement: {response.status_code}")
        
        if response.status_code != 200:
            logging.error(f"❌ Erreur téléchargement: {response.status_code}")
            logging.error(f"❌ Contenu réponse: {response.text[:200]}")
            return None
        
        audio_data = response.content
        logging.info(f"✅ Audio téléchargé: {len(audio_data)} bytes")
        
        # Vérification que nous avons bien des données audio
        if len(audio_data) < 1000:  # Fichier audio trop petit
            logging.error(f"❌ Fichier audio trop petit: {len(audio_data)} bytes")
            return None
        
        # Configuration pour la transcription en français avec format Twilio
        options = PrerecordedOptions(
            model="nova-2",
            language="fr",
            smart_format=True,
            punctuate=True,
            paragraphs=True,
            utterances=True,
            encoding="mulaw",  # Important: Twilio utilise mulaw
            sample_rate=8000   # Important: Twilio utilise 8000Hz
        )
        
        # Transcription avec les données audio téléchargées (format mulaw)
        source: FileSource = {"buffer": audio_data, "mimetype": "audio/mulaw"}
        
        response = deepgram.listen.prerecorded.v("1").transcribe_file(source, options)
        
        # Extraction du texte
        transcript = response["results"]["channels"][0]["alternatives"][0]["transcript"]
        
        if transcript and transcript.strip():
            logging.info(f"✅ Transcription réussie: {transcript}")
            return transcript.strip()
        else:
            logging.warning("⚠️ Transcription vide")
            return None
            
    except Exception as e:
        logging.error(f"❌ Erreur Deepgram: {str(e)}")
        return None

def generate_gpt4_response(transcript, caller_number="", hotel_config=None):
    """Génère une réponse intelligente avec GPT-4 selon la config de l'hôtel"""
    try:
        if not hotel_config:
            hotel_config = get_default_hotel_config()
        
        # Vérification de la clé OpenAI
        if not OPENAI_API_KEY:
            logging.warning("⚠️ OpenAI API key manquante, utilisation de réponse par défaut")
            return f"Merci pour votre message. Notre équipe du {hotel_config['nom_hotel']} a bien pris note de votre demande et vous rappellera dans les plus brefs délais."
        
        # Construction du prompt système personnalisé pour cet hôtel
        services_list = ", ".join(hotel_config.get('services', []))
        chambres_list = ", ".join(hotel_config.get('chambres_types', []))
        
        system_prompt = f"""Tu es un assistant téléphonique intelligent pour le {hotel_config['nom_hotel']} en {hotel_config['pays']}.

INFORMATIONS DE L'ÉTABLISSEMENT :
- Nom : {hotel_config['nom_hotel']}
- Horaires réception : {hotel_config['horaires_reception']}
- Check-in : {hotel_config['check_in']}
- Check-out : {hotel_config['check_out']}
- Petit-déjeuner : {hotel_config['petit_dejeuner']}
- Services disponibles : {services_list}
- Types de chambres : {chambres_list}
- Ton à adopter : {hotel_config['ton_vocal']}
- Voix IA : {hotel_config['voix_prenom']}

RÈGLES CRITIQUES :
- Tu ne communiques QUE les informations listées ci-dessus
- Tu ne confirmes JAMAIS une réservation
- Tu collectes : nom, prénom, téléphone, email, demande, moyen de recontact
- Tu vouvoies TOUJOURS le client
- Ton {hotel_config['ton_vocal']} et professionnel

GESTION DES INFORMATIONS MANQUANTES :
Si une information n'est pas disponible :
"Je suis désolé, je n'ai malheureusement pas cette information. Souhaitez-vous que je transmette votre demande à la réception afin qu'un membre de l'équipe vous rappelle ou vous contacte par email avec la réponse exacte ?"

STYLE :
- Réponses concises (2-3 phrases max)
- Patience et bienveillance
- Représente l'excellence du {hotel_config['nom_hotel']}

Tu travailles pour le {hotel_config['nom_hotel']} et tu incarnes leurs valeurs."""
        
        # Appel à l'API OpenAI GPT-4 (ancienne syntaxe)
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Message de l'appelant : {transcript}"}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        if ai_response:
            return ai_response
        else:
            return f"Merci pour votre message. Notre équipe du {hotel_config['nom_hotel']} a bien pris note de votre demande et vous rappellera dans les plus brefs délais."
            
    except Exception as e:
        logging.error(f"❌ Erreur GPT-4: {str(e)}")
        hotel_name = hotel_config['nom_hotel'] if hotel_config else "notre établissement"
        return f"Merci pour votre appel. L'équipe de {hotel_name} a bien reçu votre message et vous rappellera dans les plus brefs délais."

def generate_elevenlabs_audio(text, hotel_config=None):
    """Génère l'audio avec ElevenLabs selon la config de l'hôtel"""
    try:
        if not hotel_config:
            hotel_config = get_default_hotel_config()
        
        # Mapping des voix selon la configuration de l'hôtel
        voice_mapping = {
            ('français', 'femme'): 'g5CIjZEefAph4nQFvHAz',  # Alice - Élise
            ('français', 'homme'): 'flq6f7yk4E4fJM5XTYuZ',  # Antoine - Nolan  
            ('anglais', 'femme'): '21m00Tcm4TlvDq8ikWAM',   # Rachel - Lauren
            ('anglais', 'homme'): 'VR6AewLTigWG4xSOukaG',   # Arnold - Ethan
        }
        
        # Sélection de la voix selon la config de l'hôtel
        langue = hotel_config.get('langue_principale', 'français').lower()
        genre = hotel_config.get('voix_genre', 'femme').lower()
        voice_id = voice_mapping.get((langue, genre), 'g5CIjZEefAph4nQFvHAz')
        
        logging.info(f"🎤 Voix sélectionnée: {langue}/{genre} pour {hotel_config['voix_prenom']}")
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        data = {
            "text": text,
            "model_id": "eleven_flash_v2_5",  # Modèle multilingue 32 langues
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.5,
                "use_speaker_boost": True
            }
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Sauvegarde temporaire du fichier audio
            filename = f"/tmp/{hotel_config['voix_prenom'].lower()}_audio_{uuid.uuid4()}.mp3"
            with open(filename, "wb") as f:
                f.write(response.content)
            
            logging.info(f"✅ Audio {hotel_config['voix_prenom']} (Neo) ElevenLabs généré: {filename}")
            
            # TODO: Upload vers un service de stockage public pour retourner l'URL
            # Pour l'instant, retourne None pour utiliser le fallback Twilio
            return None
            
        else:
            logging.error(f"❌ Erreur ElevenLabs: {response.status_code}")
            return None
            
    except Exception as e:
        logging.error(f"❌ Erreur dans generate_elevenlabs_audio: {str(e)}")
        return None

@app.route("/test", methods=["GET"])
def test():
    """Endpoint de test pour vérifier la configuration"""
    config_status = {
        "twilio_sid": "✅ Configuré" if TWILIO_ACCOUNT_SID else "❌ Manquant",
        "twilio_token": "✅ Configuré" if TWILIO_AUTH_TOKEN else "❌ Manquant", 
        "openai_key": "✅ Configuré" if OPENAI_API_KEY else "❌ Manquant",
        "elevenlabs_key": "✅ Configuré" if ELEVENLABS_API_KEY else "❌ Manquant",
        "deepgram_key": "✅ Configuré" if DEEPGRAM_API_KEY else "❌ Manquant"
    }
    
    # Test rapide des APIs
    test_results = {}
    
    # Test Deepgram
    try:
        if DEEPGRAM_API_KEY:
            test_deepgram = DeepgramClient(DEEPGRAM_API_KEY)
            test_results["deepgram"] = "✅ Connexion OK"
        else:
            test_results["deepgram"] = "❌ Clé manquante"
    except:
        test_results["deepgram"] = "⚠️ Erreur de connexion"
    
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
        "ready_for_calls": all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, OPENAI_API_KEY, DEEPGRAM_API_KEY])
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
            "error": str(e),
            "status": "❌ Test échoué"
        })

# Point d'entrée principal
if __name__ == "__main__":
    logging.info("🚀 Démarrage de Neo - Agent IA Téléphonique AlwayzIA v2.0")
    logging.info("🤖 Neo (Élise) est maintenant en ligne pour l'Hôtel Beau-Rivage")
    logging.info("🏢 Société: AlwayzIA")
    logging.info("📋 Prompt: v1.2 (06.06.2025) - Maxime Maadoune Meloni")
    logging.info("🧠 GPT-4 pour l'intelligence artificielle")
    logging.info("🎤 Deepgram pour la transcription")
    logging.info("🔊 ElevenLabs Flash v2.5 pour la synthèse vocale")
    logging.info("📞 Twilio pour la téléphonie")
    logging.info("📡 Neo est prêt à recevoir les appels pour l'Hôtel Beau-Rivage...")
    
    # Configuration du port pour développement local uniquement
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
