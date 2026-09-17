import streamlit as st
import os
import json
import requests


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Story Studio",
    page_icon="🎬",
    layout="wide"
)


# ============================================================
# API KEYS
# ============================================================

def get_key(name):

    try:
        value = st.secrets.get(name)

        if value:
            return str(value)

    except Exception:
        pass

    return os.getenv(name, "")


GEMINI_API_KEY = get_key("GEMINI_API_KEY")
GROQ_API_KEY = get_key("GROQ_API_KEY")
PIXABAY_API_KEY = get_key("PIXABAY_API_KEY")


# ============================================================
# GEMINI
# ============================================================

try:

    from google import genai

    GEMINI_AVAILABLE = True
    GEMINI_ERROR = ""

except Exception as e:

    genai = None
    GEMINI_AVAILABLE = False
    GEMINI_ERROR = str(e)


# ============================================================
# PAGE STYLE
# ============================================================

st.markdown(
    """
    <style>

    .title {
        text-align: center;
        font-size: 46px;
        font-weight: 800;
        margin-top: 15px;
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
    '<div class="title">🎬 AI Story Studio</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Turn your story into cinematic AI scenes'
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
            "Fantasy",
            "Digital Art",
            "Sci-Fi",
            "Cyberpunk",
            "Dark Fantasy",
            "Comic Book",
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

    scene_count = st.slider(
        "🎞️ Number of Scenes",
        1,
        6,
        3
    )

    use_groq = st.checkbox(
        "✨ Enhance with Groq",
        value=True
    )

    use_pixabay = st.checkbox(
        "🖼️ Pixabay References",
        value=True
    )

    st.markdown("---")

    st.subheader("🔌 API Status")

    if GEMINI_API_KEY:
        st.success("Gemini API ✓")
    else:
        st.error("Gemini API ✗")

    if GROQ_API_KEY:
        st.success("Groq API ✓")
    else:
        st.warning("Groq not configured")

    if PIXABAY_API_KEY:
        st.success("Pixabay API ✓")
    else:
        st.warning("Pixabay not configured")


# ============================================================
# STORY INPUT
# ============================================================

st.subheader("📖 Your Story")

story = st.text_area(
    "Enter your complete story",
    height=230,
    placeholder=(
        "Example:\n\n"
        "A young explorer enters an ancient magical forest "
        "at night. The trees glow blue and thousands of "
        "butterflies surround her. She discovers an ancient "
        "crystal. When she touches it, the entire forest "
        "changes from blue to purple and golden light. "
        "A giant glowing portal appears between the trees."
    )
)


# ============================================================
# CHARACTER
# ============================================================

with st.expander("👤 Character Details"):

    character = st.text_area(
        "Main character description",
        height=130,
        placeholder=(
            "Young female explorer, 22 years old, "
            "long dark hair, brown leather jacket, "
            "dark trousers, hiking boots, backpack."
        )
    )


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_gemini_client():

    if not GEMINI_API_KEY:

        raise Exception(
            "GEMINI_API_KEY is missing."
        )

    if not GEMINI_AVAILABLE:

        raise Exception(
            "google-genai could not be imported.\n\n"
            + GEMINI_ERROR
        )

    return genai.Client(
        api_key=GEMINI_API_KEY
    )


# ============================================================
# GEMINI 3.5 FLASH-LITE
# INTERACTIONS API
# ============================================================

def generate_storyboard():

    client = get_gemini_client()

    prompt = f"""
You are a professional cinematic storyboard director.

Analyze this complete story:

{story}

MAIN CHARACTER:

{character}

VISUAL STYLE:

{style}

LIGHTING:

{lighting}

CAMERA:

{camera}

ASPECT RATIO:

{aspect_ratio}

Create exactly {scene_count} connected cinematic scenes.

The scenes must tell the complete story from beginning
to end.

IMPORTANT:

- Keep the same character appearance in every scene.
- Keep clothing consistent.
- Keep important objects consistent.
- Keep the environment logically consistent.
- Make each scene visually interesting.
- Follow the story exactly.
- Do not invent unrelated events.
- Do not invent unrelated characters.
- Do not add text.
- Do not add logos.
- Do not add watermarks.
- Show transformations clearly.
- Show color changes clearly.
- Describe emotions.
- Describe environment.
- Describe lighting.
- Describe camera angle.
- Describe important objects.
- Describe visual effects.

If the story contains a color transformation,
make it extremely clear.

For example:

blue forest → purple forest → golden magical light

Create a strong cinematic image prompt for every scene.

Return ONLY valid JSON.

Use this exact structure:

{{
    "story_title": "short title",
    "character_bible": "fixed appearance of main character",
    "scenes": [
        {{
            "scene_number": 1,
            "scene_title": "scene title",
            "story_action": "what happens",
            "environment": "environment",
            "character": "character appearance",
            "objects": "important objects",
            "colors": "important colors",
            "lighting": "lighting",
            "camera": "camera angle",
            "image_prompt": "complete cinematic image prompt",
            "negative_prompt": "negative prompt"
        }}
    ]
}}
"""

    try:

        interaction = client.interactions.create(
            model="gemini-3.5-flash-lite",
            input=prompt
        )

    except Exception as e:

        raise Exception(
            "Gemini 3.5 Flash-Lite failed.\n\n"
            + str(e)
        )


    text = getattr(
        interaction,
        "output_text",
        None
    )


    if not text:

        try:

            text = interaction.output_text

        except Exception:

            text = ""


    if not text:

        raise Exception(
            "Gemini returned an empty response."
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
            "Gemini returned invalid JSON.\n\n"
            "RAW RESPONSE:\n\n"
            + text
        )


# ============================================================
# GROQ PROMPT ENHANCEMENT
# ============================================================

def improve_with_groq(
    prompt,
    negative_prompt,
    character_bible
):

    if not GROQ_API_KEY:

        return prompt, negative_prompt


    try:

        from groq import Groq

        client = Groq(
            api_key=GROQ_API_KEY
        )


        instruction = f"""
You are an expert cinematic AI image prompt engineer.

CHARACTER BIBLE:

{character_bible}

IMAGE PROMPT:

{prompt}

NEGATIVE PROMPT:

{negative_prompt}

Improve this prompt for cinematic image generation.

Improve:

- composition
- character consistency
- environment
- lighting
- atmosphere
- depth
- camera
- colors
- visual effects
- emotion
- storytelling

Do not change the story.

Do not add unrelated characters.

Do not add unrelated objects.

Make color transformations visually obvious.

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
            temperature=0.25
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


        result = json.loads(
            text.strip()
        )


        return (
            result.get(
                "prompt",
                prompt
            ),
            result.get(
                "negative_prompt",
                negative_prompt
            )
        )


    except Exception:

        return prompt, negative_prompt


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
    "🚀 GENERATE STORY",
    type="primary",
    use_container_width=True
)


# ============================================================
# MAIN GENERATION
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
        "🧠 Gemini 3.5 Flash-Lite is creating your storyboard..."
    ):

        try:

            storyboard = generate_storyboard()

        except Exception as e:

            st.error(
                "❌ Gemini Error"
            )

            st.code(
                str(e)
            )

            st.stop()


    # --------------------------------------------------------
    # DATA
    # --------------------------------------------------------

    story_title = storyboard.get(
        "story_title",
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


    if not scenes:

        st.error(
            "Gemini returned no scenes."
        )

        st.stop()


    st.success(
        f"🎬 {len(scenes)} scenes created!"
    )


    st.header(
        "🎞️ " + story_title
    )


    # --------------------------------------------------------
    # CHARACTER BIBLE
    # --------------------------------------------------------

    with st.expander(
        "👤 Character Consistency"
    ):

        st.write(
            character_bible
        )


    # --------------------------------------------------------
    # SCENES
    # --------------------------------------------------------

    for index, scene in enumerate(
        scenes
    ):

        number = scene.get(
            "scene_number",
            index + 1
        )

        title = scene.get(
            "scene_title",
            f"Scene {number}"
        )

        action = scene.get(
            "story_action",
            ""
        )

        environment = scene.get(
            "environment",
            ""
        )

        objects = scene.get(
            "objects",
            ""
        )

        image_prompt = scene.get(
            "image_prompt",
            ""
        )

        negative_prompt = scene.get(
            "negative_prompt",
            ""
        )


        st.markdown("---")


        st.header(
            f"🎬 Scene {number}: {title}"
        )


        st.write(
            action
        )


        # ----------------------------------------------------
        # GROQ
        # ----------------------------------------------------

        if use_groq:

            with st.spinner(
                f"✨ Improving Scene {number}..."
            ):

                final_prompt, final_negative = (
                    improve_with_groq(
                        image_prompt,
                        negative_prompt,
                        character_bible
                    )
                )

        else:

            final_prompt = image_prompt

            final_negative = negative_prompt


        # ----------------------------------------------------
        # FINAL PROMPT
        # ----------------------------------------------------

        final_prompt = f"""
Create a cinematic image for Scene {number}.

COMPLETE STORY:

{story}

CHARACTER CONSISTENCY:

{character_bible}

SCENE ACTION:

{action}

ENVIRONMENT:

{environment}

IMPORTANT OBJECTS:

{objects}

AI IMAGE PROMPT:

{final_prompt}

VISUAL STYLE:

{style}

LIGHTING:

{lighting}

CAMERA:

{camera}

ASPECT RATIO:

{aspect_ratio}

IMPORTANT:

Keep the character identical.

Keep clothing consistent.

Keep important objects consistent.

Preserve the story.

Show the environment clearly.

Show emotions clearly.

Show transformations clearly.

Show color changes clearly.

Make the image visually cinematic.

Do not add unrelated characters.

Do not add unrelated objects.

Do not add text.

Do not add logos.

Do not add watermarks.

NEGATIVE PROMPT:

{final_negative}
"""


        # ----------------------------------------------------
        # SHOW PROMPT
        # ----------------------------------------------------

        with st.expander(
            f"🔍 Scene {number} Prompt"
        ):

            st.write(
                final_prompt
            )


        # ----------------------------------------------------
        # PIXABAY REFERENCES
        # ----------------------------------------------------

        if use_pixabay:

            query = (
                environment
                + " "
                + objects
            )


            references = search_pixabay(
                query[:100]
            )


            if references:

                with st.expander(
                    f"🖼️ Pixabay References — Scene {number}"
                ):

                    columns = st.columns(3)


                    for ref_index, reference in enumerate(
                        references
                    ):

                        with columns[
                            ref_index % 3
                        ]:

                            if reference.get(
                                "image"
                            ):

                                st.image(
                                    reference["image"],
                                    use_container_width=True
                                )

                            st.caption(
                                reference.get(
                                    "tags",
                                    ""
                                )
                            )


        # ----------------------------------------------------
        # IMAGE GENERATION PLACEHOLDER
        # ----------------------------------------------------

        st.info(
            "🎨 Scene prompt generated successfully. "
            "The actual image-generation API can be connected "
            "to this scene."
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "AI Story Studio | "
    "Gemini 3.5 Flash-Lite | "
    "Groq | Pixabay"
)
