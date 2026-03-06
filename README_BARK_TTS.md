# Bark TTS - Text-to-Speech with Suno's Bark Model

A Python script that loads the Suno Bark model from HuggingFace and generates TTS from text files via command line.

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. The script will automatically download the Bark model on first run.

## Usage

### Basic Usage
```bash
python bark_tts.py --input input.txt --output output.wav
```

### Advanced Usage
```bash
python bark_tts.py -i input.txt -o output.wav --voice_preset v2/en_speaker_6 --temperature 0.8
```

### Command Line Arguments

- `-i, --input`: Input text file path (required)
- `-o, --output`: Output audio file path (required)
- `--voice_preset`: Voice preset to use (default: v2/en_speaker_6)
- `--temperature`: Generation temperature (0.1-1.0, default: 0.7)
- `--min_eos_p`: Minimum end-of-sentence probability (default: 0.05)
- `--device`: Device to use (auto/cpu/cuda, default: auto)
- `--model`: HuggingFace model name (default: suno/bark)

## Voice Presets

### English Speakers
- `v2/en_speaker_0` through `v2/en_speaker_9`

### Other Languages
- German: `v2/de_speaker_1` through `v2/de_speaker_8`
- Spanish: `v2/es_speaker_1` through `v2/es_speaker_9`
- French: `v2/fr_speaker_1` through `v2/fr_speaker_9`
- Hindi: `v2/hi_speaker_1` through `v2/hi_speaker_8`
- Italian: `v2/it_speaker_1` through `v2/it_speaker_9`
- Polish: `v2/pl_speaker_1` through `v2/pl_speaker_9`
- Portuguese: `v2/pt_speaker_1` through `v2/pt_speaker_9`
- Russian: `v2/ru_speaker_1` through `v2/ru_speaker_9`
- Chinese: `v2/zh_speaker_1` through `v2/zh_speaker_9`

## Examples

### Generate speech with default English voice:
```bash
python bark_tts.py -i test_bark_input.txt -o test_output.wav
```

### Generate speech with Hindi voice:
```bash
python bark_tts.py -i hindi_text.txt -o hindi_output.wav --voice_preset v2/hi_speaker_1
```

### Generate speech with higher creativity:
```bash
python bark_tts.py -i story.txt -o story.wav --temperature 0.9 --voice_preset v2/en_speaker_3
```

## Output Formats

The script supports multiple audio formats based on the file extension:
- `.wav` - WAV format (default)
- `.mp3` - MP3 format
- `.flac` - FLAC format

## Performance Tips

1. **First Run**: The model download may take several minutes on first run.
2. **GPU Usage**: Use `--device cuda` if you have a compatible GPU for faster generation.
3. **Memory**: The script uses CPU offloading for memory efficiency on CPU.
4. **Batch Processing**: For multiple files, you can use shell loops:
   ```bash
   for file in *.txt; do
       python bark_tts.py -i "$file" -o "${file%.txt}.wav"
   done
   ```

## Troubleshooting

### Common Issues

1. **Out of Memory**: Try using `--device cpu` or reduce input text length.
2. **Slow Generation**: Ensure you have sufficient RAM and consider GPU usage.
3. **Model Download Fails**: Check internet connection and HuggingFace access.

### Dependencies

If you encounter import errors, install manually:
```bash
pip install torch torchaudio transformers soundfile
```

## Features

- ✅ Loads Bark model from HuggingFace
- ✅ Command-line interface
- ✅ Multiple voice presets and languages
- ✅ Configurable generation parameters
- ✅ Multiple audio output formats
- ✅ Automatic device detection
- ✅ Memory-efficient CPU offloading
- ✅ Error handling and validation
