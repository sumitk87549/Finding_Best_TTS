# F5-Hindi TTS Audio Generation

This script generates Text-to-Speech (TTS) audio from Hindi text using the SPRINGLab/F5-Hindi-24KHz model from HuggingFace.

## Requirements

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. **Ensure you have the following files:**
   - `hin1.txt` - Hindi text file to convert to speech
   - `Access_Token.txt` - Your HuggingFace access token
   - Reference audio file (required for F5-TTS zero-shot voice cloning)

2. **Provide Reference Audio:**
   
   F5-TTS is a zero-shot voice cloning model that requires a short reference audio clip (3-10 seconds) and its corresponding text. You need to:
   
   - Place a Hindi reference audio file (e.g., `ref_audio.wav`)
   - Update the `REF_AUDIO` and `REF_TEXT` variables in the script

3. **Run the script:**

```bash
python SPRINGLab__F5-Hindi-24KHz.py
```

4. **Output:**
   
   The generated audio will be saved in the `TTS/` directory with the naming format:
   ```
   TTS/SPRINGLab__F5-Hindi-24KHz__YYYYMMDD_HHMMSS.wav
   ```

## Configuration

Edit the following variables in the script as needed:

- `MODEL_NAME`: HuggingFace model identifier
- `TEXT_FILE`: Input Hindi text file
- `TOKEN_FILE`: HuggingFace access token file
- `OUTPUT_DIR`: Directory to save output audio
- `REF_AUDIO`: Reference audio file path
- `REF_TEXT`: Text corresponding to reference audio

## Notes

- The model uses 24kHz sample rate
- Output format is WAV
- Requires CUDA for GPU acceleration (will use CPU if not available)
- Reference audio should be 3-10 seconds long for best results

## Troubleshooting

If you encounter issues:
1. Ensure your HuggingFace token has access to the model
2. Check that reference audio exists and is in WAV format
3. Verify all dependencies are installed correctly
4. For GPU support, ensure PyTorch is installed with CUDA support
