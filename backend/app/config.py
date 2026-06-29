import os
from pathlib import Path
from typing import Dict, Any, List
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # API Keys
    GROQ_API_KEY: str = Field(default="mock_groq_key")
    GEMINI_API_KEY: str = Field(default="mock_gemini_key")
    NEWS_API_KEY: str = Field(default="mock_news_key")
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_API_BASE: str = Field(default="")
    
    # Security & Governance
    TEE_ENCRYPTION_KEY: str = Field(default="")
    DATABASE_URL: str = Field(default="sqlite:///./nexusai.db")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CHAOS_MONKEY_ENABLED: bool = Field(default=False)
    
    # Server configuration
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")
    FRONTEND_URL: str = Field(default="http://localhost:5173")
    
    # Mock fallback control — set to False in production to surface API errors
    ALLOW_MOCK_FALLBACK: bool = Field(default=False)
    
    # Email notifications settings
    EMAIL_PROVIDER: str = Field(default="mock")
    EMAIL_DIGEST_MODE: bool = Field(default=True)
    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: str = Field(default="")
    SMTP_PASSWORD: str = Field(default="")
    NOTIFY_EMAIL: str = Field(default="")
    RESEND_API_KEY: str = Field(default="")
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR.parent, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure TEE Encryption key exists and is persistent
if not settings.TEE_ENCRYPTION_KEY:
    tee_key_file = BASE_DIR / "app" / "mock_data" / ".tee_key"
    if tee_key_file.exists():
        try:
            settings.TEE_ENCRYPTION_KEY = tee_key_file.read_text(encoding="utf-8").strip()
            print(f"Loaded persistent TEE key from {tee_key_file}")
        except Exception as e:
            print(f"Error reading persistent TEE key: {e}")
    
    if not settings.TEE_ENCRYPTION_KEY:
        from cryptography.fernet import Fernet
        generated_key = Fernet.generate_key().decode()
        settings.TEE_ENCRYPTION_KEY = generated_key
        try:
            tee_key_file.parent.mkdir(parents=True, exist_ok=True)
            tee_key_file.write_text(generated_key, encoding="utf-8")
            print(f"Generated new persistent TEE key and saved to {tee_key_file}")
        except Exception as e:
            print(f"Failed to save generated TEE key: {e}")

# Business Configurations Path
BUSINESS_CONFIG_DIR = BASE_DIR / "app" / "business_config"

def load_yaml_config(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def get_business_config(domain: str = "hr_saas") -> Dict[str, Any]:
    """Load business YAML configs for a specific domain."""
    icp_path = BUSINESS_CONFIG_DIR / "icp_profiles" / f"{domain}_icp.yaml"
    personas_path = BUSINESS_CONFIG_DIR / "personas" / f"{domain}_personas.yaml"
    triggers_path = BUSINESS_CONFIG_DIR / "triggers" / f"{domain}_triggers.yaml"
    guardrails_path = BUSINESS_CONFIG_DIR / "guardrails" / "safety_policies.yaml"
    
    return {
        "icp": load_yaml_config(icp_path),
        "personas": load_yaml_config(personas_path),
        "triggers": load_yaml_config(triggers_path),
        "guardrails": load_yaml_config(guardrails_path)
    }
