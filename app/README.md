# AILoker — MVP

Platform lowongan kerja AI-native Indonesia: **kopilot karier** untuk pencari kerja
(skor kecocokan + skill gap per lowongan) dan **asisten rekrutmen** untuk perusahaan
(JD Writer, deteksi lowongan bermasalah, ranking pelamar otomatis).

Stack: Python 3.12, FastAPI, Jinja2, SQLite (stdlib), Tailwind CDN, pypdf, httpx.
Bahasa UI: Bahasa Indonesia.

## Cara menjalankan (lokal)

```bash
cd ~/workspace/ailoker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# isi data contoh (12 lowongan + akun demo)
.venv/bin/python -m app.seed

# jalankan server (port dari env PORT, default 8000)
PORT=8000 .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Buka http://localhost:8000 (di komputer sendiri) atau http://IP-VM:8000 dari perangkat lain.

Untuk contoh CV siap upload: `sample_cv.pdf` (dibuat via `.venv/bin/python make_sample_cv.py`).

## Environment variables

| Variable | Default | Keterangan |
|---|---|---|
| `PORT` | `8000` | Port HTTP yang didengarkan uvicorn / container |
| `DATABASE_PATH` | `./ailoker.db` (di folder `app/`) | Path file SQLite |
| `AI_PROVIDER` | *(otomatis)* | `anthropic` / `openai_compat` / `demo`. Jika dikosongkan: `ANTHROPIC_API_KEY` ada → anthropic; `AI_API_KEY` ada → openai_compat; sisanya demo |
| `ANTHROPIC_API_KEY` | *(kosong)* | API key Anthropic untuk provider `anthropic` (langsung ke `api.anthropic.com`) |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-5` | Model Anthropic (bisa diubah, mis. model lebih hemat untuk scoring massal) |
| `AI_API_KEY` | *(kosong)* | API key untuk endpoint OpenAI-compatible (`openai_compat`), mis. gateway 9Router lokal |
| `AI_BASE_URL` | `http://127.0.0.1:20128/v1` | Base URL endpoint OpenAI-compatible |
| `AI_MODEL` | `musebridge/muse` | Model di endpoint OpenAI-compatible |
| `APP_SECRET` | `dev-secret-change-me` | Secret session — **wajib diganti di production** |

> **Jangan pernah menulis API key ke file / README / chat.** Key hanya lewat
> environment variable (lokal) atau secret manager (production, mis. `fly secrets set`).

## Mode demo vs AI sungguhan

- **Tanpa key apa pun** (`AI_PROVIDER=demo` otomatis): semua fitur AI memakai
  implementasi demo yang deterministis di `app/ai.py` (match score dari keyword
  overlap, JD dari template, deteksi fraud dari rule-based). Banner kuning
  "Mode demo" tampil di seluruh UI.
- **Dengan `ANTHROPIC_API_KEY`**: `app/ai.py` memanggil
  `https://api.anthropic.com/v1/messages` dengan prompt khusus per fitur.
- **Dengan `AI_API_KEY`** (tanpa key Anthropic): memanggil endpoint
  OpenAI-compatible `/v1/chat/completions` — mis. **gateway 9Router lokal**
  (`AI_BASE_URL=http://127.0.0.1:20128/v1`, `AI_MODEL=musebridge/muse`).
  Ini rute $0-tanpa-daftar-baru untuk development: memakai key gateway yang
  sudah ada. Catatan: 9Router hanya listen di `127.0.0.1`, jadi rute ini untuk
  **lokal/demo saja**; untuk production publik (Fly.io dsb.) pakai
  `ANTHROPIC_API_KEY` langsung.
- Jika panggilan AI gagal (network/error), otomatis fallback ke mode demo
  supaya aplikasi tetap bisa dipakai.

### Opsi: pakai Gemini API (gratis) sebagai pengganti Anthropic

Google menyediakan endpoint **OpenAI-compatible** resmi, jadi provider
`openai_compat` yang sama bisa dipakai **tanpa ubah kode** — cukup ganti
3 env var:

| Variable | Nilai untuk Gemini |
|---|---|
| `AI_PROVIDER` | `openai_compat` |
| `AI_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai` |
| `AI_API_KEY` | key gratis dari [Google AI Studio](https://aistudio.google.com/apikey) |
| `AI_MODEL` | `models/gemini-3-flash-preview` (per Okt 2026; awalan `models/` wajib. `gemini-2.5-flash` sudah tidak tersedia untuk pengguna baru) |

Gemini API punya **free tier** (dengan batas rate) — cukup untuk demo/MVP.
Terverifikasi 2026-10-13: `parse_cv`, `match_score`, `write_jd`, `detect_fraud`
semua mengembalikan JSON valid via endpoint ini (konektor `custom.gemini`,
skill di `~/workspace/skills/gemini/`).
Di Render: tambahkan ketiga env var di atas di tab Environment (gantikan
`ANTHROPIC_API_KEY`). Catatan: untuk narasi pendaftaran Claude Startups,
integrasi Claude-nya tetap terbukti lewat mode 9Router lokal; Gemini di sini
murni opsi operasional $0.

Semua alur bisa dicoba end-to-end dalam mode demo tanpa key.

## Akun demo (dari `app.seed`)

| Peran | Email | Password |
|---|---|---|
| Perusahaan | `perusahaan@ailoker.com` | `demo1234` |
| Pencari kerja | `pencari@ailoker.com` | `demo1234` |
| Pencari kerja 2 | `sinta@ailoker.com` | `demo1234` |

Akun perusahaan demo sudah punya 12 lowongan contoh (teknologi, marketing,
operasional, customer service, dll.).

## Struktur kode

```
ailoker/
├── app/
│   ├── main.py          # FastAPI: semua routes (landing, auth, loker, profil, perusahaan)
│   ├── ai.py            # Lapisan AI: parse_cv, match_score, skill_gaps, write_jd,
│   │                    #   screen_applicants, detect_fraud (+ mode demo & fallback)
│   ├── db.py            # SQLite via stdlib (DATABASE_PATH)
│   ├── auth.py          # Registrasi/login, password PBKDF2-HMAC-SHA256, session cookie
│   ├── seed.py          # Data contoh (python -m app.seed)
│   └── templates/       # Jinja2 (base, index, daftar, masuk, loker_*, profil,
│                        #   perusahaan_dashboard, pelamar) — semua URL relatif
├── Dockerfile           # python:3.12-slim, baca PORT & DATABASE_PATH dari env
├── fly.toml             # Config deploy Fly.io (volume /data untuk SQLite)
├── requirements.txt
├── make_sample_cv.py    # Generator contoh CV PDF untuk testing
└── sample_cv.pdf
```

## Arsitektur hemat token

- **Hasil parsing CV disimpan di DB** (`profiles`) — CV hanya diparse sekali per upload.
- **Hasil match score di-cache** (`match_cache` per user × lowongan); cache dihapus
  otomatis saat profil berubah, dihitung ulang hanya saat dibutuhkan.
- **Skor disimpan saat melamar** (`applications.ai_score`) — dashboard perusahaan
  memakai skor tersimpan, tanpa inferensi ulang.
- **Pemisahan model** (saat API key aktif): `ANTHROPIC_MODEL` bisa diarahkan ke
  model hemat untuk scoring massal, dan model lebih besar hanya untuk fitur
  generation (JD writer, dsb.) — tinggal ubah env tanpa ubah kode.
- Mode demo sepenuhnya offline: nol biaya saat development/testing.

## Deploy ke production — GRATIS (Vercel + Turso, tanpa kartu kredit)

Rute $0 yang disarankan saat ini: **Vercel** (hosting, custom domain gratis,
tanpa kartu kredit) + **Turso** (database cloud gratis, tanpa kartu kredit).
Vercel itu serverless — kode di repo ini sudah disiapkan: `api/index.py`
(entrypoint), `vercel.json` (routing), dan `app/db.py` otomatis memakai Turso
bila `TURSO_URL` + `TURSO_TOKEN` diset (kalau tidak diset, tetap SQLite lokal
seperti biasa). Batasan jujur: cold start beberapa detik saat lama tidak
dikunjungi; request maksimal 60 detik (panggilan AI Gemini umumnya 10–30 detik).

**Langkah 1 — database Turso (sekali saja):**

1. Daftar gratis di [turso.tech](https://turso.tech) (tanpa kartu kredit).
2. Buat database baru → salin **URL** (`libsql://...turso.io`) dan **token**-nya.
   Simpan baik-baik, token ini rahasia.

**Langkah 2 — deploy di Vercel:**

1. Daftar di [vercel.com](https://vercel.com) → "Sign up with GitHub".
2. **Add New → Project** → **Import** repo GitHub ailoker-mu → **Deploy**
   (tidak perlu ubah setting build apa pun).
3. Setelah project jadi, buka **Settings → Environment Variables**, tambahkan:
   - `TURSO_URL` = URL database Turso
   - `TURSO_TOKEN` = token Turso
   - `AI_PROVIDER` = `openai_compat`
   - `AI_BASE_URL` = `https://generativelanguage.googleapis.com/v1beta/openai`
   - `AI_MODEL` = `models/gemini-3-flash-preview`
   - `AI_API_KEY` = key Gemini-mu (dari https://aistudio.google.com/apikey)
   - `APP_SECRET` = string acak panjang (bebas, mis. hasil `openssl rand -hex 32`)
   - `AILOKER_AUTO_SEED` = `1`
4. **Deployments → Redeploy** (agar env var terbaca) → app live di alamat
   seperti `https://ailoker.vercel.app`. Kunjungan pertama memicu pembuatan
   tabel + seed otomatis (akun demo + 12 lowongan), jadi agak lama — wajar.

**Langkah 3 — pasang domain `ailoker.com`:**

1. Di dashboard Vercel → project ailoker → **Settings → Domains** →
   tambahkan `ailoker.com` (dan `www.ailoker.com` bila mau).
2. Vercel menampilkan DNS record yang dibutuhkan (A record).
3. Buka panel DNS di registrar tempat kamu beli `ailoker.com`, tambahkan
   record tersebut. Tunggu propagasi (umumnya < 1 jam).
4. HTTPS aktif otomatis — selesai.

> Alternatif hosting: **SnapDeploy** (gratis, tanpa kartu, jalan dengan
> `Dockerfile` apa adanya — tapi custom domain butuh paket $12/bln);
> **Render** (per Oktober 2026 minta verifikasi kartu kredit untuk free tier).
> File `render.yaml` tetap tersedia bila suatu saat kembali ke Render.

**Catatan penting:** provider `openai_compat` (gateway 9Router) hanya untuk
pengembangan lokal — 9Router listen di `127.0.0.1` dan tak terjangkau dari
hosting publik. Production memakai key langsung (Gemini/Anthropic).

## Keamanan & batasan MVP

- Password di-hash PBKDF2-HMAC-SHA256 (200.000 iterasi), session cookie HttpOnly.
- Upload CV: hanya PDF, maks 5 MB, teks hasil scan gambar akan ditolak halus.
- MVP ini single-worker + SQLite: cocok untuk demo/beta (ratusan pengguna).
  Untuk skala besar, migrasi ke Postgres + worker ganda adalah langkah berikutnya.
- Jangan commit file `.db` atau API key ke Git.
