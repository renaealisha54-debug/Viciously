import threading
import time
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

# Import mediator logic
import mediator

class MediatorUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=20, spacing=10, **kwargs)
        
        self.status_label = Label(
            text="[ Status: Idle ]", 
            size_hint_y=0.1, 
            font_size='18sp'
        )
        self.add_widget(self.status_label)
        
        self.log_label = Label(
            text="Viciously Engine Initialized...\nReady to monitor conversation.",
            size_hint_y=None,
            font_size='14sp',
            halign='left',
            valign='top'
        )
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        
        scroll = ScrollView(size_hint=(1, 0.7))
        scroll.add_widget(self.log_label)
        self.add_widget(scroll)
        
        self.toggle_btn = Button(
            text="Start Mediator Engine", 
            size_hint_y=0.2, 
            font_size='18sp',
            background_color=(0.2, 0.7, 0.3, 1)
        )
        self.toggle_btn.bind(on_press=self.toggle_engine)
        self.add_widget(self.toggle_btn)
        
        self.running = False
        self.engine_thread = None

    def toggle_engine(self, instance):
        if not self.running:
            self.running = True
            self.status_label.text = "[ Status: Listening... ]"
            self.toggle_btn.text = "Stop Mediator Engine"
            self.toggle_btn.background_color = (0.8, 0.2, 0.2, 1)
            
            # Start background thread for audio analysis loop
            self.engine_thread = threading.Thread(target=self.run_engine, daemon=True)
            self.engine_thread.start()
        else:
            self.running = False
            self.status_label.text = "[ Status: Stopped ]"
            self.toggle_btn.text = "Start Mediator Engine"
            self.toggle_btn.background_color = (0.2, 0.7, 0.3, 1)

    def run_engine(self):
        # Call Android permission prompt
        mediator.check_and_request_permissions()
        
        while self.running:
            try:
                mediator.record_audio_chunk(duration_sec=7)
                transcript = mediator.transcribe_audio()
                
                if transcript and len(transcript) > 4 and "[BLANK_AUDIO]" not in transcript:
                    analysis, advice = mediator.analyze_argument_and_deescalate(transcript)
                    
                    # Update UI on main Kivy thread
                    Clock.schedule_once(lambda dt: self.update_log(f"Analysis: {analysis}\nAdvice: {advice}"))
                    
                    mediator.speak_advice(advice)
                    mediator.save_encrypted_summary(analysis, advice)
                else:
                    Clock.schedule_once(lambda dt: self.update_log("... Listening (silence/ambient) ..."))
            except Exception as e:
                Clock.schedule_once(lambda dt: self.update_log(f"Error: {e}"))
                
            time.sleep(1)

    def update_log(self, text):
        self.log_label.text += f"\n\n{text}"

class ViciouslyApp(App):
    def build(self):
        self.title = "Viciously Mediator"
        return MediatorUI()

if __name__ == "__main__":
    ViciouslyApp().run()
