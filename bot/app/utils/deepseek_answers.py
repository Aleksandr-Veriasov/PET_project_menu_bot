from packages.recipes_core.services.provider import get_default_extractor


async def extract_recipes(
        description: str, transcript: str
) -> tuple[str, str, str]:

    extractor = get_default_extractor()
    data = await extractor.extract(
        description=description, recognized_text=transcript
    )
    return data.title, data.instructions_text, data.ingredients_text
