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
# GEMINI IMPORT
# ============================================================

try:
    from google import genai

    GEMINI_AVAILABLE = True
    GEMINI_IMPORT_ERROR = ""

except Exception as e:
    genai = None
    GEMINI_AVAILABLE = False
    GEMINI_IMPORT_ERROR = str(e)


# ============================================================
# CSS
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
        font-size: 18px;
        color: #777;
        margin-bottom: 30px;
    }

    .scene-card {
        padding: 20px;
        border-radius: 15px;
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
            "Soft Natural",
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
        st.warning("Groq API not configured")

    if PIXABAY_API_KEY:
        st.success("Pixabay API ✓")
    else:
        st.warning("Pixabay API not configured")


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
        "slowly changes from blue to purple and golden light. "
        "A giant glowing portal appears between the trees "
        "and she walks toward it."
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
            "dark trousers, hiking boots, backpack, "
            "curious and brave expression."
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
            + GEMINI_IMPORT_ERROR
        )

    return genai.Client(
        api_key=GEMINI_API_KEY
    )


# ============================================================
# CREATE STORYBOARD
# ============================================================

def create_storyboard():

    client = get_gemini_client()

    prompt = f"""
You are a professional cinematic storyboard director.

Analyze the following complete story:

{story}

MAIN CHARACTER:

{character}

Create exactly {scene_count} connected cinematic scenes.

VISUAL STYLE:
{style}

LIGHTING:
{lighting}

CAMERA:
{camera}

ASPECT RATIO:
{aspect_ratio}

IMPORTANT REQUIREMENTS:

1. The scenes must tell the complete story.
2. Keep the same character appearance in every scene.
3. Keep clothing consistent.
4. Keep important objects consistent.
5. Keep the visual style consistent.
6. Make each scene visually different when the story requires it.
7. Preserve the story's important details.
8. Do not add unrelated characters.
9. Do not add unrelated objects.
10. Do not add text.
11. Do not add logos.
12. Do not add watermarks.
13. Clearly show transformations.
14. Clearly show color changes.
15. Create cinematic compositions.
16. Describe emotions.
17. Describe lighting.
18. Describe environment.
19. Describe camera angle.
20. Describe important visual effects.

If the story says:

BLUE → PURPLE

the image prompt must clearly describe the visible transformation.

Return ONLY valid JSON.

Use this format:

{{
    "story_title": "title",
    "character_bible": "fixed appearance of the character",
    "scenes": [
        {{
            "scene_number": 1,
            "scene_title": "title",
            "story_action": "what happens",
            "environment": "environment",
            "character": "character appearance",
            "objects": "important objects",
            "colors": "colors",
            "lighting": "lighting",
            "camera": "camera",
            "image_prompt": "complete cinematic image prompt",
            "negative_prompt": "negative prompt"
        }}
    ]
}}
"""

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )

    except Exception as e:

        raise Exception(
            "Gemini 2.5 Flash-Lite request failed.\n\n"
            + str(e)
        )

    text = response.text or ""

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
# GROQ ENHANCEMENT
# ============================================================

def enhance_prompt(
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

ORIGINAL IMAGE PROMPT:
{prompt}

NEGATIVE PROMPT:
{negative_prompt}

Improve the image prompt.

Improve:

- cinematic composition
- character consistency
- environment
- lighting
- atmosphere
- depth
- camera
- colors
- visual effects
- emotional storytelling
- object placement

Do NOT change the story.

Do NOT add unrelated characters.

Do NOT add unrelated objects.

If the story contains a color transformation,
make it visually obvious.

Return ONLY JSON:

{{
    "prompt": "improved image prompt",
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

        data = json.loads(
            text.strip()
        )

        return (
            data.get(
                "prompt",
                prompt
            ),
            data.get(
                "negative_prompt",
                negative_prompt
            )
        )

    except Exception:

        return prompt, negative_prompt


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
                    "image": item.get(
                        "webformatURL"
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
    "🚀 GENERATE STORY",
    type="primary",
    use_container_width=True
)


# ============================================================
# MAIN
# ============================================================

if generate:

    if not story.strip():

        st.warning(
            "Please enter your story first."
        )

        st.stop()


    # ========================================================
    # CREATE STORYBOARD
    # ========================================================

    with st.spinner(
        "🧠 Gemini 2.5 Flash-Lite is analyzing your story..."
    ):

        try:

            storyboard = create_storyboard()

        except Exception as e:

            st.error(
                "❌ Gemini Error"
            )

            st.code(
                str(e)
            )

            st.stop()


    # ========================================================
    # STORY INFORMATION
    # ========================================================

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
            "No scenes were returned by Gemini."
        )

        st.stop()


    st.success(
        f"🎬 {len(scenes)} scenes created successfully!"
    )


    st.header(
        "🎞️ " + story_title
    )


    # ========================================================
    # CHARACTER BIBLE
    # ========================================================

    with st.expander(
        "👤 Character Consistency"
    ):

        st.write(
            character_bible
        )


    # ========================================================
    # PROCESS EACH SCENE
    # ========================================================

    for index, scene in enumerate(
        scenes
    ):

        scene_number = scene.get(
            "scene_number",
            index + 1
        )

        scene_title = scene.get(
            "scene_title",
            f"Scene {scene_number}"
        )

        story_action = scene.get(
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

        original_prompt = scene.get(
            "image_prompt",
            ""
        )

        negative_prompt = scene.get(
            "negative_prompt",
            ""
        )


        st.markdown("---")

        st.header(
            f"🎬 Scene {scene_number}: "
            f"{scene_title}"
        )

        st.write(
            story_action
        )


        # ====================================================
        # GROQ
        # ====================================================

        if use_groq:

            with st.spinner(
                f"✨ Improving Scene {scene_number}..."
            ):

                final_prompt, final_negative = (
                    enhance_prompt(
                        original_prompt,
                        negative_prompt,
                        character_bible
                    )
                )

        else:

            final_prompt = original_prompt

            final_negative = negative_prompt


        # ====================================================
        # FINAL PROMPT
        # ====================================================

        final_prompt = f"""
Cinematic AI image for Scene {scene_number}.

COMPLETE STORY:
{story}

CHARACTER CONSISTENCY:
{character_bible}

SCENE ACTION:
{story_action}

ENVIRONMENT:
{environment}

IMPORTANT OBJECTS:
{objects}

IMAGE PROMPT:
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

Keep the character identical to previous scenes.

Keep clothing consistent.

Keep important objects consistent.

Preserve the story.

Show the environment clearly.

Show emotions clearly.

Show important visual details.

Show color changes clearly.

Show transformations clearly.

Do not add unrelated characters.

Do not add unrelated objects.

Do not add text.

Do not add logos.

Do not add watermarks.

NEGATIVE PROMPT:
{final_negative}
"""


        # ====================================================
        # PROMPT DISPLAY
        # ====================================================

        with st.expander(
            f"🔍 View Scene {scene_number} Prompt"
        ):

            st.write(
                final_prompt
            )


        # ====================================================
        # NOTE ABOUT IMAGE
        # ====================================================

        st.info(
            "🎨 Image prompt ready. "
            "Connect your image-generation API/model "
            "to generate the actual image."
        )


        # ====================================================
        # PIXABAY REFERENCES
        # ====================================================

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
                    f"🖼️ Visual References — Scene {scene_number}"
                ):

                    columns = st.columns(3)


                    for ref_index, ref in enumerate(
                        references
                    ):

                        with columns[
                            ref_index % 3
                        ]:

                            if ref.get(
                                "image"
                            ):

                                st.image(
                                    ref["image"],
                                    use_container_width=True
                                )

                            st.caption(
                                ref.get(
                                    "tags",
                                    ""
                                )
                            )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "AI Story Studio • "
    "Gemini 2.5 Flash-Lite • Groq • Pixabay"
)
