import os
import time
import mediator
import secure_db
import whisper_engine
import speaker_id
import prune_logs
import notifier
import audio_compressor

COMPRESSED_AUDIO = os.path.expanduser("~/viciously/temp_16k.wav")

def run_pipeline_cycle():
    print("\n--- [Orchestrator Cycle Active] ---")
    
    # 1. Enforce privacy retention (purge > 7 days)
    prune_logs.enforce_privacy_retention()
    
    # 2. Record raw audio chunk
    mediator.record_audio_chunk(duration_sec=7)
    
    # 3. Downsample & compress audio stream to 16kHz Mono
    if os.path.exists(mediator.WAV_AUDIO):
        success = audio_compressor.compress_to_16k_mono(mediator.WAV_AUDIO, COMPRESSED_AUDIO)
        working_file = COMPRESSED_AUDIO if success else mediator.WAV_AUDIO
    else:
        working_file = mediator.WAV_AUDIO

    # 4. Transcribe optimized stream & instant-purge raw audio
    transcript = whisper_engine.process_audio_to_text(working_file)
    
    if transcript and len(transcript) > 4 and "[BLANK_AUDIO]" not in transcript:
        # 5. Profile speaker dynamics
        speaker_tag = speaker_id.analyze_speaker_profile(working_file)
        print(f"[Speaker Identified]: {speaker_tag}")
        
        # 6. Generate de-escalation advice
        analysis, advice = mediator.analyze_argument_and_deescalate(transcript)
        
        # 7. Push alert & speak
        notifier.send_android_notification("Viciously De-escalation", advice)
        mediator.speak_advice(advice)
        
        # 8. Store encrypted summary
        secure_db.init_secure_db()
        mediator.save_encrypted_summary(f"[{speaker_tag}] {analysis}", advice)
    else:
        print("[Status] Quiet environment — buffers cleared.")

    # Clean up temporary compressed file
    if os.path.exists(COMPRESSED_AUDIO):
        os.remove(COMPRESSED_AUDIO)

if __name__ == "__main__":
    print("=== Viciously Engine Orchestrator Ready (Audio Stream Optimized) ===")
    try:
        while True:
            run_pipeline_cycle()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Orchestrator Stopped]")
