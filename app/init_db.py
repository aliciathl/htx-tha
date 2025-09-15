import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.database import Base, engine
from models.imageModel import Image

if __name__ == "__main__":
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")