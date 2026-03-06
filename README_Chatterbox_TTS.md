# Chatterbox TTS CLI Script

A comprehensive command-line interface for ResembleAI's Chatterbox Text-to-Speech model with full parameter control and voice options.

## Features

- 🎤 **Multiple Voice Options**: Default, Indian male/female, custom voice files
- 🎛️ **Full Parameter Control**: Pitch, speed, expressivity, CFG weight
- 🌍 **Multilingual Support**: Automatic Devanagari to Latin transliteration
- 💻 **Low-Spec Friendly**: CPU mode with memory optimization
- 📱 **Easy to Use**: Simple command-line interface
- 🔄 **Batch Processing**: Automatic text chunking for long inputs

## Installation

The script automatically handles dependency installation. Just run:

```bash
python chatterbox_tts.py --help
```

## Quick Start

### Basic Usage
```bash
python chatterbox_tts.py input.txt
```

### With Indian Voice
```bash
python chatterbox_tts.py input.txt --voice indian_male
```

### Custom Parameters
```bash
python chatterbox_tts.py input.txt --voice indian_female --speed 1.2 --pitch 2 --exaggeration 0.8
```

## Command Line Options

### Required Arguments
- `input_file`: Path to text file containing text to convert

### Voice Options
- `--voice {default,indian_male,indian_female}`: Pre-defined voice selection (default: default)
- `--custom-voice PATH`: Path to custom voice WAV file

### Audio Parameters
- `--pitch FLOAT`: Pitch adjustment in semitones (-12.0 to 12.0, default: 0.0)
- `--speed FLOAT`: Speed adjustment factor (0.5 to 2.0, default: 1.0)
- `--exaggeration FLOAT`: Expressivity/exaggeration (0.0 to 1.0, default: 0.5)
- `--cfg FLOAT`: CFG weight (0.0 to 1.0, default: 0.5)

### Technical Settings
- `--device {auto,cpu,cuda}`: Device to use (default: auto)
- `--chunk-size INT`: Text chunk size for memory management (default: 500)

### Output Options
- `-o, --output PATH`: Output audio file path
- `--format {wav,flac,ogg}`: Audio format (default: wav)

### Other Options
- `--no-transliterate`: Disable Devanagari to Latin transliteration
- `--quiet, -q`: Reduce output verbosity

## Usage Examples

### 1. Basic TTS Generation
```bash
python chatterbox_tts.py input.txt
```
*Uses default voice and settings*

### 2. Indian Voice with Custom Speed
```bash
python chatterbox_tts.py input.txt --voice indian_male --speed 1.2
```
*Uses Indian male voice with 20% faster speech*

### 3. Expressive Speech
```bash
python chatterbox_tts.py input.txt --exaggeration 0.8 --cfg 0.3 --pitch 1
```
*More expressive speech with slight pitch increase*

### 4. CPU Mode for Low-Spec Systems
```bash
python chatterbox_tts.py input.txt --device cpu --chunk-size 300
```
*Optimized for systems without GPU*

### 5. Custom Voice File
```bash
python chatterbox_tts.py input.txt --custom-voice my_voice.wav --output custom_output.wav
```
*Uses your own voice sample for cloning*

### 6. High-Quality Output
```bash
python chatterbox_tts.py input.txt --voice indian_female --format flac --exaggeration 0.7
```
*High-quality FLAC output with expressive speech*

## Parameter Guide

### Voice Selection
- **default**: Neutral American voice
- **indian_male**: Indian-accented male voice
- **indian_female**: Indian-accented female voice
- **custom**: Your own voice sample (5-15 seconds recommended)

### Audio Parameters
- **Pitch**: 
  - Negative values = lower pitch
  - Positive values = higher pitch
  - Range: -12 to +12 semitones
- **Speed**:
  - 0.5 = half speed
  - 1.0 = normal speed
  - 2.0 = double speed
- **Exaggeration**:
  - 0.0 = neutral speech
  - 0.5 = balanced (default)
  - 1.0 = highly expressive
- **CFG Weight**:
  - Lower values (0.3) = more creative/expression
  - Higher values (0.7) = more stable/consistent

### Device Settings
- **auto**: Automatically detects GPU (recommended)
- **cpu**: Forces CPU usage (for low-spec systems)
- **cuda**: Forces GPU usage (if available)

## Text Processing

### Devanagari Support
The script automatically transliterates Devanagari text to Latin script for natural pronunciation:

```
Input:  "यार... Sherlock Holmes बोला"
Output: "yaar... Sherlock Holmes bola"
```

### Text Chunking
Long texts are automatically split into manageable chunks (default 500 characters) to:
- Prevent memory issues
- Allow progress tracking
- Handle very long inputs

## File Requirements

### Input Text File
- Plain text (.txt) file
- UTF-8 encoding recommended
- Supports mixed languages (Hinglish, etc.)
- No strict size limit (auto-chunked)

### Custom Voice Files (Optional)
- WAV format
- 5-15 seconds duration
- Clean speech, minimal background noise
- Sample rate: 16kHz or higher

## Performance Tips

### For Low-Spec Systems
```bash
python chatterbox_tts.py input.txt --device cpu --chunk-size 300 --quiet
```

### For Faster Generation
```bash
python chatterbox_tts.py input.txt --chunk-size 200 --device cuda
```

### For Best Quality
```bash
python chatterbox_tts.py input.txt --exaggeration 0.7 --cfg 0.4 --format flac
```

## Troubleshooting

### Common Issues

1. **Memory Issues**: Reduce chunk-size or use CPU mode
2. **Slow Generation**: Use smaller chunk-size or GPU mode
3. **Voice Not Found**: Check internet connection for voice downloads
4. **Dependency Issues**: Let the script auto-install dependencies

### Error Messages

- **"Model not loaded"**: Try running with `--device cpu`
- **"Missing dependencies"**: Script will auto-install, just wait
- **"Voice file not found"**: Check custom voice file path

## Example Files

Run the example script to see different usage patterns:

```bash
python example_usage.py
```

This will demonstrate:
- Basic usage
- Different voice options
- Parameter combinations
- CPU vs GPU modes

## Output

The script generates:
- Audio file (WAV/FLAC/OGG format)
- Progress information during generation
- Performance metrics (duration, processing time)
- File size and format details

## Technical Details

- **Model**: ResembleAI Chatterbox (0.5B parameters)
- **Download Size**: ~1GB (first time only)
- **Memory Usage**: 2-4GB RAM
- **Sample Rate**: 22050 Hz
- **Audio Quality**: Production-grade

## License

This script uses ResembleAI's Chatterbox model (MIT License) and includes additional functionality for CLI usage.
