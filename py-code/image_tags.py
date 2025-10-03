
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

def get_tags_from_cache(df,model_id,prompt):
    df_tags = pd.DataFrame(columns=['tags'])
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

    if model_id == "Pixtral_transformer":
        from transformers import AutoProcessor, LlavaForConditionalGeneration
        from transformers import pipeline
        print("Using Pixtral model for tag generation")
        model_id = "mistral-community/pixtral-12b"
        model = LlavaForConditionalGeneration.from_pretrained(model_id)
        processor = AutoProcessor.from_pretrained(model_id)

    if model_id == "Mistral_mlx":
        import mlx.core as mx
        from mlx_vlm import load, generate
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.utils import load_config
        model_path = "mlx-community/pixtral-12b-bf16"
        model, processor = load(model_path)
        config = load_config(model_path)


    i = 0
    for image_url in tqdm(df['local_path']):
        image = Im.open(image_url)
        image = ImageOps.contain(image, (1024,1024))
        
        #print(f"Processing image {i} of {len(image_list)}")
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
            print(f"Output: {full_outputs}")
            df.at[df.index[i], 'tags'] = full_outputs[0][len(prompt)+16:]
        
        if model_id == "mistral-community/pixtral-12b":
            PROMPT = f'''<s>[INST]{prompt}\n [IMG] [/INST]'''
            inputs = processor(text=PROMPT, images=image, return_tensors="pt").to("cpu")
            generate_ids = model.generate(**inputs, max_new_tokens=64)
            output = processor.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
            print(output)
            df.at[df.index[i], 'tags'] = output[len(prompt)+1:]
            
        if model_id == "Mistral_mlx":
            PROMPT = prompt
            formatted_prompt = apply_chat_template(processor, config, PROMPT, num_images=1)
            output = generate(model, processor, formatted_prompt, image, verbose=False)
            print(output.text)
            df.at[df.index[i], 'tags'] = output.text

        elif model_id is None:
            print("No model selected, exiting.")
            sys.exit(1)
        i += 1

    #df_tags = pd.DataFrame({'image': image_list, 'tags': tags})
    df_tags.to_csv('./image_tags.csv', index=False, sep=',')
    return df
