import os
from datetime import datetime, timezone
from flask import current_app as app, request, jsonify, send_file
from sqlalchemy import func as sa_func
from werkzeug.utils import secure_filename
from .utils.logging import logger
from .models.database import SessionLocal
from .models.imageModel import Image
from .services.worker import enqueue_image_job

ALLOWED_EXT = {"jpg","jpeg","png"}

def error_response(msg, code=400):
    return jsonify({"status":"error","data":None,"error":msg}), code

@app.route("/api/images", methods=["POST"])
def upload_image():
    if "file" not in request.files: return error_response("No file part")
    file = request.files["file"]
    if file.filename == "": return error_response("No file selected")
    if file.filename.rsplit(".",1)[-1].lower() not in ALLOWED_EXT:
        return error_response("Unsupported file type")
    db = SessionLocal()
    try:
        upload_dir = app.config["UPLOAD_DIR"]
        os.makedirs(upload_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        stored_filename = f"{timestamp}_{secure_filename(file.filename)}"
        stored_path = os.path.join(upload_dir, stored_filename)
        file.save(stored_path)

        img = Image(original_name=file.filename, stored_path=stored_path)
        db.add(img); db.commit(); db.refresh(img)

        enqueue_image_job(img.id, stored_path, file.filename)

        return jsonify({"status":"success","data":{"image_id":img.id,"original_name":file.filename,"stored_path":stored_path,"status":"processing"},"error":None}), 202
    except Exception as e:
        db.rollback(); logger.exception(e); return error_response(str(e),500)
    finally:
        db.close()

@app.route("/api/images", methods=["GET"])
def list_images():
    db = SessionLocal()
    try:
        imgs = db.query(Image).all()
        data = []
        for i in imgs:
            data.append({
                "image_id": i.id,
                "original_name": i.original_name,
                "processed_at": i.processed_at.isoformat() if i.processed_at else None,
                "status": i.status,
                "thumbnails": i.thumbnails or {}
            })
        return jsonify({"status":"success","data":data,"error":None})
    finally: db.close()

@app.route("/api/images/<int:image_id>/thumbnails/<size>", methods=["GET"])
def get_thumbnail(image_id,size):
    if size not in {"small","medium"}: return error_response("Invalid size")
    db = SessionLocal()
    try:
        img = db.query(Image).filter(Image.id==image_id).first()
        if not img or not img.thumbnails or size not in img.thumbnails: return error_response("Thumbnail not found",404)
        path = img.thumbnails[size]
        if not os.path.exists(path): return error_response("File missing",404)
        return send_file(path)
    finally: db.close()

@app.route("/api/stats", methods=["GET"])
def get_stats():
    db = SessionLocal()
    try:
        total = db.query(sa_func.count(Image.id)).scalar()
        success = db.query(Image).filter(Image.status=="success").count()
        failed = db.query(Image).filter(Image.status=="failed").count()
        diffs = [(i.processed_at-i.created_at).total_seconds() for i in db.query(Image).filter(Image.processed_at.isnot(None)).all() if i.created_at and i.processed_at]
        avg_time = sum(diffs)/len(diffs) if diffs else None
        return jsonify({"status":"success","data":{"total":total,"success":success,"failed":failed,"average_processing_time_seconds":avg_time},"error":None})
    finally: db.close()

@app.route("/api/images/<int:image_id>", methods=["GET"])
def get_image_details(image_id):
    db = SessionLocal()
    try:
        img = db.query(Image).filter(Image.id==image_id).first()
        if not img:
            return error_response("Image not found",404)
        return jsonify({
            "status": "success",
            "data": {
                "image_id": img.id,
                "original_name": img.original_name,
                "status": img.status,
                "created_at": img.created_at.isoformat() if img.created_at else None,
                "processed_at": img.processed_at.isoformat() if img.processed_at else None,
                "metadata": img.image_metadata,
                "thumbnails": img.thumbnails,
                "caption": img.caption
            },
            "error": None
        })
    finally:
        db.close()

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "success",
        "data": {"message": "Image Processing API is running"},
        "error": None
    })