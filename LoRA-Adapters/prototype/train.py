#!/usr/bin/env python3
"""Minimal LoRA fine-tuning pipeline for Qwen3-0.6B."""

import json
import os
import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, TaskType
from trl import SFTTrainer, SFTConfig
import matplotlib.pyplot as plt

# --- Configuration ---
BASE_MODEL = "Qwen/Qwen3-8B"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "adapter")
DATASET_NAME = "yahma/alpaca-cleaned"
DATASET_SIZE = 200
MAX_LENGTH = 512
SEED = 42

# LoRA config
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"]

# Training config
NUM_EPOCHS = 3
BATCH_SIZE = 1
GRADIENT_ACCUMULATION_STEPS = 4
LEARNING_RATE = 2e-4


def get_device():
    """Select best available device."""
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_and_prepare_dataset(tokenizer):
    """Load alpaca-cleaned and format as chat messages."""
    dataset = load_dataset(DATASET_NAME, split="train")
    dataset = dataset.shuffle(seed=SEED).select(range(DATASET_SIZE))

    # Split 180 train / 20 eval
    split = dataset.train_test_split(test_size=20, seed=SEED)
    train_dataset = split["train"]
    eval_dataset = split["test"]

    def format_as_chat(example):
        messages = []
        messages.append({"role": "system", "content": "You are a helpful assistant."})

        user_content = example["instruction"]
        if example.get("input"):
            user_content += f"\n\n{example['input']}"

        messages.append({"role": "user", "content": user_content})
        messages.append({"role": "assistant", "content": example["output"]})

        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False,
            enable_thinking=False,
        )
        return {"text": text}

    train_dataset = train_dataset.map(format_as_chat)
    eval_dataset = eval_dataset.map(format_as_chat)

    return train_dataset, eval_dataset


def setup_model_and_tokenizer():
    """Load base model and tokenizer."""
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    device = get_device()
    print(f"Using device: {device}")

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype="auto",
    )

    return model, tokenizer


def save_loss_curve(log_history, output_dir):
    """Plot and save training loss curve."""
    steps = [entry["step"] for entry in log_history if "loss" in entry]
    losses = [entry["loss"] for entry in log_history if "loss" in entry]

    if not steps:
        print("No loss data to plot.")
        return

    plt.figure(figsize=(8, 5))
    plt.plot(steps, losses, marker="o", markersize=3)
    plt.xlabel("Step")
    plt.ylabel("Training Loss")
    plt.title("LoRA Fine-Tuning Loss Curve")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "..", "loss_curve.png"), dpi=150)
    plt.close()
    print("Loss curve saved.")


def main():
    print("=" * 50)
    print("LoRA Fine-Tuning Pipeline")
    print("=" * 50)

    # 1. Setup
    print("\n[1/5] Loading model and tokenizer...")
    model, tokenizer = setup_model_and_tokenizer()

    # 2. Dataset
    print("\n[2/5] Preparing dataset...")
    train_dataset, eval_dataset = load_and_prepare_dataset(tokenizer)
    print(f"  Train: {len(train_dataset)} examples")
    print(f"  Eval:  {len(eval_dataset)} examples")

    # 3. LoRA config (passed to SFTTrainer, not applied manually)
    print("\n[3/5] Configuring LoRA adapters...")
    peft_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=TARGET_MODULES,
        task_type=TaskType.CAUSAL_LM,
        bias="none",
    )

    # 4. Train
    print("\n[4/5] Training...")
    prototype_dir = os.path.dirname(__file__)

    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        learning_rate=LEARNING_RATE,
        lr_scheduler_type="cosine",
        warmup_steps=14,
        logging_steps=5,
        save_strategy="epoch",
        eval_strategy="epoch",
        max_length=MAX_LENGTH,
        dataset_text_field="text",
        fp16=False,
        bf16=False,
        report_to="none",
        seed=SEED,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        peft_config=peft_config,
        processing_class=tokenizer,
    )

    trainer.model.print_trainable_parameters()
    result = trainer.train()

    # 5. Save
    print("\n[5/5] Saving artifacts...")
    trainer.model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    # Save training log
    log_path = os.path.join(prototype_dir, "training_log.json")
    with open(log_path, "w") as f:
        json.dump(trainer.state.log_history, f, indent=2)
    print(f"  Training log saved to {log_path}")

    # Save loss curve
    save_loss_curve(trainer.state.log_history, OUTPUT_DIR)

    print("\n" + "=" * 50)
    print("Training complete!")
    print(f"  Adapter saved to: {OUTPUT_DIR}")
    print(f"  Total train loss: {result.training_loss:.4f}")
    print("=" * 50)


if __name__ == "__main__":
    main()
