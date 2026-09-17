import streamlit as st
import os
import json
import requests


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Story Generator",
    page_icon="🎨",
    layout="wide"
)


# ============================================================
# LOAD API KEYS
# ============================================================

def get_secret(name):
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, "")


GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
GROQ_API_KEY = get_secret("GROQ_API_KEY")
PIXABAY_API_KEY = get_secret("PIXABAY_API_KEY")


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .title {
        text-align: center;
        font-size: 45px;
        font-weight: 800;
        margin-top: 20px;
    }

    .subtitle {
        text-align: center;
        color: #777;
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
    '<div class="title">🎨 AI Story Image Generator</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Create detailed cinematic image prompts from your story'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Settings")

    style = st.selectbox(
        "Image Style",
        [
            "Cinematic",
            "Photorealistic",
            "3D Animation",
            "Anime",
            "Fantasy",
            "Digital Art",
            "Sci-Fi",
            "Cyberpunk",
            "Dark Fantasy",
            "Watercolor"
        ]
    )

    aspect_ratio = st.selectbox(
        "Aspect Ratio",
        [
            "1:1",
            "16:9",
            "9:16",
            "4:3",
            "3:4"
        ]
    )

    lighting = st.selectbox(
        "Lighting",
        [
            "Cinematic",
            "Golden Hour",
            "Moonlight",
            "Dramatic",
            "Neon",
            "Soft Natural",
            "Volumetric"
        ]
    )

    camera = st.selectbox(
        "Camera",
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
        "Use Groq Enhancement",
        value=True
    )

    use_pixabay = st.checkbox(
        "Use Pixabay References",
        value=True
    )


# ============================================================
# STORY INPUT
# ============================================================

st.subheader("📖 Enter Your Story")

story = st.text_area(
    "Story / Scene",
    height=220,
    placeholder=(
        "Example:\n\n"
        "A young explorer enters an ancient magical forest "
        "at night. The trees glow blue and thousands of "
        "butterflies surround her. She touches an ancient "
        "crystal and the entire forest changes from blue "
        "to purple. A glowing portal appears behind her."
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
            "brown jacket, backpack, curious expression."
        )
    )


# ============================================================
# GEMINI FUNCTION
# ============================================================

def generate_gemini_prompt():

    if not GEMINI_API_KEY:

        raise Exception(
            "GEMINI_API_KEY is missing. "
            "Add it in Streamlit Secrets."
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

Analyze this story carefully:

{story}

Character details:

{character}

Visual style:

{style}

Aspect ratio:

{aspect_ratio}

Lighting:

{lighting}

Camera:

{camera}

Create a highly detailed image-generation prompt.

The image must accurately represent the story.

Include:

1. Main subject
2. Characters
3. Character appearance
4. Clothing
5. Facial expression
6. Environment
7. Background
8. Important objects
9. Colors
10. Lighting
11. Camera angle
12. Composition
13. Depth
14. Atmosphere
15. Emotion
16. Special effects
17. Transformations
18. Color changes

If the story contains a color transformation,
make it visually obvious.

Example:

blue forest transforming into purple forest.

Do not add unrelated objects.

Do not add text.

Do not add logos.

Do not add watermarks.

Make the result cinematic, creative and visually impressive.

Return ONLY JSON.

Format:

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


    raise Exception(
        "Gemini models failed.\n\n"
        + str(last_error)
    )


# ============================================================
# GROQ FUNCTION
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
Improve this cinematic AI image prompt.

Original prompt:

{prompt}

Negative prompt:

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

Do not change the story.

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
        ].message.content


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
# PIXABAY FUNCTION
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
                    "tags": item.get(
                        "tags",
                        ""
                    ),
                    "page": item.get(
                        "pageURL",
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
    "✨ GENERATE",
    type="primary",
    use_container_width=True
)


# ============================================================
# MAIN PROCESS
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

            result = generate_gemini_prompt()

        except Exception as error:

            st.error(
                "Gemini Error"
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
    # RESULT
    # --------------------------------------------------------

    st.success(
        "Prompt generated successfully!"
    )

    st.subheader(
        "🎬 " + title
    )

    st.caption(
        "Gemini model: " + model_used
    )


    st.markdown(
        "### 🖼️ Final Image Prompt"
    )

    st.info(
        image_prompt
    )


    st.markdown(
        "### 🚫 Negative Prompt"
    )

    st.code(
        negative_prompt
    )


    # --------------------------------------------------------
    # PIXABAY
    # --------------------------------------------------------

    if use_pixabay:

        with st.spinner(
            "🔎 Finding visual references..."
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

                    if item["image"]:

                        st.image(
                            item["image"],
                            use_container_width=True
                        )

                    st.caption(
                        item["tags"]
                    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "AI Story Generator | "
    "Streamlit + Gemini Lite + Groq + Pixabay"
)
