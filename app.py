import os
import streamlit as st
from dotenv import load_dotenv
from backend.profile_manager import ProfileManager

# Load environment variables from .env file
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path, override=True)

# Streamlit Page Config
st.set_page_config(
    page_title="YouTube Automation Control Center",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    /* Dark glassmorphic modern design */
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        backdrop-filter: blur(10px);
        margin-bottom: 15px;
    }
    .status-badge {
        background: #1e293b;
        color: #38bdf8;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid #0284c7;
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
pm = ProfileManager()
profiles = pm.list_profiles()

if "active_profile_id" not in st.session_state:
    st.session_state["active_profile_id"] = profiles[0] if profiles else "default_psychology"

st.session_state["youtube_api_key"] = os.environ.get("YOUTUBE_API_KEY", "").strip()
st.session_state["gemini_api_key"] = os.environ.get("GEMINI_API_KEY", "").strip()
st.session_state["openrouter_api_key"] = os.environ.get("OPENROUTER_API_KEY", "").strip()

# Load Active Profile
active_profile = pm.get_profile(st.session_state["active_profile_id"])
st.session_state["active_profile"] = active_profile

# Sidebar Navigation & Active Channel Selector
with st.sidebar:
    st.image("https://img.icons8.com/isometric-folders/100/youtube-play.png", width=64)
    st.title("Control Center")
    st.caption("Autonomous Video Pipeline v2.5")
    st.markdown("---")
    
    st.subheader("📺 Active Channel")
    selected_p = st.selectbox(
        "Select Channel Profile",
        options=profiles,
        index=profiles.index(st.session_state["active_profile_id"]) if st.session_state["active_profile_id"] in profiles else 0,
        key="channel_selector"
    )
    if selected_p != st.session_state["active_profile_id"]:
        st.session_state["active_profile_id"] = selected_p
        st.session_state["active_profile"] = pm.get_profile(selected_p)
        st.rerun()

    st.info(f"**Niche:** {active_profile.get('niche', 'Psychology')}\n\n**Voice:** {active_profile.get('voice_settings', {}).get('voice_id', 'Default')}")

    st.markdown("---")
    st.subheader("🔒 Server Security (.env)")
    
    gem_key = st.session_state["gemini_api_key"]
    yt_key = st.session_state["youtube_api_key"]
    or_key = st.session_state["openrouter_api_key"]
    
    if gem_key:
        st.success(f"✅ Gemini API: Connected (`{gem_key[:4]}...{gem_key[-4:]}`)")
    else:
        st.warning("⚠️ Gemini API: Missing in `.env` (Fallback)")

    if yt_key:
        st.success(f"✅ YouTube API: Connected (`{yt_key[:4]}...{yt_key[-4:]}`)")
    else:
        st.info("ℹ️ YouTube API: Missing in `.env` (Benchmark)")

    if or_key:
        st.success(f"✅ OpenRouter API: Connected (`{or_key[:4]}...{or_key[-4:]}`)")
    else:
        st.warning("⚠️ OpenRouter API: Missing in `.env` (No AI voice/image/video)")
        
    st.caption("Keys are securely loaded from local `.env` file on server startup.")

# Main Header
st.title("🎬 Autonomous YouTube Video Production Hub")
st.markdown("Automated Market Intelligence ➔ AI Script Generation ➔ TTS Synthesis ➔ Video Assembly")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="metric-card">
        <h4>Active Channel</h4>
        <p style="font-size:1.4rem; font-weight:bold; color:#38bdf8;">{}</p>
    </div>
    """.format(active_profile.get("channel_name", "Default")), unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-card">
        <h4>Retention Model</h4>
        <p style="font-size:1.4rem; font-weight:bold; color:#a855f7;">6-Part Framework</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card">
        <h4>TTS Engine</h4>
        <p style="font-size:1.4rem; font-weight:bold; color:#34d399;">{}</p>
    </div>
    """.format("Fish Audio (OpenRouter)" if st.session_state.get("openrouter_api_key") else active_profile.get("voice_settings", {}).get("tts_model", "edge-tts")), unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="metric-card">
        <h4>Video Assembly</h4>
        <p style="font-size:1.4rem; font-weight:bold; color:#f43f5e;">MoviePy 1080p</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.subheader("⚡ Quick Navigation")
st.write("Use the sidebar pages to navigate through the production modules:")
c1, c2, c3 = st.columns(3)
with c1:
    st.page_link("pages/2_Channel_Studio.py", label="Channel Studio", icon="⚙️")
with c2:
    st.page_link("pages/3_Research.py", label="Market Intelligence", icon="🔍")
with c3:
    st.page_link("pages/4_Pipeline.py", label="Script & Video Pipeline", icon="🚀")
