import streamlit as st
import os
import io
import time
from PIL import Image
from gtts import gTTS
from groq import Groq
from huggingface_hub import InferenceClient

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI Story & Media Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Sidebar: Custom Styling & Theme Selection
# ---------------------------------------------------------
st.sidebar.title("🎨 Theme & Customization")

theme_choice = st.sidebar.selectbox(
    "Choose Color Theme",
    ["Dark Midnight", "Light Elegant", "Cyberpunk Neon", "Enchanted Forest", "Sunset Glow"]
)

# Theme CSS Dictionary
THEMES = {
    "Dark Midnight": {
        "bg": "#0e1117", "card": "#1e232a", "text": "#ffffff", "accent": "#4A90E2"
    },
    "Light Elegant": {
        "bg": "#f8f9fa", "card": "#ffffff", "text": "#212529", "accent": "#0d6efd"
    },
    "Cyberpunk Neon": {
        "bg": "#050505", "card": "#120024", "text": "#00ffcc", "accent": "#ff007f"
    },
    "Enchanted Forest": {
        "bg": "#0b1d13", "card": "#132a1c", "text": "#e0f2fe", "accent": "#22c55e"
    },
    "Sunset Glow": {
        "bg": "#1a0b1c", "card": "#2d1236", "text": "#fdf2f8", "accent": "#f43f5e"
    }
}

active_theme = THEMES[theme_choice]

# Inject Custom CSS
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {active_theme['bg']};
        color: {active_theme['text']};
    }}
    div[data-testid="stSidebar"] {{
        background-color: {active_theme['card']};
    }}
    .story-card {{
        background-color: {active_theme['card']};
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid {active_theme['accent']};
        margin-bottom: 20px;
    }}
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# API Keys Handling (Secrets + Sidebar Fallbacks)
# ---------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 API Configuration")

# 1. Groq API Key (For Text)
groq_api_key = st.secrets.get("GROQ_API_KEY") if "GROQ_API_KEY" in st.secrets else None
if not groq_api_key:
    groq_api_key = st.sidebar.text_input(
        "Groq API Key (Text Gen)", 
        type="password", 
        help="Get a free key at https://console.groq.com/keys"
    )

# 2. Hugging Face Token (For Images)
hf_token = st.secrets.get("HF_TOKEN") if "HF_TOKEN" in st.secrets else None
if not hf_token:
    hf_token = st.sidebar.text_input(
        "Hugging Face Token (Image Gen)", 
        type="password", 
        help="Get a free token at https://huggingface.co/settings/tokens"
    )

if groq_api_key and hf_token:
    st.sidebar.success("API Keys Loaded!")

# ---------------------------------------------------------
# AI Inference Helper Functions
# ---------------------------------------------------------
def get_active_groq_models(client: Groq) -> list:
    """Dynamically fetches active text models from Groq."""
    try:
        models_data = client.models.list()
        active_models = [
            m.id for m in models_data.data 
            if "whisper" not in m.id.lower() and "safetensors" not in m.id.lower()
        ]
        if active_models:
            return active_models
    except Exception:
        pass
    
    return ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

def generate_ai_story(prompt: str, max_words: int, api_key: str) -> str:
    """Generates story text via Groq."""
    client = Groq(api_key=api_key)
    
    system_prompt = (
        f"You are a creative storyteller. Write a narrative story based on '{prompt}'. "
        f"Keep the total length to approximately {max_words} words. "
        "Write clear, vivid, cinematic sentences."
    )
    
    models_to_try = get_active_groq_models(client)
    last_error = None

    for model in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Write the story for '{prompt}'."}
                ],
                max_tokens=max_words * 3,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_error = e
            continue

    st.error(f"Text Generation Error: {last_error}")
    return None

def generate_ai_image(prompt: str, api_key: str) -> Image.Image:
    """Generates visuals using active HF Inference models (FLUX.1-schnell with SDXL fallback)."""
    client = InferenceClient(api_key=api_key)
    enhanced_prompt = f"Digital illustration artwork of {prompt}, fairytale aesthetic, high quality, vibrant"
    
    image_models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-xl-base-1.0",
        "runwayml/stable-diffusion-v1-5"
    ]
    
    last_err = None
    for model in image_models:
        try:
            image = client.text_to_image(
                enhanced_prompt,
                model=model
            )
            return image
        except Exception as e:
            last_err = e
            continue
            
    st.error(f"Image Generation Failed on HF: {last_err}")
    return None

def create_voiceover(text: str) -> io.BytesIO:
    """Generates speech audio using gTTS."""
    fp = io.BytesIO()
    tts = gTTS(text=text, lang='en', slow=False)
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# ---------------------------------------------------------
# Main UI Layout
# ---------------------------------------------------------
st.title("🎬 AI Story, Photo & Video Studio")
st.caption("Generate custom stories, AI artwork, and full narration-driven scenes.")

# Input Controls
col_title, col_limit = st.columns([3, 1])
with col_title:
    story_title = st.text_input("Enter Story Topic or Title:", "Snow White")
with col_limit:
    word_limit = st.slider("Word Limit:", min_value=50, max_value=500, value=150, step=25)

mode_choice = st.radio(
    "Choose Output Format:",
    ["Story & Photo Generator", "Full Cinematic Movie/Video Scene Breakdown"],
    horizontal=True
)

generate_btn = st.button("🚀 Generate Studio Content", type="primary", use_container_width=True)

# ---------------------------------------------------------
# Execution Logic
# ---------------------------------------------------------
if generate_btn:
    if not groq_api_key or not hf_token:
        st.warning("Please configure both Groq API Key and Hugging Face Token in secrets or the sidebar.")
        st.stop()

    with st.spinner("Writing story narrative..."):
        story_text = generate_ai_story(story_title, word_limit, groq_api_key)

    if story_text:
        st.session_state['current_story'] = story_text
        st.session_state['story_title'] = story_title
        # Reset media state for new generation
        st.session_state['main_image'] = None
        st.session_state['scene_images'] = {}

if 'current_story' in st.session_state:
    story_text = st.session_state['current_story']
    title = st.session_state['story_title']

    st.markdown("---")
    st.markdown(f"<div class='story-card'><h2>📖 {title}</h2><p>{story_text}</p></div>", unsafe_allow_html=True)

    # Mode 1: Single Photo & Narrative
    if mode_choice == "Story & Photo Generator":
        st.subheader("🖼️ AI Story Illustration")
        
        if st.session_state.get('main_image') is None:
            with st.spinner("Painting relevant AI photo according to the story..."):
                image_prompt = f"A scene from {title}: {story_text[:150]}"
                st.session_state['main_image'] = generate_ai_image(image_prompt, hf_token)

        if st.session_state.get('main_image'):
            st.image(st.session_state['main_image'], caption=f"AI Generated Photo for '{title}'", use_column_width=True)

    # Mode 2: Full Scene Breakdown with Audio & Visuals
    elif mode_choice == "Full Cinematic Movie/Video Scene Breakdown":
        st.subheader("🎥 Cinematic Movie Scene Experience")
        st.info("Converting every line of the story into audio voiceover, scene visuals, and character actions.")

        lines = [line.strip() for line in story_text.split('.') if len(line.strip()) > 5]

        if 'scene_images' not in st.session_state:
            st.session_state['scene_images'] = {}

        for idx, line in enumerate(lines, 1):
            st.markdown(f"#### 🎬 Scene {idx}")
            col_vis, col_aud = st.columns([2, 1])

            with col_vis:
                if idx not in st.session_state['scene_images']:
                    with st.spinner(f"Rendering scene {idx} photo..."):
                        scene_img = generate_ai_image(f"{title}, {line}", hf_token)
                        st.session_state['scene_images'][idx] = scene_img

                if st.session_state['scene_images'].get(idx):
                    st.image(st.session_state['scene_images'][idx], use_column_width=True)

            with col_aud:
                st.write(f"**Dialogue / Line:**")
                st.info(f'"{line}."')
                
                audio_fp = create_voiceover(line)
                st.audio(audio_fp, format="audio/mp3")

            st.divider()
