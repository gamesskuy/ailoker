"""Entrypoint Vercel — runtime Python Vercel otomatis mengenali variabel `app`
(ASGI) di file ini sebagai serverless function.

Catatan path: Vercel meletakkan file ini di root bundle (mis. /var/task/index.py),
bukan di api/. Karena itu tambahkan direktori file ini DAN induknya ke sys.path
agar paket `app/` selalu ketemu di semua layout.
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
for _p in (_here, os.path.dirname(_here)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.main import app  # noqa: F401  (diekspos ke Vercel sebagai ASGI app)
