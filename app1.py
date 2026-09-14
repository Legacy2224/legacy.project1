import tempfile
import time
import requests
import streamlit as st
import replicate
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
# 2. Sidebar Customization (User-selected colors)
# -------------------------------------------------------------------
st.sidebar.title("⚙️ Custom Styling")
bg_color = st.sidebar.color_picker("Pick App Background Color", "#F0F2F6")
text_color = st.sidebar.color_picker("Pick Text Color", "#1F1F1F")
card_color = st.sidebar.color_picker("Pick Card Background Color", "#FFFFFF")

# Apply custom styling dynamically with CSS
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
# 3. App Title & Subtitle
# -------------------------------------------------------------------
st.title("✨ AI Story & Animation Studio")
st.write("Enter a title, set your desired word limit, and generate a fully customized story and animation!")

# -------------------------------------------------------------------
# 4. User Inputs
# -------------------------------------------------------------------
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
        help="Drag the slider or click the number box to type your word limit (50–1000 words)."
    )

# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------

def generate_gemini_story(title: str, limit: int) -> str:
    """Generates a story using gemini-3.1-flash-lite (high free-tier limits)."""
    prompt = (
        f"Write an immersive, detailed, creative story strictly titled '{title}'. "
        f"The storyline must be deeply centered around this title. "
        f"Target word count: strictly around {limit} words. Do not make it brief or summarize—write out the full narrative."
    )
    
    # Using gemini-3.1-flash-lite to prevent 429 Resource Exhausted errors
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )
    return response.text


def generate_free_animation(title: str, story: str) -> str:
    """Generates a free video using Replicate's zero-scope video model."""
    video_prompt = f"Cinematic 3D animation visual based on '{title}': {story[:200]}"
    
    # Run open-source video generation via Replicate API
    output = replicate.run(
        "anotherjesse/zeroscope-v2-xl:9f747673945c62801b13b84701c783929c0eed26e52c2e145bab317e07b3d7a9",
        input={"prompt": video_prompt}
    )
    
    # Replicate returns a URL to the MP4 file
    if isinstance(output, list) and len(output) > 0:
        return output[0]
    return output

# -------------------------------------------------------------------
# 5. Core Application Logic
# -------------------------------------------------------------------
if story_title:
    st.subheader(f"📖 Story: {story_title}")
    
    with st.spinner(f"Writing a ~{word_limit}-word story about '{story_title}'..."):
        try:
            story_text = generate_gemini_story(story_title, word_limit)
            
            # Count actual words generated
            actual_word_count = len(story_text.split())
            
            # Display Story in card
            st.markdown(f'<div class="story-card">{story_text}</div>', unsafe_allow_html=True)
            st.caption(f"📊 **Generated Word Count:** {actual_word_count} words (Target: {word_limit} words)")

            # -------------------------------------------------------
            # 6. Video Generation
            # -------------------------------------------------------
            st.write("---")
            st.write("### Do you like this story?")
            
            if st.button("👍 Yes, generate animation!"):
                st.info("Story approved! Generating video via Replicate (takes ~30-60 seconds)...")
                
                with st.spinner("Rendering animation..."):
                    try:
                        video_url = generate_free_animation(story_title, story_text)
                        
                        st.write("### 🎬 Generated Animation")
                        # Display video directly from the URL
                        st.video(video_url)
                        st.success("Animation generated successfully!")
                    
                    except Exception as vid_err:
                        st.error(
                            f"Error generating video: {vid_err}\n\n"
                            "Make sure `REPLICATE_API_TOKEN` is added to your Streamlit secrets."
                        )

        except Exception as e:
            if "429" in str(e):
                st.error("Free rate limit reached for Gemini. Please wait 30 seconds and try clicking generate again.")
            else:
                st.error(f"Error generating story: {e}")

# Sidebar Info
st.sidebar.write("---")
st.sidebar.info("Ensure `streamlit`, `google-genai`, and `replicate` are in your `requirements.txt` file!")
