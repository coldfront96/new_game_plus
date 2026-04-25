"""
src/game
--------
Runtime driver for New Game Plus.

This package holds the text-mode CLI entry point and the glue layer that
wires the rules engine (character creation, combat, encounters, loot) into
an interactive loop.  It is deliberately thin: all mechanics live in
``src/rules_engine``; this package only orchestrates user I/O and the
turn/round lifecycle.
"""
