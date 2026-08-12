import os
import argparse
from dotenv import load_dotenv
load_dotenv(override=True)

from backend.profile_manager import ProfileManager
from backend.competitor_engine import analyze_competitors
from backend.script_engine import generate_script
from backend.audio_engine import generate_audio
from backend.video_engine import generate_video_assets
from backend.assembly_engine import assemble_video
from backend.packaging_engine import package_video
from backend.session_manager import SessionManager

def run_pipeline(topic="Dark Psychology", profile_id="default_psychology", target_minutes=10):
    print("==================================================")
    print(" YOUTUBE AUTOMATION CONTROL CENTER - PIPELINE")
    print(f" Topic: {topic}")
    print(f" Profile: {profile_id}")
    print(f" Target: {target_minutes} minutes")
    print("==================================================")

    pm = ProfileManager()
    profile = pm.get_profile(profile_id)
    print(f"[+] Loaded Channel Profile: {profile.get('channel_name')}")

    sm = SessionManager()
    session = sm.create_session(topic=topic, profile_id=profile_id, profile_name=profile.get("channel_name", profile_id))
    session_id = session["session_id"]
    print(f"[+] Session: {session_id}")

    yt_key = os.environ.get("YOUTUBE_API_KEY")
    gem_key = os.environ.get("GEMINI_API_KEY")
    or_key = os.environ.get("OPENROUTER_API_KEY")

    print("\n[Step 0] Market Intelligence & Gap Analysis...")
    competitor_insights = analyze_competitors(
        seed_topic=topic,
        youtube_api_key=yt_key,
        gemini_api_key=gem_key
    )
    if competitor_insights and not competitor_insights.get("error_notice"):
        sm.save_research(session_id, topic, competitor_insights)

    print("\n[Step 1] Script Generation...")
    script_data = generate_script(
        topic=topic,
        competitor_insights=competitor_insights,
        channel_profile=profile,
        gemini_api_key=gem_key,
        session_id=session_id,
        target_video_length_minutes=target_minutes
    )

    print("\n[Step 2] TTS Voice Synthesis...")
    voice_settings = dict(profile.get("voice_settings", {}))
    if or_key:
        voice_settings["openrouter_api_key"] = or_key
    audio_assets = generate_audio(
        script_data=script_data,
        voice_settings=voice_settings,
        session_id=session_id
    )

    print("\n[Step 3] Visual Asset Generation...")
    api_config = {}
    if or_key:
        api_config["openrouter_api_key"] = or_key
    video_assets = generate_video_assets(
        script_data=script_data,
        audio_assets=audio_assets,
        visual_settings=profile.get("visual_settings", {}),
        api_config=api_config,
        session_id=session_id
    )

    print("\n[Step 4] MoviePy Timeline Assembly & Rendering...")
    final_video_path = assemble_video(
        script_data=script_data,
        audio_assets=audio_assets,
        video_assets=video_assets,
        visual_settings=profile.get("visual_settings", {}),
        session_id=session_id
    )

    print("\n[Step 5] SEO & Thumbnail Packaging...")
    package_info = package_video(
        final_video_path=final_video_path,
        script_data=script_data,
        competitor_insights=competitor_insights,
        session_id=session_id,
        audio_assets=audio_assets
    )

    sm.save_checkpoint(session_id, "script_data", script_data)
    sm.save_checkpoint(session_id, "audio_assets", audio_assets)
    sm.save_checkpoint(session_id, "video_assets", video_assets)
    if final_video_path and os.path.exists(final_video_path):
        sm.register_asset(session_id, 0, "final_video", final_video_path, status="COMPILED")
    sm.update_status(session_id, "PACKAGED", current_step="COMPLETED")
    bundle_path = sm.export_bundle(session_id)
    print(f"[+] Offline session bundle: {bundle_path}")

    print("\n==================================================")
    print(" PIPELINE EXECUTION COMPLETE!")
    print(f" Session: {session_id}")
    print(f" Final Upload Package: {package_info['package_dir']}")
    print(f" Final Video: {package_info['video_path']}")
    print(f" Thumbnail: {package_info['thumbnail_path']}")
    print(f" Metadata: {package_info['metadata_path']}")
    print("==================================================")
    return package_info

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous YouTube Video Production Pipeline")
    parser.add_argument("--topic", type=str, default="Dark Psychology", help="Target seed topic")
    parser.add_argument("--profile", type=str, default="default_psychology", help="Channel Profile ID")
    parser.add_argument("--minutes", type=int, default=10, help="Target video length in minutes (5, 10, 15, 20)")
    args = parser.parse_args()

    run_pipeline(topic=args.topic, profile_id=args.profile, target_minutes=args.minutes)
