import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.utils import platform

class MediatorUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=20, spacing=15, **kwargs)
        
        self.status_label = Label(
            text="Viciously Mediator\nForeground Service Manager", 
            font_size='20sp',
            halign='center'
        )
        self.add_widget(self.status_label)
        
        # Battery Optimization Button
        self.battery_btn = Button(
            text="Disable Battery Optimization (Doze)", 
            size_hint_y=0.2,
            background_color=(0.2, 0.5, 0.8, 1)
        )
        self.battery_btn.bind(on_press=self.request_battery_optimization_exemption)
        self.add_widget(self.battery_btn)

        # Service Control Buttons
        self.start_btn = Button(
            text="Start Foreground Service", 
            size_hint_y=0.2,
            background_color=(0.2, 0.7, 0.3, 1)
        )
        self.start_btn.bind(on_press=self.start_service)
        self.add_widget(self.start_btn)

        self.stop_btn = Button(
            text="Stop Foreground Service", 
            size_hint_y=0.2,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        self.stop_btn.bind(on_press=self.stop_service)
        self.add_widget(self.stop_btn)

    def request_battery_optimization_exemption(self, instance):
        """Requests Android OS to exclude this app from Doze mode killing."""
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                Settings = autoclass('android.provider.Settings')
                Uri = autoclass('android.net.Uri')
                
                activity = PythonActivity.mActivity
                package_name = activity.getPackageName()
                
                intent = Intent()
                intent.setAction(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                intent.setData(Uri.parse(f"package:{package_name}"))
                activity.startActivity(intent)
            except Exception as e:
                print(f"[Battery Settings Error]: {e}")

    def start_service(self, instance):
        if platform == 'android':
            from android import AndroidService
            service = AndroidService('Viciously Engine', 'Running in background...')
            service.start('service started')
            self.status_label.text = "Status: Service Active in Background"

    def stop_service(self, instance):
        if platform == 'android':
            from android import AndroidService
            service = AndroidService('Viciously Engine', 'Running in background...')
            service.stop()
            self.status_label.text = "Status: Service Stopped"

class ViciouslyApp(App):
    def build(self):
        return MediatorUI()

if __name__ == "__main__":
    ViciouslyApp().run()
