"""
Voyager Configuration
Loads environment variables and application settings
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration settings"""
    
    # OpenAI Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # Application Settings
    APP_NAME = "Voyager"
    APP_VERSION = "0.1.0"
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    
    # Agent Settings
    AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "120"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    
    @classmethod
    def validate(cls):
        """Check if required settings exist"""
        if not cls.OPENAI_API_KEY:
            raise ValueError(" OPENAI_API_KEY not found! Add it to .env file")
        
        print(f"   Configuration loaded successfully")
        print(f"   Model: {cls.OPENAI_MODEL}")
        print(f"   Temperature: {cls.OPENAI_TEMPERATURE}")
        return True


# Validate configuration when this file is imported
Config.validate()

