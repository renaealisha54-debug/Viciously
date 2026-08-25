import time
import os
from android.runnable import run_on_ui_thread
from jnius import autoclass

import wake_listener

PythonService = autoclass('org.kivy.android.PythonService')
Context = autoclass('android.content.Context')
AudioManager = autoclass('android.media.AudioManager')

def request_audio_focus():
    """Handles Android Audio Focus so recording doesn't crash during phone calls."""
    try:
        activity = PythonService.mService
        audio_service = activity.getSystemService(Context.AUDIO_SERVICE)
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
    """
    Continuous gating loop running in the Android Foreground Service.
    Each cycle is a single wake_listener probe - the expensive mediator
    pipeline only runs when wake_listener actually triggers it.
    """
    print("=== Viciously Foreground Service Started (wake-word gating mode) ===")

    while True:
        try:
            if request_audio_focus():
                wake_listener.idle_gate_step()
            else:
                print("[Service] Audio focus lost (e.g., incoming call). Pausing cycle.")
        except Exception as e:
            print(f"[Service Loop Error]: {e}")

        time.sleep(wake_listener.IDLE_POLL_INTERVAL_SEC)

if __name__ == "__main__":
    run_foreground_loop()
