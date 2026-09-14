import time
import urllib.parse
import requests
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
st.title("✨ AI Story & Video Studio")
st.write("Enter a title, set your desired word limit, and generate a fully customized story and AI motion video!")

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


def generate_free_pollinations_video(title: str, max_retries: int = 3) -> bytes:
    """
    Generates a free AI MP4 motion video via Pollinations AI.
    Includes auto-retry logic for 429 rate limits and a fallback stream.
    """
    video_prompt = urllib.parse.quote(f"3D cinematic animation video of {title}, vibrant colors, moving scene, detailed motion")
    video_url = f"https://image.pollinations.ai/prompt/{video_prompt}?width=1280&height=720&model=video&nologo=true&seed=42"
    
    # Attempt request with retry logic for 429 rate limits
    for attempt in range(max_retries):
        try:
            response = requests.get(video_url, timeout=35)
            
            if response.status_code == 200:
                return response.content
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 5
                st.warning(f"Server is busy (Rate Limit 429). Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                break
        except Exception:
            time.sleep(3)

    # Reliable fallback MP4 video scene if Pollinations free GPUs are completely saturated
    st.info("ℹ️ Free AI video generator is currently at peak capacity. Loading fallback motion video...")
    fallback_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    return requests.get(fallback_url).content

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
    
    # Generate story only if the user types a new title
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

    # Display saved story from state so it doesn't disappear on button clicks
    if st.session_state.current_story:
        story_text = st.session_state.current_story
        actual_word_count = len(story_text.split())
        
        st.markdown(f'<div class="story-card">{story_text}</div>', unsafe_allow_html=True)
        st.caption(f"📊 **Generated Word Count:** {actual_word_count} words (Target: {word_limit} words)")

        # -------------------------------------------------------
        # 5. Free Real Video Generation Section
        # -------------------------------------------------------
        st.write("---")
        st.write("### Do you like this story?")
        
        if st.button("🎬 Generate Real AI Video!"):
            with st.spinner("Rendering AI video clip (takes ~15-30 seconds)..."):
                try:
                    video_bytes = generate_free_pollinations_video(story_title)
                    st.write("### 🎬 Generated Scene Video")
                    st.video(video_bytes, format="video/mp4")
                    st.success("Video loaded successfully with zero API costs!")
                except Exception as vid_err:
                    st.error(f"Error loading video stream: {vid_err}")

# Sidebar Info
st.sidebar.write("---")
st.sidebar.info("Ensure `streamlit`, `requests`, and `google-genai` are in your `requirements.txt` file!")
