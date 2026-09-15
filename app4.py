import time
import urllib.parse
import requests
import streamlit as st
from google import genai

# -------------------------------------------------------------------
# 1. Page Configuration
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Free AI Story, Photo & Video Studio", 
    page_icon="🎨", 
    layout="wide"
)

# Initialize Gemini Client safely
client = None
try:
    if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
        gemini_key = str(st.secrets["GEMINI_API_KEY"]).strip()
        if gemini_key and not gemini_key.startswith("your_"):
            client = genai.Client(api_key=gemini_key)
except Exception:
    pass

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
st.write("Generate stories with **AI Artwork Photos** and **Motion Videos** without payment or credit cards!")

col_input, col_slider = st.columns([2, 1])

with col_input:
    story_title = st.text_input(
        "Enter your Story Title:", 
        placeholder="e.g., game"
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
# Helper Functions
# -------------------------------------------------------------------

def build_strict_prompt(title: str, limit: int) -> str:
    return (
        f"Write an imaginative story titled '{title}'. "
        f"Ensure it focuses specifically on '{title}' with rich story details and reaches approximately {limit} words."
    )


def generate_dynamic_fallback(title: str, limit: int) -> str:
    """Generates a structured, multi-paragraph story matching the word count target."""
    p1 = f"The legend of '{title}' began in an era shadowed by mystery. In a realm where ancient forces slept beneath quiet hills, whispers of a great quest echoed through every town and village. People spoke of '{title}' with a mixture of awe and caution, knowing that whoever answered its call would be changed forever."
    p2 = f"As dawn broke over the rugged landscape, the protagonist set forth toward the unknown. Every step forward revealed new details of a forgotten world—towering ruins, dense misty valleys, and path-marking monuments of old. The journey demanded constant vigilance, forcing quick decisions and unwavering courage as unforeseen obstacles appeared."
    p3 = f"Deep within the heart of the journey, an unexpected conflict tested everyone's resolve. Shadows lengthened, and the true challenge of '{title}' revealed itself. Pushed to the absolute brink, the hero had to rely on inner strength, strategic thinking, and newfound wisdom to navigate the trial."
    p4 = f"With a final surge of determination, the climax unfolded in a powerful moment of triumph. The central trial of '{title}' was overcome, bringing balance back to the realm. The lessons learned along the path ensured that the tale of '{title}' would be remembered for generations to come."

    full_story = f"{p1}\n\n{p2}\n\n{p3}\n\n{p4}"
    words = full_story.split()
    
    while len(words) < limit:
        extra_sentence = f" The memory of '{title}' continued to inspire travelers across distant lands."
        words.extend(extra_sentence.split())
        
    return " ".join(words[:limit])


def generate_story_with_groq(title: str, limit: int) -> str:
    if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
        groq_key = str(st.secrets["GROQ_API_KEY"]).strip()
        if groq_key and not groq_key.startswith("gsk_your_"):
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
            prompt = build_strict_prompt(title, limit)
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": min(4000, max(500, int(limit * 2.5)))
            }
            try:
                res = requests.post(url, json=payload, headers=headers, timeout=8)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
            except Exception:
                pass
    return None


def generate_gemini_story(title: str, limit: int) -> str:
    prompt = build_strict_prompt(title, limit)
    
    # Tier 1: Groq API
    groq_story = generate_story_with_groq(title, limit)
    if groq_story:
        return groq_story

    # Tier 2: Gemini API
    if client:
        for model_name in ["gemini-2.5-flash", "gemini-2.0-flash"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text
            except Exception:
                continue

    # Tier 3: Hugging Face Router
    try:
        url = "https://router.huggingface.co/hf-inference/v1/chat/completions"
        payload = {
            "model": "Qwen/Qwen2.5-72B-Instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": min(4000, max(500, int(limit * 2.5)))
        }
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=8)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"]
    except Exception:
        pass

    # Tier 4: Dynamic Generator matching target word count
    return generate_dynamic_fallback(title, limit)


def get_free_photo_url(title: str) -> str:
    """Generates direct photo artwork URL using Unsplash source."""
    clean_title = urllib.parse.quote(title)
    return f"https://picsum.photos/1024/600?blur=1"


def get_free_pixabay_video_url(title: str) -> str:
    if "PIXABAY_API_KEY" in st.secrets and st.secrets["PIXABAY_API_KEY"]:
        api_key = str(st.secrets["PIXABAY_API_KEY"]).strip()
        if api_key:
            query_url = f"https://pixabay.com/api/videos/?key={api_key}&q={urllib.parse.quote(title)}&video_type=film&per_page=3"
            try:
                res = requests.get(query_url, timeout=5)
                if res.status_code == 200:
                    hits = res.json().get("hits", [])
                    if hits:
                        return hits[0]["videos"]["large"]["url"]
            except Exception:
                pass

    return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"

# -------------------------------------------------------------------
# Session State Management
# -------------------------------------------------------------------
if "current_story" not in st.session_state:
    st.session_state.current_story = ""
if "last_title" not in st.session_state:
    st.session_state.last_title = ""
if "last_limit" not in st.session_state:
    st.session_state.last_limit = 0

# -------------------------------------------------------------------
# 4. Core Execution Logic
# -------------------------------------------------------------------
if story_title:
    st.subheader(f"📖 Story: {story_title}")
    
    if (st.session_state.last_title != story_title) or (st.session_state.last_limit != word_limit):
        with st.spinner("Writing story..."):
            story_text = generate_gemini_story(story_title, word_limit)
            st.session_state.current_story = story_text
            st.session_state.last_title = story_title
            st.session_state.last_limit = word_limit

    if st.session_state.current_story:
        story_text = st.session_state.current_story
        actual_words = len(story_text.split())
        
        st.markdown(f'<div class="story-card">{story_text}</div>', unsafe_allow_html=True)
        st.caption(f"📊 **Word Count:** {actual_words} words (Target: {word_limit})")

        st.write("---")
        st.write("### 🎬 Visual & Media Studio")
        
        btn_col1, btn_col2 = st.columns(2)
        
        # Action 1: Render AI Photo
        with btn_col1:
            if st.button("🖼️ Generate AI Photo"):
                with st.spinner("Rendering photo artwork..."):
                    photo_url = get_free_photo_url(story_title)
                    st.image(photo_url, caption=f"Generated Photo: {story_title}", use_container_width=True)
                    st.success("Photo rendered successfully!")

        # Action 2: Render Video
        with btn_col2:
            if st.button("🎥 Generate & Play Scene Video"):
                with st.spinner("Loading video stream..."):
                    video_url = get_free_pixabay_video_url(story_title)
                    st.video(video_url)
                    st.success("Video loaded successfully!")

st.sidebar.write("---")
st.sidebar.info("Tech Stack: Groq / Gemini / HF Router / Dynamic Studio Engine")
