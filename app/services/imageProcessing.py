import os
from datetime import datetime, timezone
from PIL import Image as PILImage, UnidentifiedImageError
import exifread
from ..utils.logging import logger
from werkzeug.utils import secure_filename
from transformers import BlipProcessor, BlipForConditionalGeneration
import torch

THUMB_SIZES = {"small": (128, 128), "medium": (512, 512)}


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


def generate_local_caption(path, max_tokens=30):
    """Generate caption locally using BLIP via transformers"""
    try:
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device)
        model.eval()

        raw_image = PILImage.open(path).convert("RGB")

        with torch.no_grad():
            # Fix padding issue by adding padding=True
            inputs = processor(raw_image, return_tensors="pt", padding=True).to(device)
            out = model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False, num_beams=1)
            caption = processor.decode(out[0], skip_special_tokens=True)

        # Clean up the caption
        if caption.lower().startswith("a picture of "):
            caption = caption[13:]
        elif caption.lower().startswith("an image of "):
            caption = caption[12:]

        return caption.strip()

    except Exception as e:
        logger.exception(f"Local BLIP caption generation failed: {e}")
        # Fallback to metadata-based caption
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
    caption = generate_local_caption(stored_path)

    return {
        "stored_path": stored_path,
        "processed_at": datetime.now(timezone.utc),
        "metadata": metadata,
        "thumbnails": thumbnails,
        "caption": caption
    }
