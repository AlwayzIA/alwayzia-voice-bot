from flask import Flask, request, jsonify
from twilio.twiml import VoiceResponse
import requests
import os
import uuid
import json
import gspread
from google.oauth2.service_account import Credentials

# Initialisation de l'application Flask
app = Flask(__name__)

# Configuration des variables d'environnement
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
import openai
from deepgram import DeepgramClient, PrerecordedOptions

# Configuration Google Sheets
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")  # Service Account JSON
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")  # ID du tableur principal

# Configuration OpenAI
openai.api_key = OPENAI_API_KEY

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

def get_hotel_config(twilio_number):
    """Récupère la configuration de l'hôtel depuis Google Sheets selon le numéro Twilio appelé"""
    try:
        if not GOOGLE_CREDENTIALS_JSON:
            print("⚠️ Google Credentials manquantes, utilisation config par défaut")
            return get_default_hotel_config()
        
        # Connexion à Google Sheets
        import json
        credentials_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        credentials = Credentials.from_service_account_info(credentials_dict)
        gc = gspread.authorize(credentials)
        
        # Ouverture du tableur principal
        sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1
        
        # Recherche de l'hôtel par numéro Twilio
        records = sheet.get_all_records()
        
        for record in records:
            if record.get('numero_twilio') == twilio_number:
                print(f"✅ Configuration trouvée pour {record.get('nom_hotel', 'Hôtel')}")
                return record
        
        print(f"⚠️ Aucune config trouvée pour {twilio_number}, utilisation par défaut")
        return get_default_hotel_config()
        
    except Exception as e:
        print(f"❌ Erreur Google Sheets: {str(e)}")
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
            "/webhook - Webhook Twilio pour appels entrants",
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

@app.route("/webhook", methods=["POST"])
def webhook():
    """Webhook principal pour recevoir les appels Twilio"""
    try:
        print("📞 Nouvel appel reçu sur le webhook Neo")
        
        # Récupération des informations de l'appel
        caller_number = request.form.get("From", "Numéro inconnu")
        called_number = request.form.get("To", "Numéro inconnu")
        call_sid = request.form.get("CallSid", "SID inconnu")
        
        print(f"🔢 De: {caller_number} | Vers: {called_number}")
        print(f"🆔 Call SID: {call_sid}")
        
        # Création de la réponse TwiML
        response = VoiceResponse()
        
        # Récupération de la configuration de l'hôtel
        called_number = request.form.get("To", "")
        hotel_config = get_hotel_config(called_number)
        
        print(f"🏨 Hôtel détecté: {hotel_config['nom_hotel']}")
        print(f"🎭 Voix: {hotel_config['voix_prenom']} ({hotel_config['voix_genre']})")
        
        # Message d'accueil dynamique selon la config de l'hôtel
        import datetime
        current_hour = datetime.datetime.now().hour
        
        if 6 <= current_hour <= 17:
            welcome_message = f"Bonjour et bienvenue au {hotel_config['nom_hotel']}. {hotel_config['voix_prenom']} à votre service, que puis-je faire pour vous aujourd'hui ?"
        else:
            welcome_message = f"Bonsoir et bienvenue au {hotel_config['nom_hotel']}. {hotel_config['voix_prenom']} à votre service, que puis-je faire pour vous ce soir ?"
        
        # Génération de l'audio avec la voix configurée pour cet hôtel
        welcome_audio_url = generate_elevenlabs_audio(welcome_message, hotel_config)
        
        if welcome_audio_url:
            response.play(welcome_audio_url)
        else:
            # Fallback sur Twilio si ElevenLabs échoue
            response.say(welcome_message, language="fr-FR", voice="Polly.Celine")
        
        # Enregistrement du message
        response.record(
            action="/process_recording",
            method="POST",
            max_length=60,  # 1 minute max
            finish_on_key="#",
            play_beep=True,
            timeout=5,
            transcribe=False
        )
        
        # Fallback message selon les spécifications Neo
        fallback_msg = "Je n'ai pas reçu votre message. Merci de rappeler ou d'appuyer sur dièse pour terminer votre appel."
        fallback_audio = generate_elevenlabs_audio(fallback_msg)
        
        if fallback_audio:
            response.play(fallback_audio)
        else:
            response.say(fallback_msg, language="fr-FR", voice="Polly.Celine")
        
# Configuration Deepgram
deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        print("✅ Réponse TwiML générée avec ElevenLabs - Neo")
        return str(response)
        
    except Exception as e:
        print(f"🚨 ERREUR dans webhook Neo: {str(e)}")
        response = VoiceResponse()
        response.say(
            "Désolé, une erreur technique s'est produite. Veuillez rappeler plus tard.",
            language="fr-FR",
            voice="Polly.Celine"
        )
        return str(response)

@app.route("/process_recording", methods=["POST"])
def process_recording():
    """Traitement de l'enregistrement vocal avec Deepgram + GPT-4 + ElevenLabs"""
    try:
        print("🔔 Neo traite l'enregistrement en cours...")
        
        # Récupération de l'URL d'enregistrement
        recording_url = request.form.get("RecordingUrl")
        recording_sid = request.form.get("RecordingSid", "SID inconnu")
        call_sid = request.form.get("CallSid", "SID inconnu")
        caller_number = request.form.get("From", "Numéro inconnu")
        
        print(f"🎧 URL d'enregistrement: {recording_url}")
        print(f"🆔 Recording SID: {recording_sid}")
        print(f"📞 Appelant: {caller_number}")
        
        if not recording_url:
            print("❌ Aucune URL d'enregistrement fournie")
            response = VoiceResponse()
            error_msg = "Désolé, je n'ai pas pu récupérer votre enregistrement."
            error_audio = generate_elevenlabs_audio(error_msg)
            
            if error_audio:
                response.play(error_audio)
            else:
                response.say(error_msg, language="fr-FR", voice="Polly.Celine")
            return str(response)
        
        # Téléchargement de l'audio
        print("📥 Neo télécharge l'audio...")
        audio_content = download_twilio_recording(recording_url)
        
        if not audio_content:
            print("❌ Échec du téléchargement audio")
            response = VoiceResponse()
            response.say(
                "Erreur lors du téléchargement de votre message.",
                language="fr-FR",
                voice="Polly.Celine"
            )
            return str(response)
        
        # Transcription avec Deepgram
        print("🎤 Neo transcrit avec Deepgram...")
        transcript = transcribe_with_deepgram(audio_content)
        
        if not transcript:
            print("❌ Échec de la transcription")
            response = VoiceResponse()
            response.say(
                "Désolé, je n'ai pas pu comprendre votre message. Pouvez-vous rappeler ?",
                language="fr-FR",
                voice="Polly.Celine"
            )
            return str(response)
        
        print(f"📝 Transcription Neo: {transcript}")
        
        # Récupération de la configuration de l'hôtel pour ce numéro
        called_number = request.form.get("To", "")
        hotel_config = get_hotel_config(called_number)
        
        print(f"🏨 Traitement pour: {hotel_config['nom_hotel']}")
        
        # Génération de réponse avec GPT-4 selon la config de l'hôtel
        print("🤖 Neo génère une réponse avec GPT-4...")
        ai_response = generate_gpt4_response(transcript, caller_number, hotel_config)
        
        print(f"💭 Réponse Neo: {ai_response}")
        
        # Génération audio avec ElevenLabs selon la config
        print("🔊 Neo génère l'audio avec ElevenLabs...")
        response_audio_url = generate_elevenlabs_audio(ai_response, hotel_config)
        
        # Création de la réponse TwiML
        response = VoiceResponse()
        
        if response_audio_url:
            response.play(response_audio_url)
        else:
            # Fallback sur Twilio
            response.say(ai_response, language="fr-FR", voice="Polly.Celine")
        
        # Message de fin personnalisé selon l'hôtel
        end_message = f"Merci infiniment pour votre appel. Toute l'équipe du {hotel_config['nom_hotel']} reste à votre disposition. Très belle journée à vous !"
        end_audio = generate_elevenlabs_audio(end_message, hotel_config)
        
        if end_audio:
            response.play(end_audio)
        else:
            response.say(end_message, language="fr-FR", voice="Polly.Celine")
        
        print("✅ Neo a terminé le traitement avec succès")
        return str(response)
        
    except Exception as e:
        print(f"🚨 ERREUR dans process_recording Neo: {str(e)}")
        response = VoiceResponse()
        response.say(
            "Désolé, une erreur s'est produite lors du traitement de votre message.",
            language="fr-FR",
            voice="Polly.Celine"
        )
        return str(response)

def download_twilio_recording(recording_url):
    """Télécharge l'enregistrement depuis Twilio"""
    try:
        # Construction de l'URL pour télécharger l'audio WAV
        if recording_url.endswith('.json'):
            audio_url = recording_url.replace('.json', '.wav')
        else:
            audio_url = recording_url
        
        print(f"🔗 URL audio finale: {audio_url}")
        
        # Téléchargement avec authentification Twilio
        response = requests.get(
            audio_url, 
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ Audio téléchargé: {len(response.content)} bytes")
            return response.content
        else:
            print(f"❌ Erreur de téléchargement: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur dans download_twilio_recording: {str(e)}")
        return None

def transcribe_with_deepgram(audio_content):
    """Transcrit l'audio avec Deepgram"""
    try:
        # Configuration pour la transcription en français
        options = PrerecordedOptions(
            model="nova-2",
            language="fr",
            smart_format=True,
            punctuate=True,
            paragraphs=True,
            utterances=True
        )
        
        # Transcription
        response = deepgram.listen.prerecorded.v("1").transcribe_file(
            {"buffer": audio_content, "mimetype": "audio/wav"},
            options
        )
        
        # Extraction du texte
        transcript = response["results"]["channels"][0]["alternatives"][0]["transcript"]
        
        if transcript and transcript.strip():
            return transcript.strip()
        else:
            print("⚠️ Transcription vide")
            return None
            
    except Exception as e:
        print(f"❌ Erreur Deepgram: {str(e)}")
        return None

def generate_gpt4_response(transcript, caller_number="", hotel_config=None):
    """Génère une réponse intelligente avec GPT-4 selon la config de l'hôtel"""
    try:
        if not hotel_config:
            hotel_config = get_default_hotel_config()
        
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
        
        # Appel à l'API OpenAI GPT-4
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
        print(f"❌ Erreur GPT-4: {str(e)}")
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
        
        print(f"🎤 Voix sélectionnée: {langue}/{genre} pour {hotel_config['voix_prenom']}")
        
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
            
            print(f"✅ Audio {hotel_config['voix_prenom']} (Neo) ElevenLabs généré: {filename}")
            
            # TODO: Upload vers un service de stockage public pour retourner l'URL
            # Pour l'instant, retourne None pour utiliser le fallback Twilio
            return None
            
        else:
            print(f"❌ Erreur ElevenLabs: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur dans generate_elevenlabs_audio: {str(e)}")
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
            openai.api_key = OPENAI_API_KEY
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
        "webhook_url": f"{request.host_url}webhook",
        "ready_for_calls": all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, OPENAI_API_KEY, DEEPGRAM_API_KEY])
    })

@app.route("/demo", methods=["POST"])
def demo():
    """Endpoint de démonstration pour tester Neo sans appel téléphonique"""
    try:
        data = request.get_json()
        test_message = data.get("message", "Bonjour, je voudrais faire une réservation pour ce soir.")
        
        # Test de la chaîne complète (sans audio)
        response_text = generate_gpt4_response(test_message)
        
        return jsonify({
            "agent": "Neo",
            "company": "AlwayzIA",
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
    print("🚀 Démarrage de Neo - Agent IA Téléphonique AlwayzIA v2.0")
    print("🤖 Neo (Élise) est maintenant en ligne pour l'Hôtel Beau-Rivage")
    print("🏢 Société: AlwayzIA")
    print("📋 Prompt: v1.2 (06.06.2025) - Maxime Maadoune Meloni")
    print("🧠 GPT-4 pour l'intelligence artificielle")
    print("🎤 Deepgram pour la transcription")
    print("🔊 ElevenLabs Flash v2.5 pour la synthèse vocale")
    print("📞 Twilio pour la téléphonie")
    print("📡 Neo est prêt à recevoir les appels pour l'Hôtel Beau-Rivage...")
    
    # Configuration du port (Railway utilise la variable PORT)
    port = int(os.environ.get("PORT", 5000))
    
    # Démarrage de l'application
    app.run(
        host="0.0.0.0", 
        port=port, 
        debug=False  # Mettre True pour le debug en développement
    )
