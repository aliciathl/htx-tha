#!/usr/bin/env python3
"""
Basic API testing script for the Image Processing API
"""
import requests
import time
import os

BASE_URL = "http://localhost:5000"

def test_health():
    """Test if API is running"""
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print("✅ API is running")
            return True
        else:
            print("❌ API health check failed")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is it running?")
        return False

def test_upload_image():
    """Test image upload"""
    print("\n--- Testing Image Upload ---")
    
    # Create a simple test image if none exists
    test_image_path = "test_image.jpg"
    if not os.path.exists(test_image_path):
        print("No test image found. Please create a test image or provide a path.")
        return None
    
    try:
        with open(test_image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{BASE_URL}/api/images", files=files)
        
        print(f"Upload response: {response.status_code}")
        if response.status_code == 202:
            data = response.json()
            image_id = data['data']['image_id']
            print(f"✅ Upload successful! Image ID: {image_id}")
            return image_id
        else:
            print(f"❌ Upload failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def test_list_images():
    """Test listing images"""
    print("\n--- Testing List Images ---")
    try:
        response = requests.get(f"{BASE_URL}/api/images")
        print(f"List response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            count = len(data['data'])
            print(f"✅ Found {count} images")
            return data['data']
        else:
            print(f"❌ List failed: {response.text}")
            return []
    except Exception as e:
        print(f"❌ List error: {e}")
        return []

def test_image_details(image_id):
    """Test getting image details"""
    print(f"\n--- Testing Image Details (ID: {image_id}) ---")
    try:
        response = requests.get(f"{BASE_URL}/api/images/{image_id}")
        print(f"Details response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            status = data['data']['status']
            print(f"✅ Image status: {status}")
            return data['data']
        else:
            print(f"❌ Details failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Details error: {e}")
        return None

def test_thumbnail(image_id, size="small"):
    """Test getting thumbnail"""
    print(f"\n--- Testing Thumbnail {size} (ID: {image_id}) ---")
    try:
        response = requests.get(f"{BASE_URL}/api/images/{image_id}/thumbnails/{size}")
        print(f"Thumbnail response: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Thumbnail {size} available")
            return True
        else:
            print(f"❌ Thumbnail failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Thumbnail error: {e}")
        return False

def test_stats():
    """Test getting statistics"""
    print("\n--- Testing Statistics ---")
    try:
        response = requests.get(f"{BASE_URL}/api/stats")
        print(f"Stats response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            stats = data['data']
            print(f"✅ Total images: {stats['total_images']}")
            print(f"✅ Successful: {stats['successful']}")
            print(f"✅ Failed: {stats['failed']}")
            print(f"✅ Processing: {stats['processing']}")
            return stats
        else:
            print(f"❌ Stats failed: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Stats error: {e}")
        return None

def main():
    """Run all tests"""
    print("🚀 Starting API Tests")
    
    # Test health
    if not test_health():
        return
    
    # Test upload
    image_id = test_upload_image()
    if not image_id:
        print("⚠️  Skipping remaining tests due to upload failure")
        return
    
    # Wait a bit for processing
    print("\n⏳ Waiting 3 seconds for processing...")
    time.sleep(3)
    
    # Test other endpoints
    test_list_images()
    test_image_details(image_id)
    test_thumbnail(image_id, "small")
    test_thumbnail(image_id, "medium") 
    test_stats()

    print("\n🎉 All Tests completed!")

if __name__ == "__main__":
    main()