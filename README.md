# OrganizeAI Backend 🧠🛋️

OrganizeAI is an AI-powered virtual staging and e-commerce pipeline. It takes a user's photo of a cluttered space, uses vision models to identify the mess, generates a pristine structural render of the cleaned room, and curates a shoppable list of real-world organizational products.

![OrganizeAI Demo](docs/demo.png)

## System Architecture & Agentic Workflow

This backend is built with **Python** and **FastAPI**, utilizing an event-driven Server-Sent Events (SSE) architecture to stream real-time pipeline updates to the client. 

Instead of a monolithic AI call, the system delegates tasks across specialized models and APIs, ensuring high fidelity and robust error handling:

1. **Ingestion & Validation:** Receives base64 image payloads and room context.
2. **Computer Vision (GPT-4o):** Analyzes the structural clutter, identifying specific problem areas and outputting a structured JSON schema of recommended product categories.
3. **Generative Staging (ControlNet Canny):** Uses edge-detection blueprints to lock the original room geometry while restyling the surfaces to be minimalist and clean.
4. **Parallel E-Commerce Search (Rainforest API):** Asynchronously maps the AI's product recommendations to real-world Amazon listings, fetching current prices and links in parallel for maximum speed.

## Technical Highlights
* **Resilient API Design:** If a downstream service (e.g., the generation model or search API) times out or triggers a safety filter, the pipeline catches the exception, logs the payload, and serves graceful fallbacks without crashing the user session.
* **Async Concurrency:** Leverages `asyncio.gather` to execute external API calls concurrently, dropping response times significantly.
* **Strict Type Validation:** Uses Pydantic V2 for strict data serialization and environment configuration.

## Tech Stack
* **Framework:** FastAPI, Uvicorn, Python 3.12
* **Package Management:** Poetry
* **AI/ML:** OpenAI (GPT-4o Vision), Replicate (Stable Diffusion / ControlNet)
* **Integrations:** Rainforest API (Amazon Search)

## Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/organize-ai-backend.git](https://github.com/YOUR_USERNAME/organize-ai-backend.git)
   cd organize-ai-backend
