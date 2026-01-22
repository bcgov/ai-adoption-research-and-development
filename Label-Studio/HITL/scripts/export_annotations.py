#!/usr/bin/env python3
# HITL/scripts/export_annotations.py
"""Export annotations from Label Studio to JSON/CSV for downstream processing."""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.label_studio_client import HITLClient


def extract_annotation_data(task: dict) -> list:
    """
    Extract structured data from a task's annotations.

    Returns list of dicts, one per annotated region.
    """
    results = []

    task_id = task['id']
    image_path = task.get('data', {}).get('image', '')

    for annotation in task.get('annotations', []):
        annotation_id = annotation['id']
        created_at = annotation.get('created_at', '')

        # Group results by region ID
        regions_by_id = {}
        for item in annotation.get('result', []):
            region_id = item.get('id')
            if not region_id:
                continue

            if region_id not in regions_by_id:
                regions_by_id[region_id] = {
                    'task_id': task_id,
                    'annotation_id': annotation_id,
                    'region_id': region_id,
                    'image_path': image_path,
                    'created_at': created_at,
                    'bbox_x': None,
                    'bbox_y': None,
                    'bbox_width': None,
                    'bbox_height': None,
                    'text': '',
                    'status': ''
                }

            item_type = item.get('type')
            value = item.get('value', {})

            if item_type == 'rectanglelabels':
                regions_by_id[region_id]['bbox_x'] = value.get('x')
                regions_by_id[region_id]['bbox_y'] = value.get('y')
                regions_by_id[region_id]['bbox_width'] = value.get('width')
                regions_by_id[region_id]['bbox_height'] = value.get('height')
            elif item_type == 'textarea':
                text_list = value.get('text', [])
                regions_by_id[region_id]['text'] = text_list[0] if text_list else ''
            elif item_type == 'choices':
                choices = value.get('choices', [])
                regions_by_id[region_id]['status'] = choices[0] if choices else ''

        results.extend(regions_by_id.values())

    return results


def export_to_json(data: list, output_path: str):
    """Export data to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Exported {len(data)} regions to {output_path}")


def export_to_csv(data: list, output_path: str):
    """Export data to CSV file."""
    if not data:
        print("No data to export")
        return

    fieldnames = [
        'task_id', 'annotation_id', 'region_id', 'image_path', 'created_at',
        'bbox_x', 'bbox_y', 'bbox_width', 'bbox_height', 'text', 'status'
    ]

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"Exported {len(data)} regions to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Export Label Studio annotations')
    parser.add_argument('--project', '-p', type=int, help='Project ID (default: first project)')
    parser.add_argument('--format', '-f', choices=['json', 'csv', 'both'], default='both',
                        help='Output format (default: both)')
    parser.add_argument('--output', '-o', type=str, default='exports',
                        help='Output directory (default: exports)')
    parser.add_argument('--status', '-s', type=str, choices=['Accepted', 'Rejected', 'Needs Review'],
                        help='Filter by status')
    parser.add_argument('--accepted-only', action='store_true',
                        help='Only export accepted annotations')
    args = parser.parse_args()

    # Initialize client
    label_studio_url = os.environ.get('LABEL_STUDIO_URL', 'http://localhost:8080')

    try:
        client = HITLClient(url=label_studio_url)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Get project
    project_id = args.project
    if project_id is None:
        projects = client.get_projects()
        if not projects:
            print("ERROR: No projects found")
            sys.exit(1)
        project_id = projects[0]['id']
        print(f"Using project: {projects[0]['title']} (ID: {project_id})")

    # Get tasks with annotations
    print(f"\nFetching tasks from project {project_id}...")
    response = client._request("GET", f"/api/projects/{project_id}/tasks")
    tasks = response.json()

    # Filter to only tasks with annotations
    annotated_tasks = [t for t in tasks if t.get('annotations')]
    print(f"Found {len(annotated_tasks)} annotated tasks")

    # Extract annotation data
    all_regions = []
    for task in annotated_tasks:
        regions = extract_annotation_data(task)
        all_regions.extend(regions)

    print(f"Extracted {len(all_regions)} annotated regions")

    # Apply filters
    if args.accepted_only:
        all_regions = [r for r in all_regions if r['status'] == 'Accepted']
        print(f"Filtered to {len(all_regions)} accepted regions")
    elif args.status:
        all_regions = [r for r in all_regions if r['status'] == args.status]
        print(f"Filtered to {len(all_regions)} regions with status '{args.status}'")

    if not all_regions:
        print("No annotations to export")
        return

    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Export
    if args.format in ('json', 'both'):
        json_path = os.path.join(args.output, f'annotations_{timestamp}.json')
        export_to_json(all_regions, json_path)

    if args.format in ('csv', 'both'):
        csv_path = os.path.join(args.output, f'annotations_{timestamp}.csv')
        export_to_csv(all_regions, csv_path)

    # Summary by status
    print("\nSummary by status:")
    status_counts = {}
    for r in all_regions:
        status = r['status'] or 'Unknown'
        status_counts[status] = status_counts.get(status, 0) + 1
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")


if __name__ == '__main__':
    main()
