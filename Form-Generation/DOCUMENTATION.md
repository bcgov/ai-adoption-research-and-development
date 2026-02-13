# Form Generation Pipeline - Technical Documentation

## Overview

The Form Generation Pipeline is a comprehensive system for generating synthetic form images with realistic handwritten text. It combines Python-based data generation, a Deno-based handwriting service, and image composition techniques to create filled-out form images that can be used for training and testing document processing systems.

## System Architecture

The system consists of three main components working together:

1. **Data Generation Layer** (`generate_form_data.py`) - Generates realistic form field values
2. **Handwriting Service** (`handwriting-generator/`) - Converts text to handwritten images via HTTP API
3. **Form Composition Engine** (`build_test_form.py`) - Composes handwritten text onto form templates

```
┌─────────────────────┐
│  build_test_form.py │
│   (Main Script)     │
└──────────┬──────────┘
           │
           ├─────────────────┐
           │                 │
           ▼                 ▼
┌──────────────────┐  ┌──────────────────────┐
│ generate_form_   │  │ generate_text_image  │
│    data.py       │  │       .py            │
│                  │  │                      │
│ • Faker library  │  │ • HTTP Client        │
│ • Random logic   │  │ • Image processing   │
│ • Field rules    │  │ • Cropping           │
└──────────────────┘  └──────────┬───────────┘
                                  │
                                  │ HTTP POST
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │ handwriting-generator/   │
                    │    (Deno Service)       │
                    │                         │
                    │ • handwritten.js        │
                    │ • Port 8000            │
                    └─────────────────────────┘
```

## Technology Stack

### Python Components
- **Pillow (PIL)** - Image manipulation and composition
- **Faker** - Realistic fake data generation (names, dates, etc.)
- **NumPy** - Image array processing for text cropping
- **Requests** - HTTP client for communicating with handwriting service

### Deno Service
- **Deno Runtime** - TypeScript runtime for the handwriting service
- **handwritten.js** - NPM package that generates handwritten-style text images
- **Deno Standard Library** - HTTP server implementation

### Data Format
- **JSON** - Template annotations (COCO format) and generated form data
- **JPEG/PNG** - Image formats for templates and output

## Complete Data Flow

### Step 1: Data Generation (`generate_form_data.py`)

The `generate_data()` function creates a dictionary of form field values using probabilistic rules:

**Checkbox Fields:**
- Uses `roll100(percentage)` function to determine checkbox states
- Example: `checkbox_need_assistance_yes` has 70% probability of being True
- Each checkbox pair (Yes/No) is mutually exclusive

**Text Fields:**
- **Names**: Generated using `Faker.name()`
- **Phone Numbers**: Random patterns like `###-###-###`, `(###) ### ###`, etc.
- **Dates**: Multiple format variations (`%Y-%b-%d`, `%m/%d/%Y`, etc.)
- **SIN Numbers**: Formatted as `###-###-###` or `### ### ###`
- **Money Values**: Random amounts with variable formatting (commas, decimals)
- **Signatures**: Derived from names (e.g., "John Doe" → "J. Doe" or "John D.")

**Income Fields:**
- 30% chance of being filled
- If filled, 80% chance of non-zero value
- Uses `generate_money_value()` for realistic monetary amounts

**Output:** Python dictionary mapping field names to values (strings, booleans, or None)

### Step 2: Handwriting Image Generation (`generate_text_image.py`)

The system uses an optimized batch approach:

1. **Collect All Texts:**
   - Iterates through all form fields
   - Collects all text values that need handwriting generation
   - Creates mapping from field names to text indices

2. **Batch HTTP Request to Deno Service:**
   ```python
   POST http://localhost:8000/generate-batch
   Body: {"texts": ["John Doe", "123-456-7890", "X", ...]}
   ```

3. **Deno Service Processing (`handwriting-generator/main.ts`):**
   - **Batch Endpoint**: Receives array of texts via POST request
   - **Parallel Workers**: Distributes work across Deno Web Workers
   - **Worker Processing** (`handwriting-generator/worker.ts`):
     - Each worker processes texts in parallel
     - Calls `handwritten.js` library for each text
     - Returns base64-encoded PNG images
   - **Response Format**: `{"images": ["base64...", "base64...", ...]}`
   - **Fallback**: If batch fails, falls back to individual requests

4. **Image Processing:**
   - Decodes base64 to PNG bytes for each image
   - Converts to PIL Image (RGBA format)
   - **Crops to text bounds** using `crop_to_text()`:
     - Uses NumPy to find non-background pixels (RGB > 180 threshold)
     - Calculates bounding box of text content
     - Removes excess white space around text

**Output:** List of PIL Image objects with transparent backgrounds, cropped to text content

### Step 3: Form Composition (`build_test_form.py`)

The `build_test_form()` function orchestrates the composition:

1. **Load Template:**
   - Opens `template.jpg` as base image
   - Loads `template.json` containing field annotations

2. **Annotation Lookup:**
   - `template.json` uses COCO annotation format:
     ```json
     {
       "categories": [{"id": 1, "name": "name"}, ...],
       "annotations": [{"category_id": 1, "bbox": [x, y, width, height]}, ...]
     }
     ```
   - Maps category names to bounding boxes (x, y, width, height)

3. **Field Processing Loop:**
   For each category in the template:
   - Retrieves value from generated data
   - Gets bounding box from annotation
   - Determines field type (checkbox vs text)

4. **Checkbox Rendering:**
   - If value is `True`:
     - Generates handwritten "X" image
     - Scales to 70% of checkbox bbox size
     - Centers within checkbox area
     - Pastes with alpha transparency

5. **Text Field Rendering:**
   - Generates handwritten text image
   - Applies field-specific scaling rules:

   **Special Cases:**
   - **`explain_changes`**: Max 600×200px, maintains aspect ratio
   - **Income fields** (`income*`): Fixed 32px height, 5% horizontal padding
   - **Other fields**: Fixed 32px height, 30% reserved for label, 2% horizontal padding

   **Scaling Algorithm:**
   ```python
   # Calculate scale to fit within available space
   scale = min(available_width / orig_width, available_height / orig_height)
   new_width = orig_width * scale
   new_height = orig_height * scale
   ```

   **Positioning:**
   - Centers text within bounding box
   - Accounts for padding and label offsets
   - Uses alpha mask for transparent background

6. **Image Composition:**
   - Pastes each text/checkbox image onto template
   - Uses PIL's `paste()` with alpha mask for transparency
   - Maintains original template quality

7. **Output:**
   - Saves composed image as `output/form_image_{number}.jpg`
   - Saves data as `output/form_data_{number}.json`

## How Text is Drawn on the Form

### Coordinate System
- Origin (0,0) is top-left corner
- X increases rightward, Y increases downward
- Bounding boxes: `[x, y, width, height]` where (x,y) is top-left corner

### Positioning Algorithm

1. **Get Bounding Box:**
   ```python
   bbox = annotation['bbox']  # [x, y, width, height]
   bbox_x, bbox_y = bbox[0], bbox[1]
   bbox_width, bbox_height = bbox[2], bbox[3]
   ```

2. **Calculate Available Space:**
   - Subtract padding from bbox dimensions
   - Account for label space (30% for regular fields)
   - Result: `available_width`, `available_height`

3. **Scale Text Image:**
   - Calculate scale factor to fit available space
   - Maintain aspect ratio
   - Apply scale: `new_size = original_size * scale`

4. **Calculate Paste Position:**
   ```python
   paste_x = bbox_x + padding + (available_width - new_width) // 2
   paste_y = bbox_y + label_offset + (available_height - new_height) // 2
   ```

5. **Composite:**
   ```python
   template_image.paste(text_img, (paste_x, paste_y), mask=text_img)
   ```
   - `mask=text_img` preserves transparency (alpha channel)
   - Only non-transparent pixels are pasted

### Field-Specific Rendering Rules

**Checkboxes:**
- Scale: 70% of bbox size
- Position: Centered in bbox
- Content: Handwritten "X" character

**Income Fields:**
- Height: Fixed 32px
- Padding: 5% horizontal padding
- Alignment: Centered horizontally, vertically centered

**Regular Text Fields:**
- Height: Fixed 32px
- Label Space: 30% of bbox height reserved for label
- Padding: 2% horizontal padding
- Alignment: Centered in available space (below label)

**Explain Changes Field:**
- Max Size: 600×200px
- Scaling: Maintains aspect ratio, fits within max size
- Alignment: Centered in bbox

## File Structure

```
Form-Generation/
├── build_test_form.py          # Main orchestration script (with batch support)
├── generate_form_data.py       # Data generation logic
├── generate_text_image.py      # Handwriting API client & image processing
│                                # - Batch API support
│                                # - Connection pooling (Session)
│                                # - LRU caching
│                                # - Performance timing logs
├── template.jpg                # Base form template image
├── template.json               # Field annotations (COCO format)
├── requirements                # Python dependencies
├── output/                     # Generated forms and data
│   ├── form_data_0.json
│   └── form_image_0.jpg
└── handwriting-generator/       # Deno service
    ├── main.ts                 # HTTP server with batch endpoint
    ├── worker.ts               # Worker script for parallel generation
    └── dev_deps.ts             # Development dependencies
```

## Template Annotation Format

The `template.json` file uses COCO (Common Objects in Context) annotation format:

```json
{
  "categories": [
    {"id": 1, "name": "name"},
    {"id": 2, "name": "phone"},
    ...
  ],
  "annotations": [
    {
      "id": 0,
      "category_id": 1,
      "bbox": [x, y, width, height],
      "area": 12345.67
    },
    ...
  ]
}
```

- **categories**: Maps category IDs to field names
- **annotations**: Defines bounding boxes for each field
- **bbox**: `[x, y, width, height]` in pixels
- Field names in categories must match keys in generated data dictionary

## Handwriting Service Details

### API Endpoints

#### Single Text Generation (Backward Compatible)
- **URL**: `http://localhost:8000/generate`
- **Method**: POST
- **Request Body**: `{"text": "string to render"}`
- **Response**: `{"image": "base64-encoded-png"}`
- **Use Case**: Individual text generation, fallback when batch fails

#### Batch Generation (Optimized)
- **URL**: `http://localhost:8000/generate-batch`
- **Method**: POST
- **Request Body**: `{"texts": ["text1", "text2", ...]}`
- **Response**: `{"images": ["base64...", "base64...", ...]}`
- **Use Case**: Generating multiple texts efficiently
- **Performance**: Uses parallel Deno Workers for concurrent generation

### handwritten.js Library
- Generates handwritten-style text using SVG paths
- Converts to PNG format for Python compatibility
- Each call produces slightly different handwriting style
- Supports any ASCII text input
- CPU-bound operation (benefits from parallel workers)

### Service Architecture

**Main Process** (`main.ts`):
- HTTP server handling requests
- Routes to appropriate endpoint
- Manages worker pool for batch requests

**Worker Process** (`worker.ts`):
- Handles individual text generation
- Runs in parallel with other workers
- Communicates via message passing

**Worker Pool**:
- Automatically sized based on CPU cores (`navigator.hardwareConcurrency`)
- Distributes work round-robin across workers
- Cleans up after batch completion

### Service Startup
```bash
cd handwriting-generator
deno task start
```

The service runs continuously, handling batch requests with parallel workers for optimal performance.

## Image Processing Details

### Text Cropping (`crop_to_text()`)

Purpose: Remove excess white space around handwritten text

Algorithm:
1. Convert image to RGBA format
2. Create NumPy array from image
3. Identify non-background pixels:
   - Background threshold: RGB > 180 (light gray/white)
   - Alpha > 0 (visible pixels)
4. Find bounding box of non-background pixels
5. Crop image to bounding box

Benefits:
- Reduces image size
- Improves scaling accuracy
- Better positioning on form

### Alpha Compositing

When pasting text onto template:
- Uses RGBA format (Red, Green, Blue, Alpha)
- Alpha channel controls transparency
- `mask=text_img` parameter uses alpha channel as mask
- Only opaque pixels overwrite template pixels
- Transparent pixels preserve template background

## Usage Example

```bash
# 1. Start handwriting service
cd handwriting-generator
deno task start

# 2. Generate forms (in another terminal)
cd Form-Generation
python build_test_form.py 5  # Generate 5 forms
```

This will:
1. Generate 5 sets of form data
2. Create handwritten images for each text field
3. Compose images onto template
4. Save 5 form images and 5 JSON data files

## Extending the System

### Adding New Field Types

1. **Add to `generate_form_data.py`:**
   ```python
   test_data['new_field'] = generate_new_value()
   ```

2. **Add annotation to `template.json`:**
   ```json
   {
     "categories": [{"id": N, "name": "new_field"}],
     "annotations": [{"category_id": N, "bbox": [x, y, w, h]}]
   }
   ```

3. **Add rendering rules to `build_test_form.py`** (if special handling needed)

### Customizing Field Rendering

Modify the scaling/positioning logic in `build_test_form.py`:

```python
elif name == 'your_field_name':
    # Custom scaling rules
    fixed_height = 40
    # ... custom logic
```

### Changing Handwriting Style

The handwriting style is determined by `handwritten.js`. To change:
- Modify the Deno service to use different parameters
- Or replace `handwritten.js` with alternative library
- Update API response format if needed

## Performance Optimizations

The system has been optimized for performance with several key improvements:

### Batch API (`/generate-batch`)
- **Purpose**: Reduces HTTP overhead by generating multiple images in a single request
- **Implementation**: Accepts array of texts, returns array of images
- **Benefit**: Eliminates N HTTP round-trips, reducing per-text overhead from ~2.1s to ~0.8s
- **Usage**: Automatically used by `build_test_form.py` when `use_batch=True`

### Connection Pooling
- **Implementation**: Uses `requests.Session()` for HTTP connection reuse
- **Benefit**: Eliminates TCP connection overhead for subsequent requests
- **Location**: `generate_text_image.py` - `get_session()` function

### LRU Caching
- **Implementation**: `@lru_cache(maxsize=100)` decorator on handwriting generation
- **Benefit**: Caches repeated strings (e.g., "X", common dates) to avoid redundant generation
- **Location**: `generate_text_image.py` - `_generate_handwriting_image_cached()`

### Parallel Generation (Deno Workers)
- **Implementation**: Uses Deno Web Workers to parallelize CPU-bound handwriting generation
- **Benefit**: Utilizes multiple CPU cores for concurrent image generation
- **Configuration**: Automatically detects CPU cores (`navigator.hardwareConcurrency`)
- **Location**: `handwriting-generator/worker.ts` and batch endpoint in `main.ts`

### Performance Metrics
- **Before optimization**: ~2.1s per text × 22 fields = ~46s (timed out)
- **After batch API**: ~0.8s per text in batch, ~35s total per form
- **After workers**: Further reduction depending on CPU cores available
- **Timing logs**: Detailed performance breakdown available in console output

### Performance Considerations

- **Handwriting Service**: Now uses parallel workers for CPU-bound generation
- **Image Processing**: NumPy operations are efficient for cropping
- **Composition**: PIL paste operations are fast for single images
- **Bottleneck**: CPU-bound handwriting generation (mitigated by workers)

For further optimization:
- Increase worker count if more CPU cores available
- Expand cache size for more repeated values
- Pre-generate common handwriting images

## Error Handling

The system includes comprehensive error handling:

- **Missing template files**: Clear error messages
- **HTTP errors from handwriting service**: Detailed error logging with status codes
- **Batch API failures**: Automatic fallback to individual requests
- **Invalid JSON responses**: Error messages with raw response for debugging
- **Image processing failures**: Graceful error handling
- **Missing field annotations**: Warnings printed, processing continues
- **Worker failures**: Individual worker errors don't crash batch processing

All errors are logged to console with descriptive messages and timing information.

## Performance Monitoring

The system includes detailed timing logs:

- **Per-field timing**: HTTP request time, decode time, total time
- **Batch timing**: Total batch time, average per-text time
- **Image processing**: PIL operations, cropping operations
- **Form-level timing**: Total form processing time, breakdown by stage
- **Overall timing**: Multi-form generation statistics

Example output:
```
[Form 0] Generating 36 handwriting images in batch...
  [Batch Timing] 36 texts: HTTP=28.570s, decode=0.007s, total=28.577s (0.794s per text)
[Form 0] Batch generation completed in 28.577s
[Form 0] Total form processing time: 34.605s (save: 0.013s)
[Overall] Generated 1 form(s) in 34.618s (avg: 34.618s per form)
```
