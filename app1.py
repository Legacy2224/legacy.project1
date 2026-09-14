import streamlit as st
import time

# 1. Page Configuration
st.set_page_config(page_title="AI Story & Video Generator", page_icon="🎨", layout="wide")

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
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
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
st.write("Enter a title below, set your word limit, and watch your story and animation come to life!")

# 4. User Inputs
col_input, col_slider = st.columns([2, 1])

with col_input:
    story_title = st.text_input("Enter your Story Title:", placeholder="e.g., The Secret of the Neon Forest")

with col_slider:
    # 📏 Word Limit Feature (Scrollable & Editable Slider)
    word_limit = st.slider(
        label="📏 Select Word Limit:",
        min_value=0,
        max_value=1000,
        value=250,  # Default word limit
        step=10,
        help="Drag the slider or click the number box to type your exact word limit (0–1000)."
    )

# 5. Core Application Logic
if story_title:
    st.subheader(f"📖 Story: {story_title}")
    
    # Story Generation Logic (Placeholder - Replace with OpenAI API call in production)
    with st.spinner(f"Writing your story (~{word_limit} words)..."):
        time.sleep(1) # Simulates generation time
        story_text = (
            f"Once upon a time in a world inspired by '{story_title}', magical lights began to glow. "
            f"The main character stepped forward, discovering an ancient secret that changed the universe forever. "
            f"Every step brought new color, mystery, and excitement to their unbelievable journey. "
            f"(Target Length: {word_limit} words)"
        )
    
    # Display Story in a styled card
    st.markdown(f'<div class="story-card"><p>{story_text}</p></div>', unsafe_allow_html=True)
    
    # 6. User Feedback for Video Generation
    st.write("---")
    st.write("### Do you like this story?")
    col1, col2 = st.columns([1, 4])
    
    with col1:
        liked = st.button("👍 Yes, generate animation!")
    
    if liked:
        st.success("Story approved! Generating animated video...")
        
        with st.spinner("Rendering animation..."):
            time.sleep(2) # Simulates video processing
            
        # Video Display (Displays simulated animated preview; plug video URL/file here for real output)
        st.write("### 🎬 Generated Animation")
        st.markdown(
            f'<div class="animated-box">🎬 Animation preview for "{story_title}"</div>', 
            unsafe_allow_html=True
        )

# Instructions for dependencies
st.sidebar.write("---")
st.sidebar.info("Don't forget to create a `requirements.txt` file in GitHub containing `streamlit` to deploy!")
