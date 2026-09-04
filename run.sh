#!/usr/bin/env bash
set -euo pipefail

# ── Fail loudly on any error ─────────────────────────────────────────
trap 'echo ""; echo "ERROR: something went wrong (see above). Fix the issue and re-run ./run.sh"; exit 1' ERR

# ── Locate Python 3.11+ ──────────────────────────────────────────────
find_python() {
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            ver=$("$cmd" -c 'import sys; print(sys.version_info.major, sys.version_info.minor)')
            major=${ver%% *}
            minor=${ver##* }
            if [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; then
                echo "$cmd"
                return
            fi
        fi
    done
    echo ""
}

PYTHON=$(find_python)
if [ -z "$PYTHON" ]; then
    echo "Python 3.11 or newer is required but was not found on your system."
    echo ""
    echo "Install it from https://www.python.org/downloads/ and make sure"
    echo "the 'python3' command is on your PATH, then re-run this script."
    exit 1
fi

echo "Using $($PYTHON --version) ($PYTHON)"

# ── Create venv if needed, then activate ──────────────────────────────
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv .venv
fi
source .venv/bin/activate

# ── Install dependencies ──────────────────────────────────────────────
echo "Installing dependencies..."
pip install -q -r requirements.txt

# ── Run the pipeline ─────────────────────────────────────────────────
echo ""
python -m dealsight run

# ── Print output location ────────────────────────────────────────────
QUEUE_HTML="$(cd "$(dirname "$0")" && pwd)/out/queue.html"
echo ""
echo "Output: $QUEUE_HTML"
echo "Open that file in your browser to view the queue."
