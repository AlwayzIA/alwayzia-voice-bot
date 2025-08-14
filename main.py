import os
import asyncio
import openai
import sounddevice as sd
import numpy as np
from deepgram import Deepgram
from elevenlabs import generate, play, set_api_key
from dotenv import load_dotenv

# 🔐 Charger les variables d’environnement depuis le fichier .env
load_dotenv()

# 📌 Clés API (ne pas écrire en dur dans le script)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# 🔧 Configuration des clients API
openai.api_key = OPENAI_API_KEY
dg_client = Deepgram(DEEPGRAM_API_KEY)
set_api_key(ELEVENLABS_API_KEY)

# 🎙️ Paramètres audio
SAMPLE_RATE = 16000
CHANNELS = 1

# 🧠 Génération de réponse avec GPT
async def get_gpt_response(prompt):
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Tu es Neo, un assistant vocal intelligent qui répond clairement aux clients des hôtels."},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content']

# 🗣️ Génération vocale avec ElevenLabs
def speak(text):
    audio = generate(text=text, voice="Josh")  # Ou ta voix ElevenLabs perso
    play(audio)

# 🎧 Transcription avec Deepgram (live)
async def transcribe_stream():
    print("🎙️ Parle maintenant, j'écoute...")

    stream = await dg_client.transcription.live(
        {'punctuate': True, 'language': 'fr'},
    )

    loop = asyncio.get_event_loop()

    def callback(indata, frames, time, status):
        if status:
            print(status)
        loop.call_soon_threadsafe(stream.send, indata.copy().tobytes())

    with sd.InputStream(callback=callback, channels=CHANNELS, samplerate=SAMPLE_RATE, dtype='int16'):
        async for msg in stream:
            if msg.get("channel") and msg["channel"]["alternatives"]:
                transcript = msg["channel"]["alternatives"][0].get("transcript", "")
                if transcript:
                    print(f"🗨️ Tu as dit : {transcript}")
                    await stream.finish()
                    return transcript

# 🚀 Exécution principale
async def main():
    transcription = await transcribe_stream()
    gpt_reply = await get_gpt_response(transcription)
    print(f"🤖 Neo : {gpt_reply}")
    speak(gpt_reply)

if __name__ == "__main__":
    asyncio.run(main())
