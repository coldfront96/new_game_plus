"""
src/launcher/window_wrapper.py
-------------------------------
Standalone window wrapper for Echoes of the Infinite.

Launches the :class:`~src.game.master_app.MasterApp` in a dedicated OS
window titled "Echoes of the Infinite" at a fixed 1280 × 720 resolution,
eliminating the "context break" that occurred when the Pygame door slam
handed off to a raw terminal.

Strategy order (first that succeeds wins)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. **pywebview + textual serve** — true native OS window with no visible
   terminal chrome.  Requires ``pywebview`` and the ``textual`` CLI to be
   installed.  The Textual app is served locally on ``SERVE_PORT`` and
   displayed inside the webview window.

2. **Terminal emulator subprocess** — spawn a supported terminal emulator
   (wezterm, alacritty, xterm, gnome-terminal, konsole, xfce4-terminal)
   with a custom title and fixed geometry.  Falls back through the list
   until one is found on ``PATH``.

3. **In-process Textual run** — run the app directly in the calling
   terminal.  No dedicated window, but fully functional.

Entry points
~~~~~~~~~~~~
* ``from src.launcher.window_wrapper import launch; launch()`` — called by
  ``launcher.py`` after the Pygame intro.
* ``python src/launcher/window_wrapper.py`` — direct invocation for
  development or CI.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TITLE      = "Echoes of the Infinite"
WIDTH      = 1280
HEIGHT     = 720
SERVE_PORT = 8765

_REPO_ROOT  = Path(__file__).parent.parent.parent
_MASTER_APP = _REPO_ROOT / "src" / "game" / "master_app.py"

# Terminal emulators tried in preference order.
# Each entry: (executable_name, command_prefix_before_the_python_invocation)
_TERMINAL_CANDIDATES: list[tuple[str, list[str]]] = [
    ("wezterm",        ["wezterm", "start", "--title", TITLE, "--"]),
    ("alacritty",      ["alacritty", "--title", TITLE, "-e"]),
    ("xterm",          ["xterm", "-title", TITLE, "-geometry", "160x45", "-e"]),
    ("gnome-terminal", ["gnome-terminal", f"--title={TITLE}", "--"]),
    ("konsole",        ["konsole", "--title", TITLE, "-e"]),
    ("xfce4-terminal", ["xfce4-terminal", f"--title={TITLE}", "-e"]),
]


# ===========================================================================
# Public entry point
# ===========================================================================


def launch() -> None:
    """Launch the Master App using the best available window strategy."""
    if _try_pywebview():
        return
    if _try_terminal_emulator():
        return
    _run_in_process()


# ===========================================================================
# Strategy 1 — pywebview + textual serve
# ===========================================================================


def _try_pywebview() -> bool:
    """Attempt to open a pywebview window serving the Textual app.

    Returns True if the window was opened and closed successfully.
    Returns False if pywebview is not installed or the server failed to start.
    """
    try:
        import webview  # noqa: F401
    except ImportError:
        return False

    server = subprocess.Popen(
        [
            sys.executable, "-m", "textual", "serve",
            "--port", str(SERVE_PORT),
            str(_MASTER_APP),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(_REPO_ROOT),
    )

    # Give the development server time to bind its port.
    time.sleep(2.5)

    if server.poll() is not None:
        # Server exited immediately — likely an error (e.g. port in use).
        return False

    try:
        import webview  # real import with full schema now

        window = webview.create_window(
            title=TITLE,
            url=f"http://localhost:{SERVE_PORT}",
            width=WIDTH,
            height=HEIGHT,
            resizable=False,
        )
        webview.start()
        return True
    except Exception:  # noqa: BLE001
        return False
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


# ===========================================================================
# Strategy 2 — terminal emulator subprocess
# ===========================================================================


def _try_terminal_emulator() -> bool:
    """Spawn a terminal emulator window running the Master App.

    Returns True if a terminal emulator was found and launched.
    Returns False if no supported emulator is on PATH.
    """
    # Command that the terminal will execute: run master_app.py directly.
    python_args = [sys.executable, str(_MASTER_APP)]

    for exe, prefix in _TERMINAL_CANDIDATES:
        if shutil.which(exe) is None:
            continue
        try:
            result = subprocess.run(
                prefix + python_args,
                cwd=str(_REPO_ROOT),
                check=False,
            )
            return True
        except (OSError, subprocess.SubprocessError):
            continue

    return False


# ===========================================================================
# Strategy 3 — in-process fallback
# ===========================================================================


def _run_in_process() -> None:
    """Run the Master App directly inside the calling terminal."""
    import os
    sys.path.insert(0, str(_REPO_ROOT))
    os.chdir(_REPO_ROOT)

    from src.game.master_app import MasterApp  # noqa: PLC0415
    MasterApp().run()


# ---------------------------------------------------------------------------
# Direct invocation
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    launch()
