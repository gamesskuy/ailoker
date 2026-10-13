"""Entrypoint Vercel — runtime Python Vercel otomatis mengenali variabel `app`
(ASGI) di file ini sebagai serverless function. Tidak perlu Mangum/adapter."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: F401  (diekspos ke Vercel sebagai ASGI app)
