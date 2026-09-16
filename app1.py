import base64
import io
import json
import urllib.parse

import requests
import streamlit as st
from google import genai
from gtts import gTTS

# Optional Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Story, Photo & Video Studio",
    page_icon="🎨",
    layout="wide"
)


# ============================================================
# 2. API CLIENTS
# ============================================================

gemini_client = None
groq_client = None

gemini_error = None
groq_error = None


# ---------------- Gemini ----------------

try:
    if "GEMINI_API_KEY" in st.secrets:
        gemini_key = str(st.secrets["GEMINI_API_KEY"]).strip()

        if gemini_key and not gemini_key.startswith("your_"):
            gemini_client = genai.Client(api_key=gemini_key)
        else:
            gemini_error = "GEMINI_API_KEY is empty or still using a placeholder."
    else:
        gemini_error = "GEMINI_API_KEY is missing from Streamlit secrets."

except Exception as e:
    gemini_error = str(e)


# ---------------- Groq ----------------

if GROQ_AVAILABLE:

    try:
        if "GROQ_API_KEY" in st.secrets:

            groq_key = str(st.secrets["GROQ_API_KEY"]).strip()

            if groq_key and not groq_key.startswith("your_"):
                groq_client = Groq(api_key=groq_key)

    except Exception as e:
        groq_error = str(e)


# ============================================================
# 3. CUSTOM STYLING
# ============================================================

st.sidebar.title("⚙️ Custom Styling")

bg_color = st.sidebar.color_picker(
    "App Background Color",
    "#F0F2F6"
)

text_color = st.sidebar.color_picker(
    "Text Color",
    "#1F1F1F"
)

card_color = st.sidebar.color_picker(
    "Card Background Color",
    "#FFFFFF"
)

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
        border-radius: 14px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.10);
        margin-bottom: 20px;
        line-height: 1.7;
        font-size: 17px;
        color: {text_color};
    }}

    .media-card {{
        background-color: {card_color};
        padding: 20px;
        border-radius: 14px;
        margin-top: 15px;
        margin-bottom: 20px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.08);
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 4. HEADER
# ============================================================

st.title("✨ AI Story, Photo & Video Studio")

st.write(
    "Create an AI story with matching artwork, narration, "
    "and relevant video footage."
)


# ============================================================
# 5. USER INPUT
# ============================================================

col_input, col_slider = st.columns([2, 1])

with col_input:

    story_title = st.text_input(
        "Enter your Story Title",
        placeholder="e.g. Snow White and the Seven Dwarfs"
    )

with col_slider:

    word_limit = st.slider(
        "📏 Story Word Limit",
        min_value=50,
        max_value=1000,
        value=350,
        step=25
    )


# ============================================================
# 6. GEMINI STORY GENERATION
# ============================================================

def generate_gemini_story(title: str, limit: int):

    if not gemini_client:

        st.error(
            f"⚠️ Gemini Client Error: {gemini_error}"
        )

        return None

    prompt = f"""
Write an original, engaging story titled:

"{title}"

The story should strongly stay focused on the title.

Include:

- A clear beginning
- Interesting characters
- Specific locations
- Meaningful actions
- A problem or conflict
- A satisfying ending

Do NOT write generic filler.

Make the story approximately {limit} words.

Return ONLY the story.
"""

    models_to_try = [
        "gemini-3.8-flash",
        "gemini-2.5-flash"
    ]

    errors = []

    for model_name in models_to_try:

        try:

            response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt
            )

            if response and response.text:

                return response.text.strip()

        except Exception as e:

            errors.append(
                f"{model_name}: {str(e)}"
            )

    st.error(
        "Gemini story generation failed:\n\n"
        + "\n".join(errors)
    )

    return None


# ============================================================
# 7. CREATE VISUAL SCENE PROMPT
# ============================================================

def create_visual_prompt(title: str, story: str):

    if not gemini_client:
        return None

    prompt = f"""
You are a professional cinematic storyboard artist.

Story title:
{title}

Story:
{story}

Create ONE highly specific visual scene for this story.

The image must clearly represent the actual story.

Do NOT create a generic landscape.

Include:

1. Main characters
2. Their appearance
3. Their actions
4. Location
5. Important objects
6. Time of day
7. Lighting
8. Camera angle
9. Mood
10. Visual style

The scene should look like a cinematic fantasy movie frame.

If the story contains characters, make the characters the
main focus of the image.

Do not add random objects.

Do not add text.

Return ONLY the image-generation prompt.
"""

    try:

        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        if response and response.text:

            return response.text.strip()

    except Exception:

        pass

    return f"""
Create a cinematic scene from the story "{title}".

Focus on the main characters and their actions.
Show the most important story moment.
Detailed environment, cinematic lighting,
strong character expressions, fantasy movie style,
wide composition, highly detailed, no text.
"""


# ============================================================
# 8. OPTIONAL GROQ PROMPT ENHANCEMENT
# ============================================================

def improve_visual_prompt_with_groq(title, visual_prompt):

    if not groq_client:
        return visual_prompt

    try:

        completion = groq_client.chat.completions.create(

            model="llama-3.3-70b-versatile",

            messages=[
                {
                    "role": "system",
                    "content": """
You are an expert cinematic image prompt engineer.

Improve prompts for AI image generation.

Keep the original story meaning.

Make characters, actions, location and composition
very explicit.

Never replace the story with a generic landscape.

Return ONLY the improved prompt.
"""
                },

                {
                    "role": "user",
                    "content": f"""
Story title:
{title}

Original visual prompt:
{visual_prompt}
"""
                }
            ],

            temperature=0.4,

            max_tokens=500
        )

        improved = completion.choices[0].message.content

        if improved:
            return improved.strip()

    except Exception:

        pass

    return visual_prompt


# ============================================================
# 9. GEMINI IMAGE GENERATION
# ============================================================

def generate_ai_image(image_prompt):

    if not gemini_client:

        st.error("Gemini client is not available.")

        return None

    try:

        interaction = gemini_client.interactions.create(

            model="gemini-3.1-flash-image",

            input=image_prompt,

            response_format={
                "type": "image",
                "aspect_ratio": "16:9",
                "image_size": "1K"
            }
        )

        # Official Gemini image output
        if hasattr(interaction, "output_image"):

            output_image = interaction.output_image

            if output_image and output_image.data:

                return base64.b64decode(
                    output_image.data
                )

        # Fallback: inspect interaction steps
        if hasattr(interaction, "steps"):

            for step in interaction.steps:

                if getattr(step, "type", None) != "model_output":
                    continue

                content_blocks = getattr(
                    step,
                    "content",
                    []
                )

                for block in content_blocks:

                    if getattr(block, "type", None) == "image":

                        if getattr(block, "data", None):

                            return base64.b64decode(
                                block.data
                            )

    except Exception as e:

        st.error(
            f"⚠️ Gemini image generation failed:\n\n{e}"
        )

    return None


# ============================================================
# 10. EXTRACT PIXABAY SEARCH TERMS
# ============================================================

def create_video_search_query(title, story):

    if not gemini_client:

        return title

    prompt = f"""
You are selecting stock footage for a story.

Story title:
{title}

Story:
{story}

Create a Pixabay video search query.

IMPORTANT:

Pixabay searches for real-world visual concepts.

Do not write a long sentence.

Return 3 to 5 simple English keywords.

Examples:

Snow White story:
enchanted forest fairy tale

Space adventure:
astronaut space spaceship

Ocean adventure:
ocean sailing boat waves

Dragon story:
dragon castle fantasy

The query must describe visual footage
that could actually exist as stock video.

Return ONLY the search keywords.
"""

    try:

        response = gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        if response and response.text:

            query = response.text.strip()

            # Remove accidental formatting
            query = query.replace(
                "\n",
                " "
            )

            return query[:100]

    except Exception:

        pass

    return title


# ============================================================
# 11. PIXABAY VIDEO SEARCH
# ============================================================

def get_pixabay_video(title, story):

    if "PIXABAY_API_KEY" not in st.secrets:

        return None, "PIXABAY_API_KEY is missing."

    api_key = str(
        st.secrets["PIXABAY_API_KEY"]
    ).strip()

    if not api_key:

        return None, "PIXABAY_API_KEY is empty."

    search_query = create_video_search_query(
        title,
        story
    )

    url = "https://pixabay.com/api/videos/"

    params = {
        "key": api_key,
        "q": search_query,
        "video_type": "film",
        "per_page": 10,
        "safesearch": "true"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        if response.status_code != 200:

            return None, (
                f"Pixabay returned HTTP "
                f"{response.status_code}"
            )

        data = response.json()

        hits = data.get(
            "hits",
            []
        )

        if not hits:

            return None, (
                f"No relevant Pixabay video found "
                f"for: {search_query}"
            )

        # Try to find the largest useful video
        for hit in hits:

            videos = hit.get(
                "videos",
                {}
            )

            for quality in [
                "large",
                "medium",
                "small"
            ]:

                if quality in videos:

                    video_url = videos[
                        quality
                    ].get("url")

                    if video_url:

                        return (
                            video_url,
                            search_query
                        )

    except Exception as e:

        return None, str(e)

    return None, "No usable video found."


# ============================================================
# 12. AUDIO GENERATION
# ============================================================

def generate_audio_narration(text):

    try:

        tts = gTTS(
            text=text,
            lang="en"
        )

        audio_buffer = io.BytesIO()

        tts.write_to_fp(
            audio_buffer
        )

        audio_buffer.seek(0)

        return audio_buffer

    except Exception as e:

        st.error(
            f"Audio generation failed: {e}"
        )

        return None


# ============================================================
# 13. SESSION STATE
# ============================================================

if "current_story" not in st.session_state:
    st.session_state.current_story = ""

if "last_title" not in st.session_state:
    st.session_state.last_title = ""

if "last_limit" not in st.session_state:
    st.session_state.last_limit = 0

if "visual_prompt" not in st.session_state:
    st.session_state.visual_prompt = ""

if "generated_image" not in st.session_state:
    st.session_state.generated_image = None

if "video_url" not in st.session_state:
    st.session_state.video_url = None

if "video_query" not in st.session_state:
    st.session_state.video_query = ""


# ============================================================
# 14. GENERATE STORY
# ============================================================

if story_title:

    if (
        st.session_state.last_title != story_title
        or
        st.session_state.last_limit != word_limit
    ):

        with st.spinner(
            "🧠 Gemini is writing your story..."
        ):

            story_text = generate_gemini_story(
                story_title,
                word_limit
            )

        if story_text:

            st.session_state.current_story = story_text

            st.session_state.last_title = (
                story_title
            )

            st.session_state.last_limit = (
                word_limit
            )

            # Reset media when story changes
            st.session_state.visual_prompt = ""
            st.session_state.generated_image = None
            st.session_state.video_url = None
            st.session_state.video_query = ""


# ============================================================
# 15. DISPLAY STORY
# ============================================================

if st.session_state.current_story:

    story_text = st.session_state.current_story

    st.subheader(
        f"📖 {story_title}"
    )

    actual_words = len(
        story_text.split()
    )

    st.markdown(
        f"""
        <div class="story-card">
        {story_text}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption(
        f"📊 {actual_words} words "
        f"(Target: {word_limit})"
    )


    # ========================================================
    # MEDIA STUDIO
    # ========================================================

    st.write("---")

    st.header("🎬 Visual & Media Studio")


    # ========================================================
    # VISUAL PROMPT
    # ========================================================

    if st.button(
        "🧠 Create Story Scene",
        use_container_width=True
    ):

        with st.spinner(
            "🎨 Understanding your story and designing the scene..."
        ):

            visual_prompt = create_visual_prompt(
                story_title,
                story_text
            )

            visual_prompt = improve_visual_prompt_with_groq(
                story_title,
                visual_prompt
            )

            st.session_state.visual_prompt = (
                visual_prompt
            )

    if st.session_state.visual_prompt:

        with st.expander(
            "🔍 View AI Visual Prompt"
        ):

            st.write(
                st.session_state.visual_prompt
            )


    # ========================================================
    # IMAGE + VIDEO BUTTONS
    # ========================================================

    col1, col2 = st.columns(2)


    # ========================================================
    # AI IMAGE
    # ========================================================

    with col1:

        if st.button(
            "🖼️ Generate AI Story Image",
            use_container_width=True
        ):

            # Automatically create prompt if needed
            if not st.session_state.visual_prompt:

                with st.spinner(
                    "🧠 Creating a scene from your story..."
                ):

                    visual_prompt = create_visual_prompt(
                        story_title,
                        story_text
                    )

                    visual_prompt = (
                        improve_visual_prompt_with_groq(
                            story_title,
                            visual_prompt
                        )
                    )

                    st.session_state.visual_prompt = (
                        visual_prompt
                    )

            with st.spinner(
                "🎨 Gemini is generating the actual story artwork..."
            ):

                image_bytes = generate_ai_image(
                    st.session_state.visual_prompt
                )

            if image_bytes:

                st.session_state.generated_image = (
                    image_bytes
                )

                st.success(
                    "✅ Story-matching artwork generated!"
                )


    # ========================================================
    # PIXABAY VIDEO
    # ========================================================

    with col2:

        if st.button(
            "🎥 Find Matching Story Video",
            use_container_width=True
        ):

            with st.spinner(
                "🔎 Searching Pixabay for a relevant scene..."
            ):

                video_url, video_info = (
                    get_pixabay_video(
                        story_title,
                        story_text
                    )
                )

            if video_url:

                st.session_state.video_url = (
                    video_url
                )

                st.session_state.video_query = (
                    video_info
                )

                st.success(
                    f"✅ Found footage for: "
                    f"{video_info}"
                )

            else:

                st.session_state.video_url = None

                st.warning(
                    f"🎬 No sufficiently relevant video "
                    f"was found.\n\n{video_info}"
                )


    # ========================================================
    # DISPLAY IMAGE
    # ========================================================

    if st.session_state.generated_image:

        st.write("### 🖼️ Story Artwork")

        st.image(
            st.session_state.generated_image,
            caption=f"AI artwork — {story_title}",
            use_container_width=True
        )


    # ========================================================
    # DISPLAY VIDEO
    # ========================================================

    if st.session_state.video_url:

        st.write("### 🎥 Matching Video")

        if st.session_state.video_query:

            st.caption(
                "Pixabay search: "
                + st.session_state.video_query
            )

        st.video(
            st.session_state.video_url
        )


    # ========================================================
    # AUDIO
    # ========================================================

    st.write("---")

    st.write("### 🔊 Narration")

    if st.button(
        "🔊 Read Story Aloud",
        use_container_width=True
    ):

        with st.spinner(
            "🎙️ Generating narration..."
        ):

            audio = generate_audio_narration(
                story_text
            )

        if audio:

            st.audio(
                audio,
                format="audio/mp3"
            )


# ============================================================
# 16. SIDEBAR API STATUS
# ============================================================

st.sidebar.write("---")

st.sidebar.subheader("🔌 API Status")

if gemini_client:

    st.sidebar.success(
        "🟢 Gemini connected"
    )

else:

    st.sidebar.error(
        "🔴 Gemini not connected"
    )


if groq_client:

    st.sidebar.success(
        "🟢 Groq connected"
    )

else:

    st.sidebar.info(
        "⚪ Groq not connected"
    )


if "PIXABAY_API_KEY" in st.secrets:

    st.sidebar.success(
        "🟢 Pixabay configured"
    )

else:

    st.sidebar.warning(
        "🟡 Pixabay not configured"
    )
