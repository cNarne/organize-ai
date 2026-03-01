import asyncio
import logging
import uuid

from supabase import create_client, Client
from config import settings

logger = logging.getLogger("OrganizeAI.Supabase")

BUCKET = "generated-images"


class SupabaseService:
    """
    Wraps Supabase Storage and Database operations.
    The sync supabase client is run in a thread pool to avoid blocking
    FastAPI's async event loop.
    """

    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            logger.warning("Supabase credentials not set — storage and DB persistence disabled.")
            self._client: Client | None = None
        else:
            self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def upload_image(self, image_bytes: bytes) -> str:
        """
        Uploads a PNG to Supabase Storage.
        Returns the public CDN URL.
        Falls back to empty string if Supabase is not configured.
        """
        if not self.enabled:
            logger.warning("Supabase not configured — skipping image upload.")
            return ""

        path = f"{uuid.uuid4()}.png"

        def _upload():
            self._client.storage.from_(BUCKET).upload(
                path,
                image_bytes,
                {"content-type": "image/png", "upsert": "false"}
            )
            return self._client.storage.from_(BUCKET).get_public_url(path)

        public_url = await asyncio.to_thread(_upload)
        logger.info(f"Image uploaded to Supabase Storage: {public_url}")
        return public_url

    async def save_scan(
        self,
        user_id: str,
        room_type: str,
        after_image_url: str,
        shopping_list: list[dict],
        detected_items: list[dict],
    ) -> str | None:
        """
        Persists a completed scan to the database.
        Returns the new scan UUID, or None if Supabase is not configured.
        """
        if not self.enabled:
            logger.warning("Supabase not configured — skipping scan save.")
            return None

        def _insert():
            result = self._client.table("scans").insert({
                "user_id": user_id,
                "room_type": room_type,
                "after_image_url": after_image_url,
                "shopping_list": shopping_list,
                "detected_items": detected_items,
            }).execute()
            return result.data[0]["id"]

        scan_id = await asyncio.to_thread(_insert)
        logger.info(f"Scan saved to database: scan_id={scan_id}")
        return scan_id


# Singleton
supabase_service = SupabaseService()
