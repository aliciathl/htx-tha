from loguru import logger
import sys

logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add("app.log", rotation="1 MB", retention="7 days", level="INFO",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}")
