import os
import json
import streamlit as st
import pandas as pd
from backend.session_manager import SessionManager

st.set_page_config(page_title="Session Manager | YouTube Control Center", page_icon="🗂️", layout="wide")

st.title("🗂️ Production Session Manager & Audit Trail Explorer")
st.caption("Manage unique production runs, view API request & response logs, and resume interrupted video pipelines.")

sm = SessionManager()
sessions = sm.list_sessions()

# --- TOP SUMMARY METRICS ---
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

total_count = len(sessions)
completed_count = sum(1 for s in sessions if s.get("status") == "PACKAGED")
in_progress_count = sum(1 for s in sessions if s.get("status") not in ["PACKAGED", "FAILED"])
failed_count = sum(1 for s in sessions if s.get("status") == "FAILED")

with col_m1:
    st.metric("Total Sessions", total_count)
with col_m2:
    st.metric("In Progress / Resumable", in_progress_count)
with col_m3:
    st.metric("Completed & Packaged", completed_count)
with col_m4:
    st.metric("Failed / Interrupted", failed_count)

st.markdown("---")

# --- NEW SESSION CREATION QUICK ACTION ---
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
    # Filter Controls
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

    # GRID CARDS VIEW
    for s in filtered_sessions:
        s_id = s.get("session_id")
        topic = s.get("topic")
        status = s.get("status")
        created_at = s.get("created_at", "")[:19].replace("T", " ")
        updated_at = s.get("updated_at", "")[:19].replace("T", " ")
        curr_step = s.get("current_step", "N/A")
        
        status_color = "🟢" if status == "PACKAGED" else "🔵" if status in ["SCRIPT_GENERATED", "ASSETS_GENERATED", "ASSEMBLED"] else "🔴" if status == "FAILED" else "⚪"
        
        with st.expander(f"{status_color} **{s_id}** — Topic: **{topic}** | Status: `{status}` (Updated: {updated_at})", expanded=False):
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
                st.markdown("### ⚡ Session Actions")
                
                # RESUME SESSION BUTTON
                if st.button(f"▶ Resume Session in Pipeline", key=f"resume_{s_id}"):
                    st.session_state["active_session_id"] = s_id
                    st.session_state["current_topic"] = topic
                    
                    # Load checkpoints if available
                    script_data = sm.load_checkpoint(s_id, "script_data")
                    if script_data:
                        st.session_state["script_data"] = script_data
                        
                    audio_assets = sm.load_checkpoint(s_id, "audio_assets")
                    if audio_assets:
                        st.session_state["audio_assets"] = audio_assets
                        
                    video_assets = sm.load_checkpoint(s_id, "video_assets")
                    if video_assets:
                        st.session_state["video_assets"] = video_assets
                        
                    st.success(f"✅ Session `{s_id}` loaded into active state!")
                    st.switch_page("pages/4_Pipeline.py")

                # DELETE SESSION BUTTON
                if st.button(f"🗑 Delete Session", key=f"del_{s_id}", type="secondary"):
                    sm.delete_session(s_id)
                    st.rerun()

            st.markdown("---")
            st.markdown("### 📜 Audit Trail & Live API Request/Response Log")
            
            audit_entries = sm.get_audit_trail(s_id)
            if not audit_entries:
                st.info("No API audit logs recorded for this session yet.")
            else:
                df_audit = []
                for entry in audit_entries:
                    df_audit.append({
                        "Time": entry.get("timestamp", "")[11:19],
                        "Step": entry.get("step"),
                        "Service / API": entry.get("service"),
                        "Status": entry.get("status"),
                        "Duration (s)": entry.get("duration_sec"),
                        "Request Summary": str(entry.get("request"))[:90] + "...",
                        "Response Summary": str(entry.get("response"))[:90] + "..."
                    })
                st.dataframe(pd.DataFrame(df_audit), use_container_width=True)
                
                # Expandable detailed inspector for each API log entry
                with st.expander("🔍 Detailed Raw Request & Response Inspector"):
                    for idx_a, entry in enumerate(audit_entries, 1):
                        st.markdown(f"#### Entry #{idx_a}: `{entry.get('service')}` — Status: `{entry.get('status')}` ({entry.get('duration_sec')}s)")
                        c_req, c_resp = st.columns(2)
                        with c_req:
                            st.markdown("**📤 Request Payload / Prompt:**")
                            st.json(entry.get("request", {}))
                        with c_resp:
                            st.markdown("**📥 Response Output / Data:**")
                            st.json(entry.get("response", {}))
                        st.markdown("---")
