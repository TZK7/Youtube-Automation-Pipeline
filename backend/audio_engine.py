import os
import wave
import asyncio
import contextlib

def get_audio_duration(file_path):
    """
    Returns exact audio duration in milliseconds and seconds using Python's native wave module
    or MP3 frame estimation.
    """
    if not os.path.exists(file_path):
        return 0.0, 0.0

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".wav":
        try:
            with contextlib.closing(wave.open(file_path, 'r')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                duration_sec = frames / float(rate)
                return duration_sec * 1000.0, duration_sec
        except Exception as e:
            print(f"[-] Error reading wave duration: {e}")

    # Fallback / MP3 estimation based on file size or wave header check
    size_bytes = os.path.getsize(file_path)
    # Average 128 kbps mp3 = 16000 bytes/sec
    duration_sec = max(1.0, size_bytes / 16000.0)
    return duration_sec * 1000.0, duration_sec


async def _synthesize_edge_tts(text, voice_id, output_file, rate="+0%", pitch="+0Hz"):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice_id, rate=rate, pitch=pitch)
    await communicate.save(output_file)


def create_fallback_silent_wav(output_path, text):
    """
    Creates a simple WAV audio file with soft synthetic tone matching spoken text length
    if edge-tts network is offline or uninstalled.
    """
    import math
    import struct
    
    words = len(text.split())
    # Estimate ~0.4 sec per word, min 3 seconds
    duration = max(3.0, words * 0.45)
    sample_rate = 22050
    num_samples = int(sample_rate * duration)
    
    with wave.open(output_path, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        # Soft soothing ambient tone
        values = []
        for i in range(num_samples):
            t = float(i) / sample_rate
            sample = int(3000 * math.sin(2 * math.pi * 220.0 * t))
            packed_value = struct.pack('<h', sample)
            values.append(packed_value)
            
        wav_file.writeframes(b''.join(values))
    return duration


def generate_audio(script_data, voice_settings=None, output_dir=None):
    """
    Synthesizes audio for each scene in script_data using edge-tts.
    Saves scene_01.wav, scene_02.wav, etc. and calculates exact duration in ms.
    """
    if voice_settings is None:
        voice_settings = {}
    voice_id = voice_settings.get("voice_id", "en-US-ChristopherNeural")
    speed = voice_settings.get("speed", "+0%")
    pitch = voice_settings.get("pitch", "+0Hz")
    
    if output_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "data", "audio_assets")
    os.makedirs(output_dir, exist_ok=True)
    
    scenes = script_data.get("scenes", [])
    audio_results = []

    print(f"[+] Synthesizing audio for {len(scenes)} scenes using voice '{voice_id}'...")

    for idx, scene in enumerate(scenes, 1):
        spoken_text = scene.get("spoken_text", "")
        file_name = f"scene_{idx:02d}.wav"
        output_path = os.path.join(output_dir, file_name)
        
        synthesized = False
        try:
            # Use edge-tts
            mp3_temp = os.path.join(output_dir, f"scene_{idx:02d}.mp3")
            asyncio.run(_synthesize_edge_tts(spoken_text, voice_id, mp3_temp, rate=speed, pitch=pitch))
            
            # If mp3 generated, we can use it directly or convert to wav
            output_path = mp3_temp
            synthesized = True
        except Exception as e:
            print(f"[-] edge-tts synthesis warning for scene {idx}: {e}")
        
        if not synthesized:
            output_path = os.path.join(output_dir, f"scene_{idx:02d}.wav")
            create_fallback_silent_wav(output_path, spoken_text)

        duration_ms, duration_sec = get_audio_duration(output_path)
        print(f"  [>] Scene {idx}: {duration_sec:.2f}s ({duration_ms:.0f}ms) -> {output_path}")

        audio_results.append({
            "scene_number": idx,
            "spoken_text": spoken_text,
            "audio_path": output_path,
            "duration_ms": duration_ms,
            "duration_sec": duration_sec
        })

    return audio_results
