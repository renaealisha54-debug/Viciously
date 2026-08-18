import os
import subprocess
import sqlite3
import time

RAW_AUDIO = "raw_chunk.m4a"
WAV_AUDIO = "chunk.wav"

def cleanup_files():
    for f in [RAW_AUDIO, WAV_AUDIO]:
        if os.path.exists(f):
            os.remove(f)

def record_audio_chunk(duration=5):
    cleanup_files()
    print("\n[Listening... Speak now!]")
    subprocess.run(["termux-microphone-record", "-f", RAW_AUDIO, "-l", str(duration)])
    time.sleep(duration + 0.5)

def convert_audio():
    if not os.path.exists(RAW_AUDIO):
        return False
    cmd = ["ffmpeg", "-y", "-i", RAW_AUDIO, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", WAV_AUDIO]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.exists(WAV_AUDIO)

def transcribe_chunk():
    if not convert_audio():
        return ""

    model_path = os.path.expanduser("~/whisper.cpp/models/ggml-tiny.en.bin")
    binary_path = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")
    
    cmd = [binary_path, "-m", model_path, "-f", WAV_AUDIO, "-nt", "-np"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    cleanup_files()
    return result.stdout.strip()

# Simple On-Device Keyword/Emotion Analyzer
def analyze_intent(text):
    triggers = ["angry", "frustrated", "never", "always", "upset", "hate", "wrong"]
    found_triggers = [word for word in triggers if word in text.lower()]
    
    if found_triggers:
        return f"High Intensity (Triggers detected: {', '.join(found_triggers)})"
    return "Neutral / Calm"

# Save context to SQLite
def save_memory(transcript, intensity):
    conn = sqlite3.connect("encrypted_memory.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO memories (timestamp, summary) VALUES (?, ?)",
        (int(time.time()), f"Text: '{transcript}' | Tone: {intensity}")
    )
    conn.commit()
    conn.close()

def init_db():
    conn = sqlite3.connect("encrypted_memory.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER,
            summary TEXT
        )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("=== Mediator Engine Online ===")
    try:
        while True:
            transcript = transcribe_chunk()
            if transcript and len(transcript) > 2:
                intensity = analyze_intent(transcript)
                print(f"-> Text: \"{transcript}\"")
                print(f"-> Analysis: {intensity}")
                save_memory(transcript, intensity)
            else:
                print("-> [Silence or ambient noise]")
    except KeyboardInterrupt:
        cleanup_files()
        print("\n[Session stopped]")

