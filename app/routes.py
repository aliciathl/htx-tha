import os
from datetime import datetime, timezone
from flask import Blueprint, current_app, request, jsonify, send_file, url_for
from sqlalchemy import func as sa_func
from werkzeug.utils import secure_filename
from .utils.logging import logger
from .models.database import SessionLocal
from .models.imageModel import Image
from .services.worker import enqueue_image_job

routes_bp = Blueprint("routes_bp", __name__)

ALLOWED_EXT = {"jpg", "jpeg", "png"}

def error_response(msg, code=400):
    return jsonify({"status": "error", "data": None, "error": msg}), code

def build_thumbnail_urls(image_id):
    return {
        "small": url_for("routes_bp.get_thumbnail", image_id=image_id, size="small", _external=True),
        "medium": url_for("routes_bp.get_thumbnail", image_id=image_id, size="medium", _external=True)
    }

@routes_bp.route("/api/images", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return error_response("No file part")
    file = request.files["file"]
    if file.filename == "":
        return error_response("No file selected")
    if file.filename.rsplit(".", 1)[-1].lower() not in ALLOWED_EXT:
        return error_response("Unsupported file type")

    db = SessionLocal()
    try:
        upload_dir = current_app.config["UPLOAD_DIR"]
        os.makedirs(upload_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        stored_filename = f"{timestamp}_{secure_filename(file.filename)}"
        stored_path = os.path.join(upload_dir, stored_filename)
        file.save(stored_path)

        img = Image(original_name=file.filename, stored_path=stored_path)
        db.add(img)
        db.commit()
        db.refresh(img)

        enqueue_image_job(img.id, stored_path, file.filename)

        return jsonify({
            "status": "success",
            "data": {
                "image_id": img.id,
                "original_name": file.filename,
                "status": "processing"
            },
            "error": None
        }), 202
    except Exception as e:
        db.rollback()
        logger.exception(e)
        return error_response(str(e), 500)
    finally:
        db.close()

@routes_bp.route("/api/images", methods=["GET"])
def list_images():
    db = SessionLocal()
    try:
        imgs = db.query(Image).all()
        data = []
        for i in imgs:
            thumbnails = build_thumbnail_urls(i.id) if i.thumbnails and isinstance(i.thumbnails, dict) else {}
            data.append({
                "image_id": i.id,
                "original_name": i.original_name,
                "processed_at": i.processed_at.isoformat() if i.processed_at else None,
                "status": i.status,
                "thumbnails": thumbnails
            })
        return jsonify({"status": "success", "data": data, "error": None})
    finally:
        db.close()

@routes_bp.route("/api/images/<int:image_id>/thumbnails/<size>", methods=["GET"])
def get_thumbnail(image_id, size):
    if size not in {"small", "medium"}:
        return error_response("Invalid size")
    db = SessionLocal()
    try:
        img = db.query(Image).filter(Image.id == image_id).first()
        if not img or not img.thumbnails or size not in img.thumbnails:
            return error_response("Thumbnail not found", 404)
        path = img.thumbnails[size]
        if not os.path.exists(path):
            return error_response("File missing", 404)
        return send_file(path)
    finally:
        db.close()

@routes_bp.route("/api/images/<int:image_id>", methods=["GET"])
def get_image_details(image_id):
    db = SessionLocal()
    try:
        img = db.query(Image).filter(Image.id == image_id).first()
        if not img:
            return error_response("Image not found", 404)
        thumbnails = build_thumbnail_urls(img.id) if img.thumbnails else {}
        return jsonify({
            "status": "success",
            "data": {
                "image_id": img.id,
                "original_name": img.original_name,
                "status": img.status,
                "created_at": img.created_at.isoformat() if img.created_at else None,
                "processed_at": img.processed_at.isoformat() if img.processed_at else None,
                "metadata": img.image_metadata,
                "thumbnails": thumbnails,
                "caption": img.caption
            },
            "error": None
        })
    finally:
        db.close()

@routes_bp.route("/api/stats", methods=["GET"])
def get_stats():
    db = SessionLocal()
    try:
        total_images = db.query(sa_func.count(Image.id)).scalar()
        successful = db.query(Image).filter(Image.status == "success").count()
        failed = db.query(Image).filter(Image.status == "failed").count()
        processing = total_images - successful - failed
        success_rate = (successful / total_images * 100) if total_images else 0

        diffs = [
            (i.processed_at - i.created_at).total_seconds()
            for i in db.query(Image).filter(Image.processed_at.isnot(None)).all()
            if i.created_at and i.processed_at
        ]
        avg_time = round(sum(diffs) / len(diffs), 2) if diffs else 0

        return jsonify({
            "status": "success",
            "data": {
                "total_images": total_images,
                "successful": successful,
                "failed": failed,
                "processing": processing,
                "success_rate": round(success_rate, 2),
                "average_processing_time_seconds": avg_time
            },
            "error": None
        })
    finally:
        db.close()

@routes_bp.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "success",
        "data": {"message": "Image Processing API is running"},
        "error": None
    })
