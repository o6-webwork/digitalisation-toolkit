import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Model Configuration (API URLs and tokens are provided by frontend)
    TRANSLATION_MODEL: str = os.getenv("TRANSLATION_MODEL", "sealion")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen2.5")

    # Docling Configuration
    ARTIFACTS_PATH: str = os.getenv("ARTIFACTS_PATH", "")
    MODEL_STORAGE_DIRECTORY: str = os.getenv("MODEL_STORAGE_DIRECTORY", "")

    # Performance Configuration
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))
    PARALLEL_PROCESSING_THRESHOLD: int = int(os.getenv("PARALLEL_PROCESSING_THRESHOLD", "20"))
    GPU_MEMORY_FRACTION: float = float(os.getenv("GPU_MEMORY_FRACTION", "0.8"))
    
    @staticmethod
    def get_api_config(url: Optional[str] = None, authorization: Optional[str] = None, model_name: Optional[str] = None) -> tuple[str, str, str]:
        """Get API configuration - all parameters must be provided by frontend"""
        if not url:
            raise ValueError("API URL must be provided by frontend.")

        if not authorization:
            raise ValueError("API token must be provided by frontend.")

        final_url = url
        final_auth = authorization
        final_model = model_name if model_name else Settings.LLM_MODEL

        return final_url, final_auth, final_model

settings = Settings()