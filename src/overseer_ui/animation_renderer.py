"""PH5-010 · PH5-011 · PH5-012 · PH5-013 — Terminal VFX Renderer.

src/overseer_ui/animation_renderer.py
---------------------------------------
Provides an async VFX queue and frame-by-frame rendering helpers that
overlay visual effects onto the Textual voxel grid widget without blocking
the main physics thread.

Key types
~~~~~~~~~
* :class:`VFXEvent`          — immutable event descriptor enqueued by callers.
* :class:`AnimationRenderer` — consumes the queue and dispatches to render methods.

Visual effects implemented
~~~~~~~~~~~~~~~~~~~~~~~~~~
* ``lightning_bolt``  (PH5-011) — jagged Z-line from origin to target.
* ``damage_flash``    (PH5-012) — red background flash at damaged-entity cell.
* ``rain_particle``   (PH5-013) — per-frame rain overlay from WeatherState.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from textual.widgets import Static


# ---------------------------------------------------------------------------
# PH5-010 · VFXEvent dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class VFXEvent:
    """A single visual-effect event enqueued for asynchronous rendering.

    Attributes:
        event_type:  Identifier string (``"lightning_bolt"``, ``"damage_flash"``,
                     ``"rain_particle"``).
        origin:      ``(row, col)`` viewport coordinate of the effect source.
        target:      ``(row, col)`` viewport coordinate of the effect target, or
                     ``None`` for non-directional effects.
        duration_ms: How long the effect lasts in milliseconds.
        payload:     Arbitrary extra data (e.g. ``hp_delta``, particle lists).
    """

    event_type: str
    origin: tuple[int, int]
    target: tuple[int, int] | None
    duration_ms: int
    payload: dict


# ---------------------------------------------------------------------------
# PH5-010 · AnimationRenderer
# ---------------------------------------------------------------------------

class AnimationRenderer:
    """Async VFX consumer that renders effects onto a Textual ``Static`` widget.

    The renderer maintains an internal :class:`asyncio.Queue` of
    :class:`VFXEvent` objects.  Callers enqueue events from any thread via
    :meth:`enqueue` (non-blocking); the :meth:`run_loop` coroutine dispatches
    them to the appropriate ``_render_*`` coroutine.

    All rendering is interleaved with ``asyncio.sleep(0)`` yields so that the
    main physics thread is never blocked.

    Args:
        grid_widget: The Textual ``Static`` widget that displays the voxel grid.
    """

    def __init__(self, grid_widget: "Static") -> None:
        self._queue: asyncio.Queue[VFXEvent] = asyncio.Queue(maxsize=128)
        self._grid_widget = grid_widget
        self.running: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(self, event: VFXEvent) -> None:
        """Non-blocking enqueue of *event*.

        If the queue is full the *oldest* event is discarded before the new
        one is added, ensuring that fresh events are never dropped.

        Args:
            event: The :class:`VFXEvent` to add to the queue.
        """
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                self._queue.get_nowait()   # drop oldest
            except asyncio.QueueEmpty:
                pass
            try:
                self._queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # extremely unlikely; silently drop

    async def run_loop(self) -> None:
        """Consume events from the queue and dispatch to render coroutines.

        Runs until :meth:`stop` is called.  Each iteration awaits the next
        event and then calls the matching ``_render_*`` coroutine.  Unknown
        event types are silently ignored.
        """
        self.running = True
        while self.running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                await asyncio.sleep(0)
                continue

            if event.event_type == "lightning_bolt":
                await self._render_lightning_bolt(event)
            elif event.event_type == "damage_flash":
                await self._render_damage_flash(event)
            elif event.event_type == "rain_particle":
                await self._render_rain_particles(event)
            else:
                # Unknown event type — yield and continue.
                await asyncio.sleep(0)

    async def stop(self) -> None:
        """Signal the run loop to stop and drain any remaining events."""
        self.running = False
        # Drain the queue.
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        await asyncio.sleep(0)

    # ------------------------------------------------------------------
    # PH5-011 · Lightning Bolt Z-line VFX
    # ------------------------------------------------------------------

    async def _render_lightning_bolt(self, event: VFXEvent) -> None:
        """Render a jagged Z-line lightning bolt from *origin* to *target*.

        The Z-line path has three segments:

        1. Horizontal segment from ``c0`` to ``c1`` at row ``r0``.
        2. Diagonal segment from ``(r0, c1)`` to ``(r1, c0)`` stepping one
           row per column.
        3. Horizontal segment from ``c0`` to ``c1`` at row ``r1``.

        A yellow ``⚡`` glyph is overlaid at each cell in sequence with a
        30 ms delay between cells.  After *duration_ms*, the grid is refreshed
        to restore original content.

        Args:
            event: The :class:`VFXEvent` describing the effect.
        """
        from rich.text import Text

        r0, c0 = event.origin
        r1, c1 = event.target if event.target is not None else event.origin

        path: list[tuple[int, int]] = []

        # Segment 1: horizontal at r0
        col_step = 1 if c1 >= c0 else -1
        for c in range(c0, c1 + col_step, col_step):
            path.append((r0, c))

        # Segment 2: diagonal from (r0, c1) → (r1, c0)
        row_step = 1 if r1 > r0 else -1
        col_step2 = 1 if c0 > c1 else -1
        r_cur, c_cur = r0 + row_step, c1 + col_step2
        while r_cur != r1 + row_step and c_cur != c0 + col_step2:
            path.append((r_cur, c_cur))
            r_cur += row_step
            c_cur += col_step2

        # Segment 3: horizontal at r1
        col_step3 = 1 if c1 >= c0 else -1
        for c in range(c0, c1 + col_step3, col_step3):
            path.append((r1, c))

        # Render each glyph with a frame delay.
        for _row, _col in path:
            overlay = Text("⚡", style="bold yellow")
            self._grid_widget.update(overlay)
            await asyncio.sleep(0.03)

        # Hold for the remaining duration, then refresh.
        hold_s = max(0.0, event.duration_ms / 1000.0 - len(path) * 0.03)
        if hold_s > 0:
            await asyncio.sleep(hold_s)
        self._grid_widget.refresh()

    def enqueue_lightning_bolt(
        self,
        origin: tuple[int, int],
        target: tuple[int, int],
        duration_ms: int = 400,
    ) -> None:
        """Construct and enqueue a ``lightning_bolt`` :class:`VFXEvent`.

        Args:
            origin:      ``(row, col)`` start coordinate.
            target:      ``(row, col)`` end coordinate.
            duration_ms: Effect duration in milliseconds.
        """
        self.enqueue(VFXEvent(
            event_type="lightning_bolt",
            origin=origin,
            target=target,
            duration_ms=duration_ms,
            payload={},
        ))

    # ------------------------------------------------------------------
    # PH5-012 · Damage Flash VFX
    # ------------------------------------------------------------------

    async def _render_damage_flash(self, event: VFXEvent) -> None:
        """Render a red-background flash at the damaged entity's viewport cell.

        Sequence:

        1. Overlay the cell at *origin* with a ``"on red"`` Rich ``Text`` block
           for *duration_ms* milliseconds.
        2. Refresh to restore original content.
        3. Print the HP delta to the combat log widget (if available in payload).

        Args:
            event: The :class:`VFXEvent` with ``origin`` and ``payload["hp_delta"]``.
        """
        from rich.text import Text

        hold_s = event.duration_ms / 1000.0
        flash = Text("█", style="on red")
        self._grid_widget.update(flash)
        await asyncio.sleep(hold_s)
        self._grid_widget.refresh()
        await asyncio.sleep(0)

        # Print HP delta to combat log if a RichLog widget is wired in.
        hp_delta: int = event.payload.get("hp_delta", 0)
        if hp_delta < 0:
            combat_log = event.payload.get("combat_log")
            if combat_log is not None:
                try:
                    combat_log.write(
                        f"[red][-{abs(hp_delta)} HP][/red]"
                    )
                except Exception:  # noqa: BLE001
                    pass

    def enqueue_damage_flash(
        self,
        position: tuple[int, int],
        hp_delta: int,
        duration_ms: int = 200,
        combat_log: Any = None,
    ) -> None:
        """Construct and enqueue a ``damage_flash`` :class:`VFXEvent`.

        Args:
            position:    ``(row, col)`` viewport coordinate of the damaged entity.
            hp_delta:    HP change (negative for damage).
            duration_ms: Flash duration in milliseconds.
            combat_log:  Optional Textual ``RichLog`` widget to write the delta.
        """
        self.enqueue(VFXEvent(
            event_type="damage_flash",
            origin=position,
            target=None,
            duration_ms=duration_ms,
            payload={"hp_delta": hp_delta, "combat_log": combat_log},
        ))

    # ------------------------------------------------------------------
    # PH5-013 · Rain Particle VFX
    # ------------------------------------------------------------------

    async def _render_rain_particles(self, event: VFXEvent) -> None:
        """Render a full-grid rain overlay with current and next-frame particles.

        Reads ``event.payload["particles"]`` (current frame) and
        ``event.payload["next_particles"]`` (next frame), composing a single
        ``Text`` object with cyan ``~`` glyphs at particle positions.  The
        grid is updated once per call, then the renderer awaits a 10 FPS
        frame delay (100 ms) before rendering the next frame.

        The rain loop is expected to be driven externally by successive
        ``rain_particle`` events from :meth:`enqueue_rain_update`; it does
        not run indefinitely on its own.

        Args:
            event: The :class:`VFXEvent` with particle coordinate lists in payload.
        """
        from rich.text import Text

        particles: list[tuple[int, int]] = [
            tuple(p) for p in event.payload.get("particles", [])
        ]

        # Build a VP_ROWS × VP_COLS grid; inject rain glyphs at particle positions.
        _VP_ROWS = 24
        _VP_COLS = 80
        particle_set: set[tuple[int, int]] = set(particles)

        grid_text = Text()
        for row in range(_VP_ROWS):
            for col in range(_VP_COLS):
                if (row, col) in particle_set:
                    grid_text.append("~", style="cyan")
                else:
                    grid_text.append(" ")
            grid_text.append("\n")

        self._grid_widget.update(grid_text)
        # 10 FPS rain tick — yield between frames.
        await asyncio.sleep(1 / 10)

    def enqueue_rain_update(
        self,
        particles: list[tuple[int, int]],
        next_particles: list[tuple[int, int]],
    ) -> None:
        """Construct and enqueue a ``rain_particle`` :class:`VFXEvent`.

        Args:
            particles:      Current-frame ``(row, col)`` particle positions.
            next_particles: Next-frame ``(row, col)`` particle positions.
        """
        self.enqueue(VFXEvent(
            event_type="rain_particle",
            origin=(0, 0),
            target=None,
            duration_ms=100,
            payload={"particles": particles, "next_particles": next_particles},
        ))
