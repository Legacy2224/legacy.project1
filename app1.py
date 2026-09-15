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

# Initialize Gemini Client
client = None
gemini_init_error = None

try:
    if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
        gemini_key = str(st.secrets["GEMINI_API_KEY"]).strip()
        if gemini_key and not gemini_key.startswith("your_"):
            client = genai.Client(api_key=gemini_key)
        else:
            gemini_init_error = "GEMINI_API_KEY in secrets is using a placeholder string."
    else:
        gemini_init_error = "GEMINI_API_KEY missing from st.secrets."
except Exception as e:
    gemini_init_error = str(e)

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
st.write("Generate stories with **AI Artwork Photos** and **Motion Videos**!")

col_input, col_slider = st.columns([2, 1])

with col_input:
    story_title = st.text_input(
        "Enter your Story Title:", 
        placeholder="e.g., gaming"
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
# Story Generation Engine (No Generic Text Fallback)
# -------------------------------------------------------------------

def build_strict_prompt(title: str, limit: int) -> str:
    return (
        f"Write a rich, original story titled '{title}'. "
        f"Focus specifically on plot, characters, and events themed around '{title}'. "
        f"Target approximately {limit} words."
    )

def generate_gemini_story(title: str, limit: int) -> str:
    prompt = build_strict_prompt(title, limit)
    errors = []

    # Tier 1: Try Gemini API directly
    if client:
        for model_name in ["gemini-2.5-flash", "gemini-2.0-flash"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                errors.append(f"Gemini ({model_name}) Error: {str(e)}")
    else:
        errors.append(f"Gemini Client not initialized: {gemini_init_error}")

    # Tier 2: Try Groq API (if configured in secrets)
    if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
        try:
            groq_key = str(st.secrets["GROQ_API_KEY"]).strip()
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": min(4000, max(500, int(limit * 2.5)))
            }
            res = requests.post(url, json=payload, headers=headers, timeout=8)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
            else:
                errors.append(f"Groq API Error Status {res.status_code}: {res.text}")
        except Exception as e:
            errors.append(f"Groq API Exception: {str(e)}")

    # Display real error diagnostic instead of running template loop
    error_report = "\n".join([f"- {err}" for err in errors])
    st.error(f"**API Execution Failed! Diagnostic Report:**\n{error_report}")
    return None

def get_free_photo_url(title: str) -> str:
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
# Execution Logic
# -------------------------------------------------------------------
if story_title:
    st.subheader(f"📖 Story: {story_title}")
    
    with st.spinner("Writing story..."):
        story_text = generate_gemini_story(story_title, word_limit)

    if story_text:
        actual_words = len(story_text.split())
        st.markdown(f'<div class="story-card">{story_text}</div>', unsafe_allow_html=True)
        st.caption(f"📊 **Word Count:** {actual_words} words (Target: {word_limit})")

        st.write("---")
        st.write("### 🎬 Visual & Media Studio")
        
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            if st.button("🖼️ Generate AI Photo"):
                with st.spinner("Rendering photo artwork..."):
                    photo_url = get_free_photo_url(story_title)
                    st.image(photo_url, caption=f"Generated Photo: {story_title}", use_container_width=True)

        with btn_col2:
            if st.button("🎥 Generate & Play Scene Video"):
                with st.spinner("Loading video stream..."):
                    video_url = get_free_pixabay_video_url(story_title)
                    st.video(video_url)
