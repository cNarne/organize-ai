import asyncio
import base64
import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

# Import our Services
from services.vision import vision_service
from services.generation import generation_service
from services.search import search_service

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

# In-memory image store: { image_id: bytes }
# Keeps generated images available for the lifetime of the server process.
_image_store: dict[str, bytes] = {}


# --- Data Transfer Objects (DTOs) ---
class RoomAnalysisRequest(BaseModel):
    image_base64: str | None = None
    room_type: str
    user_id: str


# --- The AI Pipeline Logic ---
async def ai_pipeline_generator(room_type: str, image_base64: str) -> AsyncGenerator[dict, None]:
    """
    Orchestrates the AI steps: Vision -> Search -> Generation.
    """

    # Phase 1: Ingestion
    logger.info(f"Starting analysis for {room_type}")
    yield {"status": "processing", "stage": "ingestion", "message": "Image received. Decoding...", "progress": 5}
    await asyncio.sleep(0.5)

    # Phase 2: Computer Vision
    yield {"status": "processing", "stage": "vision_analysis", "message": "Analyzing clutter with Gemini Vision...", "progress": 20}

    detected_items = []
    try:
        if image_base64:
            detected_items = await vision_service.analyze_clutter(image_base64, room_type)
            yield {
                "status": "processing",
                "stage": "clutter_detection",
                "message": f"Identified {len(detected_items)} clutter items.",
                "progress": 40,
                "data": detected_items
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
        data_uri = await generation_service.render_clean_room(room_type, image_base64, product_names)

        # Strip the data URI prefix and store raw bytes server-side.
        # The SSE stream sends only a small URL — not megabytes of base64.
        b64_data = data_uri.split(",", 1)[1]
        image_bytes = base64.b64decode(b64_data)
        image_id = str(uuid.uuid4())
        _image_store[image_id] = image_bytes
        after_image_url = f"http://localhost:8000/api/image/{image_id}"

        logger.info(f"Image stored with id={image_id}")
        yield {"status": "processing", "stage": "image_generation", "message": "Design rendered successfully.", "progress": 95}
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        after_image_url = "https://placehold.co/1024x1024?text=Generation+Failed"

    # Phase 5: Completion
    yield {
        "status": "complete",
        "progress": 100,
        "message": "Analysis complete.",
        "data": {
            "after_image_url": after_image_url,
            "shopping_list": shopping_list
        }
    }


# --- Image Retrieval Endpoint ---
@app.get("/api/image/{image_id}")
def get_image(image_id: str):
    image_bytes = _image_store.get(image_id)
    if not image_bytes:
        raise HTTPException(status_code=404, detail="Image not found.")
    return Response(content=image_bytes, media_type="image/png")


# --- Analysis Stream Endpoint ---
@app.post("/api/analyze/stream")
async def stream_analysis(request: Request, body: RoomAnalysisRequest):
    async def event_generator():
        try:
            async for step_data in ai_pipeline_generator(body.room_type, body.image_base64):
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
