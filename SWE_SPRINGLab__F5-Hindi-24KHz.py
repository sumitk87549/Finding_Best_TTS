import os
from datetime import datetime
from huggingface_hub import login
from huggingface_hub import hf_hub_download
from f5_tts.infer.utils_infer import load_model, load_vocoder
from f5_tts.infer.infer_cli import infer_process
import torch
import soundfile as sf
from pathlib import Path
import subprocess
import warnings
import sys

def check_ffmpeg():
    """Check if ffmpeg is available and install if needed."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        pass
    
    print("Warning: ffmpeg not found. Attempting to install...")
    try:
        # Try to install ffmpeg using apt (Ubuntu/Debian)
        subprocess.run(['sudo', 'apt-get', 'update'], check=True, capture_output=True)
        subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ffmpeg'], check=True, capture_output=True)
        print("ffmpeg installed successfully!")
        return True
    except:
        print("Could not install ffmpeg automatically.")
        print("Please install ffmpeg manually:")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        return False

# Check for ffmpeg at startup
if not check_ffmpeg():
    print("\nContinuing without ffmpeg - some audio processing may be limited...\n")

# Suppress pydub ffmpeg warning
warnings.filterwarnings('ignore', message='.*ffmpeg.*')

def load_access_token():
    """Load Hugging Face access token from file."""
    try:
        with open('Access_Token.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("Error: Access_Token.txt file not found!")
        return None

def load_hindi_text():
    """Load Hindi text from hin1.txt file."""
    try:
        with open('hin1.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("Error: hin1.txt file not found!")
        return None

def create_output_directory():
    """Create TTS output directory if it doesn't exist."""
    os.makedirs('TTS', exist_ok=True)

def generate_timestamp():
    """Generate timestamp for output filename."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def setup_huggingface_auth(token):
    """Setup HuggingFace authentication token."""
    login(token=token)
    return token

def generate_tts_audio(text, output_dir, model_name, ref_audio_path, ref_text):
    """Generate TTS audio and save to file."""
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Clean model name for filename
    clean_model_name = model_name.replace("/", "__").replace(":", "_")
    
    # Generate output filename
    output_filename = f"{clean_model_name}__{timestamp}.wav"
    output_path = os.path.join(output_dir, output_filename)
    
    print(f"Generating TTS audio...")
    print(f"Input text length: {len(text)} characters")
    print(f"Reference audio: {ref_audio_path}")
    
    # Configuration
    device = "cuda" if torch.cuda.is_available() else "cpu"
    vocoder_name = "vocos"
    nfe_step = 32
    cfg_strength = 0.1
    sway_sampling_coef = 0.0
    speed = 1.0
    
    # Load vocoder
    print("Loading vocoder...")
    vocoder = load_vocoder(
        vocoder_name=vocoder_name,
        is_local=False,
        local_path=None,
        device=device
    )
    
    # Load model
    print("Loading F5-TTS model...")
    from omegaconf import OmegaConf
    from f5_tts.model import CFM
    import importlib
    from importlib.resources import files
    
    # Create custom config that exactly matches Hindi model architecture
    model_cfg = OmegaConf.create({
        'model': {
            'backbone': 'DiT',
            'arch': {
                'dim': 768,
                'depth': 18,
                'heads': 12,
                'dim_head': 64,
                'ff_mult': 2,
                'dropout': 0.1,
                # text_num_embeds will be set by load_model function
                'text_dim': None,
                'text_mask_padding': True,
                'text_embedding_average_upsampling': False,
                'qk_norm': None,
                'conv_layers': 3,
                'pe_attn_head': None,
                'attn_backend': 'torch',
                'attn_mask_enabled': False,
                'long_skip_connection': False,
                'checkpoint_activations': False
            }
        }
    })
    
    model_cls = getattr(importlib.import_module("f5_tts.model"), model_cfg.model.backbone)
    model_arc = model_cfg.model.arch
    
    # Download checkpoint from HuggingFace
    ckpt_file = hf_hub_download(
        repo_id="SPRINGLab/F5-Hindi-24KHz",
        filename="model_2500000.safetensors"
    )
    vocab_file = hf_hub_download(
        repo_id="SPRINGLab/F5-Hindi-24KHz",
        filename="vocab.txt"
    )
    
    print(f"vocab :  {vocab_file}")
    print(f"token :  custom")
    print(f"model :  {ckpt_file}")
    
    # Load model
    model = load_model(
        model_cls,
        model_arc,
        ckpt_file,
        mel_spec_type=vocoder_name,
        vocab_file=vocab_file,
        device=device
    )
    
    # Run inference
    print("Running inference...")
    audio = infer_process(
        model,
        ref_audio_path,
        ref_text,
        text,
        vocoder,
        device=device,
        nfe_step=nfe_step,
        cfg_strength=cfg_strength,
        sway_sampling_coef=sway_sampling_coef,
        speed=speed
    )
    
    # Save audio file
    sample_rate = 24000  # F5-TTS uses 24kHz
    sf.write(output_path, audio, sample_rate)
    
    print(f"TTS audio saved to: {output_path}")
    print(f"Audio format: WAV, Sample rate: {sample_rate} Hz")
    
    return output_path

def main():
    print("Starting F5-Hindi-24KHz TTS generation...")
    
    # Load access token
    access_token = load_access_token()
    if not access_token:
        return
    
    # Load Hindi text
    hindi_text = load_hindi_text()
    if not hindi_text:
        return
    
    # Create output directory
    create_output_directory()
    
    # Generate timestamp for output files
    timestamp = generate_timestamp()
    
    # Configuration
    MODEL_NAME = "SPRINGLab/F5-Hindi-24KHz"
    OUTPUT_DIR = "TTS"
    
    # Reference audio and text (required for F5-TTS zero-shot voice cloning)
    # Use built-in example audio from f5_tts package
    from importlib.resources import files
    
    try:
        # Try to use Hindi reference audio if available
        REF_AUDIO = str(files("f5_tts").joinpath("infer/examples/basic/basic_ref_hi.wav"))
        REF_TEXT = "यह एक परीक्षण है"  # Reference text
        if not os.path.exists(REF_AUDIO):
            # Fallback to English reference audio
            REF_AUDIO = str(files("f5_tts").joinpath("infer/examples/basic/basic_ref_en.wav"))
            REF_TEXT = "Some call me nature, others call me mother nature."
    except:
        # Fallback to hardcoded path
        REF_AUDIO = "infer/examples/basic/basic_ref_en.wav"
        REF_TEXT = "Some call me nature, others call me mother nature."
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to script directory
    os.chdir(script_dir)
    
    print("=" * 60)
    print("F5-Hindi TTS Audio Generation")
    print("=" * 60)
    
    # Setup HuggingFace authentication
    print("\n[1/5] Setting up HuggingFace authentication...")
    setup_huggingface_auth(access_token)
    print("Authentication successful!")
    
    # Read input text
    print("\n[2/5] Reading input text...")
    print(f"Text loaded from hin1.txt")
    print(f"Text preview: {hindi_text[:100]}...")
    
    # Check reference audio
    print("\n[3/5] Checking reference audio...")
    print(f"Using reference audio: {REF_AUDIO}")
    print(f"Reference text: {REF_TEXT}")
    
    if not os.path.exists(REF_AUDIO):
        print(f"Error: Reference audio not found at {REF_AUDIO}")
        print("F5-TTS requires reference audio for zero-shot voice cloning.")
        print("Please ensure f5_tts is properly installed with example files.")
        return
    
    # Generate TTS audio
    print("\n[4/5] Generating TTS audio...")
    try:
        output_path = generate_tts_audio(hindi_text, OUTPUT_DIR, MODEL_NAME, REF_AUDIO, REF_TEXT)
        
        print("\n[5/5] Complete!")
        print("=" * 60)
        print("TTS Generation Complete!")
        print("=" * 60)
        print(f"Output file: {output_path}")
        
        # Also save the text used for generation
        output_base = os.path.splitext(output_path)[0]
        with open(f"{output_base}.txt", 'w', encoding='utf-8') as f:
            f.write(hindi_text)
        print(f"Source text saved as: {output_base}.txt")
        
    except Exception as e:
        print(f"Error during TTS generation: {str(e)}")
        import traceback
        traceback.print_exc()
        print("Please ensure you have the required packages installed:")
        print("pip install f5-tts")

if __name__ == "__main__":
    main()