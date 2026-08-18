from kivy.utils import platform

class AndroidJNIBridge:
    def __init__(self):
        self.is_android = (platform == 'android')
        if self.is_android:
            try:
                from jnius import autoclass
                self.PythonActivity = autoclass('org.kivy.android.PythonActivity')
                self.Context = autoclass('android.content.Context')
                self.PowerManager = autoclass('android.os.PowerManager')
                self.AudioManager = autoclass('android.media.AudioManager')
                print("[JNI Bridge] Native Android Java interfaces successfully bound.")
            except Exception as e:
                print(f"[JNI Bridge Init Warning]: {e}")
                self.is_android = False

    def is_screen_active(self):
        """Checks if device screen is on without waking up CPU unnecessarily."""
        if not self.is_android:
            return True
        try:
            activity = self.PythonActivity.mActivity
            power_service = activity.getSystemService(self.Context.POWER_SERVICE)
            return power_service.isInteractive()
        except Exception as e:
            print(f"[JNI Screen Check Error]: {e}")
            return True

    def is_call_active(self):
        """Detects if phone is currently on an active call to avoid audio device conflicts."""
        if not self.is_android:
            return False
        try:
            activity = self.PythonActivity.mActivity
            audio_service = activity.getSystemService(self.Context.AUDIO_SERVICE)
            mode = audio_service.getMode()
            # MODE_IN_CALL (2) or MODE_IN_COMMUNICATION (3)
            return mode in [2, 3]
        except Exception as e:
            print(f"[JNI Call Check Error]: {e}")
            return False

if __name__ == "__main__":
    bridge = AndroidJNIBridge()
    print(f"JNI Active: {bridge.is_android}")
