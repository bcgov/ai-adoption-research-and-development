
from PIL import Image
from generate_text_image import generate_handwriting_svg, generate_text_image
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
					text_img_list = generate_text_image([str(value)], 1)
					if text_img_list:
						text_img, _ = text_img_list[0]
						bbox = annotation['bbox']
						bbox_width = int(bbox[2])
						bbox_height = int(bbox[3])
						orig_width, orig_height = text_img.size
						if 'income' in name.lower():
							# No offset, use full bbox
							new_height = bbox_height
							new_width = max(1, int(orig_width * (new_height / orig_height)))
							text_img = text_img.resize((new_width, new_height))
							paste_x = int(bbox[0]) + max((bbox_width - new_width) // 2, 0)
							paste_y = int(bbox[1])
						else:
							# Add vertical offset for field label and decrease height for text
							field_label_offset = int(0.3 * bbox_height)  # 30% of bbox height reserved for label
							available_height = bbox_height - field_label_offset
							new_height = max(1, available_height)
							new_width = max(1, int(orig_width * (new_height / orig_height)))
							text_img = text_img.resize((new_width, new_height))
							paste_x = int(bbox[0]) + max((bbox_width - new_width) // 2, 0)
							paste_y = int(bbox[1]) + field_label_offset
						# Paste text_img onto template_image at bbox (x, y)
						template_image.paste(text_img, (paste_x, paste_y))

# Trying SVG Generation with handwriting-synthesis
# Has issues with some special characters and sizing			
# import io
# from svglib.svglib import svg2rlg
# from reportlab.graphics import renderPM
# for c in categories:
# 	name = c['name']
# 	value = data.get(name)
# 	annotation = get_annotation_by_category_name(name)
# 	if value is not None and annotation is not None:
# 		if isinstance(value, bool):
# 			# Handle checkbox logic here (not implemented)
# 			pass
# 		else:
# 			# Generate SVG handwriting for this text
# 			svg_str = generate_handwriting_svg(str(value), style=0, alignment="left")
# 			# Strip XML declaration if present
# 			if svg_str.strip().startswith('<?xml'):
# 				svg_str = svg_str.split('?>', 1)[-1]
# 			# Use svglib to convert SVG string to ReportLab Drawing
# 			drawing = svg2rlg(io.StringIO(svg_str))
# 			if drawing is None:
# 				print(f"Warning: Failed to parse SVG for value '{value}'. Skipping.")
# 				continue
# 			# Render Drawing to PNG bytes
# 			png_bytes = renderPM.drawToString(drawing, fmt='PNG')
# 			# Open PNG as PIL Image
# 			text_img = Image.open(io.BytesIO(png_bytes))
# 			bbox = annotation['bbox']
# 			bbox_width = int(bbox[2])
# 			bbox_height = int(bbox[3])
# 			text_img = text_img.resize((bbox_width, bbox_height))
# 			template_image.paste(text_img, (int(bbox[0]), int(bbox[1])))

# Save the composed template image
output_path = "output/composed_template.jpg"
import os
os.makedirs(os.path.dirname(output_path), exist_ok=True)
template_image.save(output_path)
print(f"Saved composed image to {output_path}")
