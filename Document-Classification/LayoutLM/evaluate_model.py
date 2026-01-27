import json
from datasets import Dataset
from transformers import (
    LayoutLMv3ForSequenceClassification,
    Trainer,
)
import sys

if len(sys.argv) != 2:
    print("Usage: python evaluate_model.py <model_path>")
    sys.exit(1)

model_path = sys.argv[1]

# Load eval data
with open("encoded_data.jsonl", "r") as f:
    data = [json.loads(line) for line in f]

# Shuffle and split (same as training)
import random

random.shuffle(data)

eval_dataset = Dataset.from_list(data)

# Load model
model = LayoutLMv3ForSequenceClassification.from_pretrained(model_path)


# Define compute_metrics for accuracy
def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = logits.argmax(-1)
    acc = (preds == labels).astype(float).mean().item()
    return {"accuracy": acc}


# Evaluate
trainer = Trainer(
    model=model,
    eval_dataset=eval_dataset,
    compute_metrics=compute_metrics,
)
results = trainer.evaluate()
print("Evaluation results:", results)
