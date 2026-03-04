# LoRA Fine-Tuning Prototype

A proof-of-concept pipeline for parameter-efficient fine-tuning using LoRA (Low-Rank Adaptation). This prototype fine-tunes **Qwen3-8B** on a small text instruction dataset to validate the toolchain before moving to vision/OCR tasks.

## Prerequisites

- **Hardware:** Intel Xeon CPU with 128GB RAM (tested on OpenShift). Also works on any CUDA-capable GPU.
- **Python:** 3.12+ (3.10 minimum)
- **Package manager:** [uv](https://github.com/astral-sh/uv)

## Running on OpenShift

### 1. Install uv

If `uv` is not already available in your pod/container:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env  # or restart your shell
```

Verify the installation:

```bash
uv --version
```

If your system Python is older than 3.10, use `uv` to install a supported version:

```bash
uv python install 3.12
```

### 2. Clone and set up the project

```bash
git clone <your-repo-url>
cd LoRA-Adapters/prototype
```

### 3. Create a virtual environment and install dependencies

```bash
uv venv --python 3.12
uv pip install -r requirements.txt --python .venv/bin/python
```

### 4. Run training

```bash
.venv/bin/python train.py
```

The script prints progress through 5 stages:

1. Loading model and tokenizer (Qwen3-8B)
2. Preparing dataset (180 train / 20 eval from `yahma/alpaca-cleaned`)
3. Configuring LoRA adapters
4. Training (3 epochs, ~135 steps)
5. Saving artifacts

The model downloads from Hugging Face Hub on first run (~1.2GB). On CPU-only nodes this will run on CPU automatically.

### 5. Run evaluation

Requires a trained adapter in `adapter/` (run training first).

```bash
.venv/bin/python evaluate.py
```

This loads both the base model and the LoRA-adapted model, runs them on the same 20 held-out examples, prints a side-by-side comparison, and saves results to `eval_results.json`.

## Output Artifacts

| File | Description |
|---|---|
| `adapter/` | Saved LoRA adapter weights and tokenizer |
| `training_log.json` | Full training log history (loss, eval metrics per step) |
| `loss_curve.png` | Plot of training loss over steps |
| `eval_results.json` | Evaluation output (generated after running evaluate.py) |

## LoRA Configuration

| Parameter | Value | Purpose |
|---|---|---|
| `r` (rank) | 16 | Rank of the low-rank decomposition. Higher = more capacity, more parameters. |
| `alpha` | 32 | Scaling factor. The effective learning rate scales as `alpha/r` (here 2x). |
| `dropout` | 0.05 | Light regularization to reduce overfitting on the small dataset. |
| `target_modules` | q_proj, k_proj, v_proj, o_proj | All four attention projection matrices. |

Only the LoRA parameters are trained. The base model weights stay frozen, keeping total trainable parameters well under 1% of the full model.

## Loading the Adapter Independently

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-8B")
model = PeftModel.from_pretrained(base, "./adapter")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
```

## Project Structure

```
prototype/
├── README.md
├── requirements.txt
├── train.py              # Training pipeline
├── evaluate.py           # Base vs. LoRA evaluation
├── adapter/              # (generated) Saved LoRA weights
├── training_log.json     # (generated) Training metrics
├── eval_results.json     # (generated) Evaluation output
└── loss_curve.png        # (generated) Loss plot
```

## Starting Over

To remove all generated artifacts and retrain from scratch:

```bash
rm -rf adapter/ training_log.json eval_results.json loss_curve.png
```

To clear the Hugging Face model cache (frees disk space):

```bash
rm -rf ~/.cache/huggingface/hub/
```

To check disk usage in the current directory (including hidden files):

```bash
du -sh .[!.]* * | sort -rh
```

## Next Steps

- **Vision/OCR iteration:** Use Qwen3-VL's multimodal capabilities to fine-tune on image-text pairs for document OCR tasks.
- **Larger dataset:** Scale beyond 200 examples once the pipeline is validated.
- **Quantization:** Explore QLoRA (4-bit) to reduce memory usage for larger models.
