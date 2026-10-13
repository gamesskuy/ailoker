"""Lapisan AI AILoker.

Tiga mode operasi (otomatis terdeteksi, atau paksa via env AI_PROVIDER):
- ANTHROPIC: jika env ANTHROPIC_API_KEY terisi -> memanggil Anthropic
  Messages API (https://api.anthropic.com/v1/messages), model dari env
  ANTHROPIC_MODEL (default: claude-sonnet-4-5).
- OPENAI_COMPAT: jika env AI_API_KEY terisi -> memanggil endpoint
  OpenAI-compatible /v1/chat/completions (mis. gateway 9Router lokal),
  URL dari env AI_BASE_URL (default: http://127.0.0.1:20128/v1),
  model dari env AI_MODEL (default: musebridge/muse).
- DEMO: jika tidak ada key -> respons mock yang deterministis & masuk akal,
  supaya SEMUA fitur bisa dicoba end-to-end tanpa API key. UI wajib menampilkan
  label "Mode demo" saat mode ini aktif.

Hasil AI selalu diparse sebagai JSON. Jika panggilan API gagal
(network/error), otomatis fallback ke mode demo agar aplikasi tetap bisa dipakai.
"""
import json
import logging
import os
import re

import httpx

log = logging.getLogger("ailoker.ai")

# --- Konfigurasi provider ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5").strip()
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
AI_BASE_URL = os.environ.get("AI_BASE_URL", "http://127.0.0.1:20128/v1").rstrip("/")
AI_MODEL = os.environ.get("AI_MODEL", "musebridge/muse").strip()

_explicit = os.environ.get("AI_PROVIDER", "").strip().lower()
if _explicit in ("anthropic", "openai_compat", "demo"):
    PROVIDER = _explicit
elif ANTHROPIC_API_KEY:
    PROVIDER = "anthropic"
elif AI_API_KEY:
    PROVIDER = "openai_compat"
else:
    PROVIDER = "demo"

# --- Perbaikan quirk proxy VM ini ---
# no_proxy bawaan memuat entri IPv6 dengan kurung siku ("[::1]",
# "[fd8b:...::1]", ...); httpx membungkusnya lagi menjadi "all://[[...]]"
# sehingga httpx.Client() CRASH (InvalidURL: Invalid port) bahkan sebelum
# request dibuat. Buang semua entri berkurung siku di level proses — bentuk
# tanpa kurung ("::1", "fd8b:...::1") tetap ada dan ditangani httpx dengan
# benar, jadi bypass localhost tidak hilang.
for _pv in ("no_proxy", "NO_PROXY"):
    _vv = os.environ.get(_pv, "")
    if "[" in _vv:
        os.environ[_pv] = ",".join(
            p for p in _vv.split(",")
            if not (p.strip().startswith("[") and p.strip().endswith("]"))
        )


def is_demo() -> bool:
    return PROVIDER == "demo"


def provider_name() -> str:
    """Nama provider aktif: 'anthropic' | 'openai_compat' | 'demo'."""
    return PROVIDER


# ---------------------------------------------------------------------------
# Panggilan API (mode real): Anthropic Messages API atau endpoint
# OpenAI-compatible (/v1/chat/completions, mis. 9Router)
# ---------------------------------------------------------------------------
def _parse_body(text: str):
    """Parse body JSON yang mungkin berekor SSE (mis. 'data: [DONE]' dari gateway)."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        obj, _ = json.JSONDecoder().raw_decode(text)
        return obj


def _extract_json(text: str) -> dict:
    """Ambil objek JSON pertama dari teks respons (tahan fence & ekor SSE)."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return _parse_body(text)


def _call_claude(system: str, user: str, max_tokens: int = 1500) -> dict:
    """Panggil Messages API, kembalikan dict hasil parse JSON dari respons."""
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post(ANTHROPIC_URL, headers=headers, json=body)
        resp.raise_for_status()
        data = _parse_body(resp.text)
    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
    return _extract_json(text)


def _call_openai_compat(system: str, user: str, max_tokens: int = 1500) -> dict:
    """Panggil /v1/chat/completions ala OpenAI, kembalikan dict JSON.

    Bisa dipakai untuk endpoint OpenAI-compatible apa pun:
    - Gateway 9Router lokal (AI_BASE_URL=http://127.0.0.1:20128/v1)
    - Google Gemini (AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai)
    trust_env default (True) agar proxy environment tetap dipakai untuk
    endpoint eksternal; quirk no_proxy "[::1]" sudah disanitasi saat import.
    """
    url = f"{AI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "content-type": "application/json",
    }
    body = {
        "model": AI_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    with httpx.Client(timeout=90) as client:
        resp = client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = _parse_body(resp.text)
    text = data["choices"][0]["message"]["content"] or ""
    return _extract_json(text)


def _complete(system: str, user: str, max_tokens: int = 1500) -> dict:
    """Dispatch ke provider aktif."""
    if PROVIDER == "anthropic":
        return _call_claude(system, user, max_tokens)
    return _call_openai_compat(system, user, max_tokens)


def _real_or_demo(real_fn, demo_fn, *args, **kwargs):
    if is_demo():
        return demo_fn(*args, **kwargs)
    try:
        return real_fn(*args, **kwargs)
    except Exception as e:  # fallback agar app tetap jalan
        log.warning("Panggilan AI (%s) gagal (%s), fallback ke mode demo",
                    PROVIDER, e)
        return demo_fn(*args, **kwargs)


# ---------------------------------------------------------------------------
# 1. parse_cv: teks CV -> profil terstruktur
# ---------------------------------------------------------------------------
SYS_CV = (
    "Kamu adalah parser CV. Dari teks CV berikut, ekstrak profil kandidat dan "
    "kembalikan HANYA JSON valid dengan kunci: name (string), summary (string, "
    "2-3 kalimat Bahasa Indonesia), skills (array string), experience (array "
    "string, tiap item 1 kalimat), education (array string). Jangan tambah teks lain."
)


def parse_cv(text: str) -> dict:
    def real():
        return _complete(SYS_CV, f"Teks CV:\n{text[:12000]}")

    def demo():
        return _demo_parse_cv(text)

    return _real_or_demo(real, demo)


# ---------------------------------------------------------------------------
# 2. match_score: profil vs lowongan -> skor + penjelasan + skill gap
# ---------------------------------------------------------------------------
SYS_MATCH = (
    "Kamu adalah analis kecocokan karier. Nilai kecocokan kandidat terhadap "
    "lowongan dan kembalikan HANYA JSON valid dengan kunci: score (integer "
    "0-100), explanation (string Bahasa Indonesia, 2-4 kalimat: kenapa cocok "
    "dan apa yang kurang), gaps (array string: skill/kualifikasi yang perlu "
    "ditambah kandidat, maksimal 5)."
)


def match_score(profile: dict, job: dict) -> dict:
    def real():
        user = (
            f"PROFIL KANDIDAT:\nNama: {profile.get('name','')}\n"
            f"Ringkasan: {profile.get('summary','')}\n"
            f"Skills: {', '.join(profile.get('skills', []))}\n"
            f"Pengalaman: {'; '.join(profile.get('experience', []))}\n"
            f"Pendidikan: {'; '.join(profile.get('education', []))}\n\n"
            f"LOWONGAN:\nJudul: {job.get('title','')}\n"
            f"Lokasi: {job.get('location','')}\n"
            f"Deskripsi:\n{job.get('description','')[:6000]}"
        )
        return _complete(SYS_MATCH, user)

    def demo():
        return _demo_match(profile, job)

    return _real_or_demo(real, demo)


# ---------------------------------------------------------------------------
# 2b. skill_gaps: daftar skill yang kurang (turunan dari match_score)
# ---------------------------------------------------------------------------
def skill_gaps(profile: dict, job: dict) -> list[str]:
    """Kembalikan daftar skill/kualifikasi yang perlu ditambah kandidat."""
    return match_score(profile, job).get("gaps", [])


# ---------------------------------------------------------------------------
# 3. write_jd: poin kasar -> deskripsi lowongan profesional (Bahasa Indonesia)
# ---------------------------------------------------------------------------
SYS_JD = (
    "Kamu adalah HR writer profesional Indonesia. Dari poin-poin kasar berikut, "
    "tulis deskripsi lowongan kerja yang menarik dan profesional dalam Bahasa "
    "Indonesia dengan struktur: Tentang Perusahaan (1 paragraf singkat, boleh "
    "generik), Tanggung Jawab (bullet), Kualifikasi (bullet), Keuntungan "
    "(bullet). Kembalikan HANYA JSON valid dengan kunci: description (string)."
)


def write_jd(points: str, title: str, company: str) -> dict:
    def real():
        user = f"Judul posisi: {title}\nPerusahaan: {company}\nPoin-poin:\n{points}"
        return _complete(SYS_JD, user, max_tokens=2000)

    def demo():
        return {"description": _demo_write_jd(points, title, company)}

    return _real_or_demo(real, demo)


# ---------------------------------------------------------------------------
# 4. screen_applicants: ranking pelamar untuk satu lowongan
# ---------------------------------------------------------------------------
def screen_applicants(job: dict, applicants: list[dict]) -> list[dict]:
    """Kembalikan applicants terurut skor tertinggi, tiap item ditambah
    'score' dan 'reason' (ringkasan alasan)."""
    ranked = []
    for a in applicants:
        m = match_score(a.get("profile", {}), job)
        ranked.append({
            "user_id": a.get("user_id"),
            "name": a.get("name", ""),
            "score": int(m.get("score", 0)),
            "reason": m.get("explanation", ""),
            "applied_at": a.get("applied_at", 0),
        })
    ranked.sort(key=lambda x: (-x["score"], x["applied_at"]))
    return ranked


# ---------------------------------------------------------------------------
# 5. detect_fraud: klasifikasi pola lowongan penipuan
# ---------------------------------------------------------------------------
SYS_FRAUD = (
    "Kamu adalah analis keamanan rekrutmen. Periksa apakah lowongan berikut "
    "menunjukkan pola penipuan lowongan kerja (misal: meminta transfer/biaya "
    "administrasi/deposit/pulsa, gaji tidak wajar, proses instan tanpa seleksi, "
    "kontak pribadi WhatsApp/Telegram sebagai satu-satunya kanal, bahasa "
    "mendesak). Kembalikan HANYA JSON valid dengan kunci: flagged (boolean), "
    "reasons (array string Bahasa Indonesia, kosong jika tidak flagged)."
)


def detect_fraud(job: dict) -> dict:
    def real():
        user = (
            f"Judul: {job.get('title','')}\nLokasi: {job.get('location','')}\n"
            f"Deskripsi:\n{(job.get('description','') or '')[:6000]}"
        )
        return _complete(SYS_FRAUD, user, max_tokens=800)

    def demo():
        return _demo_detect_fraud(job)

    return _real_or_demo(real, demo)


# ===========================================================================
# MODE DEMO — implementasi deterministis tanpa API key
# ===========================================================================
SKILL_KEYWORDS = [
    # teknologi
    "python", "javascript", "typescript", "react", "vue", "node.js", "nodejs",
    "fastapi", "django", "flask", "laravel", "php", "java", "golang", "go",
    "sql", "mysql", "postgresql", "mongodb", "redis", "docker", "kubernetes",
    "git", "linux", "aws", "gcp", "machine learning", "data analysis",
    "data analyst", "excel", "tableau", "power bi", "figma", "ui/ux", "ui ux",
    "photoshop", "illustrator", "canva",
    # marketing & konten
    "digital marketing", "seo", "sem", "social media", "content writing",
    "copywriting", "copywriter", "branding", "ads", "meta ads", "google ads",
    "tiktok", "instagram", "email marketing",
    # bisnis & operasional
    "sales", "penjualan", "marketing", "customer service", "komunikasi",
    "negosiasi", "administrasi", "akuntansi", "accounting", "keuangan",
    "finance", "hr", "rekrutmen", "operasional", "logistik", "gudang",
    "inventory", "ms office", "microsoft office", "public speaking",
    "bahasa inggris", "english", "manajemen", "leadership", "kepemimpinan",
    "analisis", "problem solving", "kerja tim", "teliti", "manajemen waktu",
]


def _demo_parse_cv(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    name = ""
    for l in lines[:6]:
        words = l.split()
        if 2 <= len(words) <= 5 and not any(c.isdigit() for c in l) and "@" not in l:
            name = l.title() if l.isupper() else l
            break
    low = text.lower()
    skills = sorted({k for k in SKILL_KEYWORDS if k in low})
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    phone = re.search(r"(?:\+62|08)\d[\d\s-]{7,}", text)
    contact = " | ".join(x for x in [email.group(0) if email else "", phone.group(0) if phone else ""] if x)

    experience, education = [], []
    edu_pat = re.compile(r"s1|s2|sma|smk|d3|d4|universitas|institut|sekolah|politeknik", re.I)
    exp_pat = re.compile(r"20\d\d|tahun|years|pengalaman|staff|manager|asisten|magang|intern", re.I)
    for l in lines:
        if len(l) < 4 or len(l) > 220:
            continue
        if edu_pat.search(l) and len(education) < 5:
            education.append(l)
        elif exp_pat.search(l) and len(experience) < 8:
            experience.append(l)
    summary_bits = []
    if skills:
        summary_bits.append(f"Memiliki keahlian di bidang {', '.join(skills[:5])}.")
    if experience:
        summary_bits.append(f"Berpengalaman sebagai {experience[0][:90]}.")
    if contact:
        summary_bits.append(f"Kontak: {contact}.")
    summary = " ".join(summary_bits) or "Profil kandidat hasil ekstraksi CV."
    return {
        "name": name or "Nama belum terdeteksi",
        "summary": summary,
        "skills": skills[:20],
        "experience": experience,
        "education": education,
    }


def _job_keywords(job: dict) -> list[str]:
    text = f"{job.get('title','')} {job.get('description','')}".lower()
    found = [k for k in SKILL_KEYWORDS if k in text]
    # kata penting dari judul (selain stopwords)
    stop = {"dan", "di", "untuk", "dengan", "yang", "staff", "staf", "senior",
            "junior", "spesialis", "specialist", "manager", "asisten"}
    for w in re.findall(r"[a-zA-Z/\.]{3,}", job.get("title", "").lower()):
        w = w.strip("./")
        if w not in stop and w not in found and len(w) > 2:
            found.append(w)
    # dedup, jaga urutan
    seen, out = set(), []
    for k in found:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out[:25]


def _demo_match(profile: dict, job: dict) -> dict:
    pskills = {s.lower() for s in profile.get("skills", [])}
    job_kw = _job_keywords(job)
    matched = [k for k in job_kw if any(k in s or s in k for s in pskills)]
    missing = [k for k in job_kw if k not in matched]
    ratio = len(matched) / max(len(job_kw), 1)
    # bonus kecil bila ada pengalaman/pendidikan terisi
    bonus = 0
    if profile.get("experience"):
        bonus += 5
    if profile.get("education"):
        bonus += 5
    score = min(97, max(8, int(35 + 55 * ratio + bonus)))
    if score >= 75:
        verdict = "Kandidat sangat cocok untuk posisi ini."
    elif score >= 50:
        verdict = "Kandidat cukup cocok, dengan beberapa area pengembangan."
    else:
        verdict = "Kecocokan masih rendah untuk posisi ini."
    parts = [verdict]
    if matched:
        parts.append(f"Kekuatan: {', '.join(matched[:6])}.")
    if missing:
        parts.append(f"Yang perlu ditingkatkan: {', '.join(missing[:6])}.")
    gaps = missing[:5]
    return {
        "score": score,
        "explanation": " ".join(parts),
        "gaps": gaps,
    }


def _demo_write_jd(points: str, title: str, company: str) -> str:
    pts = [p.strip("-•* \t") for p in points.splitlines() if p.strip()]
    resp, qual = [], []
    for p in pts:
        pl = p.lower()
        if any(w in pl for w in ["pengalaman", "pendidikan", "s1", "sma", "smk", "d3",
                                 "mampu", "memiliki", "skill", "keahlian", "fresh graduate",
                                 "umur", "usia", "diutamakan"]):
            qual.append(p)
        else:
            resp.append(p)
    if not resp:
        resp = pts[:3]
    if not qual:
        qual = ["Pendidikan minimal SMA/SMK sederajat",
                "Memiliki kemauan belajar yang tinggi", "Mampu bekerja dalam tim"]
    lines = [
        f"# {title}",
        f"**{company}**",
        "",
        "## Tentang Perusahaan",
        f"{company} adalah perusahaan yang sedang berkembang dan membuka kesempatan "
        f"bagi talenta terbaik untuk bergabung sebagai {title}.",
        "",
        "## Tanggung Jawab",
    ]
    lines += [f"- {r}" for r in resp]
    lines += ["", "## Kualifikasi"]
    lines += [f"- {q}" for q in qual]
    lines += ["", "## Keuntungan",
              "- Gaji kompetitif dan tunjangan",
              "- Lingkungan kerja yang suportif",
              "- Kesempatan pengembangan karier"]
    return "\n".join(lines)


FRAUD_RULES = [
    (re.compile(r"transfer|kirim dana|kirim uang", re.I), "Meminta transfer dana ke kandidat"),
    (re.compile(r"biaya (admin|administrasi|pendaftaran|proses)", re.I), "Meminta biaya administrasi/pendaftaran"),
    (re.compile(r"deposit|uang muka|uang jaminan", re.I), "Meminta deposit/uang muka"),
    (re.compile(r"pulsa|top ?up|voucher", re.I), "Meminta pulsa/voucher"),
    (re.compile(r"tanpa (interview|seleksi|tes)", re.I), "Menjanjikan diterima tanpa proses seleksi"),
    (re.compile(r"(langsung|pasti) diterima", re.I), "Menjanjikan kepastian diterima"),
    (re.compile(r"gaji .*?(50|100)\s?juta", re.I), "Menawarkan gaji yang tidak wajar"),
    (re.compile(r"whatsapp|wa\s*[:\d]|hubungi .*08", re.I), "Hanya menyediakan kontak pribadi (WhatsApp/nomor HP)"),
    (re.compile(r"telegram", re.I), "Mengarahkan komunikasi via Telegram"),
    (re.compile(r"segera|terbatas|hari ini juga|kesempatan emas", re.I), "Bahasa mendesak yang menekan kandidat"),
    (re.compile(r"modal (ktp|nik)|foto ktp|data pribadi", re.I), "Meminta data pribadi sensitif di awal"),
]


def _demo_detect_fraud(job: dict) -> dict:
    text = f"{job.get('title','')}\n{job.get('description','')}"
    reasons = []
    for pat, reason in FRAUD_RULES:
        if pat.search(text) and reason not in reasons:
            reasons.append(reason)
    # gaji min-max jomplang ekstrem juga mencurigakan
    try:
        smin = int(job.get("salary_min") or 0)
        smax = int(job.get("salary_max") or 0)
        if smin and smax and smax > smin * 5 and "gaji tidak wajar" not in " ".join(reasons).lower():
            reasons.append("Rentang gaji terlalu lebar/tidak wajar")
    except Exception:
        pass
    return {"flagged": bool(reasons), "reasons": reasons}
