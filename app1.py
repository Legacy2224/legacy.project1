import streamlit as st
import requests
import html
from gtts import gTTS
from io import BytesIO
from google import genai
from groq import Groq


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Free AI Story, Photo & Video Studio",
    page_icon="🎬",
    layout="wide"
)


# ============================================================
# API CLIENTS
# ============================================================

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
PIXABAY_API_KEY = st.secrets.get("PIXABAY_API_KEY", "")
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

gemini_client = None
groq_client = None

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🎬 AI Story Studio")

    st.markdown(
        """
        Create a complete story experience:

        ✍️ AI Story  
        🖼️ Matching Photo  
        🎥 Matching Video  
        🔊 Narration
        """
    )

    st.divider()

    st.subheader("⚙️ Settings")

    word_limit = st.slider(
        "Story length",
        min_value=100,
        max_value=1500,
        value=500,
        step=50
    )

    language = st.selectbox(
        "Narration language",
        [
            ("English", "en"),
            ("Hindi", "hi"),
            ("Spanish", "es"),
            ("French", "fr"),
            ("German", "de")
        ],
        format_func=lambda x: x[0]
    )

    st.divider()

    st.caption("Media is provided by Pixabay.")
    st.caption("Story generation uses Gemini Flash Lite.")


# ============================================================
# SESSION STATE
# ============================================================

if "story" not in st.session_state:
    st.session_state.story = ""

if "story_title" not in st.session_state:
    st.session_state.story_title = ""

if "image_url" not in st.session_state:
    st.session_state.image_url = None

if "video_url" not in st.session_state:
    st.session_state.video_url = None

if "audio_bytes" not in st.session_state:
    st.session_state.audio_bytes = None

if "media_queries" not in st.session_state:
    st.session_state.media_queries = []


# ============================================================
# GEMINI TEXT GENERATION
# ============================================================

def gemini_text(prompt):

    if not gemini_client:
        raise Exception("GEMINI_API_KEY is missing.")

    response = gemini_client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    if not response.text:
        raise Exception("Gemini returned an empty response.")

    return response.text.strip()


# ============================================================
# GROQ FALLBACK
# ============================================================

def groq_text(prompt):

    if not groq_client:
        raise Exception("GROQ_API_KEY is missing.")

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.8,
        max_tokens=2500
    )

    return response.choices[0].message.content.strip()


# ============================================================
# STORY GENERATION
# ============================================================

def generate_story(title, word_limit):

    prompt = f"""
Write an engaging original story titled:

"{title}"

Requirements:

- Approximately {word_limit} words
- Strong beginning, middle and ending
- Clear characters
- Vivid visual descriptions
- Suitable for a general audience
- Natural storytelling
- Do not explain your writing process
- Return only the story

The story should contain enough visual detail that photographs or
stock video can later be selected to represent important scenes.
"""

    # Try Gemini first
    try:
        return gemini_text(prompt), "Gemini"
    except Exception as gemini_error:

        # Groq fallback
        if groq_client:
            try:
                return groq_text(prompt), "Groq"
            except Exception:
                pass

        raise gemini_error


# ============================================================
# CREATE PIXABAY SEARCH QUERIES
# ============================================================

def create_media_queries(title, story):

    prompt = f"""
You are selecting stock media for a story.

Story title:
{title}

Story:
{story[:6000]}

Create 5 short Pixabay search queries that visually represent
the most important scenes in this story.

Rules:
- 2 to 5 words per query
- Use concrete visual nouns
- Include location, characters, objects or atmosphere
- Avoid full sentences
- Avoid abstract concepts
- Do not use quotation marks
- Do not number the queries

Example:

enchanted forest cottage
young princess woodland
magical forest sunrise
fairy tale castle
misty woodland path
"""

    try:
        result = gemini_text(prompt)

        queries = []

        for line in result.splitlines():

            line = line.strip()

            if not line:
                continue

            # Remove bullets/numbers
            line = line.lstrip("-•*0123456789. ")

            if line:
                queries.append(line)

        return queries[:5]

    except Exception:

        # Simple fallback based on title
        cleaned_title = title.strip()

        return [
            cleaned_title,
            f"{cleaned_title} fantasy",
            f"{cleaned_title} forest",
            f"{cleaned_title} story",
        ]


# ============================================================
# PIXABAY IMAGE SEARCH
# ============================================================

def search_pixabay_image(queries):

    if not PIXABAY_API_KEY:
        return None

    endpoint = "https://pixabay.com/api/"

    for query in queries:

        try:

            params = {
                "key": PIXABAY_API_KEY,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "safesearch": "true",
                "per_page": 10
            }

            response = requests.get(
                endpoint,
                params=params,
                timeout=15
            )

            response.raise_for_status()

            data = response.json()

            hits = data.get("hits", [])

            if hits:

                # Prefer large image
                for hit in hits:

                    url = (
                        hit.get("largeImageURL")
                        or hit.get("webformatURL")
                    )

                    if url:
                        return url

        except Exception:
            continue

    return None


# ============================================================
# PIXABAY VIDEO SEARCH
# ============================================================

def search_pixabay_video(queries):

    if not PIXABAY_API_KEY:
        return None

    endpoint = "https://pixabay.com/api/videos/"

    for query in queries:

        try:

            params = {
                "key": PIXABAY_API_KEY,
                "q": query,
                "video_type": "film",
                "safesearch": "true",
                "per_page": 10
            }

            response = requests.get(
                endpoint,
                params=params,
                timeout=15
            )

            response.raise_for_status()

            data = response.json()

            hits = data.get("hits", [])

            if hits:

                for hit in hits:

                    videos = hit.get("videos", {})

                    # Prefer larger video
                    for quality in ["large", "medium", "small", "tiny"]:

                        if quality in videos:

                            url = videos[quality].get("url")

                            if url:
                                return url

        except Exception:
            continue

    return None


# ============================================================
# NARRATION
# ============================================================

def generate_audio(text, language_code):

    audio = BytesIO()

    tts = gTTS(
        text=text,
        lang=language_code,
        slow=False
    )

    tts.write_to_fp(audio)

    audio.seek(0)

    return audio.read()


# ============================================================
# HEADER
# ============================================================

st.title("🎬 Free AI Story, Photo & Video Studio")

st.markdown(
    "Create a story, find matching visuals, and turn it into narration."
)

st.divider()


# ============================================================
# STORY INPUT
# ============================================================

title = st.text_input(
    "📖 Story title",
    placeholder="Example: Snow White and the Seven Dwarfs"
)


# ============================================================
# GENERATE STORY
# ============================================================

if st.button(
    "✨ Generate Story",
    type="primary",
    use_container_width=True
):

    if not title.strip():

        st.warning("Please enter a story title.")

    else:

        with st.spinner("✍️ Writing your story..."):

            try:

                story, provider = generate_story(
                    title,
                    word_limit
                )

                st.session_state.story = story
                st.session_state.story_title = title

                # Clear old media
                st.session_state.image_url = None
                st.session_state.video_url = None
                st.session_state.audio_bytes = None
                st.session_state.media_queries = []

                st.success(
                    f"Story generated using {provider}."
                )

            except Exception as e:

                st.error(
                    f"Story generation failed:\n\n{e}"
                )


# ============================================================
# DISPLAY STORY
# ============================================================

if st.session_state.story:

    st.divider()

    st.subheader(
        f"📖 {st.session_state.story_title}"
    )

    # Escape HTML so story text cannot accidentally
    # break the page layout.
    safe_story = html.escape(
        st.session_state.story
    )

    st.markdown(
        f"""
        <div style="
            padding: 25px;
            border-radius: 15px;
            background: rgba(128,128,128,0.10);
            line-height: 1.8;
            font-size: 17px;
        ">
        {safe_story.replace(chr(10), '<br>')}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    # ========================================================
    # MEDIA BUTTONS
    # ========================================================

    col1, col2, col3 = st.columns(3)

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    with col1:

        if st.button(
            "🖼️ Find Matching Photo",
            use_container_width=True
        ):

            with st.spinner("🔎 Finding matching photo..."):

                try:

                    queries = create_media_queries(
                        st.session_state.story_title,
                        st.session_state.story
                    )

                    st.session_state.media_queries = queries

                    image_url = search_pixabay_image(
                        queries
                    )

                    if image_url:

                        st.session_state.image_url = image_url

                        st.success("Matching photo found!")

                    else:

                        st.warning(
                            "Pixabay could not find a suitable photo."
                        )

                except Exception as e:

                    st.error(
                        f"Photo search failed: {e}"
                    )

    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------

    with col2:

        if st.button(
            "🎥 Find Matching Video",
            use_container_width=True
        ):

            with st.spinner("🔎 Finding matching video..."):

                try:

                    # Reuse queries if they already exist
                    if not st.session_state.media_queries:

                        queries = create_media_queries(
                            st.session_state.story_title,
                            st.session_state.story
                        )

                        st.session_state.media_queries = queries

                    video_url = search_pixabay_video(
                        st.session_state.media_queries
                    )

                    if video_url:

                        st.session_state.video_url = video_url

                        st.success("Matching video found!")

                    else:

                        st.warning(
                            "Pixabay could not find a suitable video."
                        )

                except Exception as e:

                    st.error(
                        f"Video search failed: {e}"
                    )

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    with col3:

        if st.button(
            "🔊 Generate Narration",
            use_container_width=True
        ):

            with st.spinner("🎙️ Creating narration..."):

                try:

                    audio = generate_audio(
                        st.session_state.story,
                        language[1]
                    )

                    st.session_state.audio_bytes = audio

                    st.success("Narration ready!")

                except Exception as e:

                    st.error(
                        f"Audio generation failed: {e}"
                    )


# ============================================================
# IMAGE DISPLAY
# ============================================================

if st.session_state.image_url:

    st.divider()

    st.subheader("🖼️ Story Photo")

    st.image(
        st.session_state.image_url,
        use_container_width=True
    )


# ============================================================
# VIDEO DISPLAY
# ============================================================

if st.session_state.video_url:

    st.divider()

    st.subheader("🎥 Story Video")

    st.video(
        st.session_state.video_url
    )


# ============================================================
# AUDIO DISPLAY
# ============================================================

if st.session_state.audio_bytes:

    st.divider()

    st.subheader("🔊 Story Narration")

    st.audio(
        st.session_state.audio_bytes,
        format="audio/mp3"
    )

    st.download_button(
        "⬇️ Download Narration",
        data=st.session_state.audio_bytes,
        file_name="story_narration.mp3",
        mime="audio/mp3"
    )


# ============================================================
# DEBUG / SEARCH TERMS
# ============================================================

if st.session_state.media_queries:

    with st.expander("🔎 Visual search terms"):

        st.write(
            st.session_state.media_queries
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "AI Story • Pixabay Photo • Pixabay Video • gTTS Narration"
)
