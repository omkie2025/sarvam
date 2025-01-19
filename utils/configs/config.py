import logging
import os

# Sarvam API subscription key
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "6200f2f5-a94c-4537-a98c-075ae49935e4")
if not SARVAM_API_KEY:
    logging.error("SARVAM_API_KEY is not set in environment variables.")
    raise ValueError("SARVAM_API_KEY is required but not set in environment variables.")

# API endpoint
SARVAM_API_URL = "https://api.sarvam.ai/speech-to-text"