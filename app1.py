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
# 1. Page & Sidebar Configuration
# -------------------------------------------------------------------
st.set_page_config(
    page_title="AI Multi-Scene & Voice Studio", page_icon="🎨", layout="wide"
)

st.sidebar.title("⚙️ Custom Styling & Voices")
bg_color = st.sidebar.color_picker("App Background Color", "#F0F2F6")
text_color = st.sidebar.color_picker("Text Color", "#1F1F1F")
card_color = st.sidebar.color_picker("Card Background Color", "#FFFFFF")

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    .story-card {{
        background-color: {card_color};
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        color: {text_color};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# 2. Client Initialization
# -------------------------------------------------------------------
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
# 3. Safe Edge-TTS Voice Generation Engine
# -------------------------------------------------------------------
async def _generate_speech_async(text: str, voice: str, output_file: str):
    """Generates audio file asynchronously using edge-tts."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)


def synthesize_audio(
    text: str, character_gender: str, filename: str
) -> str:
    """Safe wrapper to handle asyncio event loops inside Streamlit threads."""
    voice = (
        "en-US-GuyNeural"
        if character_gender.lower() == "male"
        else "en-US-AriaNeural"
    )
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If Streamlit already has a running event loop in this thread
            import nest_asyncio

            nest_asyncio.apply()
            loop.run_until_complete(
                _generate_speech_async(text, voice, filename)
            )
        else:
            loop.run_until_complete(
                _generate_speech_async(text, voice, filename)
            )
        return filename
    except Exception:
        try:
            asyncio.run(_generate_speech_async(text, voice, filename))
            return filename
        except Exception as e:
            st.error(f"Voice generation error: {e}")
            return None


# -------------------------------------------------------------------
# 4. Media Search Engine
# -------------------------------------------------------------------
def get_pixabay_video(search_keywords: str) -> str:
    """Queries Pixabay Video API using targeted search keywords."""
    if "PIXABAY_API_KEY" in st.secrets and st.secrets["PIXABAY_API_KEY"]:
        api_key = str(st.secrets["PIXABAY_API_KEY"]).strip()
        url = f"https://pixabay.com/api/videos/?key={api_key}&q={urllib.parse.quote(search_keywords)}&per_page=3&safesearch=true"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                hits = res.json().get("hits", [])
                if hits:
                    videos = hits[0].get("videos", {})
                    v_obj = (
                        videos.get("large")
                        or videos.get("medium")
                        or videos.get("small")
                    )
                    if v_obj and "url" in v_obj:
                        return v_obj["url"]
        except Exception:
            pass
    # Fallback default video stream
    return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"


# -------------------------------------------------------------------
# 5. JSON Storyboard Generator
# -------------------------------------------------------------------
def generate_storyboard(title: str):
    """Generates multi-scene storyboard schema with character dialogues."""
    prompt = f"""
    Create a detailed 3-scene story script based on the title: '{title}'.
    Return STRICT VALID JSON only. Do not include markdown or standard conversational text.
    JSON schema:
    {{
        "story_title": "{title}",
        "scenes": [
            {{
                "scene_number": 1,
                "visual_search_keywords": "3 distinct visual keywords for background video",
                "narrative": "Scene environment narrative description.",
                "character_name": "Character Name",
                "character_gender": "male or female",
                "dialogue": "Character spoken line."
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
                temperature=0.4,
            )
            response_text = res.choices[0].message.content
        except Exception:
            pass

    if not response_text and client:
        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            response_text = res.text
        except Exception as e:
            st.error(f"LLM API Error: {e}")
            return None

    try:
        clean_json = re.sub(r"```json\s*|\s*```", "", response_text).strip()
        return json.loads(clean_json)
    except Exception:
        st.error("Failed to parse script output. Please try re-generating.")
        return None


# -------------------------------------------------------------------
# 6. Streamlit User Interface
# -------------------------------------------------------------------
st.title("✨ AI Story, Photo & Video Studio")
st.write(
    "Generate multi-scene scripts, scene video clips, and character neural audio!"
)

title_input = st.text_input(
    "Enter Story Title / Topic:", placeholder="e.g. Cyberpunk Gaming Tournament"
)

if st.button("🚀 Generate Multi-Scene Storyboard"):
    if not title_input:
        st.warning("Please enter a title first!")
    else:
        with st.spinner("Generating script and character scene dialogues..."):
            board = generate_storyboard(title_input)
            if board:
                st.session_state["storyboard"] = board

if "storyboard" in st.session_state:
    board = st.session_state["storyboard"]
    st.subheader(f"📖 {board.get('story_title', 'Generated Story')}")
    st.divider()

    for idx, scene in enumerate(board.get("scenes", [])):
        st.markdown(f"### 🎬 Scene {scene['scene_number']}")

        col_video, col_details = st.columns([1, 1])

        with col_video:
            with st.spinner(
                f"Fetching scene {scene['scene_number']} video..."
            ):
                v_url = get_pixabay_video(scene["visual_search_keywords"])
                st.video(v_url)
                st.caption(
                    f"🔍 **Visual Keywords:** `{scene['visual_search_keywords']}`"
                )

        with col_details:
            st.markdown(
                f'<div class="story-card">'
                f"<b>Narrative:</b> {scene['narrative']}<br><br>"
                f"<b>Character:</b> 👤 <code>{scene['character_name']}</code> ({scene['character_gender'].capitalize()})"
                f"</div>",
                unsafe_allow_html=True,
            )

            st.info(f"💬 \"{scene['dialogue']}\"")

            audio_file = f"scene_{idx+1}_voice.mp3"
            with st.spinner("Rendering character neural audio..."):
                audio_path = synthesize_audio(
                    scene["dialogue"], scene["character_gender"], audio_file
                )
                if audio_path:
                    st.audio(audio_path, format="audio/mp3")

        st.divider()
