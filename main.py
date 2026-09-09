import os
import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from plyer import tts

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

def speak(text):
    try:
        tts.speak(text)
    except Exception:
        pass

def transcribe_and_deescalate(audio_file_path):
    if not GROQ_API_KEY or not os.path.exists(audio_file_path):
        return

    stt_url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    
    try:
        with open(audio_file_path, "rb") as f:
            files = {"file": (audio_file_path, f, "audio/wav")}
            data = {"model": "whisper-large-v3-turbo"}
            response = requests.post(stt_url, headers=headers, files=files, data=data, timeout=10)
            transcript = response.json().get("text", "").strip()

        if not transcript:
            return

        chat_url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "You are a calm mediator in a heated conversation. Output exactly one short, de-escalating sentence."},
                {"role": "user", "content": f"The phrase '{transcript}' was spoken in anger. Provide a short mediator response."}
            ],
            "max_tokens": 50
        }
        res = requests.post(chat_url, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=payload, timeout=5)
        reply = res.json()["choices"][0]["message"]["content"].strip()
        speak(reply)

    except Exception as e:
        print(f"Pipeline error: {e}")

class ViciouslyUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.add_widget(Label(text="Viciously Mediator Active (openWakeWord)", font_size='20sp'))

class ViciouslyApp(App):
    def build(self):
        return ViciouslyUI()

if __name__ == "__main__":
    ViciouslyApp().run()
