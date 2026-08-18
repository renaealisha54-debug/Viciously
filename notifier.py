import subprocess
from kivy.utils import platform

def send_android_notification(title, message):
    """Triggers native Android notification bar alert."""
    print(f"[Notification Alert] {title}: {message}")
    
    # Termux API fallback
    try:
        subprocess.run([
            "termux-notification", 
            "--title", title, 
            "--content", message,
            "--priority", "high"
        ], check=True)
    except Exception:
        pass

    # Android Native PyJnius wrapper (for APK runtime)
    if platform == 'android':
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            NotificationBuilder = autoclass('android.app.Notification$Builder')
            Context = autoclass('android.content.Context')
            
            activity = PythonActivity.mActivity
            notification_service = activity.getSystemService(Context.NOTIFICATION_SERVICE)
            
            builder = NotificationBuilder(activity)
            builder.setContentTitle(title)
            builder.setContentText(message)
            builder.setSmallIcon(activity.getApplicationInfo().icon)
            
            notification_service.notify(1, builder.build())
        except Exception as e:
            print(f"[Native Notification Error]: {e}")

if __name__ == "__main__":
    send_android_notification("Mediator Active", "Monitoring for peaceful resolution.")
