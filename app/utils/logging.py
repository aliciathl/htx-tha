from loguru import logger
import sys
import os

# Ensure logs folder exists
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add(
    os.path.join(LOG_DIR, "app.log"),
    rotation="1 MB",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}"
)
