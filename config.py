from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Loads .env for local dev; silently no-ops on Railway where vars come from os.environ
load_dotenv()

class Settings(BaseSettings):
    APP_NAME: str = "OrganizeAI"
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str | None = None
    RAINFOREST_API_KEY: str | None = None
    REPLICATE_API_TOKEN: str | None = None
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_KEY: str | None = None

settings = Settings()