from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # AI/ML settings
    google_api_key: Optional[str] = None
    
    # Database settings
    database_path: str = "invoices.db"
    
    # Logging settings
    log_level: str = "INFO"
    
    # Validation settings
    high_amount_threshold: float = 1000000.0
    amount_tolerance: float = 0.01
    
    # PDF extraction settings
    max_pdf_size_mb: int = 50
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()