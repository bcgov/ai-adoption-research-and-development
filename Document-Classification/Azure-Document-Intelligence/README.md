# Azure Document Intelligence - Training & Using a Classification Model

This sample code shows how to potentially train and use a classification model to classify documents. It uses Azure Document Intelligence to do so.

## 1. Populate the .env

Copy the file `.env.example` and populated with your own information for Document Intelligence and Azure Blob Storage.

## 2. Create Config File and Populate Relevant Folders

There's an `uploadConfigs.json` file that defines where the training files come from and what label the classifier should assign to them.

The structure looks like this:

```json
[
  { "label": "monthly-report", "fromFolder": "./report_documents", "blobFolder": "monthly-reports" },
  { "label": "other", "fromFolder": "./other_documents", "blobFolder": "other" }
]
```

At least two different labels are needed. The `label` is what the classifier will use to predict future classifications. The `fromFolder` is where in your local system these files come from. The `blobFolder` is a folder in your blob storage where they will be deposited temporarily for training.

All files of one label must go in the same blob folder, and only one label type should go into a single blob folder. No mixing and matching, just one label for one folder.

Ensure that you populate your local folders with adequate training data. See the `Document-Classification/LayoutLM` folder for more information on where you can generate or download sample files.

## 3. Run the Script

This project was built using Deno.

To run the main file, use `deno task launch`.

There's a hardcoded couple of file paths that I used for testing in the `main.ts` file. You may want to change those depending on your training data.

## 4. Use the Demo

Run `deno task demo` to start the demo server. By default, it's available at `http://localhost:8081/demo/`.

In the demo, you can upload an image for classification, and it will show both the image and results in the browser.
