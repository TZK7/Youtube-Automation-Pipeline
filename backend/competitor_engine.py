import os
import re
import json
import datetime
import sys
import requests

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

def fetch_curlcffi_transcript(video_id):
    """
    Attempts to fetch closed captions via Chrome TLS impersonation (curl_cffi).
    Returns pure raw transcript text or empty string.
    """
    try:
        from curl_cffi import requests
        url = f"https://www.youtube.com/watch?v={video_id}"
        r = requests.get(url, impersonate="chrome120", timeout=12)
        m_captions = re.search(r'"captionTracks":\s*(\[.*?\])', r.text)
        if m_captions:
            tracks = json.loads(m_captions.group(1))
            for t in tracks:
                b_url = t.get("baseUrl")
                if b_url:
                    json3_url = b_url + "&fmt=json3" if "fmt=" not in b_url else re.sub(r'fmt=[^&]+', 'fmt=json3', b_url)
                    r_sub = requests.get(json3_url, impersonate="chrome120", timeout=12)
                    if r_sub.status_code == 200:
                        c_json = r_sub.json()
                        text_parts = [seg["utf8"] for ev in c_json.get("events", []) for seg in ev.get("segs", []) if "utf8" in seg]
                        full_txt = re.sub(r'\s+', ' ', " ".join(text_parts)).strip()
                        if len(full_txt) > 20:
                            return full_txt[:3000]
    except Exception:
        pass
    return ""

def fetch_video_transcript(video_id, video_title="", video_desc="", gemini_api_key=None, return_source=False):
    """
    Fetches raw transcript or raw description text.
    PURE RAW TEXT ONLY - NO PREFIXES OR GENERATED SUMMARY STRINGS.
    If return_source=True, returns (text, source) where source is one of:
    'captions', 'transcript_api', 'description', 'gemini_search', 'none'.
    """
    def _ret(text, source):
        return (text, source) if return_source else text

    # 1. Try curl_cffi Chrome TLS impersonation
    curled = fetch_curlcffi_transcript(video_id)
    if len(curled) > 20:
        return _ret(curled, "captions")

    # 2. Try youtube_transcript_api library
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        tx_list = api.list(video_id)
        for t in tx_list:
            try:
                if getattr(t, 'is_translatable', False) and getattr(t, 'language_code', '') != 'en':
                    data = t.translate('en').fetch()
                else:
                    data = t.fetch()
                raw_text = " ".join([getattr(s, 'text', str(s)) for s in data])
                clean = re.sub(r'\s+', ' ', raw_text).strip()
                if len(clean) > 20:
                    return _ret(clean[:3000], "transcript_api")
            except Exception:
                continue
    except Exception:
        pass

    # 3. Use raw video description if available (no prefixes)
    clean_desc = re.sub(r'https?://\S+', '', video_desc).strip()
    clean_desc = re.sub(r'\s+', ' ', clean_desc)
    if len(clean_desc) > 30:
        return _ret(clean_desc[:2000], "description")

    # 4. Fallback: Use Gemini Pro with Google Search Grounding to find the transcript online
    if gemini_api_key:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=gemini_api_key)
            prompt = f"Provide a pure text summary of the spoken words in this video: https://www.youtube.com/watch?v={video_id}. Do NOT include any prefixes like 'The video talks about'. Return just raw transcript text."
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
            for m_name in ["gemini-3.5-flash", "gemini-3.1-flash-lite"]:
                try:
                    resp = client.models.generate_content(model=m_name, contents=prompt, config=config)
                    if resp and resp.text:
                        clean_ai = re.sub(r'\s+', ' ', resp.text).strip()
                        if len(clean_ai) > 20:
                            return _ret(clean_ai[:3000], "gemini_search")
                except Exception:
                    continue
        except Exception:
            pass

    return _ret("Closed captions not available for this video.", "none")

def clean_html(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&#39;', "'", text)
    return re.sub(r'\s+', ' ', text).strip()

def analyze_competitors(seed_topic, youtube_api_key=None, gemini_api_key=None, output_dir=None,
                        use_cache=True, cache_max_age_hours=72):
    """
    Retrieves ONLY real high-velocity videos matching seed_topic from YouTube Data API v3 or Gemini Search Grounding.
    Fetches actual spoken transcripts and real user comments (per video).
    Results are cached in the database by topic — repeated calls within cache_max_age_hours
    return the stored result WITHOUT re-spending API calls. Pass use_cache=False to force a fresh fetch.
    """
    # --- RESEARCH CACHE CHECK (avoids re-spending API quota on the same topic) ---
    if use_cache:
        try:
            from backend.database import PipelineDB
            db = PipelineDB()
            cached = db.get_research_cache(seed_topic, max_age_hours=cache_max_age_hours)
            if cached and cached.get("top_videos") and not cached.get("error_notice"):
                print(f"[+] Research cache HIT for '{seed_topic}' (cached at {cached.get('_cached_at', '?')[:19]}) — no API calls spent.")
                cached["from_cache"] = True
                return cached
        except Exception as e_cache:
            print(f"[-] Research cache check warning: {e_cache}")

    print(f"[+] Fetching real competitor videos & transcripts for topic: '{seed_topic}'...")
    
    if output_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "data")
    os.makedirs(output_dir, exist_ok=True)
    
    videos = []
    all_comments = []
    video_transcripts_map = {}
    
    # 1. Real YouTube Data API v3 Fetch
    if youtube_api_key and youtube_api_key.strip():
        try:
            from googleapiclient.discovery import build
            youtube = build('youtube', 'v3', developerKey=youtube_api_key.strip())
            
            thirty_days_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat() + "Z"
            
            search_response = youtube.search().list(
                q=seed_topic,
                type='video',
                part='id,snippet',
                maxResults=10,
                order='viewCount',
                publishedAfter=thirty_days_ago
            ).execute()
            
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            
            if video_ids:
                stats_response = youtube.videos().list(
                    id=','.join(video_ids),
                    part='snippet,statistics'
                ).execute()
                
                now = datetime.datetime.utcnow()
                for item in stats_response.get('items', []):
                    vid_id = item['id']
                    v_title = item['snippet']['title']
                    v_desc = item['snippet'].get('description', '')
                    pub_str = item['snippet']['publishedAt'].replace('Z', '+00:00')
                    try:
                        pub_dt = datetime.datetime.fromisoformat(pub_str).replace(tzinfo=None)
                    except Exception:
                        pub_dt = now - datetime.timedelta(days=7)
                    
                    hours_published = max(1.0, (now - pub_dt).total_seconds() / 3600.0)
                    view_count = int(item['statistics'].get('viewCount', 0))
                    velocity = round(view_count / hours_published, 2)
                    
                    t_snippet, t_source = fetch_video_transcript(vid_id, video_title=v_title, video_desc=v_desc, gemini_api_key=gemini_api_key, return_source=True)
                    if t_snippet:
                        video_transcripts_map[vid_id] = t_snippet

                    videos.append({
                        "video_id": vid_id,
                        "video_url": f"https://www.youtube.com/watch?v={vid_id}",
                        "title": v_title,
                        "channel": item['snippet']['channelTitle'],
                        "views": view_count,
                        "hours_published": round(hours_published, 1),
                        "view_velocity": velocity,
                        "published_at": item['snippet']['publishedAt'],
                        "transcript_snippet": t_snippet,
                        "transcript_source": t_source,
                        "comments": []
                    })

                videos.sort(key=lambda x: x['view_velocity'], reverse=True)

                # PER-VIDEO comments (top 5 videos) so relevance is preserved
                videos_by_id = {v["video_id"]: v for v in videos}
                for vid_id in [v['video_id'] for v in videos[:5]]:
                    try:
                        comment_response = youtube.commentThreads().list(
                            videoId=vid_id,
                            part='snippet',
                            maxResults=20,
                            order='relevance'
                        ).execute()
                        for c_item in comment_response.get('items', []):
                            raw_text = c_item['snippet']['topLevelComment']['snippet']['textDisplay']
                            cleaned = clean_html(raw_text)
                            if len(cleaned) > 5:
                                videos_by_id[vid_id]["comments"].append(cleaned)
                                all_comments.append(cleaned)
                    except Exception as e_c:
                        print(f"[-] Could not fetch comments for video {vid_id}: {e_c}")
        except Exception as e:
            print(f"[-] YouTube Data API fetch error: {e}")

    # 2. Fallback: yt-dlp Search (if YouTube API returned no videos or is unauthenticated)
    if not videos:
        print(f"[+] Using yt-dlp to search for real YouTube videos for topic: '{seed_topic}'...")
        try:
            import subprocess
            cmd = ["python", "-m", "yt_dlp", f"ytsearch5:{seed_topic}", "--dump-json", "--no-warnings"]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.stdout:
                for line in proc.stdout.splitlines():
                    try:
                        v_data = json.loads(line.strip())
                        vid_id = v_data.get("id")
                        v_title = v_data.get("title")
                        
                        # Avoid duplicates
                        if any(v["video_id"] == vid_id for v in videos):
                            continue
                            
                        # Calculate velocity based on upload date if available
                        pub_str = v_data.get("upload_date", "")
                        hours_published = 24.0
                        if pub_str and len(pub_str) == 8:
                            try:
                                pub_dt = datetime.datetime.strptime(pub_str, "%Y%m%d")
                                hours_published = max(1.0, (datetime.datetime.now() - pub_dt).total_seconds() / 3600.0)
                            except Exception:
                                pass
                                
                        view_count = int(v_data.get("view_count", 0))
                        velocity = round(view_count / hours_published, 2)
                        
                        # Extract transcript
                        v_desc = v_data.get("description", "")
                        t_snippet, t_source = fetch_video_transcript(vid_id, video_title=v_title, video_desc=v_desc, gemini_api_key=gemini_api_key, return_source=True)
                        if t_snippet:
                            video_transcripts_map[vid_id] = t_snippet

                        videos.append({
                            "video_id": vid_id,
                            "video_url": f"https://www.youtube.com/watch?v={vid_id}",
                            "title": v_title,
                            "channel": v_data.get("uploader", ""),
                            "views": view_count,
                            "hours_published": round(hours_published, 1),
                            "view_velocity": velocity,
                            "published_at": pub_str,
                            "transcript_snippet": t_snippet,
                            "transcript_source": t_source,
                            "comments": []
                        })
                    except Exception as e_parse:
                        continue
                videos.sort(key=lambda x: x['view_velocity'], reverse=True)
        except Exception as e_dlp:
            print(f"[-] yt-dlp search fallback failed: {e_dlp}")

    if not videos:
        print(f"[!] No real YouTube videos found for topic '{seed_topic}'.")
        insights = {
            "seed_topic": seed_topic,
            "analyzed_at": datetime.datetime.now().isoformat(),
            "top_videos": [],
            "top_comments_sample": [],
            "common_tropes": [],
            "content_gaps": [],
            "emotional_triggers": [],
            "recommended_angle": "",
            "error_notice": f"No live YouTube videos found for topic '{seed_topic}'. Please check your search topic or YouTube API key."
        }
        out_file = os.path.join(output_dir, "competitor_insights.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(insights, f, indent=2)
        return insights

    # Prepare real payload for Gemini analysis (per-video transcripts AND per-video comments)
    payload_videos = []
    for v in videos[:5]:
        payload_videos.append({
            "title": v.get("title"),
            "channel": v.get("channel"),
            "views": v.get("views"),
            "video_url": v.get("video_url", f"https://www.youtube.com/watch?v={v.get('video_id', '')}"),
            "transcript_snippet": video_transcripts_map.get(v.get("video_id"), v.get("transcript_snippet", "")),
            "transcript_source": v.get("transcript_source", "unknown"),
            "audience_comments": v.get("comments", [])[:10]
        })

    # Gemini Real Analysis
    tropes = []
    content_gaps = []
    emotional_triggers = []
    script_pros = []
    script_cons = []
    analysis_text = ""

    if gemini_api_key and gemini_api_key.strip():
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=gemini_api_key.strip())
            prompt = f"""
You are an expert YouTube Market Intelligence Analyst and Script Doctor.
Perform a deep, highly specific analysis tailored EXCLUSIVELY to topic "{seed_topic}".
Analyze these ACTUAL competitor videos. Each video object includes its title, spoken transcript
(field "transcript_snippet", source noted in "transcript_source"), and its OWN audience comments
(field "audience_comments") so you can judge each video's script against its own audience reaction:

{json.dumps(payload_videos, indent=2)}

Synthesize an exact, data-backed analysis for topic "{seed_topic}". Return a JSON object with:
1. "common_tropes": array of 3-4 specific title & thumbnail tropes observed in these actual videos for "{seed_topic}".
2. "content_gaps": array of 3-4 specific topics, questions, or scientific mechanisms that were MISSING or EXPLAINED POORLY in these actual spoken transcripts.
3. "emotional_triggers": array of 3-4 specific pain points, anxieties, or desires expressed in these actual user comments.
4. "script_pros": array of 4-6 SPECIFIC scriptwriting strengths observed in these transcripts that clearly worked (hooks that landed, explanation structures, pacing devices, phrases the audience praised in comments). Each entry must reference what technique it is and why it worked.
5. "script_cons": array of 4-6 SPECIFIC scriptwriting weaknesses in these transcripts (boring sections, confusing explanations, missing payoffs, things the audience complained about in comments). Each entry must state the flaw and its consequence.
6. "recommended_angle": 1-2 sentence positioning recommendation directly addressing these transcript gaps and comment pain points.
DO NOT use generic or repeated phrases across topics. Make every point unique to "{seed_topic}" and grounded in the actual transcripts and comments provided.
"""
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3
            )

            for model_name in ["gemini-3.5-flash", "gemini-3.1-flash-lite"]:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config
                    )
                    parsed = json.loads(response.text)
                    tropes = parsed.get("common_tropes", [])
                    content_gaps = parsed.get("content_gaps", [])
                    emotional_triggers = parsed.get("emotional_triggers", [])
                    script_pros = parsed.get("script_pros", [])
                    script_cons = parsed.get("script_cons", [])
                    analysis_text = parsed.get("recommended_angle", "")
                    if content_gaps and emotional_triggers:
                        break
                except Exception as e_m:
                    err_msg = str(e_m).encode('ascii', 'ignore').decode('ascii')
                    print(f"[-] Gemini analysis model {model_name} notice: {err_msg}")
        except Exception as e_g:
            err_msg = str(e_g).encode('ascii', 'ignore').decode('ascii')
            print(f"[-] Gemini gap analysis warning: {err_msg}")

    # 100% REAL DATA EXTRACTORS (NO SYNTHETIC OR TEMPLATE STRINGS)
    if not tropes:
        tropes = ["⚠️ AI Analysis Unavailable (Gemini Quota Exceeded or API Error)."]
    if not content_gaps:
        content_gaps = ["⚠️ AI Analysis Unavailable (Gemini Quota Exceeded or API Error)."]
    if not emotional_triggers:
        emotional_triggers = ["⚠️ AI Analysis Unavailable (Gemini Quota Exceeded or API Error)."]
    if not analysis_text:
        analysis_text = "⚠️ AI Analysis Unavailable (Gemini Quota Exceeded or API Error). Please upgrade your Gemini API plan or try again later."

    insights = {
        "seed_topic": seed_topic,
        "analyzed_at": datetime.datetime.now().isoformat(),
        "top_videos": videos,
        "top_comments_sample": all_comments[:15],
        "common_tropes": tropes,
        "content_gaps": content_gaps,
        "emotional_triggers": emotional_triggers,
        "script_pros": script_pros,
        "script_cons": script_cons,
        "recommended_angle": analysis_text,
        "from_cache": False
    }

    out_file = os.path.join(output_dir, "competitor_insights.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(insights, f, indent=2)

    # --- SAVE TO RESEARCH CACHE (so the same topic never re-spends API calls) ---
    try:
        from backend.database import PipelineDB
        db = PipelineDB()
        db.save_research_cache(seed_topic, insights)
        print(f"[+] Research result cached in database for topic '{seed_topic}'")
    except Exception as e_cache:
        print(f"[-] Research cache save warning: {e_cache}")

    print(f"[+] Saved real transcript & comment insights to {out_file}")
    return insights
