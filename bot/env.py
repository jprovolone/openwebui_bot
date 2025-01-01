import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("dotenv not installed, skipping...")


WEBUI_URL = os.getenv("WEBUI_URL", "http://localhost:8080")
TOKEN = os.getenv("TOKEN", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
OPENWEBUI_API_KEY = os.getenv("OPENWEBUI_API_KEY", "")
