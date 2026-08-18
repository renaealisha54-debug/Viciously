import time
import os
from android.runnable import run_on_ui_thread
from jnius import autoclass

# Import your existing mediator logic
import mediator

# Java/Android Native API Bindings via PyJnius
PythonService = autoclass('org.kivy.android.PythonService')
Context = autoclass('android.content.Context')
AudioManager = autoclass('android.media.AudioManager')

def request_audio_focus():
    """Handles Android Audio Focus so recording doesn't crash during phone calls."""
    try:
        activity = PythonService.mService
        audio_service = activity.getSystemService(Context.AUDIO_SERVICE)
        # Request temporary audio focus
        result = audio_service.requestAudioFocus(
            None, 
            AudioManager.STREAM_MUSIC, 
            AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK
        )
        return result == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
    except Exception as e:
        print(f"[Service Warning] Audio focus check skipped: {e}")
        return True

def run_foreground_loop():
    """Continuous listening loop running in the Android Foreground Service."""
    print("=== Viciously Foreground Service Started ===")
    
    while True:
        try:
            # Check if phone call or external audio took focus
            if request_audio_focus():
                mediator.record_audio_chunk(duration_sec=7)
                transcript = mediator.transcribe_audio()
                
                if transcript and len(transcript) > 4 and "[BLANK_AUDIO]" not in transcript:
                    analysis, advice = mediator.analyze_argument_and_deescalate(transcript)
                    mediator.speak_advice(advice)
                    mediator.save_encrypted_summary(analysis, advice)
            else:
                print("[Service] Audio focus lost (e.g., incoming call). Pausing cycle.")
                
        except Exception as e:
            print(f"[Service Loop Error]: {e}")
            
        time.sleep(2)

if __name__ == "__main__":
    run_foreground_loop()
