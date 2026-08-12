import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def _create_subtitle_image(text, width=1920, height=1080):
    """
    Creates a transparent PNG numpy array with stylized centered high-contrast subtitles
    for robust Windows rendering without ImageMagick dependencies.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    if not text:
        return np.array(img)
        
    try:
        font = ImageFont.truetype("arialbd.ttf", 64)
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except Exception:
            font = ImageFont.load_default()
            
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    padding_x = 40
    padding_y = 20
    
    center_x = width // 2
    center_y = int(height * 0.78)
    
    bg_box = [
        center_x - text_w // 2 - padding_x,
        center_y - text_h // 2 - padding_y,
        center_x + text_w // 2 + padding_x,
        center_y + text_h // 2 + padding_y
    ]
    
    # Semi-transparent dark pill background with gold border
    draw.rounded_rectangle(bg_box, radius=18, fill=(15, 20, 35, 220), outline=(255, 215, 0, 255), width=4)
    
    # Yellow/white bold text centered
    text_pos = (center_x - text_w // 2, center_y - text_h // 2 - 5)
    # Outline shadow
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        draw.text((text_pos[0] + dx, text_pos[1] + dy), text, font=font, fill=(0, 0, 0, 255))
    draw.text(text_pos, text, font=font, fill=(255, 255, 255, 255))
    
    return np.array(img)


def assemble_video(script_data, audio_assets, video_assets, visual_settings=None, output_filepath=None, session_id=None):
    """
    MoviePy Timeline Assembly (MoviePy 1.x & 2.x compatible):
    - Synchronizes video clip duration to exact audio length.
    - Applies dynamic camera zoom (Ken Burns effect).
    - Overlays on_screen_text centered subtitles.
    - Concatenates scenes with 0.5s crossfade transition.
    - Renders final 1080p 30fps MP4.
    """
    print("[+] Assembling final timeline with MoviePy...")

    if output_filepath is None:
        if session_id:
            from backend.session_manager import SessionManager
            sm = SessionManager()
            output_filepath = os.path.join(sm.get_session_dir(session_id), "final_video.mp4")
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_filepath = os.path.join(base_dir, "data", "outputs", "final_video.mp4")
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    
    try:
        from moviepy import (
            VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips, vfx
        )
    except ImportError:
        from moviepy.editor import (
            VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips, vfx
        )
    
    scenes = script_data.get("scenes", [])
    processed_clips = []
    
    for idx, (scene, audio_info, video_info) in enumerate(zip(scenes, audio_assets, video_assets), 1):
        v_path = video_info["video_path"]
        a_path = audio_info["audio_path"]
        sub_text = scene.get("on_screen_text", "")
        
        audio_clip = AudioFileClip(a_path)
        exact_duration = audio_clip.duration
        
        v_clip = VideoFileClip(v_path)
        
        def set_dur(c, dur):
            return c.with_duration(dur) if hasattr(c, 'with_duration') else c.set_duration(dur)

        def set_aud(c, aud):
            return c.with_audio(aud) if hasattr(c, 'with_audio') else c.set_audio(aud)

        def subc(c, start, end):
            if hasattr(c, 'subclipped'):
                return c.subclipped(start, end)
            elif hasattr(c, 'subclip'):
                return c.subclip(start, end)
            return c

        if v_clip.duration < exact_duration:
            n_loops = int(np.ceil(exact_duration / max(0.1, v_clip.duration)))
            try:
                v_clip = concatenate_videoclips([v_clip] * n_loops)
            except Exception:
                pass
        v_clip = subc(v_clip, 0, exact_duration)
        v_clip = set_dur(v_clip, exact_duration)
        v_clip = set_aud(v_clip, audio_clip)
        
        # Ken Burns Zoom Effect
        try:
            if hasattr(vfx, 'Resize'):
                zoomed_clip = v_clip.with_effects([vfx.Resize(lambda t: 1.0 + 0.12 * (t / max(0.1, exact_duration)))])
            else:
                zoomed_clip = v_clip.fx(vfx.resize, lambda t: 1.0 + 0.12 * (t / max(0.1, exact_duration)))
        except Exception:
            zoomed_clip = v_clip
            
        # Add Subtitle Overlay Clip
        if sub_text:
            sub_img_array = _create_subtitle_image(sub_text)
            sub_clip = ImageClip(sub_img_array)
            sub_clip = set_dur(sub_clip, exact_duration)
            final_scene_clip = CompositeVideoClip([zoomed_clip, sub_clip], size=(1920, 1080))
        else:
            final_scene_clip = zoomed_clip
            
        final_scene_clip = set_dur(final_scene_clip, exact_duration)
        processed_clips.append(final_scene_clip)
        print(f"  [>] Scene {idx} Timed & Prepared ({exact_duration:.2f}s)")
        
    print(f"[+] Concatenating {len(processed_clips)} scenes...")
    
    if len(processed_clips) > 1:
        try:
            final_concat = concatenate_videoclips(processed_clips, padding=-0.5, method="compose")
        except Exception:
            final_concat = concatenate_videoclips(processed_clips)
    else:
        final_concat = processed_clips[0]
        
    print(f"[+] Rendering final MP4 (1080p, 30fps) to {output_filepath}...")
    temp_audio = os.path.join(os.path.dirname(output_filepath), "temp-audio.m4a")
    
    final_concat.write_videofile(
        output_filepath,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        temp_audiofile=temp_audio,
        remove_temp=True,
        logger=None
    )
    
    # Cleanup clips
    for clip in processed_clips:
        clip.close()
    final_concat.close()
    
    print(f"[+] Final Video Render Complete! Saved to: {output_filepath}")
    return output_filepath
