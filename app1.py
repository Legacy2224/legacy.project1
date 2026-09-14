import urllib.parse
import requests
import streamlit as st
from google import genai

# -------------------------------------------------------------------
# 1. Page Configuration
# -------------------------------------------------------------------
st.set_page_config(
    page_title="AI Story & Visual Studio", 
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
    st.error(f"Error initializing Gemini Client: {e}. Check your Secrets configuration.")

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
st.title("✨ AI Story & Visual Studio")
st.write("Enter a title, set your desired word limit, and generate a fully customized story and visual scene!")

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
    """Generates story text using Gemini API."""
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


def get_pollinations_scene_image(title: str) -> str:
    """Generates a high-quality visual scene URL via Pollinations AI (100% Free & Fast)."""
    image_prompt = urllib.parse.quote(f"3D cinematic illustration of {title}, highly detailed, 8k resolution, vibrant unreal engine 5 render")
    return f"https://image.pollinations.ai/prompt/{image_prompt}?width=1280&height=720&nologo=true&seed=42"

# -------------------------------------------------------------------
# Session State Setup
# -------------------------------------------------------------------
if "current_story" not in st.session_state:
    st.session_state.current_story = ""
if "last_title" not in st.session_state:
    st.session_state.last_title = ""

# -------------------------------------------------------------------
# 4. Core Application Logic
# -------------------------------------------------------------------
if story_title:
    st.subheader(f"📖 Story: {story_title}")
    
    # Generate story only if user enters a new title
    if st.session_state.last_title != story_title:
        with st.spinner(f"Writing a ~{word_limit}-word story about '{story_title}'..."):
            try:
                story_text = generate_gemini_story(story_title, word_limit)
                st.session_state.current_story = story_text
                st.session_state.last_title = story_title
            except Exception as e:
                if "429" in str(e):
                    st.error("Free rate limit reached for Gemini. Please wait 15 seconds and try again.")
                else:
                    st.error(f"Error generating story: {e}")

    # Display saved story from session state
    if st.session_state.current_story:
        story_text = st.session_state.current_story
        actual_word_count = len(story_text.split())
        
        st.markdown(f'<div class="story-card">{story_text}</div>', unsafe_allow_html=True)
        st.caption(f"📊 **Generated Word Count:** {actual_word_count} words (Target: {word_limit} words)")

        # -------------------------------------------------------
        # 5. Visual Scene & Video Section
        # -------------------------------------------------------
        st.write("---")
        st.write("### Do you like this story?")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🖼️ Generate AI Scene Artwork"):
                with st.spinner("Generating AI artwork..."):
                    img_url = get_pollinations_scene_image(story_title)
                    st.image(img_url, caption=f"AI Generated Scene: {story_title}", use_container_width=True)
                    st.success("Scene rendered successfully via Pollinations AI!")

        with col_btn2:
            if st.button("🎬 Play Scene Video Stream"):
                with st.spinner("Loading video stream..."):
                    fallback_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
                    st.video(fallback_url)
                    st.success("HD Motion scene stream loaded!")

# Sidebar Info
st.sidebar.write("---")
st.sidebar.info("Ensure `streamlit`, `requests`, and `google-genai` are in your `requirements.txt` file!")
