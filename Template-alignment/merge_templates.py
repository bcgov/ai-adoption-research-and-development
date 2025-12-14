#!/usr/bin/env python3
import json
import csv
import os

def merge_templates(polygonal_file, rectangular_file, output_file):
    """Merge polygonal and rectangular template data into a single JSON file."""

    # Load polygonal data
    with open(polygonal_file, 'r') as f:
        polygonal_data = json.load(f)

    # Load rectangular data from CSV
    rectangular_data = []
    with open(rectangular_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rectangular_data.append(row)

    # Create category name to ID mapping from polygonal data
    category_map = {cat['name']: cat['id'] for cat in polygonal_data['categories']}

    # Track next available category ID
    max_category_id = max(cat['id'] for cat in polygonal_data['categories'])

    # Track next available annotation ID
    max_annotation_id = max(ann['id'] for ann in polygonal_data['annotations']) if polygonal_data['annotations'] else 0

    # Process rectangular data and add missing categories/annotations
    for row in rectangular_data:
        label_name = row['label_name']

        # Check if category exists, if not add it
        if label_name not in category_map:
            max_category_id += 1
            category_map[label_name] = max_category_id
            polygonal_data['categories'].append({
                'id': max_category_id,
                'name': label_name
            })

        # Check if annotation already exists for this label
        existing_annotation = None
        for ann in polygonal_data['annotations']:
            cat_name = next((cat['name'] for cat in polygonal_data['categories'] if cat['id'] == ann['category_id']), None)
            if cat_name == label_name:
                existing_annotation = ann
                break

        if existing_annotation:
            # Update existing annotation with bbox if it doesn't have one
            if 'bbox' not in existing_annotation or not existing_annotation['bbox']:
                bbox_x = float(row['bbox_x'])
                bbox_y = float(row['bbox_y'])
                bbox_width = float(row['bbox_width'])
                bbox_height = float(row['bbox_height'])
                existing_annotation['bbox'] = [bbox_x, bbox_y, bbox_width, bbox_height]
        else:
            # Create new annotation
            max_annotation_id += 1
            bbox_x = float(row['bbox_x'])
            bbox_y = float(row['bbox_y'])
            bbox_width = float(row['bbox_width'])
            bbox_height = float(row['bbox_height'])

            # Calculate area
            area = bbox_width * bbox_height

            new_annotation = {
                'id': max_annotation_id,
                'iscrowd': 0,
                'image_id': 1,  # Assuming single image
                'category_id': category_map[label_name],
                'bbox': [bbox_x, bbox_y, bbox_width, bbox_height],
                'area': area
            }

            polygonal_data['annotations'].append(new_annotation)

    # Write merged data to output file
    with open(output_file, 'w') as f:
        json.dump(polygonal_data, f, indent=2)

    print(f"Merged data written to {output_file}")
    print(f"Total categories: {len(polygonal_data['categories'])}")
    print(f"Total annotations: {len(polygonal_data['annotations'])}")

if __name__ == "__main__":
    polygonal_file = "template_polygonal.json"
    rectangular_file = "template_rectangular.csv"
    output_file = "template.json"

    merge_templates(polygonal_file, rectangular_file, output_file)
