import os
import json
import time
import shutil
import subprocess
from pathlib import Path

import requests
import streamlit as st


# ============================================================
# OPTIONAL PACKAGES
# ============================================================

try:
    from groq import Groq
except Exception:
    Groq = None

try:
    from gradio_client import Client
except Exception:
    Client = None


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Story Video Studio",
    page_icon="🎬",
    layout="wide"
)


# ============================================================
# CONFIG
# ============================================================

HF_SPACE = "Lightricks/ltx-video-distilled"

# Current active Groq model
GROQ_MODEL = "openai/gpt-oss-20b"

OUTPUT_DIR = Path("generated_story")

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# READ SECRETS
# ============================================================

def get_secret(name, default=""):

    try:
        value = st.secrets.get(name)

        if value:
            return str(value).strip()

    except Exception:
        pass

    return os.getenv(
        name,
        default
    ).strip()


GROQ_API_KEY = get_secret(
    "GROQ_API_KEY"
)

HF_TOKEN = get_secret(
    "HF_TOKEN"
)

PIXABAY_API_KEY = get_secret(
    "PIXABAY_API_KEY"
)


# ============================================================
# PAGE CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        text-align: center;
        font-size: 46px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        opacity: 0.7;
        font-size: 18px;
        margin-bottom: 30px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🎬 AI Story Video Studio</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Story → AI storyboard → real video scenes → final MP4'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Settings")

    visual_style = st.selectbox(
        "🎨 Visual Style",
        [
            "Cinematic",
            "Photorealistic",
            "Fantasy",
            "3D Animation",
            "Anime",
            "Sci-Fi",
            "Cyberpunk",
            "Dark Fantasy",
            "Digital Art",
            "Comic Book"
        ]
    )

    aspect_ratio = st.selectbox(
        "📐 Aspect Ratio",
        [
            "16:9",
            "9:16",
            "1:1"
        ]
    )

    scene_count = st.slider(
        "🎞️ Number of Scenes",
        1,
        4,
        2
    )

    duration = st.slider(
        "⏱️ Scene Duration",
        0.5,
        8.0,
        2.0,
        0.5
    )

    use_pixabay = st.checkbox(
        "🖼️ Pixabay Reference Images",
        True
    )

    st.markdown("---")

    st.subheader("🔌 API Status")

    if GROQ_API_KEY:
        st.success("Groq ✓")
    else:
        st.error("Groq API missing")

    if HF_TOKEN:
        st.success("Hugging Face token ✓")
    else:
        st.info(
            "Hugging Face token optional"
        )

    if PIXABAY_API_KEY:
        st.success("Pixabay ✓")
    else:
        st.info(
            "Pixabay optional"
        )


# ============================================================
# STORY INPUT
# ============================================================

st.subheader("📖 Your Story")

story = st.text_area(
    "Write your story",
    height=250,
    placeholder=(
        "Example:\n\n"
        "A young woman walks alone through a snow-covered "
        "forest during a violent winter storm. She eventually "
        "finds a small clearing with a dying fire. She sits "
        "beside the fire and warms her hands while snow "
        "continues falling around her."
    )
)


# ============================================================
# CHARACTER
# ============================================================

with st.expander(
    "👤 Character Description"
):

    character = st.text_area(
        "Describe the main character",
        height=130,
        placeholder=(
            "A 24-year-old woman with long dark hair, "
            "a dark green winter coat, brown boots, "
            "black gloves and a small leather backpack."
        )
    )


# ============================================================
# CINEMATIC SETTINGS
# ============================================================

with st.expander(
    "🎥 Extra Cinematic Instructions"
):

    extra_details = st.text_area(
        "Optional instructions",
        height=130,
        placeholder=(
            "Slow cinematic camera movement, realistic "
            "lighting, atmospheric particles, natural "
            "character movement, detailed environment."
        )
    )


# ============================================================
# DIMENSIONS
# ============================================================

def get_dimensions(ratio):

    if ratio == "16:9":
        return 512, 704

    if ratio == "9:16":
        return 704, 512

    return 512, 512


# ============================================================
# CLEAN JSON
# ============================================================

def clean_json(text):

    if not text:
        raise RuntimeError(
            "Groq returned an empty response."
        )

    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


# ============================================================
# GROQ STORYBOARD GENERATION
# ============================================================

def create_storyboard():

    if not GROQ_API_KEY:

        raise RuntimeError(
            "GROQ_API_KEY is missing.\n\n"
            "Add it in Streamlit Secrets."
        )

    if Groq is None:

        raise RuntimeError(
            "groq package is not installed."
        )

    client = Groq(
        api_key=GROQ_API_KEY
    )

    prompt = f"""
You are a professional film director,
storyboard artist and AI video prompt engineer.

Turn the following story into exactly
{scene_count} connected cinematic scenes.

STORY:
{story}

MAIN CHARACTER:
{character}

VISUAL STYLE:
{visual_style}

ASPECT RATIO:
{aspect_ratio}

EXTRA INSTRUCTIONS:
{extra_details}

IMPORTANT:

Every scene must directly represent the story.

The scenes must connect together.

The same character must remain visually consistent.

Maintain:

- same face
- same age
- same hairstyle
- same hair color
- same clothing
- same accessories
- same body appearance

Each scene must contain:

1. Story action
2. Detailed video prompt
3. Negative prompt
4. Pixabay search query

The video prompt must describe:

- character movement
- environmental movement
- camera movement
- lighting
- atmosphere
- important objects
- beginning and ending of the shot

Do NOT create static image prompts.

These prompts will be sent directly to
a text-to-video AI model.

Make the prompts cinematic and highly visual.

Return ONLY valid JSON.

Use exactly:

{{
    "title": "short story title",

    "character_bible":
    "detailed character description",

    "scenes": [

        {{
            "scene_number": 1,

            "title":
            "short scene title",

            "story_action":
            "what happens",

            "video_prompt":
            "detailed moving video prompt",

            "negative_prompt":
            "things to avoid",

            "pixabay_query":
            "short search query"
        }}
    ]
}}
"""

    try:

        response = client.chat.completions.create(

            model=GROQ_MODEL,

            messages=[

                {
                    "role": "system",
                    "content":
                    "You are a professional "
                    "storyboard generator. "
                    "Return JSON only."
                },

                {
                    "role": "user",
                    "content": prompt
                }

            ],

            temperature=0.25,

            response_format={
                "type": "json_object"
            },

            max_tokens=7000
        )

    except Exception as e:

        raise RuntimeError(
            "Groq request failed:\n\n"
            + str(e)
        )

    content = (
        response
        .choices[0]
        .message
        .content
    )

    content = clean_json(
        content
    )

    try:

        data = json.loads(
            content
        )

    except Exception as e:

        raise RuntimeError(
            "Groq returned invalid JSON:\n\n"
            + str(e)
            + "\n\n"
            + content
        )

    scenes = data.get(
        "scenes",
        []
    )

    if not scenes:

        raise RuntimeError(
            "No scenes were returned by Groq."
        )

    return data


# ============================================================
# PIXABAY SEARCH
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

        response.raise_for_status()

        data = response.json()

        results = []

        for item in data.get(
            "hits",
            []
        ):

            results.append(
                {
                    "image":
                    item.get(
                        "webformatURL"
                    ),

                    "large":
                    item.get(
                        "largeImageURL"
                    ),

                    "tags":
                    item.get(
                        "tags",
                        ""
                    )
                }
            )

        return results

    except Exception:

        return []


# ============================================================
# HUGGING FACE CLIENT
# ============================================================

@st.cache_resource(
    show_spinner=False
)
def get_hf_client():

    if Client is None:

        raise RuntimeError(
            "gradio_client is not installed.\n\n"
            "Add gradio_client to requirements.txt."
        )

    try:

        # IMPORTANT:
        #
        # Current Gradio Client uses:
        #
        # token=
        #
        # NOT:
        #
        # hf_token=

        if HF_TOKEN:

            client = Client(
                HF_SPACE,
                token=HF_TOKEN,
                verbose=False
            )

        else:

            client = Client(
                HF_SPACE,
                verbose=False
            )

        return client

    except Exception as e:

        raise RuntimeError(
            "Could not connect to Hugging Face:\n\n"
            + str(e)
        )


# ============================================================
# GENERATE VIDEO USING LTX
# ============================================================

def generate_video(
    prompt,
    negative_prompt,
    duration_seconds,
    ratio,
    seed,
    status_box
):

    client = get_hf_client()

    height, width = get_dimensions(
        ratio
    )

    status_box.info(
        "🔗 Connected to Hugging Face LTX Video..."
    )

    # --------------------------------------------------------
    # CURRENT LTX API
    # --------------------------------------------------------
    #
    # Current public Space expects:
    #
    # 1 prompt
    # 2 negative prompt
    # 3 image
    # 4 video
    # 5 height
    # 6 width
    # 7 mode
    # 8 duration
    # 9 frames to use
    # 10 seed
    # 11 randomize seed
    # 12 guidance scale
    # 13 improve texture
    #
    # Endpoint:
    #
    # /text_to_video
    #
    # --------------------------------------------------------

    try:

        job = client.submit(

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

        status_box.info(
            "⏳ LTX is generating the actual video..."
        )

        result = job.result()

    except Exception as first_error:

        # ----------------------------------------------------
        # FALLBACK TO PREDICT
        # ----------------------------------------------------

        try:

            status_box.warning(
                "🔄 Retrying video request..."
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

        except Exception as second_error:

            raise RuntimeError(
                "LTX Video generation failed.\n\n"

                "First attempt:\n"
                + str(first_error)

                + "\n\n"

                "Second attempt:\n"
                + str(second_error)
            )

    # ========================================================
    # EXTRACT RESULT
    # ========================================================

    video_path = None

    if isinstance(
        result,
        (list, tuple)
    ):

        if len(result) > 0:

            video_path = result[0]

    else:

        video_path = result

    # ========================================================
    # GRADIO FILE DATA
    # ========================================================

    if hasattr(
        video_path,
        "path"
    ):

        video_path = (
            video_path.path
        )

    elif isinstance(
        video_path,
        dict
    ):

        video_path = (
            video_path.get("path")
            or video_path.get("url")
        )

    if not video_path:

        raise RuntimeError(
            "Hugging Face returned no video."
        )

    status_box.success(
        "✅ Actual video generated."
    )

    return str(
        video_path
    )


# ============================================================
# SAVE GENERATED VIDEO
# ============================================================

def save_video(
    source,
    destination
):

    destination = Path(
        destination
    )

    # Local file

    if source and Path(
        str(source)
    ).exists():

        shutil.copy2(
            str(source),
            str(destination)
        )

        return str(
            destination
        )

    # URL

    source_string = str(
        source
    )

    if (
        source_string.startswith(
            "http://"
        )
        or
        source_string.startswith(
            "https://"
        )
    ):

        response = requests.get(
            source_string,
            timeout=180
        )

        response.raise_for_status()

        destination.write_bytes(
            response.content
        )

        return str(
            destination
        )

    raise RuntimeError(
        "Could not locate generated video:\n"
        + source_string
    )


# ============================================================
# FFMPEG CHECK
# ============================================================

def ffmpeg_available():

    try:

        result = subprocess.run(
            [
                "ffmpeg",
                "-version"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        return result.returncode == 0

    except Exception:

        return False


# ============================================================
# COMBINE VIDEOS
# ============================================================

def combine_videos(
    video_files,
    output_file
):

    if not video_files:

        raise RuntimeError(
            "No scene videos available."
        )

    if not ffmpeg_available():

        raise RuntimeError(
            "FFmpeg is not installed.\n\n"
            "Make sure packages.txt contains:\n"
            "ffmpeg"
        )

    output_file = Path(
        output_file
    )

    concat_file = (
        OUTPUT_DIR
        / "concat.txt"
    )

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as f:

        for video in video_files:

            path = (
                Path(video)
                .resolve()
                .as_posix()
            )

            f.write(
                "file '"
                + path.replace(
                    "'",
                    "'\\''"
                )
                + "'\n"
            )

    # --------------------------------------------------------
    # TRY STREAM COPY
    # --------------------------------------------------------

    command = [

        "ffmpeg",
        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(concat_file),

        "-c",
        "copy",

        str(output_file)
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # --------------------------------------------------------
    # FALLBACK TRANSCODE
    # --------------------------------------------------------

    if result.returncode != 0:

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

            "-preset",
            "veryfast",

            "-pix_fmt",
            "yuv420p",

            "-c:a",
            "aac",

            str(output_file)
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

    if result.returncode != 0:

        raise RuntimeError(
            "FFmpeg failed:\n\n"
            + result.stderr
        )

    if not output_file.exists():

        raise RuntimeError(
            "Final video was not created."
        )

    return str(
        output_file
    )


# ============================================================
# CLEAN OLD OUTPUT
# ============================================================

def clean_outputs():

    for file in OUTPUT_DIR.glob(
        "scene_*.mp4"
    ):

        try:
            file.unlink()
        except Exception:
            pass

    final = (
        OUTPUT_DIR
        / "final_story.mp4"
    )

    if final.exists():

        try:
            final.unlink()
        except Exception:
            pass


# ============================================================
# BUILD FINAL VIDEO PROMPT
# ============================================================

def build_video_prompt(
    scene,
    character_bible
):

    return f"""
Create an actual cinematic moving video.

ORIGINAL STORY:

{story}


CHARACTER CONSISTENCY:

{character_bible}


CURRENT SCENE:

{scene.get("story_action", "")}


DIRECTOR VIDEO PROMPT:

{scene.get("video_prompt", "")}


VISUAL STYLE:

{visual_style}


ASPECT RATIO:

{aspect_ratio}


EXTRA CINEMATIC DIRECTION:

{extra_details}


CHARACTER CONSISTENCY IS CRITICAL.

Keep the same:

face,
age,
hair,
hair color,
clothing,
body,
accessories,
overall appearance.


ANIMATION:

The character must move naturally.

The environment must also move naturally.

Use realistic physics.

Examples:

snow falling,
wind moving clothing,
trees moving,
fire flickering,
smoke rising,
dust floating,
water moving,
hair moving in wind,
particles passing through the camera.


CAMERA:

Use appropriate cinematic movement.

Examples:

slow tracking shot,
dolly shot,
push-in,
pull-back,
side tracking,
handheld cinematic movement,
establishing shot.


LIGHTING:

Use cinematic lighting appropriate
to the scene.


IMPORTANT:

This MUST be an actual moving video.

Do NOT create a still photograph.

Do NOT create a slideshow.

Do NOT add text.

Do NOT add subtitles.

Do NOT add logos.

Do NOT add watermarks.

Do NOT introduce unrelated characters.

Do NOT introduce unrelated objects.

Do NOT change the character's clothing.

Do NOT change the character's appearance.


The video must visually represent
the current scene from the story.
"""


# ============================================================
# GENERATE BUTTON
# ============================================================

generate_button = st.button(
    "🚀 GENERATE COMPLETE VIDEO",
    type="primary",
    use_container_width=True
)


# ============================================================
# MAIN GENERATION
# ============================================================

if generate_button:

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

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

    if Client is None:

        st.error(
            "gradio_client is not installed."
        )

        st.stop()

    # --------------------------------------------------------
    # CLEAN
    # --------------------------------------------------------

    clean_outputs()

    # ========================================================
    # STEP 1
    # ========================================================

    st.header(
        "🧠 Step 1 — Creating Storyboard"
    )

    storyboard_status = st.empty()

    storyboard_status.info(
        "Groq is analyzing your story..."
    )

    try:

        storyboard = (
            create_storyboard()
        )

    except Exception as e:

        storyboard_status.error(
            "❌ Storyboard generation failed."
        )

        st.code(
            str(e)
        )

        st.stop()

    storyboard_status.success(
        "✅ Storyboard created."
    )

    # --------------------------------------------------------
    # STORY INFO
    # --------------------------------------------------------

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

    with st.expander(
        "👤 Character Bible"
    ):

        st.write(
            character_bible
        )

    # ========================================================
    # STORYBOARD
    # ========================================================

    st.subheader(
        "🎞️ Scenes"
    )

    for scene in scenes:

        number = scene.get(
            "scene_number",
            "?"
        )

        scene_title = scene.get(
            "title",
            "Scene"
        )

        st.markdown(
            f"### 🎬 Scene {number}: {scene_title}"
        )

        st.write(
            scene.get(
                "story_action",
                ""
            )
        )

    # ========================================================
    # STEP 2
    # ========================================================

    st.header(
        "🎥 Step 2 — Creating Actual Videos"
    )

    st.info(
        "The prompts below are being sent to "
        "the Hugging Face LTX text-to-video model."
    )

    total = len(
        scenes
    )

    progress = st.progress(
        0
    )

    video_files = []

    # ========================================================
    # GENERATE EACH SCENE
    # ========================================================

    for index, scene in enumerate(
        scenes
    ):

        number = scene.get(
            "scene_number",
            index + 1
        )

        scene_title = scene.get(
            "title",
            f"Scene {number}"
        )

        st.markdown(
            f"## 🎬 Scene {number}: {scene_title}"
        )

        st.write(
            scene.get(
                "story_action",
                ""
            )
        )

        final_prompt = build_video_prompt(
            scene,
            character_bible
        )

        with st.expander(
            "🔍 View Video Prompt"
        ):

            st.write(
                final_prompt
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

        status.info(
            f"⏳ Generating Scene "
            f"{number}/{total}..."
        )

        try:

            generated = generate_video(

                prompt=final_prompt,

                negative_prompt=negative_prompt,

                duration_seconds=duration,

                ratio=aspect_ratio,

                seed=1000 + int(number),

                status_box=status
            )

            local_file = (
                OUTPUT_DIR
                / f"scene_{number}.mp4"
            )

            save_video(
                generated,
                local_file
            )

            if not local_file.exists():

                raise RuntimeError(
                    "The video was generated "
                    "but could not be saved."
                )

            if local_file.stat().st_size < 1000:

                raise RuntimeError(
                    "The returned video file "
                    "is empty or invalid."
                )

            video_files.append(
                str(local_file)
            )

            status.success(
                f"✅ Scene {number} completed."
            )

            # ------------------------------------------------
            # SHOW VIDEO
            # ------------------------------------------------

            st.video(
                str(local_file)
            )

            # ------------------------------------------------
            # DOWNLOAD SCENE
            # ------------------------------------------------

            with open(
                local_file,
                "rb"
            ) as f:

                st.download_button(

                    f"⬇️ Download Scene {number}",

                    f.read(),

                    file_name=
                    f"scene_{number}.mp4",

                    mime=
                    "video/mp4",

                    key=
                    f"scene_download_{number}",

                    use_container_width=True
                )

        except Exception as e:

            status.error(
                f"❌ Scene {number} failed."
            )

            st.code(
                str(e)
            )

        # ----------------------------------------------------
        # PIXABAY REFERENCE
        # ----------------------------------------------------

        if use_pixabay:

            query = scene.get(
                "pixabay_query",
                ""
            )

            references = search_pixabay(
                query
            )

            if references:

                with st.expander(
                    f"🖼️ Scene {number} "
                    f"Reference Images"
                ):

                    cols = st.columns(3)

                    for i, ref in enumerate(
                        references
                    ):

                        with cols[
                            i % 3
                        ]:

                            if ref.get(
                                "image"
                            ):

                                st.image(
                                    ref["image"],
                                    use_container_width=True
                                )

                            if ref.get(
                                "tags"
                            ):

                                st.caption(
                                    ref["tags"]
                                )

        progress.progress(
            (index + 1) / total
        )

        time.sleep(1)

    # ========================================================
    # STEP 3
    # ========================================================

    st.header(
        "🎞️ Step 3 — Creating Final Video"
    )

    if not video_files:

        st.error(
            "❌ No scenes were successfully generated."
        )

        st.warning(
            "Hugging Face LTX may currently be busy "
            "or its public ZeroGPU capacity may be unavailable."
        )

        st.stop()

    st.success(
        f"✅ {len(video_files)} scene(s) generated."
    )

    final_video = (
        OUTPUT_DIR
        / "final_story.mp4"
    )

    combine_status = st.empty()

    combine_status.info(
        "🎬 Combining all scenes..."
    )

    try:

        combine_videos(
            video_files,
            final_video
        )

    except Exception as e:

        combine_status.error(
            "❌ Could not create final video."
        )

        st.code(
            str(e)
        )

        st.info(
            "The individual scene videos "
            "are still available above."
        )

        st.stop()

    combine_status.success(
        "🎉 Final video created!"
    )

    # ========================================================
    # FINAL VIDEO
    # ========================================================

    st.header(
        "🎬 FINAL STORY VIDEO"
    )

    st.video(
        str(final_video)
    )

    # ========================================================
    # DOWNLOAD FINAL
    # ========================================================

    with open(
        final_video,
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
            "final_video_download"
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    st.markdown("---")

    st.subheader(
        "📊 Generation Summary"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Scenes",
            len(video_files)
        )

    with c2:

        st.metric(
            "Duration / Scene",
            f"{duration}s"
        )

    with c3:

        st.metric(
            "Format",
            aspect_ratio
        )

    with c4:

        st.metric(
            "Style",
            visual_style
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "AI Story Video Studio • "
    "Groq + Hugging Face LTX Video + Pixabay + FFmpeg"
)
