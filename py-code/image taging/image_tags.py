
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
from tqdm import tqdm
PIL.Image.MAX_IMAGE_PIXELS = 933120000
import mlx.core as mx
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config




def flatten_dict_to_list(data):
    result_list = []
    
    def process_dict(content):
        for key, val in content.items():
            # If it's a folder entry
            if key.endswith("/"):
                if isinstance(val, dict):
                    process_dict(val)
            # If it's a file entry with metadata
            elif isinstance(val, dict) and 'name' in val:
                result_list.append(val)
    
    # Start with the root content
    if len(data) == 1:
        first_val = next(iter(data.values()))
        content = first_val
    else:
        content = data
        
    process_dict(content)
    return result_list

    
def filter_untagged_images(data_list, tagged_file_ids):
    # Filter out images that are already tagged
    untagged_images = [image for image in data_list if image['fileid'] not in tagged_file_ids]
    if len(untagged_images) == 0:
        print("No (new) files to tag")
    return untagged_images

def load_model_mlx():
    model_path = "mlx-community/pixtral-12b-bf16"
    model, processor = load(model_path)
    config = load_config(model_path)
    return model, processor, config

def mlx_tags(image, prompt ,model,processor,config):
    formatted_prompt = apply_chat_template(processor, config, prompt, num_images=1)
    output = generate(model, processor, formatted_prompt, image, verbose=False)
    #print(output.text)
    #print( 'Generator token count:', output.generation_tokens , ' Generator tokens per second:', output.generation_tps)
    return output.text