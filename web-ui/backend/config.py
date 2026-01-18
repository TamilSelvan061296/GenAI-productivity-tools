import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    # Azure OpenAI settings
    MODEL_NAME: str = os.environ.get("MODEL_NAME", "gpt-4.1")
    API_VERSION: str = os.environ.get("API_VERSION", "2024-12-01-preview")
    DEPLOYMENT: str = os.environ.get("DEPLOYMENT", "gpt-4.1")
    ENDPOINT: str = os.environ.get("ENDPOINT", "")
    SUBSCRIPTION_KEY: str = os.environ.get("SUBSCRIPTION_KEY", "")

    # Knowledge base path
    KNOWLEDGE_BASE_PATH: str = os.environ.get(
        "KNOWLEDGE_BASE_PATH",
        str(Path(__file__).parent.parent.parent / "youtube-summarizer" / "knowledge_youtube")
    )

    # YouTube server paths
    YOUTUBE_SERVER_DIR: str = str(
        Path(__file__).parent.parent.parent / "youtube-summarizer"
    )
    YOUTUBE_SERVER_PATH: str = str(
        Path(__file__).parent.parent.parent / "youtube-summarizer" / "server.py"
    )

    # Server settings
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8000"))


settings = Settings()
