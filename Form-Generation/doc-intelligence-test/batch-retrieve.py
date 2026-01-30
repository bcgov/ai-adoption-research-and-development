import os
import requests
from dotenv import load_dotenv


def retrieve_results(result_id_file, results_folder="results"):
    """
    Reads each line from results.jsonl, retrieves the result from Azure Document Intelligence,
    and saves each result JSON to a file named after the 'file' field in the results folder.
    """
    import json

    load_dotenv()
    api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
    if not api_key:
        raise ValueError("Missing AZURE_DOCUMENT_INTELLIGENCE_API_KEY in .env")

    if not os.path.exists(results_folder):
        os.makedirs(results_folder)

    with open(result_id_file, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                file_name = entry["file"]
                operation_location = entry["operation_location"]
            except Exception as e:
                print(f"Error parsing line: {line.strip()} - {e}")
                continue
            headers = {
                "api-key": api_key,
            }
            response = requests.get(operation_location, headers=headers)
            if response.status_code != 200:
                print(
                    f"Failed to retrieve result for {file_name}: {response.status_code} {response.text}"
                )
                continue
            result_json = response.json()
            out_path = os.path.join(
                results_folder, f"{os.path.splitext(file_name)[0]}.json"
            )
            with open(out_path, "w") as out:
                json.dump(result_json, out, indent=2)
            print(f"Saved result for {file_name} to {out_path}")


# Example usage:
if __name__ == "__main__":
    retrieve_results("results.jsonl", "results")
