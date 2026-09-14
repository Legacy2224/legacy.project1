import tempfile
import time
import requests
import urllib.parse
import streamlit as st
from google import genai

# -------------------------------------------------------------------
# 1. Page Configuration
# -------------------------------------------------------------------
st.set_page_config(
    page_title="AI Story & Video Generator", 
    page_icon="🎨", 
    layout="wide"
)

# Initialize Gemini Client using Streamlit Secrets
try:
    if "GEMINI_API_KEY" in st.secrets:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        client = genai.Client()
except Exception as e:
    st.error(f"Error initializing Gemini Client: {e}. Check your Streamlit Secrets.")

# -------------------------------------------------------------------
# 2. Sidebar Customization
# -------------------------------------------------------------------
st.sidebar.title("⚙️ Custom Styling")
bg_color = st.sidebar.color_picker("Pick App Background Color", "#F0F2F6")
text_color = st.sidebar.color_picker("Pick Text Color", "#1F1F1F")
card_color = st.sidebar.color_picker("Pick Card Background Color", "#FFFFFF")

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
# 3. App Title & Inputs
# -------------------------------------------------------------------
st.title("✨ AI Story & Animation Studio")
st.write("Enter a title, set your desired word limit, and generate a fully customized story and visual!")

col_input, col_slider = st.columns([2, 1])

with col_input:
    story_title = st.text_input("Enter your Story Title:", placeholder="e.g., The Secret of the Neon Forest")

with col_slider:
    word_limit = st.slider(
        label="📏 Select Word Limit:",
        min_value=50,
        max_value=1000,
        value=300,
        step=25,
        help="Drag the slider or type your target word limit."
    )

# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------

def generate_gemini_story(title: str, limit: int) -> str:
    """Generates story using gemini-3.1-flash-lite (high free limits)."""
    prompt = (
        f"Write an immersive, detailed, creative story strictly titled '{title}'. "
        f"The storyline must be deeply centered around this title. "
        f"Target word count: strictly around {limit} words."
    )
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )
    return response.text


def generate_free_pollinations_image(title: str, story: str) -> str:
    """Generates 100% free visual illustration via Pollinations AI (no API key needed)."""
    clean_prompt = f"3D animation cinematic illustration of {title}, high quality fantasy concept art"
    encoded_prompt = urllib.parse.quote(clean_prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&nologo=true"
    return image_url

# -------------------------------------------------------------------
# 4. Core Application Logic
# -------------------------------------------------------------------
if story_title:
    st.subheader(f"📖 Story: {story_title}")
    
    with st.spinner(f"Writing a ~{word_limit}-word story about '{story_title}'..."):
        try:
            story_text = generate_gemini_story(story_title, word_limit)
            actual_word_count = len(story_text.split())
            
            st.markdown(f'<div class="story-card">{story_text}</div>', unsafe_allow_html=True)
            st.caption(f"📊 **Generated Word Count:** {actual_word_count} words (Target: {word_limit} words)")

            # -------------------------------------------------------
            # 5. Visual Animation Section
            # -------------------------------------------------------
            st.write("---")
            st.write("### Do you like this story?")
            
            if st.button("👍 Yes, generate visual animation!"):
                with st.spinner("Creating visual artwork..."):
                    visual_url = generate_free_pollinations_image(story_title, story_text)
                    st.write("### 🎬 Animated Story Scene")
                    st.image(visual_url, caption=f"Visual representation for '{story_title}'", use_column_width=True)
                    st.success("Visual generated for free with zero rate limits!")

        except Exception as e:
            if "429" in str(e):
                st.error("Free rate limit reached for Gemini. Please wait 15 seconds and try again.")
            else:
                st.error(f"Error generating story: {e}")

# Sidebar Info
st.sidebar.write("---")
st.sidebar.info("Ensure `streamlit` and `google-genai` are in your `requirements.txt` file!")
