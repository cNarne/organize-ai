import base64
import io
import logging

from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger("OrganizeAI.Generation")


class GenerationService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def render_clean_room(self, room_type: str, base64_image: str, product_names: list[str]) -> str:
        """
        Uses gpt-image-1 image editing to clean the original room in-place.
        The model sees the actual photo, so walls, flooring, windows, and fixed
        furniture are preserved — only the clutter is removed and replaced with
        the suggested organising products.
        Returns a base64 data URI.
        """
        # Decode base64 → raw bytes and wrap for the API
        image_bytes = base64.b64decode(base64_image)
        image_file = ("room.jpg", io.BytesIO(image_bytes), "image/jpeg")

        products_text = (
            ", ".join(product_names)
            if product_names
            else "storage baskets, floating shelves, and label makers"
        )

        prompt = (
            f"Clean and organize this {room_type}. "
            f"Remove all clutter, toys, papers, clothes, and mess from every surface and the floor. "
            f"Keep all walls, flooring, windows, doors, and large fixed furniture exactly where they are — "
            f"do not move, replace, or redesign any structural elements. "
            f"Stage the cleared areas with these organising products neatly placed where the clutter was: {products_text}. "
            f"The result should look professionally cleaned and realistically staged."
        )
        logger.info(f"Edit prompt (truncated): {prompt[:250]}...")

        response = await self.client.images.edit(
            model="gpt-image-1",
            image=image_file,
            prompt=prompt,
            size="1024x1024",
            quality="medium",
            n=1
        )

        image_b64 = response.data[0].b64_json
        logger.info("Image edit successful.")
        return f"data:image/png;base64,{image_b64}"


# Singleton
generation_service = GenerationService()
