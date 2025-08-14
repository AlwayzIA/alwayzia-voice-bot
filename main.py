# main.py

import os
import openai
from elevenlabs import generate, play, set_api_key
import time

# --- Configuration des clés API ---
openai.api_key = "ta_clé_openai"
set_api_key("sk_3ec4cb317fca644822bb40a09af061a0493d8f53908ad39b")  # Clé ElevenLabs

# --- Paramètres de la voix ElevenLabs ---
VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Rachel (par défaut)
MODEL = "eleven_multilingual_v2"

# --- Fonction pour générer la voix avec ElevenLabs ---
def speak(text):
    try:
        print(f"[Neo] {text}")
        audio = generate(
            text=text,
            voice=VOICE_ID,
            model=MODEL
        )
        play(audio)
    except Exception as e:
        print("Erreur lors de la génération vocale :", e)

# --- Fonction pour appeler l'API GPT ---
def ask_gpt(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es Neo, un assistant vocal pour les hôtels, courtois et professionnel."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Désolé, une erreur est survenue avec l'intelligence artificielle."

# --- Programme principal ---
if __name__ == "__main__":
    print("L'agent Neo est lancé...")

    # Exemples de test
    questions = [
        "Quels sont les horaires d'ouverture de la réception ?",
        "Puis-je amener mon chien à l'hôtel ?",
        "Est-ce que le petit déjeuner est inclus dans la chambre ?"
    ]

    for q in questions:
        print(f"\n[Client] {q}")
        reply = ask_gpt(q)
        speak(reply)
        time.sleep(2)
