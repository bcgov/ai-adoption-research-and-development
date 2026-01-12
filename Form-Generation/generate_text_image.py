from trdg.generators import (
    GeneratorFromStrings,
)
import os

def generate_image(text_list, count=1):
    generator = GeneratorFromStrings(
        text_list,
        count,
        language="en",
        background_type=1,
        text_color="#000000",
        is_handwritten=True,
        fonts=[],
        size=128,
        skewing_angle=0,
        random_skew=False,
        blur=0,
        random_blur=False,
        distorsion_type=0,
        distorsion_orientation=0,
        width=-1,
        alignment=1,
        orientation=0,
        space_width=1.0,
        character_spacing=0,
        margins=(5, 5, 5, 5),
        fit=False,
        output_mask=False,
        word_split=False,
        stroke_width=1, 
        stroke_fill="#000000",
        image_mode="RGB",
        output_bboxes=0,
        rtl=False,
    )

    # Return these images as a list
    images = []
    for (img, label) in generator:
        images.append((img, label))
    
    return images

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        texts = sys.argv[1:]
        images = generate_image(texts, 5)

        output_dir = './output'
        os.makedirs(output_dir, exist_ok=True)
        
        for i, (img, label) in enumerate(images):
            img_path = os.path.join(output_dir, f"{label}_{i}.png")
            img.save(img_path)
            print(f"Saved: {img_path}")

    else:
        print("Usage: python generate_text_image.py <text1> <text2> ...")
