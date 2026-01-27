def analyze_all_jpgs_in_output_folder(output_folder="../output"):
    """
    Loops through all .jpg files in the specified output folder and calls analyze_document_async for each.
    Saves each result id to a text file named <image>.result_id.txt in the same folder.
    """
    jpg_files = sorted(
        [f for f in os.listdir(output_folder) if f.lower().endswith(".jpg")]
    )
    result_ids = []
    for jpg in jpg_files:
        jpg_path = os.path.join(output_folder, jpg)
        try:
            result_id = analyze_document_async(jpg_path)
            result_ids.append(result_id)
            print(f"Processed {jpg}: result id {result_id}")
        except Exception as e:
            print(f"Error processing {jpg}: {e}")
    # Save all result ids in order to a single file
    result_txt = os.path.join(output_folder, "result_id.txt")
    with open(result_txt, "w") as out:
        for rid in result_ids:
            out.write(rid + "\n")


import os
import requests
from dotenv import load_dotenv


def analyze_document_async(file_path, output_txt_path="result_id.txt"):
    """
    Loads a file, sends it to Azure Document Intelligence async API, returns the result id, and saves it to a text file.
    API key and endpoint are loaded from .env file (DOCUMENT_INTELLIGENCE_ENDPOINT, DOCUMENT_INTELLIGENCE_KEY).
    """
    load_dotenv()
    endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
    api_key = os.getenv("DOCUMENT_INTELLIGENCE_KEY")
    if not endpoint or not api_key:
        raise ValueError(
            "Missing DOCUMENT_INTELLIGENCE_ENDPOINT or DOCUMENT_INTELLIGENCE_KEY in .env"
        )

    url = f"{endpoint}/formrecognizer/documentModels/prebuilt-document:analyze?api-version=2023-07-31"
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Content-Type": "image/jpeg",
    }
    with open(file_path, "rb") as f:
        data = f.read()
    response = requests.post(url, headers=headers, data=data)
    if response.status_code != 202:
        raise Exception(f"Request failed: {response.status_code} {response.text}")
    operation_location = response.headers.get("operation-location")
    if not operation_location:
        raise Exception("No operation-location header in response")
    # The result id is the last part of the operation-location URL
    result_id = operation_location.rstrip("/").split("/")[-1]
    with open(output_txt_path, "a") as out:
        out.write(result_id + "\n")
    return result_id
