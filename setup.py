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
    description="Hybrid colony-simulation RPG engine — Dwarf Fortress × Minecraft × Lootfiend",
    author="New Game Plus Team",
    python_requires=">=3.11",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "pytest",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
