"""FastAPI root entrypoint for Vercel Serverless Functions."""
import os
import sys

_REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.main import app

__all__ = ["app"]
