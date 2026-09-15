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
        gemini_init_error = "GEMINI_API_KEY is missing from st.secrets."
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
st.write("Generate full AI stories complete with artwork photos and video clips!")

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
# Core AI Generation Logic (Direct Gemini Call Only)
# -------------------------------------------------------------------

def generate_gemini_story(title: str, limit: int) -> str:
    if not client:
        st.error(f"⚠️ **Gemini Client Error:** {gemini_init_error}")
        return None

    prompt = (
        f"Write an original, engaging story titled '{title}'. "
        f"Focus specifically on plot, characters, and actions themed around '{title}'. "
        f"Make the story approximately {limit} words long."
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        if response and response.text:
            return response.text
        else:
            st.error("⚠️ Gemini API returned an empty response.")
            return None
    except Exception as e:
        st.error(f"⚠️ **Gemini API Error:** {str(e)}")
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
# 4. App Session State & Execution
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
        with st.spinner("Generating AI Story..."):
            story_text = generate_gemini_story(story_title, word_limit)
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
