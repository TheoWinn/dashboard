#!/usr/bin/env bash
set -euo pipefail

# --- locate repo root and cd there ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- ensure venv exists (.venv created by uv) ---
VENV_PY="../../.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "Error: .venv/bin/python not found. Did you run 'uv venv' or 'uv sync'?" >&2
  exit 1
fi

export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=true

"$VENV_PY" - << 'PY'
import os, importlib.resources as ir
p = ir.files('nvidia.cudnn') / 'lib'
print(os.fspath(p))
try:
    print('\n'.join(sorted(x.name for x in p.iterdir())))
except Exception as e:
    print("ITERDIR ERROR:", e)
PY

# --- compute CUDNN_LIBDIR using venv python ---
CUDNN_LIBDIR="$("$VENV_PY" - << 'PY'
import os, importlib.resources as ir
p = ir.files("nvidia.cudnn") / "lib"
print(os.fspath(p))
PY
)"

if [[ -z "$CUDNN_LIBDIR" ]]; then
  echo "Error: could not resolve CUDNN_LIBDIR from nvidia.cudnn" >&2
  exit 1
fi

export CUDNN_LIBDIR
export LD_LIBRARY_PATH="${CUDNN_LIBDIR}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"

# --- sanity check: verify torch sees CUDA/cuDNN ---
"$VENV_PY" - << 'PY'
import torch, os, glob
print("CUDA:", torch.version.cuda, "cuDNN:", torch.backends.cudnn.version())
print("CUDNN_LIBDIR:", os.environ.get("CUDNN_LIBDIR"))
print("has libcudnn_cnn:", bool(glob.glob(os.environ["CUDNN_LIBDIR"] + "/libcudnn_cnn.so*")))
PY

# --- run your actual script ---
"$VENV_PY" transcribe_audio.py "$@"
