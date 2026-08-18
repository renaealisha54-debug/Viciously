import os
import sqlite3
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.spinner import Spinner
from kivy.uix.slider import Slider
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader
from kivy.graphics import Color, Rectangle
from kivy.utils import platform

DB_PATH = os.path.expanduser("~/viciously/encrypted_mediator.db")

class StyledTabbedPanel(TabbedPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        self.background_color = (0.08, 0.09, 0.11, 1) # Dark theme background

        # Dashboard Tab
        self.dashboard_tab = TabbedPanelHeader(text='Dashboard')
        self.dashboard_tab.content = self.build_dashboard()
        self.add_widget(self.dashboard_tab)

        # AI Settings Tab
        self.settings_tab = TabbedPanelHeader(text='AI Settings')
        self.settings_tab.content = self.build_settings()
        self.add_widget(self.settings_tab)

    def build_dashboard(self):
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        # Header Status Card
        status_card = BoxLayout(orientation='vertical', size_hint_y=0.18, padding=10)
        with status_card.canvas.before:
            Color(0.12, 0.15, 0.18, 1)
            self.rect1 = Rectangle(size=status_card.size, pos=status_card.pos)
        status_card.bind(size=self._update_rect1, pos=self._update_rect1)

        self.status_label = Label(
            text="[b][color=00ffcc]● ENGINE ACTIVE[/color][/b]\n[size=14sp]System Status: Monitoring Audio[/size]", 
            markup=True,
            halign='center'
        )
        status_card.add_widget(self.status_label)
        layout.add_widget(status_card)

        # Quick Actions
        btn_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.12)
        
        self.start_btn = Button(
            text="Start Service", 
            background_color=(0.1, 0.7, 0.4, 1),
            font_size='14sp',
            bold=True
        )
        self.start_btn.bind(on_press=self.start_service)
        btn_layout.add_widget(self.start_btn)

        self.stop_btn = Button(
            text="Stop Service", 
            background_color=(0.8, 0.2, 0.2, 1),
            font_size='14sp',
            bold=True
        )
        self.stop_btn.bind(on_press=self.stop_service)
        btn_layout.add_widget(self.stop_btn)

        self.refresh_btn = Button(
            text="Refresh Logs", 
            background_color=(0.2, 0.5, 0.8, 1),
            font_size='14sp'
        )
        self.refresh_btn.bind(on_press=self.load_history)
        btn_layout.add_widget(self.refresh_btn)

        layout.add_widget(btn_layout)

        # Scrollable Logs View
        scroll = ScrollView(size_hint=(1, 0.7))
        self.log_text = Label(
            text="Loading encrypted database history...", 
            markup=True,
            size_hint_y=None,
            halign='left',
            valign='top',
            padding=(10, 10)
        )
        self.log_text.bind(texture_size=self.log_text.setter('size'))
        scroll.add_widget(self.log_text)
        layout.add_widget(scroll)

        self.load_history(None)
        return layout

    def build_settings(self):
        layout = ScrollView(padding=15)
        grid = GridLayout(cols=1, spacing=15, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        # Title
        grid.add_widget(Label(
            text="[b][color=00ffcc]Engine & AI Preferences[/color][/b]", 
            markup=True, 
            font_size='18sp', 
            size_hint_y=None, 
            height=30
        ))

        # 1. AI Tone Selection
        grid.add_widget(Label(text="De-escalation Tone Mode:", size_hint_y=None, height=25, halign='left'))
        self.tone_spinner = Spinner(
            text='Empathetic & Calm',
            values=('Empathetic & Calm', 'Direct & Firm', 'Socratic & Neutral', 'Humorous'),
            size_hint_y=None,
            height=40,
            background_color=(0.2, 0.25, 0.3, 1)
        )
        grid.add_widget(self.tone_spinner)

        # 2. Mic Audio Sensitivity
        grid.add_widget(Label(text="Audio Trigger Sensitivity:", size_hint_y=None, height=25))
        self.sens_slider = Slider(min=1, max=10, value=7, size_hint_y=None, height=30)
        grid.add_widget(self.sens_slider)

        # 3. Speaker Diarization Switch
        diar_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        diar_layout.add_widget(Label(text="Enable Dual-Speaker Diarization:"))
        diar_layout.add_widget(Switch(active=True))
        grid.add_widget(diar_layout)

        # 4. Local AES Encryption Switch
        enc_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        enc_layout.add_widget(Label(text="Enforce AES-256 Memory Encryption:"))
        enc_layout.add_widget(Switch(active=True))
        grid.add_widget(enc_layout)

        # 5. Auto-Purge Retention Interval
        grid.add_widget(Label(text="Auto-Purge Data Retention:", size_hint_y=None, height=25))
        self.purge_spinner = Spinner(
            text='7 Days',
            values=('24 Hours', '3 Days', '7 Days', '30 Days', 'Never Save Logs'),
            size_hint_y=None,
            height=40,
            background_color=(0.2, 0.25, 0.3, 1)
        )
        grid.add_widget(self.purge_spinner)

        # Save Button
        save_btn = Button(
            text="Save AI Configurations", 
            size_hint_y=None, 
            height=45, 
            background_color=(0.0, 0.8, 0.6, 1),
            bold=True
        )
        grid.add_widget(save_btn)

        layout.add_widget(grid)
        return layout

    def _update_rect1(self, instance, value):
        self.rect1.pos = instance.pos
        self.rect1.size = instance.size

    def load_history(self, instance):
        if not os.path.exists(DB_PATH):
            self.log_text.text = "[color=888888]No saved logs yet. System actively listening.[/color]"
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, analysis_summary, spoken_advice FROM memories ORDER BY id DESC LIMIT 10")
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                self.log_text.text = "[color=888888]No de-escalation events recorded.[/color]"
                return

            display_output = ""
            for row in rows:
                ts, summary, advice = row
                display_output += f"[color=00ffcc]● Memory Event[/color]\n[b]Analysis:[/b] {summary}\n[b]Advice:[/b] {advice}\n[color=444444]-----------------------------------[/color]\n"
            
            self.log_text.text = display_output
        except Exception as e:
            self.log_text.text = f"Error reading database: {e}"

    def start_service(self, instance):
        if platform == 'android':
            from android import AndroidService
            service = AndroidService('Viciously Engine', 'Monitoring in background...')
            service.start('service started')
            self.status_label.text = "[b][color=00ffcc]● ENGINE ACTIVE[/color][/b]\n[size=14sp]Foreground Service Running[/size]"

    def stop_service(self, instance):
        if platform == 'android':
            from android import AndroidService
            service = AndroidService('Viciously Engine', 'Monitoring in background...')
            service.stop()
            self.status_label.text = "[b][color=ff3333]○ ENGINE PAUSED[/color][/b]\n[size=14sp]Foreground Service Stopped[/size]"

class ViciouslyApp(App):
    def build(self):
        return StyledTabbedPanel()

if __name__ == "__main__":
    ViciouslyApp().run()
