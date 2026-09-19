"""PyInstaller entry point (the package's own __main__ uses relative imports, which a top-level script can't)."""
from mochi.app import main

main()
