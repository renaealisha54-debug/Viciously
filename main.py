import os
import requests
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from plyer import tts

# Native Android imports via Pyjnius
from kivy.utils import platform
if platform == 'android':
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    NotificationManager = autoclass('android.app.NotificationManager')
    NotificationChannel = autoclass('android.app.NotificationChannel')
    NotificationBuilder = autoclass('androidx.core.app.NotificationCompat$Builder')
    Context = autoclass('android.content.Context')

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

def start_foreground_notification():
    """Spawns an ongoing status notification so Android keeps the app active in RAM."""
    if platform != 'android':
        return

    try:
        activity = PythonActivity.mActivity
        channel_id = "viciously_mediator_channel"
        channel_name = "Viciously Service Channel"

        # Create Notification Channel (Android 8.0+)
        notification_service = activity.getSystemService(Context.NOTIFICATION_SERVICE)
        channel = NotificationChannel(
            channel_id, 
            channel_name, 
            NotificationManager.IMPORTANCE_LOW
        )
        notification_service.createNotificationChannel(channel)

        # Build Persistent Notification
        builder = NotificationBuilder(activity, channel_id)
        builder.setContentTitle("Viciously Voice Mediator")
        builder.setContentText("Active & monitoring for de-escalation triggers...")
        builder.setSmallIcon(activity.getApplicationInfo().icon)
        builder.setOngoing(True)

        # Notify Android
        notification = builder.build()
        notification_service.notify(1001, notification)
        print("[Android] Persistent Foreground Notification active.")
    except Exception as e:
        print(f"[Android Error] Failed to start notification: {e}")

def speak(text):
    try:
        tts.speak(text)
    except Exception:
        pass

class ViciouslyUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.add_widget(Label(text="Viciously Active in Background", font_size='20sp'))

class ViciouslyApp(App):
    def build(self):
        # Trigger foreground notification when application boots
        start_foreground_notification()
        return ViciouslyUI()

if __name__ == "__main__":
    ViciouslyApp().run()
