from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "OrganizeAI"
    
    # These must match the variables in your .env file exactly
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str | None = None
    RAINFOREST_API_KEY: str | None = None
    REPLICATE_API_TOKEN: str  # <-- Add this line
    # This reads the .env file
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

# --- THE IMPORTANT PART ---
# You must instantiate the class into a variable named 'settings'
settings = Settings()