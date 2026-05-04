#!/usr/bin/env python3
"""setup_check.py — Verify that the local inference engine can be loaded.

Run from the repository root::

    python setup_check.py

Exit codes
~~~~~~~~~~
* ``0`` — local model loaded successfully (full GPU or CPU inference ready).
* ``1`` — model file missing or llama-cpp-python unavailable; game will use
  the SimulatedAI fallback templates and still run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent
GGUF_PATH = REPO_ROOT / "assets" / "models" / "default_brain.gguf"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OK   = "\033[92m[OK]\033[0m"
_WARN = "\033[93m[WARN]\033[0m"
_FAIL = "\033[91m[FAIL]\033[0m"
_INFO = "\033[94m[INFO]\033[0m"


def _section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_model_file() -> bool:
    """Verify the GGUF model file exists at the expected path."""
    _section("Model file")
    print(f"  Expected path : {GGUF_PATH}")
    if GGUF_PATH.exists():
        size_mb = GGUF_PATH.stat().st_size / (1024 ** 2)
        print(f"  {_OK}  Found ({size_mb:.1f} MB)")
        return True
    print(
        f"  {_WARN}  Not found.\n"
        f"        Place your GGUF model at:\n"
        f"          {GGUF_PATH}\n"
        f"        The game will use SimulatedAI fallback templates until then."
    )
    return False


def check_llama_cpp() -> bool:
    """Check that llama-cpp-python is importable."""
    _section("llama-cpp-python")
    try:
        import llama_cpp  # type: ignore[import]
        version = getattr(llama_cpp, "__version__", "unknown")
        print(f"  {_OK}  llama-cpp-python {version} is installed.")
        return True
    except ImportError:
        print(
            f"  {_WARN}  llama-cpp-python is not installed.\n"
            f"        Install it with:\n"
            f"          pip install llama-cpp-python\n"
            f"        The game will use SimulatedAI fallback templates until then."
        )
        return False


def check_gpu() -> str:
    """Probe for a CUDA-capable GPU via nvidia-smi.

    Returns:
        A human-readable string: the GPU name(s) or ``"CPU-only"``.
    """
    _section("GPU / hardware detection")
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            gpus = [line.strip() for line in result.stdout.strip().splitlines()]
            for gpu in gpus:
                print(f"  {_OK}  CUDA GPU detected: {gpu}")
            print(f"  {_INFO}  n_gpu_layers will be set to -1 (all layers to VRAM).")
            return ", ".join(gpus)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    print(
        f"  {_INFO}  No CUDA GPU detected — inference will run on CPU.\n"
        f"        n_gpu_layers will be set to 0."
    )
    return "CPU-only"


def check_load_model() -> bool:
    """Attempt to initialise LocalInferenceEngine and run a quick probe."""
    _section("Engine load test")
    try:
        from src.ai_sim.llm_bridge import LocalInferenceEngine
    except ImportError as exc:
        print(f"  {_FAIL}  Could not import LocalInferenceEngine: {exc}")
        return False

    engine = LocalInferenceEngine()

    if not engine.is_local_model_loaded:
        print(
            f"  {_WARN}  LocalInferenceEngine is in fallback mode.\n"
            f"        Ensure the model file exists and llama-cpp-python is installed."
        )
        return False

    gpu_label = "GPU" if engine.n_gpu_layers == -1 else "CPU"
    print(f"  {_OK}  Model loaded successfully ({gpu_label} inference, n_gpu_layers={engine.n_gpu_layers}).")

    # Quick async smoke test
    import asyncio

    async def _smoke() -> str:
        return await engine.query_text(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'ready' in one word.",
        )

    reply = asyncio.run(_smoke())
    print(f"  {_INFO}  Smoke-test reply: {reply!r}")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║          New Game Plus — Inference Engine Check          ║")
    print("╚══════════════════════════════════════════════════════════╝")

    model_ok  = check_model_file()
    llama_ok  = check_llama_cpp()
    gpu_label = check_gpu()
    engine_ok = check_load_model()

    _section("Summary")
    rows = [
        ("Model file present",       model_ok),
        ("llama-cpp-python installed", llama_ok),
        ("GPU detected",              gpu_label != "CPU-only"),
        ("Engine loaded",             engine_ok),
    ]
    for label, status in rows:
        icon = _OK if status else _WARN
        print(f"  {icon}  {label}")

    if engine_ok:
        print(
            f"\n  {_OK}  All systems go — local inference is ready.\n"
            f"        GPU: {gpu_label}\n"
        )
        return 0

    print(
        f"\n  {_WARN}  Local inference unavailable.\n"
        f"        The game will run using SimulatedAI fallback templates.\n"
        f"        No action required — this is expected on fresh installs\n"
        f"        before the model file is downloaded.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
