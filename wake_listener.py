import os
import time
import subprocess
import sys

WHISPER_BIN = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")
MODEL_PATH = os.path.expanduser("~/whisper.cpp/models/ggml-base.en.bin")
SAMPLE_DURATION_SEC = 3
IDLE_POLL_INTERVAL_SEC = 1

# Triggers on named wake words AND common escalation indicators
WAKE_WORDS = [
    "viciously", "hey viciously", "listen", "stop", "help", "calm",
    "fuck", "shit", "shut up", "don't", "whatever", "bitch", "argument"
]

def cheap_transcribe(m4a_path):
    if not m4a_path or not os.path.exists(m4a_path):
        return ""
    wav_path = m4a_path.replace(".m4a", "_temp.wav")
    try:
        ffmpeg_cmd = ["ffmpeg", "-y", "-i", m4a_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav_path]
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        whisper_cmd = [WHISPER_BIN, "-m", MODEL_PATH, "-f", wav_path, "-nt"]
        res = subprocess.run(whisper_cmd, capture_output=True, text=True, timeout=10)
        return res.stdout.strip().lower()
    except Exception:
        return ""
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)

def record_probe_clip(duration_sec=3):
    out_dir = os.path.expanduser("~/viciously")
    os.makedirs(out_dir, exist_ok=True)
    m4a_path = os.path.join(out_dir, "probe_raw.m4a")
    if os.path.exists(m4a_path):
        os.remove(m4a_path)
    subprocess.run(["termux-microphone-record", "-q"], stderr=subprocess.DEVNULL)
    subprocess.run(["termux-microphone-record", "-f", m4a_path, "-l", str(duration_sec)], stderr=subprocess.DEVNULL)
    time.sleep(duration_sec + 0.5)
    return m4a_path if os.path.exists(m4a_path) else None

def run_full_pipeline(reason="speech detected"):
    print(f"\n[TRIGGER] Wake word/Hostility matched! Reason: {reason}")
    mediator_path = os.path.expanduser("~/Viciously/mediator.py")
    if os.path.exists(mediator_path):
        subprocess.run(["python3", mediator_path])

def idle_gate_loop():
    print(f"Listening continuously for triggers: {WAKE_WORDS}...")
    while True:
        m4a_path = record_probe_clip(SAMPLE_DURATION_SEC)
        if m4a_path:
            transcript = cheap_transcribe(m4a_path)
            if transcript:
                if any(w in transcript for w in WAKE_WORDS):
                    run_full_pipeline(reason=f"Detected phrase: '{transcript}'")
                else:
                    print(f"[Ignored background speech]: '{transcript}'")
            if os.path.exists(m4a_path):
                os.remove(m4a_path)
        time.sleep(IDLE_POLL_INTERVAL_SEC)

if __name__ == "__main__":
    try:
        idle_gate_loop()
    except KeyboardInterrupt:
        print("\n[Stopped] Listener turned off.")
        subprocess.run(["termux-microphone-record", "-q"], stderr=subprocess.DEVNULL)
        sys.exit(0)
