"""
Application configuration management.

Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from package directory
_PACKAGE_DIR = Path(__file__).parent
_PROJECT_ROOT = _PACKAGE_DIR.parent

# Try loading .env from multiple locations
for env_path in [_PACKAGE_DIR / ".env", _PROJECT_ROOT / ".env"]:
    if env_path.exists():
        load_dotenv(env_path)
        break


class Config:
    """Application configuration loaded from environment variables."""
    
    # ========================================
    # Paths
    # ========================================
    BASE_DIR: Path = _PACKAGE_DIR
    PROJECT_ROOT: Path = _PROJECT_ROOT
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{_PROJECT_ROOT / 'outreach.db'}"
    )
    
    # Legacy file paths (for migration, will be deprecated)
    LEGACY_CONFIG_FILE: Path = _PACKAGE_DIR / "config.json"
    LEGACY_CONTACTS_FILE: Path = _PACKAGE_DIR / "contacts.csv"
    LEGACY_LOG_FILE: Path = _PACKAGE_DIR / "logs.csv"
    LEGACY_DRAFTS_DIR: Path = _PACKAGE_DIR / "drafts"
    
    # ========================================
    # Authentication
    # ========================================
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # ========================================
    # API Keys
    # ========================================
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    API_KEY: str | None = os.getenv("API_KEY")  # Optional legacy API key
    
    # ========================================
    # Email Providers
    # ========================================
    # Gmail OAuth
    GMAIL_CREDENTIALS_FILE: Path = Path(
        os.getenv("CREDENTIALS_FILE", str(_PACKAGE_DIR / "credentials.json"))
    )
    GMAIL_TOKEN_FILE: Path = Path(
        os.getenv("TOKEN_FILE", str(_PACKAGE_DIR / "token.json"))
    )
    
    # SMTP (alternative to Gmail)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    # ========================================
    # Server Configuration
    # ========================================
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "5000"))
    
    # CORS
    ALLOWED_ORIGINS: list[str] = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:8080,http://127.0.0.1:8080"
    ).split(",")
    
    # Rate Limiting
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "30"))
    
    # ========================================
    # OpenAI Configuration
    # ========================================
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # ========================================
    # Email Settings
    # ========================================
    MAX_EMAILS_PER_REQUEST: int = int(os.getenv("MAX_EMAILS_PER_REQUEST", "50"))
    EMAIL_DELAY_MIN_SECONDS: int = int(os.getenv("EMAIL_DELAY_MIN_SECONDS", "15"))
    EMAIL_DELAY_MAX_SECONDS: int = int(os.getenv("EMAIL_DELAY_MAX_SECONDS", "45"))
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production mode."""
        return not cls.FLASK_DEBUG and cls.SECRET_KEY != "dev-secret-key-change-in-production"
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is not set")
        
        if cls.is_production():
            if cls.SECRET_KEY == "dev-secret-key-change-in-production":
                errors.append("SECRET_KEY must be changed for production")
        
        return errors


# Create singleton instance
config = Config()
