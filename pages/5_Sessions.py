import os
import json
import streamlit as st
import pandas as pd
from backend.session_manager import SessionManager

st.set_page_config(page_title="Session Manager | YouTube Control Center", page_icon="🗂️", layout="wide")

st.title("🗂️ Production Session Manager & Data Explorer")
st.caption("All session data is stored in the database and session folders for full offline access.")

sm = SessionManager()
sessions = sm.list_sessions()

# --- TOP SUMMARY METRICS ---
col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

total_count = len(sessions)
completed_count = sum(1 for s in sessions if s.get("status") == "PACKAGED")
in_progress_count = sum(1 for s in sessions if s.get("status") not in ["PACKAGED", "FAILED"])
failed_count = sum(1 for s in sessions if s.get("status") == "FAILED")

with col_m1:
    st.metric("Total Sessions", total_count)
with col_m2:
    st.metric("In Progress", in_progress_count)
with col_m3:
    st.metric("Completed", completed_count)
with col_m4:
    st.metric("Failed", failed_count)
with col_m5:
    db_path = sm.db.db_path
    if os.path.exists(db_path):
        db_size = os.path.getsize(db_path)
        if db_size > 1048576:
            st.metric("Database Size", f"{db_size / 1048576:.1f} MB")
        else:
            st.metric("Database Size", f"{db_size / 1024:.0f} KB")
    else:
        st.metric("Database Size", "0 KB")

st.markdown("---")

# --- NEW SESSION CREATION ---
c_create1, c_create2 = st.columns([3, 1])
with c_create1:
    new_topic = st.text_input("Start New Production Session for Topic:", value="", placeholder="e.g. Behavioral Psychology")
with c_create2:
    st.write(" ")
    st.write(" ")
    if st.button("➕ Create Session", type="primary", use_container_width=True):
        if new_topic.strip():
            active_profile = st.session_state.get("active_profile", {})
            p_id = active_profile.get("profile_id", "default_psychology")
            p_name = active_profile.get("channel_name", "Default Psychology")
            new_sess = sm.create_session(topic=new_topic.strip(), profile_id=p_id, profile_name=p_name)
            st.session_state["active_session_id"] = new_sess["session_id"]
            st.session_state["current_topic"] = new_topic.strip()
            st.success(f"✅ Session Created: `{new_sess['session_id']}`! Redirecting to Pipeline...")
            st.switch_page("pages/4_Pipeline.py")
        else:
            st.error("Please enter a topic name.")

st.markdown("---")
st.subheader("📊 Session Grid View")

if not sessions:
    st.info("No production sessions found. Create your first session above or start research in Pipeline!")
else:
    f_col1, f_col2 = st.columns([2, 2])
    with f_col1:
        search_query = st.text_input("🔍 Search by Topic or Session ID:", "").strip().lower()
    with f_col2:
        status_filter = st.selectbox("Filter Status:", ["ALL", "CREATED", "SCRIPT_GENERATED", "ASSETS_GENERATED", "ASSEMBLED", "PACKAGED", "FAILED"])

    filtered_sessions = []
    for s in sessions:
        s_id = s.get("session_id", "").lower()
        topic = s.get("topic", "").lower()
        status = s.get("status", "")
        if search_query and (search_query not in s_id and search_query not in topic):
            continue
        if status_filter != "ALL" and status != status_filter:
            continue
        filtered_sessions.append(s)

    st.write(f"Showing **{len(filtered_sessions)}** session(s)")

    for s in filtered_sessions:
        s_id = s.get("session_id")
        topic = s.get("topic")
        status = s.get("status")
        created_at = s.get("created_at", "")[:19].replace("T", " ")
        updated_at = s.get("updated_at", "")[:19].replace("T", " ")
        curr_step = s.get("current_step", "N/A")

        status_color = "🟢" if status == "PACKAGED" else "🔵" if status in ["SCRIPT_GENERATED", "ASSETS_GENERATED", "ASSEMBLED"] else "🔴" if status == "FAILED" else "⚪"

        with st.expander(f"{status_color} **{s_id}** — Topic: **{topic}** | Status: `{status}` (Updated: {updated_at})", expanded=False):

            # --- SESSION INFO + ACTIONS ---
            col_info, col_actions = st.columns([3, 2])

            with col_info:
                st.markdown(f"**Session ID:** `{s_id}`")
                st.markdown(f"**Seed Topic:** `{topic}`")
                st.markdown(f"**Profile:** `{s.get('profile_name')}` ({s.get('profile_id')})")
                st.markdown(f"**Created At:** `{created_at}`")
                st.markdown(f"**Current Step:** `{curr_step}`")
                st.markdown(f"**Completed Steps:** `{', '.join(s.get('completed_steps', [])) if s.get('completed_steps') else 'None'}`")
                if s.get("error"):
                    st.error(f"⚠️ Error: {s.get('error')}")

            with col_actions:
                st.markdown("### ⚡ Actions")
                if st.button("▶ Resume in Pipeline", key=f"resume_{s_id}"):
                    st.session_state["active_session_id"] = s_id
                    st.session_state["current_topic"] = topic
                    for cp_name, state_key in [("script_data", "script_data"), ("audio_assets", "audio_assets"), ("video_assets", "video_assets")]:
                        cp_data = sm.load_checkpoint(s_id, cp_name)
                        if cp_data:
                            st.session_state[state_key] = cp_data
                    st.success(f"✅ Session `{s_id}` loaded!")
                    st.switch_page("pages/4_Pipeline.py")

                if st.button("📦 Export Offline Bundle", key=f"export_{s_id}"):
                    bundle_path = sm.export_bundle(s_id)
                    if bundle_path:
                        st.success(f"✅ Bundle exported to: `{bundle_path}`")
                    else:
                        st.error("Failed to export bundle.")

                if st.button("🗑 Delete Session", key=f"del_{s_id}", type="secondary"):
                    sm.delete_session(s_id)
                    st.rerun()

            # --- TABS FOR DETAILED DATA ---
            detail_tabs = st.tabs(["📊 Assets", "📜 Script", "🔍 Research", "📋 Audit Trail", "📂 Files"])

            # TAB: ASSETS
            with detail_tabs[0]:
                asset_summary = sm.get_asset_summary(s_id)
                if asset_summary:
                    a_cols = st.columns(len(asset_summary))
                    for i, (atype, info) in enumerate(asset_summary.items()):
                        with a_cols[i]:
                            size_str = f"{info['total_bytes'] / 1048576:.1f} MB" if info['total_bytes'] > 1048576 else f"{info['total_bytes'] / 1024:.0f} KB"
                            st.metric(f"{atype.title()} Files", f"{info['count']} ({size_str})")

                    all_assets = sm.get_assets(s_id)
                    if all_assets:
                        df_assets = []
                        for a in all_assets:
                            file_exists = os.path.exists(a["file_path"]) if a["file_path"] else False
                            df_assets.append({
                                "Scene": a["scene_number"],
                                "Type": a["asset_type"],
                                "File": a["file_name"],
                                "Size": f"{a['file_size_bytes'] / 1024:.0f} KB" if a["file_size_bytes"] else "0 KB",
                                "Status": a["status"],
                                "Engine/Model": a.get("engine_used") or a.get("model_used") or "",
                                "Duration": f"{a['duration_sec']:.1f}s" if a["duration_sec"] else "",
                                "Exists": "✅" if file_exists else "❌"
                            })
                        st.dataframe(pd.DataFrame(df_assets), use_container_width=True, hide_index=True)

                        st.markdown("**Asset Preview**")
                        audio_assets = [a for a in all_assets if a["asset_type"] == "audio"]
                        video_assets = [a for a in all_assets if a["asset_type"] == "video"]
                        image_assets = [a for a in all_assets if a["asset_type"] == "image"]

                        preview_type = st.radio("Preview:", ["Audio", "Video", "Images"], horizontal=True, key=f"preview_{s_id}")
                        preview_assets = audio_assets if preview_type == "Audio" else video_assets if preview_type == "Video" else image_assets

                        for pa in preview_assets[:12]:
                            fp = pa["file_path"]
                            if not os.path.exists(fp):
                                continue
                            st.markdown(f"**Scene {pa['scene_number']:02d}** — `{pa['file_name']}`")
                            if pa["asset_type"] == "audio":
                                st.audio(fp)
                            elif pa["asset_type"] == "video":
                                st.video(fp)
                            elif pa["asset_type"] == "image":
                                st.image(fp, use_column_width=True)
                            st.caption(f"Status: {pa['status']} | {pa.get('engine_used') or pa.get('model_used') or 'N/A'}")
                else:
                    st.info("No assets registered for this session yet.")

            # TAB: SCRIPT
            with detail_tabs[1]:
                script_meta = sm.db.get_script_meta(s_id)
                if script_meta:
                    sc1, sc2, sc3 = st.columns(3)
                    with sc1:
                        st.metric("Scenes", script_meta.get("scene_count", 0))
                    with sc2:
                        st.metric("Total Words", script_meta.get("total_words", 0))
                    with sc3:
                        st.metric("Target", f"{script_meta.get('target_minutes', 10)} min")

                    st.markdown(f"**Title:** {script_meta.get('title', 'N/A')}")
                    st.markdown(f"**Hook:** {script_meta.get('hook_statement', 'N/A')}")

                    if st.checkbox("Show full script data", key=f"script_{s_id}"):
                        script_data = sm.db.get_script(s_id)
                        if script_data:
                            scenes = script_data.get("scenes", [])
                            for sc in scenes:
                                st.markdown(f"#### Scene {sc.get('scene_number', '?')}: {sc.get('retention_stage', '')}")
                                st.markdown(f"**Spoken Text:**\n{sc.get('spoken_text', '')}")
                                st.markdown(f"**Image Prompt:** `{sc.get('ai_image_prompt', '')[:200]}`")
                                st.markdown(f"**On-Screen Text:** `{sc.get('on_screen_text', '')}`")
                                st.markdown("---")
                else:
                    st.info("No script data saved for this session.")

            # TAB: RESEARCH
            with detail_tabs[2]:
                research = sm.get_research(s_id)
                if research:
                    st.markdown(f"**Seed Topic:** `{research.get('seed_topic', 'N/A')}`")

                    top_videos = research.get("top_videos", [])
                    if top_videos:
                        st.markdown(f"**Top Videos Analyzed:** {len(top_videos)}")
                        for v in top_videos[:5]:
                            st.markdown(f"- **{v.get('title', '')}** — {v.get('channel', '')} ({v.get('views', 0):,} views)")

                    gaps = research.get("content_gaps", [])
                    if gaps:
                        st.markdown("**Content Gaps:**")
                        for g in gaps:
                            st.info(f"• {g}")

                    triggers = research.get("emotional_triggers", [])
                    if triggers:
                        st.markdown("**Emotional Triggers:**")
                        for t in triggers:
                            st.warning(f"• {t}")

                    tropes = research.get("common_tropes", [])
                    if tropes:
                        st.markdown("**Common Tropes:**")
                        for tr in tropes:
                            st.success(f"• {tr}")

                    angle = research.get("recommended_angle", "")
                    if angle:
                        st.markdown(f"**Recommended Angle:** {angle}")
                else:
                    st.info("No competitor research saved for this session.")

            # TAB: AUDIT TRAIL
            with detail_tabs[3]:
                cost_summary = sm.get_api_cost_summary(s_id)
                ac1, ac2, ac3 = st.columns(3)
                with ac1:
                    st.metric("Total API Calls", cost_summary.get("total_calls", 0))
                with ac2:
                    st.metric("Success", cost_summary.get("success_count", 0))
                with ac3:
                    total_time = cost_summary.get("total_api_time") or 0
                    st.metric("Total API Time", f"{total_time:.1f}s")

                audit_entries = sm.get_audit_trail(s_id)
                if audit_entries:
                    df_audit = []
                    for entry in audit_entries:
                        df_audit.append({
                            "Time": entry.get("timestamp", "")[11:19],
                            "Step": entry.get("step"),
                            "Service": entry.get("service"),
                            "Status": entry.get("status"),
                            "Duration (s)": entry.get("duration_sec"),
                            "Request": str(entry.get("request"))[:90] + "...",
                            "Response": str(entry.get("response"))[:90] + "..."
                        })
                    st.dataframe(pd.DataFrame(df_audit), use_container_width=True, hide_index=True)

                    if st.checkbox("🔍 Inspect Raw Payloads", key=f"inspect_{s_id}"):
                        for idx_a, entry in enumerate(audit_entries, 1):
                            st.markdown(f"#### Entry #{idx_a}: `{entry.get('step')}` — `{entry.get('service')}` ({entry.get('status')} | {entry.get('duration_sec')}s)")
                            c_req, c_resp = st.columns(2)
                            with c_req:
                                st.markdown("**📤 Request:**")
                                st.json(entry.get("request", {}))
                            with c_resp:
                                st.markdown("**📥 Response:**")
                                st.json(entry.get("response", {}))
                            st.markdown("---")
                else:
                    st.info("No API audit logs recorded for this session yet.")

            # TAB: FILES ON DISK
            with detail_tabs[4]:
                sess_dir = sm.get_session_dir(s_id)
                if os.path.exists(sess_dir):
                    st.markdown(f"**Session Directory:** `{sess_dir}`")

                    all_files = []
                    for root, dirs, files in os.walk(sess_dir):
                        for fname in files:
                            fpath = os.path.join(root, fname)
                            rel_path = os.path.relpath(fpath, sess_dir)
                            fsize = os.path.getsize(fpath)
                            all_files.append({
                                "File": rel_path,
                                "Size": f"{fsize / 1024:.1f} KB" if fsize < 1048576 else f"{fsize / 1048576:.1f} MB",
                                "Size (bytes)": fsize
                            })

                    if all_files:
                        total_size = sum(f["Size (bytes)"] for f in all_files)
                        size_str = f"{total_size / 1048576:.1f} MB" if total_size > 1048576 else f"{total_size / 1024:.0f} KB"
                        st.markdown(f"**{len(all_files)} files** | **Total: {size_str}**")

                        display_files = [{k: v for k, v in f.items() if k != "Size (bytes)"} for f in all_files]
                        st.dataframe(pd.DataFrame(display_files), use_container_width=True, hide_index=True)

                        bundle_path = os.path.join(sess_dir, "session_bundle.json")
                        if os.path.exists(bundle_path):
                            st.success(f"✅ Offline bundle available: `session_bundle.json` ({os.path.getsize(bundle_path) / 1024:.0f} KB)")
                        else:
                            if st.button("Generate Offline Bundle", key=f"gen_bundle_{s_id}"):
                                bp = sm.export_bundle(s_id)
                                if bp:
                                    st.success(f"✅ Bundle generated: `{bp}`")
                                    st.rerun()
                    else:
                        st.info("Session directory is empty.")
                else:
                    st.warning("Session directory not found on disk.")
