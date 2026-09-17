import os
import json
import time
import shutil
from pathlib import Path

import requests
import streamlit as st

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from gradio_client import Client
except ImportError:
    Client = None


# ============================================================
# STREAMLIT
# ============================================================

st.set_page_config(
    page_title="AI Story Video Generator",
    page_icon="🎬",
    layout="wide"
)


# ============================================================
# CONFIG
# ============================================================

HF_SPACE = "Lightricks/ltx-video-distilled"

GROQ_MODEL = "openai/gpt-oss-20b"

OUTPUT_DIR = Path("generated_story")
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# SECRETS
# ============================================================

def get_secret(name):

    try:
        value = st.secrets.get(name)

        if value:
            return str(value).strip()

    except Exception:
        pass

    return os.getenv(name, "").strip()


GROQ_API_KEY = get_secret("GROQ_API_KEY")
HF_TOKEN = get_secret("HF_TOKEN")
PIXABAY_API_KEY = get_secret("PIXABAY_API_KEY")


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <h1 style="text-align:center;">
    🎬 AI Story Video Generator
    </h1>

    <p style="text-align:center;">
    Story → Scenes → AI Video → Final MP4
    </p>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Settings")

    visual_style = st.selectbox(
        "Visual Style",
        [
            "Cinematic",
            "Photorealistic",
            "Fantasy",
            "Dark Fantasy",
            "3D Animation",
            "Anime",
            "Sci-Fi",
            "Cyberpunk"
        ]
    )

    aspect_ratio = st.selectbox(
        "Aspect Ratio",
        [
            "16:9",
            "9:16",
            "1:1"
        ]
    )

    scene_count = st.slider(
        "Number of Scenes",
        1,
        4,
        2
    )

    duration = st.slider(
        "Scene Duration",
        0.3,
        8.0,
        2.0,
        0.1
    )

    st.markdown("---")

    st.write("API Status")

    if GROQ_API_KEY:
        st.success("Groq ✓")
    else:
        st.error("Groq missing")

    if HF_TOKEN:
        st.success("Hugging Face ✓")
    else:
        st.info("HF token optional")

    if PIXABAY_API_KEY:
        st.success("Pixabay ✓")
    else:
        st.info("Pixabay optional")


# ============================================================
# INPUT
# ============================================================

st.subheader("📖 Story")

story = st.text_area(
    "Enter your story",
    height=220,
    placeholder=(
        "Example:\n\n"
        "Elara enters an ancient forest. "
        "She follows a mossy path and discovers "
        "an ancient stone altar covered in glowing runes."
    )
)


st.subheader("👤 Character")

character = st.text_area(
    "Character description",
    height=120,
    placeholder=(
        "Elara is a young woman with long dark hair, "
        "a green cloak, leather boots and a small backpack."
    )
)


st.subheader("🎥 Cinematic Direction")

extra_details = st.text_area(
    "Optional instructions",
    height=100,
    placeholder=(
        "Slow cinematic camera movement, realistic lighting, "
        "wind, atmospheric particles and natural character motion."
    )
)


# ============================================================
# DIMENSIONS
# ============================================================

def get_dimensions():

    if aspect_ratio == "16:9":

        return 512, 704

    if aspect_ratio == "9:16":

        return 704, 512

    return 512, 512


# ============================================================
# GROQ
# ============================================================

def create_storyboard():

    if not GROQ_API_KEY:

        raise RuntimeError(
            "GROQ_API_KEY is missing."
        )

    if Groq is None:

        raise RuntimeError(
            "groq package is not installed."
        )

    client = Groq(
        api_key=GROQ_API_KEY
    )

    prompt = f"""
You are an expert film director and AI video prompt engineer.

Turn this story into exactly {scene_count} connected cinematic scenes.

STORY:

{story}

CHARACTER:

{character}

VISUAL STYLE:

{visual_style}

ASPECT RATIO:

{aspect_ratio}

EXTRA DIRECTION:

{extra_details}

Create connected scenes.

Keep the character consistent between every scene.

Every scene must contain:

scene_number
title
story_action
video_prompt
negative_prompt
pixabay_query

The video_prompt must describe actual MOVEMENT.

Include:

character movement
camera movement
environment movement
lighting
atmosphere
objects
beginning of shot
ending of shot

Do NOT write image prompts.

These prompts will be sent directly to a video generation model.

Return ONLY valid JSON.

Format:

{{
    "title": "story title",
    "character_bible": "consistent character description",
    "scenes": [
        {{
            "scene_number": 1,
            "title": "scene title",
            "story_action": "what happens",
            "video_prompt": "detailed moving video prompt",
            "negative_prompt": "bad things to avoid",
            "pixabay_query": "short search query"
        }}
    ]
}}
"""

    response = client.chat.completions.create(

        model=GROQ_MODEL,

        messages=[
            {
                "role": "system",
                "content":
                "Return JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.2,

        response_format={
            "type": "json_object"
        },

        max_tokens=7000
    )

    text = response.choices[0].message.content

    if text.startswith("```"):

        text = text.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        ).strip()

    return json.loads(text)


# ============================================================
# HUGGING FACE CLIENT
# ============================================================

@st.cache_resource
def get_hf_client():

    if Client is None:

        raise RuntimeError(
            "gradio_client is missing.\n\n"
            "Add gradio_client to requirements.txt."
        )

    try:

        if HF_TOKEN:

            return Client(
                HF_SPACE,
                token=HF_TOKEN
            )

        return Client(
            HF_SPACE
        )

    except Exception as e:

        raise RuntimeError(
            "Could not connect to Hugging Face:\n\n"
            + str(e)
        )


# ============================================================
# IMPORTANT:
# EXTRACT GRADIO VIDEO RESULT
# ============================================================

def extract_video_result(result):

    """
    Current LTX Space returns:

        (output_video_path, used_seed)

    But Gradio may represent the file in
    several different ways.

    This function handles all common cases.
    """

    st.write(
        "🔎 Processing Hugging Face response..."
    )

    # --------------------------------------------------------
    # Tuple / list
    # --------------------------------------------------------

    if isinstance(
        result,
        (tuple, list)
    ):

        if len(result) == 0:

            return None

        # Current LTX:
        #
        # result[0] = video
        # result[1] = seed

        video = result[0]

    else:

        video = result

    # --------------------------------------------------------
    # None
    # --------------------------------------------------------

    if video is None:

        return None

    # --------------------------------------------------------
    # String
    # --------------------------------------------------------

    if isinstance(
        video,
        str
    ):

        return video

    # --------------------------------------------------------
    # Dict
    # --------------------------------------------------------

    if isinstance(
        video,
        dict
    ):

        for key in [
            "path",
            "video",
            "url",
            "value"
        ]:

            if key in video:

                value = video[key]

                if value:

                    return str(value)

    # --------------------------------------------------------
    # Gradio FileData
    # --------------------------------------------------------

    if hasattr(
        video,
        "path"
    ):

        path = getattr(
            video,
            "path",
            None
        )

        if path:

            return str(path)

    # --------------------------------------------------------
    # Gradio data object
    # --------------------------------------------------------

    if hasattr(
        video,
        "url"
    ):

        url = getattr(
            video,
            "url",
            None
        )

        if url:

            return str(url)

    # --------------------------------------------------------
    # repr fallback
    # --------------------------------------------------------

    return str(video)


# ============================================================
# DOWNLOAD / COPY VIDEO
# ============================================================

def save_video(
    source,
    destination
):

    destination = Path(
        destination
    )

    source = str(source)

    # --------------------------------------------------------
    # LOCAL FILE
    # --------------------------------------------------------

    if os.path.isfile(source):

        shutil.copy2(
            source,
            destination
        )

        return True

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    if source.startswith(
        "http://"
    ) or source.startswith(
        "https://"
    ):

        response = requests.get(
            source,
            timeout=180
        )

        response.raise_for_status()

        destination.write_bytes(
            response.content
        )

        return True

    return False


# ============================================================
# GENERATE VIDEO
# ============================================================

def generate_scene_video(
    prompt,
    negative_prompt,
    duration_seconds,
    seed,
    status
):

    client = get_hf_client()

    height, width = get_dimensions()

    status.info(
        "🔗 Connected to LTX Video..."
    )

    # ========================================================
    # CURRENT LTX API
    # ========================================================
    #
    # The current Space has:
    #
    # /text_to_video
    #
    # and accepts:
    #
    # prompt
    # negative_prompt
    # input image
    # input video
    # height
    # width
    # mode
    # duration
    # frames
    # seed
    # randomize seed
    # guidance scale
    # improve texture
    #
    # ========================================================

    try:

        status.info(
            "🎥 Sending scene to LTX..."
        )

        result = client.predict(

            prompt,

            negative_prompt,

            None,

            None,

            int(height),

            int(width),

            "text-to-video",

            float(duration_seconds),

            9,

            int(seed),

            False,

            1.0,

            True,

            api_name="/text_to_video"
        )

    except Exception as e:

        raise RuntimeError(
            "Hugging Face video request failed:\n\n"
            + str(e)
        )

    # ========================================================
    # EXTRACT VIDEO
    # ========================================================

    video_source = extract_video_result(
        result
    )

    if not video_source:

        raise RuntimeError(
            "Hugging Face returned no video."
        )

    # ========================================================
    # CHECK LOCAL PATH
    # ========================================================

    if os.path.isfile(
        str(video_source)
    ):

        return str(video_source)

    # ========================================================
    # SOMETIMES GRADIO RETURNS FILE OBJECT
    # ========================================================

    if hasattr(
        video_source,
        "path"
    ):

        path = video_source.path

        if path and os.path.isfile(
            path
        ):

            return path

    # ========================================================
    # URL
    # ========================================================

    if str(
        video_source
    ).startswith(
        "http"
    ):

        return str(
            video_source
        )

    # ========================================================
    # NOTHING FOUND
    # ========================================================

    raise RuntimeError(
        "LTX returned a response, but "
        "no usable video file was found.\n\n"
        "Returned value:\n\n"
        + repr(result)
    )


# ============================================================
# PIXABAY
# ============================================================

def search_pixabay(query):

    if not PIXABAY_API_KEY:

        return []

    if not query:

        return []

    try:

        response = requests.get(

            "https://pixabay.com/api/",

            params={
                "key": PIXABAY_API_KEY,
                "q": query,
                "image_type": "photo",
                "safesearch": "true",
                "per_page": 6
            },

            timeout=20
        )

        data = response.json()

        return data.get(
            "hits",
            []
        )

    except Exception:

        return []


# ============================================================
# PROMPT BUILDER
# ============================================================

def build_prompt(
    scene,
    character_bible
):

    return f"""
Create an actual moving cinematic video.

STORY:

{story}


CHARACTER:

{character_bible}


CURRENT SCENE:

{scene["story_action"]}


VIDEO ACTION:

{scene["video_prompt"]}


STYLE:

{visual_style}


ASPECT RATIO:

{aspect_ratio}


EXTRA:

{extra_details}


IMPORTANT:

The character must move naturally.

The environment must move naturally.

Camera must move naturally.

Use cinematic composition.

Use realistic lighting.

Use atmospheric particles.

Preserve character identity.

Preserve clothing.

Preserve hairstyle.

Preserve age.

Preserve body appearance.

Do NOT create a still image.

Do NOT create a slideshow.

Do NOT add text.

Do NOT add subtitles.

Do NOT add logos.

Do NOT add watermarks.

Do NOT introduce unrelated characters.

Do NOT change the character.

This must be an actual moving video.
"""


# ============================================================
# CLEAN OLD FILES
# ============================================================

def clean_old_files():

    for file in OUTPUT_DIR.glob(
        "*.mp4"
    ):

        try:
            file.unlink()
        except Exception:
            pass


# ============================================================
# MAIN BUTTON
# ============================================================

if st.button(
    "🚀 GENERATE COMPLETE VIDEO",
    type="primary",
    use_container_width=True
):

    if not story.strip():

        st.warning(
            "Please enter a story."
        )

        st.stop()

    if not GROQ_API_KEY:

        st.error(
            "GROQ_API_KEY is missing."
        )

        st.stop()

    clean_old_files()

    # ========================================================
    # STEP 1
    # ========================================================

    st.header(
        "🧠 Step 1 — Creating Storyboard"
    )

    try:

        storyboard = create_storyboard()

    except Exception as e:

        st.error(
            "Storyboard generation failed."
        )

        st.code(
            str(e)
        )

        st.stop()

    st.success(
        "✅ Storyboard created."
    )

    title = storyboard.get(
        "title",
        "AI Story"
    )

    character_bible = storyboard.get(
        "character_bible",
        character
    )

    scenes = storyboard.get(
        "scenes",
        []
    )

    st.subheader(
        "🎬 " + title
    )

    st.write(
        character_bible
    )

    # ========================================================
    # SCENES
    # ========================================================

    for scene in scenes:

        st.markdown(
            f"""
            ## 🎬 Scene {scene["scene_number"]}:
            {scene["title"]}
            """
        )

        st.write(
            scene["story_action"]
        )

    # ========================================================
    # STEP 2
    # ========================================================

    st.header(
        "🎥 Step 2 — Generating Actual Videos"
    )

    progress = st.progress(0)

    generated_files = []

    total = len(scenes)

    for index, scene in enumerate(
        scenes
    ):

        number = scene["scene_number"]

        title = scene["title"]

        st.markdown(
            f"""
            ## 🎬 Scene {number}: {title}
            """
        )

        st.write(
            scene["story_action"]
        )

        prompt = build_prompt(
            scene,
            character_bible
        )

        with st.expander(
            "🔍 View Video Prompt"
        ):

            st.write(
                prompt
            )

        negative_prompt = scene.get(
            "negative_prompt",
            (
                "worst quality, blurry, "
                "jittery, distorted, "
                "bad anatomy, duplicate "
                "characters, inconsistent "
                "character, text, subtitles, "
                "logo, watermark"
            )
        )

        status = st.empty()

        try:

            source = generate_scene_video(

                prompt,

                negative_prompt,

                duration,

                1000 + number,

                status
            )

            local_file = (
                OUTPUT_DIR
                / f"scene_{number}.mp4"
            )

            if source != str(
                local_file
            ):

                if not save_video(
                    source,
                    local_file
                ):

                    raise RuntimeError(
                        "Video was returned, "
                        "but could not be saved."
                    )

            if not local_file.exists():

                raise RuntimeError(
                    "Video file does not exist."
                )

            if local_file.stat().st_size == 0:

                raise RuntimeError(
                    "Video file is empty."
                )

            generated_files.append(
                str(local_file)
            )

            status.success(
                f"✅ Scene {number} generated successfully."
            )

            st.video(
                str(local_file)
            )

            with open(
                local_file,
                "rb"
            ) as video_file:

                st.download_button(

                    f"⬇️ Download Scene {number}",

                    video_file.read(),

                    file_name=
                    f"scene_{number}.mp4",

                    mime=
                    "video/mp4",

                    key=
                    f"download_{number}"
                )

        except Exception as e:

            status.error(
                f"❌ Scene {number} failed."
            )

            st.code(
                str(e)
            )

        # ====================================================
        # PIXABAY REFERENCES
        # ====================================================

        if PIXABAY_API_KEY:

            query = scene.get(
                "pixabay_query",
                ""
            )

            images = search_pixabay(
                query
            )

            if images:

                st.subheader(
                    "🖼️ Reference Images"
                )

                cols = st.columns(3)

                for i, image in enumerate(
                    images[:6]
                ):

                    with cols[
                        i % 3
                    ]:

                        url = image.get(
                            "webformatURL"
                        )

                        if url:

                            st.image(
                                url,
                                use_container_width=True
                            )

        progress.progress(
            (index + 1) / total
        )

    # ========================================================
    # STEP 3
    # ========================================================

    st.header(
        "🎞️ Step 3 — Final Video"
    )

    if not generated_files:

        st.error(
            "❌ No scenes were successfully generated."
        )

        st.info(
            "The Hugging Face Space may be "
            "temporarily unavailable or out of "
            "ZeroGPU capacity."
        )

        st.stop()

    # ========================================================
    # ONE SCENE
    # ========================================================

    if len(generated_files) == 1:

        final_file = Path(
            generated_files[0]
        )

    # ========================================================
    # MULTIPLE SCENES
    # ========================================================

    else:

        try:

            import subprocess

            concat_file = (
                OUTPUT_DIR
                / "concat.txt"
            )

            with open(
                concat_file,
                "w",
                encoding="utf-8"
            ) as f:

                for file in generated_files:

                    absolute_path = (
                        Path(file)
                        .resolve()
                        .as_posix()
                    )

                    f.write(
                        "file '"
                        + absolute_path
                        + "'\n"
                    )

            final_file = (
                OUTPUT_DIR
                / "final_story.mp4"
            )

            command = [

                "ffmpeg",
                "-y",

                "-f",
                "concat",

                "-safe",
                "0",

                "-i",
                str(concat_file),

                "-c:v",
                "libx264",

                "-pix_fmt",
                "yuv420p",

                "-c:a",
                "aac",

                str(final_file)
            ]

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result.returncode != 0:

                raise RuntimeError(
                    result.stderr
                )

        except Exception as e:

            st.warning(
                "Could not combine scenes."
            )

            st.code(
                str(e)
            )

            st.info(
                "Individual scene videos "
                "are still available above."
            )

            st.stop()

    # ========================================================
    # FINAL
    # ========================================================

    st.success(
        "🎉 FINAL VIDEO CREATED!"
    )

    st.video(
        str(final_file)
    )

    with open(
        final_file,
        "rb"
    ) as f:

        st.download_button(

            "⬇️ DOWNLOAD FINAL VIDEO",

            f.read(),

            file_name=
            "final_story.mp4",

            mime=
            "video/mp4",

            type=
            "primary",

            use_container_width=True,

            key=
            "final_download"
        )
