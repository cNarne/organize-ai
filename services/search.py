import httpx
import logging
import asyncio
import json
from typing import List, Optional
from pydantic import BaseModel
from config import settings

logger = logging.getLogger("OrganizeAI.Search")

# --- Data Models ---
class ProductResult(BaseModel):
    title: str
    price: str
    image: str
    link: str
    rating: float
    source_query: str

class AmazonSearchService:
    def __init__(self):
        self.api_base = "https://api.rainforestapi.com/request"
        self.api_key = settings.RAINFOREST_API_KEY
        self.mock_db = {
            "cable management": {"title": "Joto Cable Management Sleeve", "price": "$11.99", "image": "https://m.media-amazon.com/images/I/718VCAX41PL._AC_SL1500_.jpg", "link": "https://amazon.com/dp/B015HWXG4M", "rating": 4.5},
            "monitor stand": {"title": "Westree Monitor Stand Riser", "price": "$29.99", "image": "https://m.media-amazon.com/images/I/71S-p+g3CjL._AC_SL1500_.jpg", "link": "https://amazon.com/dp/B07H8N4858", "rating": 4.7},
        }

    async def search_product(self, query: str) -> Optional[ProductResult]:
        """
        Async call to Rainforest API to find the best Amazon match.
        """
        if not self.api_key:
            logger.warning("No Rainforest Key. Using Mock Data.")
            return self._get_mock(query)

        params = {
            "api_key": self.api_key,
            "type": "search",
            "amazon_domain": "amazon.com",
            "search_term": query,
            "sort_by": "featured",
            "output": "json"
        }

        try:
            # --- LOGGING: AUDIT TRAIL ---
            # Create a copy to redact the key before printing
            safe_params = params.copy()
            safe_params['api_key'] = "REDACTED_FOR_LOGS"
            
            logger.info(f"--- AMAZON SEARCH REQUEST ({query}) ---")
            logger.info(json.dumps(safe_params, indent=2))
            logger.info("-------------------------------------")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.api_base, params=params)
                
                if response.status_code != 200:
                    logger.error(f"Search API Error {response.status_code}: {response.text}")
                    return self._get_mock(query)
                
                data = response.json()
                results = data.get("search_results", [])
                
                if not results:
                    logger.warning(f"No results found for '{query}'")
                    return None

                top_pick = results[0]
                
                return ProductResult(
                    title=top_pick.get("title", "Unknown Item"),
                    price=top_pick.get("price", {}).get("raw", "N/A"),
                    image=top_pick.get("image", ""),
                    link=top_pick.get("link", ""),
                    rating=top_pick.get("rating", 0.0),
                    source_query=query
                )

        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            return self._get_mock(query)

    def _get_mock(self, query) -> ProductResult:
        """Fallback generator"""
        key = "cable management" if "cable" in query.lower() else "monitor stand"
        item = self.mock_db.get(key, {
            "title": f"Amazon Basics {query.title()}",
            "price": "$19.99",
            "image": "https://placehold.co/200x200?text=Product",
            "link": "https://amazon.com", 
            "rating": 4.0
        })
        return ProductResult(**item, source_query=query)

search_service = AmazonSearchService()