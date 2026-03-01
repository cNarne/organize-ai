import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from pydantic import BaseModel

from config import settings

logger = logging.getLogger("OrganizeAI.Search")

# --- Amazon PA-API 5.0 constants ---
_HOST = "webservices.amazon.com"
_REGION = "us-east-1"
_URI = "/paapi5/searchitems"
_SERVICE = "ProductAdvertisingAPI"
_TARGET = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems"


# --- Data Model ---
class ProductResult(BaseModel):
    title: str
    price: str
    image: str
    link: str
    rating: float
    source_query: str


# --- AWS Signature Version 4 helpers ---
def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret: str, date_stamp: str) -> bytes:
    k = _hmac_sha256(("AWS4" + secret).encode("utf-8"), date_stamp)
    k = _hmac_sha256(k, _REGION)
    k = _hmac_sha256(k, _SERVICE)
    k = _hmac_sha256(k, "aws4_request")
    return k


def _signed_headers(access_key: str, secret_key: str, amz_date: str, date_stamp: str, body: str) -> dict:
    body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

    headers = {
        "content-encoding": "amz-1.0",
        "content-type": "application/json; charset=utf-8",
        "host": _HOST,
        "x-amz-date": amz_date,
        "x-amz-target": _TARGET,
    }

    sorted_keys = sorted(headers)
    canonical_headers = "".join(f"{k}:{headers[k]}\n" for k in sorted_keys)
    signed_headers_str = ";".join(sorted_keys)

    canonical_request = "\n".join([
        "POST", _URI, "",
        canonical_headers, signed_headers_str, body_hash,
    ])

    credential_scope = f"{date_stamp}/{_REGION}/{_SERVICE}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amz_date, credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])

    signature = hmac.new(
        _signing_key(secret_key, date_stamp),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    auth = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers_str}, Signature={signature}"
    )
    return {**headers, "Authorization": auth}


# --- Search Service ---
class AmazonSearchService:
    def __init__(self):
        self._access_key = settings.AMAZON_ACCESS_KEY
        self._secret_key = settings.AMAZON_SECRET_KEY
        self._associate_tag = settings.AMAZON_ASSOCIATE_TAG

    @property
    def _enabled(self) -> bool:
        return bool(self._access_key and self._secret_key and self._associate_tag)

    async def search_product(self, query: str) -> Optional[ProductResult]:
        if not self._enabled:
            logger.warning("Amazon PA-API credentials not configured — using mock data.")
            return self._mock(query)

        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        payload = {
            "Keywords": query,
            "Resources": [
                "Images.Primary.Medium",
                "ItemInfo.Title",
                "Offers.Listings.Price",
            ],
            "SearchIndex": "All",
            "PartnerTag": self._associate_tag,
            "PartnerType": "Associates",
            "Marketplace": "www.amazon.com",
            "Operation": "SearchItems",
        }
        body = json.dumps(payload, separators=(",", ":"))
        headers = _signed_headers(self._access_key, self._secret_key, amz_date, date_stamp, body)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(f"https://{_HOST}{_URI}", content=body, headers=headers)

            if response.status_code != 200:
                logger.error(f"PA-API error {response.status_code}: {response.text[:400]}")
                return self._mock(query)

            data = response.json()
            items = data.get("SearchResult", {}).get("Items", [])

            if not items:
                logger.warning(f"No PA-API results for '{query}'")
                return None

            item = items[0]
            title = item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", query)
            # DetailPageURL already contains the affiliate tag
            link = item.get("DetailPageURL", "https://www.amazon.com")
            image = item.get("Images", {}).get("Primary", {}).get("Medium", {}).get("URL", "")
            listings = item.get("Offers", {}).get("Listings", [])
            price = listings[0].get("Price", {}).get("DisplayAmount", "N/A") if listings else "N/A"

            logger.info(f"PA-API result for '{query}': {title} — {price}")
            return ProductResult(title=title, price=price, image=image, link=link, rating=0.0, source_query=query)

        except Exception as e:
            logger.error(f"PA-API search failed for '{query}': {e}")
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
