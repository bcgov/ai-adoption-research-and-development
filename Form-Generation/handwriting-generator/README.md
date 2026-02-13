
# Handwriting Generator Service

This directory contains HTTP services for generating handwriting images from text using handwritten.js.

## Option A: Node server (recommended for form generation)

Uses the **local patched** `Form-Generation/handwritten.js` clone, which supports the `lineWidth` option for the explain_changes field (more words per line).

1. **Install dependencies in the local handwritten.js clone** (once):

   ```sh
   cd Form-Generation/handwritten.js && npm install && cd ../handwriting-generator
   ```

2. **Start the Node server:**

   ```sh
   cd Form-Generation/handwriting-generator
   node server-node.js
   ```

   - Listens on [http://localhost:8000](http://localhost:8000), same API as the Deno service.

## Option B: Deno service

Uses the stock npm `handwritten.js` (no `lineWidth`; explain_changes will wrap at ~5 words per line).

- **Requirements:** [Deno](https://deno.land/) (v1.28+)
- **Run:** from this directory, `deno task start`
- Service starts on [http://localhost:8000](http://localhost:8000)

## How to Run the Form (complete-fill)

1. Start either server (Node or Deno) on port 8000.
2. From `Form-Generation`:

   ```sh
   python build_test_form.py 1 --complete-fill
   ```

   Use the **Node server** if you want the explain_changes paragraph to use `lineWidth: 95` (patched local clone).

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
