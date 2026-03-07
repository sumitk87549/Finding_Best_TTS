#!/bin/bash

# A quick runner wrapper to execute the VibeVoice test script.
# It automatically activates the Python Virtual environment if it exists in the workspace.

set -e

echo "================================================"
echo "    Running VibeVoice Hindi-7B Inference Tester   "
echo "================================================"

WORKSPACE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$WORKSPACE_DIR"

if [ -d ".venv" ]; then
    echo "[*] Found logical python virtual environment (.venv). Activating..."
    source .venv/bin/activate
fi

# Ensure VibeVoice module dependencies are installed
if python -c "import vibevoice" &> /dev/null; then
    echo "[*] VibeVoice package seems available."
else
    echo "[!] Installing missing VibeVoice requirements..."
    pip install -e ./VibeVoice > /dev/null 2>&1
    echo "[*] Installed VibeVoice dependencies."
fi

echo "[*] Starting execution..."
python run_vibevoice_test.py
echo "[*] Script finished."
