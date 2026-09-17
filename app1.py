def generate_gemini_prompt(
    story,
    style,
    aspect_ratio,
    lighting,
    camera,
    character
):
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY is missing.")

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    instruction = f"""
You are an expert AI image prompt engineer.

Analyze the following story and create a highly detailed,
cinematic image-generation prompt.

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

Requirements:

- Preserve every important story element.
- Identify the main character.
- Describe character appearance and clothing.
- Describe the environment.
- Describe important objects.
- Describe colors.
- Describe lighting.
- Describe camera composition.
- Describe atmosphere.
- Describe emotions.
- Describe magical/special effects.
- Clearly describe transformations.
- Clearly describe color changes.
- Do not add unrelated objects.
- Do not add text.
- Do not add logos.
- Do not add watermarks.
- Make the scene visually creative and cinematic.

Return ONLY valid JSON:

{{
    "title": "short title",
    "prompt": "complete detailed image prompt",
    "negative_prompt": "negative prompt"
}}
"""

    # ========================================================
    # TRY GEMINI 2.5 FLASH-LITE FIRST
    # ========================================================

    models_to_try = [
        "gemini-2.5-flash-lite",
        "gemini-1.5-flash-lite"
    ]

    last_error = None

    for model_name in models_to_try:

        try:

            response = client.models.generate_content(
                model=model_name,
                contents=instruction
            )

            text = response.text.strip()

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

            try:

                result = json.loads(text)

                # Add model information
                result["model_used"] = model_name

                return result

            except json.JSONDecodeError:

                return {
                    "title": "AI Generated Scene",
                    "prompt": text,
                    "negative_prompt": (
                        "blurry, low quality, distorted face, "
                        "bad anatomy, extra fingers, extra limbs, "
                        "duplicate objects, text, logo, watermark"
                    ),
                    "model_used": model_name
                }

        except Exception as error:

            last_error = error

            continue

    raise Exception(
        f"Gemini models failed. Last error: {last_error}"
    )
