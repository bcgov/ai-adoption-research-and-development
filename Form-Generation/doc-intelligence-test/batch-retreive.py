import os
import requests
from dotenv import load_dotenv


def retrieve_results(result_id_file, results_folder="results"):
    """
    Reads each result id from the result_id_file, retrieves the result from Azure Document Intelligence,
    and saves each result JSON to its own file in the results folder.
    """
    load_dotenv()
    endpoint = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
    api_key = os.getenv("DOCUMENT_INTELLIGENCE_KEY")
    if not endpoint or not api_key:
        raise ValueError(
            "Missing DOCUMENT_INTELLIGENCE_ENDPOINT or DOCUMENT_INTELLIGENCE_KEY in .env"
        )

    if not os.path.exists(results_folder):
        os.makedirs(results_folder)

    with open(result_id_file, "r") as f:
        result_ids = [line.strip() for line in f if line.strip()]

    for result_id in result_ids:
        url = f"{endpoint}/formrecognizer/documentModels/prebuilt-document/analyzeResults/{result_id}?api-version=2023-07-31"
        headers = {
            "Ocp-Apim-Subscription-Key": api_key,
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(
                f"Failed to retrieve result {result_id}: {response.status_code} {response.text}"
            )
            continue
        result_json = response.json()
        out_path = os.path.join(results_folder, f"{result_id}.json")
        with open(out_path, "w") as out:
            import json

            json.dump(result_json, out, indent=2)
        print(f"Saved result {result_id} to {out_path}")


# Example usage:
# retrieve_results("../output/result_id.txt", "results")
