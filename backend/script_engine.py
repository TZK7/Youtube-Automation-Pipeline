import os
import sys
import json

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

def generate_script(topic, competitor_insights, channel_profile, gemini_api_key=None, output_dir=None, session_id=None):
    """
    Generates a retention-focused YouTube script using Gemini 2.5 SDK.
    Prepends the channel profile's character_anchor to all ai_image_prompt fields.
    Logs audit trails and saves checkpoints if session_id is provided.
    """
    safe_topic = str(topic).encode('ascii', 'ignore').decode('ascii') if topic else "Behavioral Psychology"
    print(f"[+] Generating script for topic: '{safe_topic}' with retention framework...")
    
    if output_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "data")
    os.makedirs(output_dir, exist_ok=True)
    
    character_anchor = channel_profile.get("character_anchor", "").strip()
    art_style = channel_profile.get("visual_settings", {}).get("art_style_prompt", "clean lines, modern style")
    
    content_gaps = competitor_insights.get("content_gaps", ["Lacks practical breakdown"])
    emotional_triggers = competitor_insights.get("emotional_triggers", ["Fear of confrontation"])
    
    system_instruction = f"""
You are an elite YouTube Retention Strategist and Scriptwriter specializing in {channel_profile.get('niche', 'Psychology')}.
Your mission is to write a high-retention video script addressing the topic: "{topic}".

Key Requirements:
1. EXPLICITLY address the competitor content gaps: {content_gaps}
2. TARGET the audience emotional triggers: {emotional_triggers}
3. Follow the 6-Part Retention Framework across scene blocks:
   - Part 1: Pattern Interrupt Hook (0-15s)
   - Part 2: Anti-Hook Reveal (15-30s)
   - Part 3: Scientific Mechanism (30-60s)
   - Part 4: Value Bomb (60-70% mark)
   - Part 5: Application & Stakes
   - Part 6: Soft CTA
4. Return a JSON object with:
   - "title": Compelling YouTube Title
   - "hook_statement": High-converting thumbnail text overlay
   - "scenes": Array of objects, each containing:
     - "scene_number": Integer (1 to 6)
     - "retention_stage": String matching one of the 6 parts above
     - "spoken_text": Natural, engaging spoken script (30-60 words per scene)
     - "ai_image_prompt": Visual scene description (DO NOT include character details, just the scene action/setting)
     - "image_to_video_prompt": Camera movement (e.g., "Slow push in on character, subtle eye movement")
     - "on_screen_text": 2-4 word punchy subtitle overlay for key moment
     - "target_duration_sec": Target duration in seconds (float)
"""

    script_data = None

    if gemini_api_key and gemini_api_key.strip():
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=gemini_api_key.strip())
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.7
            )
            
            user_prompt = f"Generate the full 6-part retention script for '{topic}' targeting the gap: {content_gaps[0]}"
            for model_name in ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"]:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=user_prompt,
                        config=config
                    )
                    script_data = json.loads(response.text)
                    break
                except Exception as e_m:
                    err_msg = str(e_m).encode('ascii', 'ignore').decode('ascii')
                    print(f"[-] Script model {model_name} notice: {err_msg}")
        except Exception as e:
            err_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            print(f"[-] Gemini script generation warning: {err_msg}")

    # Fallback template if API not available or error occurs
    if not script_data or "scenes" not in script_data:
        print("[!] Generating default structured script template.")
        script_data = {
            "topic": topic,
            "title": f"The Dark Psychology of {topic}: How to Stay Unshakable",
            "hook_statement": "THE UNSPOKEN RULE",
            "scenes": [
                {
                    "scene_number": 1,
                    "retention_stage": "Pattern Interrupt Hook (0-15s)",
                    "spoken_text": f"Ever notice how most advice on {topic} completely fails when real tension hits? Most people panic and freeze, giving away their leverage instantly.",
                    "ai_image_prompt": "standing in a modern high-rise office holding a clipboard, looking directly at camera with calm intense gaze, dim dramatic lighting",
                    "image_to_video_prompt": "Slow push in on character face, dramatic lighting shift",
                    "on_screen_text": "DON'T FREEZE IN CONFLICT",
                    "target_duration_sec": 7.5
                },
                {
                    "scene_number": 2,
                    "retention_stage": "Anti-Hook Reveal (15-30s)",
                    "spoken_text": "Here is the uncomfortable truth: aggressive confrontation isn't power. Silence is. When you master calculated stillness, the room shifts toward you.",
                    "ai_image_prompt": "sitting at a sleek glass desk in a minimalist psychology laboratory, demonstrating a subtle hand gesture of calm authority",
                    "image_to_video_prompt": "Pan left around desk, character maintains calm eye contact",
                    "on_screen_text": "SILENCE IS POWER",
                    "target_duration_sec": 8.0
                },
                {
                    "scene_number": 3,
                    "retention_stage": "Scientific Mechanism (30-60s)",
                    "spoken_text": "Neurologically, when someone attempts a power play, your amygdala triggers an adrenaline spike. By taking a 2-second breath delay, you bypass emotional reaction and activate the prefrontal cortex.",
                    "ai_image_prompt": "pointing to a glowing holographic brain diagram displaying active neural pathways in a dark futuristic study",
                    "image_to_video_prompt": "Slow tilt up from glowing brain diagram to character smile",
                    "on_screen_text": "AMYGDALA VS PREFRONTAL",
                    "target_duration_sec": 10.0
                },
                {
                    "scene_number": 4,
                    "retention_stage": "Value Bomb (60-70% mark)",
                    "spoken_text": "The exact script to reset dominance: pause, hold eye contact without blinking, and ask calmly, 'What outcome are you aiming for right now?'",
                    "ai_image_prompt": "standing before a chalkboard with gold behavioral flowchart notes, making an empowering open-palm gesture",
                    "image_to_video_prompt": "Smooth rack focus from flowchart notes to character",
                    "on_screen_text": "THE REFRAME SCRIPT",
                    "target_duration_sec": 8.5
                },
                {
                    "scene_number": 5,
                    "retention_stage": "Application & Stakes",
                    "spoken_text": "When you apply this frame, you shift from defensive response to executive control. You preserve your energy while forcing the other party to reveal their intent.",
                    "ai_image_prompt": "walking confidently through a bright modern gallery corridor with soft ambient lighting",
                    "image_to_video_prompt": "Tracking shot following character walking toward camera",
                    "on_screen_text": "EXECUTIVE CONTROL",
                    "target_duration_sec": 7.5
                },
                {
                    "scene_number": 6,
                    "retention_stage": "Soft CTA",
                    "spoken_text": "Mastering human dynamics takes daily practice. Subscribe to Mindset Dynamics for deeper breakdowns on behavioral psychology every week.",
                    "ai_image_prompt": "standing in warm studio lighting next to a sleek subscribe graphic icon, smiling invitingly",
                    "image_to_video_prompt": "Slow zoom out revealing channel subscribe badge",
                    "on_screen_text": "SUBSCRIBE FOR PSYCHOLOGY",
                    "target_duration_sec": 6.5
                }
            ]
        }

    # CRITICAL BACKEND CONSTRAINT: Prepend character_anchor to every scene's ai_image_prompt
    for scene in script_data.get("scenes", []):
        base_prompt = scene.get("ai_image_prompt", "")
        if character_anchor and not base_prompt.startswith(character_anchor[:20]):
            scene["ai_image_prompt"] = f"{character_anchor}, {base_prompt}"
        else:
            scene["ai_image_prompt"] = base_prompt

    out_file = os.path.join(output_dir, "script_data.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=2)

    # Session Management & Audit Logging
    if session_id:
        try:
            from backend.session_manager import SessionManager
            sm = SessionManager()
            sm.save_checkpoint(session_id, "script_data", script_data)
            sm.update_status(session_id, "SCRIPT_GENERATED", current_step="ASSET_GENERATION")
            
            sm.log_api_call(
                session_id=session_id,
                step="SCRIPT_GENERATION",
                service="Gemini 2.5 SDK (google.genai)",
                request_data={
                    "topic": topic,
                    "niche": channel_profile.get("niche", "Psychology"),
                    "gaps_addressed": content_gaps[:2],
                    "triggers_targeted": emotional_triggers[:2]
                },
                response_data={
                    "status": "SUCCESS",
                    "title": script_data.get("title"),
                    "hook_statement": script_data.get("hook_statement"),
                    "scene_count": len(script_data.get("scenes", []))
                },
                status="SUCCESS",
                duration_sec=0.0
            )
        except Exception as e_sm:
            print(f"[-] Session logging warning for script: {e_sm}")

    print(f"[+] Successfully generated script with {len(script_data['scenes'])} scenes. Saved to {out_file}")
    return script_data
