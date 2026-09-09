import os
import time
import subprocess
import requests

WHISPER_BIN = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")
MODEL_PATH = os.path.expanduser("~/whisper.cpp/models/ggml-base.en.bin")
WORK_DIR = os.path.expanduser("~/viciously")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

os.makedirs(WORK_DIR, exist_ok=True)

def cleanup_file(filepath):
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass

def speak(text):
    print(f"\n[AI Mediator Response]: {text}\n")
    subprocess.run(["termux-tts-speak", text], stderr=subprocess.DEVNULL)

def generate_deescalation(spoken_text):
    if not GROQ_API_KEY:
        print("\n[Notice] GROQ_API_KEY environment variable is empty. Using local fallback.")
        speak("Let's take a pause and take a deep breath before continuing.")
        return

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "You are a calm mediator during a heated discussion. Output exactly one brief, soothing sentence to lower tension."
            },
            {
                "role": "user",
                "content": f"The phrase '{spoken_text}' was just spoken. Give a brief de-escalation response."
            }
        ],
        "max_tokens": 50
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        data = res.json()
        
        if "choices" in data and len(data["choices"]) > 0:
            reply = data["choices"][0]["message"]["content"].strip()
            speak(reply)
        else:
            err_msg = data.get("error", {}).get("message", str(data))
            print(f"[Groq API Error]: {err_msg}")
            speak("Let me step in for a second so we can speak calmly.")
    except Exception as e:
        print(f"[Request Error]: {e}")
        speak("Let's take a short pause to keep things calm.")

def record_audio_chunk(duration_sec=7):
    m4a_path = os.path.join(WORK_DIR, "raw_chunk.m4a")
    wav_path = os.path.join(WORK_DIR, "chunk.wav")

    cleanup_file(m4a_path)
    cleanup_file(wav_path)

    print(f"[Microphone] Monitoring conversation ({duration_sec}s)...")
    subprocess.run(["termux-microphone-record", "-q"], stderr=subprocess.DEVNULL)
    subprocess.run(["termux-microphone-record", "-f", m4a_path, "-l", str(duration_sec)], stderr=subprocess.DEVNULL)
    time.sleep(duration_sec + 0.5)

    if not os.path.exists(m4a_path) or os.path.getsize(m4a_path) == 0:
        return None

    try:
        ffmpeg_cmd = ["ffmpeg", "-y", "-i", m4a_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav_path]
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return wav_path
    except Exception:
        return None

def process_chunk():
    wav_path = record_audio_chunk(7)
    if not wav_path:
        return

    print("[Whisper.cpp] Transcribing clip...")
    try:
        whisper_cmd = [WHISPER_BIN, "-m", MODEL_PATH, "-f", wav_path, "-nt"]
        res = subprocess.run(whisper_cmd, capture_output=True, text=True, timeout=15)
        text = res.stdout.strip()

        if text and not text.startswith("["):
            print(f"[Mediator Heard]: '{text}'")
            generate_deescalation(text)
    except Exception as e:
        print(f"[Error]: {e}")
    finally:
        cleanup_file(os.path.join(WORK_DIR, "raw_chunk.m4a"))
        cleanup_file(wav_path)

if __name__ == "__main__":
    print("=== Viciously Mediator Engine Active ===")
    process_chunk()
