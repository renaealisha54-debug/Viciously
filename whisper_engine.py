import os
import subprocess

BASE_DIR = os.path.expanduser("~/viciously")
WHISPER_CLI = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")
MODEL_FILE = os.path.expanduser("~/whisper.cpp/models/ggml-tiny.en.bin")

def process_audio_to_text(wav_file_path):
    """
    Executes native Whisper C++ binary on a 16kHz WAV chunk 
    and instantly purges text artifacts after reading.
    """
    if not os.path.exists(wav_file_path):
        return ""

    cmd = [
        WHISPER_CLI,
        "-m", MODEL_FILE,
        "-f", wav_file_path,
        "-nt",          # No timestamps in raw output
        "-otxt"         # Output as plain text file
    ]
    
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        txt_file = wav_file_path + ".txt"
        
        transcript = ""
        if os.path.exists(txt_file):
            with open(txt_file, "r") as f:
                transcript = f.read().strip()
            os.remove(txt_file)  # Instantly erase raw text output from storage
            
        return transcript
    except Exception as e:
        print(f"[Whisper Engine Error]: {e}")
        return ""
    finally:
        # Secure Purge: Remove WAV input chunk from disk
        if os.path.exists(wav_file_path):
            os.remove(wav_file_path)

if __name__ == "__main__":
    print("[Whisper Engine] Native audio processing module loaded.")
