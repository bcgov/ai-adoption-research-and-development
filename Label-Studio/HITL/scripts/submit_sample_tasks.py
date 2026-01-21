#!/usr/bin/env python3
# HITL/scripts/submit_sample_tasks.py
"""Submit sample images as tasks to Label Studio."""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.label_studio_client import HITLClient


def main():
    """Submit sample images from the images directory."""
    label_studio_url = os.environ.get('LABEL_STUDIO_URL', 'http://localhost:8080')

    images_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'images'
    )

    # Get project ID from command line or find the first project
    project_id = None
    if len(sys.argv) > 1:
        project_id = int(sys.argv[1])

    # Initialize client
    try:
        client = HITLClient(url=label_studio_url)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Find project if not specified
    if project_id is None:
        projects = client.client.get_projects()
        if not projects:
            print("ERROR: No projects found. Run setup_project.py first.")
            sys.exit(1)
        project_id = projects[0].id
        print(f"Using project: {projects[0].title} (ID: {project_id})")

    # Check for images
    if not os.path.exists(images_dir):
        print(f"ERROR: Images directory not found: {images_dir}")
        sys.exit(1)

    image_files = [
        f for f in os.listdir(images_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ]

    if not image_files:
        print(f"No images found in {images_dir}")
        print("Add some .jpg or .png files to test the OCR workflow")
        sys.exit(0)

    print(f"\nFound {len(image_files)} images in {images_dir}")
    print("Submitting tasks...")

    task_ids = client.create_tasks_from_directory(
        project_id=project_id,
        directory=images_dir
    )

    print(f"\nCreated {len(task_ids)} tasks:")
    for i, (filename, task_id) in enumerate(zip(image_files, task_ids)):
        print(f"  {i+1}. {filename} -> Task ID: {task_id}")

    print(f"\nOpen Label Studio to start annotating:")
    print(f"  {label_studio_url}/projects/{project_id}/data")


if __name__ == '__main__':
    main()
