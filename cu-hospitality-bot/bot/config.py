import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
UNIT_HEAD_IDS = [int(id_str.strip()) for id_str in os.getenv("UNIT_HEAD_IDS", "").split(",") if id_str.strip()]

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

UNIT_NAME = os.getenv("UNIT_NAME", "Hospitality Unit")
CHAPEL_NAME = os.getenv("CHAPEL_NAME", "Covenant University Chapel")
TIMEZONE = os.getenv("TIMEZONE", "Africa/Lagos")
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure logging
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(LOG_LEVEL)

    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] — %(message)s"
    )

    # Rotating file handler (5MB max, 3 backups)
    file_handler = RotatingFileHandler(
        "logs/bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Silence verbose loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)

    return logger
