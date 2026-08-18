import os
import sqlite3
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.utils import platform

DB_PATH = os.path.expanduser("~/viciously/encrypted_mediator.db")

class MediatorUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=15, spacing=10, **kwargs)
        
        # Header Status
        self.status_label = Label(
            text="[b]Viciously Mediator Engine[/b]", 
            markup=True,
            font_size='22sp',
            size_hint_y=0.1
        )
        self.add_widget(self.status_label)
        
        # Control Buttons Area
        btn_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.15)
        
        self.start_btn = Button(text="Start Service", background_color=(0.2, 0.7, 0.3, 1))
        self.start_btn.bind(on_press=self.start_service)
        btn_layout.add_widget(self.start_btn)

        self.stop_btn = Button(text="Stop Service", background_color=(0.8, 0.2, 0.2, 1))
        self.stop_btn.bind(on_press=self.stop_service)
        btn_layout.add_widget(self.stop_btn)

        self.refresh_btn = Button(text="Refresh Logs", background_color=(0.3, 0.5, 0.8, 1))
        self.refresh_btn.bind(on_press=self.load_history)
        btn_layout.add_widget(self.refresh_btn)

        self.add_widget(btn_layout)

        # Scrollable Log Display Area
        self.scroll_view = ScrollView(size_hint=(1, 0.75))
        self.log_text = Label(
            text="Loading encrypted database history...", 
            markup=True,
            size_hint_y=None,
            halign='left',
            valign='top'
        )
        self.log_text.bind(texture_size=self.log_text.setter('size'))
        self.scroll_view.add_widget(self.log_text)
        self.add_widget(self.scroll_view)

        # Initial load of records
        self.load_history(None)

    def load_history(self, instance):
        """Reads recent summaries from the local database."""
        if not os.path.exists(DB_PATH):
            self.log_text.text = "No saved logs yet. Service is monitoring."
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, analysis_summary, spoken_advice FROM memories ORDER BY id DESC LIMIT 10")
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                self.log_text.text = "No de-escalation events recorded."
                return

            display_output = ""
            for row in rows:
                ts, summary, advice = row
                display_output += f"[color=00ff00]● Memory Event[/color]\n[b]Analysis:[/b] {summary}\n[b]Advice:[/b] {advice}\n-----------------------------------\n"
            
            self.log_text.text = display_output
        except Exception as e:
            self.log_text.text = f"Error reading encrypted storage: {e}"

    def start_service(self, instance):
        if platform == 'android':
            from android import AndroidService
            service = AndroidService('Viciously Engine', 'Monitoring in background...')
            service.start('service started')
            self.status_label.text = "[b]Status: Service Running[/b]"

    def stop_service(self, instance):
        if platform == 'android':
            from android import AndroidService
            service = AndroidService('Viciously Engine', 'Monitoring in background...')
            service.stop()
            self.status_label.text = "[b]Status: Service Stopped[/b]"

class ViciouslyApp(App):
    def build(self):
        return MediatorUI()

if __name__ == "__main__":
    ViciouslyApp().run()
