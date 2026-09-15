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
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        client = genai.Client()
except Exception as e:
    st.sidebar.warning("Gemini Client initialization warning. Ensure GEMINI_API_KEY is configured.")

# -------------------------------------------------------------------
# 2. Custom UI Styling
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
        placeholder="e.g., A cybernetic owl flying through a neon forest"
    )

with col_slider:
    word_limit = st.slider(
        label="📏 Select Word Limit:",
        min_value=50,
        max_value=1000,
        value=250,
        step=25
    )

# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------

def generate_story_with_groq_fallback(title: str, limit: int) -> str:
    """Attempts Groq API using updated, active models."""
    if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
        groq_key = str(st.secrets["GROQ_API_KEY"]).strip()
        if groq_key and not groq_key.startswith("gsk_your_"):
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
            
            groq_models = [
                "llama-3.1-8b-instant",
                "llama-3.3-70b-specdec",
                "llama3-70b-8192"
            ]
            
            for model in groq_models:
                payload = {
                    "model": model,
                    "messages": [{
                        "role": "user", 
                        "content": f"Write an immersive story strictly titled '{title}'. Target word count: around {limit} words."
                    }],
                    "temperature": 0.7
                }
                try:
                    res = requests.post(url, json=payload, headers=headers, timeout=8)
                    if res.status_code == 200:
                        return res.json()["choices"][0]["message"]["content"]
                except Exception:
                    pass
                
    return None


def generate_story_with_huggingface(title: str, limit: int) -> str:
    """Free public fallback using Hugging Face router."""
    url = "https://router.huggingface.co/hf-inference/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    if "HF_TOKEN" in st.secrets and st.secrets["HF_TOKEN"]:
        headers["Authorization"] = f"Bearer {st.secrets['HF_TOKEN'].strip()}"

    payload = {
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "messages": [{
            "role": "user", 
            "content": f"Write an immersive story strictly titled '{title}'. Target word count: around {limit} words."
        }],
        "max_tokens": 1000
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
    return None


def generate_story_with_pollinations(title: str, limit: int) -> str:
    """100% Free emergency fallback engine - No API key required, zero rate limits."""
    prompt = f"Write an immersive story titled '{title}'. Target word count: strictly around {limit} words."
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://text.pollinations.ai/{encoded_prompt}"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200 and res.text:
            return res.text
    except Exception:
        pass
    return None


def generate_gemini_story(title: str, limit: int) -> str:
    """Generates story text with multi-tier failover: Groq -> Gemini -> Hugging Face -> Pollinations."""
    prompt = (
        f"Write an immersive story strictly titled '{title}'. "
        f"Target word count: strictly around {limit} words."
    )
    
    # Tier 1: Groq API
    groq_story = generate_story_with_groq_fallback(title, limit)
    if groq_story:
        return groq_story

    # Tier 2: Gemini (Flash & Lite models)
    models_to_try = [
        "gemini-2.5-flash", 
        "gemini-2.5-flash-lite", 
        "gemini-2.0-flash", 
        "gemini-2.0-flash-lite"
    ]
    
    if client:
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text
            except Exception as err:
                err_str = str(err)
                if "429" in err_str:
                    continue  # Skip to next model immediately on rate limit
                elif "404" in err_str or "NOT_FOUND" in err_str:
                    continue

    # Tier 3: Hugging Face Public Inference
    hf_story = generate_story_with_huggingface(title, limit)
    if hf_story:
        return hf_story

    # Tier 4: Emergency Free Keyless Engine (Pollinations Text)
    pollinations_story = generate_story_with_pollinations(title, limit)
    if pollinations_story:
        return pollinations_story

    raise RuntimeError(
        "All story generation services are temporarily unreachable. Please check your internet connection and try again!"
    )


def get_free_photo_url(title: str) -> str:
    """Generates free dynamic AI photo artwork via Pollinations AI (No API Key needed)."""
    encoded_prompt = urllib.parse.quote(f"3D cinematic photo of {title}, highly detailed, 8k resolution")
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true&seed=42"


def get_free_pixabay_video_url(title: str) -> str:
    """Attempts Pixabay API search for stock videos, falls back to a default sample video on error."""
    if "PIXABAY_API_KEY" in st.secrets and st.secrets["PIXABAY_API_KEY"]:
        api_key = st.secrets["PIXABAY_API_KEY"]
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

# -------------------------------------------------------------------
# 4. Core Execution Logic
# -------------------------------------------------------------------
if story_title:
    st.subheader(f"📖 Story: {story_title}")
    
    # Re-generate story only if title has changed
    if st.session_state.last_title != story_title:
        with st.spinner("Writing story..."):
            try:
                story_text = generate_gemini_story(story_title, word_limit)
                st.session_state.current_story = story_text
                st.session_state.last_title = story_title
            except Exception as e:
                st.error(f"Error generating story: {e}")

    # Display Story Content
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
st.sidebar.info("Free Tech Stack: Groq / Gemini / HF Router / Pollinations Text & Photo / Pixabay Engine")
