import os
import json
import datetime
from PIL import Image, ImageDraw, ImageFont

def generate_thumbnail(script_data, output_path, video_frame_path=None):
    """
    Grabs a keyframe or generates a high-contrast YouTube thumbnail with bold text.
    """
    width, height = 1280, 720
    
    if video_frame_path and os.path.exists(video_frame_path):
        try:
            img = Image.open(video_frame_path).resize((width, height))
        except Exception:
            img = Image.new("RGB", (width, height), (20, 25, 40))
    else:
        img = Image.new("RGB", (width, height), (20, 25, 40))
        draw = ImageDraw.Draw(img)
        # Background gradient & vector shapes
        for y in range(height):
            r = int(20 + 40 * (y / height))
            g = int(25 + 15 * (y / height))
            b = int(45 + 50 * (y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b))
            
        # Draw dramatic thumbnail vector element
        draw.ellipse([width // 2, 80, width - 100, height - 80], fill=(245, 215, 180), outline=(255, 215, 0), width=6)
        
    draw = ImageDraw.Draw(img)
    
    # Bold High-Contrast Text Overlay
    hook_text = script_data.get("hook_statement", "UNSPOKEN RULES").upper()
    
    try:
        font = ImageFont.truetype("arialbd.ttf", 72)
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", 68)
        except Exception:
            font = ImageFont.load_default()
            
    # Text background badge
    bbox = draw.textbbox((0, 0), hook_text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    box_x = 60
    box_y = 120
    draw.rectangle([box_x, box_y, box_x + tw + 60, box_y + th + 40], fill=(255, 215, 0)) # Gold background
    
    # Dark text shadow
    draw.text((box_x + 32, box_y + 18), hook_text, font=font, fill=(0, 0, 0))
    draw.text((box_x + 30, box_y + 16), hook_text, font=font, fill=(15, 15, 25))
    
    img.save(output_path, "JPEG", quality=95)
    print(f"[+] Thumbnail saved to: {output_path}")
    return output_path


def package_video(final_video_path, script_data, competitor_insights=None, output_dir=None):
    """
    Saves thumbnail.jpg, metadata.txt, and bundles all final assets into ready_to_upload/[topic_timestamp]/.
    """
    if competitor_insights is None:
        competitor_insights = {}
        
    topic = script_data.get("topic", "Behavioral_Psychology")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join(c if c.isalnum() else "_" for c in topic)[:25]
    
    if output_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "ready_to_upload", f"{safe_topic}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Copy / save final video
    dest_video_path = os.path.join(output_dir, "final_video.mp4")
    if os.path.exists(final_video_path) and final_video_path != dest_video_path:
        import shutil
        shutil.copy2(final_video_path, dest_video_path)
    elif not os.path.exists(dest_video_path):
        open(dest_video_path, 'a').close()
        
    # 2. Generate Thumbnail
    thumb_path = os.path.join(output_dir, "thumbnail.jpg")
    generate_thumbnail(script_data, thumb_path)
    
    # 3. Create metadata.txt
    title = script_data.get("title", f"Mastering {topic}")
    content_gaps = competitor_insights.get("content_gaps", ["N/A"])
    
    metadata_content = f"""==================================================
YOUTUBE UPLOAD METADATA BUNDLE
Generated: {datetime.datetime.now().isoformat()}
Topic: {topic}
==================================================

TITLE:
{title}

DESCRIPTION:
In this video, we unpack the psychological mechanisms behind {topic} and give you 3 immediate verbal scripts to maintain authority and calm during conflict.

CHAPTERS:
0:00 Pattern Interrupt
0:15 The Anti-Hook
0:30 Amygdala & Neural Mechanisms
1:00 Executive Reframe Script
1:30 Daily Practice & Mindset

TAGS:
{topic}, Behavioral Psychology, Dark Psychology, Human Dynamics, Stoicism, Mindset, Body Language, Personal Growth, High Retention

COMPETITOR BENCHMARK NOTES:
- Competitor Gaps Addressed: {', '.join(content_gaps)}
- Retention Target: 6-part framework applied
- Character Anchor Applied: Active Channel Aesthetic
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
