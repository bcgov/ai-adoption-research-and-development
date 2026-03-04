#!/usr/bin/env python3
"""Evaluate base model vs. LoRA-adapted model on held-out examples."""

import json
import os
import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# Must match train.py
BASE_MODEL = "Qwen/Qwen3-8B"
ADAPTER_DIR = os.path.join(os.path.dirname(__file__), "adapter")
DATASET_NAME = "yahma/alpaca-cleaned"
DATASET_SIZE = 200
SEED = 42
MAX_NEW_TOKENS = 256


def get_device():
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_eval_dataset():
    """Load the same 20 eval examples used during training."""
    dataset = load_dataset(DATASET_NAME, split="train")
    dataset = dataset.shuffle(seed=SEED).select(range(DATASET_SIZE))
    split = dataset.train_test_split(test_size=20, seed=SEED)
    return split["test"]


def generate_response(model, tokenizer, instruction, input_text="", device="cpu"):
    """Generate a response for a single example."""
    messages = [{"role": "system", "content": "You are a helpful assistant."}]

    user_content = instruction
    if input_text:
        user_content += f"\n\n{input_text}"
    messages.append({"role": "user", "content": user_content})

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
        enable_thinking=False,
    )
    inputs = tokenizer(text, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            temperature=None,
            top_p=None,
            top_k=None,
            pad_token_id=tokenizer.pad_token_id,
        )

    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
    )
    return response.strip()


def main():
    device = get_device()
    print(f"Using device: {device}")
    prototype_dir = os.path.dirname(__file__)

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load eval dataset
    eval_dataset = load_eval_dataset()
    print(f"Evaluating on {len(eval_dataset)} examples\n")

    results = []

    # --- Base model ---
    print("Loading base model...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype="auto",
    ).to(device)
    base_model.eval()

    print("Generating base model responses...")
    for i, example in enumerate(eval_dataset):
        base_response = generate_response(
            base_model, tokenizer, example["instruction"], example.get("input", ""), device
        )
        results.append({
            "instruction": example["instruction"],
            "input": example.get("input", ""),
            "expected": example["output"],
            "base_response": base_response,
        })
        print(f"  Base [{i+1}/{len(eval_dataset)}] done")

    del base_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # --- LoRA model ---
    print("\nLoading LoRA-adapted model...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype="auto",
    ).to(device)
    lora_model = PeftModel.from_pretrained(base_model, ADAPTER_DIR).to(device)
    lora_model.eval()

    print("Generating LoRA model responses...")
    for i, example in enumerate(eval_dataset):
        lora_response = generate_response(
            lora_model, tokenizer, example["instruction"], example.get("input", ""), device
        )
        results[i]["lora_response"] = lora_response
        print(f"  LoRA [{i+1}/{len(eval_dataset)}] done")

    # Print side-by-side comparison
    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    for i, r in enumerate(results):
        print(f"\n--- Example {i+1} ---")
        print(f"Instruction: {r['instruction'][:100]}...")
        print(f"Expected:    {r['expected'][:100]}...")
        print(f"Base:        {r['base_response'][:100]}...")
        print(f"LoRA:        {r['lora_response'][:100]}...")

    # Save results
    output_path = os.path.join(prototype_dir, "eval_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
