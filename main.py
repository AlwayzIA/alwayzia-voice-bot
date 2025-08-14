import os
import openai
import asyncio
import sounddevice as sd
import numpy as np
from deepgram import Deepgram
from elevenlabs import generate, play, set_api_key

# 🔐 Clés API stockées dans des variables d’environnement
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# 🔧 Configuration des services
openai.api_key = OPENAI_API_KEY
dg_client = Deepgram(DEEPGRAM_API_KEY)
set_api_key(ELEVENLABS_API_KEY)

# 🎙️ Paramètres audio
SAMPLE_RATE = 16000
CHANNELS = 1

# 🧠 Fonction pour générer une réponse GPT
async def get_gpt_response(prompt):
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are Neo, an AI voice assistant."},
                  {"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# 🗣️ Fonction pour générer la voix avec ElevenLabs
def speak(text):
    audio = generate(text=text, voice="Josh")  # ou un nom de voix personnalisé
    play(audio)

# 🔊 Fonction de transcription avec Deepgram
async def transcribe_stream():
    print("🎧 Enregistrement... Parle maintenant.")
    
    stream = await dg_client.transcription.live(
        {'punctuate': True, 'language': 'fr'},
    )

    loop = asyncio.get_event_loop()
    audio_buffer = []

    def callback(indata, frames, time, status):
        if status:
            print(status)
        audio_data = indata.copy().tobytes()
        loop.call_soon_threadsafe(stream.send, audio_data)

    with sd.InputStream(callback=callback, channels=CHANNELS, samplerate=SAMPLE_RATE, dtype='int16'):
        async for msg in stream:
            if msg.get("channel") and msg["channel"]["alternatives"]:
                transcript = msg["channel"]["alternatives"][0].get("transcript", "")
                if transcript:
                    print(f"🗨️ Tu as dit : {transcript}")
                    await stream.finish()
                    return transcript

# 🚀 Lancement principal
async def main():
    transcription = await transcribe_stream()
    gpt_reply = await get_gpt_response(transcription)
    print(f"🤖 Neo : {gpt_reply}")
    speak(gpt_reply)

if __name__ == "__main__":
    asyncio.run(main())
