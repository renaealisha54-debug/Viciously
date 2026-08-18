import wave
import audioop
import os

def compress_to_16k_mono(input_wav_path, output_wav_path):
    """
    Downsamples any input WAV file to 16000Hz PCM Mono.
    This reduces file footprint and CPU processing load for Whisper C++.
    """
    if not os.path.exists(input_wav_path):
        print("[Compressor Error] Input file does not exist.")
        return False

    try:
        with wave.open(input_wav_path, 'rb') as in_wave:
            n_channels = in_wave.getnchannels()
            sample_width = in_wave.getsampwidth()
            framerate = in_wave.getframerate()
            n_frames = in_wave.getnframes()
            
            raw_data = in_wave.readframes(n_frames)

        # 1. Convert Stereo to Mono if needed
        if n_channels > 1:
            raw_data = audioop.tomono(raw_data, sample_width, 1, 1)

        # 2. Resample to 16000Hz if needed
        target_rate = 16000
        if framerate != target_rate:
            raw_data, _ = audioop.ratecv(raw_data, sample_width, 1, framerate, target_rate, None)

        # 3. Write compressed 16kHz mono audio chunk
        with wave.open(output_wav_path, 'wb') as out_wave:
            out_wave.setnchannels(1)
            out_wave.setsampwidth(sample_width)
            out_wave.setframerate(target_rate)
            out_wave.writeframes(raw_data)

        print(f"[Audio Stream] Compressed {input_wav_path} -> 16kHz Mono ({output_wav_path})")
        return True

    except Exception as e:
        print(f"[Compressor Exception]: {e}")
        return False

if __name__ == "__main__":
    print("[Audio Compressor Module Loaded]")
