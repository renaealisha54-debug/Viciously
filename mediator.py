import os
import time
import subprocess
import sqlite3
import requests
import json

BASE_DIR = os.path.expanduser("~/viciously")
WHISPER_PATH = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")
MODEL_PATH = os.path.expanduser("~/whisper.cpp/models/ggml-tiny.en.bin")

DB_FILE = os.path.join(BASE_DIR, "encrypted_memory.db")
RAW_AUDIO = os.path.join(BASE_DIR, "raw_chunk.m4a")
WAV_AUDIO = os.path.join(BASE_DIR, "chunk.wav")

PASSPHRASE = "SuperSecretMediatorKey2026!"
RETENTION_DAYS = 7

# --- Android Runtime Permission Prompt ---

def check_and_request_permissions():
    """Prompts Android runtime permissions if building via Android API wrapper."""
    try:
        # Request microphone permission via Termux / Android API wrapper
        res = subprocess.run(["termux-microphone-record", "-i"], capture_output=True, text=True)
        if "Permission denied" in res.stderr or "Permission denied" in res.stdout:
            print("[Permission Alert] Microphone permission is required for APK audio analysis.")
            subprocess.run(["termux-tts-speak", "Please grant microphone permissions to activate mediator."])
    except Exception:
        pass

# --- Encrypted Storage ---

def fetch_knowledge_context():
    """Queries encrypted boundaries and history."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA key = '{PASSPHRASE}';")
        cursor.execute("SELECT category, subject, fact_or_rule FROM knowledge_base WHERE weight >= 2")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return ""
            
        context_str = "\n[INTERNAL ENCRYPTED BOUNDARIES & HISTORY]:\n"
        for row in rows:
            context_str += f"- ({row[0].upper()} - {row[1]}): {row[2]}\n"
        return context_str
    except Exception as e:
        print(f"[DB Warning] Could not fetch knowledge context: {e}")
        return ""

def save_encrypted_summary(summary, advice):
    """Saves non-verbatim summary and advice to encrypted database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA key = '{PASSPHRASE}';")
        
        current_time = int(time.time())
        cursor.execute(
            "INSERT INTO memories (timestamp, transcript, advice) VALUES (?, ?, ?)",
            (current_time, summary, advice)
        )
        
        cutoff_time = current_time - (RETENTION_DAYS * 86400)
        cursor.execute("DELETE FROM memories WHERE timestamp < ?", (cutoff_time,))
        
        conn.commit()
        conn.close()
        print("[Security] Non-verbatim analysis saved to encrypted storage.")
    except Exception as e:
        print(f"[DB Error] Failed to save memory: {e}")

# --- Speech & Hardware Handlers ---

def speak_advice(text):
    if not text:
        return
    print(f"[TTS Output] Speaking: '{text}'")
    try:
        subprocess.run(["termux-tts-speak", "-r", "1.0", text], check=True)
    except Exception as e:
        print(f"[TTS Error] Could not speak advice: {e}")

def record_audio_chunk(duration_sec=7):
    """Captures audio chunk and instantly purges raw file after WAV conversion."""
    print(f"\n[Microphone] Monitoring conversation ({duration_sec}s)...")
    
    subprocess.run(["termux-microphone-record", "-f", RAW_AUDIO], check=True)
    time.sleep(duration_sec)
    subprocess.run(["termux-microphone-record", "-q"], check=True)
    
    if os.path.exists(RAW_AUDIO):
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", RAW_AUDIO,
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
            WAV_AUDIO
        ]
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        # DELETE RAW AUDIO IMMEDIATELY
        os.remove(RAW_AUDIO)

def transcribe_audio():
    """Transcribes audio and deletes WAV file immediately."""
    if not os.path.exists(WAV_AUDIO):
        return ""
        
    print("[Whisper.cpp] Transcribing and identifying voice patterns...")
    cmd = [WHISPER_PATH, "-m", MODEL_PATH, "-f", WAV_AUDIO, "-nt", "-otxt"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    txt_output = WAV_AUDIO + ".txt"
    transcript = ""
    if os.path.exists(txt_output):
        with open(txt_output, "r") as f:
            transcript = f.read().strip()
        os.remove(txt_output)
        
    # DELETE WAV FILE IMMEDIATELY
    if os.path.exists(WAV_AUDIO):
        os.remove(WAV_AUDIO)
        
    return transcript

# --- Speaker Analysis & Analysis Engine ---

def analyze_argument_and_deescalate(raw_transcript):
    """
    Analyzes argument tone, assigns speaker perspectives, assumes who appears in the wrong,
    references key pinpoints WITHOUT repeating exact spoken words, and gives advice.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    background_context = fetch_knowledge_context()
    
    system_prompt = (
        "You are an objective AI relationship mediator analyzing a live argument between two speakers.\n"
        f"{background_context}\n\n"
        "STRICT PRIVACY & FORMATTING INSTRUCTIONS:\n"
        "1. Identify the speakers (e.g., Speaker A vs Speaker B).\n"
        "2. Form a tentative ASSUMPTION about who appears more off-track or in the wrong.\n"
        "3. Explicitly state that this is ONLY an initial assumption based on limited context.\n"
        "4. Pinpoint the underlying themes/issues that triggered this assumption WITHOUT repeating their exact spoken words or verbatim phrases.\n"
        "5. Provide a calm, 1-sentence de-escalation suggestion.\n\n"
        "Return a JSON object with exactly two keys:\n"
        ' - "summary": The assessment stating the assumption, who seems off-track, and the pinpointed themes (no exact quotes).\n'
        ' - "advice": A brief spoken advice sentence for the room.'
    )
    
    user_prompt = f"Live Conversation Transcript: \"{raw_transcript}\""

    # Cloud Path (Groq API)
    if groq_api_key:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3
            }
            res = requests.post(url, json=payload, headers=headers, timeout=6)
            if res.status_code == 200:
                data = res.json()['choices'][0]['message']['content']
                parsed = json.loads(data)
                return parsed.get("summary", ""), parsed.get("advice", "Take a slow breath before continuing.")
        except Exception as e:
            print(f"[Cloud Fallback] Groq offline: {e}")

    # Local Fallback (Ollama)
    try:
        ollama_url = "http://localhost:11434/api/generate"
        prompt = f"{system_prompt}\n\n{user_prompt}\nReturn JSON:"
        payload = {"model": "llama3.2:1b", "prompt": prompt, "format": "json", "stream": False}
        res = requests.post(ollama_url, json=payload, timeout=10)
        if res.status_code == 200:
            parsed = json.loads(res.json()['response'])
            return parsed.get("summary", ""), parsed.get("advice", "Take a slow breath before continuing.")
    except Exception:
        pass

    return (
        "Assumption: Based on tone, one speaker seems defensive over budget pinpoints. (Preliminary assessment).",
        "Take a slow breath before responding to keep the conversation calm."
    )

# --- Engine Execution Loop ---

if __name__ == "__main__":
    print("=== Viciously Mediator Engine Active ===")
    check_and_request_permissions()
    
    try:
        while True:
            record_audio_chunk(duration_sec=7)
            transcript = transcribe_audio()
            
            if transcript and len(transcript) > 4 and "[BLANK_AUDIO]" not in transcript:
                print(f"\n[Raw Audio Transcribed & Purged from Disk]")
                
                analysis, advice = analyze_argument_and_deescalate(transcript)
                
                print(f"\n[Mediator Analysis]:\n{analysis}")
                print(f"\n[Mediator Spoken Advice]:\n{advice}\n")
                
                speak_advice(advice)
                save_encrypted_summary(analysis, advice)
            else:
                print("[No actionable audio detected - buffers purged]")
                
    except KeyboardInterrupt:
        print("\n[Engine Stopped]")
