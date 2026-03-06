#!/usr/bin/env python3
"""
Bark TTS - Text-to-Speech using Suno's Bark model
Loads model from HuggingFace and generates audio from text files via command line.

Usage:
    python bark_tts.py --input input.txt --output output.wav
    python bark_tts.py -i input.txt -o output.wav --voice_preset v2/en_speaker_6
"""

import argparse
import os
import sys
import warnings
from pathlib import Path

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    import torch
    import torchaudio
    from transformers import AutoProcessor, BarkModel
    import soundfile as sf
except ImportError as e:
    print(f"Error: Missing required package. Please install: {e}")
    print("Run: pip install torch torchaudio transformers soundfile")
    sys.exit(1)


class BarkTTS:
    def __init__(self, device="auto"):
        """
        Initialize Bark TTS model
        
        Args:
            device (str): Device to use ('auto', 'cpu', 'cuda')
        """
        self.device = self._setup_device(device)
        self.model = None
        self.processor = None
        print(f"Initializing Bark TTS on device: {self.device}")
        
    def _setup_device(self, device):
        """Setup the computation device"""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return device
    
    def load_model(self, model_name="suno/bark"):
        """
        Load the Bark model and processor from HuggingFace
        
        Args:
            model_name (str): HuggingFace model name
        """
        try:
            print(f"Loading model: {model_name}")
            self.processor = AutoProcessor.from_pretrained(model_name)
            self.model = BarkModel.from_pretrained(model_name).to(self.device)
            
            # Enable CPU offloading for memory efficiency
            if self.device == "cpu":
                self.model.enable_cpu_offload()
            
            print("Model loaded successfully!")
            return True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def generate_speech(self, text, voice_preset=None, temperature=0.7, min_eos_p=0.05):
        """
        Generate speech from text
        
        Args:
            text (str): Input text to convert to speech
            voice_preset (str): Voice preset (e.g., 'v2/en_speaker_6')
            temperature (float): Generation temperature
            min_eos_p (float): Minimum end-of-sentence probability
            
        Returns:
            tuple: (audio_array, sample_rate)
        """
        if not self.model or not self.processor:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        try:
            print(f"Generating speech for text: {text[:100]}...")
            
            # Process inputs
            inputs = self.processor(
                text,
                voice_preset=voice_preset,
                return_tensors="pt"
            ).to(self.device)
            
            # Generate speech
            with torch.no_grad():
                speech_output = self.model.generate(
                    **inputs,
                    temperature=temperature,
                    min_eos_p=min_eos_p,
                    do_sample=True
                )
            
            # Get audio array and sample rate
            audio_array = speech_output[0].cpu().numpy()
            sample_rate = self.model.generation_config.sample_rate
            
            print("Speech generation completed!")
            return audio_array, sample_rate
            
        except Exception as e:
            print(f"Error generating speech: {e}")
            return None, None
    
    def save_audio(self, audio_array, sample_rate, output_path):
        """
        Save audio array to file
        
        Args:
            audio_array: Audio data array
            sample_rate: Audio sample rate
            output_path (str): Output file path
        """
        try:
            # Ensure output directory exists
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save audio file
            sf.write(output_path, audio_array, sample_rate)
            print(f"Audio saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error saving audio: {e}")
            return False


def read_text_file(file_path):
    """Read text content from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading text file {file_path}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Bark TTS - Generate speech from text files using Suno's Bark model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bark_tts.py --input input.txt --output output.wav
  python bark_tts.py -i input.txt -o output.wav --voice_preset v2/en_speaker_6
  python bark_tts.py -i story.txt -o story.wav --temperature 0.8

Available voice presets:
  v2/en_speaker_0 through v2/en_speaker_9 (English speakers)
  v2/de_speaker_1 through v2/de_speaker_8 (German speakers)
  v2/es_speaker_1 through v2/es_speaker_9 (Spanish speakers)
  v2/fr_speaker_1 through v2/fr_speaker_9 (French speakers)
  v2/hi_speaker_1 through v2/hi_speaker_8 (Hindi speakers)
  v2/it_speaker_1 through v2/it_speaker_9 (Italian speakers)
  v2/pl_speaker_1 through v2/pl_speaker_9 (Polish speakers)
  v2/pt_speaker_1 through v2/pt_speaker_9 (Portuguese speakers)
  v2/ru_speaker_1 through v2/ru_speaker_9 (Russian speakers)
  v2/zh_speaker_1 through v2/zh_speaker_9 (Chinese speakers)
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        required=True,
        help='Input text file path'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help='Output audio file path (supports .wav, .mp3, .flac)'
    )
    
    parser.add_argument(
        '--voice_preset',
        type=str,
        default='v2/en_speaker_6',
        help='Voice preset to use (default: v2/en_speaker_6)'
    )
    
    parser.add_argument(
        '--temperature',
        type=float,
        default=0.7,
        help='Generation temperature (0.1-1.0, default: 0.7)'
    )
    
    parser.add_argument(
        '--min_eos_p',
        type=float,
        default=0.05,
        help='Minimum end-of-sentence probability (default: 0.05)'
    )
    
    parser.add_argument(
        '--device',
        type=str,
        choices=['auto', 'cpu', 'cuda'],
        default='auto',
        help='Device to use for computation (default: auto)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='suno/bark',
        help='HuggingFace model name (default: suno/bark)'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' does not exist.")
        sys.exit(1)
    
    # Read input text
    text = read_text_file(args.input)
    if not text:
        print("Error: Could not read input text or file is empty.")
        sys.exit(1)
    
    print(f"Input text length: {len(text)} characters")
    
    # Initialize TTS
    tts = BarkTTS(device=args.device)
    
    # Load model
    if not tts.load_model(args.model):
        print("Error: Failed to load model.")
        sys.exit(1)
    
    # Generate speech
    audio_array, sample_rate = tts.generate_speech(
        text=text,
        voice_preset=args.voice_preset,
        temperature=args.temperature,
        min_eos_p=args.min_eos_p
    )
    
    if audio_array is None:
        print("Error: Failed to generate speech.")
        sys.exit(1)
    
    # Save audio
    if tts.save_audio(audio_array, sample_rate, args.output):
        print(f"\n✅ Success! Audio saved to: {args.output}")
        print(f"📊 Audio info - Sample rate: {sample_rate}Hz, Duration: {len(audio_array)/sample_rate:.2f}s")
    else:
        print("Error: Failed to save audio.")
        sys.exit(1)


if __name__ == "__main__":
    main()
