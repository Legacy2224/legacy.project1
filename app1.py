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
# GET SECRETS
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
PIXABAY_API_KEY = get_secret("PIXABAY_API_KEY")
HF_TOKEN = get_secret("HF_TOKEN")


# ============================================================
# HUGGING FACE SPACE
# ============================================================

HF_VIDEO_SPACE = "Lightricks/ltx-video-distilled"


# ============================================================
# IMPORT GRADIO CLIENT
# ============================================================

try:
    from gradio_client import Client

    GRADIO_AVAILABLE = True
    GRADIO_ERROR = ""

except Exception as e:

    Client = None
    GRADIO_AVAILABLE = False
    GRADIO_ERROR = str(e)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        text-align: center;
        font-size: 46px;
        font-weight: 800;
        margin-top: 10px;
    }

    .subtitle {
        text-align: center;
        color: #777;
        font-size: 18px;
        margin-bottom: 30px;
    }

    .scene-box {
        padding: 18px;
        border-radius: 14px;
        border: 1px solid rgba(128,128,128,0.25);
        margin-bottom: 18px;
    }

    .success-box {
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #2e7d32;
        margin-top: 15px;
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
    'Create a complete multi-scene AI video for free'
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
        value=3
    )

    duration = st.slider(
        "⏱️ Seconds per Scene",
        min_value=2.0,
        max_value=5.0,
        value=2.0,
        step=0.5
    )

    quality_mode = st.selectbox(
        "✨ Quality",
        [
            "Fast / Free",
            "Balanced"
        ]
    )

    use_pixabay = st.checkbox(
        "🖼️ Show Pixabay References",
        value=True
    )

    st.markdown("---")

    st.header("🔌 API Status")

    if GROQ_API_KEY:
        st.success("Groq ✓")
    else:
        st.error("Groq API missing")

    if HF_TOKEN:
        st.success("Hugging Face ✓")
    else:
        st.warning(
            "HF token not configured"
        )

    if PIXABAY_API_KEY:
        st.success("Pixabay ✓")
    else:
        st.info(
            "Pixabay optional"
        )

    st.markdown("---")

    st.caption(
        "Video engine:"
    )

    st.caption(
        "LTX Video 0.9.8"
    )

    st.caption(
        "Hugging Face ZeroGPU"
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
# OPTIONAL EXTRA DETAILS
# ============================================================

with st.expander("🎬 Extra Cinematic Details"):

    extra_details = st.text_area(
        "Optional instructions",
        height=100,
        placeholder=(
            "Slow camera movement, dramatic lighting, "
            "magical particles, realistic motion, "
            "cinematic depth of field."
        )
    )


# ============================================================
# GROQ STORYBOARD
# ============================================================

def create_storyboard():

    if not GROQ_API_KEY:

        raise Exception(
            "GROQ_API_KEY is missing.\n\n"
            "Add it to Streamlit Secrets."
        )


    try:

        from groq import Groq

    except Exception as e:

        raise Exception(
            "Groq package is not installed.\n\n"
            + str(e)
        )


    client = Groq(
        api_key=GROQ_API_KEY
    )


    prompt = f"""
You are a professional film director,
storyboard artist and AI video prompt engineer.

STORY:

{story}

MAIN CHARACTER:

{character}

VISUAL STYLE:

{visual_style}

ASPECT RATIO:

{aspect_ratio}

EXTRA DETAILS:

{extra_details}

Create exactly {scene_count} connected scenes.

The scenes MUST represent the actual story.

Do not create generic unrelated scenes.

Keep the main character visually consistent.

Keep the same:

- age
- hairstyle
- clothing
- body appearance
- important objects

across all scenes.

Every scene must continue naturally from the
previous scene.

If the story contains a transformation such as:

blue → purple → gold

make that transformation extremely visible
and progressive.

Each scene must describe:

1. what the character does
2. what the environment looks like
3. camera movement
4. lighting
5. colors
6. atmosphere
7. motion
8. important objects
9. transition from previous scene
10. transition to next scene

The video model needs ACTION, not just a
static image description.

Write prompts that describe movement.

For example:

"The camera slowly moves toward the character
while glowing particles swirl around her."

NOT:

"A beautiful magical forest."

Return ONLY valid JSON.

Format:

{{
    "title": "story title",
    "character_bible": "exact character appearance",
    "scenes": [
        {{
            "scene_number": 1,
            "title": "scene title",
            "story_action": "what happens",
            "video_prompt": "detailed video generation prompt",
            "negative_prompt": "things to avoid",
            "pixabay_query": "short reference search query"
        }}
    ]
}}
"""


    try:

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You create cinematic storyboards "
                        "and return strict JSON."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3
        )

    except Exception as e:

        raise Exception(
            "Groq request failed.\n\n"
            + str(e)
        )


    text = response.choices[
        0
    ].message.content


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

        return json.loads(text)

    except Exception:

        raise Exception(
            "Groq returned invalid JSON.\n\n"
            "RAW RESPONSE:\n\n"
            + text
        )


# ============================================================
# PIXABAY
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
                    "image": item.get(
                        "webformatURL"
                    ),
                    "large": item.get(
                        "largeImageURL"
                    ),
                    "tags": item.get(
                        "tags",
                        ""
                    )
                }
            )


        return results


    except Exception:

        return []


# ============================================================
# ASPECT RATIO
# ============================================================

def get_dimensions(ratio):

    if ratio == "16:9":

        return 512, 896

    if ratio == "9:16":

        return 896, 512

    return 704, 704


# ============================================================
# CONNECT TO HUGGING FACE
# ============================================================

@st.cache_resource
def get_hf_client():

    if not GRADIO_AVAILABLE:

        raise Exception(
            "gradio_client is not installed.\n\n"
            + GRADIO_ERROR
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
            "Could not connect to Hugging Face "
            "LTX Video Space.\n\n"
            + str(e)
        )


# ============================================================
# GENERATE ONE VIDEO
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


    # --------------------------------------------------------
    # LTX Video API
    #
    # The current LTX Space exposes:
    #
    # /text_to_video
    #
    # Arguments are based on its current
    # public Gradio API.
    # --------------------------------------------------------

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
    # RESULT
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
# COPY VIDEO TO LOCAL DIRECTORY
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
            "Generated video file was not found:\n"
            + str(source)
        )


    shutil.copy2(
        source,
        destination
    )


    return str(destination)


# ============================================================
# COMBINE VIDEOS
# ============================================================

def combine_videos(
    video_files,
    output_file
):

    if not video_files:

        raise Exception(
            "No video clips available."
        )


    concat_file = (
        Path(
            output_file
        ).parent
        / "concat_list.txt"
    )


    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as file:

        for video in video_files:

            absolute_path = (
                Path(video)
                .resolve()
                .as_posix()
            )

            file.write(
                "file '"
                + absolute_path.replace(
                    "'",
                    "'\\''"
                )
                + "'\n"
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
        "-c",
        "copy",
        output_file
    ]


    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


    if process.returncode != 0:

        # Fallback: re-encode
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
            output_file
        ]


        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )


    if process.returncode != 0:

        raise Exception(
            "FFmpeg could not combine the videos.\n\n"
            + process.stderr
        )


    if not Path(
        output_file
    ).exists():

        raise Exception(
            "Final video was not created."
        )


    return output_file


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
    # VALIDATE STORY
    # --------------------------------------------------------

    if not story.strip():

        st.warning(
            "Please enter your story first."
        )

        st.stop()


    # --------------------------------------------------------
    # CHECK GROQ
    # --------------------------------------------------------

    if not GROQ_API_KEY:

        st.error(
            "GROQ_API_KEY is missing."
        )

        st.info(
            "Add GROQ_API_KEY to Streamlit Secrets."
        )

        st.stop()


    # --------------------------------------------------------
    # CREATE WORK DIRECTORY
    # --------------------------------------------------------

    work_dir = Path(
        "generated_story"
    )

    work_dir.mkdir(
        exist_ok=True
    )


    # --------------------------------------------------------
    # STEP 1
    # --------------------------------------------------------

    st.header(
        "🧠 Step 1 — Story Analysis"
    )


    with st.spinner(
        "Groq is converting your story into cinematic scenes..."
    ):

        try:

            storyboard = create_storyboard()

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
            "No scenes were created."
        )

        st.stop()


    st.success(
        f"Created {len(scenes)} scenes."
    )


    # --------------------------------------------------------
    # SHOW CHARACTER
    # --------------------------------------------------------

    with st.expander(
        "👤 Character Consistency"
    ):

        st.write(
            character_bible
        )


    # --------------------------------------------------------
    # STEP 2
    # --------------------------------------------------------

    st.header(
        "🎥 Step 2 — Generate Video Scenes"
    )


    video_files = []


    total_scenes = len(
        scenes
    )


    progress = st.progress(
        0
    )


    status = st.empty()


    # --------------------------------------------------------
    # EACH SCENE
    # --------------------------------------------------------

    for index, scene in enumerate(
        scenes
    ):

        number = scene.get(
            "scene_number",
            index + 1
        )

        title = scene.get(
            "title",
            f"Scene {number}"
        )

        action = scene.get(
            "story_action",
            ""
        )

        video_prompt = scene.get(
            "video_prompt",
            ""
        )

        negative_prompt = scene.get(
            "negative_prompt",
            ""
        )

        pixabay_query = scene.get(
            "pixabay_query",
            ""
        )


        # ----------------------------------------------------
        # BUILD FINAL VIDEO PROMPT
        # ----------------------------------------------------

        final_prompt = f"""
Create Scene {number} of a continuous cinematic story.

STORY:
{story}

CHARACTER CONSISTENCY:
{character_bible}

SCENE:
{action}

VISUAL STYLE:
{visual_style}

ASPECT RATIO:
{aspect_ratio}

SCENE VIDEO PROMPT:
{video_prompt}

EXTRA CINEMATIC DETAILS:
{extra_details}

IMPORTANT:

The character must remain visually consistent.

Keep the same clothing, hairstyle,
age and physical appearance.

The scene must contain real motion.

Use natural camera movement.

Animate the environment.

Animate particles, lighting and objects
when appropriate.

If this scene contains a transformation,
make the transformation progressive and visible.

If the story says that colors change,
show the actual color transition.

Do not make this a static slideshow.

Do not add unrelated characters.

Do not add unrelated objects.

Do not add text.

Do not add logos.

Do not add watermarks.

Create an actual moving cinematic shot.
"""


        # ----------------------------------------------------
        # SCENE DISPLAY
        # ----------------------------------------------------

        st.markdown(
            f"### 🎬 Scene {number}: {title}"
        )

        st.write(
            action
        )


        with st.expander(
            f"🔍 Scene {number} Prompt"
        ):

            st.write(
                final_prompt
            )


        # ----------------------------------------------------
        # GENERATE VIDEO
        # ----------------------------------------------------

        status.info(
            f"🎥 Generating Scene {number}/{total_scenes}..."
        )


        try:

            seed = (
                1000
                + number
            )


            remote_video = generate_video(
                final_prompt,
                negative_prompt,
                duration,
                aspect_ratio,
                seed
            )


            local_video = (
                work_dir
                / f"scene_{number}.mp4"
            )


            copy_video(
                remote_video,
                local_video
            )


            video_files.append(
                str(local_video)
            )


            st.video(
                str(local_video)
            )


            with open(
                local_video,
                "rb"
            ) as video_file:

                st.download_button(
                    label=(
                        f"⬇️ Download Scene {number}"
                    ),
                    data=video_file.read(),
                    file_name=(
                        f"scene_{number}.mp4"
                    ),
                    mime="video/mp4",
                    key=f"download_scene_{number}",
                    use_container_width=True
                )


        except Exception as e:

            st.error(
                f"❌ Scene {number} failed."
            )

            st.code(
                str(e)
            )

            st.warning(
                "You can try again later if "
                "the Hugging Face ZeroGPU queue "
                "is full."
            )


        progress.progress(
            (index + 1)
            / total_scenes
        )


        # Small delay to avoid hammering
        # the public Space.

        time.sleep(2)


        # ----------------------------------------------------
        # PIXABAY REFERENCES
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
                    f"🖼️ Scene {number} References"
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


                            st.caption(
                                ref.get(
                                    "tags",
                                    ""
                                )
                            )


    # --------------------------------------------------------
    # GENERATION FINISHED
    # --------------------------------------------------------

    status.success(
        "All available scenes finished."
    )


    # --------------------------------------------------------
    # COMBINE
    # --------------------------------------------------------

    if video_files:

        st.header(
            "🎞️ Step 3 — Combine Scenes"
        )


        final_video = (
            work_dir
            / "final_story.mp4"
        )


        with st.spinner(
            "🎬 Combining all scenes into one video..."
        ):

            try:

                combine_videos(
                    video_files,
                    str(final_video)
                )


                st.success(
                    "🎉 Final video created!"
                )


                st.subheader(
                    "🎬 Your Complete Story"
                )


                st.video(
                    str(final_video)
                )


                with open(
                    final_video,
                    "rb"
                ) as video_file:

                    st.download_button(
                        label="⬇️ DOWNLOAD FINAL VIDEO",
                        data=video_file.read(),
                        file_name="final_story.mp4",
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )


            except Exception as e:

                st.error(
                    "Could not combine the videos."
                )

                st.code(
                    str(e)
                )


    else:

        st.error(
            "No video scenes were successfully generated."
        )

        st.info(
            "The Hugging Face ZeroGPU service may "
            "currently be busy or over quota. "
            "Try again later."
        )


# ============================================================
# INFORMATION
# ============================================================

st.markdown("---")

st.subheader(
    "ℹ️ About the Free Video Generator"
)

st.write(
    """
This application uses Groq for story planning and
Hugging Face's public LTX Video ZeroGPU Space for
actual video generation.

The application creates separate cinematic scenes
and then combines the generated MP4 files into one
final video.
"""
)

st.caption(
    "Free usage is subject to Hugging Face ZeroGPU "
    "daily quotas and queue availability."
)
