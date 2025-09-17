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
git clone <the_url_of_this_repo>
cd htx_tha
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
in .env: HF_API_KEY=your_huggingface_api_key
```

### 4. Run the Server
```bash
python main.py
```
API available at: `http://localhost:5000`

### 5. Test the API
```bash
cp /path/to/test/image.jpg test_image.jpg
pytest -q tests/test_api.py
```

## API Endpoints

### 1. Check API Status
```http
GET http://localhost:5000/
```
**Response:**
```json
{
  "data": {
    "message": "Image Processing API is running"
  },
  "error": null,
  "status": "success"
}
```

### 2. Upload Image
```http
POST http://localhost:5000/api/images
Content-Type: multipart/form-data

file: [select image file - test_image.jpg]
```

**Response:**
```json
{
  "data": {
    "image_id": 1,
    "original_name": "test_image.jpg",
    "status": "processing"
  },
  "error": null,
  "status": "success"
}
```

### 3. List All Images
```http
GET http://localhost:5000/api/images
```

**Response:**
```json
{
  "data": [
    {
      "image_id": 1,
      "original_name": "test_image.jpg",
      "processed_at": "2025-09-17T12:32:59.530218",
      "status": "success",
      "thumbnails": {
        "medium": "http://localhost:5000/api/images/1/thumbnails/medium",
        "small": "http://localhost:5000/api/images/1/thumbnails/small"
      }
    }
  ],
  "error": null,
  "status": "success"
}
```

### 4. Get Image Details
```http
GET http://localhost:5000/api/images/1
```

**Response:**
```json
{
  "data": {
    "caption": null,
    "created_at": "2025-09-17T12:32:58",
    "image_id": 1,
    "metadata": {
      "file_datetime": "2025-09-17T12:32:58.952950+00:00",
      "format": "jpeg",
      "height": 190,
      "processed_at": "2025-09-17T12:32:59.035575+00:00",
      "size_bytes": 5883,
      "width": 265
    },
    "original_name": "test_image.jpg",
    "processed_at": "2025-09-17T12:32:59.530218",
    "status": "success",
    "thumbnails": {
      "medium": "http://localhost:5000/api/images/1/thumbnails/medium",
      "small": "http://localhost:5000/api/images/1/thumbnails/small"
    }
  },
  "error": null,
  "status": "success"
}
```

### 5. Get Thumbnails
```http
GET http://localhost:5000/api/images/1/thumbnails/small
GET http://localhost:5000/api/images/1/thumbnails/medium
```

**Response:** Binary image data (JPEG format)

### 6. Processing Statistics
```http
GET http://localhost:5000/api/stats
```

**Response:**
```json
{
  "data": {
    "average_processing_time_seconds": 0.98,
    "failed": 0,
    "processing": 0,
    "success_rate": 100.0,
    "successful": 3,
    "total_images": 3
  },
  "error": null,
  "status": "success"
}
```

## Testing with Postman

### Postman Collection Setup

1. **Create New Collection**: "Image Processing API"
2. **Set Base URL**: `http://localhost:5000`
3. **Configure requests as shown below**

### Request Examples in Postman

#### 1. API Status Check
- **Method**: GET
- **URL**: `{{base_url}}/`
- **Expected Status**: 200 OK

#### 2. Upload Image
- **Method**: POST
- **URL**: `{{base_url}}/api/images`
- **Body**: 
  - Type: `form-data`
  - Key: `file` (File type)
  - Value: Select your test image (e.g., `test_image.jpg`)
- **Expected Status**: 202 ACCEPTED

#### 3. List Images
- **Method**: GET
- **URL**: `{{base_url}}/api/images`
- **Expected Status**: 200 OK

#### 4. Get Specific Image
- **Method**: GET
- **URL**: `{{base_url}}/api/images/1`
- **Expected Status**: 200 OK

#### 5. Get Small Thumbnail
- **Method**: GET
- **URL**: `{{base_url}}/api/images/1/thumbnails/small`
- **Expected Status**: 200 OK
- **Response**: Binary image data

#### 6. Get Statistics
- **Method**: GET
- **URL**: `{{base_url}}/api/stats`
- **Expected Status**: 200 OK

### Postman Environment Variables
```json
{
  "base_url": "http://localhost:5000"
}
```

### Testing Workflow

1. **Start the API server**
2. **Test API status** to ensure server is running
3. **Upload an image** using form-data
4. **Wait for processing** (usually < 1 second)
5. **List all images** to see processed results
6. **Get image details** to see full metadata
7. **Download thumbnails** to verify image processing
8. **Check statistics** to monitor API performance

## Image Processing Flow

1. **Upload**: Image saved with unique filename, database record created
2. **Queue**: Processing job added to background queue (non-blocking)
3. **Process**: Generate thumbnails, extract metadata/EXIF, AI captioning
4. **Store**: Results saved to database, status updated to "success"
5. **Retrieve**: API endpoints serve processed data and thumbnails

## Dependencies

Listed under requirements.txt:

### Common HTTP Status Codes
- `200 OK`: Successful GET requests
- `202 ACCEPTED`: Successful image upload (processing started)
- `400 BAD REQUEST`: Invalid request (wrong file type, missing file)
- `404 NOT FOUND`: Image not found
- `500 INTERNAL SERVER ERROR`: Server processing error

## Configuration

### Environment Variables
- `HF_API_KEY`: HuggingFace API key for image captioning
- `FLASK_DEBUG=1`: Enable debug mode

## Manual Testing Scripts

### cURL Testing
```bash
# Check API status
curl http://localhost:5000/

# Upload image
curl -F "file=@test_image.jpg" http://localhost:5000/api/images

# List images
curl http://localhost:5000/api/images

# Get specific image
curl http://localhost:5000/api/images/1

# Download thumbnail
curl http://localhost:5000/api/images/1/thumbnails/small --output thumb_small.jpg

# Get statistics
curl http://localhost:5000/api/stats
```

### Python Testing Script
```bash
# Place test image in app directory
cp /path/to/image.jpg test_image.jpg

# Run test script
python test_api.py
```

### Pytest Testing
```bash
pytest -q tests/test_api.py
```

## Troubleshooting

### Common Issues

**"No file part"**
- Solution: Use form field name "file" with multipart/form-data
- In Postman: Body → form-data → Key: "file" (File type)

**"Unsupported file type"**
- Solution: Only .jpg, .jpeg, .png files accepted
- Check file extension and MIME type

**AI captioning not working**
- Solution: Set HF_API_KEY environment variable
- Check HuggingFace API credentials and model availability

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build -d

# Check container status
docker ps 

# View logs
docker logs <container_id>

# Test API in container
curl http://localhost:5000/
```

## Resources

- [HuggingFace BLIP Model](https://huggingface.co/Salesforce/blip-image-captioning-large)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [RESTful API Design](https://restfulapi.net/)
- [Postman Documentation](https://learning.postman.com/docs/)
- [PIL/Pillow Documentation](https://pillow.readthedocs.io/)
