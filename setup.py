"""
setup.py
--------
Package metadata for New Game Plus.

Install in editable mode for local development::

    pip install -e .
"""

from setuptools import setup, find_packages

setup(
    name="new_game_plus",
    version="0.1.0",
    description="High-fidelity game engine and simulation built on D&D 3.5e SRD mechanics with autonomous AI agency in a procedural voxel world",
    author="New Game Plus Team",
    python_requires=">=3.11",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "pytest",
        "opensimplex",
    ],
    entry_points={
        "console_scripts": [
            "new-game-plus=src.game.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
