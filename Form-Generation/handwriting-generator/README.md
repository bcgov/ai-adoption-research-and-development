# Handwriting Generator Service

Node HTTP service for generating handwriting images from text using the local patched **handwritten.js** (supports `lineWidth` for the explain_changes field).

## Setup

1. **Install dependencies in the local handwritten.js clone** (once):

   ```sh
   cd Form-Generation/handwritten.js && npm install && cd ../handwriting-generator
   ```

2. **Start the server:**

   ```sh
   cd Form-Generation/handwriting-generator
   node server-node.js
   ```

   Listens on [http://localhost:8000](http://localhost:8000).

## Performance and tuning

The server uses a **worker thread pool** to generate multiple handwriting images in parallel within each batch request:

- **Default**: Pool size = 2× CPU cores (minimum 1). The actual size used for a request is `min(batch size, pool size)`.
- **Override**: Set the `HANDWRITING_WORKERS` environment variable to fix the pool size:
  ```sh
  HANDWRITING_WORKERS=8 node server-node.js
  ```
- At startup, the server logs the effective worker count (default or from `HANDWRITING_WORKERS`).
- Repeated texts (with no `options`) are served from an in-memory cache, which speeds up multi-form runs that share content (e.g. many "X" checkmarks).

## Running form generation

1. Start the server (see above), then from `Form-Generation`:

   ```sh
   python build_test_form.py 1 --complete-fill
   ```

   To generate multiple forms (multi-page) in parallel:
   ```sh
   python build_test_form.py 4              # 4 forms, default parallelism
   MAX_PARALLEL_FORMS=8 python build_test_form.py 8 --complete-fill
   ```
   Form-level parallelism is controlled by `MAX_PARALLEL_FORMS` (see Form-Generation/README.md).

   Or use `./start_handwriting_server.sh` from `Form-Generation` to start the server in one terminal, then run the Python script in another.

## API

- **POST /generate** – Single text: `{ "text": "Your text here" }` → `{ "image": "data:image/png;base64,..." }`
- **POST /generate-batch** – Batch: `{ "texts": ["...", "..."], "options": { "lineWidth": 95 } }` → `{ "images": ["data:image/png;base64,...", ...] }`

## Example: Python client

```python
import requests
import base64

resp = requests.post(
    'http://localhost:8000/generate',
    json={'text': 'Hello world!'}
)
if resp.status_code == 200:
    b64 = resp.json()["image"]
    if b64.startswith("data:image"):
        b64 = b64.split(",", 1)[-1]
    with open('output.png', 'wb') as f:
        f.write(base64.b64decode(b64))
else:
    print(resp.json())
```

For more details, see `server-node.js`.
