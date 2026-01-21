# Load, shuffle, and split encoded data
import json
import random

input_jsonl = "encoded_data.jsonl"
with open(input_jsonl, "r") as f:
    data = [json.loads(line) for line in f]

# Don't want all the real documents together
random.shuffle(data)

# Use 90% of the data as training, the rest as evaulation
split_idx = int(0.9 * len(data))
train_data = data[:split_idx]
eval_data = data[split_idx:]

print(
    f"Loaded {len(data)} samples. Split: {len(train_data)} train, {len(eval_data)} eval."
)
from transformers import LayoutLMv3ForSequenceClassification, Trainer, TrainingArguments
from datasets import Dataset

train_dataset = Dataset.from_list(train_data)
eval_dataset = Dataset.from_list(eval_data)

# This example only uses two labels, but in a larger scenario this should be based on training data.
model = LayoutLMv3ForSequenceClassification.from_pretrained(
    "microsoft/layoutlmv3-base", num_labels=2
)

training_args = TrainingArguments(
    output_dir="./results", per_device_train_batch_size=4, num_train_epochs=3
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
)
trainer.train()
