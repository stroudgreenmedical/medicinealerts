from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import secrets


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Medicines Alerts Manager"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./data/alerts.db")
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"
    
    # Admin credentials
    ADMIN_EMAIL: str = Field(default="anjan.chakraborty@nhs.net")
    ADMIN_PASSWORD: str = Field(default="changeme")  # Must be changed in production
    
    # GOV.UK APIs
    GOVUK_SEARCH_API: str = "https://www.gov.uk/api/search.json"
    GOVUK_CONTENT_API: str = "https://www.gov.uk/api/content"
    
    # Configuration
    APPROVER_NAME: str = "Dr Anjan Chakraborty"
    APPROVER_SWITCH_DATE: str = "2025-09-17"  # Switch to Chandni after this
    APPROVER_AFTER: str = "Chandni Shah"
    POLL_INTERVAL_HOURS: int = 4
    BACKFILL_YEARS: int = 8
    
    # Filtering
    ORG_FILTER: str = "medicines-and-healthcare-products-regulatory-agency"
    RELEVANT_SPECIALTIES: list[str] = Field(
        default=["General practice", "Dispensing GP practices"]
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()