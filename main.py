import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

# Import our Services
from config import settings
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

# --- Data Transfer Objects (DTOs) ---
class RoomAnalysisRequest(BaseModel):
    image_base64: str | None = None 
    room_type: str
    user_id: str

# --- The AI Pipeline Logic ---
async def ai_pipeline_generator(room_type: str, image_base64: str) -> AsyncGenerator[dict, None]:
    """
    Orchestrates the AI steps: Vision -> Search -> Response.
    """
    
    # Phase 1: Ingestion
    logger.info(f"Starting analysis for {room_type}")
    yield {"status": "processing", "stage": "ingestion", "message": "Image received. Decoding...", "progress": 5}
    await asyncio.sleep(0.5)
    
    # Phase 2: Computer Vision (Real Gemini Call)
    yield {"status": "processing", "stage": "vision_analysis", "message": "Analyzing clutter with Gemini Vision...", "progress": 20}
    
    detected_items = []
    try:
        if image_base64:
            # Call the Vision Service
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

    # Phase 3: Generative AI (Placeholder for now)
    yield {"status": "processing", "stage": "image_generation", "message": "Rendering new minimalist design (respecting room layout)...", "progress": 60}
    
    # We don't need the messy summary anymore, the image itself is the guide.
    messy_summary = "" 
    
    generated_image_url = ""
    try:
        # --- UPDATED CALL: Passing image_base64 ---
        if settings.REPLICATE_API_TOKEN and image_base64:
            generated_image_url = await generation_service.render_clean_room(room_type, messy_summary, image_base64)
            yield {"status": "processing", "stage": "image_generation", "message": "Design rendered successfully.", "progress": 75}
        else:
             generated_image_url = "https://placehold.co/1024x1024?text=Missing+Replicate+Key+or+Image"
             logger.warning("Skipping generation: Missing Replicate key or image data.")
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        generated_image_url = "https://placehold.co/1024x1024?text=Gen+Error"
    
    # Phase 4: Product Search (Real Amazon Search)
    yield {"status": "processing", "stage": "product_matching", "message": f"Searching Amazon for {len(detected_items)} items...", "progress": 80}
    
    shopping_list = []
    
    # Run searches in parallel for speed
    if detected_items:
        try:
            search_tasks = [
                search_service.search_product(item["query_string"]) 
                for item in detected_items
            ]
            results = await asyncio.gather(*search_tasks)
            
            # Filter out failed searches
            for res in results:
                if res:
                    shopping_list.append(res.model_dump())
        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Don't crash the whole pipeline if search fails, just return empty list
            shopping_list = []

    # Phase 5: Completion
    yield {
        "status": "complete", 
        "progress": 100, 
        "message": "Analysis complete.",
        "data": {
            "after_image_url": generated_image_url,  # <--- The Real DALL-E URL
            "shopping_list": shopping_list 
        }
    }

# --- The API Endpoint ---
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