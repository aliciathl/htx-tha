import threading, queue, time
from .imageProcessing import process_image_task
from ..models.database import SessionLocal
from ..models.imageModel import Image
from ..utils.logging import logger

_JOB_QUEUE = queue.Queue()
_WORKER_STARTED = False

def start_worker(app):
    global _WORKER_STARTED
    if _WORKER_STARTED: return
    _WORKER_STARTED = True

    def loop():
        logger.info("Worker started")
        while True:
            try:
                job = _JOB_QUEUE.get()
                if job is None: break
                image_id, stored_path, original_name = job.values()
                thumb_dir = app.config["THUMBNAIL_DIR"]
                upload_dir = app.config["UPLOAD_DIR"]
                logger.info(f"Processing image {image_id}")
                try:
                    result = process_image_task(stored_path, original_name, upload_dir, thumb_dir)
                    with SessionLocal() as db:
                        img = db.query(Image).filter(Image.id == image_id).first()
                        if img:
                            img.thumbnails = result["thumbnails"]
                            img.image_metadata = result["metadata"]
                            img.caption = result["caption"]
                            img.processed_at = result["processed_at"]
                            img.status = "success"
                            db.add(img)
                            db.commit()
                            logger.info(f"Job success {image_id}")
                except Exception as e:
                    logger.exception(f"Job failed {image_id}: {e}")
                    with SessionLocal() as db:
                        img = db.query(Image).filter(Image.id==image_id).first()
                        if img:
                            img.status = "failed"
                            db.add(img)
                            db.commit()
                finally:
                    _JOB_QUEUE.task_done()
            except Exception as e:
                logger.exception(f"Worker loop error: {e}")
                time.sleep(1)

    threading.Thread(target=loop, daemon=True, name="Worker").start()

def enqueue_image_job(image_id, stored_path, original_name):
    _JOB_QUEUE.put({"image_id": image_id, "stored_path": stored_path, "original_name": original_name})
