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

For each text value in the generated data:

1. **HTTP Request to Deno Service:**
   ```python
   POST http://localhost:8000/generate
   Body: {"text": "John Doe"}
   ```

2. **Deno Service Processing (`handwriting-generator/main.ts`):**
   - Receives text via POST request
   - Calls `handwritten.js` library with text
   - Returns base64-encoded PNG image
   - Response format: `{"image": "data:image/png;base64,..."}`

3. **Image Processing:**
   - Decodes base64 to PNG bytes
   - Converts to PIL Image (RGBA format)
   - **Crops to text bounds** using `crop_to_text()`:
     - Uses NumPy to find non-background pixels (RGB > 180 threshold)
     - Calculates bounding box of text content
     - Removes excess white space around text

**Output:** PIL Image object with transparent background, cropped to text content

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
├── build_test_form.py          # Main orchestration script
├── generate_form_data.py       # Data generation logic
├── generate_text_image.py      # Handwriting API client & image processing
├── template.jpg                # Base form template image
├── template.json               # Field annotations (COCO format)
├── requirements                # Python dependencies
├── output/                     # Generated forms and data
│   ├── form_data_0.json
│   └── form_image_0.jpg
└── handwriting-generator/       # Deno service
    ├── main.ts                 # HTTP server
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

### API Endpoint
- **URL**: `http://localhost:8000/generate`
- **Method**: POST
- **Request Body**: `{"text": "string to render"}`
- **Response**: `{"image": "base64-encoded-png"}`

### handwritten.js Library
- Generates handwritten-style text using SVG paths
- Converts to PNG format for Python compatibility
- Each call produces slightly different handwriting style
- Supports any ASCII text input

### Service Startup
```bash
cd handwriting-generator
deno task start
```

The service runs continuously, handling multiple requests sequentially.

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

## Performance Considerations

- **Handwriting Service**: Single-threaded, processes requests sequentially
- **Image Processing**: NumPy operations are efficient for cropping
- **Composition**: PIL paste operations are fast for single images
- **Bottleneck**: HTTP requests to handwriting service (network latency)

For batch generation, consider:
- Parallelizing handwriting requests (requires service modifications)
- Caching common text values
- Pre-generating handwriting images

## Error Handling

The system includes error handling for:
- Missing template files
- HTTP errors from handwriting service
- Invalid JSON responses
- Image processing failures
- Missing field annotations (warnings printed)

All errors are logged to console with descriptive messages.
