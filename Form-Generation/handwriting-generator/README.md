
# Handwriting Generator Deno Service

This directory contains a Deno-based HTTP service for generating handwriting images from text using handwritten.js.

## Requirements

- [Deno](https://deno.land/) (v1.28+)

## How to Run the Service

1. **Install Deno** (if not already installed):
   - See <https://deno.land/manual/getting_started/installation>

2. **Navigate to this service directory:**

   ```sh
   cd Form-Generation/handwriting-generator
   ```

3. **Start the service:**

   ```sh
   deno task start
   ```

   - The service will start on [http://localhost:8000](http://localhost:8000)

4. **Test the service:**
   - Send a POST request to `http://localhost:8000/generate` with JSON body:

     ```json
     { "text": "Your text here" }
     ```

   - The response will be a JSON object with a base64-encoded PNG image:

     ```json
     { "image": "data:image/png;base64,..." }
     ```

## Example: Python Client

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

---
For more details, see the code in `main.ts`.
