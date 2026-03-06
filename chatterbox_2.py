#!/usr/bin/env python3
"""
Chatterbox TTS — Hindi/Hinglish Optimised
==========================================
Key upgrades over original:
  • --voice-file  : supply ANY local WAV/MP3 of an Indian speaker (strongest lever)
  • --voice-url   : supply a direct URL to a voice sample
  • Reliable fallback Indian voice URLs (multiple mirrors per preset)
  • ITRANS transliteration instead of Harvard-Kyoto for Devanagari input
  • Richer text cleaning: stage-directions, section headers, em-dashes, ellipses
  • Better chunk splitting that respects Hindi poetic rhythm
  • Verbose voice-prompt diagnostics so silent fallback never happens again
  • CPU-friendly defaults for Ryzen / laptop use

Usage examples:
  # Best quality — provide your own Indian speaker clip (5-15 sec, clear speech)
  python chatterbox_tts_hindi.py text.txt --voice-file my_indian_voice.wav

  # Use a preset voice (downloads from multiple mirror URLs)
  python chatterbox_tts_hindi.py text.txt --voice indian_male

  # Provide a direct URL to a voice sample
  python chatterbox_tts_hindi.py text.txt --voice-url https://example.com/indian_voice.wav

  # Full example
  python chatterbox_tts_hindi.py translation.txt \\
      --voice-file my_speaker.wav \\
      --exaggeration 0.55 --cfg 0.45 \\
      --chunk-size 250 --device cpu \\
      --output hindi_story.wav
"""

import argparse
import os
import sys
import time
import re
import warnings
from pathlib import Path
from typing import Optional, List, Any

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Preset Indian voice samples — multiple mirrors per voice for reliability
# ksp  = Karthik (Indian male English, CMU ARCTIC)
# axb  = Abirami (Indian female English, CMU ARCTIC)
# ---------------------------------------------------------------------------
VOICE_URLS: dict = {
    "indian_male": [
        # CMU ARCTIC ksp — Karthik (Indian English male)
        "http://festvox.org/cmu_arctic/cmu_arctic/cmu_us_ksp_arctic/wav/arctic_a0001.wav",
        "https://github.com/festvox/cmu_us_ksp_arctic/raw/master/wav/arctic_a0001.wav",
        # OpenSLR mirror
        "https://openslr.org/resources/28/recs/male/ksp/arctic_a0001.wav",
    ],
    "indian_female": [
        # CMU ARCTIC axb — Abirami (Indian English female)
        "http://festvox.org/cmu_arctic/cmu_arctic/cmu_us_axb_arctic/wav/arctic_a0001.wav",
        "https://github.com/festvox/cmu_us_axb_arctic/raw/master/wav/arctic_a0001.wav",
    ],
}


# ---------------------------------------------------------------------------
# Environment check
# ---------------------------------------------------------------------------

def check_environment() -> bool:
    print("Checking environment...")
    ver = sys.version_info
    print(f"   Python {ver.major}.{ver.minor}.{ver.micro}")
    if ver >= (3, 13):
        print("   WARNING: Python 3.13+ may have compatibility issues - prefer 3.10-3.12")

    required = ["torch", "transformers", "numpy", "librosa", "soundfile"]
    for pkg in required:
        try:
            __import__(pkg)
            print(f"   OK: {pkg}")
        except ImportError:
            print(f"   MISSING: {pkg}  (pip install {pkg})")

    try:
        import chatterbox.tts  # noqa: F401
        print("   OK: chatterbox-tts")
        return True
    except ImportError as e:
        print(f"   MISSING: chatterbox-tts: {e}")
        print("\nInstall guide:")
        print("   pip install torch==2.6.0 torchaudio==2.6.0")
        print("   pip install 'numpy>=1.24.0,<1.26.0'")
        print("   pip install transformers==4.46.3 librosa soundfile")
        print("   pip install indic-transliteration chatterbox-tts")
        return False


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

def try_download(urls: List[str], dest: str) -> bool:
    """Try each URL in order until one succeeds. Returns True on success."""
    import requests
    for url in urls:
        try:
            print(f"   Trying: {url}")
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            if len(r.content) < 1000:
                print(f"   Too small ({len(r.content)} bytes) - skipping")
                continue
            with open(dest, "wb") as f:
                f.write(r.content)
            print(f"   Saved to {dest} ({len(r.content) // 1024} KB)")
            return True
        except Exception as e:
            print(f"   Failed: {e}")
    return False


# ---------------------------------------------------------------------------
# Text preprocessing
# ---------------------------------------------------------------------------

def clean_text_for_tts(text: str) -> str:
    """
    Stage-1 cleaning — removes structural elements that confuse TTS:
    section headers, author lines, stage directions, dividers.
    """
    lines = text.splitlines()
    cleaned = []

    skip_patterns = re.compile(
        r"^("
        r"[-=]{3,}"                      # section dividers  --- ===
        r"|JAMES\s+ALLEN"                # author attribution
        r"|AS\s+A\s+MAN\s+THINKETH"     # title lines
        r"|[A-Z][A-Z\s]{4,}"            # all-caps section headers (5+ chars)
        r")$",
        re.IGNORECASE,
    )
    # Stage-direction patterns: (Pause...) [deep breath] *smiles*
    stage_dir = re.compile(r"[\(\[\*].*?[\)\]\*]")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if skip_patterns.match(line):
            continue
        line = stage_dir.sub("", line).strip()
        if line:
            cleaned.append(line)

    text = " ".join(cleaned)

    # Normalise punctuation for natural TTS pausing
    text = re.sub(r"\.{3,}", ", ", text)        # ellipsis -> short pause
    text = re.sub(r"\s*—\s*", ", ", text)       # em-dash -> comma pause
    text = re.sub(r"\s*–\s*", ", ", text)       # en-dash -> comma pause
    text = re.sub(r"\s{2,}", " ", text)         # collapse extra spaces
    text = re.sub(r",\s*,", ",", text)          # no double commas
    return text.strip()


def transliterate_devanagari(text: str) -> str:
    """
    Convert Devanagari to ITRANS romanisation with post-processing for
    better English-TTS pronunciation.
    ITRANS is far more phonetically intuitive than Harvard-Kyoto (HK):
      दिमाग  ->  dimaag  (vs HK: dimAga which TTS reads as "dim-AY-ga")
    Lines without Devanagari are passed through unchanged.
    """
    try:
        from indic_transliteration import sanscript
        lines = text.split("\n")
        out = []
        for line in lines:
            if any("\u0900" <= c <= "\u097F" for c in line):
                converted = sanscript.transliterate(
                    line, sanscript.DEVANAGARI, sanscript.ITRANS
                )
                # Make long vowels more natural for English TTS
                # ITRANS: aa stays aa (good), ii -> ee, uu -> oo
                converted = converted.replace("ii", "ee").replace("uu", "oo")
                # Remove trailing virama artefacts
                converted = re.sub(r"\bH\b", "", converted)
                out.append(converted)
            else:
                out.append(line)
        return "\n".join(out)
    except ImportError:
        print("WARNING: indic-transliteration not installed - Devanagari will not be converted")
        print("         pip install indic-transliteration")
        return text


def preprocess(text: str) -> str:
    text = clean_text_for_tts(text)
    text = transliterate_devanagari(text)
    return text


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def split_chunks(text: str, max_chars: int = 250) -> List[str]:
    """
    Split on sentence endings first, then on commas for long sentences.
    250 chars is the sweet-spot for Chatterbox on CPU: large enough for
    natural prosody, small enough to avoid memory issues on a Ryzen laptop.
    """
    segments = re.split(r"(?<=[.!?])\s+", text.strip())

    fine: List[str] = []
    for seg in segments:
        if len(seg) <= max_chars:
            fine.append(seg)
        else:
            sub = re.split(r"(?<=,)\s+", seg)
            buf = ""
            for s in sub:
                if len(buf) + len(s) + 1 <= max_chars:
                    buf = (buf + " " + s).strip()
                else:
                    if buf:
                        fine.append(buf)
                    buf = s
            if buf:
                fine.append(buf)

    # Merge tiny orphan segments (< 30 chars) with the previous chunk
    merged: List[str] = []
    for seg in fine:
        if merged and len(merged[-1]) < 30:
            merged[-1] = merged[-1] + " " + seg
        else:
            merged.append(seg)

    return [s.strip() for s in merged if s.strip()] or [text]


# ---------------------------------------------------------------------------
# Main TTS class
# ---------------------------------------------------------------------------

class HindiChatterboxTTS:

    def __init__(self, device: str = "auto"):
        self.device = self._detect_device(device)
        self.model = None

    def _detect_device(self, device: str) -> str:
        if device != "auto":
            return device
        try:
            import torch
            if torch.cuda.is_available():
                print(f"CUDA available: {torch.cuda.get_device_name(0)}")
                return "cuda"
        except ImportError:
            pass
        print("Using CPU  (Ryzen tip: close background apps, set power plan to Performance)")
        return "cpu"

    def load_model(self) -> bool:
        print("Loading Chatterbox model...")
        try:
            from chatterbox.tts import ChatterboxTTS
            t0 = time.time()
            self.model = ChatterboxTTS.from_pretrained(device=self.device)
            print(f"Model ready on {self.device} in {time.time() - t0:.1f}s  (sr={self.model.sr} Hz)")
            return True
        except Exception as e:
            print(f"Model load failed: {e}")
            return False

    def resolve_voice_prompt(
        self,
        voice_file: Optional[str],
        voice_url: Optional[str],
        voice_preset: str,
    ) -> Optional[str]:
        """
        Priority order:
          1. --voice-file  (local file — best option, use this!)
          2. --voice-url   (direct URL you supply)
          3. --voice       preset (tries multiple mirror URLs automatically)
          4. None -> Chatterbox default (American English — avoid for Hindi)
        """
        # 1. Local file
        if voice_file:
            if os.path.exists(voice_file):
                size_kb = os.path.getsize(voice_file) // 1024
                print(f"Using local voice file: {voice_file} ({size_kb} KB)")
                return voice_file
            else:
                print(f"ERROR: --voice-file not found: {voice_file}")
                sys.exit(1)

        # 2. Direct URL
        if voice_url:
            dest = "voice_custom_url.wav"
            print(f"Downloading voice from URL: {voice_url}")
            if try_download([voice_url], dest):
                return dest
            print("URL download failed - continuing without voice prompt (may sound American)")
            return None

        # 3. Preset
        if voice_preset != "default":
            urls = VOICE_URLS.get(voice_preset, [])
            if urls:
                dest = f"voice_{voice_preset}.wav"
                if os.path.exists(dest):
                    print(f"Using cached preset voice: {dest}")
                    return dest
                print(f"Downloading preset voice '{voice_preset}' (trying {len(urls)} mirrors)...")
                if try_download(urls, dest):
                    return dest
                print(f"All preset mirrors failed for '{voice_preset}'")
                print("Best fix: record 5-15s of clear Indian speech and use --voice-file")

        print("No voice prompt resolved - using Chatterbox default voice (likely American accent)")
        print("For Indian accent: --voice-file your_indian_speaker.wav  (record or download a clip)")
        return None

    def generate(
        self,
        text: str,
        voice_prompt: Optional[str],
        chunk_size: int,
        exaggeration: float,
        cfg_weight: float,
    ) -> Optional[Any]:
        if not self.model:
            return None

        processed = preprocess(text)
        chunks = split_chunks(processed, chunk_size)
        print(f"Text split into {len(chunks)} chunk(s) after preprocessing")

        import torch
        wavs = []
        t_total = time.time()

        for i, chunk in enumerate(chunks, 1):
            if not chunk.strip():
                continue
            preview = chunk[:70].replace("\n", " ")
            print(f"Chunk {i}/{len(chunks)} ({len(chunk)} chars): {preview}...")
            t0 = time.time()
            wav = self.model.generate(
                chunk,
                audio_prompt_path=voice_prompt,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
            )
            dur = wav.shape[-1] / self.model.sr
            print(f"   Done in {time.time() - t0:.1f}s -> {dur:.1f}s audio")
            wavs.append(wav)

        if not wavs:
            print("No audio generated")
            return None

        final = torch.cat(wavs, dim=-1)
        total_dur = final.shape[-1] / self.model.sr
        elapsed = time.time() - t_total
        print(f"\nGeneration complete: {total_dur:.1f}s audio in {elapsed:.1f}s (RTF {elapsed / total_dur:.1f}x)")
        return final

    def save(self, audio: Any, path: str) -> bool:
        try:
            import soundfile as sf
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
            arr = audio.squeeze().cpu().numpy()
            sf.write(path, arr, self.model.sr)
            mb = os.path.getsize(path) / 1e6
            dur = len(arr) / self.model.sr
            print(f"Saved: {path}  ({dur:.1f}s, {mb:.1f} MB)")
            return True
        except Exception as e:
            print(f"Save failed: {e}")
            return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Chatterbox TTS - Hindi/Hinglish optimised",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
BEST QUALITY (Indian accent):
  1. Record 5-15 seconds of a clear Indian speaker (any topic, quiet room).
  2. Save as WAV.
  3. Pass with --voice-file my_speaker.wav

QUICK EXAMPLES:
  python chatterbox_tts_hindi.py text.txt --voice indian_male
  python chatterbox_tts_hindi.py text.txt --voice-file my_voice.wav -o out.wav
        """,
    )

    p.add_argument("input_file", help="Input .txt file")

    vg = p.add_argument_group("Voice (priority: --voice-file > --voice-url > --voice)")
    vg.add_argument(
        "--voice-file",
        metavar="PATH",
        help="BEST: local WAV/MP3 of an Indian speaker (5-15 sec, clear speech in a quiet room)",
    )
    vg.add_argument(
        "--voice-url",
        metavar="URL",
        help="Direct URL to a voice sample WAV/MP3",
    )
    vg.add_argument(
        "--voice",
        choices=["default", "indian_male", "indian_female"],
        default="default",
        help="Preset voice (used only if no --voice-file or --voice-url)",
    )

    p.add_argument("--exaggeration", type=float, default=0.55,
                   help="Expressivity 0.0-1.0  (default 0.55; for calm Hindi narration try 0.4-0.6)")
    p.add_argument("--cfg", type=float, default=0.45,
                   help="CFG weight 0.0-1.0  (default 0.45; lower = more natural pacing)")
    p.add_argument("--chunk-size", type=int, default=250,
                   help="Max chars per chunk  (default 250; reduce to 150 if out-of-memory on CPU)")
    p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    p.add_argument("-o", "--output", help="Output WAV path")
    p.add_argument("-q", "--quiet", action="store_true")

    args = p.parse_args()

    for name, val in [("exaggeration", args.exaggeration), ("cfg", args.cfg)]:
        if not 0.0 <= val <= 1.0:
            print(f"ERROR: --{name} must be 0.0-1.0")
            sys.exit(1)

    if not os.path.exists(args.input_file):
        print(f"ERROR: File not found: {args.input_file}")
        sys.exit(1)

    if not args.output:
        args.output = Path(args.input_file).stem + "_chatterbox.wav"

    if not check_environment():
        sys.exit(1)

    print("\nChatterbox TTS - Hindi/Hinglish Mode")
    print("=" * 50)

    tts = HindiChatterboxTTS(device=args.device)
    if not tts.load_model():
        sys.exit(1)

    voice_prompt = tts.resolve_voice_prompt(
        voice_file=args.voice_file,
        voice_url=args.voice_url,
        voice_preset=args.voice,
    )

    text = Path(args.input_file).read_text(encoding="utf-8").strip()
    if not text:
        print("ERROR: Empty input file")
        sys.exit(1)
    print(f"Input: {len(text):,} chars, {len(text.split()):,} words")

    audio = tts.generate(
        text=text,
        voice_prompt=voice_prompt,
        chunk_size=args.chunk_size,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg,
    )

    if audio is None:
        sys.exit(1)

    tts.save(audio, args.output)
    print(f"\nOutput: {args.output}")


if __name__ == "__main__":
    main()
