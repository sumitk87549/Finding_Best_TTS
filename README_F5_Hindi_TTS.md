# F5-Hindi-24KHz TTS CLI Script

This script provides a command-line interface for generating Hindi text-to-speech using the SPRINGLab F5-Hindi-24KHz model from HuggingFace.

## Features

- 🎯 High-quality Hindi TTS using F5-TTS architecture
- 📝 Handles long texts through automatic chunking
- 💻 Automatic device detection (CPU/CUDA)
- 📥 Automatic model download from HuggingFace
- 🔧 Simple command-line interface

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Test installation:**
   ```bash
   python test_f5_installation.py
   ```

## Usage

### Basic Usage

```bash
python f5_hindi_tts.py input.txt
```

### Advanced Usage

```bash
# Specify output file
python f5_hindi_tts.py input.txt --output my_audio.wav

# Use CPU instead of GPU
python f5_hindi_tts.py input.txt --device cpu

# Adjust chunk size for memory management
python f5_hindi_tts.py input.txt --chunk-size 150

# Force re-download of model files
python f5_hindi_tts.py input.txt --force-download

# Quiet mode (less verbose output)
python f5_hindi_tts.py input.txt --quiet
```

## Command Line Options

- `input_file`: Path to Hindi text file (required)
- `--device`: Device to use (`auto`, `cpu`, `cuda`) [default: auto]
- `--output`: Output audio file path [default: {input_name}_f5_hindi_tts.wav]
- `--chunk-size`: Text chunk size for memory management [default: 200]
- `--force-download`: Force re-download of model files
- `--quiet, -q`: Reduce output verbosity

## Input Text Format

- Supports Hindi text in Devanagari script
- UTF-8 encoding recommended
- Automatically handles text chunking for long inputs
- Removes excessive whitespace automatically

## Model Information

- **Model**: SPRINGLab/F5-Hindi-24KHz
- **Architecture**: F5-TTS (Flow Matching)
- **Language**: Hindi
- **Sample Rate**: 24kHz
- **License**: CC-BY-4.0

## Example

Given an input file `hindi_story.txt` containing:
```
नमस्ते! यह एक उदाहरण है। F5-Hindi-24KHz मॉडल बहुत अच्छा है।
```

Run:
```bash
python f5_hindi_tts.py hindi_story.txt
```

This will generate `hindi_story_f5_hindi_tts.wav` with the synthesized speech.

## Troubleshooting

### Common Issues

1. **CUDA out of memory**: Use `--device cpu` or reduce `--chunk-size`
2. **Model download fails**: Check internet connection and try `--force-download`
3. **Audio quality issues**: Ensure input text is clean Hindi in Devanagari script

### Requirements

- Python 3.8+
- PyTorch
- TorchAudio
- F5-TTS
- HuggingFace Hub
- ~2GB disk space for model files

## Model Details

The F5-Hindi-24KHz model was trained by SPRING Lab, IIT Madras on:
- IndicTTS-Hindi dataset
- IndicVoices-R Hindi dataset
- 151M parameters (small configuration)
- 8x A100 40GB GPUs for one week

For more information, visit: https://huggingface.co/SPRINGLab/F5-Hindi-24KHz
