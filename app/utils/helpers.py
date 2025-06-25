import os
import uuid
from PIL import Image
from config.settings import ALLOWED_EXTENSIONS, MAX_FILE_SIZE

def is_allowed_file(filename: str) -> bool:
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_size(file_size: int) -> bool:
    return file_size <= MAX_FILE_SIZE

def generate_unique_filename(original_filename: str) -> str:
    ext = original_filename.rsplit('.', 1)[1].lower()
    unique_id = str(uuid.uuid4())
    return f"{unique_id}.{ext}"

def validate_image(file_path: str) -> bool:
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False

def cleanup_temp_file(file_path: str) -> None:
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass