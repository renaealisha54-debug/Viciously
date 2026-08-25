# Viciously

An Android app (built with Kivy + Termux) that listens for consensual, in-the-moment conversational escalation and offers real-time de-escalation support.

## How it works

1. **`wake_listener.py`** — a lightweight gating layer that periodically checks short audio probes for:
   - Loud/escalating voice (amplitude only, no transcription needed)
   - Wake phrases (matched with phonetic + fuzzy tolerance, so near-miss transcriptions still count)
   - Manual voice commands ("start recording" / "stop recording")

   Raw audio from these probes is deleted immediately after each check - nothing is stored unless a real trigger fires.

2. On a trigger, the full pipeline in **`mediator.py`** runs:
   - Records a real audio chunk
   - Transcribes it via `whisper.cpp`
   - Sends the transcript to an LLM (Groq cloud, falling back to local Ollama) for de-escalation analysis
   - Speaks advice back via TTS
   - Saves an encrypted summary to a local database (`secure_db.py`)

3. **Consent signal**: every trigger beeps audibly before recording starts - 1 beep for a low-stress phrase, 3 beeps for loud voice or high-stress phrases - so anyone in the room knows analysis is active.

4. **`service.py`** runs this as a persistent Android foreground service, respecting audio focus (so it pauses cleanly during phone calls).

5. **`main.py`** is the Kivy dashboard: shows encrypted history, a live rolling "escalation" percentage, and a live volume-level indicator (no raw audio is ever displayed - only these derived numbers).

## Requirements

- Termux + Termux:API (companion app from F-Droid)
- Python 3, `numpy`, `jellyfish`, `pycryptodomex`, `requests`, `flask`
- `whisper.cpp` built locally with the `tiny.en` or `base.en` model
- Ollama (local fallback) and/or a Groq API key (cloud) for the analysis step

## Status

Actively in development - wake-word detection, beep signaling, and the live dashboard are working; the Android APK build (via buildozer) is in progress.
