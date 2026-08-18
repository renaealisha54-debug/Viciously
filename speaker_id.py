import wave
import numpy as np
import os

def analyze_speaker_profile(wav_path):
    """
    Extracts audio energy and approximate pitch to tag speakers 
    as Speaker A or Speaker B without external cloud APIs.
    """
    if not os.path.exists(wav_path):
        return "Unknown Speaker"
        
    try:
        with wave.open(wav_path, 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            signal = np.frombuffer(frames, dtype=np.int16)
            
            if len(signal) == 0:
                return "Unknown"

            # Calculate Root Mean Square (Energy) & Zero Crossing Rate
            rms = np.sqrt(np.mean(signal.astype(float)**2))
            zero_crossings = np.nonzero(np.diff(signal > 0))[0]
            zcr = len(zero_crossings) / float(len(signal))
            
            # Simple heuristic split based on pitch frequency profile
            if zcr > 0.12:
                return "Speaker A (Higher Pitch/Dynamic)"
            else:
                return "Speaker B (Lower Pitch/Steady)"
    except Exception as e:
        print(f"[Speaker ID Warning]: {e}")
        return "Unassigned Speaker"

if __name__ == "__main__":
    print("[Speaker Profile Engine Loaded]")
