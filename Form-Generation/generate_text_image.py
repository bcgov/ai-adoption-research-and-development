import requests
import base64
import time
from functools import lru_cache

# Global session for connection pooling
_session = None

def get_session():
    """Get or create a requests session with connection pooling."""
    global _session
    if _session is None:
        _session = requests.Session()
    return _session

# LRU cache for repeated strings (common values like "X", dates, etc.)
@lru_cache(maxsize=100)
def _generate_handwriting_image_cached(text, api_url):
    """Cached version of handwriting generation."""
    return _generate_handwriting_image_impl(text, api_url)

def _generate_handwriting_image_impl(text, api_url="http://localhost:8000/generate"):
    """
    Internal implementation: Sends a POST request to the Deno handwriting service.
    Returns PNG image bytes (from base64 JSON response).
    """
    start_time = time.time()
    payload = {"text": text}
    session = get_session()
    
    request_start = time.time()
    response = session.post(api_url, json=payload)
    request_time = time.time() - request_start
    
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"HTTP error: {e}\nStatus code: {response.status_code}\nResponse text: {response.text}")
        raise
    
    decode_start = time.time()
    try:
        data = response.json()
        b64 = data["image"]
        # If image is a list, get the first element
        if isinstance(b64, list):
            b64 = b64[0]
        # Remove data URL prefix if present
        if b64.startswith("data:image"):
            b64 = b64.split(",", 1)[-1]
        image_bytes = base64.b64decode(b64)
        decode_time = time.time() - decode_start
        total_time = time.time() - start_time
        print(f"  [Timing] '{text[:30]}...': HTTP={request_time:.3f}s, decode={decode_time:.3f}s, total={total_time:.3f}s")
        return image_bytes
    except Exception as e:
        print(f"JSON decode/base64 error: {e}\nRaw response: {response.text}")
        raise

def generate_handwriting_image(text, api_url="http://localhost:8000/generate", use_cache=True):
    """
    Sends a POST request to the Deno handwriting service and returns the PNG image bytes.
    Uses caching for repeated strings.
    Args:
        text (str): The text to render.
        api_url (str): The Deno service endpoint URL.
        use_cache (bool): Whether to use LRU cache for repeated strings.
    Returns:
        bytes: PNG image bytes.
    Raises:
        requests.HTTPError: If the request fails.
    """
    if use_cache:
        return _generate_handwriting_image_cached(text, api_url)
    else:
        return _generate_handwriting_image_impl(text, api_url)

def generate_handwriting_images_batch(texts, api_url="http://localhost:8000/generate", options=None):
    """
    Batch API: Generate multiple handwriting images in a single request.
    Args:
        texts (list[str]): List of texts to render.
        api_url (str): The Deno service endpoint URL (should be /generate-batch).
        options (dict, optional): Passed to handwritten.js (e.g. {"lineWidth": 95} if using a patched build).
    Returns:
        list[bytes]: List of PNG image bytes.
    """
    if not texts:
        return []
    
    start_time = time.time()
    payload = {"texts": texts}
    if options is not None and isinstance(options, dict):
        payload["options"] = options
    session = get_session()
    
    request_start = time.time()
    response = session.post(api_url, json=payload)
    request_time = time.time() - request_start
    
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"HTTP error: {e}\nStatus code: {response.status_code}\nResponse text: {response.text}")
        raise
    
    decode_start = time.time()
    try:
        data = response.json()
        images = data["images"]
        # Decode all base64 images
        image_bytes_list = []
        for i, b64 in enumerate(images):
            if isinstance(b64, list):
                b64 = b64[0]
            if b64.startswith("data:image"):
                b64 = b64.split(",", 1)[-1]
            image_bytes_list.append(base64.b64decode(b64))
        
        decode_time = time.time() - decode_start
        total_time = time.time() - start_time
        print(f"  [Batch Timing] {len(texts)} texts: HTTP={request_time:.3f}s, decode={decode_time:.3f}s, total={total_time:.3f}s ({total_time/len(texts):.3f}s per text)")
        return image_bytes_list
    except Exception as e:
        print(f"JSON decode/base64 error: {e}\nRaw response: {response.text}")
        raise

def crop_to_text(img, bg_threshold=180):
    """
    Crops the image to the bounding box of non-background (non-white) pixels.
    Args:
        img (PIL.Image): RGBA or RGB image to crop.
        bg_threshold (int): RGB threshold for background (250 is white).
    Returns:
        PIL.Image: Cropped image containing only the text.
    """
    import numpy as np
    crop_start = time.time()
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    arr = np.array(img)
    # Mask for non-white pixels (allow some tolerance)
    mask = ~((arr[...,0] > bg_threshold) & (arr[...,1] > bg_threshold) & (arr[...,2] > bg_threshold) & (arr[...,3] > 0))
    coords = np.argwhere(mask)
    if coords.size == 0:
        return img  # No text found, return original
    y0, x0 = coords.min(axis=0)[:2]
    y1, x1 = coords.max(axis=0)[:2]
    # PIL crop box is (left, upper, right, lower)
    cropped = img.crop((x0, y0, x1+1, y1+1))
    crop_time = time.time() - crop_start
    if crop_time > 0.01:  # Only log if it takes significant time
        print(f"    [Crop Timing] crop={crop_time:.3f}s")
    return cropped
