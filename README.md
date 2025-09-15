
# Image Processing Pipeline API

This is a Flask-based REST API that automatically processes uploaded images, generates thumbnails, extracts metadata, and provides AI-generated captions.

## Features

- Upload JPG/PNG images via REST API
- Generate small (128x128) and medium (512x512) thumbnails
- Extract metadata (dimensions, format, size, datetime, EXIF data)
- AI-powered image captioning using HuggingFace BLIP model
- Non-blocking background processing with job queue
- SQLite database storage
- Error handling and logging

## Quick Start

### 1. Setup
```bash
git clone <repo_url>
cd htx_tha/app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python init_db.py
```

### 3. Set Environment Variables
```bash
export HF_API_KEY=your_huggingface_api_key  # This is for the AI captioning
```

### 4. Run the Server
```bash
python routes.py
```
API available at: `http://localhost:5000`

### 5. Test the API
```bash
cp /path/to/test/image.jpg test_image.jpg
python test_api.py
```

## API Endpoints

### Upload Image
```bash
POST /api/images
curl -F "file=@photo.jpg" http://localhost:5000/api/images
```
**Response (202 Accepted):**
```json
{
  "status": "success",
  "data": {
    "image_id": 1,
    "original_name": "photo.jpg",
    "status": "processing",
    "message": "Image uploaded successfully and processing started"
  },
  "error": null
}
```

### List All Images
```bash
GET /api/images
curl http://localhost:5000/api/images
```

### Get Image Details
```bash
GET /api/images/{id}
curl http://localhost:5000/api/images/1
```
**Response:**
```json
{
  "status": "success",
  "data": {
    "image_id": 1,
    "original_name": "photo.jpg",
    "status": "success",
    "metadata": {
      "width": 1920,
      "height": 1080,
      "format": "jpg",
      "size_bytes": 2048576,
      "exif": {"Camera": "Canon"}
    },
    "thumbnails": {
      "small": "/api/images/1/thumbnails/small",
      "medium": "/api/images/1/thumbnails/medium"
    },
    "caption": "A beautiful landscape with mountains and trees"
  },
  "error": null
}
```

### Get Thumbnails
```bash
GET /api/images/{id}/thumbnails/{size}
curl http://localhost:5000/api/images/1/thumbnails/small --output thumb.jpg
```

### Processing Statistics
```bash
GET /api/stats
curl http://localhost:5000/api/stats
```
**Response:**
```json
{
  "status": "success",
  "data": {
    "total_images": 10,
    "successful": 8,
    "failed": 1,
    "processing": 1,
    "success_rate": 80.0,
    "average_processing_time_seconds": 3.45
  },
  "error": null
}
```

## Image Processing Flow

1. **Upload**: Image saved with unique filename, database record created
2. **Queue**: Processing job added to background queue (non-blocking)
3. **Process**: Generate thumbnails, extract metadata/EXIF, AI captioning
4. **Store**: Results saved to database, status updated to "success"
5. **Retrieve**: API endpoints serve processed data and thumbnails

## Dependencies

Listed under requirements.txt

## Error Handling

The API handles:
- Invalid file types (only JPG/PNG supported)
- Corrupted uploads and processing failures
- Database connection issues
- Missing resources

All errors return consistent JSON format:
```json
{
  "status": "error",
  "data": null,
  "error": "Error message description"
}
```

## Configuration

### Environment Variables
- `HF_API_KEY`: HuggingFace API key for image captioning
- `FLASK_DEBUG=1`: Enable debug mode

### File Storage
- Original images: `app/statics/imageOG/`
- Thumbnails: `app/statics/thumbnails/`
- Database: `app/image_data.db`
- Logs: `app.log`

## Testing

### Manual Testing
```bash
# Place test image in app directory
cp /path/to/image.jpg test_image.jpg

# Run test script
python test_api.py
```

### API Testing
Use the curl commands shown in the API endpoints section above.

## Troubleshooting

**Common Issues:**
- **"No file part"**: Use form field name "file" with multipart/form-data
- **"Unsupported file type"**: Only .jpg, .jpeg, .png files accepted
- **"Image not found"**: Check image ID exists via list endpoint
- **AI captioning not working**: Set HF_API_KEY environment variable

**Debug Mode:**
```bash
export FLASK_DEBUG=1
python routes.py
```

Check `app.log` for detailed processing information and errors.

## Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 routes:app
```

### Docker 
```bash
docker build -t image-processing-api .
docker run -p 5000:5000 image-processing-api
```

## Resources

- [HuggingFace BLIP Model](https://huggingface.co/Salesforce/blip-image-captioning-large)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [RESTful API Design](https://restfulapi.net/)