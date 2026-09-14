import tempfile
import streamlit as st
import time
from google import genai
from google.genai import types

# 1. Page Configuration
st.set_page_config(page_title="AI Story & Video Generator", page_icon="🎨", layout="wide")

# Initialize Gemini Client using Streamlit Secrets
try:
    if "GEMINI_API_KEY" in st.secrets:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        client = genai.Client()
except Exception as e:
    st.error(f"Error initializing Gemini Client: {e}. Please check your Secrets configuration.")

# 2. Sidebar Customization
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

# 3. App Title
st.title("✨ AI Story & Animation Studio")
st.write("Enter a title, set your desired word limit, and generate a fully customized story!")

# 4. User Inputs
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

def generate_gemini_story(title: str, limit: int) -> str:
    prompt = (
        f"Write an immersive, detailed, creative story strictly titled '{title}'. "
        f"The storyline must be deeply centered around this title. "
        f"Target word count: strictly around {limit} words. Do not make it brief or summarize—write out the full narrative."
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text

# Function to generate animation video using Veo model
def generate_story_animation(title: str, story: str):
    video_prompt = f"Cinematic, high-quality 3D animation visual depicting the main theme of the story '{title}': {story[:300]}"
    
    # Trigger long-running video generation request
    operation = client.models.generate_videos(
        model="veo-3.1-fast-generate-preview",
        prompt=video_prompt,
        config=types.GenerateVideosConfig(
            aspect_ratio="16:9",
            duration_seconds=6,
        )
    )
    
    # Poll operation status until video processing is completed
    while not operation.done:
        time.sleep(10)
        operation = client.operations.get_videos_operation(operation)
        
    return operation.response.generated_videos[0].video

# 5. Core Application Logic
if story_title:
    st.subheader(f"📖 Story: {story_title}")
    
    with st.spinner(f"Writing a ~{word_limit}-word story about '{story_title}'..."):
        try:
            story_text = generate_gemini_story(story_title, word_limit)
            actual_word_count = len(story_text.split())
            
            st.markdown(f'<div class="story-card">{story_text}</div>', unsafe_allow_html=True)
            st.caption(f"📊 **Generated Word Count:** {actual_word_count} words (Target: {word_limit} words)")

            # 6. Animation Generation Section
            st.write("---")
            st.write("### Do you like this story?")
            
            if st.button("👍 Yes, generate animation!"):
                st.info("Story approved! Video generation takes around 1-2 minutes. Please wait...")
                with st.spinner("Generating animation with Veo model..."):
                    video_result = generate_story_animation(story_title, story_text)
                    
                    # Save video to temporary file for Streamlit output
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                        tmp_file.write(video_result.video_bytes)
                        tmp_path = tmp_file.name

                st.write("### 🎬 Generated Animation")
                st.video(tmp_path)

        except Exception as e:
            st.error(f"Error processing request: {e}")

# Sidebar Info
st.sidebar.write("---")
st.sidebar.info("Ensure `streamlit` and `google-genai` are in your `requirements.txt` file!")
