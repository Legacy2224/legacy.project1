import streamlit as st
import os
import io
import re
import json
import time
import tempfile
import subprocess
from io import BytesIO

import requests
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
# PAGE CONFIGURATION
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
# API SECRETS
# ============================================================

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
HF_TOKEN = st.secrets.get("HF_TOKEN", "")


# ============================================================
# THEME CONFIGURATION
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

theme_name = st.sidebar.selectbox(
    "Choose Color Theme",
    list(THEMES.keys()),
)

theme = THEMES[theme_name]


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
        border-radius: 18px;
        border: 1px solid {theme["accent"]};
        margin-bottom: 25px;
    }}

    .story-card {{
        background-color: {theme["card"]};
        padding: 25px;
        border-radius: 15px;
        border-left: 5px solid {theme["accent"]};
        line-height: 1.8;
    }}

    .scene-card {{
        background-color: {theme["card"]};
        padding: 20px;
        border-radius: 15px;
        border-left: 4px solid {theme["accent"]};
        margin-bottom: 20px;
    }}

    .status-box {{
        padding: 15px;
        border-radius: 12px;
        background-color: {theme["card"]};
        border: 1px solid {theme["accent"]};
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# API STATUS
# ============================================================

st.sidebar.divider()
st.sidebar.subheader("🔑 API Configuration")

if GROQ_API_KEY:
    st.sidebar.success("Groq API: ✓ Connected")
else:
    st.sidebar.error("Groq API: ✗ Missing")

if HF_TOKEN:
    st.sidebar.success("Hugging Face: ✓ Connected")
else:
    st.sidebar.error("Hugging Face: ✗ Missing")

if imageio_ffmpeg:
    st.sidebar.success("FFmpeg: ✓ Available")
else:
    st.sidebar.warning(
        "FFmpeg package unavailable"
    )


# ============================================================
# AI VIDEO SETTINGS
# ============================================================

st.sidebar.divider()

st.sidebar.subheader("🤖 AI Video Engine")

hf_provider = st.sidebar.selectbox(
    "Video Provider",
    [
        "fal-ai",
    ],
    index=0,
    help=(
        "Hugging Face routes the video generation request "
        "to the selected inference provider."
    ),
)

video_model = st.sidebar.text_input(
    "AI Video Model",
    value="Wan-AI/Wan2.1-T2V-1.3B",
)

image_model = st.sidebar.text_input(
    "AI Image Model",
    value="stabilityai/stable-diffusion-xl-base-1.0",
)

video_frames = st.sidebar.slider(
    "Video Frames",
    min_value=17,
    max_value=49,
    value=33,
    step=4,
    help=(
        "More frames create longer videos but require "
        "more inference time."
    ),
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

# Keep image/video generation manageable.
scene_count = st.sidebar.slider(
    "Number of Scenes",
    min_value=3,
    max_value=10,
    value=5,
    step=1,
)

story_words = st.sidebar.slider(
    "Story Length",
    min_value=300,
    max_value=1800,
    value=700,
    step=100,
)

narration_language = st.sidebar.selectbox(
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
    except Exception:
        groq_client = None


hf_client = None

if HF_TOKEN and InferenceClient:

    try:

        hf_client = InferenceClient(
            provider=hf_provider,
            api_key=HF_TOKEN,
        )

    except Exception:
        hf_client = None


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">

    <h1>🎬 AI Story & Cinematic Studio</h1>

    <p>
    Turn an idea into a complete AI-generated cinematic experience.
    </p>

    <p>
    ✍️ Story →
    🎞️ Storyboard →
    🖼️ AI Images →
    🤖 AI Video →
    🎙️ Narration →
    🎬 Final Movie
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
            "Empty AI response."
        )

    text = text.strip()

    # Remove markdown fences.
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

    match = re.search(
        r"\[.*\]",
        text,
        re.DOTALL,
    )

    if not match:
        raise ValueError(
            "No JSON array was found."
        )

    return json.loads(
        match.group(0)
    )


# ============================================================
# GROQ TEXT GENERATION
# ============================================================

def generate_with_groq(
    prompt,
    max_tokens=6000,
    temperature=0.7,
):

    if groq_client is None:

        raise RuntimeError(
            "Groq API is not configured."
        )

    models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]

    last_error = None

    for model in models:

        try:

            response = (
                groq_client.chat.completions.create(
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
                response.choices
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

    raise RuntimeError(
        f"Groq generation failed: {last_error}"
    )


# ============================================================
# STORY GENERATOR
# ============================================================

def generate_story(
    title,
    words,
):

    prompt = f"""
You are a professional cinematic fantasy writer.

Write a completely original cinematic story.

TITLE:
{title}

TARGET WORD COUNT:
Approximately {words} words.

The story will be transformed into a multi-scene AI-generated movie.

Therefore the story must contain visually clear events.

Include:

1. Main character
2. Character appearance
3. Supporting characters
4. Important locations
5. Important objects
6. Character actions
7. Environmental details
8. Weather
9. Lighting
10. Conflict
11. Escalation
12. Major visual turning point
13. Climax
14. Emotional resolution
15. Ending

Keep characters visually consistent.

Avoid vague philosophical descriptions.

Make every major event something an AI video model
can visually understand.

Return ONLY the story.
"""

    return generate_with_groq(
        prompt,
        max_tokens=max(
            3000,
            words * 3,
        ),
        temperature=0.8,
    )


# ============================================================
# CINEMATIC SCENE PLANNER
# ============================================================

def generate_scene_plan(
    title,
    story,
    count,
):

    prompt = f"""
You are an expert film director,
cinematographer,
storyboard artist,
and AI video prompt engineer.

Convert the following COMPLETE story into EXACTLY
{count} cinematic scenes.

TITLE:
{title}

STORY:
{story}

IMPORTANT RULES:

Do NOT simply split sentences.

Create meaningful cinematic scenes.

The scenes must cover the entire story from beginning
to ending.

Characters must remain visually consistent.

Each scene must contain a clear physical action.

Each scene must be suitable for AI text-to-video generation.

The video model needs concrete descriptions.

For every scene create:

number
title
description
characters
location
objects
action
lighting
camera
image_prompt
video_prompt
narration

IMAGE PROMPT:

Describe exactly what the camera sees.

VIDEO PROMPT:

Describe what physically moves.

Include:

camera movement
character movement
environment movement
lighting changes
facial expressions
important objects

Avoid:

text
subtitles
logos
watermarks
abstract concepts

Use cinematic film language.

Return ONLY valid JSON.

Example:

[
  {{
    "number": 1,
    "title": "Entering the Forest",
    "description": "...",
    "characters": "...",
    "location": "...",
    "objects": "...",
    "action": "...",
    "lighting": "...",
    "camera": "...",
    "image_prompt": "...",
    "video_prompt": "...",
    "narration": "..."
  }}
]
"""

    raw = generate_with_groq(
        prompt,
        max_tokens=10000,
        temperature=0.5,
    )

    data = extract_json_array(
        raw
    )

    if not isinstance(
        data,
        list,
    ):

        raise ValueError(
            "Scene planner returned invalid data."
        )

    scenes = []

    for index, item in enumerate(data):

        if not isinstance(
            item,
            dict,
        ):
            continue

        scene_number = index + 1

        scene = {
            "number": scene_number,

            "title": clean_text(
                item.get(
                    "title",
                    f"Scene {scene_number}",
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
        # Make sure prompts are never empty.
        # ----------------------------------------------------

        if not scene["image_prompt"]:

            scene["image_prompt"] = (
                f"Cinematic movie still of "
                f"{scene['description']}. "
                f"Characters: {scene['characters']}. "
                f"Location: {scene['location']}. "
                f"Action: {scene['action']}. "
                f"Lighting: {scene['lighting']}. "
                f"Professional fantasy film, "
                f"high detail, widescreen."
            )

        if not scene["video_prompt"]:

            scene["video_prompt"] = (
                f"Cinematic AI-generated movie shot. "
                f"{scene['description']} "
                f"{scene['action']} "
                f"Characters move naturally. "
                f"Environment moves naturally. "
                f"{scene['camera']} "
                f"{scene['lighting']}. "
                f"Smooth cinematic camera motion."
            )

        if not scene["narration"]:

            scene["narration"] = (
                scene["description"]
            )

        scenes.append(
            scene
        )

    if not scenes:

        raise ValueError(
            "No scenes were generated."
        )

    # Ensure requested count.
    if len(scenes) > count:

        scenes = scenes[:count]

    return scenes


# ============================================================
# AI IMAGE GENERATION
# ============================================================

def generate_ai_image(
    prompt,
):

    if hf_client is None:

        return None, (
            "Hugging Face client unavailable."
        )

    enhanced_prompt = f"""
Cinematic fantasy movie still.

{prompt}

Professional cinematography.
Photorealistic cinematic detail.
Beautiful composition.
Detailed environment.
Consistent character appearance.
Natural anatomy.
Natural hands.
Expressive faces.
Atmospheric depth.
Volumetric lighting.
Film-quality color grading.
Widescreen composition.

Absolutely no text.
No captions.
No subtitles.
No logos.
No watermark.
"""

    try:

        image = hf_client.text_to_image(
            enhanced_prompt,
            model=image_model,
        )

        if image is not None:

            return image, None

        return None, (
            "The image provider returned no image."
        )

    except Exception as exc:

        return None, str(exc)


# ============================================================
# AI VIDEO GENERATION
# ============================================================

def generate_ai_video(
    prompt,
    seed=None,
):

    if hf_client is None:

        raise RuntimeError(
            "Hugging Face client unavailable."
        )

    enhanced_prompt = f"""
Create a cinematic AI-generated video.

SCENE:

{prompt}

VISUAL STYLE:

High-quality cinematic fantasy film.
Professional movie cinematography.
Natural character motion.
Natural environmental motion.
Physically believable movement.
Detailed faces.
Detailed clothing.
Atmospheric depth.
Volumetric lighting.
Film-quality composition.

CAMERA:

Smooth cinematic camera movement.
Professional lens.
Natural depth of field.
Controlled motion.

DO NOT INCLUDE:

text
subtitles
captions
logos
watermarks
UI
static slideshow
still photograph
human stock footage
existing movie footage

This must be a newly AI-generated moving video scene.
"""

    negative_prompt = [
        "text",
        "subtitle",
        "caption",
        "logo",
        "watermark",
        "static image",
        "slideshow",
        "stock footage",
        "deformed anatomy",
        "extra fingers",
        "duplicate people",
        "flickering",
        "blurry",
        "low quality",
    ]

    try:

        video = hf_client.text_to_video(
            enhanced_prompt,
            model=video_model,
            guidance_scale=video_guidance,
            negative_prompt=negative_prompt,
            num_frames=video_frames,
            num_inference_steps=video_steps,
            seed=seed,
        )

        if not video:

            raise RuntimeError(
                "The AI video provider returned no video."
            )

        return video

    except TypeError:

        # Some provider/model versions may not accept
        # every optional argument.

        video = hf_client.text_to_video(
            enhanced_prompt,
            model=video_model,
            guidance_scale=video_guidance,
            num_frames=video_frames,
        )

        if not video:

            raise RuntimeError(
                "The AI video provider returned no video."
            )

        return video


# ============================================================
# GENERATE ALL AI IMAGES
# ============================================================

def generate_all_images(
    scenes,
):

    results = []

    total = len(scenes)

    progress = st.progress(
        0,
        text="Preparing AI scene images...",
    )

    for index, scene in enumerate(scenes):

        number = safe_int(
            scene.get(
                "number",
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
                f"Generating AI image "
                f"for Scene {number}/{total}..."
            ),
        )

        image, error = generate_ai_image(
            scene.get(
                "image_prompt",
                "",
            )
        )

        result = {
            "scene": number,
            "title": title,
            "image": image,
            "error": error,
        }

        results.append(
            result
        )

        if error:

            st.session_state.generation_errors.append(
                f"Scene {number} image: {error}"
            )

    progress.progress(
        1.0,
        text="AI scene images completed ✓",
    )

    return results


# ============================================================
# GENERATE ALL AI VIDEOS
# ============================================================

def generate_all_videos(
    scenes,
):

    results = []

    total = len(scenes)

    progress = st.progress(
        0,
        text="Starting AI video generation...",
    )

    for index, scene in enumerate(scenes):

        number = safe_int(
            scene.get(
                "number",
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
                f"AI-generating Scene "
                f"{number}/{total}..."
            ),
        )

        try:

            # Different deterministic seed per scene.
            seed = (
                int(time.time())
                + number * 1009
            )

            video_bytes = generate_ai_video(
                scene.get(
                    "video_prompt",
                    "",
                ),
                seed=seed,
            )

            results.append({
                "scene": number,
                "title": title,
                "video": video_bytes,
                "prompt": scene.get(
                    "video_prompt",
                    "",
                ),
                "error": None,
                "source": "AI",
            })

        except Exception as exc:

            error_message = str(
                exc
            )

            st.session_state.generation_errors.append(
                f"Scene {number} video: {error_message}"
            )

            results.append({
                "scene": number,
                "title": title,
                "video": None,
                "prompt": scene.get(
                    "video_prompt",
                    "",
                ),
                "error": error_message,
                "source": "AI",
            })

        progress.progress(
            (index + 1) / total,
            text=(
                f"AI video generation "
                f"{index + 1}/{total}"
            ),
        )

    return results


# ============================================================
# GENERATE NARRATION
# ============================================================

def generate_all_narration(
    scenes,
    language,
):

    results = []

    total = len(scenes)

    progress = st.progress(
        0,
        text="Creating narration...",
    )

    for index, scene in enumerate(scenes):

        number = safe_int(
            scene.get(
                "number",
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

            audio_bytes = buffer.getvalue()

            results.append({
                "scene": number,
                "title": scene.get(
                    "title",
                    "",
                ),
                "text": text,
                "audio": audio_bytes,
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
# GET FFMPEG
# ============================================================

def get_ffmpeg():

    if imageio_ffmpeg is None:

        raise RuntimeError(
            "imageio-ffmpeg is not installed. "
            "Add imageio-ffmpeg to requirements.txt."
        )

    try:

        return imageio_ffmpeg.get_ffmpeg_exe()

    except Exception as exc:

        raise RuntimeError(
            f"FFmpeg could not be located: {exc}"
        )


# ============================================================
# WRITE TEMP FILE
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
# COMBINE AI VIDEOS
# ============================================================

def combine_ai_videos(
    video_items,
):

    usable = []

    # --------------------------------------------------------
    # IMPORTANT:
    # Every item is validated before using ["scene"].
    # This fixes the previous x["scene"] error.
    # --------------------------------------------------------

    for item in video_items:

        if not isinstance(
            item,
            dict,
        ):
            continue

        scene_number = safe_int(
            item.get(
                "scene",
            ),
            0,
        )

        video = item.get(
            "video",
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
            "No AI-generated videos are available "
            "to combine."
        )

    # Sort by scene.
    usable.sort(
        key=lambda x: x[0]
    )

    ffmpeg = get_ffmpeg()

    temp_dir = tempfile.mkdtemp(
        prefix="ai_movie_",
    )

    try:

        scene_files = []

        # ----------------------------------------------------
        # Write individual videos.
        # ----------------------------------------------------

        for scene_number, video in usable:

            path = write_temp_file(
                temp_dir,
                f"scene_{scene_number}.mp4",
                video,
            )

            scene_files.append(
                path
            )

        # ----------------------------------------------------
        # Create concat file.
        # ----------------------------------------------------

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
        # First try stream copy.
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
            output_file,
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,
        )

        # ----------------------------------------------------
        # If stream copy fails, re-encode.
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
                timeout=600,
            )

        if (
            result.returncode != 0
            or not os.path.exists(
                output_file
            )
        ):

            error_text = (
                result.stderr
                .decode(
                    "utf-8",
                    errors="ignore",
                )
            )

            raise RuntimeError(
                "Could not combine AI videos.\n"
                + error_text[-2000:]
            )

        with open(
            output_file,
            "rb",
        ) as file:

            return file.read()

    finally:

        # Clean temporary files.
        try:

            for filename in os.listdir(
                temp_dir
            ):

                path = os.path.join(
                    temp_dir,
                    filename,
                )

                if os.path.isfile(
                    path
                ):

                    os.remove(
                        path
                    )

            os.rmdir(
                temp_dir
            )

        except Exception:
            pass


# ============================================================
# COMBINE AUDIO
# ============================================================

def combine_audio(
    audio_items,
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
                "scene",
            ),
            0,
        )

        audio = item.get(
            "audio",
        )

        if scene <= 0:
            continue

        if not audio:
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
        prefix="ai_audio_",
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
            "audio_concat.txt",
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
            "narration.mp3",
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
            timeout=600,
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

        try:

            for filename in os.listdir(
                temp_dir
            ):

                path = os.path.join(
                    temp_dir,
                    filename,
                )

                if os.path.isfile(
                    path
                ):

                    os.remove(
                        path
                    )

            os.rmdir(
                temp_dir
            )

        except Exception:
            pass


# ============================================================
# ADD NARRATION TO FINAL MOVIE
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
        prefix="narrated_movie_",
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
            "narrated_movie.mp4",
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
            timeout=600,
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

        try:

            for filename in os.listdir(
                temp_dir
            ):

                path = os.path.join(
                    temp_dir,
                    filename,
                )

                if os.path.isfile(
                    path
                ):

                    os.remove(
                        path
                    )

            os.rmdir(
                temp_dir
            )

        except Exception:
            pass


# ============================================================
# MAIN INPUT
# ============================================================

story_title = st.text_input(
    "📖 Enter Story Topic or Title",
    value="Elara and the Secret Forest",
)

generation_mode = st.radio(
    "Choose Output",
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
# GENERATION PIPELINE
# ============================================================

if generate_button:

    # --------------------------------------------------------
    # Validate APIs
    # --------------------------------------------------------

    if not GROQ_API_KEY:

        st.error(
            "GROQ_API_KEY is missing."
        )

        st.info(
            "Add GROQ_API_KEY to Streamlit secrets."
        )

        st.stop()

    if not HF_TOKEN:

        st.error(
            "HF_TOKEN is missing."
        )

        st.info(
            "Add HF_TOKEN to Streamlit secrets."
        )

        st.stop()

    if hf_client is None:

        st.error(
            "Hugging Face client could not be initialized."
        )

        st.stop()

    # --------------------------------------------------------
    # Reset old project
    # --------------------------------------------------------

    st.session_state.story = ""
    st.session_state.story_title = story_title
    st.session_state.scenes = []
    st.session_state.scene_images = []
    st.session_state.scene_videos = []
    st.session_state.scene_audio = []
    st.session_state.full_audio = None
    st.session_state.final_movie = None
    st.session_state.generation_errors = []
    st.session_state.project_ready = False

    # ========================================================
    # STEP 1
    # ========================================================

    st.header(
        "1️⃣ Creating Story"
    )

    try:

        story_progress = st.progress(
            0,
            text="AI is writing the story...",
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
    # STEP 2
    # ========================================================

    st.header(
        "2️⃣ Creating Cinematic Scenes"
    )

    try:

        scene_progress = st.progress(
            0,
            text="AI is directing the story...",
        )

        scenes = generate_scene_plan(
            story_title,
            story,
            scene_count,
        )

        st.session_state.scenes = scenes

        scene_progress.progress(
            1.0,
            text=(
                f"{len(scenes)} cinematic scenes created ✓"
            ),
        )

    except Exception as exc:

        st.error(
            f"Scene planning failed: {exc}"
        )

        st.stop()

    # ========================================================
    # STEP 3
    # ========================================================

    st.header(
        "3️⃣ Generating AI Images"
    )

    st.session_state.scene_images = (
        generate_all_images(
            scenes
        )
    )

    # ========================================================
    # STORY-ONLY MODE
    # ========================================================

    if generation_mode == "📖 Story + AI Images":

        st.success(
            "Story and AI images generated."
        )

        st.session_state.project_ready = True

    # ========================================================
    # COMPLETE AI MOVIE
    # ========================================================

    else:

        # ====================================================
        # STEP 4
        # ====================================================

        st.header(
            "4️⃣ Generating AI Video Scenes"
        )

        st.info(
            """
            🤖 Every scene below is being generated
            as a NEW AI video from its cinematic prompt.

            No Pixabay video.
            No stock video.
            No human footage.
            """
        )

        st.session_state.scene_videos = (
            generate_all_videos(
                scenes
            )
        )

        # ====================================================
        # STEP 5
        # ====================================================

        st.header(
            "5️⃣ Generating Narration"
        )

        st.session_state.scene_audio = (
            generate_all_narration(
                scenes,
                narration_language[1],
            )
        )

        # ====================================================
        # STEP 6
        # ====================================================

        st.header(
            "6️⃣ Combining AI Video Scenes"
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
                No AI video scenes were returned.

                Check your Hugging Face token,
                selected provider, model availability,
                and provider credits.
                """
            )

        else:

            st.write(
                f"AI video scenes available: "
                f"**{valid_video_count}/{len(scenes)}**"
            )

            try:

                movie_progress = st.progress(
                    0,
                    text="Combining AI-generated scenes...",
                )

                movie = combine_ai_videos(
                    st.session_state.scene_videos
                )

                movie_progress.progress(
                    1.0,
                    text="AI movie assembled ✓",
                )

                st.session_state.final_movie = movie

            except Exception as exc:

                st.session_state.generation_errors.append(
                    f"Movie assembly: {exc}"
                )

                st.error(
                    f"Movie assembly failed: {exc}"
                )

        # ====================================================
        # STEP 7
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
        # STEP 8
        # ====================================================

        if (
            st.session_state.final_movie
            and
            st.session_state.full_audio
        ):

            st.header(
                "8️⃣ Creating Final Narrated Movie"
            )

            try:

                final_movie = (
                    add_narration_to_movie(
                        st.session_state.final_movie,
                        st.session_state.full_audio,
                    )
                )

                st.session_state.final_movie = (
                    final_movie
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


# ============================================================
# DISPLAY SCENES
# ============================================================

if st.session_state.scenes:

    st.divider()

    st.header(
        "🎬 Cinematic Scene Breakdown"
    )

    # --------------------------------------------------------
    # Build SAFE lookups.
    #
    # This is deliberately defensive.
    # It prevents:
    #
    # x["scene"]
    #
    # from crashing when x is malformed.
    # --------------------------------------------------------

    image_lookup = {}

    for item in st.session_state.scene_images:

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

        if "scene" not in item:
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

        if "scene" not in item:
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
    # Render scenes.
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
                "number",
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
                f"**📖 Description**  \n"
                f"{scene.get('description', '')}"
            )

            st.markdown(
                f"**👤 Characters**  \n"
                f"{scene.get('characters', '')}"
            )

            st.markdown(
                f"**📍 Location**  \n"
                f"{scene.get('location', '')}"
            )

            st.markdown(
                f"**🎭 Action**  \n"
                f"{scene.get('action', '')}"
            )

            st.markdown(
                f"**💡 Lighting**  \n"
                f"{scene.get('lighting', '')}"
            )

            st.markdown(
                f"**📷 Camera**  \n"
                f"{scene.get('camera', '')}"
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

            # =================================================
            # IMAGE + VIDEO
            # =================================================

            col1, col2 = st.columns(
                2
            )

            # -------------------------------------------------
            # IMAGE
            # -------------------------------------------------

            with col1:

                st.subheader(
                    "🖼️ AI Image"
                )

                image_data = image_lookup.get(
                    number
                )

                if (
                    isinstance(
                        image_data,
                        dict,
                    )
                    and
                    image_data.get(
                        "image"
                    )
                ):

                    st.image(
                        image_data["image"],
                        use_container_width=True,
                    )

                    image_bytes = BytesIO()

                    image_data["image"].save(
                        image_bytes,
                        format="PNG",
                    )

                    st.download_button(
                        label=(
                            f"⬇️ Download Scene "
                            f"{number} Image"
                        ),
                        data=image_bytes.getvalue(),
                        file_name=(
                            f"scene_{number}.png"
                        ),
                        mime="image/png",
                        key=(
                            f"download_image_{number}"
                        ),
                    )

                else:

                    st.info(
                        "AI image unavailable."
                    )

            # -------------------------------------------------
            # VIDEO
            # -------------------------------------------------

            with col2:

                st.subheader(
                    "🤖 AI-Generated Video"
                )

                video_data = video_lookup.get(
                    number
                )

                if (
                    isinstance(
                        video_data,
                        dict,
                    )
                    and
                    video_data.get(
                        "video"
                    )
                ):

                    video_bytes = (
                        video_data["video"]
                    )

                    st.video(
                        video_bytes
                    )

                    st.download_button(
                        label=(
                            f"⬇️ Download AI "
                            f"Video {number}"
                        ),
                        data=video_bytes,
                        file_name=(
                            f"ai_scene_{number}.mp4"
                        ),
                        mime="video/mp4",
                        key=(
                            f"download_video_{number}"
                        ),
                    )

                    st.caption(
                        "🤖 Generated by AI"
                    )

                elif (
                    isinstance(
                        video_data,
                        dict,
                    )
                    and
                    video_data.get(
                        "error"
                    )
                ):

                    st.error(
                        video_data["error"]
                    )

                else:

                    st.warning(
                        "AI video unavailable for this scene."
                    )

            # =================================================
            # AI VIDEO PROMPT
            # =================================================

            st.markdown("---")

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

            audio_data = audio_lookup.get(
                number
            )

            if (
                isinstance(
                    audio_data,
                    dict,
                )
                and
                audio_data.get(
                    "audio"
                )
            ):

                audio_bytes = (
                    audio_data["audio"]
                )

                st.audio(
                    audio_bytes,
                    format="audio/mp3",
                )

                st.download_button(
                    label=(
                        f"⬇️ Download Narration "
                        f"{number}"
                    ),
                    data=audio_bytes,
                    file_name=(
                        f"scene_{number}_narration.mp3"
                    ),
                    mime="audio/mp3",
                    key=(
                        f"download_audio_{number}"
                    ),
                )


# ============================================================
# FINAL MOVIE
# ============================================================

if st.session_state.final_movie:

    st.divider()

    st.header(
        "🎬 Complete AI-Generated Movie"
    )

    st.success(
        "Your multi-scene AI movie is ready."
    )

    st.video(
        st.session_state.final_movie
    )

    st.download_button(
        label="⬇️ Download Complete AI Movie",
        data=st.session_state.final_movie,
        file_name=(
            f"{st.session_state.story_title}"
            .replace(" ", "_")
            .replace("/", "_")
            + "_AI_Movie.mp4"
        ),
        mime="video/mp4",
        type="primary",
        use_container_width=True,
        key="download_complete_movie",
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
        label="⬇️ Download Complete Narration",
        data=st.session_state.full_audio,
        file_name="complete_narration.mp3",
        mime="audio/mp3",
        key="download_complete_audio",
    )


# ============================================================
# ERROR REPORT
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

    scenes_total = len(
        st.session_state.scenes
    )

    images_total = 0

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

            images_total += 1

    videos_total = 0

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

            videos_total += 1

    audio_total = 0

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

            audio_total += 1

    c1, c2, c3, c4 = st.columns(
        4
    )

    c1.metric(
        "🎬 Scenes",
        scenes_total,
    )

    c2.metric(
        "🖼️ AI Images",
        images_total,
    )

    c3.metric(
        "🤖 AI Videos",
        videos_total,
    )

    c4.metric(
        "🎙️ Narrations",
        audio_total,
    )

    if videos_total == scenes_total:

        st.success(
            "🎉 Every scene has an AI-generated video."
        )

    elif videos_total > 0:

        st.warning(
            f"{videos_total} of {scenes_total} "
            "scenes have AI-generated videos."
        )

    else:

        st.error(
            "No AI-generated video scenes were produced."
        )
