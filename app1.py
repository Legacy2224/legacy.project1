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

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from gtts import gTTS
from groq import Groq
from google import genai
import imageio_ffmpeg


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
# API KEYS
# ============================================================

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
PIXABAY_API_KEY = st.secrets.get("PIXABAY_API_KEY", "")


# ============================================================
# CLIENTS
# ============================================================

gemini_client = None
groq_client = None

if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        gemini_client = None

if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception:
        groq_client = None


# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
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
    "generation_complete": False,
    "media_generation_complete": False,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


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
            <div style="font-size:45px;">🎬</div>
            <h2 style="margin:0;">AI Story Studio</h2>
            <p style="opacity:0.7;">
                Story → Scenes → Images → Video → Voice
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    # --------------------------------------------------------
    # COLOUR CUSTOMIZATION
    # --------------------------------------------------------

    st.subheader("🎨 Studio Colours")

    primary_color = st.color_picker(
        "Primary colour",
        "#7C3AED"
    )

    background_color = st.color_picker(
        "Background colour",
        "#0E1117"
    )

    card_color = st.color_picker(
        "Card colour",
        "#171B24"
    )

    text_color = st.color_picker(
        "Text colour",
        "#FFFFFF"
    )

    accent_color = st.color_picker(
        "Accent colour",
        "#22C55E"
    )

    st.divider()

    # --------------------------------------------------------
    # STORY SETTINGS
    # --------------------------------------------------------

    st.subheader("⚙️ Story Settings")

    word_limit = st.slider(
        "Story length",
        min_value=150,
        max_value=2000,
        value=700,
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

    scene_count = st.slider(
        "Number of video scenes",
        min_value=4,
        max_value=10,
        value=6
    )

    clip_duration = st.slider(
        "Seconds per scene",
        min_value=3,
        max_value=10,
        value=5
    )

    st.divider()

    # --------------------------------------------------------
    # API STATUS
    # --------------------------------------------------------

    st.subheader("🔑 API Status")

    if GEMINI_API_KEY:
        st.success("Gemini ✓")
    else:
        st.warning("Gemini API key missing")

    if GROQ_API_KEY:
        st.success("Groq ✓")
    else:
        st.info("Groq fallback unavailable")

    if PIXABAY_API_KEY:
        st.success("Pixabay ✓")
    else:
        st.warning("Pixabay API key missing")

    st.divider()

    st.info(
        "This version creates a structured cinematic storyboard "
        "before searching for images and video clips."
    )


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    f"""
    <style>

    .stApp {{
        background-color: {background_color};
        color: {text_color};
    }}

    [data-testid="stSidebar"] {{
        background-color: {card_color};
    }}

    .main-title {{
        font-size: 44px;
        font-weight: 800;
        color: {text_color};
        margin-bottom: 5px;
    }}

    .subtitle {{
        color: rgba(255,255,255,0.68);
        font-size: 17px;
        margin-bottom: 25px;
    }}

    .story-card {{
        background: {card_color};
        border: 1px solid rgba(255,255,255,0.08);
        border-left: 5px solid {primary_color};
        border-radius: 18px;
        padding: 28px;
        line-height: 1.85;
        font-size: 17px;
        margin-top: 15px;
    }}

    .scene-card {{
        background: {card_color};
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 18px;
        border-left: 5px solid {primary_color};
    }}

    .feature-card {{
        background: {card_color};
        border-radius: 16px;
        padding: 22px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.08);
    }}

    div.stButton > button {{
        border-radius: 12px;
        border: 1px solid {primary_color};
        font-weight: 600;
    }}

    div.stButton > button:hover {{
        border-color: {accent_color};
        color: {accent_color};
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# TITLE
# ============================================================

st.markdown(
    '<div class="main-title">🎬 AI Story, Photo & Cinematic Video Studio</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Create an original story and transform it into a cinematic '
    'multi-scene visual experience.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# GEMINI TEXT GENERATION
# ============================================================

def gemini_text(prompt):

    if not gemini_client:
        raise Exception(
            "GEMINI_API_KEY is missing or Gemini could not be initialized."
        )

    response = gemini_client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    if not response or not response.text:
        raise Exception(
            "Gemini returned an empty response."
        )

    return response.text.strip()


# ============================================================
# GROQ TEXT GENERATION
# ============================================================

def groq_text(prompt):

    if not groq_client:
        raise Exception(
            "GROQ_API_KEY is missing."
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
        max_tokens=6000
    )

    if not response.choices:
        raise Exception(
            "Groq returned no choices."
        )

    return response.choices[0].message.content.strip()


# ============================================================
# GENERIC AI TEXT WITH FALLBACK
# ============================================================

def ai_text(prompt):

    gemini_error = None

    if gemini_client:

        try:
            return gemini_text(prompt), "Gemini Flash Lite"

        except Exception as e:
            gemini_error = e

    if groq_client:

        try:
            return groq_text(prompt), "Groq"

        except Exception as groq_error:
            raise Exception(
                f"Gemini failed: {gemini_error}\n\n"
                f"Groq failed: {groq_error}"
            )

    raise Exception(
        f"Gemini failed: {gemini_error}\n\n"
        "No Groq fallback is configured."
    )


# ============================================================
# STORY GENERATOR
# ============================================================

def generate_story(title, word_limit):

    prompt = f"""
You are an expert cinematic fantasy storyteller.

Create an ORIGINAL story titled:

"{title}"

Length:
Approximately {word_limit} words.

Requirements:

1. Strong cinematic opening.
2. Clear protagonist.
3. Important supporting characters.
4. Specific locations.
5. A meaningful conflict.
6. Escalating events.
7. Strong emotional progression.
8. A satisfying ending.
9. Highly visual writing.
10. Every major scene must contain things that can be visually shown.
11. Include concrete:
    - characters
    - clothing
    - environments
    - objects
    - architecture
    - weather
    - lighting
    - actions
    - creatures when relevant
12. Avoid vague descriptions.
13. Make the story suitable for a general audience.
14. Do not explain the writing process.
15. Return ONLY the story.

The story should be suitable for conversion into a cinematic
multi-scene movie.
"""

    return ai_text(prompt)


# ============================================================
# SCENE PLANNER
# ============================================================

def create_scene_plan(title, story, number_of_scenes):

    prompt = f"""
You are a professional film director, storyboard artist,
cinematographer and visual prompt engineer.

Convert the story below into EXACTLY {number_of_scenes}
cinematic scenes.

TITLE:
{title}

STORY:
{story[:16000]}

IMPORTANT:

The scenes must cover the ENTIRE story from beginning to ending.

Do NOT simply divide the story by sentence.

Each scene should represent an important visual event.

For every scene determine:

- scene number
- scene title
- what happens
- characters present
- location
- important objects
- character actions
- lighting
- weather
- atmosphere
- image search query
- video search query
- narration

VISUAL CONTINUITY:

If the same character appears in multiple scenes,
keep their appearance consistent.

For example:

Elara = young woman, long dark brown hair,
emerald cloak, leather boots.

Do not randomly change her appearance.

IMAGE QUERY:

Create a concise query suitable for Pixabay.

VIDEO QUERY:

Create a concise query suitable for Pixabay video search.

Queries must describe visible things.

Do not use abstract terms such as:

emotion
concept
symbolism
meaning
hope
fear

Instead use visible things such as:

young woman entering enchanted forest
dark castle during thunderstorm
ancient glowing stone doorway
warrior riding through snowy mountain

NARRATION:

Write 1–3 sentences describing what the narrator says
during this scene.

Return ONLY this format:

SCENE|1|TITLE|DESCRIPTION|CHARACTERS|LOCATION|OBJECTS|ACTION|LIGHTING|IMAGE_QUERY|VIDEO_QUERY|NARRATION

SCENE|2|TITLE|DESCRIPTION|CHARACTERS|LOCATION|OBJECTS|ACTION|LIGHTING|IMAGE_QUERY|VIDEO_QUERY|NARRATION

...

Do not use the | character inside any field.
"""

    result, _ = ai_text(prompt)

    scenes = []

    for raw_line in result.splitlines():

        line = raw_line.strip()

        if not line.startswith("SCENE|"):
            continue

        parts = line.split("|")

        if len(parts) < 12:
            continue

        try:
            scene_number = int(parts[1].strip())
        except Exception:
            scene_number = len(scenes) + 1

        scene = {
            "number": scene_number,
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
        }

        scenes.append(scene)

    # --------------------------------------------------------
    # Fallback if AI formatting fails
    # --------------------------------------------------------

    if not scenes:

        sentences = [
            s.strip()
            for s in re.split(r'(?<=[.!?])\s+', story)
            if len(s.strip()) > 20
        ]

        if not sentences:
            sentences = [story]

        chunk_size = max(
            1,
            len(sentences) // number_of_scenes
        )

        for i in range(number_of_scenes):

            start = i * chunk_size
            end = (
                len(sentences)
                if i == number_of_scenes - 1
                else (i + 1) * chunk_size
            )

            description = " ".join(
                sentences[start:end]
            )

            scenes.append({
                "number": i + 1,
                "title": f"Scene {i + 1}",
                "description": description,
                "characters": title,
                "location": "cinematic environment",
                "objects": "story elements",
                "action": description,
                "lighting": "cinematic lighting",
                "image_query": title,
                "video_query": title,
                "narration": description
            })

    return scenes[:number_of_scenes]


# ============================================================
# PIXABAY IMAGE SEARCH
# ============================================================

def pixabay_image(query):

    if not PIXABAY_API_KEY:
        return None

    url = "https://pixabay.com/api/"

    params = {
        "key": PIXABAY_API_KEY,
        "q": query[:100],
        "image_type": "photo",
        "orientation": "horizontal",
        "safesearch": "true",
        "per_page": 20
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        hits = data.get("hits", [])

        if not hits:
            return None

        # ----------------------------------------------------
        # Prefer landscape images
        # ----------------------------------------------------

        for hit in hits:

            image_url = (
                hit.get("largeImageURL")
                or hit.get("webformatURL")
            )

            if image_url:

                return {
                    "url": image_url,
                    "page": hit.get("pageURL", ""),
                    "query": query
                }

    except Exception:
        return None

    return None


# ============================================================
# PIXABAY VIDEO SEARCH
# ============================================================

def pixabay_video(query):

    if not PIXABAY_API_KEY:
        return None

    url = "https://pixabay.com/api/videos/"

    params = {
        "key": PIXABAY_API_KEY,
        "q": query[:100],
        "video_type": "film",
        "safesearch": "true",
        "per_page": 20
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        hits = data.get("hits", [])

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

                if quality not in videos:
                    continue

                video_url = videos[
                    quality
                ].get("url")

                if video_url:

                    return {
                        "url": video_url,
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
# IMAGE DOWNLOAD
# ============================================================

def download_image(url):

    try:

        response = requests.get(
            url,
            timeout=30
        )

        response.raise_for_status()

        return Image.open(
            BytesIO(response.content)
        ).convert("RGB")

    except Exception:
        return None


# ============================================================
# IMAGE FIT
# ============================================================

def image_fit(image, size):

    target_width, target_height = size

    if image.width <= 0 or image.height <= 0:
        return image

    image_ratio = (
        image.width / image.height
    )

    target_ratio = (
        target_width / target_height
    )

    if image_ratio > target_ratio:

        new_height = target_height

        new_width = int(
            new_height * image_ratio
        )

    else:

        new_width = target_width

        new_height = int(
            new_width / image_ratio
        )

    image = image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS
    )

    left = (
        new_width - target_width
    ) // 2

    top = (
        new_height - target_height
    ) // 2

    return image.crop(
        (
            left,
            top,
            left + target_width,
            top + target_height
        )
    )


# ============================================================
# FONT
# ============================================================

def get_font(size):

    fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf"
    ]

    for path in fonts:

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

def create_cinematic_poster(
    title,
    scene_images
):

    width = 1600
    height = 1000

    canvas = Image.new(
        "RGB",
        (width, height),
        (12, 14, 20)
    )

    valid_images = []

    for item in scene_images:

        image = download_image(
            item["url"]
        )

        if image:

            valid_images.append(
                (image, item)
            )

    if not valid_images:
        return None

    # --------------------------------------------------------
    # Main image
    # --------------------------------------------------------

    main_image = valid_images[0][0]

    main_image = ImageEnhance.Color(
        main_image
    ).enhance(1.18)

    main_image = ImageEnhance.Contrast(
        main_image
    ).enhance(1.08)

    main_image = image_fit(
        main_image,
        (width, height)
    )

    canvas.paste(
        main_image,
        (0, 0)
    )

    # --------------------------------------------------------
    # Cinematic overlay
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
        fill=(0, 0, 0, 95)
    )

    draw.rectangle(
        (0, 500, width, height),
        fill=(0, 0, 0, 150)
    )

    canvas = Image.alpha_composite(
        canvas.convert("RGBA"),
        overlay
    ).convert("RGB")

    # --------------------------------------------------------
    # Scene thumbnails
    # --------------------------------------------------------

    thumb_size = (250, 145)

    start_x = 55
    thumb_y = 725

    for index, (image, item) in enumerate(
        valid_images[1:5]
    ):

        x = (
            start_x +
            index * 300
        )

        thumb = image_fit(
            image,
            thumb_size
        )

        canvas.paste(
            thumb,
            (x, thumb_y)
        )

        draw = ImageDraw.Draw(
            canvas
        )

        draw.rectangle(
            (
                x,
                thumb_y + 115,
                x + 250,
                thumb_y + 145
            ),
            fill=(0, 0, 0)
        )

        draw.text(
            (
                x + 10,
                thumb_y + 121
            ),
            f"Scene {index + 2}",
            font=get_font(16),
            fill="white"
        )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    draw = ImageDraw.Draw(
        canvas
    )

    title_font = get_font(68)

    title_text = title

    if len(title_text) > 32:

        words = title_text.split()

        line1 = ""
        line2 = ""

        for word in words:

            if len(
                line1 + " " + word
            ) < 32:

                line1 += (
                    (" " if line1 else "")
                    + word
                )

            else:

                line2 += (
                    (" " if line2 else "")
                    + word
                )

        title_text = (
            line1 +
            "\n" +
            line2
        )

    draw.text(
        (55, 545),
        title_text,
        font=title_font,
        fill="white",
        stroke_width=2,
        stroke_fill="black"
    )

    subtitle_font = get_font(24)

    draw.text(
        (58, 675),
        "A CINEMATIC STORY EXPERIENCE",
        font=subtitle_font,
        fill=(220, 220, 220)
    )

    # --------------------------------------------------------
    # Border
    # --------------------------------------------------------

    draw.rectangle(
        (
            15,
            15,
            width - 15,
            height - 15
        ),
        outline=(255, 255, 255),
        width=3
    )

    output = BytesIO()

    canvas.save(
        output,
        format="JPEG",
        quality=94
    )

    output.seek(0)

    return output.getvalue()


# ============================================================
# VIDEO DOWNLOAD
# ============================================================

def download_video(
    url,
    output_path
):

    try:

        response = requests.get(
            url,
            timeout=90,
            stream=True
        )

        response.raise_for_status()

        with open(
            output_path,
            "wb"
        ) as file:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
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

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

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

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-pix_fmt",
        "yuv420p",

        "-an",

        output_path
    ]

    try:

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180
        )

        return (
            result.returncode == 0
            and os.path.exists(output_path)
        )

    except Exception:
        return False


# ============================================================
# MULTI-SCENE VIDEO
# ============================================================

def create_multiscene_video(
    scene_videos,
    clip_duration
):

    if not scene_videos:
        return None

    temp_dir = tempfile.mkdtemp(
        prefix="story_video_"
    )

    try:

        normalized_files = []

        # ----------------------------------------------------
        # Download + normalize
        # ----------------------------------------------------

        for index, scene in enumerate(
            scene_videos
        ):

            raw_path = os.path.join(
                temp_dir,
                f"raw_{index}.mp4"
            )

            normalized_path = os.path.join(
                temp_dir,
                f"scene_{index}.mp4"
            )

            downloaded = download_video(
                scene["url"],
                raw_path
            )

            if not downloaded:
                continue

            success = normalize_video(
                raw_path,
                normalized_path,
                clip_duration
            )

            if success:

                normalized_files.append(
                    normalized_path
                )

        if not normalized_files:
            return None

        # ----------------------------------------------------
        # FFmpeg concat
        # ----------------------------------------------------

        concat_file = os.path.join(
            temp_dir,
            "concat.txt"
        )

        with open(
            concat_file,
            "w",
            encoding="utf-8"
        ) as file:

            for path in normalized_files:

                safe_path = path.replace(
                    "'",
                    "'\\''"
                )

                file.write(
                    f"file '{safe_path}'\n"
                )

        final_path = os.path.join(
            temp_dir,
            "final_story.mp4"
        )

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        command = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_file,
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
        ) as file:

            return file.read()

    except Exception:
        return None

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# ============================================================
# GENERATE AUDIO
# ============================================================

def generate_audio(
    text,
    language_code
):

    output = BytesIO()

    tts = gTTS(
        text=text,
        lang=language_code,
        slow=False
    )

    tts.write_to_fp(
        output
    )

    output.seek(0)

    return output.read()


# ============================================================
# CREATE NARRATION PER SCENE
# ============================================================

def create_scene_narrations(
    scenes,
    language_code
):

    audio_items = []

    total = len(scenes)

    progress = st.progress(
        0,
        text="Preparing scene narration..."
    )

    for index, scene in enumerate(scenes):

        try:

            text = scene.get(
                "narration",
                scene.get(
                    "description",
                    ""
                )
            )

            audio = generate_audio(
                text,
                language_code
            )

            audio_items.append({
                "scene": scene["number"],
                "title": scene["title"],
                "audio": audio,
                "text": text
            })

        except Exception as e:

            st.warning(
                f"Narration failed for Scene "
                f"{scene['number']}: {e}"
            )

        progress.progress(
            (index + 1) / total,
            text=f"Narration {index + 1}/{total}"
        )

    return audio_items


# ============================================================
# CREATE NARRATED VIDEO
# ============================================================

def combine_video_with_audio(
    video_bytes,
    audio_items
):

    if not video_bytes:
        return None

    if not audio_items:
        return video_bytes

    temp_dir = tempfile.mkdtemp(
        prefix="narrated_story_"
    )

    try:

        video_path = os.path.join(
            temp_dir,
            "video.mp4"
        )

        audio_path = os.path.join(
            temp_dir,
            "narration.mp3"
        )

        output_path = os.path.join(
            temp_dir,
            "narrated_movie.mp4"
        )

        with open(
            video_path,
            "wb"
        ) as file:

            file.write(
                video_bytes
            )

        # ----------------------------------------------------
        # Combine all scene audio using FFmpeg concat
        # ----------------------------------------------------

        audio_files = []

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
            ) as file:

                file.write(
                    item["audio"]
                )

            audio_files.append(path)

        concat_audio = os.path.join(
            temp_dir,
            "audio_concat.txt"
        )

        with open(
            concat_audio,
            "w",
            encoding="utf-8"
        ) as file:

            for path in audio_files:

                safe_path = path.replace(
                    "'",
                    "'\\''"
                )

                file.write(
                    f"file '{safe_path}'\n"
                )

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        # ----------------------------------------------------
        # First concatenate audio
        # ----------------------------------------------------

        audio_command = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_audio,
            "-c:a",
            "libmp3lame",
            audio_path
        ]

        audio_result = subprocess.run(
            audio_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300
        )

        if (
            audio_result.returncode != 0
            or not os.path.exists(audio_path)
        ):

            return video_bytes

        # ----------------------------------------------------
        # Combine video + narration
        # ----------------------------------------------------

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

            return video_bytes

        with open(
            output_path,
            "rb"
        ) as file:

            return file.read()

    except Exception:
        return video_bytes

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# ============================================================
# STORY TITLE INPUT
# ============================================================

title = st.text_input(
    "📖 Enter your story title",
    placeholder=(
        "Example: Elara and the Enchanted Forest"
    )
)


# ============================================================
# GENERATE STORY BUTTON
# ============================================================

if st.button(
    "✨ Generate Complete Story",
    type="primary",
    use_container_width=True
):

    if not title.strip():

        st.warning(
            "Please enter a story title first."
        )

        st.stop()

    if not GEMINI_API_KEY and not GROQ_API_KEY:

        st.error(
            "Please configure GEMINI_API_KEY or GROQ_API_KEY "
            "in Streamlit secrets."
        )

        st.stop()

    # --------------------------------------------------------
    # Clear previous project
    # --------------------------------------------------------

    st.session_state.story = ""
    st.session_state.story_title = title
    st.session_state.provider = ""
    st.session_state.scenes = []
    st.session_state.scene_images = []
    st.session_state.scene_videos = []
    st.session_state.scene_audio = []
    st.session_state.poster_bytes = None
    st.session_state.video_bytes = None
    st.session_state.narrated_video_bytes = None
    st.session_state.audio_bytes = None
    st.session_state.generation_complete = False
    st.session_state.media_generation_complete = False

    # --------------------------------------------------------
    # Generate story
    # --------------------------------------------------------

    with st.spinner(
        "✍️ Writing your cinematic story..."
    ):

        try:

            story, provider = generate_story(
                title,
                word_limit
            )

            st.session_state.story = story
            st.session_state.provider = provider

        except Exception as e:

            st.error(
                f"Story generation failed:\n\n{e}"
            )

            st.stop()

    # --------------------------------------------------------
    # Generate scene plan
    # --------------------------------------------------------

    with st.spinner(
        "🎞️ Creating cinematic storyboard..."
    ):

        try:

            scenes = create_scene_plan(
                title,
                st.session_state.story,
                scene_count
            )

            st.session_state.scenes = scenes

            if not scenes:

                st.error(
                    "The AI could not create any scenes."
                )

            else:

                st.session_state.generation_complete = True

        except Exception as e:

            st.error(
                f"Scene planning failed:\n\n{e}"
            )


# ============================================================
# DISPLAY STORY
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
        f"Generated with {st.session_state.provider}"
    )


# ============================================================
# DISPLAY STORYBOARD
# ============================================================

if st.session_state.scenes:

    st.divider()

    st.subheader(
        "🎞️ Cinematic Storyboard"
    )

    for scene in st.session_state.scenes:

        st.markdown(
            f"""
            <div class="scene-card">

                <h3>
                    🎬 Scene {scene["number"]}:
                    {html.escape(scene["title"])}
                </h3>

                <p>
                    <b>What happens:</b><br>
                    {html.escape(scene["description"])}
                </p>

                <p>
                    <b>Characters:</b>
                    {html.escape(scene["characters"])}
                </p>

                <p>
                    <b>Location:</b>
                    {html.escape(scene["location"])}
                </p>

                <p>
                    <b>Objects:</b>
                    {html.escape(scene["objects"])}
                </p>

                <p>
                    <b>Action:</b>
                    {html.escape(scene["action"])}
                </p>

                <p>
                    <b>Lighting:</b>
                    {html.escape(scene["lighting"])}
                </p>

                <small>
                    🖼️ Image:
                    {html.escape(scene["image_query"])}
                    <br>
                    🎥 Video:
                    {html.escape(scene["video_query"])}
                </small>

            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# MEDIA GENERATION
# ============================================================

if st.session_state.story and st.session_state.scenes:

    st.divider()

    st.subheader(
        "🎨 Create Story Media"
    )

    col1, col2, col3 = st.columns(3)

    # ========================================================
    # STORY PHOTO
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

                st.session_state.scene_images = []
                st.session_state.poster_bytes = None

                progress = st.progress(
                    0,
                    text="Finding story-specific images..."
                )

                found_images = []

                total = len(
                    st.session_state.scenes
                )

                for index, scene in enumerate(
                    st.session_state.scenes
                ):

                    query = scene[
                        "image_query"
                    ]

                    # ------------------------------------------------
                    # Retry with a simplified query if necessary
                    # ------------------------------------------------

                    result = pixabay_image(
                        query
                    )

                    if not result:

                        simplified_query = (
                            scene["location"] +
                            " " +
                            scene["action"]
                        )[:100]

                        result = pixabay_image(
                            simplified_query
                        )

                    if result:

                        result["scene"] = (
                            scene["number"]
                        )

                        result["title"] = (
                            scene["title"]
                        )

                        result["description"] = (
                            scene["description"]
                        )

                        found_images.append(
                            result
                        )

                    progress.progress(
                        (index + 1) / total,
                        text=(
                            f"Image {index + 1}/{total}"
                        )
                    )

                    time.sleep(0.15)

                st.session_state.scene_images = (
                    found_images
                )

                if found_images:

                    with st.spinner(
                        "🎨 Building cinematic poster..."
                    ):

                        poster = (
                            create_cinematic_poster(
                                st.session_state.story_title,
                                found_images
                            )
                        )

                    st.session_state.poster_bytes = (
                        poster
                    )

                    st.success(
                        f"Created a cinematic photo using "
                        f"{len(found_images)} scene images."
                    )

                else:

                    st.warning(
                        "No relevant images were found."
                    )


    # ========================================================
    # MULTI-SCENE VIDEO
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

            else:

                st.session_state.scene_videos = []
                st.session_state.video_bytes = None
                st.session_state.narrated_video_bytes = None

                progress = st.progress(
                    0,
                    text="Finding cinematic video clips..."
                )

                found_videos = []

                total = len(
                    st.session_state.scenes
                )

                for index, scene in enumerate(
                    st.session_state.scenes
                ):

                    query = scene[
                        "video_query"
                    ]

                    result = pixabay_video(
                        query
                    )

                    if not result:

                        simplified_query = (
                            scene["location"] +
                            " " +
                            scene["action"]
                        )[:100]

                        result = pixabay_video(
                            simplified_query
                        )

                    if result:

                        result["scene"] = (
                            scene["number"]
                        )

                        result["title"] = (
                            scene["title"]
                        )

                        found_videos.append(
                            result
                        )

                    progress.progress(
                        (index + 1) / total,
                        text=(
                            f"Video {index + 1}/{total}"
                        )
                    )

                    time.sleep(0.2)

                st.session_state.scene_videos = (
                    found_videos
                )

                if found_videos:

                    with st.spinner(
                        "🎬 Downloading and assembling movie..."
                    ):

                        video = (
                            create_multiscene_video(
                                found_videos,
                                clip_duration
                            )
                        )

                    st.session_state.video_bytes = (
                        video
                    )

                    if video:

                        st.success(
                            f"Created a {len(found_videos)}-scene movie."
                        )

                        # --------------------------------------------
                        # Automatically create narration
                        # --------------------------------------------

                        with st.spinner(
                            "🎙️ Generating scene narration..."
                        ):

                            try:

                                scene_audio = (
                                    create_scene_narrations(
                                        st.session_state.scenes,
                                        language[1]
                                    )
                                )

                                st.session_state.scene_audio = (
                                    scene_audio
                                )

                                if scene_audio:

                                    narrated = (
                                        combine_video_with_audio(
                                            video,
                                            scene_audio
                                        )
                                    )

                                    st.session_state.narrated_video_bytes = (
                                        narrated
                                    )

                            except Exception as e:

                                st.warning(
                                    f"Narrated video could not be created: {e}"
                                )

                    else:

                        st.error(
                            "Video clips were found, but "
                            "FFmpeg could not assemble them."
                        )

                else:

                    st.warning(
                        "No relevant video clips were found."
                    )


    # ========================================================
    # FULL STORY NARRATION
    # ========================================================

    with col3:

        if st.button(
            "🔊 Generate Full Narration",
            use_container_width=True
        ):

            with st.spinner(
                "🎙️ Creating complete story narration..."
            ):

                try:

                    audio = generate_audio(
                        st.session_state.story,
                        language[1]
                    )

                    st.session_state.audio_bytes = (
                        audio
                    )

                    st.success(
                        "Complete narration created!"
                    )

                except Exception as e:

                    st.error(
                        f"Narration failed:\n\n{e}"
                    )


# ============================================================
# DISPLAY PHOTO
# ============================================================

if st.session_state.poster_bytes:

    st.divider()

    st.subheader(
        "🖼️ Your Cinematic Story Photo"
    )

    st.image(
        st.session_state.poster_bytes,
        use_container_width=True
    )

    st.download_button(
        "⬇️ Download Story Photo",
        data=st.session_state.poster_bytes,
        file_name="story_cinematic_poster.jpg",
        mime="image/jpeg",
        use_container_width=True
    )

    st.caption(
        "Visual sources: Pixabay • Composite generated by this app"
    )


# ============================================================
# DISPLAY ORIGINAL VIDEO
# ============================================================

if st.session_state.video_bytes:

    st.divider()

    st.subheader(
        "🎥 Your Multi-Scene Movie"
    )

    st.video(
        st.session_state.video_bytes
    )

    st.download_button(
        "⬇️ Download Multi-Scene Video",
        data=st.session_state.video_bytes,
        file_name="story_multi_scene.mp4",
        mime="video/mp4",
        use_container_width=True
    )


# ============================================================
# DISPLAY NARRATED VIDEO
# ============================================================

if st.session_state.narrated_video_bytes:

    st.divider()

    st.subheader(
        "🎬 Your Complete Narrated Movie"
    )

    st.video(
        st.session_state.narrated_video_bytes
    )

    st.download_button(
        "⬇️ Download Narrated Movie",
        data=st.session_state.narrated_video_bytes,
        file_name="story_narrated_movie.mp4",
        mime="video/mp4",
        use_container_width=True
    )

    st.success(
        "Your video now contains the cinematic scenes and narration."
    )


# ============================================================
# DISPLAY FULL NARRATION
# ============================================================

if st.session_state.audio_bytes:

    st.divider()

    st.subheader(
        "🔊 Complete Story Narration"
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
# SCENE-BY-SCENE MEDIA PREVIEW
# ============================================================

if (
    st.session_state.scene_images
    or st.session_state.scene_videos
):

    st.divider()

    st.subheader(
        "🎞️ Scene-by-Scene Media"
    )

    image_lookup = {
        item["scene"]: item
        for item in st.session_state.scene_images
    }

    video_lookup = {
        item["scene"]: item
        for item in st.session_state.scene_videos
    }

    for scene in st.session_state.scenes:

        number = scene["number"]

        with st.expander(
            f"🎬 Scene {number}: {scene['title']}"
        ):

            left, right = st.columns(2)

            with left:

                if number in image_lookup:

                    image_data = image_lookup[
                        number
                    ]

                    image = download_image(
                        image_data["url"]
                    )

                    if image:

                        st.image(
                            image,
                            use_container_width=True
                        )

                    st.caption(
                        f"Image query: "
                        f"{image_data['query']}"
                    )

                else:

                    st.info(
                        "No image found for this scene."
                    )

            with right:

                if number in video_lookup:

                    video_data = video_lookup[
                        number
                    ]

                    try:

                        st.video(
                            video_data["url"]
                        )

                    except Exception:

                        st.write(
                            "Video preview unavailable."
                        )

                    st.caption(
                        f"Video query: "
                        f"{video_data['query']}"
                    )

                else:

                    st.info(
                        "No video found for this scene."
                    )

            st.markdown(
                f"**Narration:** {scene['narration']}"
            )


# ============================================================
# PROJECT INFORMATION
# ============================================================

if st.session_state.story:

    st.divider()

    st.subheader(
        "📊 Project Information"
    )

    info1, info2, info3, info4 = st.columns(4)

    with info1:
        st.metric(
            "Story words",
            len(
                st.session_state.story.split()
            )
        )

    with info2:
        st.metric(
            "Scenes",
            len(
                st.session_state.scenes
            )
        )

    with info3:
        st.metric(
            "Images",
            len(
                st.session_state.scene_images
            )
        )

    with info4:
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
        opacity:0.65;
        padding:15px;
    ">
        🎬 AI Story Studio
        &nbsp; • &nbsp;
        Gemini
        &nbsp; • &nbsp;
        Groq
        &nbsp; • &nbsp;
        Pixabay
        &nbsp; • &nbsp;
        gTTS
        &nbsp; • &nbsp;
        FFmpeg
    </div>
    """,
    unsafe_allow_html=True
)
