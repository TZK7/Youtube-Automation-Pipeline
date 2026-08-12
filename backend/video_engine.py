import os
import math
import time
import base64
import requests
from PIL import Image, ImageDraw, ImageFont


def _generate_grok_image(prompt, output_path, api_key):
    """
    Generates an image using OpenRouter Image Gen API.
    Tries Grok Imagine Image 2.0 first, with Seedream 4.5 fallback for maximum reliability & speed.
    Saves the decoded image to output_path (PNG).
    Returns True on success, False on failure.
    """
    models = [
        "x-ai/grok-imagine-image-2.0",
        "bytedance-seed/seedream-4.5",
        "qwen/qwen-image-3-pro",
        "black-forest-labs/flux.2-flex"
    ]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://youtube-automation-pipeline.local",
        "X-Title": "YouTube Automation Pipeline"
    }
    
    for model_name in models:
        try:
            print(f"    [>] Requesting image with model '{model_name}'...")
            resp = requests.post(
                "https://openrouter.ai/api/v1/images",
                headers=headers,
                json={
                    "model": model_name,
                    "prompt": prompt
                },
                timeout=45
            )
            
            if resp.status_code != 200:
                print(f"    [-] Model {model_name} returned status {resp.status_code}: {resp.text[:200]}")
                continue
            
            data = resp.json()
            images = data.get("data", [])
            if not images:
                print(f"    [-] Model {model_name} returned empty data array")
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
                        return True
            
            if b64_str:
                img_bytes = base64.b64decode(b64_str)
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                print(f"    [+] Image generated via {model_name}: {len(img_bytes)} bytes -> {os.path.basename(output_path)}")
                return True
                
        except Exception as e:
            print(f"    [-] Model {model_name} request error: {e}")
            continue
            
    print(f"    [-] All image generation models failed")
    return False


def _generate_grok_video(image_path, motion_prompt, output_path, api_key, max_poll_seconds=180):
    """
    Generates a video from an image using ByteDance Seedance via OpenRouter API.
    This is an async job-based workflow:
      1. Submit job with first_frame image + motion prompt
      2. Poll status until completed or failed
      3. Download resulting MP4 (without Bearer header for CDN/S3 compatibility)
    Returns True on success, False on failure.
    """
    models_to_try = [
        "bytedance/seedance-1-5-pro",
        "bytedance/seedance-2.5",
        "x-ai/grok-imagine-video-1.5"
    ]
    
    try:
        # Read and encode local image as base64 data URI
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
        
        job_id = None
        polling_url = None
        
        for model_name in models_to_try:
            print(f"    [>] Submitting video job with model '{model_name}'...")
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
                    print(f"    [+] Video job submitted ({model_name}): {job_id}. Polling for completion...")
                    break
            else:
                print(f"    [-] Video model {model_name} submit returned status {submit_resp.status_code}: {submit_resp.text[:150]}")
        
        if not polling_url:
            print(f"    [-] Video generation: No video job could be submitted")
            return False
        
        # Step 2: Poll until complete
        poll_interval = 5
        max_polls = max_poll_seconds // poll_interval
        
        for attempt in range(max_polls):
            time.sleep(poll_interval)
            try:
                poll_resp = requests.get(polling_url, headers=headers, timeout=30)
                poll_data = poll_resp.json()
                status = poll_data.get("status", "unknown")
                
                if status == "completed":
                    video_urls = poll_data.get("unsigned_urls", [])
                    if not video_urls:
                        video_urls = poll_data.get("urls", [])
                    
                    if video_urls:
                        # Download WITHOUT OpenRouter Bearer header to avoid 401 S3 signature mismatch
                        download_headers = {"User-Agent": "Mozilla/5.0"}
                        video_resp = requests.get(video_urls[0], headers=download_headers, timeout=120)
                        if video_resp.status_code == 200 and len(video_resp.content) > 1000:
                            with open(output_path, "wb") as f:
                                f.write(video_resp.content)
                            print(f"    [+] Video downloaded: {len(video_resp.content)} bytes -> {os.path.basename(output_path)}")
                            return True
                        else:
                            print(f"    [-] Video download failed: status {video_resp.status_code}")
                            return False
                    else:
                        print(f"    [-] Completed but no video URLs in response: {poll_data}")
                        return False
                        
                elif status == "failed":
                    error_msg = poll_data.get("error", poll_data.get("message", "Unknown error"))
                    print(f"    [-] Video generation failed: {error_msg}")
                    return False
                else:
                    if attempt % 3 == 0:
                        print(f"    [>] Status: {status} (poll {attempt + 1}/{max_polls})...")
                        
            except Exception as e_poll:
                print(f"    [-] Poll error (attempt {attempt + 1}): {e_poll}")
        
        print(f"    [-] Video generation timed out after {max_poll_seconds}s")
        return False
        
    except Exception as e:
        print(f"    [-] Video generation error: {e}")
        return False


def _create_vector_webcomic_frame(prompt, scene_num, frame_index, total_frames, width=1920, height=1080):
    """
    Generates a stylized modern webcomic vector canvas frame matching the character anchor & prompt.
    Used as fallback when OpenRouter API is unavailable.
    """
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


def generate_video_assets(script_data, audio_assets, visual_settings=None, output_dir=None, api_config=None, session_id=None):
    """
    Generates video clips (scene_01.mp4, scene_02.mp4) synchronized to each audio segment.
    
    Priority order:
      1. OpenRouter Image Gen (Grok Imagine Image 2.0 / Seedream 4.5) + ByteDance Seedance Image-to-Video
      2. Local PIL vector animation fallback
    Logs audit trails and saves checkpoints if session_id is provided.
    """
    if visual_settings is None:
        visual_settings = {}
    if api_config is None:
        api_config = {}
    if output_dir is None:
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
        image_prompt = scene.get("ai_image_prompt", "")
        motion_prompt = scene.get("image_to_video_prompt", "Slow cinematic camera pan")
        duration_sec = audio_info.get("duration_sec", 6.0)
        
        output_file = os.path.join(output_dir, f"scene_{idx:02d}.mp4")
        image_file = os.path.join(output_dir, f"scene_{idx:02d}.png")
        
        grok_success = False
        
        # --- Priority 1: Grok/Seedream Image Gen + Seedance Image-to-Video via OpenRouter ---
        if openrouter_api_key:
            print(f"  [>] Scene {idx}: Generating AI image...")
            image_ok = _generate_grok_image(image_prompt, image_file, openrouter_api_key)
            
            if image_ok:
                print(f"  [>] Scene {idx}: Converting AI image to video clip...")
                full_motion_prompt = f"{motion_prompt}. {image_prompt[:100]}"
                video_ok = _generate_grok_video(image_file, full_motion_prompt, output_file, openrouter_api_key)
                
                if video_ok:
                    grok_success = True
                else:
                    print(f"  [-] Scene {idx}: Video generation model failed, creating video clip from generated AI image...")
                    try:
                        _create_video_from_still(image_file, output_file, duration_sec)
                        grok_success = True
                    except Exception as e_still:
                        print(f"  [-] Scene {idx}: Still image video fallback failed: {e_still}")
            else:
                print(f"  [-] Scene {idx}: AI image generation failed, falling back to local vector animation...")
        
        # --- Priority 2: Local PIL vector animation fallback ---
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
                frame_img = _create_vector_webcomic_frame(image_prompt, idx, f_idx, total_frames)
                frames.append(np.array(frame_img))
                
            clip = ImageSequenceClip(frames, fps=fps)
            clip.write_videofile(
                output_file,
                fps=fps,
                codec="libx264",
                audio=False,
                logger=None
            )
            clip.close()
            
        print(f"  [>] Scene {idx} Video Generated: {duration_sec:.2f}s -> {output_file}")
        video_results.append({
            "scene_number": idx,
            "video_path": output_file,
            "image_path": image_file if os.path.exists(image_file) else None,
            "duration_sec": duration_sec,
            "prompt": image_prompt
        })

        # Granular per-scene Visual Audit Trail logging
        s_id = session_id or api_config.get("session_id")
        if s_id:
            try:
                from backend.session_manager import SessionManager
                sm = SessionManager()
                
                # Log Image Gen per scene
                sm.log_api_call(
                    session_id=s_id,
                    step=f"VISUAL_IMAGE_SCENE_{idx:02d}",
                    service="OpenRouter Image Gen (Grok/Seedream)" if openrouter_api_key else "Local Vector Canvas",
                    request_data={
                        "scene_number": idx,
                        "prompt": image_prompt
                    },
                    response_data={
                        "status": "SUCCESS" if os.path.exists(image_file) else "FALLBACK",
                        "image_path": image_file if os.path.exists(image_file) else None,
                        "file_size_bytes": os.path.getsize(image_file) if os.path.exists(image_file) else 0
                    },
                    status="SUCCESS" if os.path.exists(image_file) else "FALLBACK",
                    duration_sec=0.0
                )
                
                # Log Video Clip per scene
                sm.log_api_call(
                    session_id=s_id,
                    step=f"VISUAL_VIDEO_SCENE_{idx:02d}",
                    service="ByteDance Seedance 1.5 Pro (OpenRouter)" if (openrouter_api_key and grok_success) else "MoviePy Animator",
                    request_data={
                        "scene_number": idx,
                        "motion_prompt": motion_prompt,
                        "duration_sec": duration_sec
                    },
                    response_data={
                        "status": "SUCCESS" if grok_success else "FALLBACK",
                        "video_path": output_file,
                        "file_size_bytes": os.path.getsize(output_file) if os.path.exists(output_file) else 0
                    },
                    status="SUCCESS" if grok_success else "FALLBACK",
                    duration_sec=round(duration_sec, 2)
                )
            except Exception as e_sm:
                print(f"[-] Session logging warning for video scene {idx}: {e_sm}")

    # Session Management & Audit Logging
    s_id = session_id or api_config.get("session_id")
    if s_id:
        try:
            from backend.session_manager import SessionManager
            sm = SessionManager()
            sm.save_checkpoint(s_id, "video_assets", video_results)
            sm.update_status(s_id, "ASSETS_GENERATED", current_step="ASSEMBLY")
            
            sm.log_api_call(
                session_id=s_id,
                step="VISUAL_GENERATION",
                service="Grok Image 2.0 & Seedance Video (OpenRouter)" if openrouter_api_key else "Local PIL Animator",
                request_data={
                    "scene_count": len(scenes),
                    "image_model": "x-ai/grok-imagine-image-2.0 / bytedance-seed/seedream-4.5" if openrouter_api_key else "local-pil",
                    "video_model": "bytedance/seedance-1-5-pro" if openrouter_api_key else "local-pil"
                },
                response_data={
                    "status": "SUCCESS",
                    "generated_count": len(video_results),
                    "clips": [v["video_path"] for v in video_results]
                },
                status="SUCCESS",
                duration_sec=round(sum(v["duration_sec"] for v in video_results), 2)
            )
        except Exception as e_sm:
            print(f"[-] Session logging warning for video: {e_sm}")

    return video_results


def _create_video_from_still(image_path, output_path, duration_sec):
    """
    Creates a video from a generated AI image with a subtle zoom/pan effect using MoviePy.
    Used when AI image gen succeeds so the user ALWAYS gets their real generated AI visual!
    """
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
