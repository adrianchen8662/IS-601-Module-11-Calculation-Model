# app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    This class uses Pydantic's BaseSettings to automatically load configuration
    from environment variables or a .env file. This follows the Twelve-Factor App
    methodology for configuration management.
    """
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/calculator_db"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
