import argparse
import os
import sys
import torch
import wave

# Add the local svara-tts-inference directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "svara-tts-inference"))

try:
    from tts_engine.encoder import svara_text_to_tokens
    from tts_engine.mapper import extract_custom_token_numbers, raw_to_code_id
    from tts_engine.codec import SNACCodec
    import tts_engine.constants as constants
except ImportError as e:
    print(f"Error: Could not import svara-tts-inference modules. Ensure svara-tts-inference is in the same directory.")
    print(f"Details: {e}")
    sys.exit(1)

from transformers import AutoModelForCausalLM, AutoTokenizer

def main():
    parser = argparse.ArgumentParser(description="Test samudr-ai/svara-tts-v1-hindi-ft locally")
    parser.add_argument("text_file", help="Path to the text file")
    parser.add_argument("--output", default="output.wav", help="Output audio file path")
    parser.add_argument("--speaker_id", default="Hindi (Male)", help="Speaker ID, e.g. 'Hindi (Male)', 'Hindi (Female)'")
    args = parser.parse_args()

    if not os.path.exists(args.text_file):
        print(f"Error: Text file '{args.text_file}' not found.")
        sys.exit(1)

    with open(args.text_file, "r", encoding="utf-8") as f:
        text = f.read().strip()

    model_id = "samudr-ai/svara-tts-v1-hindi-ft"
    tokenizer_id = "kenpath/svara-tts-v1"
    print(f"Loading tokenizer from {tokenizer_id}...")
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)
    
    print(f"Loading model {model_id}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    # To run successfully on a laptop, we use bfloat16 if cuda is available
    model = AutoModelForCausalLM.from_pretrained(
        model_id, 
        device_map="auto" if torch.cuda.is_available() else None,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32
    )
    
    # Load SNAC Codec
    print("Loading SNAC codec...")
    codec = SNACCodec(device=device)

    # Generate prompt
    print(f"Generating audio for text: '{text[:50]}...'")
    prompt_ids = svara_text_to_tokens(
        text=text,
        speaker_id=args.speaker_id,
        tokenizer=tokenizer,
        return_decoded=False
    )
    
    input_ids = torch.tensor([prompt_ids]).to(model.device)
    
    # Run text generation
    print("Running inference (this may take a while depending on your hardware)...")
    
    with torch.no_grad():
        outputs = model.generate(
            input_ids,
            max_new_tokens=2048,
            temperature=0.75,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=constants.END_OF_SPEECH
        )
    
    generated_ids = outputs[0][input_ids.shape[1]:]
    generated_text = tokenizer.decode(generated_ids, skip_special_tokens=False)
    
    print("Decoding audio tokens...")
    
    # Collect all valid code strings
    codes = []
    good_count = 0
    for raw_n in extract_custom_token_numbers(generated_text):
        code = raw_to_code_id(raw_n, good_count)
        if code > 0:
            codes.append(code)
            good_count += 1
            
    print(f"Generated {len(codes)} valid audio tokens. Converting to audio...")
    
    if len(codes) == 0:
        print("Warning: No audio tokens generated. Please check the input text and model.")
        sys.exit(1)
        
    pcm_audio = codec.decode(codes)
    
    # Write to WAV
    print(f"Saving to {args.output}...")
    with wave.open(args.output, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2) # 16-bit
        wf.setframerate(codec.sample_rate)
        wf.writeframes(pcm_audio)
        
    print(f"Success! Saved generation to {args.output}")

if __name__ == "__main__":
    main()
