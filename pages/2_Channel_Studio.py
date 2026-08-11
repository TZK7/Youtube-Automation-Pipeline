import os
import re
import streamlit as st
from backend.profile_manager import ProfileManager

st.set_page_config(page_title="Channel Studio | YouTube Control Center", page_icon="⚙️", layout="wide")

st.title("⚙️ Channel Studio")
st.caption("Manage brand identity, character aesthetic anchors, voice profiles, and visual styling.")

pm = ProfileManager()
profiles = pm.list_profiles()

st.subheader("📁 Select or Create Profile")
col_sel, col_new = st.columns([3, 2])

with col_sel:
    profile_id = st.selectbox(
        "Active Profile",
        options=profiles,
        index=profiles.index(st.session_state.get("active_profile_id", profiles[0])) if st.session_state.get("active_profile_id") in profiles else 0
    )

with col_new:
    new_name = st.text_input("Create New Profile ID", placeholder="e.g. stoic_mindset").strip()
    if st.button("➕ Create Profile"):
        # Validation for Profile ID
        if not new_name:
            st.error("Profile ID cannot be empty.")
        elif len(new_name) < 2:
            st.error("Profile ID must be at least 2 characters long.")
        elif len(new_name) > 40:
            st.error("Profile ID cannot exceed 40 characters.")
        elif not re.match(r"^[a-zA-Z0-9_\-]+$", new_name):
            st.error("Profile ID can only contain letters, numbers, underscores, and hyphens.")
        elif new_name in profiles:
            st.error(f"Profile ID '{new_name}' already exists! Choose another name.")
        else:
            safe_id = new_name
            pm.save_profile(safe_id, pm.get_profile("default_psychology"))
            st.session_state["active_profile_id"] = safe_id
            st.success(f"Created profile '{safe_id}'!")
            st.rerun()

curr_data = pm.get_profile(profile_id)

st.markdown("---")
with st.form("channel_profile_form"):
    st.subheader("🆔 Brand Identity & Niche")
    ch_name = st.text_input("Channel Name*", value=curr_data.get("channel_name", "")).strip()
    ch_niche = st.text_area("Channel Niche / Core Topic*", value=curr_data.get("niche", "")).strip()
    
    st.subheader("🗣️ Voice & Audio Settings")
    v_col1, v_col2, v_col3 = st.columns(3)
    with v_col1:
        tts_model = st.selectbox("TTS Engine", options=["edge-tts", "Google Cloud TTS", "gTTS"], index=0)
    with v_col2:
        voice_options = [
            "en-US-ChristopherNeural",
            "en-US-AvaNeural",
            "en-US-GuyNeural",
            "en-GB-SoniaNeural",
            "en-AU-WilliamNeural"
        ]
        curr_v = curr_data.get("voice_settings", {}).get("voice_id", "en-US-ChristopherNeural")
        voice_id = st.selectbox("Voice ID", options=voice_options, index=voice_options.index(curr_v) if curr_v in voice_options else 0)
    with v_col3:
        speed = st.text_input("Speed Modulation (e.g. +0%, -10%, +15%)*", value=curr_data.get("voice_settings", {}).get("speed", "+0%")).strip()
        pitch = st.text_input("Pitch Modulation (e.g. +0Hz, -5Hz, +2Hz)*", value=curr_data.get("voice_settings", {}).get("pitch", "+0Hz")).strip()

    st.subheader("🎨 Visual Styling & Character Anchor")
    vis_col1, vis_col2 = st.columns(2)
    with vis_col1:
        aspect_ratio = st.selectbox("Aspect Ratio", options=["16:9", "9:16"], index=0 if curr_data.get("visual_settings", {}).get("aspect_ratio") == "16:9" else 1)
    with vis_col2:
        art_style = st.text_input("Art Style Prompt*", value=curr_data.get("visual_settings", {}).get("art_style_prompt", "modern webcomic vector style, clean lines, flat shading")).strip()

    st.markdown("**Character Anchor Prompt String*** *(Must contain detailed aesthetic description)*")
    char_anchor = st.text_area(
        "Character Anchor Prompt",
        value=curr_data.get("character_anchor", "Jessica mascot, mid-30s Caucasian female psychologist, blonde hair with soft waves, navy blouse under white lab coat, modern webcomic vector style, clean lines, flat shading."),
        height=100
    ).strip()

    submitted = st.form_submit_button("💾 Save Channel Profile")
    
    if submitted:
        # Strict Form Validations
        errors = []
        
        if not ch_name or len(ch_name) < 2:
            errors.append("Channel Name must be at least 2 characters long.")
        if len(ch_name) > 60:
            errors.append("Channel Name cannot exceed 60 characters.")
            
        if not ch_niche or len(ch_niche) < 5:
            errors.append("Channel Niche description must be at least 5 characters long.")
            
        if not re.match(r"^[\+\-]?\d+(\.\d+)?%$", speed):
            errors.append("Speed Modulation must be in percentage format (e.g. '+0%', '-10%', '+15%').")
            
        if not re.match(r"^[\+\-]?\d+(\.\d+)?(Hz|st)?$", pitch):
            errors.append("Pitch Modulation must be in valid format (e.g. '+0Hz', '-5Hz').")
            
        if not art_style or len(art_style) < 3:
            errors.append("Art Style Prompt must be at least 3 characters long.")
            
        if not char_anchor or len(char_anchor) < 15:
            errors.append("Character Anchor Prompt must be a detailed description (at least 15 characters).")
            
        if errors:
            for err in errors:
                st.error(f"❌ Validation Error: {err}")
        else:
            updated_data = {
                "channel_name": ch_name,
                "niche": ch_niche,
                "voice_settings": {
                    "tts_model": tts_model,
                    "voice_id": voice_id,
                    "speed": speed,
                    "pitch": pitch
                },
                "visual_settings": {
                    "aspect_ratio": aspect_ratio,
                    "art_style_prompt": art_style
                },
                "character_anchor": char_anchor,
                "reference_image_paths": curr_data.get("reference_image_paths", [])
            }
            pm.save_profile(profile_id, updated_data)
            st.session_state["active_profile"] = updated_data
            st.session_state["active_profile_id"] = profile_id
            st.success(f"✅ Successfully validated and saved channel profile '{profile_id}'!")
            st.rerun()

st.markdown("---")
st.subheader("🖼️ Character Reference Images & Moodboard")
uploaded_files = st.file_uploader(
    "Upload Character Reference Images (Max 10MB per file, PNG/JPG/WEBP)",
    accept_multiple_files=True,
    type=["png", "jpg", "jpeg", "webp"]
)

if uploaded_files:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref_dir = os.path.join(base_dir, "data", "reference_images", profile_id)
    os.makedirs(ref_dir, exist_ok=True)
    
    saved_paths = []
    file_errors = []
    
    for file in uploaded_files:
        # File Size Validation (10MB limit)
        if file.size > 10 * 1024 * 1024:
            file_errors.append(f"File '{file.name}' exceeds maximum allowed size of 10MB.")
            continue
            
        f_path = os.path.join(ref_dir, file.name)
        with open(f_path, "wb") as f_out:
            f_out.write(file.getbuffer())
        saved_paths.append(f_path)
        
    if file_errors:
        for err in file_errors:
            st.error(f"❌ Upload Error: {err}")
            
    if saved_paths:
        existing = curr_data.get("reference_image_paths", [])
        # Combine and deduplicate
        combined = list(set(existing + saved_paths))
        curr_data["reference_image_paths"] = combined
        pm.save_profile(profile_id, curr_data)
        st.success(f"✅ Uploaded and validated {len(saved_paths)} reference image(s)!")

# Display current reference images
ref_paths = curr_data.get("reference_image_paths", [])
if ref_paths:
    r_cols = st.columns(min(4, len(ref_paths)))
    for idx, r_path in enumerate(ref_paths):
        if os.path.exists(r_path):
            with r_cols[idx % 4]:
                st.image(r_path, caption=os.path.basename(r_path), use_column_width=True)
