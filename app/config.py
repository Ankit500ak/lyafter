"""
Configuration management for the Lyftr AI webhook API.
Loads environment variables with defaults and validation.
"""
import os
from typing import Optional
from urllib.parse import urlparse


class Config:
    """Application configuration from environment variables."""
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:////data/app.db"
    )
    
    # Webhook secret - MUST be set for readiness check
    WEBHOOK_SECRET: Optional[str] = os.getenv("WEBHOOK_SECRET")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # API
    API_TITLE: str = "Lyftr Webhook API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "WhatsApp-like webhook API with HMAC verification"
    
    @classmethod
    def validate(cls) -> tuple[bool, Optional[str]]:
        """
        Validate critical configuration.
        Returns: (is_valid, error_message)
        """
        if not cls.WEBHOOK_SECRET:
            return False, "WEBHOOK_SECRET environment variable is not set"
        
        if not cls.DATABASE_URL:
            return False, "DATABASE_URL environment variable is not set"
        
        return True, None
    
    @classmethod
    def get_db_path(cls) -> str:
        """Extract the file path from DATABASE_URL."""
        url = cls.DATABASE_URL
        if url.startswith("sqlite:///"):
            # Handle sqlite:///path/to/db.db format (3 slashes = absolute)
            return url.replace("sqlite:///", "")
        elif url.startswith("sqlite://"):
            # Handle sqlite://path/to/db.db format (2 slashes = relative)
            return url.replace("sqlite://", "")
        return url


config = Config()
