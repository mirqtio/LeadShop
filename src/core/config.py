"""
LeadFactory Configuration Settings
Implements environment-based configuration with validation
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Core Application
    APP_NAME: str = Field(default="LeadFactory", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    ENVIRONMENT: str = Field(default="development", description="Environment (development/staging/production)")
    BASE_URL: str = Field(default="http://localhost:8000", description="Base application URL")
    DEBUG: bool = Field(default=False, description="Debug mode")
    SECRET_KEY: str = Field(..., description="Secret key for JWT and encryption")
    
    # Database Configuration
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DATABASE_POOL_MIN_CONN: int = Field(default=2, description="Minimum database connections")
    DATABASE_POOL_MAX_CONN: int = Field(default=10, description="Maximum database connections")
    DATABASE_ECHO: bool = Field(default=False, description="Echo SQL queries")
    
    # Redis Configuration
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    CACHE_TTL: int = Field(default=3600, description="Default cache TTL in seconds")
    
    # Celery Configuration
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", description="Celery result backend")
    
    # External API Keys
    GOOGLE_API_KEY: Optional[str] = Field(default=None, description="Google API key")
    GOOGLE_PAGESPEED_API_KEY: Optional[str] = Field(default=None, description="Google PageSpeed API key")
    GOOGLE_PLACES_API_KEY: Optional[str] = Field(default=None, description="Google Places API key for GBP integration")
    SEMRUSH_API_KEY: Optional[str] = Field(default=None, description="SEMrush API key")
    SCREENSHOTONE_API_KEY: Optional[str] = Field(default=None, description="ScreenshotOne API key for screenshot capture")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    
    # AWS Configuration (PRP-000)
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS access key ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS secret access key")
    AWS_DEFAULT_REGION: str = Field(default="us-east-1", description="AWS default region")
    AWS_S3_BUCKET_NAME: Optional[str] = Field(default=None, description="S3 bucket name for file storage")
    
    # Email Configuration
    SENDGRID_API_KEY: Optional[str] = Field(default=None, description="SendGrid API key")
    FROM_EMAIL: str = Field(default="noreply@leadfactory.com", description="Default from email")
    FROM_NAME: str = Field(default="LeadFactory", description="Default from name")
    
    # Performance Settings
    MAX_CONCURRENT_ASSESSMENTS: int = Field(default=10, description="Max concurrent assessments")
    MAX_CONCURRENT_REQUESTS: int = Field(default=10, description="Max concurrent HTTP requests")
    REQUEST_TIMEOUT_SECONDS: int = Field(default=30, description="HTTP request timeout")
    MAX_LEADS_PER_BATCH: int = Field(default=100, description="Max leads per batch operation")
    
    # Cost Control
    COST_BUDGET_USD: float = Field(default=1000.0, description="Monthly cost budget in USD")
    DAILY_BUDGET_CAP: float = Field(default=100.0, description="Daily cost cap in USD")
    PER_LEAD_CAP: float = Field(default=2.50, description="Cost cap per lead assessment")
    
    # Feature Flags
    ENABLE_ENRICHMENT: bool = Field(default=True, description="Enable lead enrichment")
    ENABLE_LLM_INSIGHTS: bool = Field(default=True, description="Enable LLM insights")
    ENABLE_EMAIL_TRACKING: bool = Field(default=True, description="Enable email tracking")
    ENABLE_PAGESPEED: bool = Field(default=True, description="Enable PageSpeed assessments")
    ENABLE_SEMRUSH: bool = Field(default=False, description="Enable SEMrush integration")
    ENABLE_OPENAI: bool = Field(default=True, description="Enable OpenAI integration")
    
    # Pricing
    REPORT_PRICE_CENTS: int = Field(default=39900, description="Report price in cents ($399.00)")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json/text)")
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics")
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def report_price_dollars(self) -> float:
        return self.REPORT_PRICE_CENTS / 100.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields from .env


# Create global settings instance
settings = Settings()

# Validate required settings for production
if settings.is_production:
    required_production_settings = [
        "SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL",
    ]
    
    for setting in required_production_settings:
        if not getattr(settings, setting):
            raise ValueError(f"Production setting {setting} is required but not set")