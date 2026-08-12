import os
import json

DEFAULT_PROFILE = {
    "channel_name": "Behavioral Psychology Insights",
    "niche": "Behavioral Psychology, Mindset, and Human Dynamics",
    "voice_settings": {
        "tts_model": "edge-tts",
        "voice_id": "en-US-ChristopherNeural",
        "speed": "+0%",
        "pitch": "+0Hz"
    },
    "visual_settings": {
        "aspect_ratio": "16:9",
        "art_style_prompt": "modern webcomic vector style, clean lines, flat shading"
    },
    "character_anchor": "Jessica mascot, mid-30s Caucasian female psychologist, blonde hair with soft waves, navy blouse under white lab coat, modern webcomic vector style, clean lines, flat shading.",
    "reference_image_paths": []
}

class ProfileManager:
    def __init__(self, profiles_dir=None):
        if profiles_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            profiles_dir = os.path.join(base_dir, "data", "profiles")
        self.profiles_dir = profiles_dir
        os.makedirs(self.profiles_dir, exist_ok=True)
        self.ensure_default_profile()

    def ensure_default_profile(self):
        default_path = os.path.join(self.profiles_dir, "default_psychology.json")
        if not os.path.exists(default_path):
            self.save_profile("default_psychology", DEFAULT_PROFILE)

    def list_profiles(self):
        profiles = []
        for filename in os.listdir(self.profiles_dir):
            if filename.endswith(".json"):
                profiles.append(os.path.splitext(filename)[0])
        return profiles if profiles else ["default_psychology"]

    def get_profile(self, profile_id):
        filepath = os.path.join(self.profiles_dir, f"{profile_id}.json")
        if not os.path.exists(filepath):
            # Fallback to default
            return DEFAULT_PROFILE.copy()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[-] Error loading profile {profile_id}: {e}")
            return DEFAULT_PROFILE.copy()

    def save_profile(self, profile_id, profile_data):
        safe_id = "".join(c for c in profile_id if c.isalnum() or c in ("_", "-")).strip()
        if not safe_id:
            safe_id = "channel_profile"
        profile_data["profile_id"] = safe_id
        filepath = os.path.join(self.profiles_dir, f"{safe_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2)
        return safe_id
