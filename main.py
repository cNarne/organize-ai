import asyncio
import base64
import json
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

# Import our Services
from services.vision import vision_service
from services.generation import generation_service
from services.search import search_service
from services.supabase_service import supabase_service

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OrganizeAI")

app = FastAPI(title="OrganizeAI API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Data Transfer Objects (DTOs) ---
class RoomAnalysisRequest(BaseModel):
    image_base64: str | None = None
    room_type: str
    user_id: str


# --- The AI Pipeline Logic ---
async def ai_pipeline_generator(
    room_type: str, image_base64: str, user_id: str
) -> AsyncGenerator[dict, None]:
    """
    Orchestrates the AI steps: Vision -> Search -> Generation -> Persist.
    """

    # Phase 1: Ingestion
    logger.info(f"Starting analysis for user={user_id}")
    yield {"status": "processing", "stage": "ingestion", "message": "Image received. Decoding...", "progress": 5}
    await asyncio.sleep(0.5)

    # Phase 2: Computer Vision — detects room type and clutter items from the image
    yield {"status": "processing", "stage": "vision_analysis", "message": "Analyzing room and clutter with Vision...", "progress": 20}

    detected_items = []
    detected_room_type = room_type  # fallback to client-provided value
    try:
        if image_base64:
            detected_items, detected_room_type = await vision_service.analyze_clutter(image_base64)
            yield {
                "status": "processing",
                "stage": "clutter_detection",
                "message": f"Detected: {detected_room_type}. Found {len(detected_items)} clutter items.",
                "progress": 40,
                "data": detected_items,
                "room_type": detected_room_type
            }
        else:
            yield {"status": "error", "message": "No image data provided."}
            return
    except Exception as e:
        logger.error(f"Vision failed: {e}")
        yield {"status": "error", "message": "Vision API Failed. Check server logs."}
        return

    # Phase 3: Product Search — runs before generation so product names inform the image prompt
    yield {"status": "processing", "stage": "product_matching", "message": f"Searching Amazon for {len(detected_items)} items...", "progress": 60}

    shopping_list = []
    product_names = []

    if detected_items:
        try:
            search_tasks = [
                search_service.search_product(item["query_string"])
                for item in detected_items
            ]
            results = await asyncio.gather(*search_tasks)

            for res in results:
                if res:
                    shopping_list.append(res.model_dump())
                    product_names.append(res.title)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            product_names = [item["query_string"] for item in detected_items]

    yield {"status": "processing", "stage": "product_matching", "message": f"Found {len(shopping_list)} products.", "progress": 75}

    # Phase 4: Image Generation
    yield {"status": "processing", "stage": "image_generation", "message": "Rendering staged design with your products...", "progress": 80}

    after_image_url = ""
    try:
        data_uri = await generation_service.render_clean_room(detected_room_type, image_base64, product_names)

        # Decode base64 → bytes and upload to Supabase Storage.
        # The SSE stream sends back a CDN URL, not megabytes of base64.
        b64_data = data_uri.split(",", 1)[1]
        image_bytes = base64.b64decode(b64_data)
        after_image_url = await supabase_service.upload_image(image_bytes)

        if not after_image_url:
            # Supabase not configured — fall back to data URI so dev still works
            after_image_url = data_uri

        yield {"status": "processing", "stage": "image_generation", "message": "Design rendered successfully.", "progress": 95}
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        after_image_url = "https://placehold.co/1024x1024?text=Generation+Failed"

    # Phase 5: Persist scan to database
    await supabase_service.save_scan(
        user_id=user_id,
        room_type=detected_room_type,
        after_image_url=after_image_url,
        shopping_list=shopping_list,
        detected_items=detected_items,
    )

    # Phase 6: Completion
    yield {
        "status": "complete",
        "progress": 100,
        "message": "Analysis complete.",
        "data": {
            "after_image_url": after_image_url,
            "shopping_list": shopping_list
        }
    }


# --- Analysis Stream Endpoint ---
@app.post("/api/analyze/stream")
async def stream_analysis(request: Request, body: RoomAnalysisRequest):
    async def event_generator():
        try:
            async for step_data in ai_pipeline_generator(body.room_type, body.image_base64, body.user_id):
                yield {
                    "event": "pipeline_update",
                    "data": json.dumps(step_data)
                }
        except asyncio.CancelledError:
            logger.warning("Client disconnected. Stopping pipeline.")
            raise

    return EventSourceResponse(event_generator())


# --- Health Check ---
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "OrganizeAI-Backend"}
