import streamlit as st
import requests
import html
import json
import re
import os
import tempfile
import subprocess
import shutil
import time
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from gtts import gTTS
from groq import Groq

# Gemini import
try:
    from google import genai
except ImportError:
    genai = None

# FFmpeg import is OPTIONAL so the app does not crash on startup
try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Story & Cinematic Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "story": "",
    "story_title": "",
    "provider": "",
    "scenes": [],
    "scene_images": [],
    "scene_videos": [],
    "scene_audio": [],
    "poster_bytes": None,
    "video_bytes": None,
    "narrated_video_bytes": None,
    "audio_bytes": None,
    "project_generated": False,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# SECRETS
# ============================================================

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
PIXABAY_API_KEY = st.secrets.get("PIXABAY_API_KEY", "")


# ============================================================
# API CLIENTS
# ============================================================

gemini_client = None
groq_client = None


if GEMINI_API_KEY and genai:

    try:
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )
    except Exception:
        gemini_client = None


if GROQ_API_KEY:

    try:
        groq_client = Groq(
            api_key=GROQ_API_KEY
        )
    except Exception:
        groq_client = None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="
            text-align:center;
            padding:10px 0 20px 0;
        ">
            <div style="font-size:50px;">🎬</div>

            <h2 style="margin:0;">
                AI Story Studio
            </h2>

            <p style="opacity:0.7;">
                Story → Scenes → Images → Video → Voice
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    # ========================================================
    # THEME
    # ========================================================

    st.subheader("🎨 Theme")

    theme_choice = st.selectbox(
        "Choose colour theme",
        [
            "Dark Midnight",
            "Light Elegant",
            "Cyberpunk Neon",
            "Enchanted Forest",
            "Sunset Glow"
        ]
    )

    THEMES = {

        "Dark Midnight": {
            "background": "#0E1117",
            "card": "#1E232A",
            "text": "#FFFFFF",
            "primary": "#4A90E2",
            "accent": "#22C55E"
        },

        "Light Elegant": {
            "background": "#F8F9FA",
            "card": "#FFFFFF",
            "text": "#212529",
            "primary": "#0D6EFD",
            "accent": "#198754"
        },

        "Cyberpunk Neon": {
            "background": "#050505",
            "card": "#120024",
            "text": "#00FFCC",
            "primary": "#FF007F",
            "accent": "#00FFFF"
        },

        "Enchanted Forest": {
            "background": "#0B1D13",
            "card": "#132A1C",
            "text": "#E0F2FE",
            "primary": "#22C55E",
            "accent": "#A3E635"
        },

        "Sunset Glow": {
            "background": "#1A0B1C",
            "card": "#2D1236",
            "text": "#FDF2F8",
            "primary": "#F43F5E",
            "accent": "#FB923C"
        }
    }

    theme = THEMES[theme_choice]

    st.divider()

    # ========================================================
    # STORY SETTINGS
    # ========================================================

    st.subheader("⚙️ Story Settings")

    word_limit = st.slider(
        "Story length",
        150,
        2000,
        700,
        50
    )

    scene_count = st.slider(
        "Number of scenes",
        4,
        10,
        6
    )

    clip_duration = st.slider(
        "Video seconds / scene",
        3,
        10,
        5
    )

    narration_language = st.selectbox(
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

    # ========================================================
    # API STATUS
    # ========================================================

    st.subheader("🔑 API Status")

    if GEMINI_API_KEY:
        st.success("Gemini ✓")
    else:
        st.warning("Gemini missing")

    if GROQ_API_KEY:
        st.success("Groq ✓")
    else:
        st.info("Groq fallback unavailable")

    if PIXABAY_API_KEY:
        st.success("Pixabay ✓")
    else:
        st.warning("Pixabay missing")

    if imageio_ffmpeg:
        st.success("FFmpeg ✓")
    else:
        st.warning(
            "FFmpeg package unavailable"
        )


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    f"""
    <style>

    .stApp {{
        background-color: {theme["background"]};
        color: {theme["text"]};
    }}

    section[data-testid="stSidebar"] {{
        background-color: {theme["card"]};
    }}

    .main-title {{
        font-size: 44px;
        font-weight: 800;
        margin-bottom: 5px;
    }}

    .subtitle {{
        font-size: 17px;
        opacity: 0.7;
        margin-bottom: 25px;
    }}

    .story-card {{
        background-color: {theme["card"]};
        padding: 28px;
        border-radius: 18px;
        border-left: 5px solid {theme["primary"]};
        line-height: 1.8;
        margin: 20px 0;
    }}

    .scene-card {{
        background-color: {theme["card"]};
        padding: 22px;
        border-radius: 16px;
        border-left: 5px solid {theme["primary"]};
        margin-bottom: 20px;
    }}

    .feature-card {{
        background-color: {theme["card"]};
        padding: 20px;
        border-radius: 16px;
        text-align: center;
    }}

    div.stButton > button {{
        border-radius: 12px;
        font-weight: 600;
        min-height: 45px;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🎬 AI Story, Photo & Cinematic Video Studio</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Create a story, intelligently divide it into cinematic scenes, '
    'find relevant visuals, generate narration and assemble a movie.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# AI TEXT - GEMINI
# ============================================================

def gemini_generate(prompt):

    if not gemini_client:

        raise RuntimeError(
            "Gemini is not configured."
        )

    response = gemini_client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    if not response:

        raise RuntimeError(
            "Gemini returned no response."
        )

    text = getattr(
        response,
        "text",
        None
    )

    if not text:

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return text.strip()


# ============================================================
# AI TEXT - GROQ
# ============================================================

def groq_generate(prompt):

    if not groq_client:

        raise RuntimeError(
            "Groq is not configured."
        )

    response = groq_client.chat.completions.create(

        model="llama-3.3-70b-versatile",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.8,

        max_tokens=7000
    )

    if not response.choices:

        raise RuntimeError(
            "Groq returned no response."
        )

    return response.choices[0].message.content.strip()


# ============================================================
# AI TEXT WITH FALLBACK
# ============================================================

def ai_generate(prompt):

    errors = []

    if gemini_client:

        try:

            return (
                gemini_generate(prompt),
                "Gemini"
            )

        except Exception as e:

            errors.append(
                f"Gemini: {e}"
            )

    if groq_client:

        try:

            return (
                groq_generate(prompt),
                "Groq"
            )

        except Exception as e:

            errors.append(
                f"Groq: {e}"
            )

    raise RuntimeError(
        "\n\n".join(errors)
        if errors
        else
        "No AI provider is configured."
    )


# ============================================================
# STORY GENERATION
# ============================================================

def generate_story(title, words):

    prompt = f"""
You are a professional cinematic storyteller.

Write an ORIGINAL story based on:

TITLE:
{title}

TARGET LENGTH:
approximately {words} words.

The story must be highly visual and suitable for conversion
into a cinematic multi-scene movie.

Include:

- A memorable protagonist
- Supporting characters
- Specific locations
- Important objects
- Character actions
- A clear conflict
- Escalation
- A climax
- A satisfying ending
- Strong visual details
- Lighting
- Weather
- Atmosphere
- Creatures or magical elements when appropriate

Avoid vague abstract writing.

Make important events visually filmable.

Do not explain the process.

Return ONLY the story.
"""

    return ai_generate(prompt)


# ============================================================
# SCENE PLANNING
# ============================================================

def create_scene_plan(
    title,
    story,
    number_of_scenes
):

    prompt = f"""
You are a professional movie director,
storyboard artist and cinematographer.

Turn the COMPLETE story below into EXACTLY
{number_of_scenes} cinematic scenes.

TITLE:
{title}

STORY:
{story}

IMPORTANT:

Do NOT simply split the story by sentences.

Instead identify the important visual events.

The scenes must cover the entire story,
including the ending.

Maintain character continuity.

For every scene create:

1. Scene number
2. Scene title
3. Detailed description
4. Characters
5. Location
6. Important objects
7. Character actions
8. Lighting
9. Image search query
10. Video search query
11. Narration

IMAGE QUERY:

Must describe visible things.

VIDEO QUERY:

Must describe visible movement/action.

Do not use abstract concepts.

BAD:
"magical hope and emotional transformation"

GOOD:
"young woman standing beside glowing ancient doorway in forest"

Return EXACTLY this format:

SCENE|1|TITLE|DESCRIPTION|CHARACTERS|LOCATION|OBJECTS|ACTION|LIGHTING|IMAGE_QUERY|VIDEO_QUERY|NARRATION

SCENE|2|TITLE|DESCRIPTION|CHARACTERS|LOCATION|OBJECTS|ACTION|LIGHTING|IMAGE_QUERY|VIDEO_QUERY|NARRATION

Do not use the | symbol inside fields.
"""

    result, _ = ai_generate(prompt)

    scenes = []

    for line in result.splitlines():

        line = line.strip()

        if not line.startswith("SCENE|"):
            continue

        parts = line.split("|")

        if len(parts) < 12:
            continue

        try:

            number = int(
                parts[1].strip()
            )

        except Exception:

            number = len(scenes) + 1

        scenes.append({

            "number": number,

            "title": parts[2].strip(),

            "description": parts[3].strip(),

            "characters": parts[4].strip(),

            "location": parts[5].strip(),

            "objects": parts[6].strip(),

            "action": parts[7].strip(),

            "lighting": parts[8].strip(),

            "image_query": parts[9].strip(),

            "video_query": parts[10].strip(),

            "narration": parts[11].strip()
        })

    # --------------------------------------------------------
    # FALLBACK SCENE CREATION
    # --------------------------------------------------------

    if not scenes:

        sentences = re.split(
            r'(?<=[.!?])\s+',
            story
        )

        sentences = [
            x.strip()
            for x in sentences
            if len(x.strip()) > 15
        ]

        if not sentences:
            sentences = [story]

        total = len(sentences)

        for i in range(number_of_scenes):

            start = int(
                i * total / number_of_scenes
            )

            end = int(
                (i + 1) * total / number_of_scenes
            )

            description = " ".join(
                sentences[start:end]
            )

            if not description:
                description = story

            scenes.append({

                "number": i + 1,

                "title":
                    f"Scene {i + 1}",

                "description":
                    description,

                "characters":
                    title,

                "location":
                    "cinematic environment",

                "objects":
                    "important story objects",

                "action":
                    description,

                "lighting":
                    "cinematic lighting",

                "image_query":
                    title,

                "video_query":
                    title,

                "narration":
                    description
            })

    return scenes[:number_of_scenes]


# ============================================================
# PIXABAY IMAGE SEARCH
# ============================================================

def search_pixabay_image(query):

    if not PIXABAY_API_KEY:
        return None

    try:

        response = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": PIXABAY_API_KEY,
                "q": query[:100],
                "image_type": "photo",
                "orientation": "horizontal",
                "safesearch": "true",
                "per_page": 20
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        hits = data.get(
            "hits",
            []
        )

        if not hits:
            return None

        # Prefer large images
        hits.sort(
            key=lambda x:
                x.get("imageWidth", 0),
            reverse=True
        )

        for hit in hits:

            url = (
                hit.get("largeImageURL")
                or hit.get("webformatURL")
            )

            if url:

                return {
                    "url": url,
                    "page": hit.get(
                        "pageURL",
                        ""
                    ),
                    "query": query
                }

    except Exception:
        return None

    return None


# ============================================================
# PIXABAY VIDEO SEARCH
# ============================================================

def search_pixabay_video(query):

    if not PIXABAY_API_KEY:
        return None

    try:

        response = requests.get(
            "https://pixabay.com/api/videos/",
            params={
                "key": PIXABAY_API_KEY,
                "q": query[:100],
                "video_type": "film",
                "safesearch": "true",
                "per_page": 20
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        hits = data.get(
            "hits",
            []
        )

        if not hits:
            return None

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

                video = videos.get(
                    quality
                )

                if not video:
                    continue

                url = video.get(
                    "url"
                )

                if url:

                    return {
                        "url": url,
                        "page": hit.get(
                            "pageURL",
                            ""
                        ),
                        "query": query
                    }

    except Exception:
        return None

    return None


# ============================================================
# DOWNLOAD IMAGE
# ============================================================

def download_image(url):

    try:

        response = requests.get(
            url,
            timeout=30
        )

        response.raise_for_status()

        return Image.open(
            BytesIO(
                response.content
            )
        ).convert("RGB")

    except Exception:
        return None


# ============================================================
# FIT IMAGE
# ============================================================

def fit_image(
    image,
    target_size
):

    width, height = target_size

    ratio = max(
        width / image.width,
        height / image.height
    )

    new_size = (
        int(image.width * ratio),
        int(image.height * ratio)
    )

    image = image.resize(
        new_size,
        Image.Resampling.LANCZOS
    )

    left = (
        image.width - width
    ) // 2

    top = (
        image.height - height
    ) // 2

    return image.crop(
        (
            left,
            top,
            left + width,
            top + height
        )
    )


# ============================================================
# FONT
# ============================================================

def get_font(size):

    possible_fonts = [

        "/usr/share/fonts/truetype/dejavu/"
        "DejaVuSans-Bold.ttf",

        "/usr/share/fonts/truetype/liberation2/"
        "LiberationSans-Bold.ttf",

        "C:/Windows/Fonts/arialbd.ttf"
    ]

    for path in possible_fonts:

        if os.path.exists(path):

            try:

                return ImageFont.truetype(
                    path,
                    size
                )

            except Exception:
                pass

    return ImageFont.load_default()


# ============================================================
# CINEMATIC POSTER
# ============================================================

def create_poster(
    title,
    images
):

    if not images:
        return None

    width = 1600
    height = 900

    canvas = Image.new(
        "RGB",
        (width, height),
        "#111111"
    )

    main = download_image(
        images[0]["url"]
    )

    if not main:
        return None

    main = fit_image(
        main,
        (width, height)
    )

    main = ImageEnhance.Color(
        main
    ).enhance(1.2)

    main = ImageEnhance.Contrast(
        main
    ).enhance(1.08)

    canvas.paste(
        main,
        (0, 0)
    )

    # --------------------------------------------------------
    # Overlay
    # --------------------------------------------------------

    overlay = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(
        overlay
    )

    draw.rectangle(
        (0, 0, width, height),
        fill=(0, 0, 0, 85)
    )

    draw.rectangle(
        (0, 560, width, height),
        fill=(0, 0, 0, 175)
    )

    canvas = Image.alpha_composite(
        canvas.convert("RGBA"),
        overlay
    ).convert("RGB")

    draw = ImageDraw.Draw(
        canvas
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    draw.text(
        (60, 590),
        title,
        font=get_font(65),
        fill="white",
        stroke_width=2,
        stroke_fill="black"
    )

    draw.text(
        (65, 680),
        "A CINEMATIC AI STORY",
        font=get_font(25),
        fill="#DDDDDD"
    )

    # --------------------------------------------------------
    # Thumbnail strip
    # --------------------------------------------------------

    thumbnail_width = 200
    thumbnail_height = 115

    x = 60
    y = 755

    for index, item in enumerate(
        images[:6]
    ):

        img = download_image(
            item["url"]
        )

        if not img:
            continue

        thumb = fit_image(
            img,
            (
                thumbnail_width,
                thumbnail_height
            )
        )

        canvas.paste(
            thumb,
            (x, y)
        )

        x += 220

        if x > 1300:
            break

    output = BytesIO()

    canvas.save(
        output,
        format="JPEG",
        quality=95
    )

    output.seek(0)

    return output.getvalue()


# ============================================================
# FFMPEG
# ============================================================

def get_ffmpeg():

    if imageio_ffmpeg is None:

        raise RuntimeError(
            "FFmpeg is not installed. "
            "Add imageio-ffmpeg to requirements.txt."
        )

    try:

        return imageio_ffmpeg.get_ffmpeg_exe()

    except Exception as e:

        raise RuntimeError(
            f"Could not locate FFmpeg: {e}"
        )


# ============================================================
# DOWNLOAD VIDEO
# ============================================================

def download_video(
    url,
    output_path
):

    try:

        response = requests.get(
            url,
            stream=True,
            timeout=120
        )

        response.raise_for_status()

        with open(
            output_path,
            "wb"
        ) as file:

            for chunk in response.iter_content(
                1024 * 1024
            ):

                if chunk:
                    file.write(chunk)

        return True

    except Exception:
        return False


# ============================================================
# NORMALIZE VIDEO
# ============================================================

def normalize_video(
    input_path,
    output_path,
    duration
):

    ffmpeg = get_ffmpeg()

    command = [

        ffmpeg,

        "-y",

        "-i",
        input_path,

        "-t",
        str(duration),

        "-vf",
        (
            "scale=1280:720:"
            "force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2"
        ),

        "-r",
        "25",

        "-an",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-pix_fmt",
        "yuv420p",

        output_path
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=240
    )

    return (
        result.returncode == 0
        and os.path.exists(
            output_path
        )
    )


# ============================================================
# CREATE MULTI-SCENE VIDEO
# ============================================================

def create_movie(
    videos,
    duration
):

    if not videos:
        return None

    temp_dir = tempfile.mkdtemp(
        prefix="cinematic_movie_"
    )

    try:

        normalized = []

        # ----------------------------------------------------
        # Download each scene
        # ----------------------------------------------------

        for index, video in enumerate(videos):

            raw = os.path.join(
                temp_dir,
                f"raw_{index}.mp4"
            )

            clean = os.path.join(
                temp_dir,
                f"scene_{index}.mp4"
            )

            if not download_video(
                video["url"],
                raw
            ):
                continue

            if normalize_video(
                raw,
                clean,
                duration
            ):

                normalized.append(
                    clean
                )

        if not normalized:
            return None

        # ----------------------------------------------------
        # Create concat file
        # ----------------------------------------------------

        concat = os.path.join(
            temp_dir,
            "concat.txt"
        )

        with open(
            concat,
            "w",
            encoding="utf-8"
        ) as f:

            for path in normalized:

                path = path.replace(
                    "'",
                    "'\\''"
                )

                f.write(
                    f"file '{path}'\n"
                )

        final_path = os.path.join(
            temp_dir,
            "movie.mp4"
        )

        ffmpeg = get_ffmpeg()

        command = [

            ffmpeg,

            "-y",

            "-f",
            "concat",

            "-safe",
            "0",

            "-i",
            concat,

            "-c",
            "copy",

            final_path
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300
        )

        if (
            result.returncode != 0
            or not os.path.exists(final_path)
        ):

            return None

        with open(
            final_path,
            "rb"
        ) as f:

            return f.read()

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# ============================================================
# GENERATE TTS
# ============================================================

def create_audio(
    text,
    lang
):

    output = BytesIO()

    tts = gTTS(
        text=text,
        lang=lang,
        slow=False
    )

    tts.write_to_fp(
        output
    )

    output.seek(0)

    return output.read()


# ============================================================
# SCENE AUDIO
# ============================================================

def create_scene_audio(
    scenes,
    lang
):

    results = []

    progress = st.progress(
        0,
        text="Creating narration..."
    )

    total = len(scenes)

    for index, scene in enumerate(
        scenes
    ):

        try:

            audio = create_audio(
                scene["narration"],
                lang
            )

            results.append({

                "scene":
                    scene["number"],

                "title":
                    scene["title"],

                "text":
                    scene["narration"],

                "audio":
                    audio
            })

        except Exception as e:

            st.warning(
                f"Scene {scene['number']} "
                f"narration failed: {e}"
            )

        progress.progress(
            (index + 1) / total,
            text=(
                f"Narration "
                f"{index + 1}/{total}"
            )
        )

    return results


# ============================================================
# COMBINE AUDIO FILES
# ============================================================

def combine_audio_files(
    audio_items
):

    if not audio_items:
        return None

    temp_dir = tempfile.mkdtemp(
        prefix="story_audio_"
    )

    try:

        files = []

        for index, item in enumerate(
            audio_items
        ):

            path = os.path.join(
                temp_dir,
                f"audio_{index}.mp3"
            )

            with open(
                path,
                "wb"
            ) as f:

                f.write(
                    item["audio"]
                )

            files.append(path)

        concat = os.path.join(
            temp_dir,
            "audio.txt"
        )

        with open(
            concat,
            "w",
            encoding="utf-8"
        ) as f:

            for path in files:

                path = path.replace(
                    "'",
                    "'\\''"
                )

                f.write(
                    f"file '{path}'\n"
                )

        output_path = os.path.join(
            temp_dir,
            "full_narration.mp3"
        )

        ffmpeg = get_ffmpeg()

        command = [

            ffmpeg,

            "-y",

            "-f",
            "concat",

            "-safe",
            "0",

            "-i",
            concat,

            "-c:a",
            "libmp3lame",

            output_path
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300
        )

        if (
            result.returncode != 0
            or not os.path.exists(output_path)
        ):

            return None

        with open(
            output_path,
            "rb"
        ) as f:

            return f.read()

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# ============================================================
# COMBINE VIDEO + AUDIO
# ============================================================

def add_narration_to_video(
    video_bytes,
    audio_bytes
):

    if not video_bytes or not audio_bytes:
        return None

    temp_dir = tempfile.mkdtemp(
        prefix="narrated_movie_"
    )

    try:

        video_path = os.path.join(
            temp_dir,
            "video.mp4"
        )

        audio_path = os.path.join(
            temp_dir,
            "audio.mp3"
        )

        output_path = os.path.join(
            temp_dir,
            "narrated.mp4"
        )

        with open(
            video_path,
            "wb"
        ) as f:

            f.write(
                video_bytes
            )

        with open(
            audio_path,
            "wb"
        ) as f:

            f.write(
                audio_bytes
            )

        ffmpeg = get_ffmpeg()

        command = [

            ffmpeg,

            "-y",

            "-i",
            video_path,

            "-i",
            audio_path,

            "-map",
            "0:v:0",

            "-map",
            "1:a:0",

            "-c:v",
            "copy",

            "-c:a",
            "aac",

            "-shortest",

            output_path
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300
        )

        if (
            result.returncode != 0
            or not os.path.exists(output_path)
        ):

            return None

        with open(
            output_path,
            "rb"
        ) as f:

            return f.read()

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# ============================================================
# INPUT
# ============================================================

title = st.text_input(
    "📖 Story Topic / Title",
    placeholder=(
        "Example: Elara and the Secret Forest"
    )
)


# ============================================================
# MAIN GENERATE BUTTON
# ============================================================

if st.button(
    "🚀 Generate Complete Story Project",
    type="primary",
    use_container_width=True
):

    if not title.strip():

        st.warning(
            "Please enter a story title."
        )

        st.stop()

    if not GEMINI_API_KEY and not GROQ_API_KEY:

        st.error(
            "Please add GEMINI_API_KEY "
            "or GROQ_API_KEY to Streamlit secrets."
        )

        st.stop()

    # --------------------------------------------------------
    # Clear previous project
    # --------------------------------------------------------

    for key in [
        "story",
        "story_title",
        "provider",
        "scenes",
        "scene_images",
        "scene_videos",
        "scene_audio",
        "poster_bytes",
        "video_bytes",
        "narrated_video_bytes",
        "audio_bytes"
    ]:

        if key == "story_title":
            st.session_state[key] = title

        elif key == "scenes":
            st.session_state[key] = []

        elif key in [
            "scene_images",
            "scene_videos",
            "scene_audio"
        ]:

            st.session_state[key] = []

        else:

            st.session_state[key] = None \
                if key not in [
                    "story",
                    "provider"
                ] else ""

    # --------------------------------------------------------
    # STEP 1
    # --------------------------------------------------------

    st.subheader(
        "1️⃣ Writing Story"
    )

    try:

        progress = st.progress(
            0,
            text="Writing cinematic story..."
        )

        story, provider = generate_story(
            title,
            word_limit
        )

        st.session_state.story = story
        st.session_state.provider = provider

        progress.progress(
            100,
            text="Story completed ✓"
        )

    except Exception as e:

        st.error(
            f"Story generation failed:\n\n{e}"
        )

        st.stop()

    # --------------------------------------------------------
    # STEP 2
    # --------------------------------------------------------

    st.subheader(
        "2️⃣ Creating Cinematic Storyboard"
    )

    try:

        progress = st.progress(
            0,
            text="Analyzing story..."
        )

        scenes = create_scene_plan(
            title,
            story,
            scene_count
        )

        st.session_state.scenes = scenes

        progress.progress(
            100,
            text=f"{len(scenes)} scenes created ✓"
        )

        st.session_state.project_generated = True

    except Exception as e:

        st.error(
            f"Scene generation failed:\n\n{e}"
        )

        st.stop()


# ============================================================
# STORY DISPLAY
# ============================================================

if st.session_state.story:

    st.divider()

    st.subheader(
        f"📖 {st.session_state.story_title}"
    )

    safe_story = html.escape(
        st.session_state.story
    )

    st.markdown(
        f"""
        <div class="story-card">
            {safe_story.replace(chr(10), "<br>")}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption(
        f"Generated using {st.session_state.provider}"
    )


# ============================================================
# STORYBOARD DISPLAY
# ============================================================

if st.session_state.scenes:

    st.divider()

    st.subheader(
        "🎞️ Cinematic Storyboard"
    )

    for scene in st.session_state.scenes:

        with st.expander(
            f"🎬 Scene {scene['number']}: "
            f"{scene['title']}",
            expanded=False
        ):

            st.markdown(
                f"""
                <div class="scene-card">

                <h3>
                    {html.escape(scene["title"])}
                </h3>

                <p>
                    <b>📖 Description:</b><br>
                    {html.escape(scene["description"])}
                </p>

                <p>
                    <b>👤 Characters:</b>
                    {html.escape(scene["characters"])}
                </p>

                <p>
                    <b>📍 Location:</b>
                    {html.escape(scene["location"])}
                </p>

                <p>
                    <b>🎒 Objects:</b>
                    {html.escape(scene["objects"])}
                </p>

                <p>
                    <b>🏃 Action:</b>
                    {html.escape(scene["action"])}
                </p>

                <p>
                    <b>💡 Lighting:</b>
                    {html.escape(scene["lighting"])}
                </p>

                <p>
                    <b>🖼️ Image query:</b>
                    {html.escape(scene["image_query"])}
                </p>

                <p>
                    <b>🎥 Video query:</b>
                    {html.escape(scene["video_query"])}
                </p>

                <p>
                    <b>🎙️ Narration:</b>
                    {html.escape(scene["narration"])}
                </p>

                </div>
                """,
                unsafe_allow_html=True
            )


# ============================================================
# MEDIA CONTROLS
# ============================================================

if st.session_state.scenes:

    st.divider()

    st.subheader(
        "🎨 Generate Media"
    )

    col1, col2, col3 = st.columns(3)


    # ========================================================
    # PHOTO
    # ========================================================

    with col1:

        if st.button(
            "🖼️ Generate Story Photo",
            use_container_width=True
        ):

            if not PIXABAY_API_KEY:

                st.error(
                    "PIXABAY_API_KEY is missing."
                )

            else:

                images = []

                progress = st.progress(
                    0,
                    text="Searching relevant images..."
                )

                total = len(
                    st.session_state.scenes
                )

                for index, scene in enumerate(
                    st.session_state.scenes
                ):

                    query = scene[
                        "image_query"
                    ]

                    result = search_pixabay_image(
                        query
                    )

                    # --------------------------------------------
                    # Fallback query
                    # --------------------------------------------

                    if not result:

                        fallback_query = (
                            f"{scene['location']} "
                            f"{scene['action']}"
                        )

                        result = search_pixabay_image(
                            fallback_query
                        )

                    if result:

                        result["scene"] = (
                            scene["number"]
                        )

                        result["title"] = (
                            scene["title"]
                        )

                        images.append(
                            result
                        )

                    progress.progress(
                        (index + 1) / total,
                        text=(
                            f"Image "
                            f"{index + 1}/{total}"
                        )
                    )

                st.session_state.scene_images = images

                if images:

                    with st.spinner(
                        "Creating cinematic poster..."
                    ):

                        poster = create_poster(
                            st.session_state.story_title,
                            images
                        )

                    st.session_state.poster_bytes = (
                        poster
                    )

                    st.success(
                        f"{len(images)} relevant scene "
                        f"images found."
                    )

                else:

                    st.warning(
                        "No relevant images were found."
                    )


    # ========================================================
    # VIDEO
    # ========================================================

    with col2:

        if st.button(
            "🎥 Generate Multi-Scene Video",
            use_container_width=True
        ):

            if not PIXABAY_API_KEY:

                st.error(
                    "PIXABAY_API_KEY is missing."
                )

            elif imageio_ffmpeg is None:

                st.error(
                    "FFmpeg is not available."
                )

                st.info(
                    "Add imageio-ffmpeg to "
                    "requirements.txt and redeploy."
                )

            else:

                videos = []

                progress = st.progress(
                    0,
                    text="Searching cinematic video clips..."
                )

                total = len(
                    st.session_state.scenes
                )

                for index, scene in enumerate(
                    st.session_state.scenes
                ):

                    query = scene[
                        "video_query"
                    ]

                    result = search_pixabay_video(
                        query
                    )

                    if not result:

                        fallback_query = (
                            f"{scene['location']} "
                            f"{scene['action']}"
                        )

                        result = search_pixabay_video(
                            fallback_query
                        )

                    if result:

                        result["scene"] = (
                            scene["number"]
                        )

                        result["title"] = (
                            scene["title"]
                        )

                        videos.append(
                            result
                        )

                    progress.progress(
                        (index + 1) / total,
                        text=(
                            f"Video search "
                            f"{index + 1}/{total}"
                        )
                    )

                st.session_state.scene_videos = (
                    videos
                )

                if not videos:

                    st.warning(
                        "No suitable video clips found."
                    )

                else:

                    with st.spinner(
                        "🎬 Downloading and assembling movie..."
                    ):

                        movie = create_movie(
                            videos,
                            clip_duration
                        )

                    if movie:

                        st.session_state.video_bytes = (
                            movie
                        )

                        st.success(
                            f"Movie created using "
                            f"{len(videos)} scenes."
                        )

                        # ----------------------------------------
                        # Generate scene narration
                        # ----------------------------------------

                        with st.spinner(
                            "🎙️ Generating scene narration..."
                        ):

                            try:

                                audio_items = (
                                    create_scene_audio(
                                        st.session_state.scenes,
                                        narration_language[1]
                                    )
                                )

                                st.session_state.scene_audio = (
                                    audio_items
                                )

                                full_audio = (
                                    combine_audio_files(
                                        audio_items
                                    )
                                )

                                st.session_state.audio_bytes = (
                                    full_audio
                                )

                                if full_audio:

                                    narrated_movie = (
                                        add_narration_to_video(
                                            movie,
                                            full_audio
                                        )
                                    )

                                    st.session_state.narrated_video_bytes = (
                                        narrated_movie
                                    )

                            except Exception as e:

                                st.warning(
                                    f"Narration could not be "
                                    f"added: {e}"
                                )

                    else:

                        st.error(
                            "The video clips could not "
                            "be assembled."
                        )


    # ========================================================
    # FULL NARRATION
    # ========================================================

    with col3:

        if st.button(
            "🔊 Generate Full Narration",
            use_container_width=True
        ):

            with st.spinner(
                "🎙️ Generating complete narration..."
            ):

                try:

                    audio = create_audio(
                        st.session_state.story,
                        narration_language[1]
                    )

                    st.session_state.audio_bytes = (
                        audio
                    )

                    st.success(
                        "Full narration created!"
                    )

                except Exception as e:

                    st.error(
                        f"Narration failed:\n\n{e}"
                    )


# ============================================================
# POSTER
# ============================================================

if st.session_state.poster_bytes:

    st.divider()

    st.subheader(
        "🖼️ Cinematic Story Poster"
    )

    st.image(
        st.session_state.poster_bytes,
        use_container_width=True
    )

    st.download_button(
        "⬇️ Download Story Photo",
        data=st.session_state.poster_bytes,
        file_name="cinematic_story_poster.jpg",
        mime="image/jpeg",
        use_container_width=True
    )


# ============================================================
# MOVIE
# ============================================================

if st.session_state.video_bytes:

    st.divider()

    st.subheader(
        "🎥 Multi-Scene Movie"
    )

    st.video(
        st.session_state.video_bytes
    )

    st.download_button(
        "⬇️ Download Multi-Scene Movie",
        data=st.session_state.video_bytes,
        file_name="multi_scene_movie.mp4",
        mime="video/mp4",
        use_container_width=True
    )


# ============================================================
# NARRATED MOVIE
# ============================================================

if st.session_state.narrated_video_bytes:

    st.divider()

    st.subheader(
        "🎬 Complete Narrated Movie"
    )

    st.video(
        st.session_state.narrated_video_bytes
    )

    st.download_button(
        "⬇️ Download Narrated Movie",
        data=st.session_state.narrated_video_bytes,
        file_name="complete_narrated_movie.mp4",
        mime="video/mp4",
        use_container_width=True
    )


# ============================================================
# AUDIO
# ============================================================

if st.session_state.audio_bytes:

    st.divider()

    st.subheader(
        "🎙️ Full Narration"
    )

    st.audio(
        st.session_state.audio_bytes,
        format="audio/mp3"
    )

    st.download_button(
        "⬇️ Download Narration",
        data=st.session_state.audio_bytes,
        file_name="story_narration.mp3",
        mime="audio/mp3",
        use_container_width=True
    )


# ============================================================
# SCENE MEDIA
# ============================================================

if (
    st.session_state.scene_images
    or
    st.session_state.scene_videos
):

    st.divider()

    st.subheader(
        "🎞️ Scene-by-Scene Media"
    )

    image_lookup = {
        x["scene"]: x
        for x in st.session_state.scene_images
    }

    video_lookup = {
        x["scene"]: x
        for x in st.session_state.scene_videos
    }

    for scene in st.session_state.scenes:

        number = scene["number"]

        with st.expander(
            f"🎬 Scene {number}: "
            f"{scene['title']}"
        ):

            left, right = st.columns(2)

            with left:

                if number in image_lookup:

                    image_data = (
                        image_lookup[number]
                    )

                    image = download_image(
                        image_data["url"]
                    )

                    if image:

                        st.image(
                            image,
                            use_container_width=True
                        )

                    st.caption(
                        "🖼️ " +
                        image_data["query"]
                    )

                else:

                    st.info(
                        "No image found."
                    )

            with right:

                if number in video_lookup:

                    video_data = (
                        video_lookup[number]
                    )

                    st.video(
                        video_data["url"]
                    )

                    st.caption(
                        "🎥 " +
                        video_data["query"]
                    )

                else:

                    st.info(
                        "No video found."
                    )

            st.markdown(
                f"**🎙️ Narration:** "
                f"{scene['narration']}"
            )


# ============================================================
# PROJECT STATS
# ============================================================

if st.session_state.story:

    st.divider()

    st.subheader(
        "📊 Project Statistics"
    )

    a, b, c, d = st.columns(4)

    with a:

        st.metric(
            "Story words",
            len(
                st.session_state.story.split()
            )
        )

    with b:

        st.metric(
            "Scenes",
            len(
                st.session_state.scenes
            )
        )

    with c:

        st.metric(
            "Images",
            len(
                st.session_state.scene_images
            )
        )

    with d:

        st.metric(
            "Video clips",
            len(
                st.session_state.scene_videos
            )
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div style="
        text-align:center;
        opacity:0.55;
        padding:20px;
    ">
        🎬 AI Story & Cinematic Studio
        <br>
        Story • Storyboard • Visuals • Video • Narration
    </div>
    """,
    unsafe_allow_html=True
)
