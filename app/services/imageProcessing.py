import os
from datetime import datetime, timezone
from PIL import Image as PILImage, UnidentifiedImageError
import exifread
import requests
from ..utils.logging import logger
from werkzeug.utils import secure_filename

THUMB_SIZES = {"small": (128, 128), "medium": (512, 512)}
HF_MODEL = "Salesforce/blip-image-captioning-large"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
HF_API_KEY = os.getenv("HF_API_KEY")

def safe_open_image(path):
    try:
        return PILImage.open(path)
    except UnidentifiedImageError:
        logger.error(f"Unidentified image: {path}")
        raise
    except Exception as e:
        logger.exception(f"Error opening image: {e}")
        raise

def generate_thumbnails(pil_img, original_name, timestamp, thumbnail_dir):
    thumbnails = {}
    for size, dims in THUMB_SIZES.items():
        img_copy = pil_img.copy()
        img_copy.thumbnail(dims)
        ext = "jpg" if pil_img.format and pil_img.format.lower() in ("jpeg","jpg") else "png"
        filename = f"{timestamp}_{size}_{secure_filename(original_name)}"
        if not filename.lower().endswith(f".{ext}"):
            filename += f".{ext}"
        path = os.path.join(thumbnail_dir, filename)
        if img_copy.mode in ("RGBA", "P"):
            img_copy = img_copy.convert("RGB")
        img_copy.save(path)
        thumbnails[size] = path
        logger.info(f"Generated thumbnail {size}: {path}")
    return thumbnails

def extract_exif(path):
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, details=False)
        return {str(k): str(v) for k,v in tags.items()} if tags else None
    except Exception as e:
        logger.warning(f"EXIF extraction failed: {e}")
        return None

def get_caption_from_hf(path):
    if not HF_API_KEY:
        logger.warning("HF_API_KEY not set; skipping caption")
        return None
    try:
        with open(path, "rb") as f:
            files = {"file": f}
            headers = {"Authorization": f"Bearer {HF_API_KEY}"}
            resp = requests.post(HF_API_URL, headers=headers, files=files, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            if isinstance(result, list) and "generated_text" in result[0]:
                return result[0]["generated_text"]
            if isinstance(result, dict) and "generated_text" in result:
                return result["generated_text"]
        logger.warning(f"HF API failed: {resp.status_code}")
    except Exception as e:
        logger.exception(f"Caption generation error: {e}")
    return None

def process_image_task(stored_path, original_name, upload_dir, thumbnail_dir):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    pil_img = safe_open_image(stored_path)
    metadata = {
        "width": pil_img.width,
        "height": pil_img.height,
        "format": pil_img.format.lower() if pil_img.format else None,
        "size_bytes": os.path.getsize(stored_path),
        "file_datetime": datetime.fromtimestamp(os.path.getmtime(stored_path), timezone.utc).isoformat(),
        "processed_at": datetime.now(timezone.utc).isoformat()
    }
    exif = extract_exif(stored_path)
    if exif:
        metadata["exif"] = exif
    thumbnails = generate_thumbnails(pil_img, original_name, timestamp, thumbnail_dir)
    caption = get_caption_from_hf(stored_path)
    return {
        "stored_path": stored_path,
        "processed_at": datetime.now(timezone.utc),
        "metadata": metadata,
        "thumbnails": thumbnails,
        "caption": caption
    }
