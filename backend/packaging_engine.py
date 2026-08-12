import os
import json
import datetime
from PIL import Image, ImageDraw, ImageFont
from backend.utils import sanitize_filename


def generate_thumbnail(script_data, output_path, video_frame_path=None):
    width, height = 1280, 720

    if video_frame_path and os.path.exists(video_frame_path):
        try:
            img = Image.open(video_frame_path).resize((width, height))
        except Exception:
            img = Image.new("RGB", (width, height), (20, 25, 40))
    else:
        img = Image.new("RGB", (width, height), (20, 25, 40))
        draw = ImageDraw.Draw(img)
        for y in range(height):
            r = int(20 + 40 * (y / height))
            g = int(25 + 15 * (y / height))
            b = int(45 + 50 * (y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        draw.ellipse([width // 2, 80, width - 100, height - 80], fill=(245, 215, 180), outline=(255, 215, 0), width=6)

    draw = ImageDraw.Draw(img)

    hook_text = script_data.get("hook_statement", "UNSPOKEN RULES").upper()

    try:
        font = ImageFont.truetype("arialbd.ttf", 72)
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", 68)
        except Exception:
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), hook_text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    box_x = 60
    box_y = 120
    draw.rectangle([box_x, box_y, box_x + tw + 60, box_y + th + 40], fill=(255, 215, 0))

    draw.text((box_x + 32, box_y + 18), hook_text, font=font, fill=(0, 0, 0))
    draw.text((box_x + 30, box_y + 16), hook_text, font=font, fill=(15, 15, 25))

    img.save(output_path, "JPEG", quality=95)
    print(f"[+] Thumbnail saved to: {output_path}")
    return output_path


def _build_chapters(scenes, audio_assets):
    chapters = []
    cumulative_sec = 0.0
    for idx, scene in enumerate(scenes):
        minutes = int(cumulative_sec // 60)
        seconds = int(cumulative_sec % 60)
        stage = scene.get("retention_stage", f"Scene {idx+1}")
        chapters.append(f"{minutes}:{seconds:02d} {stage}")

        if idx < len(audio_assets):
            cumulative_sec += audio_assets[idx].get("duration_sec", 0)
        else:
            cumulative_sec += scene.get("target_duration_sec", 30)
    return "\n".join(chapters)


def package_video(final_video_path, script_data, competitor_insights=None, output_dir=None, session_id=None, audio_assets=None):
    if competitor_insights is None:
        competitor_insights = {}

    topic = script_data.get("topic", "Behavioral_Psychology")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = sanitize_filename(topic)

    if output_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dir_name = f"{safe_topic}_{timestamp}"
        if session_id:
            dir_name = f"{safe_topic}_{session_id}_{timestamp}"
        output_dir = os.path.join(base_dir, "ready_to_upload", dir_name)
    os.makedirs(output_dir, exist_ok=True)

    dest_video_path = os.path.join(output_dir, "final_video.mp4")
    if os.path.exists(final_video_path) and final_video_path != dest_video_path:
        import shutil
        shutil.copy2(final_video_path, dest_video_path)
    elif not os.path.exists(dest_video_path):
        open(dest_video_path, 'a').close()

    thumb_path = os.path.join(output_dir, "thumbnail.jpg")
    first_image = None
    if session_id:
        from backend.session_manager import SessionManager
        sm = SessionManager()
        vid_dir = os.path.join(sm.get_session_dir(session_id), "video_assets")
        candidate = os.path.join(vid_dir, "scene_01.png")
        if os.path.exists(candidate):
            first_image = candidate
    generate_thumbnail(script_data, thumb_path, video_frame_path=first_image)

    title = script_data.get("title", f"Mastering {topic}")
    scenes = script_data.get("scenes", [])
    content_gaps = competitor_insights.get("content_gaps", ["N/A"])
    recommended_angle = competitor_insights.get("recommended_angle", "")

    chapters = _build_chapters(scenes, audio_assets or [])

    scene_summaries = []
    for s in scenes[:5]:
        on_screen = s.get("on_screen_text", "")
        if on_screen:
            scene_summaries.append(on_screen)
    key_points = ", ".join(scene_summaries) if scene_summaries else topic

    tags = [topic, "Psychology", "Human Dynamics", "Mindset", "Personal Growth"]
    for gap in content_gaps[:3]:
        if isinstance(gap, str) and len(gap) < 40:
            tags.append(gap)
    tags_str = ", ".join(tags)

    total_words = sum(len(s.get("spoken_text", "").split()) for s in scenes)
    est_minutes = round(total_words / 150, 1)

    metadata_content = f"""==================================================
YOUTUBE UPLOAD METADATA BUNDLE
Generated: {datetime.datetime.now().isoformat()}
Topic: {topic}
Session: {session_id or 'N/A'}
Estimated Duration: {est_minutes} minutes ({total_words} words, {len(scenes)} scenes)
==================================================

TITLE:
{title}

DESCRIPTION:
In this video, we break down {topic} with a research-backed framework covering: {key_points}.
{f"Positioning: {recommended_angle}" if recommended_angle else ""}

CHAPTERS:
{chapters}

TAGS:
{tags_str}

COMPETITOR BENCHMARK NOTES:
- Gaps Addressed: {', '.join(content_gaps[:3])}
- Scene Count: {len(scenes)}
- Framework: Extended Retention Framework
- Character Anchor: Active Channel Aesthetic
"""

    meta_path = os.path.join(output_dir, "metadata.txt")
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(metadata_content)

    print(f"[+] Packaging Complete! All assets stored in: {output_dir}")
    return {
        "package_dir": output_dir,
        "video_path": dest_video_path,
        "thumbnail_path": thumb_path,
        "metadata_path": meta_path
    }
