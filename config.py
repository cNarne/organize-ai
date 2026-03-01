import os
from dotenv import load_dotenv

# Loads .env for local dev; no-ops on Railway where vars come from os.environ
load_dotenv()


class Settings:
    APP_NAME: str = "OrganizeAI"
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str | None
    RAINFOREST_API_KEY: str | None
    REPLICATE_API_TOKEN: str | None
    SUPABASE_URL: str | None
    SUPABASE_SERVICE_KEY: str | None

    def __init__(self):
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            available = [k for k in os.environ if not k.startswith("_")]
            raise RuntimeError(
                f"OPENAI_API_KEY is not set. "
                f"Available env vars: {sorted(available)}"
            )
        self.OPENAI_API_KEY = key
        self.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
        self.RAINFOREST_API_KEY = os.environ.get("RAINFOREST_API_KEY")
        self.REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
        self.SUPABASE_URL = os.environ.get("SUPABASE_URL")
        self.SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")


settings = Settings()
