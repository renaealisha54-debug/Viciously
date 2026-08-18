import os
import time
import subprocess
import sqlite3
import requests

# Directory Setup
BASE_DIR = os.path.expanduser("~/viciously")
WHISPER_PATH = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")
MODEL_PATH = os.path.expanduser("~/whisper.cpp/models/ggml-tiny.en.bin")

DB_FILE = os.path.join(BASE_DIR, "encrypted_memory.db")
RAW_AUDIO = os.path.join(BASE_DIR, "raw_chunk.m4a")
WAV_AUDIO = os.path.join(BASE_DIR, "chunk.wav")

PASSPHRASE = "SuperSecretMediatorKey2026!"
RETENTION_DAYS = 7

# --- Database & Context Fetching ---

def fetch_knowledge_context():
    """Queries active rules, boundaries, and history from knowledge_base."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA key = '{PASSPHRASE}';")
        cursor.execute("""
            SELECT category, subject, fact_or_rule, weight 
            FROM knowledge_base 
            WHERE weight >= 2 
            ORDER BY weight DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return ""
            
        context_str = "\n[KNOWN BACKGROUND & AGREED BOUNDARIES]:\n"
        for row in rows:
            cat, subject, rule, weight = row
            context_str += f"- ({cat.upper()} - {subject}): {rule}\n"
        return context_str
    except Exception as e:
        print(f"[DB Warning] Could not fetch knowledge context: {e}")
        return ""

def save_encrypted_memory(transcript, advice):
    """Saves transcript/advice and enforces the 7-day retention policy."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA key = '{PASSPHRASE}';")
        
        current_time = int(time.time())
        cursor.execute(
            "INSERT INTO memories (timestamp, transcript, advice) VALUES (?, ?, ?)",
            (current_time, transcript, advice)
        )
        
        cutoff_time = current_time - (RETENTION_DAYS * 86400)
        cursor.execute("DELETE FROM memories WHERE timestamp < ?", (cutoff_time,))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB Error] Failed to save memory: {e}")

# --- Text-to-Speech Output ---

def speak_advice(text):
    """Speaks advice aloud using Android's native TTS via Termux API."""
    if not text:
        return
    print(f"[TTS Output] Speaking: '{text}'")
    try:
        # -r 1.1 sets a slightly natural speech rate
        subprocess.run(["termux-tts-speak", "-r", "1.1", text], check=True)
    except Exception as e:
        print(f"[TTS Error] Could not speak advice: {e}")

# --- Hardware Audio & STT Functions ---

def record_audio_chunk(duration_sec=5):
    """Captures a raw audio chunk using Termux API and converts to 16kHz WAV."""
    print(f"\n[Microphone] Listening for {duration_sec} seconds...")
    
    subprocess.run(["termux-audio-record", "-f", RAW_AUDIO], check=True)
    time.sleep(duration_sec)
    subprocess.run(["termux-audio-record", "-q"], check=True)
    
    if os.path.exists(RAW_AUDIO):
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", RAW_AUDIO,
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
            WAV_AUDIO
        ]
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        os.remove(RAW_AUDIO)

def transcribe_audio():
    """Executes whisper.cpp C++ binary on the converted WAV file."""
    if not os.path.exists(WAV_AUDIO):
        return ""
        
    print("[Whisper.cpp] Transcribing audio...")
    cmd = [
        WHISPER_PATH,
        "-m", MODEL_PATH,
        "-f", WAV_AUDIO,
        "-nt",
        "-otxt"
    ]
    
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    txt_output = WAV_AUDIO + ".txt"
    transcript = ""
    if os.path.exists(txt_output):
        with open(txt_output, "r") as f:
            transcript = f.read().strip()
        os.remove(txt_output)
        
    if os.path.exists(WAV_AUDIO):
        os.remove(WAV_AUDIO)
        
    return transcript

# --- De-escalation Advice Pipeline ---

def generate_deescalation_advice(transcript):
    """Constructs prompt using active knowledge base context and queries LLM."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    background_context = fetch_knowledge_context()
    
    system_prompt = (
        "You are an objective conflict mediator monitoring a live conversation. "
        "Provide a calm, neutral 1-sentence de-escalation suggestion. "
        "If a spoken point conflicts with an agreed boundary below, gently mention it.\n"
        f"{background_context}"
    )
    
    if groq_api_key:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f'Current Transcript: "{transcript}"'}
                ],
                "temperature": 0.3
            }
            res = requests.post(url, json=payload, headers=headers, timeout=5)
            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"[Cloud Fallback] Groq unavailable: {e}")

    try:
        ollama_url = "http://localhost:11434/api/generate"
        prompt = f"{system_prompt}\n\nTranscript: \"{transcript}\"\nAdvice:"
        payload = {"model": "llama3.2:1b", "prompt": prompt, "stream": False}
        res = requests.post(ollama_url, json=payload, timeout=10)
        if res.status_code == 200:
            return res.json()['response'].strip()
    except Exception:
        pass

    return "Take a slow breath before responding to maintain calm."

# --- Main Engine Execution Loop ---

if __name__ == "__main__":
    print("=== Viciously Engine Active (TTS Enabled) ===")
    
    try:
        while True:
            record_audio_chunk(duration_sec=5)
            transcript = transcribe_audio()
            
            if transcript and len(transcript) > 3 and "[BLANK_AUDIO]" not in transcript:
                print(f"\n[Transcript Detected]: '{transcript}'")
                advice = generate_deescalation_advice(transcript)
                print(f"[Mediator Advice]: {advice}")
                
                # Speak advice aloud via Android TTS
                speak_advice(advice)
                
                # Save to encrypted DB
                save_encrypted_memory(transcript, advice)
            else:
                print("[Silence or ambient noise]")
                
    except KeyboardInterrupt:
        print("\n[Engine Stopped Manually]")
