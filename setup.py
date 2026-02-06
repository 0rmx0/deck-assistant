#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Setup script for MTG Deck Builder
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mtg-deck-builder",
    version="1.0.0",
    author="Remi",
    description="MTG Deck Builder - Commander - A tool for building and analyzing Magic: The Gathering decks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/remi/mtg-deck-builder",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PySide6>=6.0.0",
        "requests>=2.28.0",
    ],
    extras_require={
        "dev": [
            "pyinstaller>=5.0.0",
        ],
    },
)
