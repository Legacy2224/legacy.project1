import streamlit as st
import io
import os
import re
import json
import time
import tempfile
import subprocess
from io import BytesIO

from PIL import Image
from gtts import gTTS
from groq import Groq

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Story & Cinematic Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "story": "",
    "story_title": "",
    "scenes": [],
    "scene_images": [],
    "scene_videos": [],
    "scene_audio": [],
    "full_audio": None,
    "final_movie": None,
    "generation_errors": [],
    "project_ready": False,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# API KEYS
# ============================================================

GROQ_API_KEY = ""

HF_TOKEN = ""


try:
    if "GROQ_API_KEY" in st.secrets:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    pass


try:
    if "HF_TOKEN" in st.secrets:
        HF_TOKEN = st.secrets["HF_TOKEN"]
except Exception:
    pass


# ============================================================
# THEME DEFINITIONS
# ============================================================

THEMES = {
    "Dark Midnight": {
        "bg": "#0e1117",
        "card": "#1e232a",
        "text": "#ffffff",
        "accent": "#4A90E2",
        "secondary": "#8ab4f8",
    },

    "Light Elegant": {
        "bg": "#f8f9fa",
        "card": "#ffffff",
        "text": "#212529",
        "accent": "#0d6efd",
        "secondary": "#6c757d",
    },

    "Cyberpunk Neon": {
        "bg": "#050505",
        "card": "#120024",
        "text": "#00ffcc",
        "accent": "#ff007f",
        "secondary": "#00ffff",
    },

    "Enchanted Forest": {
        "bg": "#0b1d13",
        "card": "#132a1c",
        "text": "#e0f2fe",
        "accent": "#22c55e",
        "secondary": "#a3e635",
    },

    "Sunset Glow": {
        "bg": "#1a0b1c",
        "card": "#2d1236",
        "text": "#fdf2f8",
        "accent": "#f43f5e",
        "secondary": "#fb923c",
    },
}


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🎨 Theme & Customization")

theme_choice = st.sidebar.selectbox(
    "Choose Color Theme",
    list(THEMES.keys()),
)

theme = THEMES[theme_choice]


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    f"""
    <style>

    .stApp {{
        background-color: {theme["bg"]};
        color: {theme["text"]};
    }}

    section[data-testid="stSidebar"] {{
        background-color: {theme["card"]};
    }}

    .hero {{
        background-color: {theme["card"]};
        padding: 30px;
        border-radius: 20px;
        border: 1px solid {theme["accent"]};
        margin-bottom: 25px;
    }}

    .story-card {{
        background-color: {theme["card"]};
        padding: 25px;
        border-radius: 15px;
        border-left: 5px solid {theme["accent"]};
        line-height: 1.8;
        margin-bottom: 25px;
    }}

    .scene-card {{
        background-color: {theme["card"]};
        padding: 20px;
        border-radius: 15px;
        border-left: 4px solid {theme["accent"]};
        margin-bottom: 20px;
    }}

    .ai-badge {{
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        border: 1px solid {theme["accent"]};
        margin-bottom: 10px;
        font-weight: bold;
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# API INPUTS
# ============================================================

st.sidebar.divider()

st.sidebar.subheader("🔑 API Configuration")


if GROQ_API_KEY:

    st.sidebar.success(
        "Groq API: ✓ Connected"
    )

else:

    GROQ_API_KEY = st.sidebar.text_input(
        "Groq API Key",
        type="password",
        help="Your Groq API key.",
    )

    if GROQ_API_KEY:
        st.sidebar.success(
            "Groq API: ✓ Loaded"
        )


if HF_TOKEN:

    st.sidebar.success(
        "Hugging Face: ✓ Connected"
    )

else:

    HF_TOKEN = st.sidebar.text_input(
        "Hugging Face Token",
        type="password",
        help="Your Hugging Face access token.",
    )

    if HF_TOKEN:
        st.sidebar.success(
            "Hugging Face: ✓ Loaded"
        )


# ============================================================
# MODEL SETTINGS
# ============================================================

st.sidebar.divider()

st.sidebar.subheader("🧠 Text AI")

TEXT_MODEL = st.sidebar.selectbox(
    "Groq Text Model",
    [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "qwen/qwen3.6-27b",
    ],
    index=0,
)


st.sidebar.subheader("🖼️ Image AI")

IMAGE_MODEL = st.sidebar.text_input(
    "Image Model",
    value="stabilityai/stable-diffusion-xl-base-1.0",
)


st.sidebar.subheader("🎥 AI Video")

VIDEO_MODEL = st.sidebar.text_input(
    "Video Model",
    value="Wan-AI/Wan2.1-T2V-1.3B",
)


VIDEO_PROVIDER = st.sidebar.text_input(
    "HF Video Provider",
    value="fal-ai",
)


# ============================================================
# VIDEO CONTROLS
# ============================================================

video_frames = st.sidebar.slider(
    "Video Frames",
    min_value=17,
    max_value=49,
    value=33,
    step=4,
)

video_steps = st.sidebar.slider(
    "Video Inference Steps",
    min_value=10,
    max_value=40,
    value=25,
    step=5,
)

video_guidance = st.sidebar.slider(
    "Video Guidance",
    min_value=1.0,
    max_value=10.0,
    value=5.0,
    step=0.5,
)


# ============================================================
# STORY SETTINGS
# ============================================================

st.sidebar.divider()

st.sidebar.subheader("📖 Story Settings")

scene_count = st.sidebar.slider(
    "Number of Scenes",
    min_value=3,
    max_value=10,
    value=5,
)

story_words = st.sidebar.slider(
    "Story Word Count",
    min_value=300,
    max_value=1800,
    value=700,
    step=100,
)


language_option = st.sidebar.selectbox(
    "Narration Language",
    [
        ("English", "en"),
        ("Hindi", "hi"),
        ("Spanish", "es"),
        ("French", "fr"),
        ("German", "de"),
    ],
    format_func=lambda x: x[0],
)


# ============================================================
# CLIENTS
# ============================================================

groq_client = None

if GROQ_API_KEY:

    try:

        groq_client = Groq(
            api_key=GROQ_API_KEY
        )

    except Exception as exc:

        st.sidebar.error(
            f"Groq initialization failed: {exc}"
        )


hf_client = None

if HF_TOKEN and InferenceClient:

    try:

        hf_client = InferenceClient(
            provider=VIDEO_PROVIDER,
            api_key=HF_TOKEN,
        )

    except Exception as exc:

        st.sidebar.error(
            f"Hugging Face initialization failed: {exc}"
        )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">

        <h1>🎬 AI Story & Cinematic Studio</h1>

        <p>
        Transform an idea into a complete cinematic AI movie.
        </p>

        <p>
        ✍️ Story →
        🎬 Storyboard →
        🖼️ AI Images →
        🤖 AI Video →
        🎙️ Narration →
        🎞️ Final Movie
        </p>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return str(value).strip()


def safe_int(value, default=0):

    try:
        return int(value)

    except Exception:
        return default


def extract_json_array(text):

    if not text:
        raise ValueError(
            "AI returned an empty response."
        )

    text = text.strip()

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"```",
        "",
        text,
    )

    start = text.find("[")

    end = text.rfind("]")

    if start == -1 or end == -1:

        raise ValueError(
            "AI response did not contain a JSON array."
        )

    json_text = text[
        start:end + 1
    ]

    return json.loads(
        json_text
    )


# ============================================================
# GROQ GENERATOR
# ============================================================

def generate_with_groq(
    prompt,
    max_tokens=6000,
    temperature=0.7,
):

    if not GROQ_API_KEY:

        raise RuntimeError(
            "GROQ_API_KEY is missing."
        )

    if groq_client is None:

        raise RuntimeError(
            "Groq client could not be initialized."
        )


    # --------------------------------------------------------
    # CURRENT MODELS
    # --------------------------------------------------------

    models = [
        TEXT_MODEL,
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "qwen/qwen3.6-27b",
    ]


    # Remove duplicates while preserving order.

    unique_models = []

    for model in models:

        if model not in unique_models:

            unique_models.append(
                model
            )


    last_error = None


    for model in unique_models:

        try:

            response = (
                groq_client
                .chat
                .completions
                .create(

                    model=model,

                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],

                    max_tokens=max_tokens,

                    temperature=temperature,
                )
            )


            if (
                response
                and response.choices
                and response.choices[0].message
                and response.choices[0].message.content
            ):

                return (
                    response
                    .choices[0]
                    .message
                    .content
                    .strip()
                )


        except Exception as exc:

            last_error = exc

            continue


    raise RuntimeError(
        "Groq generation failed.\n\n"
        f"Last error: {last_error}"
    )


# ============================================================
# STORY GENERATION
# ============================================================

def generate_story(
    title,
    word_count,
):

    prompt = f"""
You are a professional cinematic storyteller.

Create a completely original story.

TITLE:
{title}

TARGET LENGTH:
Approximately {word_count} words.

The story will later become an AI-generated movie.

Therefore make the story extremely visual.

Include:

- Main character
- Character appearance
- Supporting characters
- Locations
- Important objects
- Physical actions
- Weather
- Lighting
- Environmental movement
- Conflict
- Escalation
- Major turning point
- Climax
- Resolution
- Ending

Characters must remain visually consistent.

Every major event should be physically visible.

Avoid abstract descriptions.

Write clear cinematic prose.

Do not include explanations.

Return ONLY the story.
"""

    return generate_with_groq(
        prompt,
        max_tokens=max(
            3000,
            word_count * 3,
        ),
        temperature=0.8,
    )


# ============================================================
# SCENE PLANNER
# ============================================================

def generate_scene_plan(
    title,
    story,
    number_of_scenes,
):

    prompt = f"""
You are a professional film director,
cinematographer,
storyboard artist,
and AI video prompt engineer.

Turn this complete story into EXACTLY
{number_of_scenes} cinematic scenes.

TITLE:

{title}

STORY:

{story}

IMPORTANT:

Do NOT simply split the story by sentences.

Create meaningful cinematic scenes.

The complete story must be covered.

Each scene must contain:

1. number
2. title
3. description
4. characters
5. location
6. objects
7. action
8. lighting
9. camera
10. image_prompt
11. video_prompt
12. narration

CHARACTER CONSISTENCY:

Describe recurring characters consistently.

IMAGE PROMPT:

Describe exactly what the AI image generator
should see.

VIDEO PROMPT:

Describe actual movement.

Include:

- character movement
- camera movement
- environmental movement
- object movement
- facial expressions
- lighting
- atmosphere

Do not use:

- text
- subtitles
- captions
- logos
- watermarks
- abstract concepts

The video prompt must describe a scene that can
actually be generated as moving video.

Return ONLY valid JSON.

Use exactly this structure:

[
  {{
    "number": 1,
    "title": "Scene title",
    "description": "Scene description",
    "characters": "Characters",
    "location": "Location",
    "objects": "Objects",
    "action": "Physical action",
    "lighting": "Lighting",
    "camera": "Camera movement",
    "image_prompt": "Detailed image prompt",
    "video_prompt": "Detailed AI video prompt",
    "narration": "Narration"
  }}
]
"""

    raw = generate_with_groq(
        prompt,
        max_tokens=12000,
        temperature=0.4,
    )

    data = extract_json_array(
        raw
    )


    if not isinstance(
        data,
        list,
    ):

        raise ValueError(
            "Scene planner did not return a list."
        )


    scenes = []


    for index, item in enumerate(data):

        if not isinstance(
            item,
            dict,
        ):

            continue


        number = index + 1


        scene = {

            "number": number,

            "title": clean_text(
                item.get(
                    "title",
                    f"Scene {number}",
                )
            ),

            "description": clean_text(
                item.get(
                    "description",
                    "",
                )
            ),

            "characters": clean_text(
                item.get(
                    "characters",
                    "",
                )
            ),

            "location": clean_text(
                item.get(
                    "location",
                    "",
                )
            ),

            "objects": clean_text(
                item.get(
                    "objects",
                    "",
                )
            ),

            "action": clean_text(
                item.get(
                    "action",
                    "",
                )
            ),

            "lighting": clean_text(
                item.get(
                    "lighting",
                    "",
                )
            ),

            "camera": clean_text(
                item.get(
                    "camera",
                    "",
                )
            ),

            "image_prompt": clean_text(
                item.get(
                    "image_prompt",
                    "",
                )
            ),

            "video_prompt": clean_text(
                item.get(
                    "video_prompt",
                    "",
                )
            ),

            "narration": clean_text(
                item.get(
                    "narration",
                    "",
                )
            ),
        }


        # ----------------------------------------------------
        # Automatic prompt repair
        # ----------------------------------------------------

        if not scene["image_prompt"]:

            scene["image_prompt"] = f"""
Cinematic movie still.

{scene["description"]}

Characters:
{scene["characters"]}

Location:
{scene["location"]}

Objects:
{scene["objects"]}

Action:
{scene["action"]}

Lighting:
{scene["lighting"]}

Professional cinematic photography,
detailed environment,
dramatic composition,
natural faces,
natural hands,
high detail,
widescreen movie frame.

No text.
No subtitles.
No logos.
No watermark.
"""


        if not scene["video_prompt"]:

            scene["video_prompt"] = f"""
Cinematic AI-generated movie scene.

{scene["description"]}

Characters:
{scene["characters"]}

Location:
{scene["location"]}

Objects:
{scene["objects"]}

Physical action:
{scene["action"]}

Camera:
{scene["camera"]}

Lighting:
{scene["lighting"]}

Characters move naturally.
The environment moves naturally.
Objects move naturally.
Smooth cinematic camera motion.
Professional fantasy movie cinematography.

No text.
No subtitles.
No logos.
No watermark.
"""


        if not scene["narration"]:

            scene["narration"] = (
                scene["description"]
            )


        scenes.append(
            scene
        )


    if not scenes:

        raise ValueError(
            "No valid scenes were created."
        )


    # Make sure the requested number is respected.

    scenes = scenes[
        :number_of_scenes
    ]


    return scenes


# ============================================================
# IMAGE GENERATOR
# ============================================================

def generate_ai_image(
    prompt
):

    if hf_client is None:

        return None, (
            "Hugging Face client is unavailable."
        )


    final_prompt = f"""
Create a cinematic AI-generated image.

{prompt}

Visual style:

cinematic fantasy movie,
high detail,
professional cinematography,
realistic lighting,
beautiful composition,
detailed environment,
natural character anatomy,
natural hands,
expressive faces,
depth of field,
atmospheric perspective,
movie-quality frame,
widescreen composition.

Absolutely no:

text,
captions,
subtitles,
logos,
watermarks,
UI elements.
"""


    try:

        image = hf_client.text_to_image(
            final_prompt,
            model=IMAGE_MODEL,
        )


        if image is None:

            return None, (
                "Image provider returned no image."
            )


        return image, None


    except Exception as exc:

        return None, str(exc)


# ============================================================
# VIDEO GENERATOR
# ============================================================

def generate_ai_video(
    prompt,
    seed,
):

    if hf_client is None:

        raise RuntimeError(
            "Hugging Face client is unavailable."
        )


    final_prompt = f"""
Generate a NEW AI-GENERATED cinematic video.

SCENE:

{prompt}

STYLE:

cinematic fantasy movie,
high-quality AI video,
natural character movement,
realistic environmental motion,
detailed faces,
realistic clothing movement,
atmospheric depth,
volumetric lighting,
professional cinematography,
smooth camera movement,
film-quality composition.

The scene must contain real motion.

Characters must move.

The environment must move.

The camera must move.

Do not create a static photograph.

Do not use stock footage.

Do not use existing movie footage.

Do not use human-uploaded footage.

Do not include:

text,
captions,
subtitles,
logos,
watermarks,
UI,
static slideshow,
still image.
"""


    negative_prompt = (
        "text, subtitles, captions, "
        "logos, watermark, UI, "
        "static image, slideshow, "
        "stock footage, existing footage, "
        "deformed anatomy, extra fingers, "
        "duplicate people, distorted face, "
        "flickering, blurry, low quality"
    )


    try:

        video = hf_client.text_to_video(

            final_prompt,

            model=VIDEO_MODEL,

            guidance_scale=video_guidance,

            negative_prompt=negative_prompt,

            num_frames=video_frames,

            num_inference_steps=video_steps,

            seed=seed,
        )


        if video is None:

            raise RuntimeError(
                "AI video provider returned no video."
            )


        return video


    except TypeError:

        # ----------------------------------------------------
        # Compatibility fallback.
        #
        # Different HF providers expose slightly
        # different optional arguments.
        # ----------------------------------------------------

        video = hf_client.text_to_video(

            final_prompt,

            model=VIDEO_MODEL,

        )


        if video is None:

            raise RuntimeError(
                "AI video provider returned no video."
            )


        return video


# ============================================================
# IMAGE PIPELINE
# ============================================================

def generate_all_images(
    scenes
):

    results = []

    total = len(
        scenes
    )


    progress = st.progress(
        0,
        text="Starting AI image generation...",
    )


    for index, scene in enumerate(
        scenes
    ):

        number = safe_int(
            scene.get(
                "number"
            ),
            index + 1,
        )


        progress.progress(
            index / total,
            text=(
                f"Generating AI image "
                f"for Scene {number}/{total}"
            ),
        )


        image, error = generate_ai_image(
            scene.get(
                "image_prompt",
                "",
            )
        )


        results.append({

            "scene": number,

            "title": scene.get(
                "title",
                f"Scene {number}",
            ),

            "image": image,

            "error": error,

        })


        if error:

            st.session_state.generation_errors.append(
                f"Scene {number} image: {error}"
            )


    progress.progress(
        1.0,
        text="AI images completed ✓",
    )


    return results


# ============================================================
# VIDEO PIPELINE
# ============================================================

def generate_all_videos(
    scenes
):

    results = []

    total = len(
        scenes
    )


    progress = st.progress(
        0,
        text="Starting AI video generation...",
    )


    for index, scene in enumerate(
        scenes
    ):

        number = safe_int(
            scene.get(
                "number"
            ),
            index + 1,
        )


        title = scene.get(
            "title",
            f"Scene {number}",
        )


        progress.progress(
            index / total,
            text=(
                f"AI-generating video "
                f"for Scene {number}/{total}"
            ),
        )


        try:

            seed = (
                int(time.time())
                + number * 1009
            )


            video = generate_ai_video(

                scene.get(
                    "video_prompt",
                    "",
                ),

                seed,
            )


            results.append({

                "scene": number,

                "title": title,

                "video": video,

                "prompt": scene.get(
                    "video_prompt",
                    "",
                ),

                "error": None,

                "source": "AI",

            })


        except Exception as exc:

            error = str(
                exc
            )


            results.append({

                "scene": number,

                "title": title,

                "video": None,

                "prompt": scene.get(
                    "video_prompt",
                    "",
                ),

                "error": error,

                "source": "AI",

            })


            st.session_state.generation_errors.append(
                f"Scene {number} video: {error}"
            )


        progress.progress(
            (index + 1) / total,
            text=(
                f"AI video progress: "
                f"{index + 1}/{total}"
            ),
        )


    return results


# ============================================================
# NARRATION
# ============================================================

def generate_all_narration(
    scenes,
    language,
):

    results = []

    total = len(
        scenes
    )


    progress = st.progress(
        0,
        text="Creating narration...",
    )


    for index, scene in enumerate(
        scenes
    ):

        number = safe_int(
            scene.get(
                "number"
            ),
            index + 1,
        )


        text = clean_text(
            scene.get(
                "narration",
                scene.get(
                    "description",
                    "",
                ),
            )
        )


        try:

            buffer = BytesIO()


            tts = gTTS(
                text=text,
                lang=language,
                slow=False,
            )


            tts.write_to_fp(
                buffer
            )


            results.append({

                "scene": number,

                "title": scene.get(
                    "title",
                    "",
                ),

                "text": text,

                "audio": buffer.getvalue(),

            })


        except Exception as exc:

            st.session_state.generation_errors.append(
                f"Scene {number} narration: {exc}"
            )


        progress.progress(
            (index + 1) / total,
            text=(
                f"Narration "
                f"{index + 1}/{total}"
            ),
        )


    return results


# ============================================================
# FFMPEG
# ============================================================

def get_ffmpeg():

    if imageio_ffmpeg is None:

        raise RuntimeError(
            "imageio-ffmpeg is not installed."
        )


    try:

        return imageio_ffmpeg.get_ffmpeg_exe()

    except Exception as exc:

        raise RuntimeError(
            f"FFmpeg error: {exc}"
        )


# ============================================================
# TEMP FILE
# ============================================================

def write_temp_file(
    directory,
    filename,
    data,
):

    path = os.path.join(
        directory,
        filename,
    )


    with open(
        path,
        "wb",
    ) as file:

        file.write(
            data
        )


    return path


# ============================================================
# CLEAN TEMP DIRECTORY
# ============================================================

def cleanup_directory(
    directory
):

    try:

        if not os.path.exists(
            directory
        ):

            return


        for filename in os.listdir(
            directory
        ):

            path = os.path.join(
                directory,
                filename,
            )


            if os.path.isfile(
                path
            ):

                os.remove(
                    path
                )


        os.rmdir(
            directory
        )


    except Exception:

        pass


# ============================================================
# COMBINE VIDEOS
# ============================================================

def combine_ai_videos(
    video_items
):

    usable = []


    # --------------------------------------------------------
    # SAFE DATA VALIDATION
    #
    # This specifically prevents:
    #
    # x["scene"]
    #
    # errors.
    # --------------------------------------------------------

    for item in video_items:

        if not isinstance(
            item,
            dict,
        ):

            continue


        if "scene" not in item:

            continue


        scene_number = safe_int(
            item.get(
                "scene"
            ),
            0,
        )


        video = item.get(
            "video"
        )


        if scene_number <= 0:

            continue


        if not video:

            continue


        usable.append(
            (
                scene_number,
                video,
            )
        )


    if not usable:

        raise RuntimeError(
            "No valid AI videos are available."
        )


    usable.sort(
        key=lambda x: x[0]
    )


    ffmpeg = get_ffmpeg()


    temp_dir = tempfile.mkdtemp(
        prefix="ai_movie_"
    )


    try:

        scene_files = []


        for scene_number, video in usable:

            path = write_temp_file(

                temp_dir,

                f"scene_{scene_number}.mp4",

                video,
            )


            scene_files.append(
                path
            )


        concat_file = os.path.join(
            temp_dir,
            "concat.txt",
        )


        with open(
            concat_file,
            "w",
            encoding="utf-8",
        ) as file:

            for path in scene_files:

                safe_path = path.replace(
                    "'",
                    "'\\''",
                )

                file.write(
                    f"file '{safe_path}'\n"
                )


        output_file = os.path.join(
            temp_dir,
            "final_movie.mp4",
        )


        # ----------------------------------------------------
        # Try direct stream copy first.
        # ----------------------------------------------------

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

            "-movflags",
            "+faststart",

            output_file,

        ]


        result = subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            timeout=900,
        )


        # ----------------------------------------------------
        # Fallback to re-encoding.
        # ----------------------------------------------------

        if (

            result.returncode != 0

            or not os.path.exists(
                output_file
            )

        ):

            command = [

                ffmpeg,

                "-y",

                "-f",
                "concat",

                "-safe",
                "0",

                "-i",
                concat_file,

                "-c:v",
                "libx264",

                "-preset",
                "veryfast",

                "-pix_fmt",
                "yuv420p",

                "-movflags",
                "+faststart",

                output_file,

            ]


            result = subprocess.run(

                command,

                stdout=subprocess.PIPE,

                stderr=subprocess.PIPE,

                timeout=900,
            )


        if (

            result.returncode != 0

            or not os.path.exists(
                output_file
            )

        ):

            error_text = (
                result
                .stderr
                .decode(
                    "utf-8",
                    errors="ignore",
                )
            )


            raise RuntimeError(
                "FFmpeg could not combine "
                "the AI videos.\n\n"
                + error_text[-3000:]
            )


        with open(
            output_file,
            "rb",
        ) as file:

            final_bytes = file.read()


        return final_bytes


    finally:

        cleanup_directory(
            temp_dir
        )


# ============================================================
# COMBINE AUDIO
# ============================================================

def combine_audio(
    audio_items
):

    usable = []


    for item in audio_items:

        if not isinstance(
            item,
            dict,
        ):

            continue


        scene = safe_int(
            item.get(
                "scene"
            ),
            0,
        )


        audio = item.get(
            "audio"
        )


        if scene <= 0 or not audio:

            continue


        usable.append(
            (
                scene,
                audio,
            )
        )


    if not usable:

        return None


    usable.sort(
        key=lambda x: x[0]
    )


    ffmpeg = get_ffmpeg()


    temp_dir = tempfile.mkdtemp(
        prefix="ai_audio_"
    )


    try:

        audio_files = []


        for scene, audio in usable:

            path = write_temp_file(

                temp_dir,

                f"scene_{scene}.mp3",

                audio,
            )


            audio_files.append(
                path
            )


        concat_file = os.path.join(
            temp_dir,
            "audio.txt",
        )


        with open(
            concat_file,
            "w",
            encoding="utf-8",
        ) as file:

            for path in audio_files:

                safe_path = path.replace(
                    "'",
                    "'\\''",
                )

                file.write(
                    f"file '{safe_path}'\n"
                )


        output_file = os.path.join(
            temp_dir,
            "complete_narration.mp3",
        )


        command = [

            ffmpeg,

            "-y",

            "-f",
            "concat",

            "-safe",
            "0",

            "-i",
            concat_file,

            "-c:a",
            "libmp3lame",

            output_file,

        ]


        result = subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            timeout=900,
        )


        if (

            result.returncode != 0

            or not os.path.exists(
                output_file
            )

        ):

            return None


        with open(
            output_file,
            "rb",
        ) as file:

            return file.read()


    finally:

        cleanup_directory(
            temp_dir
        )


# ============================================================
# ADD NARRATION TO MOVIE
# ============================================================

def add_narration_to_movie(
    movie_bytes,
    audio_bytes,
):

    if not movie_bytes:

        return None


    if not audio_bytes:

        return movie_bytes


    ffmpeg = get_ffmpeg()


    temp_dir = tempfile.mkdtemp(
        prefix="narrated_movie_"
    )


    try:

        movie_path = write_temp_file(

            temp_dir,

            "movie.mp4",

            movie_bytes,
        )


        audio_path = write_temp_file(

            temp_dir,

            "narration.mp3",

            audio_bytes,
        )


        output_path = os.path.join(
            temp_dir,
            "final_narrated_movie.mp4",
        )


        command = [

            ffmpeg,

            "-y",

            "-i",
            movie_path,

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

            "-movflags",
            "+faststart",

            output_path,

        ]


        result = subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            timeout=900,
        )


        if (

            result.returncode != 0

            or not os.path.exists(
                output_path
            )

        ):

            return movie_bytes


        with open(
            output_path,
            "rb",
        ) as file:

            return file.read()


    finally:

        cleanup_directory(
            temp_dir
        )


# ============================================================
# MAIN INPUT
# ============================================================

story_title = st.text_input(
    "📖 Enter Story Topic or Title",
    value="Elara and the Secret Forest",
)


output_mode = st.radio(

    "Choose Output Format",

    [
        "📖 Story + AI Images",
        "🎬 Complete AI Movie",
    ],

    horizontal=True,
)


generate_button = st.button(

    "🚀 Generate Cinematic Project",

    type="primary",

    use_container_width=True,
)


# ============================================================
# GENERATION
# ============================================================

if generate_button:

    # --------------------------------------------------------
    # API CHECK
    # --------------------------------------------------------

    if not GROQ_API_KEY:

        st.error(
            "❌ GROQ_API_KEY is missing."
        )

        st.info(
            "Add your Groq API key to Streamlit Secrets."
        )

        st.stop()


    if not HF_TOKEN:

        st.error(
            "❌ HF_TOKEN is missing."
        )

        st.info(
            "Add your Hugging Face token to Streamlit Secrets."
        )

        st.stop()


    if groq_client is None:

        st.error(
            "Groq client is unavailable."
        )

        st.stop()


    if hf_client is None:

        st.error(
            "Hugging Face client is unavailable."
        )

        st.stop()


    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    st.session_state.story = ""

    st.session_state.story_title = (
        story_title
    )

    st.session_state.scenes = []

    st.session_state.scene_images = []

    st.session_state.scene_videos = []

    st.session_state.scene_audio = []

    st.session_state.full_audio = None

    st.session_state.final_movie = None

    st.session_state.generation_errors = []

    st.session_state.project_ready = False


    # ========================================================
    # STEP 1 — STORY
    # ========================================================

    st.header(
        "1️⃣ AI Story Generation"
    )


    try:

        story_progress = st.progress(
            0,
            text="AI is writing your story...",
        )


        story = generate_story(

            story_title,

            story_words,
        )


        st.session_state.story = story


        story_progress.progress(
            1.0,
            text="Story completed ✓",
        )


    except Exception as exc:

        st.error(
            f"Story generation failed: {exc}"
        )

        st.stop()


    # ========================================================
    # STEP 2 — STORYBOARD
    # ========================================================

    st.header(
        "2️⃣ Cinematic Storyboard"
    )


    try:

        storyboard_progress = st.progress(
            0,
            text="AI director is creating scenes...",
        )


        scenes = generate_scene_plan(

            story_title,

            story,

            scene_count,
        )


        st.session_state.scenes = scenes


        storyboard_progress.progress(
            1.0,
            text=(
                f"{len(scenes)} scenes created ✓"
            ),
        )


    except Exception as exc:

        st.error(
            f"Storyboard generation failed: {exc}"
        )

        st.stop()


    # ========================================================
    # STEP 3 — IMAGES
    # ========================================================

    st.header(
        "3️⃣ AI Scene Images"
    )


    st.session_state.scene_images = (
        generate_all_images(
            scenes
        )
    )


    # ========================================================
    # STORY + IMAGES ONLY
    # ========================================================

    if output_mode == "📖 Story + AI Images":

        st.success(
            "🎉 Story and AI scene images are ready."
        )


        st.session_state.project_ready = True


    # ========================================================
    # COMPLETE MOVIE
    # ========================================================

    else:

        # ====================================================
        # STEP 4 — AI VIDEO
        # ====================================================

        st.header(
            "4️⃣ AI Video Generation"
        )


        st.info(
            """
            🤖 Every scene is being generated as a
            NEW AI video.

            No Pixabay.

            No stock footage.

            No human-uploaded footage.

            No existing movie footage.
            """
        )


        st.session_state.scene_videos = (
            generate_all_videos(
                scenes
            )
        )


        # ====================================================
        # STEP 5 — NARRATION
        # ====================================================

        st.header(
            "5️⃣ AI Narration"
        )


        st.session_state.scene_audio = (
            generate_all_narration(

                scenes,

                language_option[1],
            )
        )


        # ====================================================
        # STEP 6 — JOIN VIDEO
        # ====================================================

        st.header(
            "6️⃣ Creating Complete Movie"
        )


        valid_video_count = 0


        for item in st.session_state.scene_videos:

            if not isinstance(
                item,
                dict,
            ):

                continue


            if item.get(
                "video"
            ):

                valid_video_count += 1


        if valid_video_count == 0:

            st.error(
                """
                ❌ No AI video was returned.

                This normally means the selected
                Hugging Face video provider/model
                is unavailable for your account.

                Check the Hugging Face token,
                provider and model.
                """
            )


        else:

            st.write(
                f"AI videos generated: "
                f"**{valid_video_count}/{len(scenes)}**"
            )


            try:

                movie_progress = st.progress(
                    0,
                    text="Joining AI scenes...",
                )


                movie = combine_ai_videos(

                    st.session_state.scene_videos

                )


                movie_progress.progress(
                    1.0,
                    text="Movie assembled ✓",
                )


                st.session_state.final_movie = movie


            except Exception as exc:

                st.error(
                    f"Movie assembly failed: {exc}"
                )


                st.session_state.generation_errors.append(
                    f"Movie assembly: {exc}"
                )


        # ====================================================
        # STEP 7 — JOIN AUDIO
        # ====================================================

        st.header(
            "7️⃣ Combining Narration"
        )


        try:

            full_audio = combine_audio(

                st.session_state.scene_audio

            )


            st.session_state.full_audio = (
                full_audio
            )


        except Exception as exc:

            st.session_state.generation_errors.append(
                f"Audio assembly: {exc}"
            )


        # ====================================================
        # STEP 8 — NARRATED MOVIE
        # ====================================================

        if (

            st.session_state.final_movie

            and

            st.session_state.full_audio

        ):

            st.header(
                "8️⃣ Adding Narration to Movie"
            )


            try:

                final_movie = (
                    add_narration_to_movie(

                        st.session_state.final_movie,

                        st.session_state.full_audio,

                    )
                )


                if final_movie:

                    st.session_state.final_movie = (
                        final_movie
                    )


                st.success(
                    "🎬 Final narrated movie created ✓"
                )


            except Exception as exc:

                st.session_state.generation_errors.append(
                    f"Narrated movie: {exc}"
                )


        st.session_state.project_ready = True


# ============================================================
# DISPLAY STORY
# ============================================================

if st.session_state.story:

    st.divider()


    st.header(
        f"📖 {st.session_state.story_title}"
    )


    story_html = (
        st.session_state.story
        .replace(
            "\n",
            "<br>",
        )
    )


    st.markdown(

        f"""
        <div class="story-card">
        {story_html}
        </div>
        """,

        unsafe_allow_html=True,
    )


    st.download_button(

        "⬇️ Download Story",

        data=st.session_state.story,

        file_name="story.txt",

        mime="text/plain",

        key="download_story",

    )


# ============================================================
# DISPLAY SCENES
# ============================================================

if st.session_state.scenes:

    st.divider()


    st.header(
        "🎬 Cinematic Scenes"
    )


    # --------------------------------------------------------
    # SAFE LOOKUP TABLES
    # --------------------------------------------------------

    image_lookup = {}

    for item in st.session_state.scene_images:

        if not isinstance(
            item,
            dict,
        ):

            continue


        scene_number = safe_int(
            item.get(
                "scene"
            ),
            0,
        )


        if scene_number <= 0:

            continue


        image_lookup[
            scene_number
        ] = item


    video_lookup = {}

    for item in st.session_state.scene_videos:

        if not isinstance(
            item,
            dict,
        ):

            continue


        scene_number = safe_int(
            item.get(
                "scene"
            ),
            0,
        )


        if scene_number <= 0:

            continue


        video_lookup[
            scene_number
        ] = item


    audio_lookup = {}

    for item in st.session_state.scene_audio:

        if not isinstance(
            item,
            dict,
        ):

            continue


        scene_number = safe_int(
            item.get(
                "scene"
            ),
            0,
        )


        if scene_number <= 0:

            continue


        audio_lookup[
            scene_number
        ] = item


    # --------------------------------------------------------
    # RENDER EVERY SCENE
    # --------------------------------------------------------

    for index, scene in enumerate(
        st.session_state.scenes
    ):

        if not isinstance(
            scene,
            dict,
        ):

            continue


        number = safe_int(
            scene.get(
                "number"
            ),
            index + 1,
        )


        title = scene.get(
            "title",
            f"Scene {number}",
        )


        with st.expander(
            f"🎬 Scene {number}: {title}",
            expanded=False,
        ):

            st.markdown(
                '<div class="scene-card">',
                unsafe_allow_html=True,
            )


            st.markdown(
                f"### {title}"
            )


            st.markdown(
                f"""
                **📖 Description**

                {scene.get("description", "")}
                """
            )


            st.markdown(
                f"""
                **👤 Characters**

                {scene.get("characters", "")}
                """
            )


            st.markdown(
                f"""
                **📍 Location**

                {scene.get("location", "")}
                """
            )


            st.markdown(
                f"""
                **🎭 Action**

                {scene.get("action", "")}
                """
            )


            st.markdown(
                f"""
                **💡 Lighting**

                {scene.get("lighting", "")}
                """
            )


            st.markdown(
                f"""
                **📷 Camera**

                {scene.get("camera", "")}
                """
            )


            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )


            # =================================================
            # MEDIA COLUMNS
            # =================================================

            col_image, col_video = st.columns(
                2
            )


            # -------------------------------------------------
            # IMAGE
            # -------------------------------------------------

            with col_image:

                st.subheader(
                    "🖼️ AI Image"
                )


                image_item = image_lookup.get(
                    number
                )


                if (

                    image_item

                    and

                    image_item.get(
                        "image"
                    )

                ):

                    image = image_item[
                        "image"
                    ]


                    st.image(
                        image,
                        use_container_width=True,
                    )


                    image_buffer = BytesIO()


                    image.save(
                        image_buffer,
                        format="PNG",
                    )


                    st.download_button(

                        f"⬇️ Download Scene {number} Image",

                        data=image_buffer.getvalue(),

                        file_name=(
                            f"scene_{number}.png"
                        ),

                        mime="image/png",

                        key=(
                            f"download_image_{number}"
                        ),

                    )


                else:

                    st.warning(
                        "AI image was not generated."
                    )


            # -------------------------------------------------
            # VIDEO
            # -------------------------------------------------

            with col_video:

                st.subheader(
                    "🤖 AI Video"
                )


                st.markdown(
                    '<div class="ai-badge">'
                    '🤖 100% AI GENERATED'
                    '</div>',
                    unsafe_allow_html=True,
                )


                video_item = video_lookup.get(
                    number
                )


                if (

                    video_item

                    and

                    video_item.get(
                        "video"
                    )

                ):

                    video_bytes = (
                        video_item[
                            "video"
                        ]
                    )


                    st.video(
                        video_bytes
                    )


                    st.download_button(

                        f"⬇️ Download Scene {number} Video",

                        data=video_bytes,

                        file_name=(
                            f"ai_scene_{number}.mp4"
                        ),

                        mime="video/mp4",

                        key=(
                            f"download_video_{number}"
                        ),

                    )


                elif video_item:

                    st.error(
                        video_item.get(
                            "error",
                            "AI video generation failed.",
                        )
                    )


                else:

                    st.warning(
                        "AI video was not generated."
                    )


            # =================================================
            # VIDEO PROMPT
            # =================================================

            st.divider()


            st.subheader(
                "🎥 AI Video Prompt"
            )


            st.code(

                scene.get(
                    "video_prompt",
                    "",
                ),

                language="text",

            )


            # =================================================
            # NARRATION
            # =================================================

            st.subheader(
                "🎙️ Narration"
            )


            narration = scene.get(
                "narration",
                "",
            )


            st.info(
                narration
            )


            audio_item = audio_lookup.get(
                number
            )


            if (

                audio_item

                and

                audio_item.get(
                    "audio"
                )

            ):

                audio_bytes = audio_item[
                    "audio"
                ]


                st.audio(
                    audio_bytes,
                    format="audio/mp3",
                )


                st.download_button(

                    f"⬇️ Download Scene {number} Narration",

                    data=audio_bytes,

                    file_name=(
                        f"scene_{number}_narration.mp3"
                    ),

                    mime="audio/mp3",

                    key=(
                        f"download_narration_{number}"
                    ),

                )


# ============================================================
# FINAL MOVIE
# ============================================================

if st.session_state.final_movie:

    st.divider()


    st.header(
        "🎬 Complete AI Movie"
    )


    st.success(
        "Your AI-generated multi-scene movie is ready!"
    )


    st.markdown(
        '<div class="ai-badge">'
        '🤖 AI-GENERATED MOVIE'
        '</div>',
        unsafe_allow_html=True,
    )


    st.video(
        st.session_state.final_movie
    )


    safe_title = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        st.session_state.story_title,
    )


    st.download_button(

        "⬇️ Download Complete AI Movie",

        data=st.session_state.final_movie,

        file_name=(
            f"{safe_title}_AI_Movie.mp4"
        ),

        mime="video/mp4",

        type="primary",

        use_container_width=True,

        key="download_final_movie",

    )


# ============================================================
# FULL NARRATION
# ============================================================

if st.session_state.full_audio:

    st.divider()


    st.header(
        "🎙️ Complete Narration"
    )


    st.audio(
        st.session_state.full_audio,
        format="audio/mp3",
    )


    st.download_button(

        "⬇️ Download Complete Narration",

        data=st.session_state.full_audio,

        file_name="complete_narration.mp3",

        mime="audio/mp3",

        key="download_complete_narration",

    )


# ============================================================
# DIAGNOSTICS
# ============================================================

if st.session_state.generation_errors:

    st.divider()


    with st.expander(
        "⚠️ Generation Diagnostics"
    ):

        st.warning(
            "Some components encountered errors."
        )


        for error in st.session_state.generation_errors:

            st.write(
                f"• {error}"
            )


# ============================================================
# PROJECT SUMMARY
# ============================================================

if st.session_state.project_ready:

    st.divider()


    st.header(
        "📊 Project Summary"
    )


    total_scenes = len(
        st.session_state.scenes
    )


    total_images = 0


    for item in st.session_state.scene_images:

        if (

            isinstance(
                item,
                dict,
            )

            and

            item.get(
                "image"
            )

        ):

            total_images += 1


    total_videos = 0


    for item in st.session_state.scene_videos:

        if (

            isinstance(
                item,
                dict,
            )

            and

            item.get(
                "video"
            )

        ):

            total_videos += 1


    total_audio = 0


    for item in st.session_state.scene_audio:

        if (

            isinstance(
                item,
                dict,
            )

            and

            item.get(
                "audio"
            )

        ):

            total_audio += 1


    c1, c2, c3, c4 = st.columns(
        4
    )


    c1.metric(
        "🎬 Scenes",
        total_scenes,
    )


    c2.metric(
        "🖼️ AI Images",
        total_images,
    )


    c3.metric(
        "🤖 AI Videos",
        total_videos,
    )


    c4.metric(
        "🎙️ Narrations",
        total_audio,
    )


    if total_videos == total_scenes:

        st.success(
            "🎉 Every scene has an AI-generated video."
        )

    elif total_videos > 0:

        st.warning(
            f"{total_videos} of {total_scenes} "
            "scenes have AI videos."
        )

    else:

        st.error(
            "No AI videos were generated."
        )
