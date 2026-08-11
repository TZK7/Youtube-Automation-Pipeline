from dotenv import load_dotenv
load_dotenv(override=True)

from backend.profile_manager import ProfileManager
from backend.competitor_engine import analyze_competitors
from backend.script_engine import generate_script
from backend.audio_engine import generate_audio
from backend.video_engine import generate_video_assets
from backend.assembly_engine import assemble_video
from backend.packaging_engine import package_video

def run_pipeline(topic="Dark Psychology", profile_id="default_psychology"):
    print("==================================================")
    print(" YOUTUBE AUTOMATION CONTROL CENTER - PIPELINE")
    print(f" Topic: {topic}")
    print(f" Profile: {profile_id}")
    print("==================================================")
    
    # 1. Profile Manager
    pm = ProfileManager()
    profile = pm.get_profile(profile_id)
    print(f"[+] Loaded Channel Profile: {profile.get('channel_name')}")
    
    yt_key = os.environ.get("YOUTUBE_API_KEY")
    gem_key = os.environ.get("GEMINI_API_KEY")
    
    # 2. Competitor Engine
    print("\n[Step 0] Market Intelligence & Gap Analysis...")
    competitor_insights = analyze_competitors(
        seed_topic=topic,
        youtube_api_key=yt_key,
        gemini_api_key=gem_key
    )
    
    # 3. Script Engine
    print("\n[Step 1] Script Generation via Google AI Studio (Gemini 2.5)...")
    script_data = generate_script(
        topic=topic,
        competitor_insights=competitor_insights,
        channel_profile=profile,
        gemini_api_key=gem_key
    )
    
    # 4. Audio Engine
    print("\n[Step 2] TTS Voice Synthesis (edge-tts)...")
    audio_assets = generate_audio(
        script_data=script_data,
        voice_settings=profile.get("voice_settings", {})
    )
    
    # 5. Video Engine
    print("\n[Step 3] Visual Asset Generation...")
    video_assets = generate_video_assets(
        script_data=script_data,
        audio_assets=audio_assets,
        visual_settings=profile.get("visual_settings", {})
    )
    
    # 6. Assembly Engine
    print("\n[Step 4] MoviePy Timeline Assembly & Rendering...")
    final_video_path = assemble_video(
        script_data=script_data,
        audio_assets=audio_assets,
        video_assets=video_assets,
        visual_settings=profile.get("visual_settings", {})
    )
    
    # 7. Packaging Engine
    print("\n[Step 5] SEO & Thumbnail Delivery Packaging...")
    package_info = package_video(
        final_video_path=final_video_path,
        script_data=script_data,
        competitor_insights=competitor_insights
    )
    
    print("\n==================================================")
    print(" PIPELINE EXECUTION COMPLETE!")
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
    args = parser.parse_args()
    
    run_pipeline(topic=args.topic, profile_id=args.profile)
