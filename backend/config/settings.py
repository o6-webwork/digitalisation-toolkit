import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Configuration
    TRANSLATION_API_URL: str = os.getenv("TRANSLATION_API_URL", "")
    TRANSLATION_API_TOKEN: str = os.getenv("TRANSLATION_API_TOKEN", "token-abc123")
    TRANSLATION_MODEL: str = os.getenv("TRANSLATION_MODEL", "sealion")
    
    LLM_API_URL: str = os.getenv("LLM_API_URL", "http://localhost:11437/v1/chat/completions")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen2.5")
    
    # Docling Configuration
    ARTIFACTS_PATH: str = os.getenv("ARTIFACTS_PATH", "")
    MODEL_STORAGE_DIRECTORY: str = os.getenv("MODEL_STORAGE_DIRECTORY", "")
    
    @staticmethod
    def get_api_config(url: Optional[str] = None, authorization: Optional[str] = None, model_name: Optional[str] = None) -> tuple[str, str, str]:
        """Get API configuration with fallbacks to environment variables"""
        final_url = url if url else Settings.LLM_API_URL
        final_auth = authorization if authorization else Settings.TRANSLATION_API_TOKEN
        final_model = model_name if model_name else Settings.LLM_MODEL
        
        if not final_auth or not final_url:
            raise ValueError("API URL or token is not configured.")
            
        return final_url, final_auth, final_model

settings = Settings()