"""
wake_listener.py

Gating layer that sits in FRONT of the existing mediator pipeline
(mediator.record_audio_chunk -> transcribe_audio -> analyze_argument_and_deescalate).

Nothing here transcribes or saves audio on its own. It only decides WHEN
the existing (expensive) pipeline in mediator.py should run, based on:

  1. Amplitude / loud-voice detection (cheap, no ASR involved)
  2. Manual voice commands ("start recording" / "stop recording")
  3. Wake-word / escalation-phrase matching on short transcribed samples,
     using phonetic + fuzzy matching so near-miss transcriptions
     ("shut the duck up" etc.) still match.

All wake-word matches are INSTANT triggers (no tiering) - any single
match fires the full pipeline immediately.

Manual commands ("start recording" / "I'm recording") put the listener
into a continuous manual session (bypasses wake-word gating entirely,
records continuously) until "stop recording" or "recording off" is heard.
"""

import os
import time
import wave
import subprocess
import numpy as np
import jellyfish

import mediator
import notifier

BASE_DIR = os.path.expanduser("~/viciously")
SAMPLE_WAV = os.path.join(BASE_DIR, "wake_sample.wav")

# --- Escalation / wake-word phrases (instant trigger, phonetic+fuzzy matched) ---
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
]

# --- Manual override voice commands (separate from escalation triggers) ---
START_COMMANDS = ["start recording", "im recording"]
STOP_COMMANDS = ["stop recording", "recording off"]

# --- Tunables ---
AMPLITUDE_RMS_THRESHOLD = 4000       # tune from AI Settings tab; int16 RMS
SAMPLE_DURATION_SEC = 3.5             # short probe clip used for keyword spotting
IDLE_POLL_INTERVAL_SEC = 1.5         # gap between idle probes
FUZZY_MATCH_MAX_DISTANCE = 2         # ceiling only; actual max is length-scaled, see _max_distance_for

MAX_SKIPPABLE_WORDS = 1  # tolerate this many dropped filler words (e.g. "are") per phrase

# Phrase-side filler words that may be entirely absent from the transcript
# (e.g. "what are you doing" said as "what you doing") without breaking a match.
OPTIONAL_PHRASE_FILLERS = {"are", "a", "an", "the", "to", "is", "did", "you're", "youre"}


def _normalize(text):
    return "".join(ch for ch in text.lower().strip() if ch.isalnum() or ch.isspace())


def _max_distance_for(word):
    """
    Scale allowed edit distance by word length so short words don't
    fuzzy-match unrelated short words (e.g. 'hoe' vs 'you' is only
    2 edits apart, which is meaningless at 3 letters).
    """
    length = len(word)
    if length <= 3:
        return 0   # short words (hoe, dum, cunt, stop) must match exactly or phonetically
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


def phrase_matches(transcript, phrase_list):
    """
    Phonetic + fuzzy match: checks whether transcript contains, in order,
    a word for each word in a phrase (allowing a small number of filler
    words to be skipped/dropped, e.g. "what you doing" for "what are you
    doing"), where each matched pair is either identical, phonetically
    close (Double Metaphone), or a small edit-distance apart. Returns the
    matched phrase, or None.
    """
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


def _subsequence_matches_phrase(transcript_words, start, phrase_words):
    """
    Walks transcript_words from `start`, matching each phrase word in order.
    - Allows skipping up to MAX_SKIPPABLE_WORDS transcript words between
      matches (extra words the speaker said that aren't part of the phrase).
    - Allows phrase-side filler words (OPTIONAL_PHRASE_FILLERS) to be
      entirely absent from the transcript (e.g. "are" dropped in
      "what [are] you doing").
    At least one non-filler phrase word must still be matched for a hit.
    """
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
    """Records a short probe clip for amplitude + keyword checks. Deletes itself when read."""
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
    """Cheap amplitude check - no ASR involved."""
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


def cheap_transcribe(wav_path):
    """Runs whisper.cpp on the short probe clip only (not the full 7s chunk)."""
    cmd = [mediator.WHISPER_PATH, "-m", mediator.MODEL_PATH, "-f", wav_path, "-nt", "-otxt"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    txt_path = wav_path + ".txt"
    text = ""
    if os.path.exists(txt_path):
        with open(txt_path, "r") as f:
            text = f.read().strip()
        os.remove(txt_path)
    return text


def announce_trigger(reason):
    """Consent signal: fires only when the real pipeline is about to run."""
    notifier.send_android_notification("Viciously Active", f"Recording started ({reason}).")
    mediator.speak_advice("Recording started.")


def run_full_pipeline(reason):
    announce_trigger(reason)
    mediator.record_audio_chunk(duration_sec=7)
    transcript = mediator.transcribe_audio()
    if transcript and len(transcript) > 4 and "[BLANK_AUDIO]" not in transcript:
        analysis, advice = mediator.analyze_argument_and_deescalate(transcript)
        mediator.speak_advice(advice)
        mediator.save_encrypted_summary(analysis, advice)


def manual_session_loop():
    """Continuous recording session, active until a stop command is heard."""
    print("[Wake Listener] Manual recording session started.")
    notifier.send_android_notification("Viciously Active", "Manual recording session started.")
    mediator.speak_advice("Recording.")

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
                mediator.speak_advice("Recording stopped.")
                return

            analysis, advice = mediator.analyze_argument_and_deescalate(transcript)
            mediator.speak_advice(advice)
            mediator.save_encrypted_summary(analysis, advice)


def idle_gate_loop():
    """
    Main idle loop: short cheap probes, gated on amplitude and/or wake phrases.
    Any match (amplitude OR phrase) is an instant trigger of the full pipeline.
    A manual "start recording" command switches into manual_session_loop().
    """
    print("=== Wake Listener Active (idle gating mode) ===")
    while True:
        try:
            wav_path = record_probe_clip(duration_sec=SAMPLE_DURATION_SEC)
            if not wav_path:
                time.sleep(IDLE_POLL_INTERVAL_SEC)
                continue

            rms = measure_rms(wav_path)
            loud = rms >= AMPLITUDE_RMS_THRESHOLD

            transcript = cheap_transcribe(wav_path) if not loud else ""
            if os.path.exists(wav_path):
                os.remove(wav_path)

            if loud:
                run_full_pipeline(reason="loud/escalating voice")
                continue

            if transcript:
                if phrase_matches(transcript, START_COMMANDS):
                    manual_session_loop()
                    continue

                matched = phrase_matches(transcript, WAKE_PHRASES)
                if matched:
                    run_full_pipeline(reason=f"wake phrase: '{matched}'")
                    continue

            time.sleep(IDLE_POLL_INTERVAL_SEC)

        except Exception as e:
            print(f"[Wake Listener Loop Error]: {e}")
            time.sleep(IDLE_POLL_INTERVAL_SEC)


if __name__ == "__main__":
    idle_gate_loop()
