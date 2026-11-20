import os
from pathlib import Path
import sys

# Ensure backend root is on sys.path
backend_dir = str(Path(__file__).resolve().parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set test environment variables
os.environ.setdefault(
    "AUTH_SECRET_KEY",
    "test-secret-key-for-testing-at-least-32-chars-long!",
)
