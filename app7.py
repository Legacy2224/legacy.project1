import streamlit as st
import requests
import html
import json
import re
import os
import tempfile
import subprocess
import shutil
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from gtts import gTTS

from google import genai
from groq import Groq
import imageio_ffmpeg


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Free AI Story, Photo & Video Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# API KEYS
# ============================================================

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
PIXABAY_API_KEY = st.secrets.get("PIXABAY_API_KEY", "")
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")


# ============================================================
# CLIENTS
# ============================================================

gemini_client = None
groq_client = None

if GEMINI_API_KEY:
    gemini_client = genai.Client(
        api_key=GEMINI_API_KEY
    )

if GROQ_API_KEY:
    groq_client = Groq(
        api_key=GROQ_API_KEY
    )


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "story": "",
    "story_title": "",
    "provider": "",
    "scenes": [],
    "scene_images": [],
    "scene_videos": [],
    "poster_bytes": None,
    "video_bytes": None,
    "audio_bytes": None,
    "video_path": None,
}

for key, value in defaults.items():

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
            <div style="font-size:42px;">🎬</div>
            <h2 style="margin:0;">AI Story Studio</h2>
            <p style="opacity:0.7;">
                Story → Scenes → Photo → Video → Voice
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

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
        "Video scenes",
        min_value=4,
        max_value=8,
        value=6
    )

    clip_duration = st.slider(
        "Seconds per scene",
        min_value=3,
        max_value=8,
        value=5
    )

    st.divider()

    st.info(
        "The free version creates a cinematic composite "
        "poster from story-specific Pixabay images and "
        "builds a multi-scene video from different Pixabay clips."
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
        font-size: 42px;
        font-weight: 800;
        color: {text_color};
        margin-bottom: 5px;
    }}

    .subtitle {{
        color: rgba(255,255,255,0.65);
        font-size: 17px;
        margin-bottom: 25px;
    }}

    .story-card {{
        background: {card_color};
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 28px;
        line-height: 1.85;
        font-size: 17px;
        margin-top: 15px;
    }}

    .scene-card {{
        background: {card_color};
        border-radius: 15px;
        padding: 18px;
        margin-bottom: 15px;
        border-left: 4px solid {primary_color};
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
    '<div class="main-title">🎬 Free AI Story, Photo & Video Studio</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Create an original story and automatically turn it into a '
    'visual multi-scene experience.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# GEMINI TEXT
# ============================================================

def gemini_text(prompt):

    if not gemini_client:
        raise Exception(
            "GEMINI_API_KEY is missing."
        )

    response = gemini_client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    if not response.text:
        raise Exception(
            "Gemini returned an empty response."
        )

    return response.text.strip()


# ============================================================
# GROQ FALLBACK
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
        max_tokens=5000
    )

    return response.choices[0].message.content.strip()


# ============================================================
# STORY GENERATOR
# ============================================================

def generate_story(title, word_limit):

    prompt = f"""
Create an original cinematic story titled:

"{title}"

Requirements:

- Approximately {word_limit} words.
- Strong opening.
- Clear characters.
- Clear locations.
- Interesting conflict.
- Emotional progression.
- Strong ending.
- Highly visual descriptions.
- Every major scene should contain concrete visual elements.
- Include objects, environments, characters, lighting,
  weather, architecture and actions where appropriate.
- Suitable for a general audience.
- Do not explain the writing process.
- Return only the story.
"""

    try:

        return (
            gemini_text(prompt),
            "Gemini Flash Lite"
        )

    except Exception as gemini_error:

        if groq_client:

            try:

                return (
                    groq_text(prompt),
                    "Groq fallback"
                )

            except Exception:
                pass

        raise gemini_error


# ============================================================
# SCENE PLANNER
# ============================================================

def create_scene_plan(
    title,
    story,
    number_of_scenes
):

    prompt = f"""
You are a cinematic storyboard director.

Turn the following story into exactly
{number_of_scenes} visual scenes.

TITLE:
{title}

STORY:
{story[:12000]}

For every scene provide:

SCENE_NUMBER
SCENE_TITLE
DESCRIPTION
IMAGE_QUERY
VIDEO_QUERY

The scene must contain concrete visual details.

Important:

- Do not repeat the same scene.
- Cover the story from beginning to ending.
- Every major character should appear when relevant.
- Important locations should appear.
- Important objects should appear.
- Important actions should appear.
- Include changes in weather, lighting or atmosphere when relevant.
- Queries must be suitable for Pixabay.
- Queries must describe visible things, not abstract emotions.
- Keep image and video queries between 3 and 8 words.
- Do not use quotation marks.
- Avoid words like "concept", "idea", "symbolism".
- Prefer cinematic descriptions such as:
  enchanted forest cottage
  young princess red cloak
  seven miners mountain cottage
  dark castle storm
  magical mirror room

Return ONLY blocks in this exact format:

SCENE|1|Scene title|Scene description|image search query|video search query

SCENE|2|Scene title|Scene description|image search query|video search query

...
"""

    try:

        result = gemini_text(prompt)

    except Exception:

        if groq_client:
            result = groq_text(prompt)
        else:
            raise

    scenes = []

    for line in result.splitlines():

        line = line.strip()

        if not line.startswith("SCENE|"):
            continue

        parts = line.split("|")

        if len(parts) < 6:
            continue

        try:

            scene_number = int(
                parts[1].strip()
            )

        except:
            scene_number = len(scenes) + 1

        scene = {
            "number": scene_number,
            "title": parts[2].strip(),
            "description": parts[3].strip(),
            "image_query": parts[4].strip(),
            "video_query": parts[5].strip()
        }

        scenes.append(scene)

    # Safety fallback
    if not scenes:

        scenes = [{
            "number": i + 1,
            "title": f"Scene {i + 1}",
            "description": story[:500],
            "image_query": title,
            "video_query": title
        } for i in range(number_of_scenes)]

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
        "per_page": 12
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        hits = data.get("hits", [])

        if not hits:
            return None

        # Prefer large landscape images
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
        "per_page": 12
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=20
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

            # Prefer high-quality footage
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
# FONT
# ============================================================

def get_font(size):

    possible_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
    ]

    for font_path in possible_fonts:

        if os.path.exists(font_path):

            try:
                return ImageFont.truetype(
                    font_path,
                    size
                )
            except:
                pass

    return ImageFont.load_default()


# ============================================================
# CINEMATIC POSTER CREATOR
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
                (
                    image,
                    item
                )
            )

    if not valid_images:
        return None

    # --------------------------------------------------------
    # Main image
    # --------------------------------------------------------

    main_image = valid_images[0][0]

    main_image = ImageEnhance.Color(
        main_image
    ).enhance(1.15)

    main_image = ImageEnhance.Contrast(
        main_image
    ).enhance(1.08)

    main_image = ImageOps_fit(
        main_image,
        (width, height)
    )

    canvas.paste(
        main_image,
        (0, 0)
    )

    # Dark overlay
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

    # Bottom gradient-ish bands
    draw.rectangle(
        (0, 620, width, height),
        fill=(0, 0, 0, 150)
    )

    canvas = Image.alpha_composite(
        canvas.convert("RGBA"),
        overlay
    ).convert("RGB")

    # --------------------------------------------------------
    # Smaller scene thumbnails
    # --------------------------------------------------------

    thumb_size = (250, 145)

    start_x = 55
    thumb_y = 725

    for index, (image, item) in enumerate(
        valid_images[1:5]
    ):

        x = start_x + index * 300

        thumb = ImageOps_fit(
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

        scene_font = get_font(16)

        draw.text(
            (
                x + 10,
                thumb_y + 121
            ),
            f"Scene {index + 2}",
            font=scene_font,
            fill="white"
        )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    draw = ImageDraw.Draw(
        canvas
    )

    title_font = get_font(68)

    # Wrap title
    title_text = title

    if len(title_text) > 32:

        words = title_text.split()

        line1 = ""
        line2 = ""

        for word in words:

            if len(line1 + " " + word) < 32:
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
            line1 + "\n" + line2
        )

    draw.text(
        (55, 555),
        title_text,
        font=title_font,
        fill="white",
        stroke_width=2,
        stroke_fill="black"
    )

    # Subtitle
    subtitle_font = get_font(24)

    draw.text(
        (58, 675),
        "A CINEMATIC STORY EXPERIENCE",
        font=subtitle_font,
        fill=(220, 220, 220)
    )

    # Border
    draw.rectangle(
        (15, 15, width - 15, height - 15),
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
# IMAGE FIT HELPER
# ============================================================

def ImageOps_fit(image, size):

    target_width, target_height = size

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
# DOWNLOAD VIDEO
# ============================================================

def download_video(
    url,
    output_path
):

    try:

        response = requests.get(
            url,
            timeout=60,
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

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    return (
        result.returncode == 0
        and os.path.exists(output_path)
    )


# ============================================================
# CREATE MULTI-SCENE VIDEO
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
        # Download + normalize every scene
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
        # FFmpeg concat list
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
            stderr=subprocess.PIPE
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

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# ============================================================
# NARRATION
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
# STORY TITLE INPUT
# ============================================================

title = st.text_input(
    "📖 Enter your story title",
    placeholder=(
        "Example: Snow White and the Seven Dwarfs"
    )
)


# ============================================================
# GENERATE STORY
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

    else:

        # Clear previous project
        st.session_state.story = ""
        st.session_state.scenes = []
        st.session_state.scene_images = []
        st.session_state.scene_videos = []
        st.session_state.poster_bytes = None
        st.session_state.video_bytes = None
        st.session_state.audio_bytes = None

        # ----------------------------------------------------
        # Story
        # ----------------------------------------------------

        with st.spinner(
            "✍️ Writing your cinematic story..."
        ):

            try:

                story, provider = generate_story(
                    title,
                    word_limit
                )

                st.session_state.story = story
                st.session_state.story_title = title
                st.session_state.provider = provider

            except Exception as e:

                st.error(
                    f"Story generation failed:\n\n{e}"
                )

        # ----------------------------------------------------
        # Scene plan
        # ----------------------------------------------------

        if st.session_state.story:

            with st.spinner(
                "🎞️ Breaking story into cinematic scenes..."
            ):

                try:

                    scenes = create_scene_plan(
                        title,
                        st.session_state.story,
                        scene_count
                    )

                    st.session_state.scenes = scenes

                except Exception as e:

                    st.error(
                        f"Scene planning failed:\n\n{e}"
                    )


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
        f"Generated with {st.session_state.provider}"
    )


# ============================================================
# STORYBOARD
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

            <h4>
            🎬 Scene {scene["number"]}: 
            {html.escape(scene["title"])}
            </h4>

            <p>
            {html.escape(scene["description"])}
            </p>

            <small>
            🖼️ {html.escape(scene["image_query"])}
            <br>
            🎥 {html.escape(scene["video_query"])}
            </small>

            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# MEDIA GENERATION
# ============================================================

if st.session_state.story:

    st.divider()

    st.subheader(
        "🎨 Create Story Media"
    )

    col1, col2, col3 = st.columns(3)

    # ========================================================
    # CINEMATIC PHOTO
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

                progress = st.progress(
                    0
                )

                found_images = []

                for index, scene in enumerate(
                    st.session_state.scenes
                ):

                    query = scene[
                        "image_query"
                    ]

                    result = pixabay_image(
                        query
                    )

                    if result:

                        result["scene"] = (
                            scene["number"]
                        )

                        result["title"] = (
                            scene["title"]
                        )

                        found_images.append(
                            result
                        )

                    progress.progress(
                        (
                            index + 1
                        )
                        /
                        len(
                            st.session_state.scenes
                        )
                    )

                st.session_state.scene_images = (
                    found_images
                )

                if found_images:

                    with st.spinner(
                        "🎨 Building cinematic story poster..."
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
                        f"Created a visual story poster "
                        f"from {len(found_images)} story scenes."
                    )

                else:

                    st.warning(
                        "No relevant Pixabay images were found."
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

                progress = st.progress(
                    0
                )

                found_videos = []

                for index, scene in enumerate(
                    st.session_state.scenes
                ):

                    query = scene[
                        "video_query"
                    ]

                    result = pixabay_video(
                        query
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
                        (
                            index + 1
                        )
                        /
                        len(
                            st.session_state.scenes
                        )
                    )

                st.session_state.scene_videos = (
                    found_videos
                )

                if found_videos:

                    with st.spinner(
                        "🎬 Downloading and assembling scenes..."
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
                            f"Created a {len(found_videos)}-scene video."
                        )

                    else:

                        st.error(
                            "The video clips were found, "
                            "but FFmpeg could not assemble them."
                        )

                else:

                    st.warning(
                        "No relevant video clips were found."
                    )


    # ========================================================
    # NARRATION
    # ========================================================

    with col3:

        if st.button(
            "🔊 Generate Narration",
            use_container_width=True
        ):

            with st.spinner(
                "🎙️ Creating narration..."
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
                        "Narration created!"
                    )

                except Exception as e:

                    st.error(
                        f"Narration failed:\n\n{e}"
                    )


# ============================================================
# DISPLAY GENERATED PHOTO
# ============================================================

if st.session_state.poster_bytes:

    st.divider()

    st.subheader(
        "🖼️ Your Story Photo"
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
        "Visual sources: Pixabay • Composite created by this app"
    )


# ============================================================
# DISPLAY MULTI-SCENE VIDEO
# ============================================================

if st.session_state.video_bytes:

    st.divider()

    st.subheader(
        "🎥 Your Multi-Scene Story Video"
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

    st.caption(
        "Video scenes sourced from Pixabay and assembled by this app."
    )


# ============================================================
# DISPLAY NARRATION
# ============================================================

if st.session_state.audio_bytes:

    st.divider()

    st.subheader(
        "🔊 Story Narration"
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
# SCENE MEDIA DETAILS
# ============================================================

if (
    st.session_state.scene_images
    or
    st.session_state.scene_videos
):

    st.divider()

    with st.expander(
        "🔎 See the media selected for each scene"
    ):

        if st.session_state.scene_images:

            st.markdown(
                "### 🖼️ Photo scenes"
            )

            for item in (
                st.session_state.scene_images
            ):

                st.write(
                    f"Scene {item['scene']}: "
                    f"{item['title']} — "
                    f"search: {item['query']}"
                )

        if st.session_state.scene_videos:

            st.markdown(
                "### 🎥 Video scenes"
            )

            for item in (
                st.session_state.scene_videos
            ):

                st.write(
                    f"Scene {item['scene']}: "
                    f"{item['title']} — "
                    f"search: {item['query']}"
                )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    f"""
    <div style="
        text-align:center;
        opacity:0.65;
        padding:15px;
    ">
        🎬 AI Story Studio
        &nbsp; • &nbsp;
        Gemini Flash Lite
        &nbsp; • &nbsp;
        Pixabay
        &nbsp; • &nbsp;
        gTTS
    </div>
    """,
    unsafe_allow_html=True
)
