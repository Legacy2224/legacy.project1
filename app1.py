````python
# ============================================================
# AI STORY IMAGE GENERATOR
# Streamlit + Gemini Lite + Groq + Pixabay
# ============================================================

import streamlit as st
import os
import json
import requests
import io
from PIL import Image


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
# SAFE SECRET LOADER
# ============================================================

def get_key(name):

    # Streamlit Cloud
    try:
        value = st.secrets.get(name)

        if value:
            return str(value)

    except Exception:
        pass

    # Local environment
    value = os.getenv(name)

    if value:
        return str(value)

    return ""


# ============================================================
# API KEYS
# ============================================================

GEMINI_API_KEY = get_key("GEMINI_API_KEY")
GROQ_API_KEY = get_key("GROQ_API_KEY")
PIXABAY_API_KEY = get_key("PIXABAY_API_KEY")


# ============================================================
# OPTIONAL IMAGE API
# ============================================================

IMAGE_GENERATION_API_URL = get_key(
    "IMAGE_GENERATION_API_URL"
)

IMAGE_GENERATION_API_KEY = get_key(
    "IMAGE_GENERATION_API_KEY"
)


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
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        font-size: 18px;
        color: #777;
        margin-bottom: 30px;
    }

    .section-title {
        font-size: 25px;
        font-weight: 700;
    }

    .info-box {
        padding: 15px;
        border-radius: 12px;
        background: rgba(100,100,100,0.08);
        margin-top: 10px;
        margin-bottom: 10px;
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
    'Turn your story into a detailed cinematic AI image prompt'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Settings")

    style = st.selectbox(
        "🎨 Visual Style",
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
            "Oil Painting",
            "Comic Book"
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
            "Soft Natural Light",
            "Dramatic",
            "Neon",
            "Volumetric",
            "Studio"
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
        "✨ Use Groq Enhancement",
        value=True
    )

    use_pixabay = st.checkbox(
        "🖼️ Search Pixabay References",
        value=True
    )

    st.markdown("---")

    st.caption(
        "Gemini 2.5 Flash-Lite → "
        "Gemini 1.5 Flash-Lite fallback"
    )


# ============================================================
# STORY INPUT
# ============================================================

st.markdown(
    '<div class="section-title">📖 Your Story</div>',
    unsafe_allow_html=True
)

story = st.text_area(
    "Describe the image you want",
    height=220,
    placeholder=(
        "Example:\n\n"
        "A young explorer enters an ancient magical forest "
        "at night. The trees glow blue and thousands of "
        "butterflies surround her. When she touches an "
        "ancient crystal, the entire forest slowly changes "
        "from blue to purple and a glowing portal appears."
    )
)


# ============================================================
# CHARACTER
# ============================================================

with st.expander("👤 Character Details — Optional"):

    character = st.text_area(
        "Describe the character",
        height=120,
        placeholder=(
            "Example: young female explorer, 20 years old, "
            "long dark hair, brown jacket, backpack, "
            "curious expression"
        )
    )


# ============================================================
# GEMINI IMPORT
# ============================================================

def load_gemini():

    try:

        from google import genai

        return genai

    except Exception as error:

        raise Exception(
            "Could not import google-genai. "
            "Check requirements.txt."
        ) from error


# ============================================================
# GEMINI PROMPT GENERATION
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
            "GEMINI_API_KEY is missing. "
            "Add it to Streamlit Secrets."
        )

    genai = load_gemini()

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    prompt = f"""
You are an expert cinematic AI image prompt engineer.

Analyze the story carefully.

Create ONE extremely detailed image-generation prompt.

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

The image must represent the story accurately.

Include:

- main subject
- character appearance
- clothing
- facial expression
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
- magical effects
- transformations

If the story contains a color transformation,
describe it clearly.

Example:

blue forest transforming into purple forest

must actually appear as a visible transformation
in the image.

Do not add unrelated objects.

Do not add text.

Do not add logos.

Do not add watermarks.

Make the image visually innovative and cinematic.

Return ONLY valid JSON.

FORMAT:

{{
    "title": "short title",
    "prompt": "complete detailed image prompt",
    "negative_prompt": "negative prompt"
}}
"""

    # ========================================================
    # MODEL FALLBACK
    # ========================================================

    models = [
        "gemini-2.5-flash-lite",
        "gemini-1.5-flash-lite"
    ]

    last_error = None

    for model in models:

        try:

            response = client.models.generate_content(
                model=model,
                contents=prompt
            )

            text = response.text or ""

            text = text.strip()

            # Remove markdown fences
            text = text.replace(
                "```json",
                ""
            )

            text = text.replace(
                "```",
                ""
            )

            text = text.strip()

            # Parse JSON
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
        f"All Gemini Lite models failed.\n\n"
        f"Last error:\n{last_error}"
    )


# ============================================================
# GROQ
# ============================================================

def enhance_with_groq(
    image_prompt,
    negative_prompt
):

    if not GROQ_API_KEY:

        return {
            "prompt": image_prompt,
            "negative_prompt": negative_prompt,
            "model_used": "Groq not configured"
        }

    try:

        from groq import Groq

        client = Groq(
            api_key=GROQ_API_KEY
        )

        instruction = f"""
You are an expert cinematic image prompt editor.

Improve this prompt without changing the story.

IMAGE PROMPT:

{image_prompt}

NEGATIVE PROMPT:

{negative_prompt}

Improve:

- visual storytelling
- composition
- cinematic quality
- lighting
- environment
- character consistency
- object consistency
- color accuracy
- atmosphere
- depth
- camera direction

If there is a color transformation,
make it visually obvious.

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

        text = text.strip()

        result = json.loads(text)

        result["model_used"] = "Groq"

        return result

    except Exception:

        # If Groq fails, keep Gemini result.
        return {
            "prompt": image_prompt,
            "negative_prompt": negative_prompt,
            "model_used": "Groq fallback"
        }


# ============================================================
# PIXABAY
# ============================================================

def search_pixabay(query):

    if not PIXABAY_API_KEY:

        return []

    try:

        url = "https://pixabay.com/api/"

        params = {
            "key": PIXABAY_API_KEY,
            "q": query,
            "image_type": "photo",
            "safesearch": "true",
            "per_page": 6
        }

        response = requests.get(
            url,
            params=params,
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
                    "page": item.get(
                        "pageURL"
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
# OPTIONAL IMAGE GENERATION API
# ============================================================

def generate_image_with_api(
    prompt
):

    if not IMAGE_GENERATION_API_URL:

        return None

    headers = {
        "Content-Type": "application/json"
    }

    if IMAGE_GENERATION_API_KEY:

        headers[
            "Authorization"
        ] = f"Bearer {IMAGE_GENERATION_API_KEY}"

    payload = {
        "prompt": prompt
    }

    response = requests.post(
        IMAGE_GENERATION_API_URL,
        json=payload,
        headers=headers,
        timeout=180
    )

    response.raise_for_status()

    data = response.json()

    image_url = (
        data.get("image_url")
        or data.get("url")
    )

    if not image_url:

        return None

    image_response = requests.get(
        image_url,
        timeout=120
    )

    image_response.raise_for_status()

    return Image.open(
        BytesIO(
            image_response.content
        )
    )


# ============================================================
# GENERATE BUTTON
# ============================================================

generate = st.button(
    "✨ GENERATE",
    type="primary",
    use_container_width=True
)


# ============================================================
# GENERATION
# ============================================================

if generate:

    if not story.strip():

        st.warning(
            "Please enter a story first."
        )

        st.stop()

    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    with st.spinner(
        "🧠 Gemini Lite is understanding your story..."
    ):

        try:

            result = generate_gemini_prompt(
                story=story,
                style=style,
                aspect_ratio=aspect_ratio,
                lighting=lighting,
                camera=camera,
                character=character
            )

        except Exception as error:

            st.error(
                "Gemini generation failed."
            )

            st.code(
                str(error)
            )

            st.info(
                "Check your Gemini API key and "
                "available model access."
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
            "✨ Groq is refining the visual prompt..."
        ):

            groq_result = enhance_with_groq(
                image_prompt,
                negative_prompt
            )

            image_prompt = groq_result[
                "prompt"
            ]

            negative_prompt = groq_result[
                "negative_prompt"
            ]


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

Create a single cinematic image.

Preserve every important element from the story.

Maintain consistency of:

- characters
- clothing
- environment
- objects
- colors
- lighting
- atmosphere

If the story contains a transformation,
show the transformation clearly.
"""


    # --------------------------------------------------------
    # DISPLAY PROMPT
    # --------------------------------------------------------

    st.success(
        f"Generated prompt using {model_used}"
    )

    with st.expander(
        "🔍 View Generated Prompt"
    ):

        st.markdown(
            "### Image Prompt"
        )

        st.write(
            final_prompt
        )

        st.markdown(
            "### Negative Prompt"
        )

        st.write(
            negative_prompt
        )


    # --------------------------------------------------------
    # IMAGE GENERATION
    # --------------------------------------------------------

    if IMAGE_GENERATION_API_URL:

        with st.spinner(
            "🎨 Generating image..."
        ):

            try:

                generated_image = (
                    generate_image_with_api(
                        final_prompt
                    )
                )

                if generated_image:

                    st.markdown(
                        "## 🎨 Generated Image"
                    )

                    st.image(
                        generated_image,
                        use_container_width=True
                    )

                    buffer = io.BytesIO()

                    generated_image.save(
                        buffer,
                        format="PNG"
                    )

                    st.download_button(
                        label="⬇️ Download Image",
                        data=buffer.getvalue(),
                        file_name=(
                            "ai_generated_image.png"
                        ),
                        mime="image/png",
                        use_container_width=True
                    )

                else:

                    st.warning(
                        "Image API did not return an image."
                    )

            except Exception as error:

                st.error(
                    "Image generation failed."
                )

                st.code(
                    str(error)
                )

    else:

        st.info(
            """
🎨 The story prompt has been generated successfully.

Your Gemini/Groq pipeline is working, but no image-generation
endpoint has been configured yet.

Add IMAGE_GENERATION_API_URL to Streamlit Secrets when you
connect your actual image-generation model.
"""
        )


    # --------------------------------------------------------
    # PIXABAY
    # --------------------------------------------------------

    if use_pixabay:

        with st.spinner(
            "🔎 Finding visual references..."
        ):

            # Use a short search query.
            search_query = story[:80]

            references = search_pixabay(
                search_query
            )


        if references:

            st.markdown("---")

            st.markdown(
                "## 🖼️ Pixabay References"
            )

            columns = st.columns(3)

            for index, item in enumerate(
                references
            ):

                with columns[
                    index % 3
                ]:

                    if item.get("preview"):

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


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "AI Story Image Generator • "
    "Streamlit + Gemini Lite + Groq + Pixabay"
)
````
