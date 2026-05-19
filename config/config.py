from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).parent.parent
    
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = DATA_DIR / "raw"
    PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
    ANNOTATED_DATA_DIR: Path = DATA_DIR / "annotated"
    FINAL_DATA_DIR: Path = DATA_DIR / "final"
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
