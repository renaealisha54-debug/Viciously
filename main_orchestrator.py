import os
import time
import mediator
import secure_db
import whisper_engine
import speaker_id
import prune_logs
import notifier

def run_pipeline_cycle():
    """Executes a full 360-degree mediation and privacy cycle."""
    print("\n--- [Orchestrator Cycle Active] ---")
    
    # 1. Enforce privacy retention (purge > 7 days)
    prune_logs.enforce_privacy_retention()
    
    # 2. Record audio chunk
    mediator.record_audio_chunk(duration_sec=7)
    
    # 3. Transcribe & instant-purge raw audio
    transcript = whisper_engine.process_audio_to_text(mediator.WAV_AUDIO)
    
    if transcript and len(transcript) > 4 and "[BLANK_AUDIO]" not in transcript:
        # 4. Profile speaker dynamics (Speaker A vs Speaker B)
        speaker_tag = speaker_id.analyze_speaker_profile(mediator.WAV_AUDIO)
        print(f"[Speaker Identified]: {speaker_tag}")
        
        # 5. Generate analysis & de-escalation advice
        analysis, advice = mediator.analyze_argument_and_deescalate(transcript)
        
        # 6. Push native notification alert & speak aloud
        notifier.send_android_notification("Viciously De-escalation", advice)
        mediator.speak_advice(advice)
        
        # 7. Store encrypted summary (no raw transcripts)
        secure_db.init_secure_db()
        mediator.save_encrypted_summary(f"[{speaker_tag}] {analysis}", advice)
    else:
        print("[Status] Quiet environment — raw buffers cleared.")

if __name__ == "__main__":
    print("=== Viciously Engine Orchestrator Ready ===")
    try:
        while True:
            run_pipeline_cycle()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Orchestrator Stopped]")
