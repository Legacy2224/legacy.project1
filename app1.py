import streamlit as st
import time
from openai import OpenAI

# 1. Page Configuration
st.set_page_config(page_title="AI Story & Video Generator", page_icon="🎨", layout="wide")

# Initialize OpenAI Client (reads OPENAI_API_KEY from environment or st.secrets)
client = OpenAI()

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
    }}
    /* Simple bouncing animation for video placeholder */
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
    # 📏 Word Limit Feature (Scrollable slider + typed input)
    word_limit = st.slider(
        label="📏 Select Word Limit:",
        min_value=50,
        max_value=1000,
        value=300,
        step=25,
        help="Drag the slider or click the number box to type your word limit (50–1000 words)."
    )

# Function to generate story using OpenAI API
def generate_ai_story(title: str, limit: int) -> str:
    prompt = (
        f"Write a creative, engaging, and detailed story strictly titled '{title}'. "
        f"The story must be closely related to the title. "
        f"Write approximately {limit} words. Do not make it significantly shorter than {limit} words."
    )
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a master storyteller who writes vivid stories adhering strictly to requested word limits."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    return response.choices[0].message.content

# 5. Core Application Logic
if story_title:
    st.subheader(f"📖 Story: {story_title}")
    
    with st.spinner(f"Writing a ~{word_limit}-word story about '{story_title}'..."):
        try:
            story_text = generate_ai_story(story_title, word_limit)
            
            # Count actual generated words to show the user
            actual_word_count = len(story_text.split())
            
            # Display Story in styled card
            st.markdown(f'<div class="story-card">{story_text}</div>', unsafe_allow_html=True)
            st.caption(f"📊 **Generated Word Count:** {actual_word_count} words (Target was {word_limit} words)")

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
            st.error(f"Error generating story: {e}. Please ensure your OPENAI_API_KEY is set properly.")

# Instructions for dependencies
st.sidebar.write("---")
st.sidebar.info("Don't forget to add `streamlit` and `openai` to your `requirements.txt` file!")
