import json
from PIL import Image
from transformers import LayoutLMv3Processor
from labels_enum import Label

import os

# Directory containing images
report_dir = "report_documents"
other_dir = "other_documents"
output_jsonl = "encoded_data.jsonl"

processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")


def pad_to_length(seq, length, pad_value):
    return seq + [pad_value] * (length - len(seq))


def encode_folder(folder_path, label, max_length=512):
    for fname in os.listdir(folder_path):
        fpath = os.path.join(folder_path, fname)
        print(fpath)
        # Only images
        if not (
            fname.lower().endswith(".jpg")
            or fname.lower().endswith(".png")
            or fname.lower().endswith(".jpeg")
        ):
            continue
        # Image must have three dimensions (height, width, channels)
        # Greyscale only has 2, so convert to guarantee the third
        image = Image.open(fpath).convert("RGB")
        encoding = processor(
            image,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=max_length,
        )
        item = {}
        item = {k: v[0].tolist() for k, v in encoding.items()}
        item["image_path"] = fpath
        item["label"] = label.value
        out_f.write(json.dumps(item) + "\n")


with open(output_jsonl, "w") as out_f:
    encode_folder(other_dir, Label.OTHER)
    encode_folder(report_dir, Label.MONTHLY_REPORT)
