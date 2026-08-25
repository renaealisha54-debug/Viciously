"""
wake_listener.py

Gating layer that sits in FRONT of the existing mediator pipeline
(mediator.record_audio_chunk -> transcribe_audio -> analyze_argument_and_deescalate).

Nothing here transcribes or saves audio on its own. It only decides WHEN
the existing (expensive) pipeline in mediator.py should run, based on:

  1. Amplitude / loud-voice detection (cheap, no ASR involved)
  2. Manual voice commands ("start recording" / "stop recording")
  3. Wake-word / escalation-phrase matching on short transcribed samples,
     using phonetic + fuzzy matching so near-miss transcriptions still match.

Wake-word matches are instant triggers. Loud voice and high-stress phrases
beep 3 times; low-stress phrases beep once. Manual "start recording" /
"stop recording" bypass wake-word gating for a continuous session.
"""

import os
import time
import wave
import json
import subprocess
import numpy as np
import jellyfish

import mediator
import notifier

BASE_DIR = os.path.expanduser("~/viciously")
SAMPLE_WAV = os.path.join(BASE_DIR, "wake_sample.wav")

STATUS_FILE = os.path.join(BASE_DIR, "live_status.json")
EVENTS_FILE = os.path.join(BASE_DIR, "escalation_events.json")
ESCALATION_WINDOW_SEC = 300
ESCALATION_MAX_SEVERITY_SUM = 15
RMS_REFERENCE_MAX = 15000

WAKE_PHRASES = [
    "dont talk to me like that",
    "stop",
    "bitch",
    "hoe",
    "stupid",
    "do it again",
    "keep doing it",
    "shut the fuck up",
    "i said stop",
    "dum",
    "cunt",
    "deuces",
    "i dont give a fuck",
    "retarded",
    "my name is alisha",
    "what the fuck",
    "i dont care",
    "now what are you gonna do",
    "oh youre going somewhere",
    "where you going",
    "why would you say that",
    "what are you doing",
    "keep trying me",
    "what you say",
    "go on then",
    "fuck you",
    "fuck off",
]

HIGH_STRESS_PHRASES = {
    "bitch",
    "cunt",
    "retarded",
    "shut the fuck up",
    "i said stop",
    "fuck you",
    "fuck off",
    "keep trying me",
    "go on then",
    "do it again",
    "keep doing it",
    "why would you say that",
    "now what are you gonna do",
    "oh youre going somewhere",
    "where you going",
    "what the fuck",
}

START_COMMANDS = ["start recording", "im recording"]
STOP_COMMANDS = ["stop recording", "recording off"]

AMPLITUDE_RMS_THRESHOLD = 4000
SAMPLE_DURATION_SEC = 3.5
IDLE_POLL_INTERVAL_SEC = 1.5
FUZZY_MATCH_MAX_DISTANCE = 2

MAX_SKIPPABLE_WORDS = 1
OPTIONAL_PHRASE_FILLERS = {"are", "a", "an", "the", "to", "is", "did", "you're", "youre"}


def _normalize(text):
    return "".join(ch for ch in text.lower().strip() if ch.isalnum() or ch.isspace())


def phrase_matches(transcript, phrase_list):
    norm_transcript = _normalize(transcript)
    if not norm_transcript:
        return None
    transcript_words = norm_transcript.split()
    for phrase in phrase_list:
        phrase_words = _normalize(phrase).split()
        if not phrase_words:
            continue
        for start in range(len(transcript_words)):
            if _subsequence_matches_phrase(transcript_words, start, phrase_words):
                return phrase
    return None


def _max_distance_for(word):
    length = len(word)
    if length <= 3:
        return 0
    if length <= 5:
        return 1
    return FUZZY_MATCH_MAX_DISTANCE


def _words_match(w, p):
    if w == p:
        return True
    if jellyfish.metaphone(w) == jellyfish.metaphone(p):
        return True
    max_dist = min(_max_distance_for(w), _max_distance_for(p))
    if max_dist > 0 and jellyfish.levenshtein_distance(w, p) <= max_dist:
        return True
    return False


def _subsequence_matches_phrase(transcript_words, start, phrase_words):
    t_idx = start
    skips_used = 0
    matched_any_content_word = False
    for p_word in phrase_words:
        matched = False
        lookahead = 0
        while t_idx + lookahead < len(transcript_words) and lookahead <= MAX_SKIPPABLE_WORDS:
            if _words_match(transcript_words[t_idx + lookahead], p_word):
                t_idx += lookahead + 1
                skips_used += lookahead
                matched = True
                matched_any_content_word = True
                break
            lookahead += 1
        if not matched:
            if p_word in OPTIONAL_PHRASE_FILLERS:
                continue
            return False
        if skips_used > MAX_SKIPPABLE_WORDS * len(phrase_words):
            return False
    return matched_any_content_word


def record_probe_clip(duration_sec=SAMPLE_DURATION_SEC):
    raw_path = os.path.join(BASE_DIR, "probe_raw.m4a")
    if os.path.exists(raw_path):
        os.remove(raw_path)
    subprocess.run(["termux-microphone-record", "-f", raw_path], check=True)
    time.sleep(duration_sec)
    subprocess.run(["termux-microphone-record", "-q"], check=True)
    time.sleep(0.5)

    if not os.path.exists(raw_path):
        return None

    subprocess.run(
        ["ffmpeg", "-y", "-i", raw_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", SAMPLE_WAV],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )
    os.remove(raw_path)
    return SAMPLE_WAV if os.path.exists(SAMPLE_WAV) else None


def measure_rms(wav_path):
    try:
        with wave.open(wav_path, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            signal = np.frombuffer(frames, dtype=np.int16)
            if len(signal) == 0:
                return 0
            return float(np.sqrt(np.mean(signal.astype(float) ** 2)))
    except Exception as e:
        print(f"[Wake Listener] RMS check failed: {e}")
        return 0


def _load_events():
    if not os.path.exists(EVENTS_FILE):
        return []
    try:
        with open(EVENTS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_events(events):
    try:
        with open(EVENTS_FILE, "w") as f:
            json.dump(events, f)
    except Exception as e:
        print(f"[Wake Listener] Failed to save escalation events: {e}")


def record_escalation_event(severity):
    events = _load_events()
    now = time.time()
    events.append({"ts": now, "severity": severity})
    events = [e for e in events if now - e["ts"] <= ESCALATION_WINDOW_SEC]
    _save_events(events)


def compute_escalation_percent():
    events = _load_events()
    now = time.time()
    recent_total = sum(e["severity"] for e in events if now - e["ts"] <= ESCALATION_WINDOW_SEC)
    return min(100, round((recent_total / ESCALATION_MAX_SEVERITY_SUM) * 100))


def update_live_status(current_rms=None):
    status = {"escalation_percent": compute_escalation_percent(), "last_updated": time.time()}
    if current_rms is not None:
        status["current_level_percent"] = min(100, round((current_rms / RMS_REFERENCE_MAX) * 100))
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(status, f)
    except Exception as e:
        print(f"[Wake Listener] Failed to write live status: {e}")


def cheap_transcribe(wav_path):
    cmd = [mediator.WHISPER_PATH, "-m", mediator.MODEL_PATH, "-f", wav_path, "-nt", "-otxt"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    txt_path = wav_path + ".txt"
    text = ""
    if os.path.exists(txt_path):
        with open(txt_path, "r") as f:
            text = f.read().strip()
        os.remove(txt_path)
    return text


BEEP_FILE = os.path.join(BASE_DIR, "beep_tone.wav")


def _ensure_beep_file():
    if not os.path.exists(BEEP_FILE):
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=0.15",
             "-ar", "16000", "-ac", "1", BEEP_FILE],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
        )


def beep(count=1, gap_sec=0.25):
    _ensure_beep_file()
    for _ in range(count):
        subprocess.run(["termux-media-player", "play", BEEP_FILE],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(gap_sec)


def announce_trigger(reason, high_stress=False):
    notifier.send_android_notification("Viciously Active", f"Recording started ({reason}).")
    beep(3 if high_stress else 1)


def run_full_pipeline(reason, high_stress=False):
    announce_trigger(reason, high_stress=high_stress)
    mediator.record_audio_chunk(duration_sec=7)
    transcript = mediator.transcribe_audio()
    if transcript and len(transcript) > 4 and "[BLANK_AUDIO]" not in transcript:
        analysis, advice = mediator.analyze_argument_and_deescalate(transcript)
        mediator.speak_advice(advice)
        mediator.save_encrypted_summary(analysis, advice)


def manual_session_loop():
    print("[Wake Listener] Manual recording session started.")
    notifier.send_android_notification("Viciously Active", "Manual recording session started.")
    beep(1)

    while True:
        wav_path = record_probe_clip(duration_sec=7)
        if not wav_path:
            continue
        transcript = cheap_transcribe(wav_path)
        os.remove(wav_path) if os.path.exists(wav_path) else None

        if transcript and len(transcript) > 4:
            if phrase_matches(transcript, STOP_COMMANDS):
                print("[Wake Listener] Stop command heard - ending manual session.")
                notifier.send_android_notification("Viciously", "Recording stopped.")
                beep(2)
                return

            analysis, advice = mediator.analyze_argument_and_deescalate(transcript)
            mediator.speak_advice(advice)
            mediator.save_encrypted_summary(analysis, advice)


def idle_gate_step():
    wav_path = record_probe_clip(duration_sec=SAMPLE_DURATION_SEC)
    if not wav_path:
        return

    rms = measure_rms(wav_path)
    loud = rms >= AMPLITUDE_RMS_THRESHOLD
    update_live_status(current_rms=rms)

    transcript = cheap_transcribe(wav_path) if not loud else ""
    if os.path.exists(wav_path):
        os.remove(wav_path)

    if loud:
        record_escalation_event(severity=3)
        update_live_status(current_rms=rms)
        run_full_pipeline(reason="loud/escalating voice", high_stress=True)
        return

    if transcript:
        if phrase_matches(transcript, START_COMMANDS):
            manual_session_loop()
            return

        matched = phrase_matches(transcript, WAKE_PHRASES)
        if matched:
            high_stress = matched in HIGH_STRESS_PHRASES
            record_escalation_event(severity=3 if high_stress else 1)
            update_live_status(current_rms=rms)
            run_full_pipeline(reason=f"wake phrase: '{matched}'", high_stress=high_stress)
            return


def idle_gate_loop():
    print("=== Wake Listener Active (idle gating mode) ===")
    while True:
        try:
            idle_gate_step()
            time.sleep(IDLE_POLL_INTERVAL_SEC)
        except Exception as e:
            print(f"[Wake Listener Loop Error]: {e}")
            time.sleep(IDLE_POLL_INTERVAL_SEC)


if __name__ == "__main__":
    idle_gate_loop()
