import sys
from PIL import Image
from transformers import LayoutLMv3Processor, LayoutLMv3ForSequenceClassification
import torch

if len(sys.argv) != 3:
    print("Usage: python use_model.py <model_path> <image_path>")
    sys.exit(1)

model_path = sys.argv[1]
image_path = sys.argv[2]

# Load processor and model
processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")
model = LayoutLMv3ForSequenceClassification.from_pretrained(model_path)

# Load and preprocess image
image = Image.open(image_path).convert("RGB")
inputs = processor(
    image, return_tensors="pt", truncation=True, padding="max_length", max_length=512
)

# Predict
with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits
    pred = logits.argmax(-1).item()

print(f"Predicted label: {pred}")
