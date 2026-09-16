import io
import urllib.parse
import base64

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
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Story, Photo & Video Studio",
    page_icon="🎨",
    layout="wide"
)


# ============================================================
# API CLIENTS
# ============================================================

gemini_client = None
groq_client = None

gemini_error = None
groq_error = None


# ---------------- GEMINI ----------------

try:

    if "GEMINI_API_KEY" in st.secrets:

        gemini_key = str(
            st.secrets["GEMINI_API_KEY"]
        ).strip()

        if gemini_key:

            gemini_client = genai.Client(
                api_key=gemini_key
            )

        else:

            gemini_error = (
                "GEMINI_API_KEY is empty."
            )

    else:

        gemini_error = (
            "GEMINI_API_KEY is missing."
        )

except Exception as e:

    gemini_error = str(e)


# ---------------- GROQ ----------------

if GROQ_AVAILABLE:

    try:

        if "GROQ_API_KEY" in st.secrets:

            groq_key = str(
                st.secrets["GROQ_API_KEY"]
            ).strip()

            if groq_key:

                groq_client = Groq(
                    api_key=groq_key
                )

    except Exception as e:

        groq_error = str(e)


# ============================================================
# CUSTOM STYLING
# ============================================================

st.sidebar.title("⚙️ Custom Styling")

bg_color = st.sidebar.color_picker(
    "App Background",
    "#F0F2F6"
)

text_color = st.sidebar.color_picker(
    "Text Color",
    "#1F1F1F"
)

card_color = st.sidebar.color_picker(
    "Card Background",
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
        margin-bottom: 20px;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.title("✨ AI Story, Photo & Video Studio")

st.write(
    "Create a story with matching AI artwork, "
    "narration and relevant video."
)


# ============================================================
# INPUT
# ============================================================

col1, col2 = st.columns([2, 1])

with col1:

    story_title = st.text_input(
        "📖 Story Title",
        placeholder="Snow White and the Seven Dwarfs"
    )

with col2:

    word_limit = st.slider(
        "📏 Word Limit",
        min_value=50,
        max_value=1000,
        value=300,
        step=25
    )


# ============================================================
# SESSION STATE
# ============================================================

defaults = {

    "current_story": "",

    "last_title": "",

    "last_limit": 0,

    "visual_prompt": "",

    "generated_image": None,

    "video_url": None,

    "video_query": "",

    "audio": None
}

for key, value in defaults.items():

    if key not in st.session_state:

        st.session_state[key] = value


# ============================================================
# GEMINI TEXT GENERATION
# ============================================================

def gemini_text(prompt):

    if not gemini_client:

        st.error(
            f"Gemini is not configured:\n\n{gemini_error}"
        )

        return None

    try:

        # Lite model
        response = gemini_client.models.generate_content(

            model="gemini-3.1-flash-lite",

            contents=prompt
        )

        if response and response.text:

            return response.text.strip()

        return None

    except Exception as e:

        st.error(
            f"Gemini error:\n\n{e}"
        )

        return None


# ============================================================
# STORY GENERATION
# ============================================================

def generate_story(title, limit):

    prompt = f"""
Write an original, engaging story titled:

"{title}"

Requirements:

- Stay strongly focused on the title.
- Use specific characters.
- Use a clear setting.
- Include meaningful actions.
- Include a problem or conflict.
- Include a satisfying ending.
- Make the story easy to visualize.
- Avoid generic filler.
- Target approximately {limit} words.
- Return ONLY the story.

Write the story now.
"""

    return gemini_text(prompt)


# ============================================================
# VISUAL PROMPT GENERATION
# ============================================================

def create_visual_prompt(title, story):

    prompt = f"""
You are a professional cinematic storyboard artist.

STORY TITLE:
{title}

STORY:
{story}

Create ONE detailed prompt for an AI image generator.

The image MUST show an actual important moment
from the story.

Do NOT create a generic landscape.

The prompt must describe:

- Main characters
- Character appearance
- Character actions
- Location
- Important objects
- Time of day
- Lighting
- Camera angle
- Mood
- Cinematic composition
- Art style

The characters and their actions must be
the main focus.

Do not add text.

Return ONLY the image prompt.
"""

    return gemini_text(prompt)


# ============================================================
# GROQ PROMPT ENHANCEMENT
# ============================================================

def improve_prompt_with_groq(title, prompt):

    if not groq_client:

        return prompt

    try:

        result = groq_client.chat.completions.create(

            model="llama-3.3-70b-versatile",

            messages=[

                {
                    "role": "system",
                    "content": """
You are an expert AI image prompt engineer.

Improve the provided prompt.

Keep the original story.

Make the characters, actions,
environment and composition extremely clear.

Never turn the scene into a generic landscape.

Return ONLY the improved image prompt.
"""
                },

                {
                    "role": "user",
                    "content": f"""
Story:
{title}

Image prompt:
{prompt}
"""
                }

            ],

            temperature=0.3,

            max_tokens=500
        )

        output = (
            result
            .choices[0]
            .message
            .content
        )

        if output:

            return output.strip()

    except Exception:

        pass

    return prompt


# ============================================================
# GEMINI IMAGE GENERATION
# ============================================================

def generate_ai_image(prompt):

    if not gemini_client:

        return None

    try:

        # Native Gemini image model
        response = gemini_client.models.generate_content(

            model="gemini-3.1-flash-lite-image",

            contents=prompt
        )

        if not response:

            return None

        # Gemini returns image parts
        if hasattr(response, "candidates"):

            for candidate in response.candidates:

                if not candidate.content:

                    continue

                for part in candidate.content.parts:

                    if hasattr(part, "inline_data"):

                        if part.inline_data:

                            return (
                                part.inline_data.data
                            )

    except Exception as e:

        st.error(
            f"Image generation failed:\n\n{e}"
        )

    return None


# ============================================================
# PIXABAY QUERY GENERATION
# ============================================================

def create_pixabay_query(title, story):

    prompt = f"""
You are selecting stock footage.

Story title:
{title}

Story:
{story}

Create a short Pixabay search query.

The query must contain only 3-5
visual keywords.

Examples:

Snow White:
enchanted forest fairy tale

Space story:
astronaut spaceship space

Ocean story:
ocean sailing boat

Dragon story:
dragon castle fantasy

Do NOT return a sentence.

Return ONLY the keywords.
"""

    query = gemini_text(prompt)

    if query:

        query = query.replace(
            "\n",
            " "
        ).strip()

        return query[:100]

    return title


# ============================================================
# PIXABAY VIDEO
# ============================================================

def get_pixabay_video(title, story):

    if "PIXABAY_API_KEY" not in st.secrets:

        return None, "PIXABAY_API_KEY is missing."

    api_key = str(
        st.secrets["PIXABAY_API_KEY"]
    ).strip()

    if not api_key:

        return None, "PIXABAY_API_KEY is empty."

    query = create_pixabay_query(
        title,
        story
    )

    url = "https://pixabay.com/api/videos/"

    params = {

        "key": api_key,

        "q": query,

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

            return (
                None,
                f"Pixabay HTTP {response.status_code}"
            )

        data = response.json()

        hits = data.get(
            "hits",
            []
        )

        if not hits:

            return (
                None,
                f"No matching video found for: {query}"
            )

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
                            query
                        )

        return (
            None,
            "No usable video found."
        )

    except Exception as e:

        return None, str(e)


# ============================================================
# AUDIO
# ============================================================

def generate_audio(text):

    try:

        tts = gTTS(
            text=text,
            lang="en"
        )

        buffer = io.BytesIO()

        tts.write_to_fp(
            buffer
        )

        buffer.seek(0)

        return buffer

    except Exception as e:

        st.error(
            f"Audio error: {e}"
        )

        return None


# ============================================================
# GENERATE STORY BUTTON
# ============================================================

if story_title:

    if st.button(
        "✨ Generate Story",
        type="primary",
        use_container_width=True
    ):

        # Clear previous content
        st.session_state.current_story = ""
        st.session_state.visual_prompt = ""
        st.session_state.generated_image = None
        st.session_state.video_url = None
        st.session_state.video_query = ""
        st.session_state.audio = None

        with st.spinner(
            "🧠 Writing your story..."
        ):

            story = generate_story(
                story_title,
                word_limit
            )

        if story:

            st.session_state.current_story = story

            st.session_state.last_title = story_title

            st.session_state.last_limit = word_limit

            st.success(
                "✅ Story generated!"
            )


# ============================================================
# DISPLAY STORY
# ============================================================

if st.session_state.current_story:

    story = st.session_state.current_story

    st.subheader(
        f"📖 {story_title}"
    )

    actual_words = len(
        story.split()
    )

    st.markdown(
        f"""
        <div class="story-card">
        {story}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption(
        f"📊 {actual_words} words "
        f"(target: {word_limit})"
    )


    # ========================================================
    # MEDIA STUDIO
    # ========================================================

    st.write("---")

    st.header(
        "🎬 Visual & Media Studio"
    )


    # ========================================================
    # CREATE SCENE
    # ========================================================

    if st.button(
        "🧠 Create Visual Scene",
        use_container_width=True
    ):

        with st.spinner(
            "🎨 Creating a scene from your story..."
        ):

            prompt = create_visual_prompt(
                story_title,
                story
            )

        if prompt:

            with st.spinner(
                "✨ Improving visual details..."
            ):

                prompt = improve_prompt_with_groq(
                    story_title,
                    prompt
                )

            st.session_state.visual_prompt = prompt

            st.success(
                "Scene prompt created!"
            )


    if st.session_state.visual_prompt:

        with st.expander(
            "🔍 View Visual Prompt"
        ):

            st.write(
                st.session_state.visual_prompt
            )


    # ========================================================
    # MEDIA BUTTONS
    # ========================================================

    image_col, video_col = st.columns(2)


    # ========================================================
    # IMAGE
    # ========================================================

    with image_col:

        if st.button(
            "🖼️ Generate AI Picture",
            use_container_width=True
        ):

            if not st.session_state.visual_prompt:

                with st.spinner(
                    "🧠 Creating visual scene..."
                ):

                    prompt = create_visual_prompt(
                        story_title,
                        story
                    )

                    prompt = improve_prompt_with_groq(
                        story_title,
                        prompt
                    )

                    st.session_state.visual_prompt = prompt

            with st.spinner(
                "🎨 Generating story artwork..."
            ):

                image = generate_ai_image(
                    st.session_state.visual_prompt
                )

            if image:

                st.session_state.generated_image = image

                st.success(
                    "✅ AI artwork generated!"
                )


    # ========================================================
    # VIDEO
    # ========================================================

    with video_col:

        if st.button(
            "🎥 Find Matching Video",
            use_container_width=True
        ):

            with st.spinner(
                "🔎 Searching Pixabay..."
            ):

                video, query = get_pixabay_video(
                    story_title,
                    story
                )

            if video:

                st.session_state.video_url = video

                st.session_state.video_query = query

                st.success(
                    f"Found footage for: {query}"
                )

            else:

                st.session_state.video_url = None

                st.warning(
                    query
                )


    # ========================================================
    # SHOW IMAGE
    # ========================================================

    if st.session_state.generated_image:

        st.write(
            "### 🖼️ Story Artwork"
        )

        st.image(
            st.session_state.generated_image,
            caption=story_title,
            use_container_width=True
        )


    # ========================================================
    # SHOW VIDEO
    # ========================================================

    if st.session_state.video_url:

        st.write(
            "### 🎥 Matching Video"
        )

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

    st.subheader(
        "🔊 Story Narration"
    )

    if st.button(
        "🔊 Generate Narration",
        use_container_width=True
    ):

        with st.spinner(
            "🎙️ Creating narration..."
        ):

            audio = generate_audio(
                story
            )

        if audio:

            st.session_state.audio = audio

    if st.session_state.audio:

        st.audio(
            st.session_state.audio,
            format="audio/mp3"
        )


# ============================================================
# SIDEBAR STATUS
# ============================================================

st.sidebar.write("---")

st.sidebar.subheader(
    "🔌 API Status"
)

if gemini_client:

    st.sidebar.success(
        "🟢 Gemini connected"
    )

else:

    st.sidebar.error(
        "🔴 Gemini unavailable"
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
        "🟢 Pixabay connected"
    )

else:

    st.sidebar.warning(
        "🟡 Pixabay not configured"
    )
