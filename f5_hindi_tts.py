#!/usr/bin/env python3
"""
F5-Hindi-24KHz TTS CLI Script
Uses SPRINGLab's F5-Hindi-24KHz model for Hindi text-to-speech

Usage:
    python f5_hindi_tts.py input.txt [options]
"""

import argparse
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Optional, List
import tempfile
import requests

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

def check_environment():
    """Check current environment and provide setup guidance."""
    print("🔍 Checking environment...")
    
    # Check Python version
    python_version = sys.version_info
    print(f"   Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check for required packages
    required_packages = ['torch', 'torchaudio', 'numpy']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package} available")
        except ImportError:
            missing_packages.append(package)
            print(f"   ❌ {package} missing")
    
    # Check F5-TTS specifically
    try:
        import f5_tts
        print("   ✅ f5-tts available")
        return True
    except ImportError:
        print(f"   ❌ f5-tts not available")
        missing_packages.append('f5-tts')
    
    if missing_packages:
        print(f"\n📦 Missing packages: {', '.join(missing_packages)}")
        print("\n🔧 Setup instructions:")
        print("1. Install F5-TTS:")
        print("   pip install git+https://github.com/SWivid/F5-TTS.git")
        print("\n2. Or install required packages manually:")
        print("   pip install torch torchaudio numpy")
        print("   pip install git+https://github.com/SWivid/F5-TTS.git")
        
        return False
    
    return True

class F5HindiTTS:
    """F5-Hindi-24KHz TTS generator."""
    
    def __init__(self, device: str = "auto"):
        """Initialize TTS generator."""
        self.device = self._detect_device(device)
        self.model = None
        self.model_path = None
        self.vocab_path = None
        self.ref_audio_path = None
        
        # Model files info
        self.model_repo = "SPRINGLab/F5-Hindi-24KHz"
        self.required_files = {
            "model_2500000.safetensors": "Model checkpoint",
            "vocab.txt": "Vocabulary file"
        }
        
    def _detect_device(self, device: str) -> str:
        """Detect and set the appropriate device."""
        if device == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    print(f"🎯 CUDA detected: {torch.cuda.get_device_name(0)}")
                    return "cuda"
                else:
                    print("💻 CUDA not available, using CPU")
                    return "cpu"
            except ImportError:
                return "cpu"
        return device
    
    def download_model_files(self, force_download: bool = False) -> bool:
        """Download model files from HuggingFace."""
        print("📥 Downloading F5-Hindi-24KHz model files...")
        
        try:
            from huggingface_hub import hf_hub_download, snapshot_download
            
            # Create model directory
            model_dir = Path("f5_hindi_model")
            model_dir.mkdir(exist_ok=True)
            
            # Download all files from the repo
            print(f"   Downloading from {self.model_repo}...")
            snapshot_download(
                repo_id=self.model_repo,
                local_dir=str(model_dir),
                local_dir_use_symlinks=False
            )
            
            # Set paths
            self.model_path = model_dir / "model_2500000.safetensors"
            self.vocab_path = model_dir / "vocab.txt"
            
            # Check if required files exist
            if not self.model_path.exists():
                print(f"❌ Model file not found: {self.model_path}")
                return False
            
            if not self.vocab_path.exists():
                print(f"❌ Vocab file not found: {self.vocab_path}")
                return False
            
            # Download reference audio
            ref_audio_url = "https://huggingface.co/SPRINGLab/F5-Hindi-24KHz/resolve/main/samples/dear_friends_cleaned_1001.wav"
            self.ref_audio_path = model_dir / "ref_audio.wav"
            
            if not self.ref_audio_path.exists() or force_download:
                print("   Downloading reference audio...")
                response = requests.get(ref_audio_url, timeout=60)
                response.raise_for_status()
                with open(self.ref_audio_path, 'wb') as f:
                    f.write(response.content)
            
            print(f"✅ Model files downloaded to {model_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to download model files: {e}")
            print("\n🔧 Possible solutions:")
            print("1. Check internet connection")
            print("2. Install huggingface_hub: pip install huggingface_hub")
            print("3. Try manual download from https://huggingface.co/SPRINGLab/F5-Hindi-24KHz")
            return False
    
    def load_model(self) -> bool:
        """Load F5-Hindi model."""
        if not self.model_path or not self.vocab_path:
            if not self.download_model_files():
                return False
        
        print("📥 Loading F5-Hindi model...")
        try:
            from f5_tts.model import DiT
            from f5_tts.infer.utils import load_model, load_vocoder
            
            start_time = time.time()
            
            # Load model
            self.model = load_model(
                model_path=str(self.model_path),
                vocab_path=str(self.vocab_path),
                device=self.device
            )
            
            # Load vocoder
            self.vocoder = load_vocoder(device=self.device)
            
            load_time = time.time() - start_time
            print(f"✅ Model loaded on {self.device} in {load_time:.1f}s")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            print("\n🔧 Possible solutions:")
            print("1. Ensure F5-TTS is properly installed")
            print("2. Check model file integrity")
            print("3. Try CPU mode: --device cpu")
            return False
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess Hindi text."""
        # Basic text cleaning
        text = text.strip()
        # Remove excessive whitespace
        text = ' '.join(text.split())
        return text
    
    def split_text_into_chunks(self, text: str, max_chars: int = 200) -> List[str]:
        """Split text into manageable chunks for Hindi."""
        # Split on sentence boundaries (Hindi sentence endings)
        import re
        sentences = re.split(r'[।!?]\s*', text.strip())
        chunks = []
        current = ""
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            if len(current) + len(sentence) + 1 <= max_chars:
                current = (current + " " + sentence).strip() if current else sentence
            else:
                if current:
                    chunks.append(current)
                current = sentence if len(sentence) <= max_chars else ""
        
        if current:
            chunks.append(current)
        
        return chunks if chunks else [text]
    
    def generate_audio(self, text: str, **kwargs) -> Optional:
        """Generate audio from text."""
        if not self.model:
            print("❌ Model not loaded")
            return None
        
        try:
            from f5_tts.infer.utils import infer
            
            processed_text = self.preprocess_text(text)
            
            # Split text into chunks
            chunks = self.split_text_into_chunks(processed_text)
            print(f"📝 Text split into {len(chunks)} chunk(s)")
            
            all_audio = []
            total_start = time.time()
            
            for i, chunk in enumerate(chunks, 1):
                if not chunk.strip():
                    continue
                
                print(f"🔊 Generating chunk {i}/{len(chunks)} ({len(chunk)} chars)...")
                start_time = time.time()
                
                # Generate audio for chunk
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                try:
                    # Use F5-TTS inference
                    infer(
                        model=self.model,
                        vocoder=self.vocoder,
                        ref_audio_path=str(self.ref_audio_path),
                        ref_text="",  # Let ASR transcribe
                        gen_text=chunk,
                        output_path=tmp_path,
                        device=self.device,
                        **kwargs
                    )
                    
                    # Load generated audio
                    import torchaudio
                    audio, sr = torchaudio.load(tmp_path)
                    all_audio.append(audio)
                    
                    elapsed = time.time() - start_time
                    duration = audio.shape[-1] / sr
                    print(f"   ✅ Done in {elapsed:.1f}s → {duration:.1f}s audio")
                    
                finally:
                    # Clean up temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            
            if not all_audio:
                print("❌ No audio generated")
                return None
            
            # Combine all chunks
            try:
                import torch
                final_audio = torch.cat(all_audio, dim=-1)
                
                total_time = time.time() - total_start
                total_duration = final_audio.shape[-1] / 24000  # F5-TTS uses 24kHz
                
                print(f"\n🎉 Generation complete!")
                print(f"   Total audio: {total_duration:.1f}s")
                print(f"   Processing time: {total_time:.1f}s")
                print(f"   Real-time factor: {total_time/total_duration:.1f}x")
                
                return final_audio
                
            except Exception as e:
                print(f"❌ Failed to combine audio chunks: {e}")
                return None
            
        except Exception as e:
            print(f"❌ Audio generation failed: {e}")
            print("\n🔧 Possible solutions:")
            print("1. Try shorter text input")
            print("2. Check text encoding (use UTF-8)")
            print("3. Ensure reference audio is accessible")
            return None
    
    def save_audio(self, audio, output_path: str) -> bool:
        """Save audio to file."""
        try:
            import torchaudio
            
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            
            # Ensure audio is in the right format
            if audio.dim() == 1:
                audio = audio.unsqueeze(0)
            
            torchaudio.save(output_path, audio, 24000)  # F5-TTS uses 24kHz
            
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            duration = audio.shape[-1] / 24000
            
            print(f"💾 Audio saved: {output_path}")
            print(f"   Duration: {duration:.1f}s")
            print(f"   File size: {file_size:.1f} MB")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to save audio: {e}")
            return False

def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Generate Hindi TTS using F5-Hindi-24KHz model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.txt
  %(prog)s input.txt --device cpu
  %(prog)s input.txt --output custom.wav --chunk-size 150
        """
    )
    
    # Required arguments
    parser.add_argument("input_file", help="Input Hindi text file to convert to speech")
    
    # Model options
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto",
                       help="Device to use (default: auto)")
    parser.add_argument("--force-download", action="store_true",
                       help="Force re-download of model files")
    
    # Generation options
    parser.add_argument("--chunk-size", type=int, default=200,
                       help="Text chunk size for memory management (default: 200)")
    parser.add_argument("-o", "--output", help="Output audio file path")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Reduce output verbosity")
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"❌ Input file not found: {args.input_file}")
        sys.exit(1)
    
    # Set output filename
    if not args.output:
        input_name = Path(args.input_file).stem
        args.output = f"{input_name}_f5_hindi_tts.wav"
    
    # Check environment first
    if not check_environment():
        print("\n❌ Environment setup required. Please follow the instructions above.")
        sys.exit(1)
    
    try:
        # Initialize TTS generator
        if not args.quiet:
            print("🎙️  F5-Hindi-24KHz TTS Generator")
            print("=" * 50)
        
        generator = F5HindiTTS(device=args.device)
        
        # Download/load model
        if not generator.download_model_files(force_download=args.force_download):
            sys.exit(1)
        
        if not generator.load_model():
            sys.exit(1)
        
        # Read input text
        if not args.quiet:
            print(f"📖 Reading input file: {args.input_file}")
        
        with open(args.input_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if not text:
            print("❌ Input file is empty")
            sys.exit(1)
        
        if not args.quiet:
            print(f"   Characters: {len(text):,}")
            print(f"   Words: {len(text.split()):,}")
        
        # Generate audio
        if not args.quiet:
            print("\n🎵 Generating audio...")
        
        audio = generator.generate_audio(text)
        
        if audio is None:
            print("❌ Audio generation failed")
            sys.exit(1)
        
        # Save audio
        if not args.quiet:
            print(f"\n💾 Saving audio...")
        
        success = generator.save_audio(audio, args.output)
        
        if success:
            print(f"\n✅ TTS generation complete!")
            print(f"   Output: {args.output}")
        else:
            print("❌ Failed to save audio")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
