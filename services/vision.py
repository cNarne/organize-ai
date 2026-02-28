import base64
import json
import logging
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger("OrganizeAI.Vision")

class VisionService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def analyze_clutter(self, base64_image: str) -> tuple[list[dict], str]:
        """
        Sends image to GPT-4o Vision to detect the room type and identify
        organisation products that would solve the visible clutter.
        Returns (items, detected_room_type).
        """
        prompt = """
        You are an expert Interior Organizer. Look at this room photo.

        First, identify what type of room this is (e.g. "children's bedroom",
        "home office", "living room", "kitchen", "bathroom", etc.).

        Then identify 3-5 specific organisation products that would solve the
        visible clutter, chosen specifically for that room type.

        Return ONLY valid JSON in this format:
        {
            "room_type": "detected room type as a short descriptive string",
            "items": [
                {
                    "query_string": "specific search term for amazon",
                    "reason": "why this helps",
                    "category": "storage|cable_management|decor"
                }
            ]
        }
        """

        try:
            logger.info("--- VISION REQUEST ---")
            logger.info(f"Image Payload: [Base64 String - {len(base64_image)} chars]")

            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            },
                        ],
                    }
                ],
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            logger.info(f"Vision Response: {content[:150]}...")

            data = json.loads(content)
            detected_room_type = data.get("room_type", "room")
            items = data.get("items", [])

            logger.info(f"Detected room type: {detected_room_type}")
            return items, detected_room_type

        except Exception as e:
            logger.error(f"Vision API Failed: {e}")
            return (
                [{"query_string": "general storage organizer", "reason": "API Error Fallback", "category": "storage"}],
                "room"
            )

# Singleton
vision_service = VisionService()