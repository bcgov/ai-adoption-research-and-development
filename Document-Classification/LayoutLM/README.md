# LayoutLMv3 Document Classification Workflow

This experiment demonstrates the end-to-end workflow for document classification using LayoutLMv3. The steps include data preparation, model training, evaluation, and prediction.

## 1. Install Dependencies

Initialize and enter your virtual environment.

```sh
python -m venv .venv
source .venv/bin/activate
```

Use `pip` to install dependencies.

```sh
pip install -r requirements
```

## 2. Populate Image Folders

In this test, two folders were used:

- `report_documents`: This contains the sample monthly report forms. If you don't have your own, you can look to the `Form-Generation` folder in this repo to generate a sample set. This experiement used 100 generated forms.
- `other_documents`: Any assortment of other document types. We used the [FUNSD](https://guillaumejaume.github.io/FUNSD/) sample documents.

    ```ts
    @inproceedings{jaume2019,
        title = {FUNSD: A Dataset for Form Understanding in Noisy Scanned Documents},
        author = {Guillaume Jaume, Hazim Kemal Ekenel, Jean-Philippe Thiran},
        booktitle = {Accepted to ICDAR-OST},
        year = {2019}
    }
    ```

## 3. Prepare Training Data

```sh
python prepare_training_data.py
```

Run the `prepare_training_data.py` script to generate a `jsonl` file with sample training data. This requires that the image folders are created and populated.

By default, it will save the results in the `encoded_data.jsonl` file. This file can be deceptively large, and editors like VS Code may have difficulty opening it.

Currently, this file is hardcoded to apply one type of label to each folder. Either the document is a monthly report or it falls under the `other` type.

For consistency, this is using OCR results from the LayoutLMv3 model. Documentation suggests you should be able to provide your own OCR data, but attempts at this were not successful.

## 4. Train the Model

```sh
python train_model.py
```

This script applies the training data from the previous step in order to fine-tune the LayoutLMv3 model. It uses a hard-coded 90/10 split to assign training and evaulation data.

While only two labels are specified, real training data would ideally contain much more.

Training was done on a local system. This seemed sufficient for this experiment, and the results were good. Adjust the batch size and epoch count if you find additional tweaking is necessary.

It will output the results in a checkpoint folder within `/results`.

## 5. Evaluate the Model

```sh
python evaluate_model.py <model_path>
```

Take note of where your previous checkpoint was saved. The `model_path` argument should refer to the folder, not a specific file. For example, if the checkpoint folder is `checkpoint-1`, then your command would be `python evaluate_model results/checkpoint-1`.

The output should be a measurement of accuracy (1 is 100% accurate), along with other metrics.

## 6. Use the Model

```sh
python use_model.py <model_path> <image_path>
```

Finally, you can check the predicted label for a specific document with `use_model.py`. Provide the model path and image path as arguments.

The output will contain the predicted label for that document. As per the `labels_enum.py` file, the label is actually an integer value, with 0 representing a monthly report and 1 representing any other document.

## 7. Demo with Streamlit

There's a simple UI to demo your checkpoints.

Run `streamlit run streamlit_app.py`, and it should start in your browser.

In the UI, select your checkpoint and upload an image for the classification output.
