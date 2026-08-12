import os
import math
import time
import base64
import requests
from PIL import Image, ImageDraw, ImageFont


def _generate_grok_image(prompt, output_path, api_key):
    """
    Returns dict: {"success": bool, "model_used": str, "attempts": [{"model": str, "status_code": int, "duration_sec": float, "error": str}]}
    """
    models = [
        "bytedance-seed/seedream-4.5",
        "x-ai/grok-imagine-image-2.0",
        "qwen/qwen-image-3-pro",
        "black-forest-labs/flux.2-flex"
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://youtube-automation-pipeline.local",
        "X-Title": "YouTube Automation Pipeline"
    }

    attempts = []

    for model_name in models:
        attempt_start = time.time()
        attempt_info = {"model": model_name, "status_code": 0, "duration_sec": 0.0, "error": ""}
        try:
            print(f"    [>] Requesting image with model '{model_name}'...")
            resp = requests.post(
                "https://openrouter.ai/api/v1/images",
                headers=headers,
                json={"model": model_name, "prompt": prompt},
                timeout=45
            )
            attempt_info["status_code"] = resp.status_code
            attempt_info["duration_sec"] = round(time.time() - attempt_start, 2)

            if resp.status_code != 200:
                attempt_info["error"] = resp.text[:200]
                print(f"    [-] Model {model_name} returned status {resp.status_code}: {resp.text[:200]}")
                attempts.append(attempt_info)
                continue

            data = resp.json()
            images = data.get("data", [])
            if not images:
                attempt_info["error"] = "Empty data array"
                print(f"    [-] Model {model_name} returned empty data array")
                attempts.append(attempt_info)
                continue

            img_data = images[0]
            b64_str = img_data.get("b64_json", "")

            if not b64_str:
                url_str = img_data.get("url", "")
                if url_str.startswith("data:image"):
                    b64_str = url_str.split(",", 1)[1] if "," in url_str else ""
                elif url_str.startswith("http"):
                    img_resp = requests.get(url_str, timeout=30)
                    if img_resp.status_code == 200:
                        with open(output_path, "wb") as f:
                            f.write(img_resp.content)
                        print(f"    [+] Image downloaded via {model_name}: {len(img_resp.content)} bytes")
                        attempts.append(attempt_info)
                        return {"success": True, "model_used": model_name, "attempts": attempts}

            if b64_str:
                img_bytes = base64.b64decode(b64_str)
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                print(f"    [+] Image generated via {model_name}: {len(img_bytes)} bytes -> {os.path.basename(output_path)}")
                attempts.append(attempt_info)
                return {"success": True, "model_used": model_name, "attempts": attempts}

            attempt_info["error"] = "No b64_json or url in response"

        except Exception as e:
            attempt_info["duration_sec"] = round(time.time() - attempt_start, 2)
            attempt_info["error"] = str(e)[:200]
            print(f"    [-] Model {model_name} request error: {e}")

        attempts.append(attempt_info)

    print(f"    [-] All image generation models failed")
    return {"success": False, "model_used": None, "attempts": attempts}


def _generate_grok_video(image_path, motion_prompt, output_path, api_key, max_poll_seconds=180, poll_callback=None):
    """
    Returns dict: {"success": bool, "model_used": str, "duration_sec": float, "error": str}
    poll_callback(attempt, max_polls, elapsed, status) is called on each poll iteration.
    """
    models_to_try = [
        "bytedance/seedance-1-5-pro",
        "bytedance/seedance-2.5",
        "x-ai/grok-imagine-video-1.5"
    ]

    start_time = time.time()
    result = {"success": False, "model_used": None, "duration_sec": 0.0, "error": ""}

    try:
        with open(image_path, "rb") as f:
            img_bytes = f.read()

        ext = os.path.splitext(image_path)[1].lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        data_uri = f"data:{mime};base64,{b64}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://youtube-automation-pipeline.local",
            "X-Title": "YouTube Automation Pipeline"
        }

        polling_url = None

        for model_name in models_to_try:
            print(f"    [>] Submitting video job with model '{model_name}'...")
            try:
                submit_resp = requests.post(
                    "https://openrouter.ai/api/v1/videos",
                    headers=headers,
                    json={
                        "model": model_name,
                        "prompt": motion_prompt,
                        "frame_images": [{
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                            "frame_type": "first_frame"
                        }],
                        "aspect_ratio": "16:9"
                    },
                    timeout=60
                )

                if submit_resp.status_code in (200, 201, 202):
                    job_data = submit_resp.json()
                    job_id = job_data.get("id", "")
                    polling_url = job_data.get("polling_url", "")
                    if not polling_url and job_id:
                        polling_url = f"https://openrouter.ai/api/v1/videos/{job_id}"
                    if polling_url:
                        result["model_used"] = model_name
                        print(f"    [+] Video job submitted ({model_name}): {job_id}. Polling...")
                        break
                else:
                    print(f"    [-] Video model {model_name} submit returned status {submit_resp.status_code}: {submit_resp.text[:150]}")
            except Exception as e_sub:
                print(f"    [-] Video model {model_name} submit error: {e_sub}")

        if not polling_url:
            result["error"] = "No video job could be submitted"
            result["duration_sec"] = round(time.time() - start_time, 2)
            return result

        poll_interval = 5
        max_polls = max_poll_seconds // poll_interval

        for attempt in range(max_polls):
            time.sleep(poll_interval)
            elapsed = time.time() - start_time

            if poll_callback:
                poll_callback(attempt + 1, max_polls, elapsed, "polling")

            try:
                poll_resp = requests.get(polling_url, headers=headers, timeout=30)
                poll_data = poll_resp.json()
                status = poll_data.get("status", "unknown")

                if status == "completed":
                    video_urls = poll_data.get("unsigned_urls", [])
                    if not video_urls:
                        video_urls = poll_data.get("urls", [])

                    if video_urls:
                        download_headers = {"User-Agent": "Mozilla/5.0"}
                        video_resp = requests.get(video_urls[0], headers=download_headers, timeout=120)
                        if video_resp.status_code == 200 and len(video_resp.content) > 1000:
                            with open(output_path, "wb") as f:
                                f.write(video_resp.content)
                            result["success"] = True
                            result["duration_sec"] = round(time.time() - start_time, 2)
                            print(f"    [+] Video downloaded: {len(video_resp.content)} bytes -> {os.path.basename(output_path)}")
                            if poll_callback:
                                poll_callback(attempt + 1, max_polls, elapsed, "completed")
                            return result
                        else:
                            result["error"] = f"Video download failed: status {video_resp.status_code}"
                            result["duration_sec"] = round(time.time() - start_time, 2)
                            return result
                    else:
                        result["error"] = "Completed but no video URLs in response"
                        result["duration_sec"] = round(time.time() - start_time, 2)
                        return result

                elif status == "failed":
                    error_msg = poll_data.get("error", poll_data.get("message", "Unknown error"))
                    result["error"] = str(error_msg)[:200]
                    result["duration_sec"] = round(time.time() - start_time, 2)
                    if poll_callback:
                        poll_callback(attempt + 1, max_polls, elapsed, "failed")
                    print(f"    [-] Video generation failed: {error_msg}")
                    return result
                else:
                    if attempt % 3 == 0:
                        print(f"    [>] Status: {status} (poll {attempt + 1}/{max_polls})...")

            except Exception as e_poll:
                print(f"    [-] Poll error (attempt {attempt + 1}): {e_poll}")

        result["error"] = f"Timed out after {max_poll_seconds}s"
        result["duration_sec"] = round(time.time() - start_time, 2)
        if poll_callback:
            poll_callback(max_polls, max_polls, time.time() - start_time, "timeout")
        return result

    except Exception as e:
        result["error"] = str(e)[:200]
        result["duration_sec"] = round(time.time() - start_time, 2)
        return result


def _create_vector_webcomic_frame(prompt, scene_num, frame_index, total_frames, width=1920, height=1080):
    backgrounds = [
        ((25, 30, 45), (45, 55, 80)),
        ((35, 25, 45), (70, 50, 85)),
        ((20, 35, 40), (40, 75, 85)),
        ((40, 30, 25), (85, 60, 45)),
    ]
    bg_start, bg_end = backgrounds[(scene_num - 1) % len(backgrounds)]

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = int(bg_start[0] + (bg_end[0] - bg_start[0]) * (y / height))
        g = int(bg_start[1] + (bg_end[1] - bg_start[1]) * (y / height))
        b = int(bg_start[2] + (bg_end[2] - bg_start[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    t = frame_index / max(1, total_frames)
    offset_x = int(math.sin(t * math.pi * 2) * 20)
    offset_y = int(math.cos(t * math.pi * 2) * 15)

    for x in range(0, width, 120):
        draw.line([(x + offset_x, 0), (x + offset_x, height)], fill=(100, 150, 200), width=1)
    for y in range(0, height, 120):
        draw.line([(0, y + offset_y), (width, y + offset_y)], fill=(100, 150, 200), width=1)

    center_x, center_y = width // 2 + offset_x, height // 2 + offset_y

    draw.ellipse([center_x - 120, center_y - 250, center_x + 120, center_y - 10], fill=(245, 215, 180), outline=(20, 20, 30), width=6)
    draw.chord([center_x - 140, center_y - 290, center_x + 140, center_y - 120], start=180, end=360, fill=(240, 205, 75), outline=(20, 20, 30), width=6)
    draw.ellipse([center_x - 70, center_y - 160, center_x - 20, center_y - 120], fill=(255, 255, 255), outline=(40, 40, 60), width=4)
    draw.ellipse([center_x + 20, center_y - 160, center_x + 70, center_y - 120], fill=(255, 255, 255), outline=(40, 40, 60), width=4)
    draw.ellipse([center_x - 50, center_y - 148, center_x - 36, center_y - 134], fill=(30, 60, 100))
    draw.ellipse([center_x + 36, center_y - 148, center_x + 50, center_y - 134], fill=(30, 60, 100))

    draw.polygon([
        (center_x - 200, height),
        (center_x - 120, center_y - 10),
        (center_x + 120, center_y - 10),
        (center_x + 200, height)
    ], fill=(240, 245, 250), outline=(20, 20, 30), width=6)
    draw.polygon([
        (center_x - 50, center_y - 10),
        (center_x + 50, center_y - 10),
        (center_x, center_y + 120)
    ], fill=(25, 45, 85), outline=(20, 20, 30), width=4)

    draw.rectangle([60, height - 120, width - 60, height - 40], fill=(0, 0, 0, 180), outline=(100, 200, 255), width=2)

    try:
        font = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        font = ImageFont.load_default()

    short_prompt = prompt[:110] + "..." if len(prompt) > 110 else prompt
    draw.text((80, height - 100), f"SCENE {scene_num:02d} | PROMPT: {short_prompt}", fill=(255, 255, 255), font=font)

    return img


def _create_video_from_still(image_path, output_path, duration_sec):
    try:
        from moviepy import ImageClip
    except ImportError:
        from moviepy.editor import ImageClip

    clip = ImageClip(image_path)

    try:
        clip = clip.with_duration(duration_sec)
    except AttributeError:
        clip = clip.set_duration(duration_sec)

    clip.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio=False,
        logger=None
    )
    clip.close()


def generate_image_scene(scene_data, scene_idx, output_dir, api_config, session_id=None):
    """Generates ONLY the AI image for a single scene. Returns a result dict."""
    if api_config is None:
        api_config = {}

    os.makedirs(output_dir, exist_ok=True)
    openrouter_api_key = api_config.get("openrouter_api_key", "")
    image_prompt = scene_data.get("ai_image_prompt", "")
    image_file = os.path.join(output_dir, f"scene_{scene_idx:02d}.png")

    # Skip if already exists (cache)
    if os.path.exists(image_file) and os.path.getsize(image_file) > 1000:
        print(f"  [>] Scene {scene_idx}: Reusing existing image -> {image_file}")
        return {
            "scene_number": scene_idx,
            "image_path": image_file,
            "image_model": "cached",
            "image_attempts": [],
            "image_api_duration_sec": 0.0,
            "status": "CACHED"
        }

    image_result = {"success": False, "model_used": None, "attempts": []}
    if openrouter_api_key:
        print(f"  [>] Scene {scene_idx}: Generating AI image...")
        image_result = _generate_grok_image(image_prompt, image_file, openrouter_api_key)

    ai_image_ok = image_result["success"]
    api_time = round(sum(a.get("duration_sec", 0) for a in image_result.get("attempts", [])), 2)

    result = {
        "scene_number": scene_idx,
        "image_path": image_file if (ai_image_ok and os.path.exists(image_file)) else None,
        "image_model": image_result.get("model_used"),
        "image_attempts": image_result.get("attempts", []),
        "image_api_duration_sec": api_time,
        "status": "SUCCESS" if ai_image_ok else "FALLBACK"
    }

    if session_id:
        try:
            from backend.session_manager import SessionManager
            sm = SessionManager()
            sm.log_api_call(
                session_id=session_id,
                step=f"VISUAL_IMAGE_SCENE_{scene_idx:02d}",
                service=f"OpenRouter Image ({image_result.get('model_used', 'none')})" if openrouter_api_key else "Local Vector Canvas",
                request_data={
                    "scene_number": scene_idx,
                    "prompt": image_prompt[:300],
                    "models_tried": [a["model"] for a in image_result.get("attempts", [])]
                },
                response_data={
                    "status": result["status"],
                    "model_used": image_result.get("model_used"),
                    "image_path": result["image_path"],
                    "file_size_bytes": os.path.getsize(image_file) if os.path.exists(image_file) else 0,
                    "attempts": image_result.get("attempts", [])
                },
                status=result["status"],
                duration_sec=api_time
            )
        except Exception as e_sm:
            print(f"[-] Session logging warning for image scene {scene_idx}: {e_sm}")

    return result


def generate_video_from_image(scene_data, audio_info, scene_idx, image_info, output_dir, api_config, session_id=None, poll_callback=None):
    """Generates the video for a single scene from a pre-generated image. Returns a result dict."""
    if api_config is None:
        api_config = {}

    os.makedirs(output_dir, exist_ok=True)
    openrouter_api_key = api_config.get("openrouter_api_key", "")

    image_prompt = scene_data.get("ai_image_prompt", "")
    motion_prompt = scene_data.get("image_to_video_prompt", "Slow cinematic camera pan")
    duration_sec = audio_info.get("duration_sec", 6.0)

    output_file = os.path.join(output_dir, f"scene_{scene_idx:02d}.mp4")
    image_file = (image_info or {}).get("image_path")
    ai_image_ok = bool(image_file and os.path.exists(image_file))

    scene_start = time.time()
    video_result = {"success": False, "model_used": None, "duration_sec": 0.0, "error": ""}
    grok_success = False

    if openrouter_api_key and ai_image_ok:
        print(f"  [>] Scene {scene_idx}: Converting AI image to video clip...")
        full_motion_prompt = f"{motion_prompt}. {image_prompt[:100]}"
        video_result = _generate_grok_video(image_file, full_motion_prompt, output_file, openrouter_api_key, poll_callback=poll_callback)

        if video_result["success"]:
            grok_success = True
        else:
            print(f"  [-] Scene {scene_idx}: Video gen failed ({video_result['error']}), creating video from still image...")
            try:
                _create_video_from_still(image_file, output_file, duration_sec)
                grok_success = True
                video_result["error"] = f"Still-image fallback. Cause: {video_result.get('error') or 'unknown'}"
            except Exception as e_still:
                print(f"  [-] Scene {scene_idx}: Still image video fallback failed: {e_still}")

    if not grok_success:
        try:
            from moviepy import ImageSequenceClip
        except ImportError:
            from moviepy.editor import ImageSequenceClip

        import numpy as np

        fps = 15
        total_frames = max(15, int(duration_sec * fps))
        frames = []

        for f_idx in range(total_frames):
            frame_img = _create_vector_webcomic_frame(image_prompt, scene_idx, f_idx, total_frames)
            frames.append(np.array(frame_img))

        clip = ImageSequenceClip(frames, fps=fps)
        clip.write_videofile(output_file, fps=fps, codec="libx264", audio=False, logger=None)
        clip.close()

    total_duration = round(time.time() - scene_start, 2)
    ai_video_ok = video_result["success"]

    if ai_image_ok and ai_video_ok:
        overall_status = "SUCCESS"
    elif ai_image_ok and not ai_video_ok:
        overall_status = "IMAGE_ONLY"
    else:
        overall_status = "FALLBACK"

    result = {
        "scene_number": scene_idx,
        "video_path": output_file,
        "image_path": image_file if ai_image_ok else None,
        "duration_sec": duration_sec,
        "prompt": image_prompt,
        "status": overall_status,
        "image_model": (image_info or {}).get("image_model"),
        "video_model": video_result.get("model_used"),
        "image_attempts": (image_info or {}).get("image_attempts", []),
        "video_error": video_result.get("error", ""),
        "total_api_duration_sec": total_duration,
        "image_api_duration_sec": (image_info or {}).get("image_api_duration_sec", 0.0),
        "video_api_duration_sec": video_result.get("duration_sec", 0.0)
    }

    if session_id:
        try:
            from backend.session_manager import SessionManager
            sm = SessionManager()
            sm.log_api_call(
                session_id=session_id,
                step=f"VISUAL_VIDEO_SCENE_{scene_idx:02d}",
                service=f"Seedance ({video_result.get('model_used', 'none')})" if (openrouter_api_key and ai_image_ok) else "MoviePy Animator",
                request_data={
                    "scene_number": scene_idx,
                    "motion_prompt": motion_prompt,
                    "duration_sec": duration_sec
                },
                response_data={
                    "status": overall_status,
                    "video_path": output_file,
                    "file_size_bytes": os.path.getsize(output_file) if os.path.exists(output_file) else 0,
                    "error": video_result.get("error", "")
                },
                status="SUCCESS" if ai_video_ok else "FALLBACK",
                duration_sec=round(video_result.get("duration_sec", 0.0), 2)
            )
            sm.increment_counter(session_id, "video_count")
        except Exception as e_sm:
            print(f"[-] Session logging warning for video scene {scene_idx}: {e_sm}")

    return result


def generate_video_scene(scene_data, audio_info, scene_idx, visual_settings, output_dir, api_config, session_id=None, poll_callback=None):
    """Generates image and video for a single scene (image first, then video). Returns a result dict."""
    image_info = generate_image_scene(scene_data, scene_idx, output_dir, api_config, session_id=session_id)
    return generate_video_from_image(scene_data, audio_info, scene_idx, image_info, output_dir, api_config,
                                     session_id=session_id, poll_callback=poll_callback)


def generate_video_assets(script_data, audio_assets, visual_settings=None, output_dir=None, api_config=None, session_id=None):
    if visual_settings is None:
        visual_settings = {}
    if api_config is None:
        api_config = {}
    if output_dir is None:
        if session_id:
            from backend.session_manager import SessionManager
            sm = SessionManager()
            output_dir = os.path.join(sm.get_session_dir(session_id), "video_assets")
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(base_dir, "data", "video_assets")
    os.makedirs(output_dir, exist_ok=True)

    openrouter_api_key = api_config.get("openrouter_api_key", "")

    scenes = script_data.get("scenes", [])
    video_results = []

    if openrouter_api_key:
        print(f"[+] Generating visual assets for {len(scenes)} scenes using OpenRouter AI...")
    else:
        print(f"[+] Generating visual assets for {len(scenes)} scenes using local vector animation...")

    for idx, (scene, audio_info) in enumerate(zip(scenes, audio_assets), 1):
        existing_mp4 = os.path.join(output_dir, f"scene_{idx:02d}.mp4")
        if os.path.exists(existing_mp4) and os.path.getsize(existing_mp4) > 1000:
            print(f"  [>] Scene {idx}: Reusing existing video -> {existing_mp4}")
            video_results.append({
                "scene_number": idx,
                "video_path": existing_mp4,
                "image_path": os.path.join(output_dir, f"scene_{idx:02d}.png") if os.path.exists(os.path.join(output_dir, f"scene_{idx:02d}.png")) else None,
                "duration_sec": audio_info.get("duration_sec", 6.0),
                "prompt": scene.get("ai_image_prompt", ""),
                "status": "CACHED"
            })
            continue

        result = generate_video_scene(scene, audio_info, idx, visual_settings, output_dir, api_config, session_id)
        video_results.append(result)

    s_id = session_id
    if s_id:
        try:
            from backend.session_manager import SessionManager
            sm = SessionManager()
            sm.save_checkpoint(s_id, "video_assets", video_results)
            sm.update_status(s_id, "ASSETS_GENERATED", current_step="ASSEMBLY")

            ai_success = sum(1 for v in video_results if v.get("status") == "SUCCESS")
            image_only = sum(1 for v in video_results if v.get("status") == "IMAGE_ONLY")
            fallback = sum(1 for v in video_results if v.get("status") == "FALLBACK")
            cached = sum(1 for v in video_results if v.get("status") == "CACHED")

            if fallback == 0 and image_only == 0:
                summary_status = "SUCCESS"
            elif ai_success > 0:
                summary_status = "PARTIAL"
            else:
                summary_status = "ALL_FALLBACK"

            sm.log_api_call(
                session_id=s_id,
                step="VISUAL_GENERATION_SUMMARY",
                service="OpenRouter" if openrouter_api_key else "Local PIL",
                request_data={"scene_count": len(scenes)},
                response_data={
                    "status": summary_status,
                    "ai_video_success": ai_success,
                    "image_only_count": image_only,
                    "fallback_count": fallback,
                    "cached_count": cached,
                    "total_api_duration_sec": round(sum(v.get("total_api_duration_sec", 0) for v in video_results), 2)
                },
                status=summary_status,
                duration_sec=round(sum(v.get("total_api_duration_sec", 0) for v in video_results), 2)
            )
        except Exception as e_sm:
            print(f"[-] Session logging warning for video summary: {e_sm}")

    return video_results
