import logging
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger("OrganizeAI.Generation")


class GenerationService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def _describe_layout(self, base64_image: str, room_type: str) -> str:
        """
        Uses GPT-4o Vision to extract the room's permanent structural features,
        ignoring all clutter so the generated image reflects the real room's bones.
        """
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Describe the permanent structural features of this {room_type} "
                            f"for an interior design brief. Focus ONLY on: room shape, wall colors, "
                            f"flooring type and color, window positions, door locations, and fixed "
                            f"architectural elements like built-in shelving or radiators. "
                            f"Completely ignore all clutter, toys, papers, clothes, or any moveable objects. "
                            f"Be concise, 3-4 sentences."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }],
            max_tokens=200
        )
        return response.choices[0].message.content

    async def render_clean_room(self, room_type: str, base64_image: str, product_names: list[str]) -> str:
        """
        Two-step generation pipeline:
          1. GPT-4o Vision → describes the room's structural layout (ignoring clutter)
          2. gpt-image-1 → generates a clean, staged version featuring the detected products
        Returns a base64 data URI string.
        """
        # Step 1: Get layout description from the real image
        logger.info("Generation Step 1: Describing room layout with GPT-4o Vision...")
        layout = await self._describe_layout(base64_image, room_type)
        logger.info(f"Layout description: {layout}")

        # Step 2: Build a rich prompt using layout + actual product names
        products_text = (
            ", ".join(product_names)
            if product_names
            else "modern storage baskets, floating shelves, and label makers"
        )
        prompt = (
            f"A professional interior design photo of a beautifully clean and organized {room_type}. "
            f"{layout} "
            f"The room is neatly staged with these specific products clearly visible and in use: {products_text}. "
            f"Everything is tidy and thoughtfully arranged. No clutter, no mess. "
            f"Soft natural lighting, photorealistic, magazine-quality interior photography."
        )
        logger.info(f"Generation prompt (truncated): {prompt[:250]}...")

        # Step 3: Generate with gpt-image-1
        logger.info("Generation Step 2: Calling gpt-image-1...")
        response = await self.client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
            quality="medium",
            n=1
        )

        image_b64 = response.data[0].b64_json
        logger.info("Image generation successful.")
        return f"data:image/png;base64,{image_b64}"


# Singleton
generation_service = GenerationService()
