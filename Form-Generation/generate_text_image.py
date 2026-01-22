import requests
import base64

def generate_handwriting_image(text, api_url="http://localhost:8000/generate"):
    """
    Sends a POST request to the Deno handwriting service and returns the PNG image bytes (from base64 JSON response).
    Args:
        text (str): The text to render.
        api_url (str): The Deno service endpoint URL.
    Returns:
        bytes: PNG image bytes.
    Raises:
        requests.HTTPError: If the request fails.
    """
    payload = {"text": text}
    response = requests.post(api_url, json=payload)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"HTTP error: {e}\nStatus code: {response.status_code}\nResponse text: {response.text}")
        raise
    try:
        data = response.json()
        b64 = data["image"]
        # If image is a list, get the first element
        if isinstance(b64, list):
            b64 = b64[0]
        # Remove data URL prefix if present
        if b64.startswith("data:image"):
            b64 = b64.split(",", 1)[-1]
        return base64.b64decode(b64)
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
    return cropped
