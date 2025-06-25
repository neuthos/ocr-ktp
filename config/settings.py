import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLOUD_CREDENTIALS_PATH = os.getenv("GOOGLE_CLOUD_CREDENTIALS_PATH")
TEMP_DIR = os.getenv("TEMP_DIR", "temp/")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10485760))
ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png").split(",")

os.makedirs(TEMP_DIR, exist_ok=True)