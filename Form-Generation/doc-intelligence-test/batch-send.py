def analyze_all_jpgs_in_output_folder(output_folder="../output"):
    """
    Loops through all .jpg files in the specified output folder and calls analyze_document_async for each.
    Each call appends a JSON line to results.jsonl in the same folder.
    """
    jpg_files = sorted(
        [f for f in os.listdir(output_folder) if f.lower().endswith(".jpg")]
    )
    for jpg in jpg_files:
        jpg_path = os.path.join(output_folder, jpg)
        try:
            analyze_document_async(jpg_path)
            print(f"Processed {jpg}")
        except Exception as e:
            print(f"Error processing {jpg}: {e}")


import os
import requests
from dotenv import load_dotenv
import json


def analyze_document_async(file_path):
    """
    Loads a file, sends it to Azure Document Intelligence async API, returns the operation-location.
    If output_folder is provided, appends a JSON line to results.jsonl with file name and operation_location.
    """
    load_dotenv()
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_TRAIN_ENDPOINT")
    api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
    if not endpoint or not api_key:
        raise ValueError(
            "Missing AZURE_DOCUMENT_INTELLIGENCE_TRAIN_ENDPOINT or AZURE_DOCUMENT_INTELLIGENCE_API_KEY in .env"
        )

    url = f"{endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze?api-version=2024-11-30"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }
    with open(file_path, "rb") as f:
        data = f.read()
    import base64

    base64_str = base64.b64encode(data).decode("utf-8")
    payload = {"base64Source": base64_str}
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 202:
        raise Exception(f"Request failed: {response.status_code} {response.text}")
    operation_location = response.headers.get("operation-location")
    if not operation_location:
        raise Exception("No operation-location header in response")
    # Append to results.jsonl if output_folder is provided

    result_jsonl = os.path.join("./", "results.jsonl")
    file_name = os.path.basename(file_path)
    with open(result_jsonl, "a") as out:
        out.write(
            json.dumps({"file": file_name, "operation_location": operation_location})
            + "\n"
        )
    return operation_location


# Run analyze_all_jpgs_in_output_folder if this script is executed directly
if __name__ == "__main__":
    analyze_all_jpgs_in_output_folder()
