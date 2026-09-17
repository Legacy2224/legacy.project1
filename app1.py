````python
import streamlit as st
import os
import json
import requests
import io
from PIL import Image
from io import BytesIO


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Story Image Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# API KEY LOADER
# ============================================================

def get_key(name):

    try:
        value = st.secrets.get(name)

        if value:
            return str(value)

    except Exception:
        pass

    value = os.getenv(name)

    if value:
        return str(value)

    return ""


GEMINI_API_KEY = get_key("GEMINI_API_KEY")
GROQ_API_KEY = get_key("GROQ_API_KEY")
PIXABAY_API_KEY = get_key("PIXABAY_API_KEY")


# ============================================================
# PAGE DESIGN
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
        font-size: 18px;
        color: #777;
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
    '<div class="main-title">🎨 AI Story Image Generator</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Transform your story into an AI-generated visual concept'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Settings")

    style = st.selectbox(
        "🎨 Image Style",
        [
            "Cinematic",
            "Photorealistic",
            "3D Animation",
            "Anime",
            "Digital Art",
            "Fantasy",
            "Sci-Fi",
            "Cyberpunk",
            "Dark Fantasy",
            "Watercolor",
            "Oil Painting"
        ]
    )

    aspect_ratio = st.selectbox(
        "📐 Aspect Ratio",
        [
            "1:1",
            "16:9",
            "9:16",
            "4:3",
            "3:4"
        ]
    )

    lighting = st.selectbox(
        "💡 Lighting",
        [
            "Cinematic",
            "Golden Hour",
            "Moonlight",
            "Dramatic",
            "Neon",
            "Soft Natural Light",
            "Volumetric"
        ]
    )

    camera = st.selectbox(
        "📷 Camera",
        [
            "Wide Shot",
            "Medium Shot",
            "Close-Up",
            "Extreme Close-Up",
            "Low Angle",
            "High Angle",
            "Drone View",
            "Over-the-Shoulder"
        ]
    )

    use_groq = st.checkbox(
        "✨ Enhance with Groq",
        value=True
    )

    use_pixabay = st.checkbox(
        "🖼️ Pixabay References",
        value=True
    )


# ============================================================
# STORY
# ============================================================

st.subheader("📖 Your Story")

story = st.text_area(
    "Describe the scene you want to generate",
    height=220,
    placeholder=(
        "Example:\n\n"
        "A young explorer enters an ancient magical forest "
        "at night. The trees glow blue and thousands of "
        "butterflies surround her. She touches an ancient "
        "crystal and the entire forest slowly changes from "
        "blue to purple. A glowing portal appears behind "
        "the trees."
    )
)


# ============================================================
# CHARACTER
# ============================================================

with st.expander("👤 Character Details"):

    character = st.text_area(
        "Character description",
        height=120,
        placeholder=(
            "Young female explorer, long dark hair, "
            "brown jacket, backpack, curious expression..."
        )
    )


# ============================================================
# GEMINI
# ============================================================

def generate_gemini_prompt(
    story,
    style,
    aspect_ratio,
    lighting,
    camera,
    character
):

    if not GEMINI_API_KEY:

        raise Exception(
            "GEMINI_API_KEY is missing from Streamlit Secrets."
        )

    try:

        from google import genai

    except Exception as error:

        raise Exception(
            "google-genai is not installed. "
            "Add google-genai to requirements.txt."
        ) from error


    client = genai.Client(
        api_key=GEMINI_API_KEY
    )


    instruction = f"""
You are an expert cinematic AI image prompt engineer.

Analyze the story carefully.

Create a detailed image-generation prompt.

STORY:
{story}

CHARACTER:
{character}

STYLE:
{style}

ASPECT RATIO:
{aspect_ratio}

LIGHTING:
{lighting}

CAMERA:
{camera}

The image must accurately represent the story.

Include:

- main subject
- characters
- character appearance
- clothing
- facial expressions
- environment
- background
- important objects
- colors
- lighting
- camera angle
- composition
- depth
- atmosphere
- emotions
- visual effects
- transformations

If the story contains a color change,
make the color transformation visually obvious.

Do not add unrelated objects.

Do not add text.

Do not add logos.

Do not add watermarks.

Return ONLY JSON:

{{
    "title": "short title",
    "prompt": "complete detailed image prompt",
    "negative_prompt": "negative prompt"
}}
"""


    models = [
        "gemini-2.5-flash-lite",
        "gemini-1.5-flash-lite"
    ]


    last_error = None


    for model in models:

        try:

            response = client.models.generate_content(
                model=model,
                contents=instruction
            )

            text = response.text or ""

            text = text.strip()

            text = text.replace(
                "```json",
                ""
            )

            text = text.replace(
                "```",
                ""
            )

            text = text.strip()


            try:

                result = json.loads(text)

            except Exception:

                result = {
                    "title": "AI Generated Scene",
                    "prompt": text,
                    "negative_prompt": (
                        "blurry, low quality, distorted face, "
                        "bad anatomy, extra fingers, extra limbs, "
                        "duplicate objects, text, logo, watermark"
                    )
                }


            result["model_used"] = model

            return result


        except Exception as error:

            last_error = error

            continue


    raise Exception(
        f"Gemini Lite models failed.\n\n{last_error}"
    )


# ============================================================
# GROQ
# ============================================================

def improve_with_groq(
    prompt,
    negative_prompt
):

    if not GROQ_API_KEY:

        return {
            "prompt": prompt,
            "negative_prompt": negative_prompt
        }


    try:

        from groq import Groq

        client = Groq(
            api_key=GROQ_API_KEY
        )


        instruction = f"""
Improve this AI image-generation prompt.

IMAGE PROMPT:
{prompt}

NEGATIVE PROMPT:
{negative_prompt}

Improve:

- cinematic composition
- visual storytelling
- lighting
- depth
- atmosphere
- character consistency
- environment
- colors
- camera direction
- visual effects

Preserve the original story.

Do not add unrelated objects.

Return ONLY JSON:

{{
    "prompt": "improved prompt",
    "negative_prompt": "improved negative prompt"
}}
"""


        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": instruction
                }
            ],
            temperature=0.3
        )


        text = response.choices[
            0
        ].message.content.strip()


        text = text.replace(
            "```json",
            ""
        )

        text = text.replace(
            "```",
            ""
        )


        return json.loads(
            text.strip()
        )


    except Exception:

        return {
            "prompt": prompt,
            "negative_prompt": negative_prompt
        }


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
                    "preview": item.get(
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
# GENERATE BUTTON
# ============================================================

generate = st.button(
    "✨ GENERATE IMAGE PROMPT",
    type="primary",
    use_container_width=True
)


# ============================================================
# GENERATION
# ============================================================

if generate:

    if not story.strip():

        st.warning(
            "Please enter your story first."
        )

        st.stop()


    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    with st.spinner(
        "🧠 Gemini Lite is analyzing your story..."
    ):

        try:

            result = generate_gemini_prompt(
                story,
                style,
                aspect_ratio,
                lighting,
                camera,
                character
            )

        except Exception as error:

            st.error(
                "Gemini error:"
            )

            st.code(
                str(error)
            )

            st.stop()


    title = result.get(
        "title",
        "AI Generated Scene"
    )

    image_prompt = result.get(
        "prompt",
        ""
    )

    negative_prompt = result.get(
        "negative_prompt",
        ""
    )

    model_used = result.get(
        "model_used",
        "Unknown"
    )


    # --------------------------------------------------------
    # GROQ
    # --------------------------------------------------------

    if use_groq:

        with st.spinner(
            "✨ Groq is improving the prompt..."
        ):

            improved = improve_with_groq(
                image_prompt,
                negative_prompt
            )

            image_prompt = improved.get(
                "prompt",
                image_prompt
            )

            negative_prompt = improved.get(
                "negative_prompt",
                negative_prompt
            )


    # --------------------------------------------------------
    # FINAL PROMPT
    # --------------------------------------------------------

    final_prompt = f"""
{image_prompt}

STYLE:
{style}

LIGHTING:
{lighting}

CAMERA:
{camera}

ASPECT RATIO:
{aspect_ratio}

NEGATIVE PROMPT:
{negative_prompt}
"""


    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    st.success(
        f"Prompt generated using {model_used}"
    )


    st.subheader(
        f"🎬 {title}"
    )


    st.markdown(
        "### 🖼️ AI Image Prompt"
    )

    st.info(
        final_prompt
    )


    # --------------------------------------------------------
    # PIXABAY
    # --------------------------------------------------------

    if use_pixabay:

        with st.spinner(
            "🔎 Searching Pixabay..."
        ):

            references = search_pixabay(
                story[:80]
            )


        if references:

            st.markdown("---")

            st.subheader(
                "🖼️ Pixabay References"
            )


            columns = st.columns(3)


            for index, item in enumerate(
                references
            ):

                with columns[
                    index % 3
                ]:

                    if item.get(
                        "preview"
                    ):

                        st.image(
                            item["preview"],
                            use_container_width=True
                        )

                    st.caption(
                        item.get(
                            "tags",
                            ""
                        )
                    )


st.markdown("---")

st.caption(
    "AI Story Image Generator • "
    "Gemini Lite + Groq + Pixabay"
)
````
