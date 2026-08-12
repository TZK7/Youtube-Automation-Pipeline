import os
import re
import datetime
import streamlit as st
import pandas as pd
from backend.competitor_engine import analyze_competitors
from backend.session_manager import SessionManager


st.set_page_config(page_title="Market Research | YouTube Control Center", page_icon="🔍", layout="wide")

st.title("🔍 Market Intelligence & Transcript Analysis")
st.caption("Perform automated competitor research via YouTube Data API v3, YouTube Transcript API, and Gemini 3.6 Flash.")

col_in, col_btn = st.columns([4, 1])

with col_in:
    topic_input = st.text_input(
        "Target Seed Topic*",
        value=st.session_state.get("current_topic", "Stoic Calmness"),
        placeholder="e.g. Stoic Calmness"
    ).strip()

with col_btn:
    st.write(" ")
    st.write(" ")
    run_analysis = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

force_refresh = st.checkbox(
    "🔄 Force fresh fetch (ignore cached research — spends API quota)",
    value=False,
    help="Research results are cached in the database for 72 hours per topic. Leave unchecked to reuse cached data at zero API cost."
)

# --- RESEARCH HISTORY (cached topics — reload without any API calls) ---
_sm_hist = SessionManager()
cached_topics = _sm_hist.db.list_research_cache()
if cached_topics:
    with st.expander(f"🗂️ Research History ({len(cached_topics)} cached topics — reload at zero API cost)", expanded=False):
        for c_idx, c_entry in enumerate(cached_topics):
            h_col1, h_col2, h_col3 = st.columns([3, 2, 1])
            with h_col1:
                st.markdown(f"**{c_entry['seed_topic']}**")
            with h_col2:
                st.caption(f"Fetched: {c_entry['created_at'][:19].replace('T', ' ')}")
            with h_col3:
                if st.button("📂 Load", key=f"load_hist_{c_idx}"):
                    cached_data = _sm_hist.db.get_research_cache(c_entry["seed_topic"])
                    if cached_data:
                        st.session_state["competitor_insights"] = cached_data
                        st.session_state["current_topic"] = c_entry["seed_topic"]
                        st.rerun()

if run_analysis:
    if not topic_input:
        st.error("❌ Validation Error: Target Seed Topic cannot be empty.")
    elif len(topic_input) < 2:
        st.error("❌ Validation Error: Target Seed Topic must be at least 2 characters long.")
    elif len(topic_input) > 80:
        st.error("❌ Validation Error: Target Seed Topic cannot exceed 80 characters.")
    elif not re.match(r"^[a-zA-Z0-9\s\-_,\.\'\"]+$", topic_input):
        st.error("❌ Validation Error: Seed topic contains invalid special characters.")
    else:
        # Clear previous session state cache to prevent showing stale results
        if "competitor_insights" in st.session_state:
            del st.session_state["competitor_insights"]
            
        st.session_state["current_topic"] = topic_input
        yt_key = st.session_state.get("youtube_api_key", "").strip()
        gem_key = st.session_state.get("gemini_api_key", "").strip()
        
        with st.spinner(f"Fetching live YouTube videos, extracting spoken transcripts, and analyzing audience comments for '{topic_input}'..."):
            insights = analyze_competitors(
                seed_topic=topic_input,
                youtube_api_key=yt_key,
                gemini_api_key=gem_key,
                use_cache=not force_refresh
            )
            st.session_state["competitor_insights"] = insights
            if insights.get("error_notice"):
                st.error(f"⚠️ {insights.get('error_notice')}")
            else:
                _sm = SessionManager()
                _active_sid = st.session_state.get("active_session_id")
                if _active_sid:
                    _sm.save_research(_active_sid, topic_input, insights)
                if insights.get("from_cache"):
                    st.success(f"✅ Loaded from research cache (fetched {insights.get('_cached_at', '?')[:19].replace('T', ' ')}) — no API quota spent! Use 'Force fresh fetch' for new data.")
                else:
                    st.success(f"✅ Live Competitor Analysis Complete for '{topic_input}' — result cached for future reuse.")

insights = st.session_state.get("competitor_insights")

if insights and not insights.get("error_notice"):
    st.markdown("---")
    
    c_head, c_time = st.columns([3, 1])
    with c_head:
        st.subheader(f"📊 Market Insights: '{insights.get('seed_topic')}'")
    with c_time:
        analyzed_time = insights.get('analyzed_at', '')[:19].replace('T', ' ')
        st.caption(f"⏱️ **Live Fetched At:** `{analyzed_time}`")

    top_videos = insights.get("top_videos", [])
    if top_videos:
        st.markdown("### ⚡ Top Velocity Competitor Videos (Past 30 Days)")
        
        table_rows = []
        for v in top_videos:
            v_id = v.get("video_id", "")
            v_url = v.get("video_url", f"https://www.youtube.com/watch?v={v_id}")
            table_rows.append({
                "Video Title": v.get("title", ""),
                "Channel Name": v.get("channel", ""),
                "Total Views": f"{v.get('views', 0):,}",
                "Hours Live": v.get("hours_published", 0),
                "Velocity (Views/Hr)": f"{v.get('view_velocity', 0):,}",
                "Published Date": str(v.get("published_at", ""))[:10],
                "Watch Link": v_url
            })
            
        df_display = pd.DataFrame(table_rows)
        st.dataframe(
            df_display,
            column_config={
                "Watch Link": st.column_config.LinkColumn(
                    "Watch Link",
                    help="Click to open video on YouTube",
                    validate="^https://",
                    display_text="▶ Watch Video"
                )
            },
            use_container_width=True
        )

        st.markdown("---")
        st.markdown("### 📜 Real Spoken Video Transcripts & Comments Extracted")
        t_col1, t_col2 = st.columns(2)
        
        with t_col1:
            st.markdown("#### 🗣️ Spoken Transcript Breakdown")
            for idx, v in enumerate(top_videos[:5], 1):
                v_id = v.get("video_id", "")
                v_url = v.get("video_url", f"https://www.youtube.com/watch?v={v_id}")
                t_snip = v.get("transcript_snippet", "").strip()
                t_source = v.get("transcript_source", "unknown")
                source_labels = {
                    "captions": "🟢 Real spoken captions",
                    "transcript_api": "🟢 Real spoken transcript",
                    "description": "🟡 Video description (no captions available)",
                    "gemini_search": "🟡 AI-found transcript summary",
                    "none": "🔴 Nothing available",
                    "unknown": "⚪ Source unknown (older research)"
                }

                with st.expander(f"Video {idx}: {v.get('title')[:45]}...", expanded=(idx==1)):
                    st.markdown(f"**Channel:** `{v.get('channel')}`")
                    st.markdown(f"🔗 **Direct YouTube Link:** [{v_url}]({v_url})")
                    st.caption(f"**Text source:** {source_labels.get(t_source, t_source)}")
                    st.write(t_snip)

        with t_col2:
            st.markdown("#### 💬 Audience Comments (Per Video)")
            has_per_video = any(v.get("comments") for v in top_videos[:5])
            if has_per_video:
                for idx, v in enumerate(top_videos[:5], 1):
                    v_comments = v.get("comments", [])
                    if not v_comments:
                        continue
                    with st.expander(f"Video {idx}: {v.get('title')[:40]}... ({len(v_comments)} comments)", expanded=(idx==1)):
                        for c_idx, comm in enumerate(v_comments[:10], 1):
                            st.write(f"**{c_idx}.** {comm}")
            else:
                comments = insights.get("top_comments_sample", [])
                if comments:
                    st.caption("⚠️ Older research data — comments were stored combined. Re-run analysis with 'Force fresh fetch' to get per-video comments.")
                    with st.expander(f"View {len(comments)} Combined Comments", expanded=True):
                        for c_idx, comm in enumerate(comments[:8], 1):
                            st.write(f"**{c_idx}.** {comm}")
                else:
                    st.info("No public comments retrieved for these videos.")

    st.markdown("---")
    st.markdown("### 🤖 Synthesized Analysis of Transcripts & Comments")

    col_gap, col_trigger, col_trope = st.columns(3)
    
    with col_gap:
        st.markdown("### 🎯 Content Gaps")
        st.caption("What transcripts failed to explain or answered poorly")
        for gap in insights.get("content_gaps", []):
            st.info(f"• {gap}")
            
    with col_trigger:
        st.markdown("### 🔥 Emotional Triggers")
        st.caption("Audience pain points from comment section")
        for trigger in insights.get("emotional_triggers", []):
            st.warning(f"• {trigger}")
            
    with col_trope:
        st.markdown("### 🎨 Title & Thumbnail Tropes")
        st.caption("Common patterns used by competitors")
        for trope in insights.get("common_tropes", []):
            st.success(f"• {trope}")

    # --- SCRIPT PROS & CONS (from transcript analysis, fed into script generation) ---
    script_pros = insights.get("script_pros", [])
    script_cons = insights.get("script_cons", [])
    if script_pros or script_cons:
        st.markdown("---")
        st.markdown("### ⚖️ Competitor Script Review: Pros & Cons")
        st.caption("Extracted from competitor transcripts + their audience reactions. These flow directly into the script generation prompt — pros are adopted, cons are avoided.")
        pc_col1, pc_col2 = st.columns(2)
        with pc_col1:
            st.markdown("#### ✅ Script Pros (techniques to adopt)")
            for p in script_pros:
                st.success(f"• {p}")
        with pc_col2:
            st.markdown("#### ❌ Script Cons (mistakes to avoid)")
            for c in script_cons:
                st.error(f"• {c}")

    st.markdown("---")
    st.markdown("### 💡 Recommended Positioning Angle")
    st.success(insights.get("recommended_angle", "Position video with scientific mechanism and immediate verbal reframe script."))

    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("➡️ Proceed to Script Pipeline"):
            st.switch_page("pages/4_Pipeline.py")
elif insights and insights.get("error_notice"):
    st.error(f"⚠️ {insights.get('error_notice')}")
