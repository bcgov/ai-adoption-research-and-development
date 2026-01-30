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
    API key and endpoint are loaded from .env file (AZURE_DOCUMENT_INTELLIGENCE_TRAIN_ENDPOINT, AZURE_DOCUMENT_INTELLIGENCE_API_KEY).
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
    # The result id is the last part of the operation-location URL
    result_id = operation_location.rstrip("/").split("/")[-1]
    with open(output_txt_path, "a") as out:
        out.write(result_id + "\n")
    return result_id


# Run analyze_all_jpgs_in_output_folder if this script is executed directly
if __name__ == "__main__":
    analyze_all_jpgs_in_output_folder()
