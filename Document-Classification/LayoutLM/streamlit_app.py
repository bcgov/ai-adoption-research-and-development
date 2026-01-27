import streamlit as st
from PIL import Image
import io
import os

import torch
from transformers import LayoutLMv3Processor, LayoutLMv3ForSequenceClassification
from labels_enum import Label

st.title("Document Classification Demo")


# Sidebar for model selection
st.sidebar.header("Model Settings")
results_dir = "./results"
checkpoints = [
    d
    for d in os.listdir(results_dir)
    if d.startswith("checkpoint-") and os.path.isdir(os.path.join(results_dir, d))
]
checkpoints.sort()
default_checkpoint = checkpoints[-1] if checkpoints else ""
selected_checkpoint = st.sidebar.selectbox(
    "Select model checkpoint",
    checkpoints,
    index=(
        checkpoints.index(default_checkpoint)
        if default_checkpoint in checkpoints
        else 0
    ),
)
model_path = (
    os.path.join(results_dir, selected_checkpoint) if selected_checkpoint else None
)


# Load model and processor once per model_path
@st.cache_resource
def load_model(model_path):
    processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")
    model = LayoutLMv3ForSequenceClassification.from_pretrained(model_path)
    return processor, model


processor, model = load_model(model_path)

uploaded_file = st.file_uploader(
    "Upload a document (PDF or image)", type=["png", "jpg", "jpeg"]
)

if uploaded_file:
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name
    st.write(f"Uploaded: {file_name}")
    # Only support image files for now
    if file_name.lower().endswith((".png", ".jpg", ".jpeg")):
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        st.image(image, caption="Uploaded Image")
        # Preprocess and run inference
        inputs = processor(
            image,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=512,
        )
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            pred = logits.argmax(-1).item()
        # Map prediction to label name
        label_name = None
        for lbl in Label:
            if lbl.value == pred:
                label_name = lbl.name
                break
        st.success(f"Classification result: {label_name if label_name else pred}")
    elif file_name.lower().endswith(".pdf"):
        st.info("PDF preview not supported. Proceeding to classification.")
else:
    st.write("Please upload a document to classify.")
