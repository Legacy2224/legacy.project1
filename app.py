import os
import time
import streamlit as st
from dotenv import load_dotenv
from google import genai
import replicate

load_dotenv()

# Guard: Ensure keys exist before app execution
if not os.getenv("GEMINI_API_KEY") or not os.getenv("REPLICATE_API_TOKEN"):
    st.error("Missing API Keys in .env file. Please check configuration.")
    st.stop()

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

st.set_page_config(page_title="AI Story & Animation Studio", page_icon="🎬", layout="centered")

# Session state management
for key in ["story", "visual_prompt", "video_url"]:
    if key not in st.session_state:
        st.session_state[key] = None

st.title("🎬 AI Story & Animation Studio")

# --- Step 1: Input & Story Generation ---
with st.form("story_form"):
    title = st.text_input("Story Title")
    description = st.text_area("Concept / Plot Overview")
    length = st.selectbox("Target Length", ["Short (~150 words)", "Medium (~300 words)", "Long (~500 words)"])
    submit_story = st.form_submit_button("Generate Narrative")

if submit_story:
    if not title or not description:
        st.warning("Both Title and Concept are required.")
    else:
        with st.spinner("Generating script via Gemini..."):
            prompt = f"Write a vivid narrative story titled '{title}' based on: {description}. Length: {length}."
            try:
                res = gemini_client.models.generate_content(
                    model="gemini-2.5-flash", 
                    contents=prompt
                )
                st.session_state.story = res.text
                st.session_state.video_url = None
                st.session_state.visual_prompt = None
            except Exception as e:
                st.error(f"Gemini API Error: {str(e)}")

# --- Step 2: Review & Video Prompt Construction ---
if st.session_state.story:
    st.markdown("---")
    st.subheader("Generated Narrative")
    st.write(st.session_state.story)

    if st.button("Approve & Prepare Video Prompt"):
        with st.spinner("Extracting visual sequence..."):
            extract_prompt = (
                "Convert this story into a single, highly visual camera direction prompt "
                "for a video generator. Focus on subject, cinematic lighting, and motion. "
                f"Keep it under 60 words:\n\n{st.session_state.story}"
            )
            res = gemini_client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=extract_prompt
            )
            # Inject cinematic tags
            st.session_state.visual_prompt = f"{res.text.strip()}, highly detailed, 8k resolution, cinematic lighting, photorealistic, 24fps"

# --- Step 3: Render Video ---
if st.session_state.visual_prompt:
    st.markdown("---")
    st.subheader("Visual Prompt Strategy")
    st.code(st.session_state.visual_prompt)

    if st.button("Render Animation 🎥"):
        with st.spinner("Submitting to Replicate GPU cluster (may take 60-120s)..."):
            try:
                output = replicate.run(
                    "minimax/video-01",
                    input={
                        "prompt": st.session_state.visual_prompt,
                        "prompt_optimizer": True
                    }
                )
                st.session_state.video_url = output
            except Exception as e:
                st.error(f"Replicate Generation Error: {str(e)}")

if st.session_state.video_url:
    st.markdown("---")
    st.subheader("Final Animation Output")
    st.video(st.session_state.video_url)
