from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from .database import Base

class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    original_name = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    image_metadata = Column(JSON, nullable=True)
    thumbnails = Column(JSON, nullable=True)
    caption = Column(String, nullable=True)
    status = Column(String, default="processing", index=True)
