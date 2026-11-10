"""PyInstaller entry point (the package's own __main__ uses relative imports, which a top-level script can't)."""
import os

# Prevent host GTK/GIO modules from conflicting with bundled glib
for var in ("GIO_MODULE_DIR", "GTK_PATH", "GDK_PIXBUF_MODULE_FILE"):
    os.environ.pop(var, None)
os.environ["GIO_MODULE_DIR"] = "/dev/null"

from mochi.app import main

main()
