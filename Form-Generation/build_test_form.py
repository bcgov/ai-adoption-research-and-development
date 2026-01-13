
from PIL import Image
from generate_text_image import generate_image
from generate_form_data import generate_data


# Load template image
template_path = "template.jpg"
template_image = Image.open(template_path)

# Generate data
data = generate_data()
print(data)

# Load data locations (annotations)
import json
with open("template.json", "r") as f:
	template_json = json.load(f)

annotations = template_json.get("annotations", [])
categories = template_json.get("categories", [])

# Create a lookup function to get annotations by category name
def get_annotation_by_category_name(name):
	# Find the category id for the given name
	category_id = None
	for cat in categories:
		if cat["name"] == name:
			category_id = cat["id"]
			break
	if category_id is None:
		return None
	# Return the first annotation with this category_id, or None if not found
	matches = [ann for ann in annotations if ann["category_id"] == category_id]
	if not matches:
		print(f"Warning: No annotation found for category name '{name}' (id {category_id})")
		return None
	return matches[0]

# For each annotation create image and compose on template
# Some assumptions here, if it's a boolean value, it's a checkbox
# Anything else, we need to generate text

for c in categories:
		name = c['name']
		value = data.get(name)
		annotation = get_annotation_by_category_name(name)
		if value is not None and annotation is not None:
				if isinstance(value, bool):
						# Handle checkbox logic here (not implemented)
						pass
				else:
					# Create an image for this text
					text_img_list = generate_image([str(value)], 1)
					if text_img_list:
						text_img, _ = text_img_list[0]
						bbox = annotation['bbox']
						# Resize text_img to fit bbox width and height
						bbox_width = int(bbox[2])
						bbox_height = int(bbox[3])
						text_img = text_img.resize((bbox_width, bbox_height))
						# Paste text_img onto template_image at bbox (x, y)
						template_image.paste(text_img, (int(bbox[0]), int(bbox[1])))

# Save the composed template image
output_path = "output/composed_template.jpg"
import os
os.makedirs(os.path.dirname(output_path), exist_ok=True)
template_image.save(output_path)
print(f"Saved composed image to {output_path}")
