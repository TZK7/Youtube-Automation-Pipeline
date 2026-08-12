import os
import wave
import asyncio
import contextlib
import requests

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


def _synthesize_fish_audio(text, voice_id, output_file, api_key):
    """
    Synthesizes speech using Fish Audio via OpenRouter API.
    Returns True on success, False on failure.
    The response is a raw binary MP3 audio stream.
    """
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://youtube-automation-pipeline.local",
                "X-Title": "YouTube Automation Pipeline"
            },
            json={
                "model": "fish-audio/s2.1-pro-free:free",
                "input": text,
                "voice": voice_id or "alloy",
                "response_format": "mp3"
            },
            timeout=60
        )
        if resp.status_code == 200 and len(resp.content) > 100:
            with open(output_file, "wb") as f:
                f.write(resp.content)
            print(f"    [+] Fish Audio TTS success: {len(resp.content)} bytes")
            return True
        else:
            print(f"    [-] Fish Audio TTS returned status {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"    [-] Fish Audio TTS error: {e}")
        return False


async def _synthesize_edge_tts(text, voice_id, output_file, rate="+0%", pitch="+0Hz"):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice_id, rate=rate, pitch=pitch)
    await communicate.save(output_file)


def create_fallback_silent_wav(output_path, text):
    """
    Creates a simple WAV audio file with soft synthetic tone matching spoken text length
    if all TTS engines are offline or unavailable.
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
    Synthesizes audio for each scene in script_data.
    
    Priority order:
      1. Fish Audio via OpenRouter (if openrouter_api_key provided)
      2. Edge TTS (Microsoft, free)
      3. Silent WAV fallback (offline)
    
    Saves scene_01.mp3 (or .wav) and calculates exact duration in ms.
    """
    if voice_settings is None:
        voice_settings = {}
    
    # OpenRouter API key for Fish Audio
    openrouter_api_key = voice_settings.get("openrouter_api_key", "")
    
    # Edge TTS settings (fallback)
    voice_id = voice_settings.get("voice_id", "en-US-ChristopherNeural")
    fish_voice = voice_settings.get("fish_voice_id", "alloy")
    speed = voice_settings.get("speed", "+0%")
    pitch = voice_settings.get("pitch", "+0Hz")
    
    if output_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "data", "audio_assets")
    os.makedirs(output_dir, exist_ok=True)
    
    scenes = script_data.get("scenes", [])
    audio_results = []

    # Determine which engine we'll use
    if openrouter_api_key:
        print(f"[+] Synthesizing audio for {len(scenes)} scenes using Fish Audio (OpenRouter)...")
    else:
        print(f"[+] Synthesizing audio for {len(scenes)} scenes using edge-tts voice '{voice_id}'...")

    for idx, scene in enumerate(scenes, 1):
        spoken_text = scene.get("spoken_text", "")
        output_path = None
        synthesized = False
        
        # --- Priority 1: Fish Audio via OpenRouter ---
        if openrouter_api_key and not synthesized:
            mp3_path = os.path.join(output_dir, f"scene_{idx:02d}.mp3")
            print(f"  [>] Scene {idx}: Trying Fish Audio TTS...")
            if _synthesize_fish_audio(spoken_text, fish_voice, mp3_path, openrouter_api_key):
                output_path = mp3_path
                synthesized = True

        # --- Priority 2: Edge TTS (Microsoft) ---
        if not synthesized:
            try:
                mp3_path = os.path.join(output_dir, f"scene_{idx:02d}.mp3")
                print(f"  [>] Scene {idx}: Trying edge-tts...")
                asyncio.run(_synthesize_edge_tts(spoken_text, voice_id, mp3_path, rate=speed, pitch=pitch))
                output_path = mp3_path
                synthesized = True
            except Exception as e:
                print(f"  [-] edge-tts synthesis warning for scene {idx}: {e}")
        
        # --- Priority 3: Silent WAV fallback ---
        if not synthesized:
            output_path = os.path.join(output_dir, f"scene_{idx:02d}.wav")
            print(f"  [>] Scene {idx}: Using silent WAV fallback...")
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
