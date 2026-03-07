import os
import sys
import time
import torch
import urllib.request

# Add cloned VibeVoice repository to Python path so its modules can be imported
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "VibeVoice"))

from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor

def download_voice_sample(url, save_path):
    """Download the reference voice for voice cloning if it doesn't exist."""
    if not os.path.exists(save_path):
        print(f"Downloading reference voice from {url}...")
        try:
            urllib.request.urlretrieve(url, save_path)
            print("Download complete.")
        except Exception as e:
            print(f"Failed to download voice sample: {e}")
            sys.exit(1)

def format_script(content):
    """
    Format the text content for VibeVoice processing.
    The inference system expects lines assigned to speakers, e.g., 'Speaker X: text'.
    """
    lines = content.strip().split('\n')
    # Prepend 'Speaker 1: ' to the first line so that the processor detects the speaker
    if lines:
        lines[0] = f"Speaker 1: {lines[0]}"
    return '\n'.join(lines)

def main():
    model_path = "sg123321/vibevoice-hindi-7b"
    voice_url = "https://huggingface.co/sg123321/vibevoice-hindi-7b/resolve/main/hi-Priya_woman.wav"
    
    # Path where the reference voice will be saved
    voice_path = os.path.join("VibeVoice", "demo", "voices", "hi-Priya_woman.wav")
    os.makedirs(os.path.dirname(voice_path), exist_ok=True)
    
    # Download reference voice
    download_voice_sample(voice_url, voice_path)
    
    # Determine the execution device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    load_dtype = torch.bfloat16 if device == "cuda" else torch.float32
    attn_impl = "flash_attention_2" if device == "cuda" else "sdpa"
    
    print(f"Loading processor and model from {model_path} to {device} (dtype: {load_dtype}, attn: {attn_impl})...")
    
    # Load processor
    processor = VibeVoiceProcessor.from_pretrained(model_path)
    
    # Load model with fallback for attention implementation
    try:
        model = VibeVoiceForConditionalGenerationInference.from_pretrained(
            model_path,
            torch_dtype=load_dtype,
            device_map=device,
            attn_implementation=attn_impl,
        )
    except Exception as e:
        print(f"Failed to load with {attn_impl}, falling back to sdpa: {e}")
        attn_impl = "sdpa"
        model = VibeVoiceForConditionalGenerationInference.from_pretrained(
            model_path,
            torch_dtype=load_dtype,
            device_map=device,
            attn_implementation=attn_impl,
        )
        
    model.eval()
    model.set_ddpm_inference_steps(num_steps=10)

    # Input files matching the user's prompt
    test_files = [
        "devnagri-test.txt",
        "latin-test.txt",
        "hinglish-test.txt"
    ]
    
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    for txt_file in test_files:
        if not os.path.exists(txt_file):
            print(f"Warning: {txt_file} not found. Skipping.")
            continue
            
        print(f"\n{'='*50}")
        print(f"Processing {txt_file}...")
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        if not content:
            print(f"File {txt_file} is empty. Skipping.")
            continue
            
        # Format script for the VibeVoice text parser
        formatted_script = format_script(content)
        formatted_script = formatted_script.replace("’", "'") 
        
        # Prepare model inputs
        inputs = processor(
            text=[formatted_script],
            voice_samples=[[voice_path]],
            padding=True,
            return_tensors="pt",
            return_attention_mask=True,
        )
        
        # Move tensors to the appropriate device
        for k, v in inputs.items():
            if torch.is_tensor(v):
                inputs[k] = v.to(device)
                
        print(f"Running TTS generation for {txt_file}...")
        start_time = time.time()
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=None,
                cfg_scale=1.3,
                tokenizer=processor.tokenizer,
                generation_config={'do_sample': False},
                verbose=True,
                is_prefill=True,
            )
            
        gen_time = time.time() - start_time
        print(f"Generation took {gen_time:.2f} seconds.")
        
        # Output saving format
        output_name = f"vibevoice_{os.path.splitext(txt_file)[0]}_generated.wav"
        output_path = os.path.join(output_dir, output_name)
        
        if outputs.speech_outputs and outputs.speech_outputs[0] is not None:
            processor.save_audio(outputs.speech_outputs[0], output_path=output_path)
            print(f"Audio successfully saved to {output_path}")
        else:
            print(f"Error: No speech generated for {txt_file}")
            
    print(f"\n{'='*50}")
    print("All tasks completed.")

if __name__ == '__main__':
    main()
