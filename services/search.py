import logging
from typing import Optional

import httpx
from pydantic import BaseModel

from config import settings

logger = logging.getLogger("OrganizeAI.Search")

SERPAPI_URL = "https://serpapi.com/search"


# --- Data Model ---
class ProductResult(BaseModel):
    title: str
    price: str
    image: str
    link: str
    rating: float
    source_query: str


class AmazonSearchService:
    def __init__(self):
        self._api_key = settings.SERPAPI_KEY

    @property
    def _enabled(self) -> bool:
        return bool(self._api_key)

    async def search_product(self, query: str) -> Optional[ProductResult]:
        if not self._enabled:
            logger.warning("SERPAPI_KEY not configured — using mock data.")
            return self._mock(query)

        params = {
            "engine": "amazon",
            "k": query,
            "amazon_domain": "amazon.com",
            "api_key": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(SERPAPI_URL, params=params)

            if response.status_code != 200:
                logger.error(f"SerpAPI error {response.status_code}: {response.text[:300]}")
                return self._mock(query)

            data = response.json()
            results = data.get("organic_results", [])

            if not results:
                logger.warning(f"No SerpAPI results for '{query}'")
                return None

            item = results[0]
            title = item.get("title", query)
            link = item.get("link", "https://www.amazon.com")
            image = item.get("thumbnail", "")
            price = item.get("price", "N/A")
            rating = float(item.get("rating", 0.0) or 0.0)

            logger.info(f"SerpAPI result for '{query}': {title} — {price}")
            return ProductResult(title=title, price=price, image=image, link=link, rating=rating, source_query=query)

        except Exception as e:
            logger.error(f"SerpAPI search failed for '{query}': {e}")
            return self._mock(query)

    def _mock(self, query: str) -> ProductResult:
        return ProductResult(
            title=f"Amazon Basics {query.title()}",
            price="$19.99",
            image="https://placehold.co/200x200?text=Product",
            link="https://www.amazon.com",
            rating=4.0,
            source_query=query,
        )


search_service = AmazonSearchService()
