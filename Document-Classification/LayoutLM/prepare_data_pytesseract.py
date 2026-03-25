# An optional script that gathers ocr data from an image.
# Couldn't get LayoutLM to accept this input, although it doesn't appear to be
# a fault with the input itself.

from pytesseract import image_to_data
from PIL import Image
import json

image_path = "report_documents/test_form.jpg"
image = Image.open(image_path)
ocr_data = image_to_data(image, output_type="dict")

tokens = ocr_data["text"]
bboxes = [
    [
        ocr_data["left"][i],
        ocr_data["top"][i],
        ocr_data["left"][i] + ocr_data["width"][i],
        ocr_data["top"][i] + ocr_data["height"][i],
    ]
    for i in range(len(ocr_data["text"]))
]

# Save output to JSON file in bb_output folder
output_data = {"image": image_path, "tokens": tokens, "bboxes": bboxes}
with open("bb_output/ocr_output.jsonl", "w") as f:
    json.dump(output_data, f)
print("OCR output saved to bb_output/ocr_output.jsonl")
