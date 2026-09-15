import asyncio
import json
import re
import urllib.parse
import edge_tts
import requests
import streamlit as st
from google import genai
from groq import Groq

# -------------------------------------------------------------------
# 1. Streamlit Setup & Client Initialization
# -------------------------------------------------------------------
st.set_page_config(page_title="AI Multi-Scene & Voice Studio", page_icon="🎬", layout="wide")

client = None
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    key = str(st.secrets["GEMINI_API_KEY"]).strip()
    if key and not key.startswith("your_"):
        client = genai.Client(api_key=key)

groq_client = None
if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
    key = str(st.secrets["GROQ_API_KEY"]).strip()
    if key and not key.startswith("your_"):
        groq_client = Groq(api_key=key)

# -------------------------------------------------------------------
# 2. Async TTS Voice Engine
# -------------------------------------------------------------------
async def generate_speech(text: str, voice: str, output_file: str):
    """Generates a neural voice MP3 file using Microsoft Edge TTS."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def synthesize_audio(text: str, character_gender: str, filename: str) -> str:
    # Select default neural voices based on gender
    voice = "en-US-GuyNeural" if character_gender.lower() == "male" else "en-US-AriaNeural"
    try:
        asyncio.run(generate_speech(text, voice, filename))
        return filename
    except Exception as e:
        st.error(f"Error generating voice: {e}")
        return None

# -------------------------------------------------------------------
# 3. Media Search Engine
# -------------------------------------------------------------------
def get_pixabay_video(search_keywords: str) -> str:
    """Searches Pixabay for a background scene video clip matching visual keywords."""
    if "PIXABAY_API_KEY" in st.secrets and st.secrets["PIXABAY_API_KEY"]:
        api_key = str(st.secrets["PIXABAY_API_KEY"]).strip()
        url = f"https://pixabay.com/api/videos/?key={api_key}&q={urllib.parse.quote(search_keywords)}&per_page=3"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                hits = res.json().get("hits", [])
                if hits:
                    videos = hits[0].get("videos", {})
                    v_obj = videos.get("large") or videos.get("medium") or videos.get("small")
                    if v_obj and "url" in v_obj:
                        return v_obj["url"]
        except Exception:
            pass
    return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"

# -------------------------------------------------------------------
# 4. JSON Scene Storyboard Generator
# -------------------------------------------------------------------
def generate_storyboard(title: str):
    """Generates a structured JSON containing multiple scenes, characters, dialogs, and video search prompts."""
    prompt = f"""
    Create a 3-scene story script based on title: '{title}'.
    Return STRICT VALID JSON only. No markdown fences.
    JSON schema:
    {{
        "story_title": "{title}",
        "scenes": [
            {{
                "scene_number": 1,
                "visual_search_keywords": "visual keywords for background video",
                "narrative": "Scene narrative description.",
                "character_name": "Character Name",
                "character_gender": "male or female",
                "dialogue": "Character spoken line here."
            }}
        ]
    }}
    """
    
    response_text = ""
    if groq_client:
        try:
            res = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4
            )
            response_text = res.choices[0].message.content
        except Exception:
            pass
            
    if not response_text and client:
        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            response_text = res.text
        except Exception as e:
            st.error(f"LLM API Error: {e}")
            return None

    # Parse JSON clean
    try:
        clean_json = re.sub(r'```json\s*|\s*```', '', response_text).strip()
        return json.loads(clean_json)
    except Exception:
        st.error("Failed to parse storyboard JSON. Retrying...")
        return None

# -------------------------------------------------------------------
# 5. UI Layout & Execution Flow
# -------------------------------------------------------------------
st.title("🎬 Multi-Scene AI Video & Voice Studio")

title_input = st.text_input("Enter Story Topic/Title:", placeholder="e.g. Cyberpunk Detective")

if st.button("🚀 Generate Multi-Scene Storyboard"):
    if not title_input:
        st.warning("Please enter a title first!")
    else:
        with st.spinner("Writing multi-scene script and character dialogues..."):
            storyboard = generate_storyboard(title_input)
            
        if storyboard:
            st.session_state["storyboard"] = storyboard

if "storyboard" in st.session_state:
    board = st.session_state["storyboard"]
    st.subheader(f"📖 {board.get('story_title', 'Generated Story')}")
    st.divider()

    for idx, scene in enumerate(board.get("scenes", [])):
        st.markdown(f"### 🎬 Scene {scene['scene_number']}")
        
        col_video, col_details = st.columns([1, 1])
        
        with col_video:
            with st.spinner(f"Loading scene {scene['scene_number']} video..."):
                v_url = get_pixabay_video(scene["visual_search_keywords"])
                st.video(v_url)
                st.caption(f"🔍 Video Search Keywords: `{scene['visual_search_keywords']}`")
                
        with col_details:
            st.markdown(f"**Narrative:** {scene['narrative']}")
            st.markdown(f"**Character:** 👤 `{scene['character_name']}` ({scene['character_gender'].capitalize()})")
            st.info(f"💬 \"{scene['dialogue']}\"")
            
            # Generate Audio File for character dialogue
            audio_file = f"scene_{idx+1}_voice.mp3"
            with st.spinner("Synthesizing character voice..."):
                audio_path = synthesize_audio(scene['dialogue'], scene['character_gender'], audio_file)
                if audio_path:
                    st.audio(audio_path, format="audio/mp3")

        st.divider()
