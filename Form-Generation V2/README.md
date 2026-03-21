# Form Generation Pipeline

This directory contains scripts and tools for generating synthetic form images with handwritten text, using Python and a Node-based handwriting service.

## 1. Python Environment Setup

1. **Create and activate a virtual environment:**

 ```sh
 python3 -m venv .venv
 source .venv/bin/activate
 ```

1. **Install dependencies:**

 ```sh
 pip install -r requirements
 ```

## 2. Start the Handwriting Generator Service

The form generation pipeline relies on a Node service to generate handwriting images from text.

1. **Start the server** (from this directory):

 ```sh
 ./start_handwriting_server.sh
 ```

   Or from the service directory:

 ```sh
 cd handwriting-generator
 node server-node.js
 ```

- The service runs at <http://localhost:8000>
- **Optional**: To tune how many images are generated in parallel per batch, set `HANDWRITING_WORKERS` when starting the server (default is 2× CPU cores). See `handwriting-generator/README.md` for details.

## 3. Generate Form Images

1. **Run the build_test_form.py script:**

 ```sh
 python build_test_form.py <num>
 ```

- Replace `<num>` with the number of forms you want to generate.

- For each iteration, this will:
  - Generate random form data and save it as `output/form_data_{index}.json`
  - Generate a composed form image as `output/form_image_{index}.jpg`

### Complete Fill Mode

To generate forms where all fields are filled with proper data, use the `--complete-fill` (or `-c`) flag:

 ```sh
 python build_test_form.py <num> --complete-fill
 ```

When complete fill mode is enabled:
- All income fields are populated with non-zero monetary values
- Spouse information is always included (spouse fields are always filled)
- All applicable fields contain realistic data
- The "explain changes" field contains longer text that fills the text box (single-pass with configurable line width)

This is useful for generating forms with comprehensive data for testing scenarios where you need fully populated forms.

### Parallel Generation

There are two levels of parallelism:

1. **Form-level (Python)** – How many forms are built at the same time.
   - **Default**: Up to 4 forms generated concurrently.
   - **Control**: Set `MAX_PARALLEL_FORMS`:
     ```sh
     MAX_PARALLEL_FORMS=3 python build_test_form.py 10  # 10 forms, 3 at a time
     MAX_PARALLEL_FORMS=1 python build_test_form.py 5   # Sequential (no form parallelism)
     MAX_PARALLEL_FORMS=8 python build_test_form.py 20  # 8 forms at a time
     ```

2. **Batch-level (Node server)** – How many handwriting images are generated in parallel inside each batch request.
   - **Default**: 2× CPU cores (reported in server startup logs).
   - **Control**: Start the server with `HANDWRITING_WORKERS` (e.g. `HANDWRITING_WORKERS=8 node server-node.js`). See `handwriting-generator/README.md`.

**Performance** (with default server and form parallelism):
- Single form: ~8–9s (batch + compose)
- 4 forms in parallel: ~13–14s total (~3–4s per form)
- 10 forms: ~30s total with default parallelism

## Notes

- The script uses the Node handwriting service for handwriting image generation. Make sure it is running before executing the Python script.
- This case is highly specialized to the Montly Report Form, but components outside of the `build_test_form.py` file should all be reusable for other forms.

## Previous Attempts

I wanted to note some previous attempts at the text image generation.

### TRDG

First I tried using [Text Recognition Data Generator](https://github.com/Belval/TextRecognitionDataGenerator).

It was a pain to set up, as the dependencies are all very outdated at this point. I also needed to install some system-wide dependencies, which was unwelcome. If you decide to try this again, you'll need to do this:

   ```sh
   brew install freetype pkg-config
   ```

In the end, the results were not very reliable. Sometimes things would look alright but often it would be illegible.

I also needed to modify the source code to remove a check in the data generator for the writing being too close to the background. It would often declare its own output a failure, even when I would have been happy to use it.

### handwritting-synthesis

The original is [here](https://github.com/sjvasquez/handwriting-synthesis), but I ended up using this [containerized version](https://github.com/cdeckert/handwriting-synthesis/tree/codex/dockerize-project?tab=readme-ov-file) instead.

I really liked this one. You can see a demo here: [calligrapher.ai](https://www.calligrapher.ai/).

The output from this one was my favourite, and it gave SVG results, which I preferred even though it meant extra conversion afterwards.

The problem was that it had a strange issue with only being trained on certain characters. See this error:

 > Invalid character X detected in line 0. Valid character set is {'q', 't', '"', ',', '1', ' ', 'N', '4', 'J', 'g', 'G', 'F', 'p', 'H', 'K', ';', 'E', 'o', 'R', '!', 'e', 'z', '2', '(', ')', ':', 'L', 'l', 'M', 'V', '5', 'Y', 'm', 'n', 'v', '\x00', 'k', 'S', 'u', "'", 'I', '8', '?', 'C', '3', '#', 'i', '.', 'U', 'c', 'W', 'f', 's', 'D', 'd', '0', 'P', 'b', 'j', 'r', 'a', 'T', 'O', 'B', '6', 'h', 'y', 'x', '9', 'w', 'A', '7', '-'}

It made generating acceptable test data very restricting, so I moved away from it.

### handwritten.js

Eventually, I settled for `handwritten.js`.

<https://github.com/alias-rahil/handwritten.js>

It is a little same-y between each generation, but it was extremely reliable and flexible during testing.

You can also run this in the command line for testing purposes.
