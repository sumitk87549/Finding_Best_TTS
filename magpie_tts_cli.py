#!/usr/bin/env python3
"""
Magpie TTS CLI - Text-to-Speech using NVIDIA's Magpie TTS model
Command-line interface for generating speech from text files using Hugging Face model.
"""

import argparse
import os
import sys
import torch
import torchaudio
from transformers import AutoTokenizer, AutoModel
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MagpieTTS:
    def __init__(self, model_name="nvidia/magpie_tts_multilingual_357m"):
        """
        Initialize the Magpie TTS model.
        
        Args:
            model_name (str): Hugging Face model name
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        try:
            logger.info(f"Loading model: {model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def generate_speech(self, text, output_path="output.wav", sample_rate=22050):
        """
        Generate speech from text.
        
        Args:
            text (str): Input text to convert to speech
            output_path (str): Path to save the generated audio
            sample_rate (int): Audio sample rate
        """
        try:
            logger.info("Generating speech from text...")
            
            # Tokenize the input text
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate audio
            with torch.no_grad():
                # This is a placeholder - actual implementation depends on the model's forward method
                # You may need to adjust this based on the actual model architecture
                outputs = self.model.generate(**inputs, max_length=1024)
            
            # Convert to audio waveform (this may need adjustment based on model output)
            # This is a simplified version - actual implementation may vary
            if hasattr(outputs, 'audio_values'):
                audio = outputs.audio_values
            else:
                # Fallback - you may need to implement proper audio extraction
                audio = outputs
            
            # Save the audio
            if len(audio.shape) == 3:  # Batch dimension
                audio = audio.squeeze(0)
            
            torchaudio.save(output_path, audio.cpu(), sample_rate)
            logger.info(f"Audio saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            raise
    
    def read_text_file(self, file_path):
        """
        Read text from a file.
        
        Args:
            file_path (str): Path to the text file
            
        Returns:
            str: Content of the text file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            
            if not text:
                raise ValueError("Text file is empty")
            
            logger.info(f"Successfully read text from: {file_path}")
            return text
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise

def main():
    """Main function to handle command-line interface."""
    parser = argparse.ArgumentParser(
        description="Generate speech from text using NVIDIA Magpie TTS model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python magpie_tts_cli.py -i input.txt -o output.wav
  python magpie_tts_cli.py -i story.txt -o speech.wav --sample-rate 16000
        """
    )
    
    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Path to input text file"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="magpie_output.wav",
        help="Path to output audio file (default: magpie_output.wav)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="nvidia/magpie_tts_multilingual_357m",
        help="Hugging Face model name (default: nvidia/magpie_tts_multilingual_357m)"
    )
    
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=22050,
        help="Audio sample rate (default: 22050)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input file
    if not os.path.exists(args.input):
        logger.error(f"Input file does not exist: {args.input}")
        sys.exit(1)
    
    # Validate output directory
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        logger.info(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir)
    
    try:
        # Initialize TTS model
        tts = MagpieTTS(model_name=args.model)
        
        # Read input text
        text = tts.read_text_file(args.input)
        logger.info(f"Input text length: {len(text)} characters")
        
        # Generate speech
        tts.generate_speech(text, args.output, args.sample_rate)
        
        logger.info("Speech generation completed successfully!")
        print(f"✅ Audio saved to: {args.output}")
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
