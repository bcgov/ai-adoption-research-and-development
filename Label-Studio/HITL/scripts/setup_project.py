#!/usr/bin/env python3
# HITL/scripts/setup_project.py
"""One-time setup script for HITL OCR project."""

import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.label_studio_client import HITLClient


def wait_for_label_studio(url: str, max_retries: int = 30, delay: int = 2):
    """Wait for Label Studio to be ready."""
    import requests

    print(f"Waiting for Label Studio at {url}...")

    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print("Label Studio is ready!")
                return True
        except requests.exceptions.RequestException:
            pass

        print(f"  Attempt {i+1}/{max_retries}...")
        time.sleep(delay)

    print("Label Studio not available")
    return False


def main():
    """Set up the HITL OCR project."""
    # Configuration
    project_name = "HITL OCR Review"
    project_description = "Human-in-the-loop review of low-confidence OCR results"

    label_studio_url = os.environ.get('LABEL_STUDIO_URL', 'http://localhost:8080')
    ml_backend_url = os.environ.get('ML_BACKEND_URL', 'http://ml_backend:9090')
    webhook_url = os.environ.get('WEBHOOK_URL', 'http://webhook_receiver:8000/webhook/annotation')

    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config',
        'labeling_config.xml'
    )

    # Wait for Label Studio
    if not wait_for_label_studio(label_studio_url):
        print("ERROR: Label Studio is not available. Make sure docker-compose is running.")
        sys.exit(1)

    # Initialize client
    try:
        client = HITLClient(url=label_studio_url)
    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nTo get your API key:")
        print("1. Log in to Label Studio at http://localhost:8080")
        print("2. Go to Account & Settings > Access Token")
        print("3. Copy the token and set: export LABEL_STUDIO_API_KEY=<your-token>")
        sys.exit(1)

    print(f"\nCreating project: {project_name}")
    project_id = client.create_project(
        name=project_name,
        labeling_config_path=config_path,
        description=project_description
    )
    print(f"  Project ID: {project_id}")

    print(f"\nConnecting ML backend: {ml_backend_url}")
    try:
        ml_backend_id = client.configure_ml_backend(
            project_id=project_id,
            ml_backend_url=ml_backend_url
        )
        print(f"  ML Backend ID: {ml_backend_id}")
    except Exception as e:
        print(f"  WARNING: Could not connect ML backend: {e}")
        print("  You may need to connect it manually in Label Studio settings")
        ml_backend_id = None

    print(f"\nConfiguring webhook: {webhook_url}")
    try:
        webhook_id = client.configure_webhook(
            project_id=project_id,
            webhook_url=webhook_url
        )
        print(f"  Webhook ID: {webhook_id}")
    except Exception as e:
        print(f"  WARNING: Could not configure webhook: {e}")
        print("  You may need to configure it manually in Label Studio settings")

    print("\n" + "="*50)
    print("Setup complete!")
    print("="*50)
    print(f"\nProject URL: {label_studio_url}/projects/{project_id}")
    print("\nNext steps:")
    print("1. Run: python scripts/submit_sample_tasks.py")
    print("2. Open Label Studio and start annotating")


if __name__ == '__main__':
    main()
