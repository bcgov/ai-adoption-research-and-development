from PIL import Image
from generate_text_image import generate_handwriting_image, generate_handwriting_images_batch, crop_to_text
from generate_form_data import generate_data
import time


def build_test_form(data, number=0, use_batch=True):
  # Load template image
  template_path = "template.jpg"
  template_image = Image.open(template_path)

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

  form_start_time = time.time()
  
  # Collect all texts that need to be generated, with mapping to their field info
  texts_to_generate = []
  field_info_map = {}  # Maps (name, value_key) to index in texts_to_generate
  
  for c in categories:
    name = c['name']
    value = data.get(name)
    annotation = get_annotation_by_category_name(name)
    if value is not None and annotation is not None:
      if isinstance(value, bool):
        if value:
          idx = len(texts_to_generate)
          texts_to_generate.append('X')
          field_info_map[(name, 'checkbox')] = idx
      else:
        idx = len(texts_to_generate)
        text_value = str(value)
        texts_to_generate.append(text_value)
        field_info_map[(name, 'text')] = idx
        # Debug: log text fields being collected
        if len(texts_to_generate) <= 10:  # Only log first 10 to avoid spam
          print(f"    [Debug] Collected text field '{name}': '{text_value}' at idx {idx}")
  
  # Batch generate all handwriting images
  handwriting_images = None
  if use_batch and texts_to_generate:
    batch_start = time.time()
    print(f"[Form {number}] Generating {len(texts_to_generate)} handwriting images in batch...")
    print(f"[Form {number}] Sample texts: {texts_to_generate[:5]}...")  # Debug: show first 5 texts
    print(f"[Form {number}] All texts: {texts_to_generate}")  # Debug: show ALL texts
    print(f"[Form {number}] Field map sample: {list(field_info_map.items())[:10]}")  # Debug: show mapping
    try:
      handwriting_images = generate_handwriting_images_batch(texts_to_generate, "http://localhost:8000/generate-batch")
      batch_time = time.time() - batch_start
      print(f"[Form {number}] Batch generation completed in {batch_time:.3f}s")
      print(f"[Form {number}] Received {len(handwriting_images) if handwriting_images else 0} images")
    except Exception as e:
      print(f"[Form {number}] Batch API failed, falling back to individual requests: {e}")
      use_batch = False
      handwriting_images = None
  
  # Process each category and compose on template
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
          
          # Use batch result if available, otherwise generate individually
          if use_batch and handwriting_images:
            idx = field_info_map.get((name, 'checkbox'))
            if idx is not None and idx < len(handwriting_images):
              x_img_bytes = handwriting_images[idx]
            else:
              x_img_bytes = generate_handwriting_image('X')
          else:
            x_img_bytes = generate_handwriting_image('X')
          
          from io import BytesIO
          img_start = time.time()
          x_img = Image.open(BytesIO(x_img_bytes)).convert("RGBA")
          x_img.load()
          x_img = crop_to_text(x_img)
          img_time = time.time() - img_start
          if img_time > 0.01:
            print(f"    [Image Processing] PIL open/convert: {img_time:.3f}s")
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
        # Use batch result if available, otherwise generate individually
        if use_batch and handwriting_images:
          idx = field_info_map.get((name, 'text'))
          if idx is not None and idx < len(handwriting_images):
            text_img_bytes = handwriting_images[idx]
            # Debug: verify we're using the right image
            expected_text = texts_to_generate[idx] if idx < len(texts_to_generate) else None
            if expected_text != str(value):
              print(f"    [ERROR] Field '{name}': Expected text '{str(value)}' but got image for '{expected_text}' (idx={idx})")
            else:
              # Only log first few to verify it's working
              if name in ['name', 'signature', 'date', 'phone', 'sin', 'explain_changes']:
                print(f"    [Debug] Field '{name}': Using idx {idx}, text='{str(value)}', matches expected='{expected_text}'")
          else:
            print(f"    [WARNING] Field '{name}': No batch image found (idx={idx}, len={len(handwriting_images)})")
            text_img_bytes = generate_handwriting_image(str(value))
        else:
          text_img_bytes = generate_handwriting_image(str(value))
        
        from io import BytesIO
        img_start = time.time()
        text_img = Image.open(BytesIO(text_img_bytes)).convert("RGBA")
        text_img.load()
        text_img = crop_to_text(text_img)
        img_time = time.time() - img_start
        if img_time > 0.01:
          print(f"    [Image Processing] PIL open/convert: {img_time:.3f}s")
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
            horizontal_padding = int(bbox_width * 0.02)
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

  # Save the composed template image
  output_path = f"output/form_image_{number}.jpg"
  import os
  os.makedirs(os.path.dirname(output_path), exist_ok=True)
  save_start = time.time()
  template_image.save(output_path)
  save_time = time.time() - save_start
  form_total_time = time.time() - form_start_time
  print(f"[Form {number}] Saved composed image to {output_path}")
  print(f"[Form {number}] Total form processing time: {form_total_time:.3f}s (save: {save_time:.3f}s)")


def generate_single_form(i, use_batch=True):
    """
    Generate a single form - thread-safe wrapper for parallel execution.
    Args:
        i: Form number/index
        use_batch: Whether to use batch API
    Returns:
        Form number (for tracking)
    """
    import json
    import os
    
    loop_start = time.time()
    print(f"\n[Form {i}] Starting form generation...")
    
    try:
        data_gen_start = time.time()
        data = generate_data()
        data_gen_time = time.time() - data_gen_start
        print(f"[Form {i}] Data generation: {data_gen_time:.3f}s")
        
        # Save data as JSON
        os.makedirs("output", exist_ok=True)
        json_path = f"output/form_data_{i}.json"
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[Form {i}] Saved data to {json_path}")
        
        # Build and save form image
        build_test_form(data, number=i, use_batch=use_batch)
        
        loop_time = time.time() - loop_start
        print(f"[Form {i}] Complete loop time: {loop_time:.3f}s")
        return i
    except Exception as e:
        print(f"[Form {i}] ERROR: {e}")
        raise


if __name__ == "__main__":
    import sys
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Parse command line arguments
    try:
        num_loops = int(sys.argv[1])
    except (IndexError, ValueError):
        num_loops = 1
    
    # Get parallelism setting (environment variable or default)
    # MAX_PARALLEL_FORMS controls how many forms to generate concurrently
    # Default: 4 (optimal for Deno service)
    # Set to 1 to disable parallelism
    max_parallel = int(os.environ.get('MAX_PARALLEL_FORMS', '4'))
    
    # Don't use more workers than forms to generate
    max_workers = min(num_loops, max_parallel)
    
    overall_start = time.time()
    print(f"[Overall] Starting generation of {num_loops} form(s)...")
    print(f"[Overall] Parallelism: {max_workers} worker(s) (set MAX_PARALLEL_FORMS env var to change)")
    
    # Generate forms in parallel if more than 1 form
    if num_loops == 1 or max_workers == 1:
        # Sequential generation (single form or parallelism disabled)
        generate_single_form(0, use_batch=True)
    else:
        # Parallel generation
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all form generation tasks
            futures = {executor.submit(generate_single_form, i, use_batch=True): i 
                      for i in range(num_loops)}
            
            # Wait for completion and handle results
            completed = 0
            for future in as_completed(futures):
                form_num = futures[future]
                try:
                    result = future.result()
                    completed += 1
                    print(f"[Overall] Completed {completed}/{num_loops} forms")
                except Exception as e:
                    print(f"[Overall] Form {form_num} failed: {e}")
    
    overall_time = time.time() - overall_start
    print(f"\n[Overall] Generated {num_loops} form(s) in {overall_time:.3f}s (avg: {overall_time/num_loops:.3f}s per form)")
