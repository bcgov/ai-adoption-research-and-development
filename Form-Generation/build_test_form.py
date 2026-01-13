from PIL import Image
from generate_text_image import generate_handwriting_svg, generate_text_image, generate_handwriting_image, crop_to_text
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
      # If true, generate and paste an 'X' image in the bbox
      if value:
        bbox = annotation['bbox']
        bbox_width = int(bbox[2])
        bbox_height = int(bbox[3])
        x_img_bytes = generate_handwriting_image('X')
        from io import BytesIO
        x_img = Image.open(BytesIO(x_img_bytes)).convert("RGBA")
        x_img.load()
        x_img = crop_to_text(x_img)
        # Shrink the checkbox image to % of the bbox size, centered
        scale_factor = 0.7
        new_height = int(bbox_height * scale_factor)
        new_width = int(bbox_width * scale_factor)
        orig_width, orig_height = x_img.size
        # Maintain aspect ratio
        scale = min(new_width / orig_width, new_height / orig_height)
        final_width = max(1, int(orig_width * scale))
        final_height = max(1, int(orig_height * scale))
        x_img = x_img.resize((final_width, final_height))
        paste_x = int(bbox[0]) + (bbox_width - final_width) // 2
        paste_y = int(bbox[1]) + (bbox_height - final_height) // 2
        template_image.paste(x_img, (paste_x, paste_y), mask=x_img)
    else:
      # Create an image for this text
      text_img_bytes = generate_handwriting_image(str(value))
      from io import BytesIO
      text_img = Image.open(BytesIO(text_img_bytes)).convert("RGBA")
      text_img.load()
      text_img = crop_to_text(text_img)
      bbox = annotation['bbox']
      bbox_width = int(bbox[2])
      bbox_height = int(bbox[3])
      orig_width, orig_height = text_img.size
      if name == 'explain_changes':
          # Use a standard bounding box, but maintain aspect ratio
          max_width = 600  # desired max width
          max_height = 200  # desired max height
          scale = min(max_width / orig_width, max_height / orig_height)
          new_width = max(1, int(orig_width * scale))
          new_height = max(1, int(orig_height * scale))
          text_img = text_img.resize((new_width, new_height))
          paste_x = int(bbox[0]) + max((bbox_width - new_width) // 2, 0)
          paste_y = int(bbox[1]) + max((bbox_height - new_height) // 2, 0)
      elif 'income' in name.lower():
          # Use a fixed target height for all income fields, with horizontal padding
          fixed_height = 32  # Set your desired fixed height in pixels
          horizontal_padding = int(bbox_width * 0.05)  # 5% padding on each side
          available_width = bbox_width - 2 * horizontal_padding
          scale = fixed_height / orig_height
          new_height = fixed_height
          new_width = max(1, int(orig_width * scale))
          # If new_width exceeds available_width or new_height > bbox_height, shrink to fit
          if new_width > available_width or new_height > bbox_height:
              scale = min(available_width / orig_width, bbox_height / orig_height)
              new_width = max(1, int(orig_width * scale))
              new_height = max(1, int(orig_height * scale))
          text_img = text_img.resize((new_width, new_height))
          paste_x = int(bbox[0]) + horizontal_padding + max((available_width - new_width) // 2, 0)
          paste_y = int(bbox[1]) + max((bbox_height - new_height) // 2, 0)
      else:
          # Use a fixed target height for all other fields, with horizontal padding
          fixed_height = 32  # Set your desired fixed height in pixels
          field_label_offset = int(0.3 * bbox_height)  # 30% of bbox height reserved for label
          available_height = bbox_height - field_label_offset
          horizontal_padding = int(bbox_width * 0.05)
          available_width = bbox_width - 2 * horizontal_padding
          scale = fixed_height / orig_height
          new_height = fixed_height
          new_width = max(1, int(orig_width * scale))
          # If new_width exceeds available_width or new_height > available_height, shrink to fit
          if new_width > available_width or new_height > available_height:
              scale = min(available_width / orig_width, available_height / orig_height)
              new_width = max(1, int(orig_width * scale))
              new_height = max(1, int(orig_height * scale))
          text_img = text_img.resize((new_width, new_height))
          paste_x = int(bbox[0]) + horizontal_padding + max((available_width - new_width) // 2, 0)
          paste_y = int(bbox[1]) + field_label_offset + max((available_height - new_height) // 2, 0)
      # Paste text_img onto template_image at bbox (x, y), using mask to preserve transparency
      template_image.paste(text_img, (paste_x, paste_y), mask=text_img)
				
# Using TRDG for image generation. 
# Some issues here with legibility and consistency
# for c in categories:
# 	name = c['name']
# 	value = data.get(name)
# 	annotation = get_annotation_by_category_name(name)
# 	if value is not None and annotation is not None:
# 		if isinstance(value, bool):
# 			# If true, generate and paste an 'X' image in the bbox
# 			if value:
# 				bbox = annotation['bbox']
# 				bbox_width = int(bbox[2])
# 				bbox_height = int(bbox[3])
# 				x_img_list = generate_text_image(['X'], 1)
# 				if x_img_list:
# 					x_img, _ = x_img_list[0]
# 					orig_width, orig_height = x_img.size
# 					new_height = bbox_height
# 					new_width = max(1, int(orig_width * (new_height / orig_height)))
# 					x_img = x_img.resize((new_width, new_height))
# 					paste_x = int(bbox[0]) + max((bbox_width - new_width) // 2, 0)
# 					paste_y = int(bbox[1])
# 					template_image.paste(x_img, (paste_x, paste_y), mask=x_img)
# 		else:
# 			# Create an image for this text
# 			text_img_list = generate_text_image([str(value)], 1)
# 			if text_img_list:
# 				text_img, _ = text_img_list[0]
# 				bbox = annotation['bbox']
# 				bbox_width = int(bbox[2])
# 				bbox_height = int(bbox[3])
# 				orig_width, orig_height = text_img.size
# 				if 'income' in name.lower():
# 					# No offset, use full bbox
# 					new_height = bbox_height
# 					new_width = max(1, int(orig_width * (new_height / orig_height)))
# 					text_img = text_img.resize((new_width, new_height))
# 					paste_x = int(bbox[0]) + max((bbox_width - new_width) // 2, 0)
# 					paste_y = int(bbox[1])
# 				else:
# 					# Add vertical offset for field label and decrease height for text
# 					field_label_offset = int(0.3 * bbox_height)  # 30% of bbox height reserved for label
# 					available_height = bbox_height - field_label_offset
# 					new_height = max(1, available_height)
# 					new_width = max(1, int(orig_width * (new_height / orig_height)))
# 					text_img = text_img.resize((new_width, new_height))
# 					paste_x = int(bbox[0]) + max((bbox_width - new_width) // 2, 0)
# 					paste_y = int(bbox[1]) + field_label_offset
# 				# Paste text_img onto template_image at bbox (x, y), using mask to preserve transparency
# 				template_image.paste(text_img, (paste_x, paste_y), mask=text_img)

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
