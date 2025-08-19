
from dotenv import load_dotenv
from time import sleep
import time
from PIL import Image as Im
from PIL import ImageOps
import PIL
from IPython import display
from IPython.display import display
import sys
import pandas as pd
import os
PIL.Image.MAX_IMAGE_PIXELS = 933120000
load_dotenv()
cache_dir = os.getenv("CACHE_DIR")
working_dir = os.getcwd()

full_path = os.path.realpath(cache_dir)
image_cache_list = os.listdir(full_path)
image_list = []
for pic in image_cache_list:
    pic_path = os.path.join(cache_dir, pic)
    image_list.append(pic_path)
image_list = image_list[:10]  # Limit to first 10 images for testing

def get_tags_from_cache(image_list,model_id,prompt):
    tags=[]
    
    if model_id == "LFM2":
        from transformers import AutoProcessor, AutoModelForImageTextToText
        from transformers.image_utils import load_image
        print("Using LFM2 model for tag generation")
        model_name = "LiquidAI/LFM2-VL-1.6B"
        model = AutoModelForImageTextToText.from_pretrained(
            model_name,
            device_map="mps",
            torch_dtype="bfloat16",
            trust_remote_code=True)

    avg_time = []
    i = 0
    for image_url in image_list:
        image = Im.open(image_url)
        image = ImageOps.contain(image, (1024,1024))
        start_time = time.time()
        i += 1
        print(f"Processing image {i} of {len(image_list)}")
        if model_id == "LFM2":
            processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
            conversation = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt}
                    ],
                },
            ]
            
            # Generate Answer
            inputs = processor.apply_chat_template(
                conversation,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
                tokenize=True,
            ).to("mps")
            outputs = model.generate(**inputs, max_new_tokens=64)
            full_outputs = processor.batch_decode(outputs, skip_special_tokens=True)
            print(f"Output: {full_outputs[0][len(prompt)+16:]}")
            tags.append(full_outputs[0][len(prompt)+16:])

        else:
            print("No model selected, exiting.")
            sys.exit(1)

        endtime = time.time()
        this_run_time = endtime - start_time
        avg_time.append(this_run_time)
        print(f"Time taken for iteration {i}: {this_run_time:.2f} seconds")
        print(' - ' * 50)
    df_tags = pd.DataFrame({'image': image_list, 'tags': tags})
    df_tags.to_csv('./image_tags.csv', index=False)
    return df_tags

get_tags_from_cache(image_list, "LFM2", "Generate tags for this image: ")