import urllib.parse
import requests
import streamlit as st
from groq import Groq
from google import genai
from gtts import gTTS
import io

# -------------------------------------------------------------------
# 1. Page Configuration
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Free AI Story, Photo & Video Studio", 
    page_icon="🎨", 
    layout="wide"
)

# -------------------------------------------------------------------
# Initialize API Clients
# -------------------------------------------------------------------
groq_client = None
gemini_client = None

# Groq Client Initialization
if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
    groq_key = str(st.secrets["GROQ_API_KEY"]).strip()
    if groq_key and not groq_key.startswith("your_"):
        groq_client = Groq(api_key=groq_key)

# Gemini Client Initialization
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    gemini_key = str(st.secrets["GEMINI_API_KEY"]).strip()
    if gemini_key and not gemini_key.startswith("your_"):
        gemini_client = genai.Client(api_key=gemini_key)

# -------------------------------------------------------------------
# 2. Custom Sidebar & Styling
# -------------------------------------------------------------------
st.sidebar.title("⚙️ Custom Styling")
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
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        line-height: 1.6;
        font-size: 16px;
        color: {text_color};
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------------------------
# 3. User Inputs
# -------------------------------------------------------------------
st.title("✨ AI Story, Photo & Video Studio")
st.write("Generate full AI stories complete with artwork photos, audio narration, and video clips!")

col_input, col_slider = st.columns([2, 1])

with col_input:
    story_title = st.text_input(
        "Enter your Story Title:", 
        placeholder="e.g., A journey through cyberpunk space"
    )

with col_slider:
    word_limit = st.slider(
        label="📏 Select Word Limit:",
        min_value=50,
        max_value=1000,
        value=350,
        step=25
    )

# -------------------------------------------------------------------
# Core AI & Media Logic
# -------------------------------------------------------------------

def generate_groq_story(title: str, limit: int) -> str:
    """Uses Groq API for rapid story generation."""
    if not groq_client:
        st.error("⚠️ GROQ_API_KEY is missing or invalid in st.secrets.")
        return None

    prompt = (
        f"Write an original, engaging story titled '{title}'. "
        f"Focus specifically on plot, characters, and actions themed around '{title}'. "
        f"Make the story approximately {limit} words long."
    )

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"⚠️ **Groq API Error:** {str(e)}")
        return None

def get_gemini_search_term(story_title: str) -> str:
    """Uses Gemini API to extract 2-3 precise visual keywords for Pixabay search."""
    if not gemini_client:
        return story_title  # Fallback to direct title

    prompt = (
        f"Extract 2 to 3 essential visual keywords for finding stock photos/videos related to: '{story_title}'. "
        "Return ONLY the keywords separated by spaces. Example output: space warrior planet"
    )

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        if response and response.text:
            return response.text.strip()
    except Exception:
        pass
    return story_title

def get_pixabay_photo_url(query: str) -> str:
    """Fetches photo from Pixabay API."""
    if "PIXABAY_API_KEY" in st.secrets and st.secrets["PIXABAY_API_KEY"]:
        api_key = str(st.secrets["PIXABAY_API_KEY"]).strip()
        url = f"https://pixabay.com/api/?key={api_key}&q={urllib.parse.quote(query)}&image_type=photo&per_page=3"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                hits = res.json().get("hits", [])
                if hits:
                    return hits[0].get("webformatURL") or hits[0].get("largeImageURL")
        except Exception:
            pass
    return "https://picsum.photos/1024/600"

def get_pixabay_video_url(query: str) -> str:
    """Fetches video clip from Pixabay API with dynamic resolution fallback."""
    if "PIXABAY_API_KEY" in st.secrets and st.secrets["PIXABAY_API_KEY"]:
        api_key = str(st.secrets["PIXABAY_API_KEY"]).strip()
        url = f"https://pixabay.com/api/videos/?key={api_key}&q={urllib.parse.quote(query)}&per_page=3"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                hits = res.json().get("hits", [])
                if hits:
                    videos = hits[0].get("videos", {})
                    # Safe fallback across video resolutions
                    for size in ["medium", "large", "small", "tiny"]:
                        if size in videos and "url" in videos[size]:
                            return videos[size]["url"]
        except Exception:
            pass
    return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

def generate_audio_narration(text: str) -> io.BytesIO:
    """Generates MP3 audio buffer using gTTS with write_to_fp."""
    tts = gTTS(text=text, lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# -------------------------------------------------------------------
# 4. Session State & Execution
# -------------------------------------------------------------------
if "current_story" not in st.session_state:
    st.session_state.current_story = ""
if "last_title" not in st.session_state:
    st.session_state.last_title = ""
if "last_limit" not in st.session_state:
    st.session_state.last_limit = 0

if story_title:
    st.subheader(f"📖 Story: {story_title}")
    
    if (st.session_state.last_title != story_title) or (st.session_state.last_limit != word_limit):
        with st.spinner("Generating AI Story via Groq..."):
            story_text = generate_groq_story(story_title, word_limit)
            if story_text:
                st.session_state.current_story = story_text
                st.session_state.last_title = story_title
                st.session_state.last_limit = word_limit
            else:
                st.session_state.current_story = ""

    if st.session_state.current_story:
        story_text = st.session_state.current_story
        actual_words = len(story_text.split())
        
        st.markdown(f'<div class="story-card">{story_text}</div>', unsafe_allow_html=True)
        st.caption(f"📊 **Word Count:** {actual_words} words (Target: {word_limit})")

        st.write("---")
        st.write("### 🎬 Visual & Media Studio")
        
        # Audio Narration Player
        if st.button("🔊 Read Story Aloud (Generate Audio)"):
            with st.spinner("Synthesizing audio narration..."):
                audio_fp = generate_audio_narration(story_text)
                st.audio(audio_fp, format="audio/mp3")

        st.write("")
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            if st.button("🖼️ Generate Photo"):
                with st.spinner("Searching Pixabay photo..."):
                    search_term = get_gemini_search_term(story_title)
                    photo_url = get_pixabay_photo_url(search_term)
                    st.image(photo_url, caption=f"Photo search keywords: '{search_term}'", use_container_width=True)

        with btn_col2:
            if st.button("🎥 Generate Scene Video"):
                with st.spinner("Searching Pixabay video..."):
                    search_term = get_gemini_search_term(story_title)
                    video_url = get_pixabay_video_url(search_term)
                    st.video(video_url)
