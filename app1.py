import streamlit as st
import time
from google import genai

# 1. Page Configuration
st.set_page_config(page_title="AI Story & Video Generator", page_icon="🎨", layout="wide")

# Initialize Gemini Client using Streamlit Secrets
# Make sure GEMINI_API_KEY is set in Streamlit Cloud -> Settings -> Secrets
if "GEMINI_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
else:
    # Fallback to default environment lookup
    client = genai.Client()

# 2. Sidebar Customization (User-selected colors)
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
    @keyframes pulse {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.03); }}
        100% {{ transform: scale(1); }}
    }}
    .animated-box {{
        background: linear-gradient(135deg, #6e8efb, #a770ef);
        height: 250px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 24px;
        font-weight: bold;
        animation: pulse 2s infinite;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# 3. App Title & Subtitle
st.title("✨ AI Story & Animation Studio")
st.write("Enter a title, set your desired word limit, and generate a fully customized story!")

# 4. User Inputs
col_input, col_slider = st.columns([2, 1])

with col_input:
    story_title = st.text_input("Enter your Story Title:", placeholder="e.g., The Secret of the Neon Forest")

with col_slider:
    # 📏 Word Limit Feature
    word_limit = st.slider(
        label="📏 Select Word Limit:",
        min_value=50,
        max_value=1000,
        value=300,
        step=25,
        help="Drag the slider or click the number box to type your word limit (50–1000 words)."
    )

# Function to generate story using Gemini API
def generate_gemini_story(title: str, limit: int) -> str:
    prompt = (
        f"Write an immersive, detailed, creative story strictly titled '{title}'. "
        f"The storyline must be deeply centered around this title. "
        f"Target word count: strictly around {limit} words. Do not make it brief or summarize—write out the full narrative."
    )
    
    # Updated model string to gemini-1.5-flash (or gemini-2.0-flash)
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt,
    )
    return response.text

# 5. Core Application Logic
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

            # 6. User Feedback for Video Generation
            st.write("---")
            st.write("### Do you like this story?")
            col1, col2 = st.columns([1, 4])
            
            with col1:
                liked = st.button("👍 Yes, generate animation!")
            
            if liked:
                st.success("Story approved! Generating animated video...")
                with st.spinner("Rendering animation..."):
                    time.sleep(2)
                    
                st.write("### 🎬 Generated Animation")
                st.markdown(
                    f'<div class="animated-box">🎬 Animation preview for "{story_title}"</div>', 
                    unsafe_allow_html=True
                )

        except Exception as e:
            st.error(f"Error generating story: {e}")

# Instructions for dependencies
st.sidebar.write("---")
st.sidebar.info("Dependencies needed in `requirements.txt`:\n- `streamlit`\n- `google-genai`")
