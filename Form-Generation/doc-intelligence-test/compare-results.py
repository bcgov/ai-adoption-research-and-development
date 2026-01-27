import os
import json


def load_model_config(config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
    return config["fields"]


def load_truths(truths_folder):
    """
    Loads all .json files in the truths_folder as known truths.
    Returns a dict: {basename: {key: value, ...}}
    """
    truths = {}
    for fname in sorted(os.listdir(truths_folder)):
        if fname.endswith(".json"):
            base = os.path.splitext(fname)[0]
            with open(os.path.join(truths_folder, fname), "r") as f:
                truths[base] = json.load(f)
    return truths


def load_results(results_folder):
    """
    Loads all .json files in the results_folder as returned by Document Intelligence.
    Returns a dict: {basename: {key: value, ...}}
    """
    results = {}
    for fname in sorted(os.listdir(results_folder)):
        if fname.endswith(".json"):
            base = os.path.splitext(fname)[0]
            with open(os.path.join(results_folder, fname), "r") as f:
                results[base] = json.load(f)
    return results


def compare_fields(model_fields, truth_dict, result_dict, key_map=None):
    """
    Compares expected fields to result fields, using key_map if provided.
    Returns a list of (field, truth, result, match) tuples.
    """
    comparison = []
    for field in model_fields:
        truth_key = key_map[field] if key_map and field in key_map else field
        truth_val = truth_dict.get(truth_key)
        result_val = result_dict.get(field)
        match = truth_val == result_val
        comparison.append((field, truth_val, result_val, match))
    return comparison


def main():
    model_config_path = "../../DI-Template-Training/data/outputs/model_config.json"
    truths_folder = "../output"  # known truths
    results_folder = "results"  # document intelligence results

    model_fields = load_model_config(model_config_path)
    truths = load_truths(truths_folder)
    results = load_results(results_folder)

    # Optionally, define a key_map if truth keys differ from model fields
    key_map = None  # e.g., {'model_field': 'truth_field'}

    for base in truths:
        # Find corresponding result by index or name
        result = results.get(base)
        if not result:
            print(f"No result for {base}")
            continue
        # Flatten result fields if needed (customize as per actual result structure)
        result_fields = result.get("fields", result)
        comparison = compare_fields(model_fields, truths[base], result_fields, key_map)
        print(f"\nComparison for {base}:")
        for field, truth, found, match in comparison:
            print(f"  {field}: truth={truth!r}, result={found!r}, match={match}")


if __name__ == "__main__":
    main()
