import os
import time
import requests
from kivy.app import App
from kivy.uix.label import Label
from plyer import tts

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
WAKE_WORDS = ["viciously", "hey viciously", "listen", "stop", "help", "calm", "fuck", "shit", "shut up", "don't", "whatever", "bitch"]

def speak(text):
    print(f"[AI Mediator]: {text}")
    try:
        tts.speak(text)
    except Exception:
        pass

def generate_deescalation(spoken_text):
    if not GROQ_API_KEY:
        speak("Let's take a short pause so we can speak calmly.")
        return

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a calm mediator in a heated conversation. Output exactly one short, de-escalating sentence."},
            {"role": "user", "content": f"The phrase '{spoken_text}' was spoken in anger. Provide a short mediator response."}
        ],
        "max_tokens": 50
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        data = res.json()
        reply = data["choices"][0]["message"]["content"].strip()
        speak(reply)
    except Exception:
        speak("Let me step in for a second so we can speak calmly.")

class ViciouslyApp(App):
    def build(self):
        return Label(text="Viciously Mediator Active")

if __name__ == "__main__":
    ViciouslyApp().run()
