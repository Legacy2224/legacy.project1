import os
import io
import json
import requests
import streamlit as st

from PIL import Image
from io import BytesIO

from google import genai
from groq import Groq


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Story Image Generator",
    page_icon="🎨",
    layout="wide"
)


# ============================================================
# API KEY LOADER
# ============================================================

def get_secret(name):

    # Streamlit Cloud secrets
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass

    # Local environment variables
    value = os.getenv(name)

    if value:
        return value

    return None


GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
GROQ_API_KEY = get_secret("GROQ_API_KEY")
PIXABAY_API_KEY = get_secret("PIXABAY_API_KEY")

# Your actual image-generation API
IMAGE_GENERATION_API_URL = get_secret(
    "IMAGE_GENERATION_API_URL"
)

IMAGE_GENERATION_API_KEY = get_secret(
    "IMAGE_GENERATION_API_KEY"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 45px;
        font-weight: 800;
        text-align: center;
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        color: #777;
        font-size: 18px;
        margin-bottom: 30px;
    }

    .stButton button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# TITLE
# ============================================================

st.markdown(
    '<div class="main-title">🎨 AI Story Image Generator</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Transform your story into a cinematic AI image'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Generation Settings")

    style = st.selectbox(
        "🎨 Visual Style",
        [
            "Cinematic",
            "Photorealistic",
            "3D Animation",
            "Anime",
            "Digital Art",
            "Fantasy",
            "Cyberpunk",
            "Watercolor",
            "Oil Painting",
            "Comic Book",
            "Studio Ghibli Inspired",
            "Dark Fantasy",
            "Sci-Fi"
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
            "Cinematic lighting",
            "Golden hour",
            "Soft natural light",
            "Dramatic lighting",
            "Neon lighting",
            "Moonlight",
            "Volumetric lighting",
            "Studio lighting"
        ]
    )

    camera = st.selectbox(
        "📷 Camera",
        [
            "Wide cinematic shot",
            "Medium shot",
            "Close-up",
            "Extreme close-up",
            "Low angle",
            "High angle",
            "Drone view",
            "Over-the-shoulder"
        ]
    )

    use_groq = st.checkbox(
        "✨ Enhance prompt with Groq",
        value=True
    )

    use_pixabay = st.checkbox(
        "🖼️ Find Pixabay references",
        value=True
    )


# ============================================================
# STORY INPUT
# ============================================================

st.subheader("📖 Describe Your Story")

story = st.text_area(
    "Enter your story or scene",
    height=220,
    placeholder="""
Example:

A young explorer walks into an ancient magical forest at night.
The trees glow blue and thousands of butterflies surround her.
As she touches an ancient crystal, the entire forest slowly
changes from blue to purple. A giant glowing portal appears
behind the trees.
"""
)


# ============================================================
# OPTIONAL CHARACTER DETAILS
# ============================================================

with st.expander("👤 Optional Character Details"):

    character = st.text_area(
        "Character description",
        placeholder=(
            "Example: 20-year-old female explorer, "
            "long dark hair, brown leather jacket, "
            "backpack, adventurous expression"
        ),
        height=120
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
            "GEMINI_API_KEY is missing."
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    instruction = f"""
You are an expert cinematic AI image prompt engineer.

Your job is to understand a story and convert it into
an extremely detailed image-generation prompt.

STORY:
{story}

CHARACTER DETAILS:
{character}

STYLE:
{style}

ASPECT RATIO:
{aspect_ratio}

LIGHTING:
{lighting}

CAMERA:
{camera}

IMPORTANT:

Analyze the story carefully.

The generated image must visually represent the story.

Include:

1. Main subject
2. Character appearance
3. Character clothing
4. Facial expression
5. Environment
6. Background
7. Important objects
8. Colors
9. Lighting
10. Camera angle
11. Composition
12. Depth
13. Atmosphere
14. Emotion
15. Visual effects
16. Motion where appropriate
17. Story-specific details

If the story contains:
- transformation
- color changing
- magical effects
- environmental changes
- glowing objects
- multiple important objects

make those elements extremely clear.

DO NOT add unrelated elements.

DO NOT create text.

DO NOT create logos.

DO NOT create watermarks.

Make the scene innovative, cinematic and visually impressive.

Return ONLY valid JSON:

{{
    "title": "short title",
    "prompt": "complete image generation prompt",
    "negative_prompt": "negative prompt"
}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=instruction
    )

    text = response.text.strip()

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

        return json.loads(text)

    except Exception:

        return {
            "title": "AI Generated Scene",
            "prompt": text,
            "negative_prompt": (
                "blurry, low quality, distorted face, "
                "extra limbs, extra fingers, duplicate objects, "
                "bad anatomy, text, logo, watermark"
            )
        }


# ============================================================
# GROQ
# ============================================================

def enhance_with_groq(
    prompt,
    negative_prompt
):

    if not GROQ_API_KEY:

        return {
            "prompt": prompt,
            "negative_prompt": negative_prompt
        }

    client = Groq(
        api_key=GROQ_API_KEY
    )

    instruction = f"""
You are a professional cinematic image prompt editor.

Improve this image prompt while preserving the original story.

IMAGE PROMPT:

{prompt}

NEGATIVE PROMPT:

{negative_prompt}

Improve:

- cinematic composition
- visual storytelling
- realism
- depth
- lighting
- environment
- character consistency
- object consistency
- color accuracy
- atmosphere
- camera direction
- visual effects

If the story includes color transformation,
make the transformation visually obvious.

Do NOT change the story.

Do NOT add unrelated objects.

Return ONLY JSON:

{{
    "prompt": "improved image prompt",
    "negative_prompt": "improved negative prompt"
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": instruction
            }
        ],
        temperature=0.35
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

    try:

        return json.loads(text)

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

    if response.status_code != 200:

        return []

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


# ============================================================
# IMAGE GENERATION
# ============================================================

def generate_ai_image(prompt):

    if not IMAGE_GENERATION_API_URL:

        raise Exception(
            """
IMAGE_GENERATION_API_URL is not configured.

Gemini and Groq are being used for AI prompt generation,
while Pixabay is being used for reference images.

You still need an image-generation endpoint/model
to actually create the final image.
"""
        )

    headers = {
        "Content-Type": "application/json"
    }

    if IMAGE_GENERATION_API_KEY:

        headers["Authorization"] = (
            f"Bearer {IMAGE_GENERATION_API_KEY}"
        )

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

    image_url = data.get(
        "image_url"
    )

    if not image_url:

        image_url = data.get(
            "url"
        )

    if not image_url:

        raise Exception(
            "The image API did not return an image URL."
        )

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
    "✨ GENERATE AI IMAGE",
    type="primary"
)


# ============================================================
# MAIN GENERATION PIPELINE
# ============================================================

if generate:

    if not story.strip():

        st.warning(
            "Please enter your story first."
        )

        st.stop()

    try:

        # ----------------------------------------------------
        # GEMINI
        # ----------------------------------------------------

        with st.spinner(
            "🧠 Gemini is analyzing your story..."
        ):

            result = generate_gemini_prompt(
                story=story,
                style=style,
                aspect_ratio=aspect_ratio,
                lighting=lighting,
                camera=camera,
                character=character
            )

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


        # ----------------------------------------------------
        # GROQ
        # ----------------------------------------------------

        if use_groq:

            with st.spinner(
                "✨ Groq is improving the prompt..."
            ):

                improved = enhance_with_groq(
                    image_prompt,
                    negative_prompt
                )

                image_prompt = improved[
                    "prompt"
                ]

                negative_prompt = improved[
                    "negative_prompt"
                ]


        # ----------------------------------------------------
        # FINAL PROMPT
        # ----------------------------------------------------

        final_prompt = f"""
{image_prompt}

VISUAL STYLE:
{style}

LIGHTING:
{lighting}

CAMERA:
{camera}

ASPECT RATIO:
{aspect_ratio}

NEGATIVE PROMPT:
{negative_prompt}

Create a single highly detailed cinematic image.

Every important element from the original story must
be visually represented.

Maintain consistent character appearance,
environment, objects, colors and lighting.

Do not introduce unrelated objects.
"""


        # ----------------------------------------------------
        # DISPLAY PROMPT
        # ----------------------------------------------------

        with st.expander(
            "🔍 View AI Image Prompt"
        ):

            st.write(
                final_prompt
            )


        # ----------------------------------------------------
        # PIXABAY
        # ----------------------------------------------------

        pixabay_results = []

        if use_pixabay:

            with st.spinner(
                "🔎 Searching Pixabay for visual references..."
            ):

                query = story[:100]

                pixabay_results = search_pixabay(
                    query
                )


        # ----------------------------------------------------
        # GENERATE IMAGE
        # ----------------------------------------------------

        with st.spinner(
            "🎨 Creating your AI image..."
        ):

            generated_image = generate_ai_image(
                final_prompt
            )


        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        st.success(
            f"✅ {title}"
        )

        left, right = st.columns(
            [2, 1]
        )


        # ----------------------------------------------------
        # IMAGE
        # ----------------------------------------------------

        with left:

            st.image(
                generated_image,
                caption=title,
                use_container_width=True
            )

            buffer = io.BytesIO()

            generated_image.save(
                buffer,
                format="PNG"
            )

            st.download_button(
                "⬇️ Download Image",
                buffer.getvalue(),
                "ai_generated_image.png",
                "image/png",
                use_container_width=True
            )


        # ----------------------------------------------------
        # DETAILS
        # ----------------------------------------------------

        with right:

            st.subheader(
                "🎬 Scene Details"
            )

            st.write(
                f"**Style:** {style}"
            )

            st.write(
                f"**Lighting:** {lighting}"
            )

            st.write(
                f"**Camera:** {camera}"
            )

            st.write(
                f"**Aspect Ratio:** {aspect_ratio}"
            )

            st.markdown(
                "### AI Prompt"
            )

            st.info(
                image_prompt
            )


        # ----------------------------------------------------
        # PIXABAY REFERENCES
        # ----------------------------------------------------

        if pixabay_results:

            st.markdown("---")

            st.subheader(
                "🖼️ Visual References"
            )

            columns = st.columns(3)

            for index, item in enumerate(
                pixabay_results
            ):

                with columns[
                    index % 3
                ]:

                    st.image(
                        item["preview"],
                        use_container_width=True
                    )

                    st.caption(
                        item["tags"]
                    )


    except Exception as error:

        st.error(
            "❌ Generation failed."
        )

        st.exception(error)
