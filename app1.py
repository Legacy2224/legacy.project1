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

# Initialize Gemini Client
try:
    if "GEMINI_API_KEY" in st.secrets:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        client = genai.Client()
except Exception as e:
    st.error(f"Error initializing Gemini Client: {e}")

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
st.write("Enter a title, set your desired word limit, and generate a fully customized story and visual video!")

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


def get_free_video(title: str) -> str:
    """Fetches a free context-matching HD video stream URL via Pexels API."""
    if "PEXELS_API_KEY" not in st.secrets:
        # Default fallback sample video if key is missing
        return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
        
    headers = {"Authorization": st.secrets["PEXELS_API_KEY"]}
    query = urllib.parse.quote(title)
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=1"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data.get("videos"):
            # Return high definition MP4 video link
            video_files = data["videos"][0]["video_files"]
            hd_video = next((f for f in video_files if f.get("quality") == "hd"), video_files[0])
            return hd_video["link"]
            
    # Default video if no search result is returned
    return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"

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

    if st.session_state.current_story:
        story_text = st.session_state.current_story
        actual_word_count = len(story_text.split())
        
        st.markdown(f'<div class="story-card">{story_text}</div>', unsafe_allow_html=True)
        st.caption(f"📊 **Generated Word Count:** {actual_word_count} words (Target: {word_limit} words)")

        # -------------------------------------------------------
        # 5. Free Video Section
        # -------------------------------------------------------
        st.write("---")
        st.write("### Do you like this story?")
        
        if st.button("🎬 Fetch Free Video Scene!"):
            with st.spinner("Retrieving HD video scene..."):
                video_url = get_free_video(story_title)
                st.write("### 🎬 Scene Video")
                st.video(video_url)
                st.success("Video loaded successfully with 100% free API access!")

# Sidebar Info
st.sidebar.write("---")
st.sidebar.info("Ensure `streamlit`, `requests`, and `google-genai` are in your `requirements.txt` file!")
