import os
import re
import datetime
import importlib
import streamlit as st
import pandas as pd
import backend.competitor_engine as competitor_engine_module
importlib.reload(competitor_engine_module)
from backend.competitor_engine import analyze_competitors


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
                gemini_api_key=gem_key
            )
            st.session_state["competitor_insights"] = insights
            if insights.get("error_notice"):
                st.error(f"⚠️ {insights.get('error_notice')}")
            else:
                st.success(f"✅ Live Competitor Analysis Complete for '{topic_input}'!")

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
                
                with st.expander(f"Video {idx}: {v.get('title')[:45]}...", expanded=(idx==1)):
                    st.markdown(f"**Channel:** `{v.get('channel')}`")
                    st.markdown(f"🔗 **Direct YouTube Link:** [{v_url}]({v_url})")
                    st.write(t_snip)

        with t_col2:
            st.markdown("#### 💬 Top Audience Comments Analyzed")
            comments = insights.get("top_comments_sample", [])
            if comments:
                with st.expander(f"View {len(comments)} Audience Comments Extracted", expanded=True):
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

    st.markdown("---")
    st.markdown("### 💡 Recommended Positioning Angle")
    st.success(insights.get("recommended_angle", "Position video with scientific mechanism and immediate verbal reframe script."))

    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("➡️ Proceed to Script Pipeline"):
            st.switch_page("pages/4_Pipeline.py")
elif insights and insights.get("error_notice"):
    st.error(f"⚠️ {insights.get('error_notice')}")
