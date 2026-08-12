import os
import sys
import json
import time

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass


def _build_scene_framework(target_minutes):
    if target_minutes <= 5:
        return {
            "scene_count": "6 to 8",
            "words_per_scene": "120 to 150",
            "total_words": "approximately 900",
            "framework": """Follow this Retention Framework:
   - Scene 1: Pattern Interrupt Hook (0-15s) — shocking or counterintuitive opener
   - Scene 2: Anti-Hook Reveal (15-45s) — subvert expectations, tease the real insight
   - Scene 3-4: Scientific Mechanism / Deep Dive (45s-2min) — evidence, studies, mechanisms
   - Scene 5-6: Practical Application & Stakes (2-3.5min) — actionable steps, real consequences
   - Scene 7: Value Bomb & Insight (3.5-4.5min) — the "aha" moment
   - Scene 8: Soft CTA (4.5-5min) — subscribe, comment prompt"""
        }
    elif target_minutes <= 10:
        return {
            "scene_count": "10 to 14",
            "words_per_scene": "150 to 200",
            "total_words": "approximately 1800",
            "framework": """Follow this Extended Retention Framework:
   - Scene 1: Pattern Interrupt Hook (0-20s) — shocking statement, counterintuitive claim, or visceral scenario
   - Scene 2: Anti-Hook Reveal (20-50s) — subvert the hook, reveal the real question
   - Scene 3: Context & Setup (50s-1.5min) — why this matters NOW, who is affected
   - Scene 4-5: Scientific Mechanism Deep Dive (1.5-3min) — research, studies, neuroscience, expert citations
   - Scene 6-7: Case Study / Story (3-5min) — real example that illustrates the mechanism
   - Scene 8-9: Practical Application & Verbal Scripts (5-7min) — step-by-step how-to, exact phrases, frameworks
   - Scene 10-11: Stakes & Consequences (7-8.5min) — what happens if you ignore this, emotional weight
   - Scene 12: Counterintuitive Insight / Value Bomb (8.5-9.5min) — the "aha" moment most people miss
   - Scene 13: Actionable Takeaway Summary (9.5-10min) — 2-3 bullet recap
   - Scene 14: Soft CTA (last 15-20s) — subscribe, comment prompt, next video tease"""
        }
    elif target_minutes <= 15:
        return {
            "scene_count": "14 to 18",
            "words_per_scene": "150 to 200",
            "total_words": "approximately 2700",
            "framework": """Follow this Deep Retention Framework:
   - Scene 1: Pattern Interrupt Hook (0-20s) — shocking or counterintuitive opener
   - Scene 2: Anti-Hook Reveal (20-50s) — subvert expectations
   - Scene 3: Context & Background (50s-2min) — why this matters now
   - Scene 4-6: Scientific Mechanism Deep Dive (2-4.5min) — multiple studies, mechanisms, expert insights
   - Scene 7-9: Case Studies & Stories (4.5-7.5min) — 2-3 real examples illustrating the concepts
   - Scene 10-12: Practical Application Framework (7.5-10.5min) — detailed how-to with verbal scripts and techniques
   - Scene 13-14: Advanced Nuances & Edge Cases (10.5-12min) — what most people get wrong
   - Scene 15-16: Stakes, Consequences & Emotional Weight (12-13.5min) — real impact if ignored
   - Scene 17: Counterintuitive Value Bomb (13.5-14.5min) — the insight that changes everything
   - Scene 18: Soft CTA (14.5-15min) — subscribe, comment, next video tease"""
        }
    else:
        return {
            "scene_count": "18 to 22",
            "words_per_scene": "150 to 200",
            "total_words": "approximately 3600",
            "framework": """Follow this Comprehensive Retention Framework:
   - Scene 1: Pattern Interrupt Hook (0-20s) — shocking opener
   - Scene 2: Anti-Hook Reveal (20-50s) — subvert expectations
   - Scene 3-4: Context & Background (50s-2.5min) — why this matters, who is affected
   - Scene 5-8: Scientific Mechanism Deep Dive (2.5-7min) — multiple studies, neuroscience, expert citations
   - Scene 9-12: Case Studies & Stories (7-11min) — 3-4 real examples with narrative arcs
   - Scene 13-16: Practical Application Framework (11-15min) — step-by-step techniques, verbal scripts, scenarios
   - Scene 17-18: Advanced Nuances & Common Mistakes (15-17min) — what most people get wrong
   - Scene 19-20: Stakes, Consequences & Emotional Weight (17-18.5min) — real impact
   - Scene 21: Counterintuitive Value Bomb (18.5-19.5min) — paradigm-shifting insight
   - Scene 22: Soft CTA (19.5-20min) — subscribe, comment, next video tease"""
        }


def _build_competitor_context(competitor_insights):
    content_gaps = competitor_insights.get("content_gaps", ["Lacks practical breakdown"])
    emotional_triggers = competitor_insights.get("emotional_triggers", ["Fear of confrontation"])

    transcripts = []
    for v in competitor_insights.get("top_videos", [])[:3]:
        t = v.get("transcript_snippet", "").strip()
        if t and len(t) > 30:
            title = v.get("title", "Video")
            src = v.get("transcript_source", "")
            src_tag = f" (source: {src})" if src else ""
            transcripts.append(f"[{title}]{src_tag}: {t[:800]}")
    transcript_context = "\n".join(transcripts) if transcripts else "No competitor transcripts available."

    # PER-VIDEO comments (falls back to the combined sample for old research data)
    comment_blocks = []
    for v in competitor_insights.get("top_videos", [])[:5]:
        v_comments = v.get("comments", [])
        if v_comments:
            title = v.get("title", "Video")
            lines = "\n".join(f"  - {c[:200]}" for c in v_comments[:6])
            comment_blocks.append(f"[{title}]:\n{lines}")
    if comment_blocks:
        comment_context = "\n".join(comment_blocks)
    else:
        comments = competitor_insights.get("top_comments_sample", [])
        comment_context = "\n".join(f"- {c}" for c in comments[:10]) if comments else "No audience comments available."

    common_tropes = competitor_insights.get("common_tropes", [])
    tropes_text = ", ".join(common_tropes) if common_tropes else "None identified"

    recommended_angle = competitor_insights.get("recommended_angle", "")

    # Script pros/cons extracted from competitor transcript analysis
    pros = competitor_insights.get("script_pros", [])
    cons = competitor_insights.get("script_cons", [])
    pros_text = "\n".join(f"- {p}" for p in pros) if pros else "- No competitor script strengths identified (rely on the retention framework)."
    cons_text = "\n".join(f"- {c}" for c in cons) if cons else "- No competitor script weaknesses identified."

    return {
        "content_gaps": content_gaps,
        "emotional_triggers": emotional_triggers,
        "transcript_context": transcript_context,
        "comment_context": comment_context,
        "tropes_text": tropes_text,
        "recommended_angle": recommended_angle,
        "script_pros": pros_text,
        "script_cons": cons_text
    }


def _load_master_prompt_template():
    """Loads the fixed master prompt template from data/prompts/script_master_prompt.txt.
    Returns the template string, or None if the file is missing/unreadable."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_path = os.path.join(base_dir, "data", "prompts", "script_master_prompt.txt")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if len(content) > 100:
            return content
    except Exception:
        pass
    return None


def generate_script(topic, competitor_insights, channel_profile, gemini_api_key=None, output_dir=None, session_id=None, target_video_length_minutes=10):
    safe_topic = str(topic).encode('ascii', 'ignore').decode('ascii') if topic else "Behavioral Psychology"
    print(f"[+] Generating script for topic: '{safe_topic}' ({target_video_length_minutes} min target)...")

    if output_dir is None:
        if session_id:
            from backend.session_manager import SessionManager
            sm = SessionManager()
            output_dir = sm.get_session_dir(session_id)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(base_dir, "data")
    os.makedirs(output_dir, exist_ok=True)

    character_anchor = channel_profile.get("character_anchor", "").strip()
    art_style = channel_profile.get("visual_settings", {}).get("art_style_prompt", "clean lines, modern style")

    comp = _build_competitor_context(competitor_insights)
    fw = _build_scene_framework(target_video_length_minutes)

    # Fixed master prompt template (data/prompts/script_master_prompt.txt) with dynamic pros/cons.
    # Falls back to a built-in default if the template file is missing.
    from string import Template
    template_str = _load_master_prompt_template()
    if not template_str:
        template_str = """You are an elite YouTube Retention Strategist and Scriptwriter specializing in $niche.
Your mission is to write a high-retention video script addressing the topic: "$topic".
Target video length: $target_minutes minutes.

Key Requirements:
1. EXPLICITLY address the competitor content gaps: $content_gaps
2. TARGET the audience emotional triggers: $emotional_triggers
3. $framework
4. Write $scene_count scenes with $words_per_scene words of spoken text EACH.
   The TOTAL spoken text across all scenes must be $total_words words.
   This is critical — short scripts produce unusable videos. Each scene MUST have substantial spoken text.
5. ADOPT these proven scriptwriting strengths from competitor transcripts (PROS):
$script_pros
6. AVOID these scriptwriting weaknesses from competitor transcripts (CONS):
$script_cons
7. LEARN from but DO NOT copy these competitor transcript excerpts:
$transcript_context
8. Address these real audience pain points from comments:
$comment_context
9. Differentiate from these overused competitor tropes: $tropes_text
10. Use this strategic positioning angle: $recommended_angle
11. All visual scene descriptions should match this art style: $art_style
12. Return a JSON object with:
   - "title": Compelling YouTube Title
   - "hook_statement": High-converting thumbnail text overlay (2-5 words)
   - "scenes": Array of objects, each containing:
     - "scene_number": Integer
     - "retention_stage": String matching one of the framework parts above
     - "spoken_text": Natural, engaging spoken script ($words_per_scene words per scene — this is MANDATORY)
     - "ai_image_prompt": Visual scene description (DO NOT include character details, just the scene action/setting/environment)
     - "image_to_video_prompt": Camera movement description (e.g., "Slow push in on character, subtle eye movement")
     - "on_screen_text": 2-4 word punchy subtitle overlay for key moment
     - "target_duration_sec": Target duration in seconds (30-90 seconds per scene)
"""

    system_instruction = Template(template_str).safe_substitute(
        niche=channel_profile.get("niche", "Psychology"),
        topic=str(topic),
        target_minutes=str(target_video_length_minutes),
        content_gaps=str(comp["content_gaps"]),
        emotional_triggers=str(comp["emotional_triggers"]),
        framework=fw["framework"],
        scene_count=fw["scene_count"],
        words_per_scene=fw["words_per_scene"],
        total_words=fw["total_words"],
        script_pros=comp["script_pros"],
        script_cons=comp["script_cons"],
        transcript_context=comp["transcript_context"],
        comment_context=comp["comment_context"],
        tropes_text=comp["tropes_text"],
        recommended_angle=comp["recommended_angle"],
        art_style=art_style
    )

    script_data = None
    gen_start = time.time()

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

            user_prompt = f"""Generate the full retention script for '{topic}'.
Target: {target_video_length_minutes} minutes, {fw['scene_count']} scenes, {fw['total_words']} words total.
Primary gap to address: {comp['content_gaps'][0]}
Positioning angle: {comp['recommended_angle'] or comp['content_gaps'][0]}
IMPORTANT: Each scene MUST have {fw['words_per_scene']} words of spoken_text. Do NOT write short 30-word scenes."""

            for model_name in ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-2.0-flash-lite"]:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=user_prompt,
                        config=config
                    )
                    script_data = json.loads(response.text)
                    print(f"[+] Script generated via {model_name}")
                    break
                except Exception as e_m:
                    err_msg = str(e_m).encode('ascii', 'ignore').decode('ascii')
                    print(f"[-] Script model {model_name} notice: {err_msg}")
        except Exception as e:
            err_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            print(f"[-] Gemini script generation warning: {err_msg}")

    gen_duration = time.time() - gen_start

    if not script_data or "scenes" not in script_data:
        print("[!] Generating default structured script template.")
        script_data = _build_fallback_template(topic, target_video_length_minutes)

    for scene in script_data.get("scenes", []):
        base_prompt = scene.get("ai_image_prompt", "")
        if character_anchor and not base_prompt.startswith(character_anchor[:20]):
            scene["ai_image_prompt"] = f"{character_anchor}, {base_prompt}, style: {art_style}"
        elif art_style and art_style not in base_prompt:
            scene["ai_image_prompt"] = f"{base_prompt}, style: {art_style}"

    out_file = os.path.join(output_dir, "script_data.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=2)

    if session_id:
        try:
            from backend.session_manager import SessionManager
            sm = SessionManager()
            sm.save_checkpoint(session_id, "script_data", script_data)
            sm.update_status(session_id, "SCRIPT_GENERATED", current_step="ASSET_GENERATION")

            total_words = sum(len(s.get("spoken_text", "").split()) for s in script_data.get("scenes", []))
            sm.log_api_call(
                session_id=session_id,
                step="SCRIPT_GENERATION",
                service="Gemini SDK (google.genai)",
                request_data={
                    "topic": topic,
                    "target_minutes": target_video_length_minutes,
                    "niche": channel_profile.get("niche", "Psychology"),
                    "gaps_addressed": comp["content_gaps"][:3],
                    "triggers_targeted": comp["emotional_triggers"][:3],
                    "has_transcripts": comp["transcript_context"] != "No competitor transcripts available.",
                    "has_comments": comp["comment_context"] != "No audience comments available.",
                    "recommended_angle": comp["recommended_angle"][:100] if comp["recommended_angle"] else ""
                },
                response_data={
                    "status": "SUCCESS",
                    "title": script_data.get("title"),
                    "hook_statement": script_data.get("hook_statement"),
                    "scene_count": len(script_data.get("scenes", [])),
                    "total_words": total_words,
                    "estimated_duration_min": round(total_words / 150, 1)
                },
                status="SUCCESS",
                duration_sec=round(gen_duration, 2)
            )
        except Exception as e_sm:
            print(f"[-] Session logging warning for script: {e_sm}")

    scene_count = len(script_data.get("scenes", []))
    total_words = sum(len(s.get("spoken_text", "").split()) for s in script_data.get("scenes", []))
    print(f"[+] Script: {scene_count} scenes, {total_words} words (~{total_words/150:.1f} min). Saved to {out_file}")
    return script_data


def _build_fallback_template(topic, target_minutes):
    base_scenes = [
        {
            "scene_number": 1,
            "retention_stage": "Pattern Interrupt Hook",
            "spoken_text": f"Ever notice how most advice on {topic} completely falls apart the moment real pressure hits? Most people freeze, panic, and give away every ounce of leverage they had — not because they lack knowledge, but because they were never taught the invisible mechanics that drive human behavior in high-stakes moments. What you're about to learn isn't the recycled self-help fluff that dominates this space. This is the raw framework that separates people who get walked over from people who command respect without ever raising their voice. And the first principle is going to contradict everything you've been told.",
            "ai_image_prompt": "standing in a modern high-rise office at dusk, city lights in the background, holding a clipboard, looking directly at camera with calm intense gaze, dramatic side lighting",
            "image_to_video_prompt": "Slow push in on character face, dramatic lighting shift from shadow to light",
            "on_screen_text": "THE HIDDEN FRAMEWORK",
            "target_duration_sec": 45.0
        },
        {
            "scene_number": 2,
            "retention_stage": "Anti-Hook Reveal",
            "spoken_text": f"Here is the uncomfortable truth about {topic} that nobody in this space is willing to say out loud: the most powerful response to confrontation is not aggression. It's calculated stillness. When you master the art of the pause — that deliberate two-second beat where you hold eye contact and say nothing — the entire dynamic shifts. The other person's brain goes into overdrive trying to read you, and in that uncertainty, you gain the upper hand. This isn't theory. This is backed by decades of negotiation research from Harvard and MIT, and today I'm going to break down exactly how it works and give you the exact scripts to deploy it.",
            "ai_image_prompt": "sitting at a sleek glass desk in a minimalist psychology laboratory, gesturing calmly with one hand, holographic brain scan on monitor behind, soft blue ambient lighting",
            "image_to_video_prompt": "Pan left around desk, character maintains calm eye contact with camera",
            "on_screen_text": "SILENCE IS LEVERAGE",
            "target_duration_sec": 55.0
        },
        {
            "scene_number": 3,
            "retention_stage": "Context & Setup",
            "spoken_text": f"Before we dive into the mechanism, let me tell you why this matters RIGHT NOW. In the last five years, there's been an explosion of passive-aggressive communication in professional and personal settings. Social media has trained people to be indirect, to use sarcasm as a shield, and to avoid genuine confrontation. The result? A generation of people who feel constantly disrespected but have no idea how to address it effectively. If you've ever left a conversation feeling like you were manipulated but couldn't pinpoint how, or if you've ever wanted to speak up but the words just wouldn't come — this video is specifically for you. The framework I'm about to share has been used by crisis negotiators, hostage mediators, and executive coaches.",
            "ai_image_prompt": "standing before a digital screen showing social media comment threads and conflict infographics, pointing at key statistics, modern conference room setting",
            "image_to_video_prompt": "Slow zoom out revealing the full digital screen, then refocus on character",
            "on_screen_text": "WHY THIS MATTERS NOW",
            "target_duration_sec": 60.0
        },
        {
            "scene_number": 4,
            "retention_stage": "Scientific Mechanism Deep Dive",
            "spoken_text": "Neurologically, here's what happens when someone attempts a power play on you. Your amygdala — the brain's threat detection center — fires an adrenaline spike in under 200 milliseconds. That's before your conscious mind even registers what happened. Your heart rate jumps, your muscles tense, and your prefrontal cortex — the rational decision-making center — goes partially offline. This is the fight-or-flight hijack. Every impulsive response you've ever regretted came from this moment. But here's the breakthrough: research from the University of Wisconsin shows that a deliberate two-second breath delay is enough to re-engage the prefrontal cortex. Two seconds. That's all it takes to shift from reactive to strategic.",
            "ai_image_prompt": "pointing to a glowing holographic brain diagram displaying active neural pathways, amygdala highlighted in red and prefrontal cortex in blue, dark futuristic study room",
            "image_to_video_prompt": "Slow tilt up from glowing brain diagram to character's knowing smile",
            "on_screen_text": "THE 2-SECOND RESET",
            "target_duration_sec": 60.0
        },
        {
            "scene_number": 5,
            "retention_stage": "Scientific Mechanism - Evidence",
            "spoken_text": "Dr. Matthew Lieberman at UCLA published a landmark study showing that simply labeling an emotion — saying to yourself 'I notice I'm feeling defensive right now' — reduces amygdala activity by up to 50 percent. This technique, called affect labeling, is now standard training for FBI hostage negotiators. Think about that: the people who talk armed criminals into surrendering use the same basic technique I'm teaching you right now. The difference between someone who controls a room and someone who gets controlled comes down to a 2-second neurological gap. Master that gap, and you master human dynamics.",
            "ai_image_prompt": "walking through a modern university research library with brain scan images on display screens, books and academic papers visible, warm scholarly lighting",
            "image_to_video_prompt": "Tracking shot following character through library, camera slightly below eye level for authority",
            "on_screen_text": "THE LABELING TECHNIQUE",
            "target_duration_sec": 55.0
        },
        {
            "scene_number": 6,
            "retention_stage": "Case Study",
            "spoken_text": f"Let me give you a real example. Sarah, a senior marketing director, was being publicly undermined by a colleague during a quarterly review. The colleague interrupted her mid-presentation, questioned her data sources, and implied her team's numbers were inflated. The old Sarah would have gotten defensive, stumbled through a rebuttal, and spent the rest of the day replaying it. But Sarah had learned the framework. She paused for two full seconds, maintained eye contact, and said: 'That's an interesting perspective. Let's look at the raw data together after this meeting.' The room went silent. Her colleague had nowhere to go. By refusing to react emotionally and redirecting to objective evidence, Sarah demonstrated executive presence that got her promoted three months later.",
            "ai_image_prompt": "in a corporate boardroom setting, standing confidently at the head of a conference table with projector screen behind showing marketing charts, colleagues seated around the table",
            "image_to_video_prompt": "Slow dolly in toward character standing at head of table, other figures slightly blurred",
            "on_screen_text": "EXECUTIVE PRESENCE",
            "target_duration_sec": 65.0
        },
        {
            "scene_number": 7,
            "retention_stage": "Practical Application",
            "spoken_text": "Now let me give you the exact verbal scripts. Script number one is the Redirect. When someone challenges you aggressively, you say: 'I appreciate you raising that. Let me address it directly.' This validates the other person while maintaining your authority. Script number two is the Mirror. You repeat the last 3 words of what they said as a question. If they say 'Your approach is completely wrong,' you respond: 'Completely wrong?' This forces them to elaborate and often softens their position. Script number three is the Frame Reset. You say: 'What outcome are you hoping for in this conversation?' This shifts the dynamic from attack-defense to collaborative problem-solving.",
            "ai_image_prompt": "standing before a chalkboard with gold behavioral flowchart notes and three numbered scripts, making an empowering open-palm gesture, warm studio lighting",
            "image_to_video_prompt": "Smooth rack focus from flowchart notes to character's face, then back to notes",
            "on_screen_text": "3 VERBAL SCRIPTS",
            "target_duration_sec": 60.0
        },
        {
            "scene_number": 8,
            "retention_stage": "Practical Application - Advanced",
            "spoken_text": "Here's the advanced technique that separates good communicators from exceptional ones: strategic vulnerability. After you've established your frame with the scripts I just gave you, occasionally showing a calibrated moment of honesty — something like 'I'll be transparent, this is a topic I care deeply about' — actually increases your perceived authority. Stanford research on credibility shows that leaders who acknowledge uncertainty on small points are trusted more on large points. But the key word is 'calibrated.' You never show vulnerability on your core position, only on the delivery. This is the difference between authenticity and weakness.",
            "ai_image_prompt": "sitting in a comfortable leather chair in a warm psychology office, leaning forward with engaged body language, bookshelves with psychology textbooks behind, golden hour window light",
            "image_to_video_prompt": "Slow push in as character leans forward, creating intimacy and trust",
            "on_screen_text": "STRATEGIC VULNERABILITY",
            "target_duration_sec": 55.0
        },
        {
            "scene_number": 9,
            "retention_stage": "Stakes & Consequences",
            "spoken_text": "Now let me tell you what happens when people ignore these principles. I've seen executives lose promotions because they couldn't control a single emotional outburst. I've seen relationships deteriorate because one partner kept escalating instead of pausing. The cost of not mastering this framework isn't abstract — it shows up in your career trajectory, your relationships, and your self-respect. Every time you react instead of respond, you're handing your power to someone else. And in a world that's becoming increasingly confrontational, the ability to maintain composure under pressure isn't just a nice-to-have — it's a survival skill.",
            "ai_image_prompt": "standing at a crossroads in a dramatic urban setting at night, one path lit with warm golden light and one shrouded in shadow, city skyline behind",
            "image_to_video_prompt": "Dramatic dolly back revealing the crossroads, then slow pan up to character's determined expression",
            "on_screen_text": "THE REAL COST",
            "target_duration_sec": 55.0
        },
        {
            "scene_number": 10,
            "retention_stage": "Value Bomb & Insight",
            "spoken_text": f"Here's the insight that will change everything: the goal of mastering {topic} is NOT to win arguments. It's to make arguments unnecessary. When you consistently demonstrate that you can hold your frame, stay calm, and redirect conversations productively, people stop trying to push your buttons. You develop what psychologists call 'earned authority' — respect that comes from behavior, not title. The most powerful people in any room aren't the loudest. They're the ones who speak least but are listened to most. That's the paradox most people never understand: true power is quiet.",
            "ai_image_prompt": "in a zen garden with raked sand patterns and smooth stones, standing peacefully with hands clasped behind back, early morning mist, minimalist Japanese aesthetic",
            "image_to_video_prompt": "Slow aerial descent into the zen garden, settling on character's peaceful expression",
            "on_screen_text": "QUIET POWER",
            "target_duration_sec": 50.0
        },
        {
            "scene_number": 11,
            "retention_stage": "Actionable Summary",
            "spoken_text": "Let me recap the three things you need to start doing today. First: practice the two-second pause before every response in high-stakes conversations. Set a mental trigger. Second: use affect labeling — silently name your emotion before reacting. Third: pick ONE verbal script from today and use it in your next difficult conversation. Don't try to implement everything at once. Master one technique, then layer the next. Small consistent changes in how you communicate compound into a completely different experience of human interaction.",
            "ai_image_prompt": "standing in front of a large digital screen showing a summary checklist with three golden checkmarks, modern minimalist office, bright daylight",
            "image_to_video_prompt": "Smooth pan from checklist screen to character giving a confident nod",
            "on_screen_text": "3 STEPS TODAY",
            "target_duration_sec": 45.0
        },
        {
            "scene_number": 12,
            "retention_stage": "Soft CTA",
            "spoken_text": f"Mastering human dynamics is a daily practice, not a one-time insight. If this breakdown gave you a new perspective on {topic}, hit subscribe and turn on notifications — I release deep psychological frameworks like this every week. Drop a comment telling me your biggest takeaway, and I'll personally respond to the top ones. And if you want the advanced version of today's framework, watch the video appearing on screen right now.",
            "ai_image_prompt": "standing in warm studio lighting with subscribe button graphic floating beside, smiling warmly at camera, channel branding elements visible",
            "image_to_video_prompt": "Slow zoom out revealing channel subscribe badge and end screen elements",
            "on_screen_text": "SUBSCRIBE FOR MORE",
            "target_duration_sec": 35.0
        }
    ]

    if target_minutes <= 5:
        scenes = base_scenes[:3] + [base_scenes[6]] + [base_scenes[9]] + [base_scenes[11]]
        for i, s in enumerate(scenes, 1):
            s["scene_number"] = i
    elif target_minutes <= 10:
        scenes = base_scenes[:12]
    else:
        scenes = base_scenes[:]
        extra_count = max(0, int((target_minutes - 10) / 2.5))
        for i in range(extra_count):
            extra = {
                "scene_number": len(scenes) + 1,
                "retention_stage": "Extended Deep Dive",
                "spoken_text": f"Let's go deeper into another dimension of {topic} that most content creators completely overlook. This is where the real transformation happens, beyond the surface-level advice that floods the internet. The research on this specific aspect is fascinating and directly applicable to your daily interactions. When you understand this layer, everything else clicks into place and the techniques become second nature rather than forced scripts.",
                "ai_image_prompt": "in a modern research facility with holographic displays showing interconnected concept maps, dramatic overhead lighting",
                "image_to_video_prompt": "Slow orbit around holographic displays converging on character",
                "on_screen_text": "GOING DEEPER",
                "target_duration_sec": 55.0
            }
            scenes.insert(-2, extra)
        for i, s in enumerate(scenes, 1):
            s["scene_number"] = i

    return {
        "topic": topic,
        "title": f"The Dark Psychology of {topic}: How to Stay Unshakable",
        "hook_statement": "THE UNSPOKEN RULE",
        "scenes": scenes
    }
