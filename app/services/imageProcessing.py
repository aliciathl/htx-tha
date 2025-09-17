import os
from datetime import datetime, timezone
from PIL import Image as PILImage, UnidentifiedImageError
import exifread
import requests
import base64
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
        ext = "jpg" if pil_img.format and pil_img.format.lower() in ("jpeg", "jpg") else "png"
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
        return {str(k): str(v) for k, v in tags.items()} if tags else None
    except Exception as e:
        logger.warning(f"EXIF extraction failed: {e}")
        return None


def get_caption_from_hf(path):
    """Generate image caption using HuggingFace API, fallback to local BLIP if available."""
    # --- API mode ---
    if HF_API_KEY:
        logger.info("Attempting to generate caption using HuggingFace API")

        # BLIP (preferred via API)
        try:
            with open(path, "rb") as f:
                img_bytes = f.read()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            response = requests.post(
                HF_API_URL,
                headers={
                    "Authorization": f"Bearer {HF_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={"inputs": img_b64},
                timeout=30
            )
            logger.info(f"BLIP JSON - Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"BLIP result: {result}")
                if isinstance(result, list) and result:
                    return result[0].get("generated_text") or result[0].get("caption")
                elif isinstance(result, dict):
                    return result.get("generated_text") or result.get("caption")
            else:
                logger.warning(f"BLIP failed: {response.status_code}, response: {response.text}")
        except Exception as e:
            logger.exception(f"BLIP JSON method failed: {e}")

        # Alternative API model (ViT-GPT2)
        try:
            alt_model = "nlpconnect/vit-gpt2-image-captioning"
            alt_url = f"https://api-inference.huggingface.co/models/{alt_model}"
            with open(path, "rb") as f:
                response = requests.post(
                    alt_url,
                    headers={"Authorization": f"Bearer {HF_API_KEY}"},
                    files={"file": f},
                    timeout=30
                )
            logger.info(f"Alternative model - Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Alternative result: {result}")
                if isinstance(result, list) and result:
                    return result[0].get("generated_text") or result[0].get("caption")
            else:
                logger.warning(f"Alternative model failed: {response.status_code}, response: {response.text}")
        except Exception as e:
            logger.exception(f"Alternative model failed: {e}")

    # --- Local fallback ---
    try:
        logger.info("Falling back to local BLIP model (transformers)")
        from transformers import BlipProcessor, BlipForConditionalGeneration
        import torch
        from PIL import Image

        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

        raw_image = Image.open(path).convert("RGB")
        inputs = processor(raw_image, return_tensors="pt", padding=True)  # ✅ padding added
        out = model.generate(**inputs, max_new_tokens=30)
        caption = processor.decode(out[0], skip_special_tokens=True)
        logger.info(f"Local BLIP caption generated: {caption}")
        return caption
    except Exception as e:
        logger.exception(f"Local BLIP failed: {e}")

    # --- Metadata fallback ---
    logger.error("All captioning methods failed, using metadata fallback")
    try:
        with PILImage.open(path) as img:
            return f"An image ({img.width}x{img.height}, {img.format or 'unknown format'})"
    except Exception:
        return "An uploaded image"


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
