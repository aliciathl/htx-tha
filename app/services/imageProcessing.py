import os
from datetime import datetime, timezone
from PIL import Image as PILImage, UnidentifiedImageError
import exifread
import requests
import base64
import json
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
    """Updated HuggingFace API call with improved error handling and multiple formats"""
    if not HF_API_KEY:
        logger.warning("HF_API_KEY not set; skipping caption")
        return None
    
    logger.info("Attempting to generate caption using HuggingFace API")
    
    # Method 1: Try binary data upload (new serverless inference format)
    try:
        headers = {
            "Authorization": f"Bearer {HF_API_KEY}",
        }
        
        with open(path, "rb") as f:
            response = requests.post(HF_API_URL, headers=headers, data=f.read(), timeout=30)
        
        logger.info(f"Binary upload - Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Binary upload result: {result}")
            
            # Handle different response formats
            if isinstance(result, list) and len(result) > 0:
                if "generated_text" in result[0]:
                    return result[0]["generated_text"]
                elif "caption" in result[0]:
                    return result[0]["caption"]
                elif "label" in result[0]:
                    return result[0]["label"]
            elif isinstance(result, dict):
                if "generated_text" in result:
                    return result["generated_text"]
                elif "caption" in result:
                    return result["caption"]
        
        elif response.status_code == 503:
            logger.warning("Model is loading, trying alternative method...")
        elif response.status_code == 429:
            logger.warning("Rate limit exceeded, trying alternative method...")
        else:
            logger.warning(f"Binary upload failed: {response.status_code}, response: {response.text}")
        
    except Exception as e:
        logger.warning(f"Binary upload method failed: {e}")
    
    # Method 2: Try base64 JSON format (legacy format)
    try:
        with open(path, "rb") as f:
            img_bytes = f.read()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        
        payload = json.dumps({"inputs": img_b64})
        headers = {
            "Authorization": f"Bearer {HF_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(HF_API_URL, headers=headers, data=payload, timeout=30)
        logger.info(f"Base64 JSON - Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Base64 JSON result: {result}")
            
            if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
                return result[0]["generated_text"]
            elif isinstance(result, dict) and "generated_text" in result:
                return result["generated_text"]
        else:
            logger.warning(f"Base64 JSON failed: {response.status_code}, response: {response.text}")
    
    except Exception as e:
        logger.warning(f"Base64 JSON method failed: {e}")
    
    # Method 3: Try alternative model
    try:
        alt_model = "nlpconnect/vit-gpt2-image-captioning"
        alt_url = f"https://api-inference.huggingface.co/models/{alt_model}"
        
        headers = {
            "Authorization": f"Bearer {HF_API_KEY}",
        }
        
        with open(path, "rb") as f:
            response = requests.post(alt_url, headers=headers, data=f.read(), timeout=30)
        
        logger.info(f"Alternative model - Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Alternative model result: {result}")
            
            if isinstance(result, list) and len(result) > 0:
                if "generated_text" in result[0]:
                    return result[0]["generated_text"]
                elif "caption" in result[0]:
                    return result[0]["caption"]
        else:
            logger.warning(f"Alternative model failed: {response.status_code}")
    
    except Exception as e:
        logger.warning(f"Alternative model failed: {e}")
    
    # If all methods fail, return a basic fallback
    logger.error("All HuggingFace API methods failed, using fallback caption")
    try:
        with PILImage.open(path) as img:
            return f"An image ({img.width}x{img.height}, {img.format or 'unknown format'})"
    except:
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