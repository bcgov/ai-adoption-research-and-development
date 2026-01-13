import requests
import base64


from trdg.generators import (
    GeneratorFromStrings,
)
import os

def generate_text_image(text_list, count=1):
    generator = GeneratorFromStrings(
        text_list,
        count,
        language="en",
        background_type=1,
        text_color="#000000",
        is_handwritten=True,
        fonts=[],
        size=128,
        skewing_angle=0,
        random_skew=False,
        blur=0,
        random_blur=False,
        distorsion_type=0,
        distorsion_orientation=0,
        width=-1,
        alignment=1,
        orientation=0,
        space_width=1.0,
        character_spacing=0,
        margins=(5, 5, 5, 5),
        fit=False,
        output_mask=False,
        word_split=False,
        stroke_width=1, 
        stroke_fill="#000000",
        image_mode="RGBA",
        output_bboxes=0,
        rtl=False,
    )

    # Return these images as a list, converting white to transparent
    images = []
    for (img, label) in generator:
        # Convert white background to transparent
        img = img.convert("RGBA")
        datas = img.getdata()
        newData = []
        for item in datas:
            # item is (R, G, B, A)
            if item[0] > 250 and item[1] > 250 and item[2] > 250:
                # If white, make transparent
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        img.putdata(newData)
        images.append((img, label))
    return images

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        texts = sys.argv[1:]
        images = generate_text_image(texts, 5)

        output_dir = './output'
        os.makedirs(output_dir, exist_ok=True)

        for i, (img, label) in enumerate(images):
            img_path = os.path.join(output_dir, f"{label}_{i}.png")
            img.save(img_path)
            print(f"Saved: {img_path}")
    else:
        print("Usage: python generate_text_image.py <text1> <text2> ...")

def generate_handwriting_svg(text, style=0, alignment="left", api_url="http://localhost:3000/api/preview"):
    """
    Sends a POST request to the handwriting synthesis API and returns the SVG string.
    Args:
        text (str): The text to render.
        style (int): The handwriting style index.
        alignment (str): 'left' or 'center'.
        api_url (str): The API endpoint URL.
    Returns:
        str: SVG content as a string.
    Raises:
        requests.HTTPError: If the request fails.
    """
    payload = {
        "text": text,
        "style": style,
        "alignment": alignment
    }
    response = requests.post(api_url, json=payload)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"HTTP error: {e}\nStatus code: {response.status_code}\nResponse text: {response.text}")
        raise

    try:
        data = response.json()
    except Exception as e:
        print(f"JSON decode error: {e}\nRaw response: {response.text}")
        raise
    return data.get("svg", "")

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
