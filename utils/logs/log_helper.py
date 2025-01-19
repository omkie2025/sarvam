import time
import logging
from logging.handlers import RotatingFileHandler

# General logging configuration (app logs)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("utils/logs/app.log"),  # Log general info to app.log
        logging.StreamHandler()                     # Log general info to console
    ]
)

# Separate error logger
error_logger = logging.getLogger("error")
error_handler = RotatingFileHandler("utils/logs/error.log", maxBytes=5*1024*1024, backupCount=5)  # Rotate error logs
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
error_handler.setFormatter(error_formatter)
error_logger.addHandler(error_handler)
error_logger.setLevel(logging.ERROR)

# Utility function for monitoring execution time
def log_execution_time(func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logging.info(f"Execution time for {func.__name__}: {duration:.2f} seconds")
            return result
        except Exception as e:
            # Log errors to the separate error log
            error_logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise
    return wrapper

