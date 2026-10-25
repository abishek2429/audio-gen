"""Vercel Serverless Function entrypoint for IncuBrix AI Background Music Engine."""
import os
import sys

# Ensure repository root is on sys.path for internal module imports
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.main import app

# Export ASGI app instance for Vercel Python runtime
__all__ = ["app"]
