# explain_changes Field — Detailed Documentation

This document describes how the **explain_changes** form field is generated, rendered, and composited when using **`--complete-fill`** mode. It covers the full pipeline from data generation through the Python script and the Node handwriting service, and explains the known issues (too many lines, too few characters per line, and text overlapping the label) and how to fix them.

---

## 1. Overview

- **Template**: The field is defined in `template.json` as category `explain_changes` (category_id 23). Its annotation bbox is `[x, y, width, height]` with **width ≈ 1183 px** and **height ≈ 227 px** (see §2).
- **Modes**:
  - **Normal mode** (no `--complete-fill`): One short sentence; rendered as a single handwriting image, scaled to max 600×200 px and centered in the bbox.
  - **Complete-fill mode** (`--complete-fill`): Long paragraph (30–60 words); rendered as **multiple lines** of handwriting, word-wrapped to fit the box. **Only this mode uses the multi-line pipeline** and is the one where the issues appear.

All following sections refer to **complete-fill mode** unless stated otherwise.

---

## 2. Template and Bounding Box

**Source**: `template.json` → `annotations[]` entry with `"category_id": 23`.

- **Bbox format**: `[x, y, width, height]` (COCO style; top-left corner + size).
- **Typical values** (from repo):  
  `x ≈ 128`, `y ≈ 1333`, **width ≈ 1183**, **height ≈ 227**.
- The **visual box** on the form often includes a **label** (e.g. “Explain any changes” or similar) at the **top inside the same bbox**. The script’s “content” area is intended to be the region below that label; if the label is inside the bbox, the script must reserve top space for it (see §6).

---

## 3. Data Generation (Script Side)

**File**: `generate_form_data.py`

**Relevant code** (around lines 188–192):

```python
if complete_fill:
    test_data['explain_changes'] = generate_long_text()
else:
    test_data['explain_changes'] = generate_short_text()
```

**`generate_long_text()`** (lines 46–59):

- Parameters: `min_words=30`, `max_words=60`.
- Builds a paragraph from multiple Faker sentences (8–15 words per sentence) until the word count is in range.
- Returns a **single string** (e.g. 30–60 words, no line breaks).

So in complete-fill mode, **explain_changes** is one long string. Line breaking is done later in `build_test_form.py`, not in data generation.

---

## 4. Script Pipeline: `build_test_form.py` (Complete-Fill Mode)

### 4.1 Exclusion from main batch

**Location**: First loop over categories (lines 46–66).

- For each field with a value, the script appends text to `texts_to_generate` and records `field_info_map[(name, 'text' or 'checkbox')] = index`.
- **Exception**: If `name == 'explain_changes'` and `complete_fill`, this field is **skipped** (lines 52–53). So explain_changes is **not** in the first batch of 59 texts; it is handled in a **separate, second batch**.

### 4.2 Handling explain_changes (multi-line block)

**Location**: Lines 132–231 (inside the “process each category” loop, when `value` is not a boolean).

When `name == 'explain_changes'` and `complete_fill`:

1. **Bbox and available area**
   - `bbox_width = int(bbox[2])`, `bbox_height = int(bbox[3])`.
   - **Top margin**: `top_margin = int(bbox_height * 0.05)` (e.g. ~11 px for height 226).
   - **Horizontal margin**: `h_margin = int(bbox_width * 0.02)`.
   - **Available region**:
     - `available_width = bbox_width - 2 * h_margin`
     - `available_height = bbox_height - top_margin`

2. **Chars per line (word-wrap)**  
   The script assumes handwritten.js renders with approximate constants:
   - `PX_PER_CHAR = 33`
   - `LINE_HEIGHT = 60`  
   It then solves for an “optimal” character count per line so that, after scaling each line to `available_width`, the total height of all lines (with spacing) would roughly fit in `available_height`:
   - Formula:  
     `chars ≈ sqrt(LINE_HEIGHT * available_width * text_length / (PX_PER_CHAR * available_height * 0.85))`
   - Clamp: `chars_per_line = max(25, min(optimal_chars, 90))`.

3. **Word wrap**
   - Words from `text.split()` are grouped into lines so that each line has at most `chars_per_line` characters (counting spaces).
   - Result: list of strings `lines` (e.g. 6 lines for a ~55-character-per-line wrap).

4. **Second batch request**
   - `line_images_bytes = generate_handwriting_images_batch(lines, "http://localhost:8000/generate-batch")`.
   - So the **worker** receives a **second** batch containing only the explain_changes lines (e.g. 6 texts). Each text is one line of the paragraph.

5. **Decode and crop**
   - Each batch item is base64-decoded, opened as PNG, converted to RGBA, and **cropped** with `crop_to_text()` (tight crop to non-background pixels).

6. **Scale to width**
   - For each line image, if width > `available_width`, scale down proportionally so width = `available_width`. Heights scale with the same ratio.

7. **Height and overflow**
   - `spacing = max(2, int(avg_line_height * 0.15))`.
   - `total_h = sum(line heights) + spacing * (num_lines - 1)`.
   - If `total_h > available_height`, **all** line images (and spacing) are scaled down by `s = available_height / total_h` (e.g. `s = 0.32` when overflow is large). This preserves proportions but can make text very small.

8. **Paste**
   - `paste_x = int(bbox[0]) + h_margin`
   - `paste_y = int(bbox[1]) + top_margin`
   - Lines are pasted in order from `paste_y` downward, with `spacing` between them.

So on the **script** side, the only “padding” above the first line is **top_margin = 5% of bbox height**. There is no separate “label” reserve like the 30% used for other text fields.

---

## 5. Worker Side: Handwriting Generation

**Files**: `handwriting-generator/main.ts`, `handwriting-generator/worker.ts`

### 5.1 Batch endpoint (main.ts)

- **Route**: `POST /generate-batch`.
- **Body**: `{ "texts": [ string, ... ] }`.
- For each request, the main process distributes work to **workers** (round-robin by index). Each worker receives `{ id, text }` and returns `{ id, success, image }` (base64 PNG).
- **Order**: Results are collected so that `images[i]` corresponds to `texts[i]` (order preserved).
- So the **first** batch (59 items) is checkboxes + other fields; the **second** batch (e.g. 6 items) is the explain_changes lines only.

### 5.2 Worker (worker.ts)

- **Input**: `{ id, text }` where `text` is one line of the explain_changes paragraph.
- **Call**: `handwritten(text, { outputType: 'png/b64' })`.
- **No other options** are passed (font, size, line height, etc.). The library uses its **defaults**.
- **Output**: Base64-encoded PNG of the rendered line. Dimensions depend entirely on handwritten.js defaults (font size, spacing, etc.), which are **not** documented in this repo and may not match the script’s `PX_PER_CHAR` and `LINE_HEIGHT` assumptions.

So on the **worker** side, each “line” is rendered **independently** as a single line of text with the library’s default metrics. The script then scales and stacks these images.

---

## 6. Summary of the Pipeline

| Stage | Where | What happens |
|-------|--------|----------------|
| Data | `generate_form_data.py` | `explain_changes = generate_long_text()` → one long string (30–60 words). |
| Skip batch | `build_test_form.py` | explain_changes omitted from first `texts_to_generate` when `complete_fill`. |
| Wrap | `build_test_form.py` | Word wrap using `chars_per_line` (from PX_PER_CHAR=33, LINE_HEIGHT=60). |
| Request | `generate_text_image.py` → HTTP | Second batch: `POST /generate-batch` with `texts = [ line1, line2, ... ]`. |
| Worker | `main.ts` → `worker.ts` | Each worker runs `handwritten(line, { outputType: 'png/b64' })`. |
| Response | Worker → script | List of base64 PNGs, one per line. |
| Compose | `build_test_form.py` | Decode, crop, scale to width, possibly scale down for height, paste with `paste_y = bbox[1] + top_margin`. |

---

## 7. Known Issues (Complete-Fill Only)

### 7.1 Too many lines / not enough characters per line

**Observed**: Output has many short lines; text looks “choppy” and sometimes gets scaled down heavily (e.g. “Height overflow … extra scale=0.32”).

**Cause**:
- The script assumes **PX_PER_CHAR = 33** and **LINE_HEIGHT = 60** for handwritten.js. The actual library output likely uses **different** dimensions (e.g. more pixels per character or per line).
- If the real “line height” is larger than 60, or “px per character” is smaller than 33, the formula yields a **smaller** `optimal_chars` → **more lines**.
- More lines → total height exceeds `available_height` → strong uniform scale-down → tiny text and “too many lines” visually.

So the issue is a **mismatch** between assumed and actual rendering metrics.

### 7.2 No top padding / text overrides the label

**Observed**: Handwritten content overlaps the label at the top of the box.

**Cause**:
- The script uses **top_margin = 5%** of bbox height (e.g. ~11 px). The comment says “label text is above the bbox,” but on the actual form the label is often **inside** the top of the bbox.
- Other text fields in the same script use **field_label_offset = 30%** of bbox height to reserve space for the label before placing text. explain_changes does **not** use any such reserve; it only uses the small 5% top margin.
- So **paste_y** is too high and the first line is drawn over the label.

---

## 8. Recommended Fixes

### 8.1 Align line-breaking with actual handwriting metrics

**Option A — Measure and use real metrics**

1. Generate a few sample lines with the worker (e.g. “The quick brown fox…” with known character count).
2. Decode the PNGs, run `crop_to_text`, and measure width and height. Compute approximate px-per-character and line height.
3. Replace `PX_PER_CHAR` and `LINE_HEIGHT` in `build_test_form.py` (lines 154–155) with these values, or make them configurable (e.g. from env or a small config).

**Option B — Prefer fewer, longer lines**

- Increase the **minimum** chars per line (e.g. `max(40, min(optimal_chars, 90))` or higher) so you get fewer lines.
- Optionally **increase** the constant used for “line height” in the formula so the script plans for more vertical space per line and thus chooses a larger `chars_per_line` (fewer lines). Both reduce the chance of height overflow and heavy scale-down.

**Option C — Configure handwritten.js**

- If the library supports options (font size, line height, etc.), pass options from the worker so that one “line” of text has predictable dimensions. Then set `PX_PER_CHAR` and `LINE_HEIGHT` in the script to match.

### 8.2 Reserve space for the label (top padding)

- Treat the top of the bbox like other fields: reserve a **label region** before the writing area.
- Example:  
  `label_reserve = int(bbox_height * 0.25)` (or 0.20–0.30 to match the form layout).  
  Then:
  - `available_height = bbox_height - label_reserve` (or `available_height = bbox_height - top_margin - label_reserve` if you keep a small extra margin).
  - `paste_y = int(bbox[1]) + label_reserve` (so the first line starts **below** the label).
- Use the same `label_reserve` in the **chars-per-line** formula (so `available_height` there also excludes the label). That way line count and scaling are consistent with the actual content area.

---

## 9. Quick Reference: Key Constants and Locations

| What | Value / location |
|------|-------------------|
| explain_changes bbox (template) | `template.json` annotation with `category_id: 23`; width ≈ 1183, height ≈ 227. |
| Long text generation | `generate_form_data.py`: `generate_long_text(min_words=30, max_words=60)`. |
| Skip in batch | `build_test_form.py` lines 52–53: `if name == 'explain_changes' and complete_fill: continue`. |
| Multi-line block | `build_test_form.py` lines 132–231. |
| Top margin | `top_margin = int(bbox_height * 0.05)` (line 139). |
| Chars per line | Formula lines 154–161; clamp line 161: `max(25, min(optimal_chars, 90))`. |
| PX_PER_CHAR / LINE_HEIGHT | Lines 154–155: `33`, `60`. |
| Second batch | `generate_handwriting_images_batch(lines, ...)` line 185. |
| Worker call | `handwriting-generator/worker.ts`: `handwritten(text, { outputType: 'png/b64' })`. |
| Paste position | `paste_x = bbox[0] + h_margin`, `paste_y = bbox[1] + top_margin` (lines 195–196). |

---

## 10. Debug Logs (Script)

When explain_changes is rendered in complete-fill mode, the script prints:

- `[Explain] chars_per_line=…, lines=…, box=…x…, avail=…x…`
- If height overflows: `[Explain] Height overflow: …px > …px, extra scale=…`
- `[Explain] Final: … lines, avg_h=…px, total_h=…px/…px, spacing=…px`

Use these to verify `chars_per_line`, number of lines, and whether a large scale-down is applied.

---

This document is the single detailed reference for the **explain_changes** field in **Form-Generation** for **`--complete-fill`** mode, from data generation through the script and worker, plus the described issues and fixes.
