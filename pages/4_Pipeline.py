import os
import streamlit as st
import pandas as pd
from backend.profile_manager import ProfileManager
from backend.script_engine import generate_script
from backend.audio_engine import generate_audio
from backend.video_engine import generate_video_assets
from backend.assembly_engine import assemble_video
from backend.packaging_engine import package_video

from backend.session_manager import SessionManager

st.set_page_config(page_title="Production Pipeline | YouTube Control Center", page_icon="🚀", layout="wide")

st.title("🚀 Interactive Video Production Pipeline")
st.caption("Generate Gemini 2.5 Script ➔ Human-in-the-Loop Edit ➔ Synthesize Assets ➔ Compile MoviePy Video")

pm = ProfileManager()
sm = SessionManager()

active_profile = st.session_state.get("active_profile", pm.get_profile(st.session_state.get("active_profile_id", "default_psychology")))
competitor_insights = st.session_state.get("competitor_insights", {"seed_topic": st.session_state.get("current_topic", "Dark Psychology")})
topic = competitor_insights.get("seed_topic", "Dark Psychology").strip()

# Initialize or retrieve active session
if "active_session_id" not in st.session_state or not st.session_state["active_session_id"]:
    new_sess = sm.create_session(topic=topic, profile_id=active_profile.get("profile_id", "default_psychology"), profile_name=active_profile.get("channel_name", "Default Psychology"))
    st.session_state["active_session_id"] = new_sess["session_id"]

sess_id = st.session_state["active_session_id"]
sess_meta = sm.get_session(sess_id)

# --- QUICK SESSION BAR ---
c_s1, c_s2 = st.columns([3, 1])
with c_s1:
    st.info(f"🆔 **Active Session:** `{sess_id}` | **Topic:** `{topic}` | **Status:** `{sess_meta.get('status') if sess_meta else 'ACTIVE'}`")
with c_s2:
    st.page_link("pages/5_Sessions.py", label="🗂️ Manage All Sessions", icon="📋")



tab1, tab2, tab3, tab4 = st.tabs([
    "1️⃣ Script Generation",
    "2️⃣ Human-in-the-Loop Editor",
    "3️⃣ Audio & Visual Review",
    "4️⃣ Final Compilation & Packaging"
])

# ----------------------------------------------------
# TAB 1: SCRIPT GENERATION
# ----------------------------------------------------
with tab1:
    st.subheader("📝 Step 1: AI Retention Scriptwriter")
    st.markdown("Generates a retention-focused script using Gemini 2.5 with the **6-Part Retention Framework**.")
    
    st.markdown(f"**Character Anchor Prompt String (Will be prepended to all prompts):**")
    anchor_str = active_profile.get("character_anchor", "").strip()
    st.code(anchor_str if anchor_str else "No character anchor specified in profile!", language="text")

    if st.button("✨ Generate AI Script", type="primary"):
        # Validation checks prior to script generation
        if not topic:
            st.error("❌ Validation Error: Seed topic is missing. Please complete Research phase first.")
        elif not anchor_str:
            st.error("❌ Validation Error: Active Channel Profile must have a Character Anchor Prompt set in Channel Studio.")
        else:
            with st.spinner("Calling Gemini 2.5 to craft 6-part retention script..."):
                gem_key = st.session_state.get("gemini_api_key", "").strip()
                script_data = generate_script(
                    topic=topic,
                    competitor_insights=competitor_insights,
                    channel_profile=active_profile,
                    gemini_api_key=gem_key,
                    session_id=sess_id
                )
                st.session_state["script_data"] = script_data
                st.success("✅ Script Generated Successfully! Switch to Tab 2 to review and edit.")
                
    if "script_data" in st.session_state:
        st.markdown("---")
        st.markdown(f"### 📌 Video Title: {st.session_state['script_data'].get('title')}")
        st.markdown(f"### 🪝 Hook Overlay: `{st.session_state['script_data'].get('hook_statement')}`")

# ----------------------------------------------------
# TAB 2: INTERACTIVE DATA EDITOR
# ----------------------------------------------------
with tab2:
    st.subheader("✏️ Step 2: Interactive Script & Prompt Editor")
    st.caption("Edit spoken text, tweak visual prompts, or adjust target durations prior to asset synthesis.")

    if "script_data" in st.session_state:
        s_data = st.session_state["script_data"]
        scenes = s_data.get("scenes", [])
        
        df_scenes = pd.DataFrame(scenes)
        cols_to_show = ["scene_number", "retention_stage", "spoken_text", "ai_image_prompt", "on_screen_text", "target_duration_sec"]
        for col in cols_to_show:
            if col not in df_scenes.columns:
                df_scenes[col] = ""
                
        edited_df = st.data_editor(
            df_scenes[cols_to_show],
            use_container_width=True,
            num_rows="dynamic",
            key="scene_editor"
        )
        
        if st.button("💾 Save Edited Script Changes"):
            updated_scenes = edited_df.to_dict(orient="records")
            
            # Validation checks for edited scenes
            scene_errors = []
            if not updated_scenes:
                scene_errors.append("Script must contain at least 1 scene.")
                
            for idx, sc in enumerate(updated_scenes, 1):
                txt = str(sc.get("spoken_text", "")).strip()
                prm = str(sc.get("ai_image_prompt", "")).strip()
                try:
                    dur = float(sc.get("target_duration_sec", 0))
                except Exception:
                    dur = 0.0
                    
                if not txt or len(txt) < 5:
                    scene_errors.append(f"Scene {idx}: Spoken text is too short (min 5 characters).")
                if not prm or len(prm) < 5:
                    scene_errors.append(f"Scene {idx}: Visual prompt is too short (min 5 characters).")
                if dur <= 0.5 or dur > 120.0:
                    scene_errors.append(f"Scene {idx}: Duration must be a positive number between 1.0s and 120.0s.")
                    
            if scene_errors:
                for err in scene_errors:
                    st.error(f"❌ Scene Validation Error: {err}")
            else:
                anchor = active_profile.get("character_anchor", "").strip()
                for sc in updated_scenes:
                    p = sc.get("ai_image_prompt", "")
                    if anchor and not p.startswith(anchor[:20]):
                        sc["ai_image_prompt"] = f"{anchor}, {p}"
                s_data["scenes"] = updated_scenes
                st.session_state["script_data"] = s_data
                st.success("✅ Script edits validated and saved!")
    else:
        st.warning("Please generate a script in Tab 1 first.")

# ----------------------------------------------------
# TAB 3: AUDIO & VISUAL ASSETS REVIEW
# ----------------------------------------------------
with tab3:
    st.subheader("🔊 Step 3: Audio Synthesis & Visual Asset Review")
    st.caption("Synthesize voice clips via Fish Audio (OpenRouter) or edge-tts, and generate AI visual clips via Grok.")

    if "script_data" in st.session_state:
        if st.button("🎬 Generate Audio & Video Assets", type="primary"):
            scenes_to_check = st.session_state["script_data"].get("scenes", [])
            if not scenes_to_check:
                st.error("❌ Cannot generate assets: Script contains no valid scenes.")
            else:
                with st.spinner("Synthesizing voice audio & generating AI visual scene assets..."):
                    # Build voice_settings with OpenRouter key
                    vs = dict(active_profile.get("voice_settings", {}))
                    or_key = st.session_state.get("openrouter_api_key", "")
                    if or_key:
                        vs["openrouter_api_key"] = or_key
                    
                    audio_assets = generate_audio(
                        script_data=st.session_state["script_data"],
                        voice_settings=vs,
                        session_id=sess_id
                    )
                    st.session_state["audio_assets"] = audio_assets
                    
                    # Build api_config with OpenRouter key
                    api_cfg = {}
                    if or_key:
                        api_cfg["openrouter_api_key"] = or_key
                    
                    video_assets = generate_video_assets(
                        script_data=st.session_state["script_data"],
                        audio_assets=audio_assets,
                        visual_settings=active_profile.get("visual_settings", {}),
                        api_config=api_cfg,
                        session_id=sess_id
                    )
                    st.session_state["video_assets"] = video_assets
                    st.success("✅ Assets generated! Preview below.")

        if "audio_assets" in st.session_state and "video_assets" in st.session_state:
            st.markdown("---")
            st.subheader("🎞️ Scene Asset Grid (Side-by-Side Review)")
            
            audios = st.session_state["audio_assets"]
            videos = st.session_state["video_assets"]
            
            for idx, (a, v) in enumerate(zip(audios, videos), 1):
                st.markdown(f"#### Scene {idx:02d} - Duration: `{a['duration_sec']:.2f}s`")
                grid_c1, grid_c2 = st.columns([1, 2])
                with grid_c1:
                    st.markdown("**Audio Voice Track (.wav)**")
                    if os.path.exists(a["audio_path"]):
                        st.audio(a["audio_path"])
                    st.write(f"*Text:* \"{a['spoken_text']}\"")
                with grid_c2:
                    st.markdown("**Visual Clip (.mp4)**")
                    if os.path.exists(v["video_path"]):
                        st.video(v["video_path"])
                    st.caption(f"Prompt: {v['prompt'][:120]}...")
                st.markdown("---")
    else:
        st.warning("Please generate a script in Tab 1 first.")

# ----------------------------------------------------
# TAB 4: FINAL ASSEMBLY & PACKAGING
# ----------------------------------------------------
with tab4:
    st.subheader("🎞️ Step 4: Final MoviePy Compilation & Upload Package")
    st.caption("Combines audio tracks, video clips, Ken Burns zoom effects, subtitle overlays, and renders final 1080p video.")

    if "audio_assets" in st.session_state and "video_assets" in st.session_state:
        if st.button("⚡ Compile Final Video & Package SEO", type="primary"):
            auds = st.session_state.get("audio_assets", [])
            vids = st.session_state.get("video_assets", [])
            
            if len(auds) == 0 or len(vids) == 0:
                st.error("❌ Validation Error: Audio or Video assets are missing.")
            elif len(auds) != len(vids):
                st.error("❌ Validation Error: Audio asset count does not match Video asset count.")
            else:
                with st.spinner("Rendering timeline with MoviePy & packaging thumbnail/metadata..."):
                    final_path = assemble_video(
                        script_data=st.session_state["script_data"],
                        audio_assets=st.session_state["audio_assets"],
                        video_assets=st.session_state["video_assets"],
                        visual_settings=active_profile.get("visual_settings", {})
                    )
                    st.session_state["final_video_path"] = final_path
                    
                    pkg_info = package_video(
                        final_video_path=final_path,
                        script_data=st.session_state["script_data"],
                        competitor_insights=competitor_insights
                    )
                    st.session_state["package_info"] = pkg_info
                    
                    # Update session status
                    sm.update_status(sess_id, "PACKAGED", current_step="COMPLETED")
                    sm.save_checkpoint(sess_id, "package_info", pkg_info)
                    
                    st.success("✅ Final Video & Upload Bundle Complete!")

        if "final_video_path" in st.session_state and os.path.exists(st.session_state["final_video_path"]):
            st.markdown("---")
            st.subheader("🎉 Final Render Output")
            
            f_col1, f_col2 = st.columns([2, 1])
            with f_col1:
                st.video(st.session_state["final_video_path"])
                with open(st.session_state["final_video_path"], "rb") as f_vid:
                    st.download_button(
                        label="📥 Download Final Video (.mp4)",
                        data=f_vid,
                        file_name=f"final_video_{topic}.mp4",
                        mime="video/mp4"
                    )
            with f_col2:
                pkg = st.session_state.get("package_info", {})
                t_path = pkg.get("thumbnail_path")
                if t_path and os.path.exists(t_path):
                    st.image(t_path, caption="Generated Thumbnail (JPEG)", use_column_width=True)
                
                m_path = pkg.get("metadata_path")
                if m_path and os.path.exists(m_path):
                    with open(m_path, "r", encoding="utf-8") as f_meta:
                        st.text_area("YouTube Metadata Bundle", f_meta.read(), height=220)
    else:
        st.warning("Please generate audio & video assets in Tab 3 first.")
