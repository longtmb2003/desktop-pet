#!/usr/bin/env python3
"""Compatibility shim: `python3 pet.py` still works; the app now lives in the `mochi` package."""
from mochi.app import main

main()
