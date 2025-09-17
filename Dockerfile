FROM python:3.9-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy the entire app folder into container
COPY app/ ./app/

# Create necessary directories for images and logs
RUN mkdir -p app/statics/imageOG app/statics/thumbnails app/logs

# Expose port 5000 for the Flask app
EXPOSE 5000

# Start Gunicorn pointing to your Flask app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app.main:app"]
