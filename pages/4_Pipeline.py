import os
import streamlit as st
import pandas as pd
from backend.profile_manager import ProfileManager
from backend.script_engine import generate_script
from backend.audio_engine import generate_audio_scene, get_audio_duration
from backend.video_engine import generate_video_scene, generate_image_scene, generate_video_from_image
from backend.assembly_engine import assemble_video
from backend.packaging_engine import package_video
from backend.session_manager import SessionManager

st.set_page_config(page_title="Production Pipeline | YouTube Control Center", page_icon="🚀", layout="wide")

st.title("🚀 Interactive Video Production Pipeline")
st.caption("Generate Script ➔ Human-in-the-Loop Edit ➔ Synthesize Assets ➔ Compile Video")

pm = ProfileManager()
sm = SessionManager()

active_profile = st.session_state.get("active_profile", pm.get_profile(st.session_state.get("active_profile_id", "default_psychology")))
competitor_insights = st.session_state.get("competitor_insights", {"seed_topic": st.session_state.get("current_topic", "Dark Psychology")})
topic = competitor_insights.get("seed_topic", "Dark Psychology").strip()

# --- SESSION INITIALIZATION WITH CHECKPOINT LOADING ---
if "active_session_id" not in st.session_state or not st.session_state["active_session_id"]:
    new_sess = sm.create_session(
        topic=topic,
        profile_id=active_profile.get("profile_id", st.session_state.get("active_profile_id", "default_psychology")),
        profile_name=active_profile.get("channel_name", "Default Psychology")
    )
    st.session_state["active_session_id"] = new_sess["session_id"]
else:
    sess_check = sm.get_session(st.session_state["active_session_id"])
    if sess_check:
        for cp_name, state_key in [("script_data", "script_data"), ("audio_assets", "audio_assets"), ("video_assets", "video_assets")]:
            if state_key not in st.session_state:
                cp_data = sm.load_checkpoint(st.session_state["active_session_id"], cp_name)
                if cp_data:
                    st.session_state[state_key] = cp_data

sess_id = st.session_state["active_session_id"]
sess_meta = sm.get_session(sess_id)
sess_dir = sm.get_session_dir(sess_id)

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

    st.markdown(f"**Character Anchor Prompt String (prepended to all visual prompts):**")
    anchor_str = active_profile.get("character_anchor", "").strip()

    edited_anchor = st.text_area(
        "Edit Character Anchor Prompt String",
        value=anchor_str,
        height=90,
        key="editable_character_anchor",
        help="This prompt string will be automatically prepended to all visual prompts for character consistency."
    ).strip()

    if edited_anchor and edited_anchor != anchor_str:
        active_profile["character_anchor"] = edited_anchor
        p_id = st.session_state.get("active_profile_id", "default_psychology")
        pm.save_profile(p_id, active_profile)
        st.session_state["active_profile"] = active_profile
        st.toast("✅ Character Anchor updated & saved to profile!")

    anchor_str = edited_anchor

    target_length = st.select_slider(
        "Target Video Length (minutes)",
        options=[5, 10, 15, 20],
        value=10,
        help="Controls how many scenes and words the AI generates. 10 min = ~1800 words across 10-14 scenes."
    )

    # --- FIXED MASTER PROMPT TEMPLATE (editable) ---
    _prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "prompts", "script_master_prompt.txt")
    with st.expander("📝 Master Script Prompt Template (fixed prompt with dynamic pros/cons)", expanded=False):
        st.caption(
            "This fixed template drives every script generation. Dynamic values are injected at generation time: "
            "`$topic`, `$niche`, `$target_minutes`, `$content_gaps`, `$emotional_triggers`, `$framework`, "
            "`$scene_count`, `$words_per_scene`, `$total_words`, `$script_pros`, `$script_cons`, "
            "`$transcript_context`, `$comment_context`, `$tropes_text`, `$recommended_angle`, `$art_style`."
        )
        _current_template = ""
        if os.path.exists(_prompt_path):
            with open(_prompt_path, "r", encoding="utf-8") as _f:
                _current_template = _f.read()
        _edited_template = st.text_area("Template", value=_current_template, height=400, key="master_prompt_editor", label_visibility="collapsed")
        if st.button("💾 Save Prompt Template"):
            if len(_edited_template.strip()) < 100:
                st.error("Template too short — must be at least 100 characters.")
            else:
                os.makedirs(os.path.dirname(_prompt_path), exist_ok=True)
                with open(_prompt_path, "w", encoding="utf-8") as _f:
                    _f.write(_edited_template)
                st.success("✅ Master prompt template saved! It will be used for all future script generations.")

    if st.button("✨ Generate AI Script", type="primary"):
        if not topic:
            st.error("❌ Seed topic is missing. Please complete Research phase first.")
        elif not anchor_str:
            st.error("❌ Character Anchor Prompt must be set in Channel Studio.")
        else:
            with st.spinner(f"Calling Gemini to craft {target_length}-minute retention script..."):
                gem_key = st.session_state.get("gemini_api_key", "").strip()
                script_data = generate_script(
                    topic=topic,
                    competitor_insights=competitor_insights,
                    channel_profile=active_profile,
                    gemini_api_key=gem_key,
                    session_id=sess_id,
                    target_video_length_minutes=target_length
                )
                st.session_state["script_data"] = script_data
                sm.save_checkpoint(sess_id, "script_data", script_data)
                if competitor_insights and not competitor_insights.get("error_notice"):
                    sm.save_research(sess_id, topic, competitor_insights)
                total_words = sum(len(s.get("spoken_text", "").split()) for s in script_data.get("scenes", []))
                st.success(f"✅ Script Generated! {len(script_data.get('scenes', []))} scenes, {total_words} words (~{total_words/150:.0f} min). Switch to Tab 2 to review.")

    if "script_data" in st.session_state:
        st.markdown("---")
        sd = st.session_state["script_data"]
        st.markdown(f"### 📌 Video Title: {sd.get('title')}")
        st.markdown(f"### 🪝 Hook Overlay: `{sd.get('hook_statement')}`")
        scenes = sd.get("scenes", [])
        total_words = sum(len(s.get("spoken_text", "").split()) for s in scenes)
        st.caption(f"{len(scenes)} scenes | {total_words} words | ~{total_words/150:.1f} min estimated")

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
        cols_to_show = ["scene_number", "retention_stage", "spoken_text", "ai_image_prompt", "image_to_video_prompt", "on_screen_text", "target_duration_sec"]
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
                    scene_errors.append(f"Scene {idx}: Duration must be between 1.0s and 120.0s.")

            if scene_errors:
                for err in scene_errors:
                    st.error(f"❌ {err}")
            else:
                anchor = active_profile.get("character_anchor", "").strip()
                art_style = active_profile.get("visual_settings", {}).get("art_style_prompt", "")
                for sc in updated_scenes:
                    p = sc.get("ai_image_prompt", "")
                    if anchor and not p.startswith(anchor[:20]):
                        sc["ai_image_prompt"] = f"{anchor}, {p}"
                        if art_style:
                            sc["ai_image_prompt"] += f", style: {art_style}"
                s_data["scenes"] = updated_scenes
                st.session_state["script_data"] = s_data
                sm.save_checkpoint(sess_id, "script_data", s_data)
                st.success("✅ Script edits validated and saved!")
    else:
        st.warning("Please generate a script in Tab 1 first.")

# ----------------------------------------------------
# TAB 3: AUDIO & VISUAL ASSETS — PER-SCENE STATUS CARDS
# ----------------------------------------------------
with tab3:
    st.subheader("🔊 Step 3: Audio Synthesis & Visual Asset Generation")
    st.caption("Each scene is processed individually with full request/response tracking.")

    if "script_data" in st.session_state:
        scenes_list = st.session_state["script_data"].get("scenes", [])

        if not scenes_list:
            st.error("❌ Script contains no scenes.")
        else:
            # Voice settings
            vs = dict(active_profile.get("voice_settings", {}))
            or_key = st.session_state.get("openrouter_api_key", "")
            if or_key:
                vs["openrouter_api_key"] = or_key

            api_cfg = {}
            if or_key:
                api_cfg["openrouter_api_key"] = or_key

            audio_dir = os.path.join(sess_dir, "audio_assets")
            video_dir = os.path.join(sess_dir, "video_assets")

            # Initialize scene status tracking
            if "scene_status" not in st.session_state:
                st.session_state["scene_status"] = {}

            if st.button("🎬 Generate Audio & Video Assets", type="primary"):
                st.session_state["audio_assets"] = []
                st.session_state["video_assets"] = []
                st.session_state["scene_status"] = {}
                image_infos = {}

                progress_bar = st.progress(0, text="Starting asset generation...")
                total_steps = len(scenes_list) * 3  # TTS + Image + Video per scene

                for idx, scene in enumerate(scenes_list, 1):
                    st.session_state["scene_status"][idx] = {"tts": "pending", "image": "pending", "video": "pending"}

                # ============================================================
                # PHASE 1: AUDIO + IMAGES FOR ALL SCENES (fast, reviewable)
                # ============================================================
                st.markdown("## 🎙️ Phase 1: Voice & Images")

                for idx, scene in enumerate(scenes_list, 1):
                    phase1_status = st.status(f"Scene {idx:02d} — {scene.get('retention_stage', '')} | Audio & Image", expanded=True)
                    with phase1_status:
                        # --- TTS ---
                        st.session_state["scene_status"][idx]["tts"] = "in_progress"
                        tts_placeholder = st.empty()
                        tts_placeholder.info("🎙️ Generating audio (TTS)...")

                        audio_result = generate_audio_scene(scene, idx, vs, audio_dir, session_id=sess_id)
                        st.session_state["audio_assets"].append(audio_result)
                        if audio_result.get("audio_path"):
                            sm.register_asset(
                                sess_id, idx, "audio", audio_result["audio_path"],
                                status=audio_result.get("status", "GENERATED"),
                                engine_used=audio_result.get("engine_used", ""),
                                duration_sec=audio_result.get("duration_sec", 0.0),
                                api_duration_sec=audio_result.get("api_duration_sec", 0.0)
                            )

                        if audio_result["status"] == "CACHED":
                            tts_placeholder.success(f"🎙️ Audio: **CACHED** | {audio_result['duration_sec']:.1f}s | {audio_result['engine_used']}")
                        elif audio_result["status"] == "SUCCESS":
                            tts_placeholder.success(f"🎙️ Audio: **{audio_result['engine_used']}** | {audio_result['duration_sec']:.1f}s | API: {audio_result['api_duration_sec']:.1f}s")
                        else:
                            tts_placeholder.warning(f"🎙️ Audio: **FALLBACK** ({audio_result['engine_used']}) | {audio_result['duration_sec']:.1f}s")
                        st.session_state["scene_status"][idx]["tts"] = audio_result["status"].lower()

                        # ▶ PLAYABLE AUDIO right in the progress card
                        if audio_result.get("audio_path") and os.path.exists(audio_result["audio_path"]):
                            st.audio(audio_result["audio_path"])

                        progress_bar.progress((idx * 3 - 2) / total_steps, text=f"Scene {idx}/{len(scenes_list)}: Audio done, generating image...")

                        # --- IMAGE ---
                        st.session_state["scene_status"][idx]["image"] = "in_progress"
                        img_placeholder = st.empty()
                        img_placeholder.info("🎨 Generating AI image...")

                        image_info = generate_image_scene(scene, idx, video_dir, api_cfg, session_id=sess_id)
                        image_infos[idx] = image_info

                        if image_info.get("image_path"):
                            sm.register_asset(
                                sess_id, idx, "image", image_info["image_path"],
                                status=image_info.get("status", "GENERATED"),
                                model_used=image_info.get("image_model", "")
                            )
                            if image_info["status"] == "CACHED":
                                img_placeholder.success("🎨 Image: **CACHED**")
                            else:
                                img_placeholder.success(f"🎨 Image: **{image_info.get('image_model', '?')}** | API: {image_info.get('image_api_duration_sec', 0):.1f}s")
                            # 🖼️ SHOW THE GENERATED IMAGE right in the progress card
                            st.image(image_info["image_path"], caption=f"Scene {idx:02d} — {image_info.get('image_model', 'AI image')}", width=480)
                        else:
                            img_placeholder.error("🎨 Image: **FAILED** — all AI image models failed (will use local vector animation for video)")

                        st.session_state["scene_status"][idx]["image"] = "success" if image_info.get("image_path") else "fallback"

                        st.markdown("**Audio & Image Request/Response** (click to expand)")
                        st.json({
                            "tts_request": {
                                "scene": idx,
                                "spoken_text": audio_result["spoken_text"][:200] + "..." if len(audio_result.get("spoken_text", "")) > 200 else audio_result.get("spoken_text", ""),
                                "engine": audio_result["engine_used"],
                                "voice": vs.get("fish_voice_id", vs.get("voice_id", "default"))
                            },
                            "tts_response": {
                                "status": audio_result["status"],
                                "duration_sec": audio_result["duration_sec"],
                                "api_duration_sec": audio_result["api_duration_sec"],
                                "output_path": audio_result["audio_path"]
                            },
                            "image_request": {
                                "prompt": scene.get("ai_image_prompt", "")[:300],
                                "models_tried": [a.get("model") for a in image_info.get("image_attempts", [])]
                            },
                            "image_response": {
                                "status": image_info.get("status"),
                                "model_used": image_info.get("image_model"),
                                "attempts": image_info.get("image_attempts", []),
                                "output_path": image_info.get("image_path")
                            }
                        }, expanded=False)

                        progress_bar.progress((idx * 3 - 1) / total_steps, text=f"Scene {idx}/{len(scenes_list)}: Audio & image done")

                    a_ok = audio_result["status"] in ("SUCCESS", "CACHED")
                    i_ok = image_info.get("image_path") is not None
                    phase1_status.update(
                        label=f"Scene {idx:02d} — Audio: {'✅' if a_ok else '⚠️'} | Image: {'✅' if i_ok else '❌'}",
                        state="complete" if (a_ok and i_ok) else "error",
                        expanded=False
                    )

                sm.save_checkpoint(sess_id, "audio_assets", st.session_state["audio_assets"])
                st.success(f"✅ Phase 1 complete: {len(scenes_list)} voices & images generated. Starting video generation...")

                # ============================================================
                # PHASE 2: VIDEO GENERATION (slow async API calls at the end)
                # ============================================================
                st.markdown("## 🎬 Phase 2: Video Generation")

                def make_poll_callback(placeholder, scene_idx):
                    def callback(attempt, max_polls, elapsed, status):
                        if status == "polling":
                            placeholder.caption(f"⏳ Polling video model... attempt {attempt}/{max_polls} ({elapsed:.0f}s elapsed)")
                        elif status == "completed":
                            placeholder.caption(f"✅ Video generation completed ({elapsed:.0f}s)")
                        elif status == "failed":
                            placeholder.caption(f"❌ Video generation failed ({elapsed:.0f}s)")
                        elif status == "timeout":
                            placeholder.caption(f"⏰ Video generation timed out ({elapsed:.0f}s)")
                    return callback

                for idx, scene in enumerate(scenes_list, 1):
                    audio_result = st.session_state["audio_assets"][idx - 1]
                    image_info = image_infos.get(idx, {})

                    phase2_status = st.status(f"Scene {idx:02d} — Video", expanded=True)
                    with phase2_status:
                        st.session_state["scene_status"][idx]["video"] = "in_progress"
                        video_placeholder = st.empty()
                        video_placeholder.info("🎬 Submitting video generation job...")
                        poll_status_placeholder = st.empty()

                        video_result = generate_video_from_image(
                            scene, audio_result, idx, image_info,
                            video_dir, api_cfg,
                            session_id=sess_id,
                            poll_callback=make_poll_callback(poll_status_placeholder, idx)
                        )
                        st.session_state["video_assets"].append(video_result)
                        if video_result.get("video_path"):
                            sm.register_asset(
                                sess_id, idx, "video", video_result["video_path"],
                                status=video_result.get("status", "GENERATED"),
                                model_used=video_result.get("video_model", ""),
                                duration_sec=video_result.get("duration_sec", 0.0),
                                api_duration_sec=video_result.get("total_api_duration_sec", 0.0)
                            )

                        v_status = video_result.get("status", "FALLBACK")
                        if v_status == "SUCCESS":
                            video_placeholder.success(f"🎬 Video: **AI Generated** | Model: {video_result.get('video_model', '?')} | {video_result.get('video_api_duration_sec', 0):.1f}s")
                        elif v_status == "IMAGE_ONLY":
                            video_placeholder.warning(f"🎬 Video: **Still Image** (video gen failed) | Error: {video_result.get('video_error', '')[:120]}")
                        else:
                            video_placeholder.error("🎬 Video: **FALLBACK** (local vector animation)")

                        st.session_state["scene_status"][idx]["video"] = v_status.lower()

                        st.markdown("**Video Request/Response** (click to expand)")
                        st.json({
                            "video_request": {
                                "motion_prompt": scene.get("image_to_video_prompt", ""),
                                "source_image": image_info.get("image_path")
                            },
                            "video_response": {
                                "status": v_status,
                                "model_used": video_result.get("video_model"),
                                "error": video_result.get("video_error", ""),
                                "api_duration_sec": video_result.get("video_api_duration_sec", 0)
                            }
                        }, expanded=False)

                        progress_bar.progress((len(scenes_list) * 2 + idx) / total_steps, text=f"Scene {idx}/{len(scenes_list)}: Video done")

                    phase2_status.update(
                        label=f"Scene {idx:02d} — Video: {'✅ AI' if v_status == 'SUCCESS' else '🖼️ Still' if v_status == 'IMAGE_ONLY' else '⚠️ Fallback'}",
                        state="complete" if v_status in ("SUCCESS", "CACHED") else "error" if v_status == "FALLBACK" else "running",
                        expanded=False
                    )

                # --- GENERATION SUMMARY ---
                progress_bar.progress(1.0, text="All scenes processed!")

                audios = st.session_state["audio_assets"]
                videos = st.session_state["video_assets"]

                ai_video_ok = sum(1 for v in videos if v.get("status") == "SUCCESS")
                image_only = sum(1 for v in videos if v.get("status") == "IMAGE_ONLY")
                fallback = sum(1 for v in videos if v.get("status") == "FALLBACK")
                cached = sum(1 for v in videos if v.get("status") == "CACHED")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("AI Video", ai_video_ok)
                col2.metric("Image Only", image_only)
                col3.metric("Fallback", fallback)
                col4.metric("Cached", cached)

                if fallback > 0:
                    st.warning(f"⚠️ {fallback}/{len(videos)} scenes fell back to local MoviePy animation — OpenRouter video generation failed for these scenes.")
                if image_only > 0:
                    st.info(f"ℹ️ {image_only}/{len(videos)} scenes have AI images but video generation failed — using still-image videos.")

                total_api_cost_time = sum(v.get("total_api_duration_sec", 0) for v in videos)
                total_audio_api_time = sum(a.get("api_duration_sec", 0) for a in audios)
                st.caption(f"Total API time: Audio {total_audio_api_time:.1f}s + Video {total_api_cost_time:.1f}s = {total_audio_api_time + total_api_cost_time:.1f}s")

                sm.save_checkpoint(sess_id, "audio_assets", st.session_state["audio_assets"])
                sm.save_checkpoint(sess_id, "video_assets", st.session_state["video_assets"])
                sm.update_status(sess_id, "ASSETS_GENERATED", current_step="ASSEMBLY")
                sm.export_bundle(sess_id)
                st.success("✅ All assets generated & saved to database! Proceed to Tab 4 to compile.")

            # --- PREVIEW EXISTING ASSETS ---
            if "audio_assets" in st.session_state and "video_assets" in st.session_state:
                audios = st.session_state["audio_assets"]
                videos = st.session_state["video_assets"]

                if audios and videos:
                    st.markdown("---")
                    st.subheader("🎞️ Asset Preview")

                    for idx, (a, v) in enumerate(zip(audios, videos), 1):
                        with st.expander(f"Scene {idx:02d} — {a.get('duration_sec', 0):.1f}s | Audio: {a.get('status', '?')} | Video: {v.get('status', '?')}", expanded=False):
                            grid_c1, grid_c2 = st.columns([1, 2])
                            with grid_c1:
                                st.markdown("**Audio**")
                                if os.path.exists(a.get("audio_path", "")):
                                    st.audio(a["audio_path"])
                                st.caption(f"{a.get('engine_used', '?')} | {a.get('duration_sec', 0):.1f}s")
                            with grid_c2:
                                st.markdown("**Video**")
                                if os.path.exists(v.get("video_path", "")):
                                    st.video(v["video_path"])
                                st.caption(f"Status: {v.get('status', '?')} | Model: {v.get('image_model', 'N/A')}")

                    # Per-scene retry
                    st.markdown("---")
                    retry_col1, retry_col2 = st.columns([1, 3])
                    with retry_col1:
                        retry_scene = st.number_input("Scene to retry", min_value=1, max_value=len(scenes_list), value=1, step=1)
                    with retry_col2:
                        retry_opts = st.multiselect("Retry what?", ["Audio (TTS)", "Image + Video"], default=["Image + Video"])

                    if st.button("🔄 Retry Selected Scene"):
                        scene_data = scenes_list[retry_scene - 1]
                        if "Audio (TTS)" in retry_opts:
                            existing = os.path.join(audio_dir, f"scene_{retry_scene:02d}.mp3")
                            if os.path.exists(existing):
                                os.remove(existing)
                            existing_wav = os.path.join(audio_dir, f"scene_{retry_scene:02d}.wav")
                            if os.path.exists(existing_wav):
                                os.remove(existing_wav)
                            new_audio = generate_audio_scene(scene_data, retry_scene, vs, audio_dir, session_id=sess_id)
                            st.session_state["audio_assets"][retry_scene - 1] = new_audio
                            if new_audio.get("audio_path"):
                                sm.register_asset(sess_id, retry_scene, "audio", new_audio["audio_path"],
                                    status=new_audio.get("status", "GENERATED"),
                                    engine_used=new_audio.get("engine_used", ""),
                                    duration_sec=new_audio.get("duration_sec", 0.0),
                                    api_duration_sec=new_audio.get("api_duration_sec", 0.0))
                            st.success(f"✅ Audio for scene {retry_scene} regenerated: {new_audio['status']}")

                        if "Image + Video" in retry_opts:
                            existing_mp4 = os.path.join(video_dir, f"scene_{retry_scene:02d}.mp4")
                            if os.path.exists(existing_mp4):
                                os.remove(existing_mp4)
                            existing_png = os.path.join(video_dir, f"scene_{retry_scene:02d}.png")
                            if os.path.exists(existing_png):
                                os.remove(existing_png)
                            audio_info = st.session_state["audio_assets"][retry_scene - 1]
                            new_video = generate_video_scene(
                                scene_data, audio_info, retry_scene,
                                active_profile.get("visual_settings", {}),
                                video_dir, api_cfg, session_id=sess_id
                            )
                            st.session_state["video_assets"][retry_scene - 1] = new_video
                            if new_video.get("video_path"):
                                sm.register_asset(sess_id, retry_scene, "video", new_video["video_path"],
                                    status=new_video.get("status", "GENERATED"),
                                    model_used=new_video.get("video_model", ""),
                                    duration_sec=new_video.get("duration_sec", 0.0),
                                    api_duration_sec=new_video.get("total_api_duration_sec", 0.0))
                            if new_video.get("image_path"):
                                sm.register_asset(sess_id, retry_scene, "image", new_video["image_path"],
                                    status="GENERATED", model_used=new_video.get("image_model", ""))
                            st.success(f"✅ Video for scene {retry_scene} regenerated: {new_video['status']}")

                        st.rerun()

            # Audit trail
            st.markdown("---")
            st.subheader("📋 Session Audit Trail")
            sess_audit = sm.get_audit_trail(sess_id)
            if sess_audit:
                with st.expander(f"View Full Audit Trail ({len(sess_audit)} entries)", expanded=False):
                    df_audit = []
                    for entry in sess_audit:
                        df_audit.append({
                            "Time": entry.get("timestamp", "")[11:19],
                            "Step": entry.get("step"),
                            "Service": entry.get("service"),
                            "Status": entry.get("status"),
                            "Duration (s)": entry.get("duration_sec"),
                            "Request": str(entry.get("request"))[:120],
                            "Response": str(entry.get("response"))[:120]
                        })
                    st.dataframe(pd.DataFrame(df_audit), use_container_width=True)
    else:
        st.warning("Please generate a script in Tab 1 first.")

# ----------------------------------------------------
# TAB 4: FINAL ASSEMBLY & PACKAGING
# ----------------------------------------------------
with tab4:
    st.subheader("🎞️ Step 4: Final MoviePy Compilation & Upload Package")

    if "audio_assets" in st.session_state and "video_assets" in st.session_state:
        if st.button("⚡ Compile Final Video & Package SEO", type="primary"):
            auds = st.session_state.get("audio_assets", [])
            vids = st.session_state.get("video_assets", [])

            if len(auds) == 0 or len(vids) == 0:
                st.error("❌ Audio or Video assets are missing.")
            elif len(auds) != len(vids):
                st.error("❌ Audio asset count does not match Video asset count.")
            else:
                with st.spinner("Rendering timeline with MoviePy & packaging thumbnail/metadata..."):
                    final_path = assemble_video(
                        script_data=st.session_state["script_data"],
                        audio_assets=st.session_state["audio_assets"],
                        video_assets=st.session_state["video_assets"],
                        visual_settings=active_profile.get("visual_settings", {}),
                        session_id=sess_id
                    )
                    st.session_state["final_video_path"] = final_path

                    pkg_info = package_video(
                        final_video_path=final_path,
                        script_data=st.session_state["script_data"],
                        competitor_insights=competitor_insights,
                        session_id=sess_id,
                        audio_assets=st.session_state["audio_assets"]
                    )
                    st.session_state["package_info"] = pkg_info

                    sm.update_status(sess_id, "PACKAGED", current_step="COMPLETED")
                    sm.save_checkpoint(sess_id, "package_info", pkg_info)

                    if final_path and os.path.exists(final_path):
                        sm.register_asset(sess_id, 0, "final_video", final_path, status="COMPILED")
                    t_path = pkg_info.get("thumbnail_path", "")
                    if t_path and os.path.exists(t_path):
                        sm.register_asset(sess_id, 0, "thumbnail", t_path, status="GENERATED")

                    sm.export_bundle(sess_id)
                    st.success("✅ Final Video & Upload Bundle Complete! All data saved to database.")

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
