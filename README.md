# AILoker — Platform Lowongan Kerja AI-Native 🇮🇩

**Kopilot karier** untuk pencari kerja (skor kecocokan + penjelasan + skill gap
per lowongan, latihan lamaran satu klik) dan **asisten rekrutmen** untuk
perusahaan (JD Writer Bahasa Indonesia, ranking pelamar otomatis, deteksi
lowongan palsu).

Stack: Python 3.12 · FastAPI · Jinja2 · SQLite · Tailwind · pypdf · httpx.
UI berbahasa Indonesia. Dibangun AI-native di atas Claude API —
lihat pemetaannya di [`KONSEP.md`](KONSEP.md).

## Status

MVP memakai **Gemini sebagai AI-nya** (gratis, free tier) — sudah dikonfigurasi
penuh di `render.yaml`, terverifikasi end-to-end (parse CV, match score,
JD writer, deteksi loker palsu). Tanpa key, aplikasi otomatis jalan dalam
**mode demo**: semua fitur berfungsi penuh dengan simulasi deterministis yang
jelas dilabeli.

Akun demo (ter-seed otomatis): `perusahaan@ailoker.com` / `pencari@ailoker.com` /
`sinta@ailoker.com` — password `demo1234`.

## Deploy gratis (Vercel + Turso, tanpa kartu kredit)

Panduan langkah-demi-langkah: **[app/README.md](app/README.md)** —
buat database gratis di Turso → import repo ke Vercel → isi env var →
pasang domain `ailoker.com` (custom domain gratis di Vercel).

## Jalankan lokal

```bash
cd ailoker
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.seed
PORT=8000 .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
