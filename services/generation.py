import logging
import replicate
from config import settings

logger = logging.getLogger("OrganizeAI.Generation")

class GenerationService:
    def __init__(self):
        self.client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)
        self.model_name = "jagilley/controlnet-canny"

    async def render_clean_room(self, room_type: str, messy_description: str, base64_image: str) -> str:
        """
        Generates a 'Clean' version using ControlNet Canny on Replicate.
        """
        image_uri = f"data:image/jpeg;base64,{base64_image}"
        
        prompt = f"A high-end, modern {room_type}. Perfectly organized, minimalist interior design. Clean surfaces, hidden cables, cinematic lighting, 8k resolution, photorealistic."
        
        try:
            logger.info("--- REPLICATE (CONTROLNET) REQUEST ---")
            logger.info(f"Model: {self.model_name} (Fetching latest version...)")
            
            # 1. Get the latest version object
            model = self.client.models.get(self.model_name)
            latest_version = model.versions.list()[0]
            full_model_string = f"{self.model_name}:{latest_version.id}"
            
            logger.info(f"Full Target: {full_model_string}")
            logger.info("--------------------------------------")
            
            # 2. Run Prediction with MIXED TYPES
            # Based on logs: Resolution/Samples = String, Thresholds = Integer
            output = self.client.run(
                full_model_string,
                input={
                    "image": image_uri,
                    "prompt": prompt,
                    "num_samples": "1",          # Must be STRING
                    "image_resolution": "512",   # Must be STRING
                    "low_threshold": 100,        # Must be INTEGER
                    "high_threshold": 200,       # Must be INTEGER
                    "a_prompt": "best quality, extremely detailed",
                    "n_prompt": "clutter, mess, papers, trash, wires, blurry, lowres, text, watermark, deformed"
                }
            )

            if output and len(output) > 0:
                # The model returns [edge_map, generated_image]. We want the last one.
                generated_url = output[-1]
                logger.info(f"Generation Success. URL: {generated_url}")
                return generated_url
            else:
                 raise Exception("Replicate returned no images.")

        except Exception as e:
            logger.error(f"Replicate Generation Failed: {e}")
            return "https://placehold.co/1024x1024/333/fff?text=Generation+Failed"

# Singleton
generation_service = GenerationService()