import os
from flask import Flask
from .routes import routes_bp
from .models.database import Base, engine
from .services.worker import start_worker
from .utils.logging import logger

def create_app():
    # Create Flask app
    app = Flask(__name__)

    # --- Configuration ---
    app.config["UPLOAD_DIR"] = os.path.join(os.path.dirname(__file__), "statics", "imageOG")
    app.config["THUMBNAIL_DIR"] = os.path.join(os.path.dirname(__file__), "statics", "thumbnails")
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB limit

    # Ensure directories exist
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    os.makedirs(app.config["THUMBNAIL_DIR"], exist_ok=True)

    # --- Database setup ---
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

    # --- Register routes blueprint ---
    app.register_blueprint(routes_bp)

    # --- Start background worker ---
    start_worker(app)

    logger.info("Flask app created successfully")
    return app
