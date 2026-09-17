import streamlit as st
import os
import json
import time
import shutil
import subprocess
from pathlib import Path

import requests


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Story Video Studio",
    page_icon="🎬",
    layout="wide"
)


# ============================================================
# SECRETS
# ============================================================

def get_secret(name, default=""):
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


GROQ_API_KEY = get_secret("GROQ_API_KEY")
HF_TOKEN = get_secret("HF_TOKEN")
PIXABAY_API_KEY = get_secret("PIXABAY_API_KEY")


# ============================================================
# CURRENT GROQ MODEL
# ============================================================

GROQ_MODEL = "openai/gpt-oss-20b"


# ============================================================
# CURRENT HUGGING FACE VIDEO SPACE
# ============================================================

HF_VIDEO_SPACE = "Lightricks/ltx-video-distilled"


# ============================================================
# GRADIO CLIENT
# ============================================================

try:
    from gradio_client import Client

    GRADIO_AVAILABLE = True

except Exception as e:
    Client = None
    GRADIO_AVAILABLE = False
    GRADIO_ERROR = str(e)


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
        margin-top: 10px;
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        color: #777;
        font-size: 18px;
        margin-bottom: 30px;
    }

    .scene-card {
        padding: 18px;
        border-radius: 14px;
        border: 1px solid rgba(128,128,128,0.25);
        margin-bottom: 20px;
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
    'Turn your story into multiple AI-generated video scenes'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Video Settings")

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
        min_value=1,
        max_value=4,
        value=2
    )

    duration = st.slider(
        "⏱️ Seconds per Scene",
        min_value=0.5,
        max_value=5.0,
        value=2.0,
        step=0.5
    )

    use_pixabay = st.checkbox(
        "🖼️ Show Pixabay Reference Images",
        value=True
    )

    st.markdown("---")

    st.header("🔌 API Status")

    if GROQ_API_KEY:
        st.success("Groq API ✓")
    else:
        st.error("Groq API missing")

    if HF_TOKEN:
        st.success("Hugging Face ✓")
    else:
        st.warning(
            "HF_TOKEN not configured"
        )

    if PIXABAY_API_KEY:
        st.success("Pixabay ✓")
    else:
        st.info(
            "Pixabay optional"
        )

    st.markdown("---")

    st.caption(
        "AI Video Engine"
    )

    st.caption(
        "LTX Video • Hugging Face ZeroGPU"
    )


# ============================================================
# STORY INPUT
# ============================================================

st.subheader("📖 Your Story")

story = st.text_area(
    "Enter your complete story",
    height=220,
    placeholder=(
        "Example:\n\n"
        "A young explorer enters an ancient magical forest "
        "at night. The trees glow blue. She discovers an "
        "ancient crystal. When she touches the crystal, "
        "blue energy spreads through the forest and slowly "
        "changes everything from blue to purple and then "
        "golden light. A giant portal opens between the trees."
    )
)


# ============================================================
# CHARACTER
# ============================================================

with st.expander("👤 Main Character"):

    character = st.text_area(
        "Describe the main character",
        height=130,
        placeholder=(
            "A 22-year-old female explorer with long dark "
            "hair, brown leather jacket, dark trousers, "
            "hiking boots and a small backpack."
        )
    )


# ============================================================
# EXTRA DETAILS
# ============================================================

with st.expander("🎬 Extra Cinematic Instructions"):

    extra_details = st.text_area(
        "Optional instructions",
        height=120,
        placeholder=(
            "Slow camera movement, dramatic lighting, "
            "magical particles, cinematic depth of field, "
            "realistic motion."
        )
    )


# ============================================================
# GROQ STORYBOARD
# ============================================================

def create_storyboard():

    if not GROQ_API_KEY:

        raise Exception(
            "GROQ_API_KEY is missing.\n\n"
            "Go to Streamlit → Settings → Secrets "
            "and add your Groq API key."
        )


    try:

        from groq import Groq

    except Exception as e:

        raise Exception(
            "The Groq package is not installed.\n\n"
            + str(e)
        )


    client = Groq(
        api_key=GROQ_API_KEY
    )


    prompt = f"""
You are an expert film director, storyboard artist,
and AI video prompt engineer.

Your job is to convert the user's story into a
connected cinematic video.

USER STORY:

{story}

MAIN CHARACTER:

{character}

VISUAL STYLE:

{visual_style}

ASPECT RATIO:

{aspect_ratio}

EXTRA INSTRUCTIONS:

{extra_details}

Create exactly {scene_count} connected scenes.

VERY IMPORTANT:

Every scene must come directly from the story.

Do NOT create unrelated scenes.

The same character must remain consistent.

Maintain:

- same face
- same age
- same hairstyle
- same clothing
- same body appearance
- same important objects

across every scene.

Every scene must have actual movement.

Describe:

- character movement
- camera movement
- environment movement
- lighting
- atmosphere
- colors
- objects
- action
- transition

If the story contains a color transformation,
make it visually progressive.

For example:

BLUE → PURPLE → GOLD

must be shown as a visible environmental
transformation rather than simply saying
"the forest is colorful."

The final video prompts must be useful to
a text-to-video AI model.

Avoid static descriptions.

Return ONLY valid JSON.

Use exactly this format:

{{
    "title": "short story title",

    "character_bible":
    "complete description of the consistent character",

    "scenes": [

        {{
            "scene_number": 1,

            "title":
            "short scene title",

            "story_action":
            "what happens",

            "video_prompt":
            "very detailed cinematic video prompt",

            "negative_prompt":
            "things the video model should avoid",

            "pixabay_query":
            "short search phrase"
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
                    "cinematic storyboard generator. "
                    "Return valid JSON only."
                },

                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.3,

            response_format={
                "type": "json_object"
            },

            max_tokens=7000,

            include_reasoning=False
        )

    except Exception as e:

        raise Exception(
            "Groq request failed.\n\n"
            + str(e)
        )


    text = (
        response
        .choices[0]
        .message
        .content
    )


    if not text:

        raise Exception(
            "Groq returned an empty response."
        )


    text = text.strip()


    if text.startswith("```json"):

        text = text[7:]


    if text.startswith("```"):

        text = text[3:]


    if text.endswith("```"):

        text = text[:-3]


    text = text.strip()


    try:

        data = json.loads(
            text
        )

    except Exception:

        raise Exception(
            "Groq returned invalid JSON.\n\n"
            "Response:\n\n"
            + text
        )


    return data


# ============================================================
# PIXABAY SEARCH
# ============================================================

def search_pixabay(query):

    if not PIXABAY_API_KEY:
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
# VIDEO DIMENSIONS
# ============================================================

def get_dimensions(ratio):

    if ratio == "16:9":

        return 512, 896

    if ratio == "9:16":

        return 896, 512

    return 512, 512


# ============================================================
# HUGGING FACE CLIENT
# ============================================================

@st.cache_resource
def get_hf_client():

    if not GRADIO_AVAILABLE:

        raise Exception(
            "gradio_client is not installed.\n\n"
            "Add gradio_client to requirements.txt."
        )


    try:

        if HF_TOKEN:

            client = Client(
                HF_VIDEO_SPACE,
                hf_token=HF_TOKEN
            )

        else:

            client = Client(
                HF_VIDEO_SPACE
            )


        return client


    except Exception as e:

        raise Exception(
            "Could not connect to Hugging Face.\n\n"
            + str(e)
        )


# ============================================================
# GENERATE VIDEO
# ============================================================

def generate_video(
    prompt,
    negative_prompt,
    duration_seconds,
    ratio,
    seed
):

    client = get_hf_client()


    height, width = get_dimensions(
        ratio
    )


    # The current LTX Space uses:
    #
    # prompt
    # negative_prompt
    # hidden image
    # hidden video
    # height
    # width
    # task
    # duration
    # frames_to_use
    # seed
    # randomize_seed
    # guidance_scale
    # improve_texture
    #
    # The public Space currently exposes
    # this through /text_to_video.

    try:

        result = client.predict(

            prompt,

            negative_prompt,

            None,

            None,

            height,

            width,

            "text-to-video",

            float(duration_seconds),

            9,

            int(seed),

            True,

            3.0,

            True,

            api_name="/text_to_video"
        )


    except Exception as e:

        raise Exception(
            "Hugging Face video generation failed.\n\n"
            + str(e)
        )


    # --------------------------------------------------------
    # EXTRACT VIDEO PATH
    # --------------------------------------------------------

    video_path = None


    if isinstance(
        result,
        (list, tuple)
    ):

        if len(result) > 0:

            video_path = result[0]

    else:

        video_path = result


    if not video_path:

        raise Exception(
            "Hugging Face returned no video."
        )


    return str(video_path)


# ============================================================
# COPY GENERATED VIDEO
# ============================================================

def copy_video(
    source,
    destination
):

    source = Path(
        source
    )

    destination = Path(
        destination
    )


    if not source.exists():

        raise Exception(
            "Video file does not exist:\n"
            + str(source)
        )


    shutil.copy2(
        source,
        destination
    )


    return str(destination)


# ============================================================
# COMBINE VIDEO FILES
# ============================================================

def combine_videos(
    video_files,
    output_file
):

    if not video_files:

        raise Exception(
            "There are no videos to combine."
        )


    output_file = Path(
        output_file
    )


    concat_file = (
        output_file.parent
        / "concat_list.txt"
    )


    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as file:

        for video in video_files:

            path = (
                Path(video)
                .resolve()
                .as_posix()
            )

            file.write(
                "file '"
                + path
                + "'\n"
            )


    # --------------------------------------------------------
    # FIRST ATTEMPT
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


    process = subprocess.run(

        command,

        stdout=subprocess.PIPE,

        stderr=subprocess.PIPE,

        text=True
    )


    # --------------------------------------------------------
    # FALLBACK RE-ENCODING
    # --------------------------------------------------------

    if process.returncode != 0:

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

            str(output_file)
        ]


        process = subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True
        )


    if process.returncode != 0:

        raise Exception(
            "FFmpeg failed.\n\n"
            + process.stderr
        )


    if not output_file.exists():

        raise Exception(
            "Final video was not created."
        )


    return str(output_file)


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
    # STORY VALIDATION
    # --------------------------------------------------------

    if not story.strip():

        st.warning(
            "Please enter a story first."
        )

        st.stop()


    # --------------------------------------------------------
    # GROQ VALIDATION
    # --------------------------------------------------------

    if not GROQ_API_KEY:

        st.error(
            "GROQ_API_KEY is missing."
        )

        st.stop()


    # --------------------------------------------------------
    # CREATE DIRECTORY
    # --------------------------------------------------------

    work_dir = Path(
        "generated_story"
    )

    work_dir.mkdir(
        exist_ok=True
    )


    # --------------------------------------------------------
    # CLEAN OLD FILES
    # --------------------------------------------------------

    for old_file in work_dir.glob(
        "scene_*.mp4"
    ):

        try:
            old_file.unlink()
        except Exception:
            pass


    old_final = (
        work_dir
        / "final_story.mp4"
    )

    if old_final.exists():

        try:
            old_final.unlink()
        except Exception:
            pass


    # ========================================================
    # STEP 1 — STORYBOARD
    # ========================================================

    st.header(
        "🧠 Step 1 — Creating Storyboard"
    )


    with st.spinner(
        "Analyzing your story..."
    ):

        try:

            storyboard = (
                create_storyboard()
            )

        except Exception as e:

            st.error(
                "❌ Storyboard generation failed."
            )

            st.code(
                str(e)
            )

            st.stop()


    scenes = storyboard.get(
        "scenes",
        []
    )


    character_bible = storyboard.get(
        "character_bible",
        character
    )


    story_title = storyboard.get(
        "title",
        "AI Story"
    )


    if not scenes:

        st.error(
            "No scenes were generated."
        )

        st.stop()


    # --------------------------------------------------------
    # SHOW STORY TITLE
    # --------------------------------------------------------

    st.success(
        f"Storyboard created: {story_title}"
    )


    # --------------------------------------------------------
    # CHARACTER BIBLE
    # --------------------------------------------------------

    with st.expander(
        "👤 Character Consistency Bible"
    ):

        st.write(
            character_bible
        )


    # ========================================================
    # SHOW STORYBOARD
    # ========================================================

    st.subheader(
        "🎞️ Storyboard"
    )


    for scene in scenes:

        scene_number = scene.get(
            "scene_number",
            "?"
        )

        title = scene.get(
            "title",
            "Scene"
        )

        action = scene.get(
            "story_action",
            ""
        )


        st.markdown(
            f"**Scene {scene_number}: {title}**"
        )

        st.write(
            action
        )


    # ========================================================
    # STEP 2 — VIDEO
    # ========================================================

    st.header(
        "🎥 Step 2 — Generating Actual Videos"
    )


    st.info(
        "Hugging Face ZeroGPU is a shared free GPU. "
        "Generation can take time or fail when the "
        "public queue is busy."
    )


    video_files = []


    progress = st.progress(
        0
    )


    status = st.empty()


    total = len(
        scenes
    )


    # ========================================================
    # GENERATE EACH SCENE
    # ========================================================

    for index, scene in enumerate(
        scenes
    ):

        scene_number = scene.get(
            "scene_number",
            index + 1
        )

        title = scene.get(
            "title",
            f"Scene {scene_number}"
        )

        story_action = scene.get(
            "story_action",
            ""
        )

        video_prompt = scene.get(
            "video_prompt",
            ""
        )

        negative_prompt = scene.get(
            "negative_prompt",
            "blurry, distorted, "
            "jittery motion, bad anatomy, "
            "duplicate characters, "
            "text, logo, watermark"
        )

        pixabay_query = scene.get(
            "pixabay_query",
            ""
        )


        # ----------------------------------------------------
        # SCENE CARD
        # ----------------------------------------------------

        st.markdown(
            f"## 🎬 Scene {scene_number}: {title}"
        )


        st.write(
            story_action
        )


        # ----------------------------------------------------
        # FINAL VIDEO PROMPT
        # ----------------------------------------------------

        final_prompt = f"""
Create a cinematic moving video scene.

SCENE:
{story_action}

MAIN CHARACTER:
{character_bible}

VISUAL STYLE:
{visual_style}

ORIGINAL STORY:
{story}

SCENE-SPECIFIC VIDEO DIRECTION:
{video_prompt}

EXTRA CINEMATIC INSTRUCTIONS:
{extra_details}

IMPORTANT:

This must be an actual moving video.

The character walks, moves, looks,
touches objects or performs the action
described in the story.

The camera must move naturally.

The environment must move naturally.

Lighting must animate.

Particles, smoke, water, leaves,
magic or atmospheric elements should
move when appropriate.

Keep the character visually consistent.

Keep the same:

face,
age,
hair,
clothes,
body,
accessories.

Do not change the character randomly.

If there is a color transformation,
show the transformation progressively.

For example:

blue environment
→ blue-purple transition
→ purple environment
→ purple-gold transition
→ golden environment

Do NOT simply cut from one color
to another.

Do not create unrelated events.

Do not create subtitles.

Do not create text.

Do not create logos.

Do not create watermarks.

Create a cinematic shot that can be
combined with other scenes from the story.
"""


        with st.expander(
            "🔍 View Video Prompt"
        ):

            st.write(
                final_prompt
            )


        # ----------------------------------------------------
        # GENERATE
        # ----------------------------------------------------

        status.info(
            f"🎥 Generating scene "
            f"{scene_number}/{total}..."
        )


        try:

            seed = (
                1000
                + scene_number
            )


            remote_video = generate_video(

                prompt=final_prompt,

                negative_prompt=negative_prompt,

                duration_seconds=duration,

                ratio=aspect_ratio,

                seed=seed
            )


            # ------------------------------------------------
            # LOCAL PATH
            # ------------------------------------------------

            local_video = (

                work_dir
                / f"scene_{scene_number}.mp4"

            )


            copy_video(

                remote_video,

                local_video

            )


            video_files.append(
                str(local_video)
            )


            # ------------------------------------------------
            # DISPLAY
            # ------------------------------------------------

            st.success(
                f"Scene {scene_number} generated!"
            )


            st.video(
                str(local_video)
            )


            # ------------------------------------------------
            # DOWNLOAD SCENE
            # ------------------------------------------------

            with open(
                local_video,
                "rb"
            ) as video_file:

                st.download_button(

                    label=
                    f"⬇️ Download Scene {scene_number}",

                    data=
                    video_file.read(),

                    file_name=
                    f"scene_{scene_number}.mp4",

                    mime=
                    "video/mp4",

                    key=
                    f"scene_download_{scene_number}",

                    use_container_width=True
                )


        except Exception as e:

            st.error(
                f"❌ Scene {scene_number} failed."
            )

            st.code(
                str(e)
            )

            st.warning(
                "If Hugging Face is busy, "
                "wait a little and run the scene again."
            )


        # ----------------------------------------------------
        # PIXABAY
        # ----------------------------------------------------

        if (
            use_pixabay
            and PIXABAY_API_KEY
            and pixabay_query
        ):

            references = search_pixabay(
                pixabay_query
            )


            if references:

                with st.expander(
                    f"🖼️ Scene {scene_number} "
                    f"Reference Images"
                ):

                    columns = st.columns(3)


                    for ref_index, ref in enumerate(
                        references
                    ):

                        with columns[
                            ref_index % 3
                        ]:

                            image_url = ref.get(
                                "image"
                            )


                            if image_url:

                                st.image(
                                    image_url,
                                    use_container_width=True
                                )


                            tags = ref.get(
                                "tags",
                                ""
                            )


                            if tags:

                                st.caption(
                                    tags
                                )


        progress.progress(
            (index + 1) / total
        )


        # Don't hammer the public Space
        time.sleep(2)


    # ========================================================
    # STEP 3 — COMBINE
    # ========================================================

    st.header(
        "🎞️ Step 3 — Creating Final Video"
    )


    if not video_files:

        st.error(
            "No scenes were successfully generated."
        )

        st.stop()


    st.write(
        f"{len(video_files)} video scene(s) "
        "are ready to combine."
    )


    final_video = (
        work_dir
        / "final_story.mp4"
    )


    with st.spinner(
        "Combining scenes with FFmpeg..."
    ):

        try:

            combine_videos(
                video_files,
                str(final_video)
            )

        except Exception as e:

            st.error(
                "❌ Could not combine videos."
            )

            st.code(
                str(e)
            )

            st.stop()


    # ========================================================
    # FINAL RESULT
    # ========================================================

    st.success(
        "🎉 COMPLETE VIDEO CREATED!"
    )


    st.header(
        "🎬 Your Final Story Video"
    )


    st.video(
        str(final_video)
    )


    # ========================================================
    # FINAL DOWNLOAD
    # ========================================================

    with open(
        final_video,
        "rb"
    ) as video_file:

        st.download_button(

            label=
            "⬇️ DOWNLOAD FINAL VIDEO",

            data=
            video_file.read(),

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


    # ========================================================
    # FINAL INFO
    # ========================================================

    st.markdown("---")

    st.subheader(
        "📊 Generation Summary"
    )


    col1, col2, col3 = st.columns(3)


    with col1:

        st.metric(
            "Scenes",
            len(video_files)
        )


    with col2:

        st.metric(
            "Seconds / Scene",
            duration
        )


    with col3:

        st.metric(
            "Aspect Ratio",
            aspect_ratio
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "AI Story Video Studio • "
    "Groq Storyboard + Hugging Face LTX Video + FFmpeg"
)
