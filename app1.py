import urllib.parse
import requests
import streamlit as st
from google import genai
from groq import Groq

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

# Initialize Groq Client
groq_client = None
if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
    groq_key = str(st.secrets["GROQ_API_KEY"]).strip()
    if groq_key and not groq_key.startswith("your_"):
        groq_client = Groq(api_key=groq_key)

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
# Core AI Generation & Visual Tag Extraction Logic
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

    available_models = ["gemini-2.5-flash", "gemini-2.5-pro"]
    errors = []

    for model_name in available_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and response.text:
                return response.text
        except Exception as e:
            errors.append(f"Model `{model_name}` error: {str(e)}")

    error_report = "\n".join([f"- {err}" for err in errors])
    st.error(f"⚠️ **Gemini API Execution Failed:**\n{error_report}")
    return None

def extract_visual_keywords(story_text: str, fallback_title: str) -> str:
    """Uses Groq or Gemini to extract 2-4 clean keywords representing the main visual theme."""
    prompt = (
        f"Extract 2 to 4 distinct, highly visual search keywords representing key elements "
        f"(characters, environment, core action) of this story: '{story_text[:400]}...'. "
        f"Respond ONLY with space-separated plain keywords (e.g. 'cyberpunk gamer neon classroom'). Do not include punctuation or full sentences."
    )
    
    # Try Groq first
    if groq_client:
        try:
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=20,
            )
            keywords = completion.choices[0].message.content.strip()
            if keywords:
                return keywords
        except Exception:
            pass

    # Fallback to Gemini
    if client:
        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            if res and res.text:
                return res.text.strip()
        except Exception:
            pass

    return fallback_title

def get_pixabay_photo_url(query: str) -> str:
    """Fetches a high-quality relevant photo from Pixabay API based on story keywords."""
    if "PIXABAY_API_KEY" in st.secrets and st.secrets["PIXABAY_API_KEY"]:
        api_key = str(st.secrets["PIXABAY_API_KEY"]).strip()
        if api_key:
            query_url = f"https://pixabay.com/api/?key={api_key}&q={urllib.parse.quote(query)}&image_type=photo&orientation=horizontal&per_page=5&safesearch=true"
            try:
                res = requests.get(query_url, timeout=5)
                if res.status_code == 200:
                    hits = res.json().get("hits", [])
                    if hits:
                        return hits[0]["largeImageURL"]
            except Exception:
                pass
    
    # Fallback if no specific Pixabay image found
    return f"https://picsum.photos/1024/600"

def get_pixabay_video_url(query: str) -> str:
    """Fetches a relevant video from Pixabay API based on story keywords."""
    if "PIXABAY_API_KEY" in st.secrets and st.secrets["PIXABAY_API_KEY"]:
        api_key = str(st.secrets["PIXABAY_API_KEY"]).strip()
        if api_key:
            query_url = f"https://pixabay.com/api/videos/?key={api_key}&q={urllib.parse.quote(query)}&per_page=5"
            try:
                res = requests.get(query_url, timeout=5)
                if res.status_code == 200:
                    hits = res.json().get("hits", [])
                    if hits:
                        videos = hits[0].get("videos", {})
                        video_obj = videos.get("large") or videos.get("medium") or videos.get("small")
                        if video_obj and "url" in video_obj:
                            return video_obj["url"]
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
                with st.spinner("Extracting visual scene and querying photo API..."):
                    visual_tags = extract_visual_keywords(story_text, story_title)
                    photo_url = get_pixabay_photo_url(visual_tags)
                    st.image(photo_url, caption=f"Matched Visual Tags: '{visual_tags}'", use_container_width=True)

        with btn_col2:
            if st.button("🎥 Generate & Play Scene Video"):
                with st.spinner("Extracting scene keyframes and searching video API..."):
                    visual_tags = extract_visual_keywords(story_text, story_title)
                    video_url = get_pixabay_video_url(visual_tags)
                    st.video(video_url)
