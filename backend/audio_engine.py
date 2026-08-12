import os
import wave
import asyncio
import contextlib
import time
import requests


def get_audio_duration(file_path):
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

    size_bytes = os.path.getsize(file_path)
    duration_sec = max(1.0, size_bytes / 16000.0)
    return duration_sec * 1000.0, duration_sec


def _synthesize_fish_audio(text, voice_id, output_file, api_key):
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
    import math
    import struct

    words = len(text.split())
    duration = max(3.0, words * 0.45)
    sample_rate = 22050
    num_samples = int(sample_rate * duration)

    with wave.open(output_path, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        values = []
        for i in range(num_samples):
            t = float(i) / sample_rate
            sample = int(3000 * math.sin(2 * math.pi * 220.0 * t))
            packed_value = struct.pack('<h', sample)
            values.append(packed_value)

        wav_file.writeframes(b''.join(values))
    return duration


def generate_audio_scene(scene_data, scene_idx, voice_settings, output_dir, session_id=None):
    """Generates audio for a single scene. Returns a result dict."""
    if voice_settings is None:
        voice_settings = {}

    openrouter_api_key = voice_settings.get("openrouter_api_key", "")
    tts_model = voice_settings.get("tts_model", "edge-tts")
    voice_id = voice_settings.get("voice_id", "en-US-ChristopherNeural")
    fish_voice = voice_settings.get("fish_voice_id", "alloy")
    speed = voice_settings.get("speed", "+0%")
    pitch = voice_settings.get("pitch", "+0Hz")

    os.makedirs(output_dir, exist_ok=True)

    spoken_text = scene_data.get("spoken_text", "")
    output_path = None
    synthesized = False
    engine_used = "unknown"
    api_start = time.time()

    use_fish = (tts_model == "fish-audio" or tts_model == "Fish Audio (OpenRouter)") and openrouter_api_key
    use_edge = tts_model in ("edge-tts", "")

    if use_fish:
        mp3_path = os.path.join(output_dir, f"scene_{scene_idx:02d}.mp3")
        print(f"  [>] Scene {scene_idx}: Trying Fish Audio TTS (voice: {fish_voice})...")
        if _synthesize_fish_audio(spoken_text, fish_voice, mp3_path, openrouter_api_key):
            output_path = mp3_path
            synthesized = True
            engine_used = f"Fish Audio ({fish_voice})"

    if not synthesized and (use_edge or not synthesized):
        try:
            mp3_path = os.path.join(output_dir, f"scene_{scene_idx:02d}.mp3")
            print(f"  [>] Scene {scene_idx}: Trying edge-tts (voice: {voice_id})...")
            asyncio.run(_synthesize_edge_tts(spoken_text, voice_id, mp3_path, rate=speed, pitch=pitch))
            output_path = mp3_path
            synthesized = True
            engine_used = f"Edge TTS ({voice_id})"
        except Exception as e:
            print(f"  [-] edge-tts synthesis warning for scene {scene_idx}: {e}")

    if not synthesized:
        output_path = os.path.join(output_dir, f"scene_{scene_idx:02d}.wav")
        print(f"  [>] Scene {scene_idx}: Using silent WAV fallback...")
        create_fallback_silent_wav(output_path, spoken_text)
        engine_used = "Silent WAV Fallback"

    api_duration = time.time() - api_start
    duration_ms, duration_sec = get_audio_duration(output_path)
    print(f"  [>] Scene {scene_idx}: {duration_sec:.2f}s ({engine_used}, API: {api_duration:.1f}s) -> {output_path}")

    result = {
        "scene_number": scene_idx,
        "spoken_text": spoken_text,
        "audio_path": output_path,
        "duration_ms": duration_ms,
        "duration_sec": duration_sec,
        "engine_used": engine_used,
        "api_duration_sec": round(api_duration, 2),
        "status": "SUCCESS" if synthesized else "FALLBACK"
    }

    if session_id:
        try:
            from backend.session_manager import SessionManager
            sm = SessionManager()
            sm.log_api_call(
                session_id=session_id,
                step=f"AUDIO_TTS_SCENE_{scene_idx:02d}",
                service=engine_used,
                request_data={
                    "scene_number": scene_idx,
                    "spoken_text": spoken_text,
                    "tts_model": tts_model,
                    "voice_id": fish_voice if use_fish else voice_id
                },
                response_data={
                    "status": result["status"],
                    "audio_path": output_path,
                    "duration_sec": round(duration_sec, 2),
                    "api_duration_sec": round(api_duration, 2),
                    "file_size_bytes": os.path.getsize(output_path) if os.path.exists(output_path) else 0
                },
                status=result["status"],
                duration_sec=round(api_duration, 2)
            )
            sm.increment_counter(session_id, "audio_count")
        except Exception as e_sm:
            print(f"[-] Session logging warning for audio scene {scene_idx}: {e_sm}")

    return result


def generate_audio(script_data, voice_settings=None, output_dir=None, session_id=None):
    if voice_settings is None:
        voice_settings = {}

    if output_dir is None:
        if session_id:
            from backend.session_manager import SessionManager
            sm = SessionManager()
            output_dir = os.path.join(sm.get_session_dir(session_id), "audio_assets")
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(base_dir, "data", "audio_assets")
    os.makedirs(output_dir, exist_ok=True)

    scenes = script_data.get("scenes", [])
    audio_results = []

    tts_model = voice_settings.get("tts_model", "edge-tts")
    print(f"[+] Synthesizing audio for {len(scenes)} scenes (engine: {tts_model})...")

    for idx, scene in enumerate(scenes, 1):
        existing_mp3 = os.path.join(output_dir, f"scene_{idx:02d}.mp3")
        existing_wav = os.path.join(output_dir, f"scene_{idx:02d}.wav")
        if os.path.exists(existing_mp3) and os.path.getsize(existing_mp3) > 100:
            print(f"  [>] Scene {idx}: Reusing existing audio -> {existing_mp3}")
            duration_ms, duration_sec = get_audio_duration(existing_mp3)
            audio_results.append({
                "scene_number": idx,
                "spoken_text": scene.get("spoken_text", ""),
                "audio_path": existing_mp3,
                "duration_ms": duration_ms,
                "duration_sec": duration_sec,
                "engine_used": "cached",
                "api_duration_sec": 0.0,
                "status": "CACHED"
            })
            continue
        if os.path.exists(existing_wav) and os.path.getsize(existing_wav) > 100:
            print(f"  [>] Scene {idx}: Reusing existing audio -> {existing_wav}")
            duration_ms, duration_sec = get_audio_duration(existing_wav)
            audio_results.append({
                "scene_number": idx,
                "spoken_text": scene.get("spoken_text", ""),
                "audio_path": existing_wav,
                "duration_ms": duration_ms,
                "duration_sec": duration_sec,
                "engine_used": "cached",
                "api_duration_sec": 0.0,
                "status": "CACHED"
            })
            continue

        result = generate_audio_scene(scene, idx, voice_settings, output_dir, session_id)
        audio_results.append(result)

    s_id = session_id
    if s_id:
        try:
            from backend.session_manager import SessionManager
            sm = SessionManager()
            sm.save_checkpoint(s_id, "audio_assets", audio_results)

            cached = sum(1 for a in audio_results if a["status"] == "CACHED")
            generated = sum(1 for a in audio_results if a["status"] == "SUCCESS")
            fallback = sum(1 for a in audio_results if a["status"] == "FALLBACK")

            sm.log_api_call(
                session_id=s_id,
                step="AUDIO_SYNTHESIS_SUMMARY",
                service=voice_settings.get("tts_model", "edge-tts"),
                request_data={"total_scenes": len(scenes)},
                response_data={
                    "status": "SUCCESS" if fallback == 0 else "PARTIAL",
                    "generated_count": generated,
                    "cached_count": cached,
                    "fallback_count": fallback,
                    "total_duration_sec": round(sum(a["duration_sec"] for a in audio_results), 2),
                    "total_api_duration_sec": round(sum(a["api_duration_sec"] for a in audio_results), 2)
                },
                status="SUCCESS" if fallback == 0 else "PARTIAL",
                duration_sec=round(sum(a["api_duration_sec"] for a in audio_results), 2)
            )
        except Exception as e_sm:
            print(f"[-] Session logging warning for audio summary: {e_sm}")

    return audio_results
