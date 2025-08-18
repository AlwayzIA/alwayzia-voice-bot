@app.route("/process_recording", methods=["POST"])
def process_recording():
    try:
        print("🔔 Nouvel appel reçu")
        print("📥 Traitement de l'enregistrement")

        base_url = request.form["RecordingUrl"]
        print(f"🔗 URL brute retournée par Twilio : {base_url}")

        TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
        TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

        # Étape 1 : Récupérer les métadonnées JSON de l'enregistrement
        metadata_response = requests.get(base_url, auth=(TWILIO_SID, TWILIO_TOKEN))

        if metadata_response.status_code != 200:
            print(f"❌ Erreur lors de la récupération des métadonnées : {metadata_response.status_code}")
            return "Erreur de métadonnées", 500

        metadata = metadata_response.json()
        media_url = metadata["media_url"] if "media_url" in metadata else metadata["uri"].replace('.json', '.wav')
        final_url = f"https://api.twilio.com{media_url}"

        print(f"🎧 URL du fichier audio WAV : {final_url}")

        # Étape 2 : Télécharger l’audio
        audio_response = requests.get(final_url, auth=(TWILIO_SID, TWILIO_TOKEN))
        if audio_response.status_code != 200:
            print(f"❌ Erreur HTTP: {audio_response.status_code}")
            return "Erreur de téléchargement", 500

        # Sauvegarder localement
        filename = f"/tmp/{uuid.uuid4()}.wav"
        with open(filename, "wb") as f:
            f.write(audio_response.content)

        print(f"✅ Audio sauvegardé localement : {filename}")

        # Fake transcription
        transcript = "Transcription simulée..."
        print(f"📝 Transcription : {transcript}")

        response = VoiceResponse()
        response.say(f"Vous avez dit : {transcript}", language="fr-FR", voice="Polly.Celine")
        return str(response)

    except Exception as e:
        print(f"🚨 ERREUR : {str(e)}")
        return "Erreur interne", 500
