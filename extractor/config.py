import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    database_path: str = os.getenv('DATABASE_PATH', 'data/forum_data.db')
    gemini_bridge_url: str = os.getenv('GEMINI_BRIDGE_URL', 'http://127.0.0.1:18205/v1')
    model: str = os.getenv('GEMINI_BRIDGE_MODEL', 'gemini-3.1-flash-lite')
    batch_size: int = int(os.getenv('BATCH_SIZE', '20'))
    rate_limit_delay: float = float(os.getenv('RATE_LIMIT_DELAY', '3.1'))
    max_retries: int = int(os.getenv('MAX_RETRIES', '3'))
    temperature: float = float(os.getenv('TEMPERATURE', '0.1'))
    sanitization_rules_file: Optional[str] = os.getenv('SANITIZATION_RULES_FILE')

config = Config()
