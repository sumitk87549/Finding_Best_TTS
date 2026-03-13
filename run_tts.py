#!/usr/bin/env python3
"""
run_tts.py — Generate speech with fishaudio/s2-pro on local CPU
=================================================================
3-step pipeline (mirrors the working Colab notebook exactly):
  Step 1 (optional) — DAC encode reference audio for voice cloning
  Step 2            — text2semantic: text → semantic codes  [the slow step]
  Step 3            — DAC decode: semantic codes → wav audio

Usage examples:
  # Basic TTS (random voice)
  python3 run_tts.py --text "Hello, this is a test."

  # Hindi text
  python3 run_tts.py --text "नमस्ते। यह एक परीक्षण है।"

  # With reference audio for voice cloning
  python3 run_tts.py --text "Hello world." --ref-audio my_voice.wav

  # Force-reinstall fish-speech (fixes 'Unknown model type: fish_qwen3_omni')
  python3 run_tts.py --text "Hello." --fix-fishspeech
"""

import argparse
import gc
import glob
import os
import shlex
import subprocess
import sys
import time

# ── Default paths ─────────────────────────────────────────────────────────────
HOME          = os.path.expanduser("~")
DEFAULT_WORK  = os.path.join(HOME, "s2pro_tts")
DEFAULT_MODEL = os.path.join(DEFAULT_WORK, "checkpoints", "s2-pro")
DEFAULT_OUT   = os.path.join(DEFAULT_WORK, "inference_outputs")
VENV_PYTHON   = os.path.join(DEFAULT_WORK, "venv", "bin", "python3")


# ─────────────────────────────────────────────────────────────────────────────
# PYTHON RESOLVER
# Picks the interpreter that has a compatible fish-speech (one that knows
# about 'fish_qwen3_omni' — the model type used by s2-pro).
# Priority: 1) s2pro venv  2) current Python  3) fix current Python
# ─────────────────────────────────────────────────────────────────────────────

def _fish_speech_ok(python_exe: str) -> bool:
    """Return True if this Python's fish-speech supports fish_qwen3_omni."""
    code = (
        "import sys; "
        "import fish_speech.models.text2semantic.llama as m; "
        "src = open(m.__file__).read(); "
        "sys.exit(0 if 'fish_qwen3_omni' in src else 1)"
    )
    try:
        r = subprocess.run(
            [python_exe, "-c", code],
            capture_output=True, timeout=20
        )
        return r.returncode == 0
    except Exception:
        return False


def _install_fish_speech(python_exe: str):
    """Uninstall stale fish-speech and reinstall latest from GitHub HEAD."""
    print("  Uninstalling old fish-speech...")
    subprocess.run(
        [python_exe, "-m", "pip", "uninstall", "-y", "fish-speech"],
        capture_output=True
    )
    print("  Installing latest fish-speech from GitHub (may take a few minutes)...")
    r = subprocess.run([
        python_exe, "-m", "pip", "install",
        "--upgrade", "--no-deps", "--force-reinstall",
        "git+https://github.com/fishaudio/fish-speech.git",
    ])
    if r.returncode != 0:
        print("\n[ERROR] pip install of fish-speech failed.")
        print("  Check your internet connection and try again.")
        sys.exit(1)


def resolve_python() -> str:
    """Return the path to a Python that has working s2-pro fish-speech."""

    # --- Try the venv first (created by setup_s2pro.sh) ---
    if os.path.isfile(VENV_PYTHON):
        if _fish_speech_ok(VENV_PYTHON):
            print(f"  Python  : {VENV_PYTHON}  [venv OK]")
            return VENV_PYTHON
        else:
            print(f"  Venv fish-speech is outdated — updating...")
            _install_fish_speech(VENV_PYTHON)
            if _fish_speech_ok(VENV_PYTHON):
                print(f"  Python  : {VENV_PYTHON}  [venv updated OK]")
                return VENV_PYTHON

    # --- Try current interpreter (e.g. conda base) ---
    cur = sys.executable
    if _fish_speech_ok(cur):
        print(f"  Python  : {cur}  [current env OK]")
        return cur

    # --- Fix current interpreter ---
    print(f"\n  fish-speech in '{cur}' does not support s2-pro (fish_qwen3_omni).")
    print(f"  Installing latest fish-speech into current Python...")
    _install_fish_speech(cur)
    if _fish_speech_ok(cur):
        print(f"  Python  : {cur}  [fixed OK]")
        return cur

    print("\n[ERROR] Could not get a working fish-speech install.")
    print("  Try:  bash ~/Downloads/setup_s2pro.sh")
    sys.exit(1)


# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        description="Generate TTS with fishaudio/s2-pro on CPU"
    )
    p.add_argument("--text", "-t", required=True,
                   help="Text to synthesise (any language).")
    p.add_argument("--ref-audio", "-r", default="", metavar="WAV",
                   help="Short WAV for voice cloning (optional).")
    p.add_argument("--model-dir", "-m", default=DEFAULT_MODEL,
                   help=f"Checkpoint dir. Default: {DEFAULT_MODEL}")
    p.add_argument("--output-dir", "-o", default=DEFAULT_OUT,
                   help=f"Output dir. Default: {DEFAULT_OUT}")
    p.add_argument("--threads", type=int, default=4,
                   help="CPU threads. Default 4 = all physical cores on Ryzen 5 7520U.")
    p.add_argument("--no-half", action="store_true",
                   help="Use float32 instead of bfloat16. Uses ~4 GB more RAM — not recommended on 8 GB.")
    p.add_argument("--fix-fishspeech", action="store_true",
                   help="Force-reinstall fish-speech from GitHub, then run.")
    return p.parse_args()


# ── Utilities ─────────────────────────────────────────────────────────────────
def section(title: str):
    bar = "─" * 60
    print(f"\n{bar}\n  {title}\n{bar}")


def check_model(model_dir: str):
    if not os.path.isdir(model_dir):
        print(f"\n[ERROR] Model directory not found:\n  {model_dir}")
        print("  Run setup_s2pro.sh first to download the model.")
        sys.exit(1)
    shards = glob.glob(os.path.join(model_dir, "*.safetensors"))
    if not shards:
        print(f"\n[ERROR] No .safetensors files in:\n  {model_dir}")
        print("  Download may be incomplete — re-run setup_s2pro.sh.")
        sys.exit(1)
    print(f"  Model   : OK  ({len(shards)} shard(s))")


def check_swap():
    try:
        info = open("/proc/meminfo").read()
        kb = int(next(l for l in info.splitlines()
                      if l.startswith("SwapTotal")).split()[1])
        gb = kb / 1048576
        if gb < 8:
            print(f"  [WARN] Only {gb:.1f} GB swap — need ≥ 16 GB for 8 GB RAM systems.")
            print("         Run:  sudo swapon /swapfile_s2pro")
        else:
            print(f"  Swap    : {gb:.1f} GB active  OK")
    except Exception:
        pass


def show_memory():
    r = subprocess.run(["free", "-h"], capture_output=True, text=True)
    if r.returncode == 0:
        for line in r.stdout.strip().splitlines():
            print(f"    {line}")


def get_site_packages(python_exe: str) -> str:
    r = subprocess.run(
        [python_exe, "-c",
         "import sysconfig; print(sysconfig.get_path('purelib'))"],
        capture_output=True, text=True
    )
    return r.stdout.strip()


def run_cmd(cmd: str, label: str, python_exe: str, threads: int) -> bool:
    """Run a subprocess with streaming output and the correct env."""
    print(f"\n$ {cmd}\n")

    env = os.environ.copy()
    env["OMP_NUM_THREADS"]        = str(threads)
    env["MKL_NUM_THREADS"]        = str(threads)
    env["OPENBLAS_NUM_THREADS"]   = str(threads)
    env["CUDA_VISIBLE_DEVICES"]   = ""       # no GPU on this laptop
    env["ACCELERATE_USE_CPU"]     = "true"
    env["HF_HUB_OFFLINE"]         = "1"      # model already downloaded
    env["MALLOC_TRIM_THRESHOLD_"] = "0"      # help OS reclaim pages faster

    # Inject the chosen interpreter's site-packages into PYTHONPATH so that
    # the shell command picks up the RIGHT fish-speech even if launched from
    # a different conda/system Python env.
    site = get_site_packages(python_exe)
    if site:
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{site}:{existing}" if existing else site

    start = time.time()
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        shell=True, text=True, env=env
    )
    for line in proc.stdout:
        print(line, end="", flush=True)
    proc.wait()
    elapsed = time.time() - start

    if proc.returncode == 0:
        print(f"\n[OK] {label} — {elapsed:.1f}s")
        return True
    print(f"\n[FAIL] {label} — exit code {proc.returncode}  ({elapsed:.1f}s)")
    return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    args = parse_args()

    print("\n" + "=" * 62)
    print("  fishaudio/s2-pro  —  Local CPU TTS  (Ryzen 5 7520U)")
    print("=" * 62)

    # --fix-fishspeech: force reinstall before anything else
    if args.fix_fishspeech:
        print("\n  Forcing fish-speech reinstall from GitHub...")
        target = VENV_PYTHON if os.path.isfile(VENV_PYTHON) else sys.executable
        _install_fish_speech(target)
        print("  Reinstall done.\n")

    # ── Resolve Python ────────────────────────────────────────────────────────
    section("Resolving Python / fish-speech")
    python_exe = resolve_python()

    print(f"\n  Text    : {args.text[:80]}{'...' if len(args.text) > 80 else ''}")
    print(f"  Model   : {args.model_dir}")
    print(f"  Out     : {args.output_dir}")
    print(f"  Threads : {args.threads}")
    print(f"  Prec.   : {'bfloat16 (half)' if not args.no_half else 'float32'}")
    print(f"  Ref wav : {args.ref_audio or '(none — random voice)'}")

    # ── Pre-flight checks ─────────────────────────────────────────────────────
    section("Pre-flight checks")
    check_model(args.model_dir)
    check_swap()
    print()
    show_memory()

    os.makedirs(args.output_dir, exist_ok=True)
    gc.collect()
    t0 = time.time()

    # =========================================================================
    # STEP 1 — Reference audio encoding (optional, for voice cloning)
    # =========================================================================
    prompt_tokens_path = ""
    if args.ref_audio:
        if not os.path.exists(args.ref_audio):
            print(f"\n[WARN] Ref audio not found: {args.ref_audio} — skipping.")
        else:
            section("Step 1 / 3  —  Encoding reference audio")
            cmd_enc = (
                f"{shlex.quote(python_exe)} -m fish_speech.models.dac.inference"
                f" -i {shlex.quote(args.ref_audio)}"
                f" --checkpoint-path {shlex.quote(args.model_dir)}"
                f" --output-dir {shlex.quote(args.output_dir)}"
                f" --device cpu"
            )
            if run_cmd(cmd_enc, "Ref encoding", python_exe, args.threads):
                npys = sorted(glob.glob(os.path.join(args.output_dir, "*.npy")))
                if npys:
                    prompt_tokens_path = npys[-1]
                    print(f"  Prompt tokens → {prompt_tokens_path}")
    else:
        section("Step 1 / 3  —  Reference encoding (skipped — no ref audio)")

    # =========================================================================
    # STEP 2 — text2semantic  [the slow step]
    # =========================================================================
    section("Step 2 / 3  —  text2semantic  (the slow part — leave it running)")
    print(
        "  The progress bar shows '0/32688' — 32688 is just a MAX cap.\n"
        "  Inference stops at EOS, which typically arrives after\n"
        "  150-300 steps for a short sentence.\n"
        "\n"
        "  Time estimates on Ryzen 5 7520U (8 GB RAM + 20 GB swap):\n"
        "    Model load  :  ~60-90 seconds\n"
        "    Per step    :  ~20-30 seconds\n"
        "    Short text  :  1-2 hours total\n"
        "\n"
        "  You can leave the terminal open and come back later.\n"
    )

    text_arg = args.text.replace("\n", " ")
    cmd_t2s = (
        f"{shlex.quote(python_exe)} -m fish_speech.models.text2semantic.inference"
        f" --text {shlex.quote(text_arg)}"
        f" --checkpoint-path {shlex.quote(args.model_dir)}"
        f" --output-dir {shlex.quote(args.output_dir)}"
        f" --device cpu"
    )
    if not args.no_half:
        cmd_t2s += " --half"      # bfloat16 — cuts peak RAM by ~4 GB
    if prompt_tokens_path:
        cmd_t2s += (
            f" --prompt-tokens {shlex.quote(prompt_tokens_path)}"
            f" --prompt-text {shlex.quote(text_arg)}"
        )

    if not run_cmd(cmd_t2s, "text2semantic", python_exe, args.threads):
        print("\n[ERROR] text2semantic failed. Try these in order:")
        print("  1. Free RAM: close browser, other apps, then retry.")
        print("  2. Check swap: sudo swapon /swapfile_s2pro")
        print("  3. Fix fish-speech: python3 run_tts.py --text '...' --fix-fishspeech")
        sys.exit(1)

    # =========================================================================
    # STEP 3 — DAC decode (codes → wav)  — much faster than step 2
    # =========================================================================
    section("Step 3 / 3  —  DAC decode  (codes → audio)")

    codes = sorted(glob.glob(os.path.join(args.output_dir, "codes_*.npy")))
    if not codes:
        print(f"\n[ERROR] No codes_*.npy in {args.output_dir}")
        sys.exit(1)
    codes_file = codes[-1]
    print(f"  Codes file: {codes_file}")

    cmd_dec = (
        f"{shlex.quote(python_exe)} -m fish_speech.models.dac.inference"
        f" -i {shlex.quote(codes_file)}"
        f" --checkpoint-path {shlex.quote(args.model_dir)}"
        f" --output-dir {shlex.quote(args.output_dir)}"
        f" --device cpu"
    )
    if not run_cmd(cmd_dec, "DAC decode", python_exe, args.threads):
        print("\n[ERROR] DAC decode failed.")
        sys.exit(1)

    # ── Result ────────────────────────────────────────────────────────────────
    section("Done!")

    total = time.time() - t0
    h, rem = divmod(int(total), 3600)
    m, s = divmod(rem, 60)
    elapsed = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

    wavs = sorted(glob.glob(os.path.join(args.output_dir, "*.wav")))
    if wavs:
        wav = wavs[-1]
        print(f"\n  Output : {wav}")
        print(f"  Size   : {os.path.getsize(wav) / 1024:.1f} KB")
        print(f"  Time   : {elapsed}")
        print(f"\n  Play   : aplay {shlex.quote(wav)}")
        print(f"        or: mpv {shlex.quote(wav)}")
    else:
        print(f"\n[WARN] No .wav file in {args.output_dir}")
        print(f"  Files present: {os.listdir(args.output_dir)}")


if __name__ == "__main__":
    main()
