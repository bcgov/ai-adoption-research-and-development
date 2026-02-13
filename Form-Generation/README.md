# Form Generation Pipeline

This directory contains scripts and tools for generating synthetic form images with handwritten text, using both Python and a Deno-based handwriting service.

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

The form generation pipeline relies on a Deno service to generate handwriting images from text.

1. **Navigate to the Deno service directory:**

 ```sh
 cd handwriting-generator
 ```

1. **Start the service:**

 ```sh
 deno task start
 ```

- The service will run at <http://localhost:8000>

## 3. Generate Form Images

1. **Run the build_test_form.py script:**

 ```sh
 python build_test_form.py <num>
 ```

- Replace `<num>` with the number of forms you want to generate.

- For each iteration, this will:
  - Generate random form data and save it as `output/form_data_{index}.json`
  - Generate a composed form image as `output/form_image_{index}.jpg`

### Parallel Generation

When generating multiple forms, they are generated in parallel for faster performance:

- **Default**: Up to 4 forms generated concurrently (optimal for Deno service)
- **Control**: Set `MAX_PARALLEL_FORMS` environment variable to change parallelism:
  ```sh
  MAX_PARALLEL_FORMS=3 python build_test_form.py 10  # Generate 10 forms, 3 at a time
  MAX_PARALLEL_FORMS=1 python build_test_form.py 5  # Disable parallelism (sequential)
  MAX_PARALLEL_FORMS=8 python build_test_form.py 20  # More aggressive parallelism
  ```

**Performance**:
- 3 forms: ~28s → ~10s (2.8× faster)
- 5 forms: ~48s → ~15s (3.2× faster)
- 10 forms: ~95s → ~30s (3.2× faster)

## Notes

- The script uses the Deno handwriting service for handwriting image generation. Make sure it is running before executing the Python script.
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
