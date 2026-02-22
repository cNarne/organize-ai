import base64
import json
import logging
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger("OrganizeAI.Vision")

class VisionService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def analyze_clutter(self, base64_image: str, room_type: str) -> list[dict]:
        """
        Sends image to GPT-4o (Vision) to extract a shopping list.
        Returns a structured list of dictionaries.
        """
        prompt = f"""
        You are an expert Interior Organizer. Analyze this messy {room_type}.
        Identify 3-5 specific organization products that would solve the visible clutter.
        
        Return ONLY valid JSON in this format:
        {{
            "items": [
                {{
                    "query_string": "specific search term for amazon",
                    "reason": "why this helps",
                    "category": "storage|cable_management|decor"
                }}
            ]
        }}
        """

        try:
            # --- LOGGING: AUDIT TRAIL ---
            logger.info("--- VISION REQUEST PAYLOAD ---")
            logger.info(f"Model: gpt-4o")
            logger.info(f"Room Type: {room_type}")
            # We log that we have the image, but not the 10MB string itself
            logger.info(f"Image Payload: [Base64 String - {len(base64_image)} chars]")
            logger.info(f"Prompt: {prompt.strip()[:100]}... (truncated)")
            logger.info("------------------------------")

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
            
            # Parse the response
            content = response.choices[0].message.content
            
            # Log the raw response so you can debug parsing errors
            logger.info(f"Vision Response: {content[:100]}...") 

            data = json.loads(content)
            return data.get("items", [])

        except Exception as e:
            logger.error(f"Vision API Failed: {e}")
            return [
                {"query_string": "desk organizer generic", "reason": "API Error Fallback", "category": "storage"}
            ]

# Singleton
vision_service = VisionService()