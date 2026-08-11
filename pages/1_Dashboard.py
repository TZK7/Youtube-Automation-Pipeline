import os
import streamlit as st
from backend.profile_manager import ProfileManager

st.set_page_config(page_title="Dashboard | YouTube Control Center", page_icon="📊", layout="wide")

st.title("📊 Production Dashboard")
st.caption("Review channel performance, recent uploads, and generated video packages.")

pm = ProfileManager()
profiles = pm.list_profiles()
active_profile = st.session_state.get("active_profile", pm.get_profile(profiles[0]))

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📺 Selected Profile")
    st.markdown(f"**Channel Name:** {active_profile.get('channel_name')}")
    st.markdown(f"**Niche:** {active_profile.get('niche')}")
    st.markdown(f"**Aspect Ratio:** {active_profile.get('visual_settings', {}).get('aspect_ratio')}")
    
    st.markdown("---")
    st.markdown("### 🎨 Character Anchor String")
    st.code(active_profile.get("character_anchor", "N/A"), language="text")

with col2:
    st.subheader("🎥 Generated Videos & Output Bundles")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ready_dir = os.path.join(base_dir, "ready_to_upload")
    
    if os.path.exists(ready_dir) and os.listdir(ready_dir):
        bundles = sorted(os.listdir(ready_dir), reverse=True)
        st.success(f"Found {len(bundles)} rendered video bundle(s).")
        
        for bundle in bundles:
            b_path = os.path.join(ready_dir, bundle)
            if os.path.isdir(b_path):
                with st.expander(f"📦 {bundle}", expanded=True):
                    b_col1, b_col2 = st.columns([1, 2])
                    
                    v_file = os.path.join(b_path, "final_video.mp4")
                    t_file = os.path.join(b_path, "thumbnail.jpg")
                    m_file = os.path.join(b_path, "metadata.txt")
                    
                    with b_col1:
                        if os.path.exists(t_file):
                            st.image(t_file, caption="Thumbnail (JPEG)", use_column_width=True)
                        else:
                            st.info("No thumbnail file found.")
                            
                    with b_col2:
                        if os.path.exists(v_file) and os.path.getsize(v_file) > 0:
                            st.video(v_file)
                            with open(v_file, "rb") as f_v:
                                st.download_button(
                                    label="📥 Download Video (.mp4)",
                                    data=f_v,
                                    file_name=f"{bundle}.mp4",
                                    mime="video/mp4"
                                )
                        else:
                            st.warning("Video file rendering in progress or missing.")
                            
                    if os.path.exists(m_file):
                        with open(m_file, "r", encoding="utf-8") as f_m:
                            st.text_area("SEO Metadata", f_m.read(), height=150)
    else:
        st.info("No rendered video packages found yet. Go to **Research** or **Pipeline** to generate your first video!")
