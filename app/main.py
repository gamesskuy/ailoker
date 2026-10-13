"""AILoker MVP — aplikasi web lowongan kerja AI-native (Bahasa Indonesia).

Jalankan:  uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
dari folder ~/workspace/ailoker (lihat README.md).
"""
import os
import threading
from urllib.parse import quote_plus

from fastapi import Cookie, FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pypdf import PdfReader

from . import ai, auth, db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app = FastAPI(title="AILoker")


# ---------------------------------------------------------------------------
# Inisialisasi DB malas — untuk serverless (Vercel): lifespan startup tidak
# dijamin jalan, jadi init + auto-seed dilakukan sekali saat cold start,
# dipicu oleh request pertama. Idempoten & aman untuk uvicorn/Docker juga.
# ---------------------------------------------------------------------------
_db_init_lock = threading.Lock()
_db_ready = False


@app.middleware("http")
async def _ensure_db_ready(request: Request, call_next):
    global _db_ready
    if not _db_ready:
        with _db_init_lock:
            if not _db_ready:
                try:
                    db.init_db()
                    if os.environ.get("AILOKER_AUTO_SEED", "1") == "1":
                        conn = db.connect()
                        try:
                            n_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                        finally:
                            conn.close()
                        if n_users == 0:
                            from . import seed as seed_mod
                            seed_mod.seed()
                except Exception as e:  # jangan gagalkan request gara-gara init
                    print(f"[db] init malas dilewati/gagal: {e}")
                _db_ready = True
    return await call_next(request)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def flash(url: str, msg: str) -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    return RedirectResponse(f"{url}{sep}msg={quote_plus(msg)}", status_code=303)


def current_user(token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    return auth.get_session_user(token)


def set_session(resp: RedirectResponse, token: str) -> RedirectResponse:
    resp.set_cookie(auth.SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=30 * 86400)
    return resp


def base_ctx(request: Request, user=None, msg: str = "") -> dict:
    return {
        "request": request,
        "user": user,
        "msg": msg,
        "format_rp": format_rp,
    }


def tr(request: Request, name: str, ctx: dict) -> HTMLResponse:
    """TemplateResponse untuk Starlette >= 1.x: request argumen pertama."""
    ctx = {k: v for k, v in ctx.items() if k != "request"}
    return templates.TemplateResponse(request, name, ctx)


def format_rp(n) -> str:
    try:
        n = int(n or 0)
    except Exception:
        return "-"
    if n <= 0:
        return "Gaji tidak ditampilkan"
    return "Rp " + f"{n:,}".replace(",", ".")


def get_profile(user_id) -> dict | None:
    conn = db.connect()
    try:
        row = conn.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return {
        "name": row["name"], "summary": row["summary"],
        "skills": db.jload(row["skills"], []),
        "experience": db.jload(row["experience"], []),
        "education": db.jload(row["education"], []),
        "raw_text": row["raw_text"],
    }


def save_profile(user_id, prof: dict):
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO profiles (user_id, name, summary, skills, experience, education, raw_text, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?)"
            " ON CONFLICT(user_id) DO UPDATE SET name=excluded.name, summary=excluded.summary,"
            " skills=excluded.skills, experience=excluded.experience, education=excluded.education,"
            " raw_text=excluded.raw_text, updated_at=excluded.updated_at",
            (user_id, prof.get("name", ""), prof.get("summary", ""),
             db.jdump(prof.get("skills", [])), db.jdump(prof.get("experience", [])),
             db.jdump(prof.get("education", [])), prof.get("raw_text", ""), db.now()),
        )
        # profil berubah -> cache match tidak valid lagi (hemat token: hitung ulang saat dibutuhkan)
        conn.execute("DELETE FROM match_cache WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def get_or_compute_match(user_id, job_row) -> dict:
    conn = db.connect()
    try:
        cached = conn.execute(
            "SELECT score, explanation, gaps FROM match_cache WHERE user_id=? AND job_id=?",
            (user_id, job_row["id"]),
        ).fetchone()
    finally:
        conn.close()
    if cached:
        return {"score": cached["score"], "explanation": cached["explanation"],
                "gaps": db.jload(cached["gaps"], [])}
    profile = get_profile(user_id) or {}
    job = {"title": job_row["title"], "location": job_row["location"],
           "description": job_row["description"]}
    m = ai.match_score(profile, job)
    conn = db.connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO match_cache (user_id, job_id, score, explanation, gaps, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (user_id, job_row["id"], int(m.get("score", 0)), m.get("explanation", ""),
             db.jdump(m.get("gaps", [])), db.now()),
        )
        conn.commit()
    finally:
        conn.close()
    return {"score": int(m.get("score", 0)), "explanation": m.get("explanation", ""),
            "gaps": m.get("gaps", [])}


# ---------------------------------------------------------------------------
# Landing & job board publik
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def landing(request: Request, msg: str = "", token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    user = auth.get_session_user(token)
    conn = db.connect()
    try:
        n_jobs = conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"]
        n_comp = conn.execute("SELECT COUNT(*) c FROM users WHERE role='company'").fetchone()["c"]
        n_apply = conn.execute("SELECT COUNT(*) c FROM applications").fetchone()["c"]
        latest = conn.execute(
            "SELECT j.*, u.company_name FROM jobs j JOIN users u ON u.id=j.company_id"
            " ORDER BY j.created_at DESC LIMIT 6").fetchall()
    finally:
        conn.close()
    ctx = base_ctx(request, user, msg)
    ctx.update(n_jobs=n_jobs, n_companies=n_comp, n_apply=n_apply, latest=latest)
    return tr(request, "index.html", ctx)


@app.get("/loker", response_class=HTMLResponse)
def loker_list(request: Request, q: str = "", lokasi: str = "", msg: str = "",
               token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    user = auth.get_session_user(token)
    conn = db.connect()
    try:
        sql = ("SELECT j.*, u.company_name FROM jobs j JOIN users u ON u.id=j.company_id WHERE 1=1")
        params = []
        if q:
            sql += " AND (j.title LIKE ? OR j.description LIKE ? OR u.company_name LIKE ?)"
            params += [f"%{q}%"] * 3
        if lokasi:
            sql += " AND j.location LIKE ?"
            params.append(f"%{lokasi}%")
        sql += " ORDER BY j.created_at DESC"
        jobs = conn.execute(sql, params).fetchall()
        locs = [r["location"] for r in conn.execute("SELECT DISTINCT location FROM jobs ORDER BY location")]
    finally:
        conn.close()
    # skor untuk pencari kerja yang login & punya profil
    scores = {}
    if user and user["role"] == "seeker" and get_profile(user["id"]):
        for j in jobs:
            scores[j["id"]] = get_or_compute_match(user["id"], j)["score"]
    ctx = base_ctx(request, user, msg)
    ctx.update(jobs=jobs, q=q, lokasi=lokasi, locations=locs, scores=scores)
    return tr(request, "loker_list.html", ctx)


@app.get("/loker/{job_id}", response_class=HTMLResponse)
def loker_detail(request: Request, job_id: int, msg: str = "",
                 token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    user = auth.get_session_user(token)
    conn = db.connect()
    try:
        job = conn.execute(
            "SELECT j.*, u.company_name FROM jobs j JOIN users u ON u.id=j.company_id WHERE j.id=?",
            (job_id,)).fetchone()
        applied = False
        if user and user["role"] == "seeker":
            applied = conn.execute(
                "SELECT 1 FROM applications WHERE job_id=? AND user_id=?",
                (job_id, user["id"])).fetchone() is not None
    finally:
        conn.close()
    if not job:
        return HTMLResponse("Lowongan tidak ditemukan", status_code=404)
    match = None
    if user and user["role"] == "seeker" and get_profile(user["id"]):
        match = get_or_compute_match(user["id"], job)
    ctx = base_ctx(request, user, msg)
    ctx.update(job=job, match=match, applied=applied)
    return tr(request, "loker_detail.html", ctx)


@app.post("/loker/{job_id}/lamar")
def lamar(job_id: int, token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    user = auth.get_session_user(token)
    if not user:
        return flash("/masuk", "Silakan masuk dulu untuk melamar.")
    if user["role"] != "seeker":
        return flash(f"/loker/{job_id}", "Hanya pencari kerja yang bisa melamar.")
    conn = db.connect()
    try:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        exists = conn.execute("SELECT 1 FROM applications WHERE job_id=? AND user_id=?",
                              (job_id, user["id"])).fetchone()
    finally:
        conn.close()
    if not job:
        return flash("/loker", "Lowongan tidak ditemukan.")
    if exists:
        return flash(f"/loker/{job_id}", "Kamu sudah melamar lowongan ini.")
    profile = get_profile(user["id"]) or {}
    m = get_or_compute_match(user["id"], job)
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO applications (job_id, user_id, ai_score, ai_reason, created_at)"
            " VALUES (?,?,?,?,?)",
            (job_id, user["id"], m["score"], m["explanation"], db.now()),
        )
        conn.commit()
    finally:
        conn.close()
    return flash(f"/loker/{job_id}", f"Lamaran terkirim! Skor kecocokanmu: {m['score']}/100.")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@app.get("/daftar", response_class=HTMLResponse)
def daftar_form(request: Request, msg: str = ""):
    return tr(request, "daftar.html", base_ctx(request, None, msg))


@app.post("/daftar")
def daftar(email: str = Form(...), password: str = Form(...), nama: str = Form(...),
           role: str = Form(...), perusahaan: str = Form("")):
    if role not in ("seeker", "company"):
        return flash("/daftar", "Peran tidak valid.")
    if len(password) < 6:
        return flash("/daftar", "Kata sandi minimal 6 karakter.")
    if auth.get_user_by_email(email):
        return flash("/daftar", "Email sudah terdaftar. Silakan masuk.")
    try:
        uid = auth.create_user(email, password, role, nama, perusahaan if role == "company" else None)
    except Exception:
        return flash("/daftar", "Gagal mendaftar, coba lagi.")
    resp = flash("/profil" if role == "seeker" else "/perusahaan",
                 "Pendaftaran berhasil! Selamat datang di AILoker.")
    return set_session(resp, auth.create_session(uid))


@app.get("/masuk", response_class=HTMLResponse)
def masuk_form(request: Request, msg: str = ""):
    return tr(request, "masuk.html", base_ctx(request, None, msg))


@app.post("/masuk")
def masuk(email: str = Form(...), password: str = Form(...)):
    user = auth.get_user_by_email(email)
    if not user or not auth.verify_password(password, user["salt"], user["password_hash"]):
        return flash("/masuk", "Email atau kata sandi salah.")
    dest = "/profil" if user["role"] == "seeker" else "/perusahaan"
    resp = flash(dest, f"Selamat datang kembali, {user['name']}!")
    return set_session(resp, auth.create_session(user["id"]))


@app.post("/keluar")
def keluar(token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    auth.delete_session(token)
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(auth.SESSION_COOKIE)
    return resp


# ---------------------------------------------------------------------------
# Pencari kerja: profil & CV
# ---------------------------------------------------------------------------
def _require_seeker(user):
    if not user:
        return flash("/masuk", "Silakan masuk dulu.")
    if user["role"] != "seeker":
        return flash("/", "Halaman ini khusus pencari kerja.")
    return None


@app.get("/profil", response_class=HTMLResponse)
def profil(request: Request, msg: str = "",
           token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    user = auth.get_session_user(token)
    redir = _require_seeker(user)
    if redir:
        return redir
    profile = get_profile(user["id"])
    conn = db.connect()
    try:
        lamaran = conn.execute(
            "SELECT a.*, j.title, u.company_name FROM applications a"
            " JOIN jobs j ON j.id=a.job_id JOIN users u ON u.id=j.company_id"
            " WHERE a.user_id=? ORDER BY a.created_at DESC", (user["id"],)).fetchall()
    finally:
        conn.close()
    ctx = base_ctx(request, user, msg)
    ctx.update(profile=profile, lamaran=lamaran)
    return tr(request, "profil.html", ctx)


@app.post("/profil/upload")
async def upload_cv(cv: UploadFile = File(...),
                    token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    user = auth.get_session_user(token)
    redir = _require_seeker(user)
    if redir:
        return redir
    if not cv.filename.lower().endswith(".pdf"):
        return flash("/profil", "File harus berformat PDF.")
    data = await cv.read()
    if len(data) > 5 * 1024 * 1024:
        return flash("/profil", "Ukuran file maksimal 5 MB.")
    try:
        reader = PdfReader(__import__("io").BytesIO(data))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return flash("/profil", "Gagal membaca PDF. Pastikan file tidak rusak.")
    if len(text.strip()) < 30:
        return flash("/profil", "Teks CV tidak terbaca (mungkin hasil scan gambar).")
    parsed = ai.parse_cv(text)
    save_profile(user["id"], {
        "name": parsed.get("name", user["name"]),
        "summary": parsed.get("summary", ""),
        "skills": parsed.get("skills", []),
        "experience": parsed.get("experience", []),
        "education": parsed.get("education", []),
        "raw_text": text[:20000],
    })
    return flash("/profil", "CV berhasil dianalisis AI dan profilmu sudah diperbarui!")


@app.post("/profil/simpan")
def simpan_profil(nama: str = Form(""), ringkasan: str = Form(""),
                  skills: str = Form(""), pengalaman: str = Form(""),
                  pendidikan: str = Form(""),
                  token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    user = auth.get_session_user(token)
    redir = _require_seeker(user)
    if redir:
        return redir
    old = get_profile(user["id"]) or {}
    save_profile(user["id"], {
        "name": nama.strip() or old.get("name", ""),
        "summary": ringkasan.strip(),
        "skills": [s.strip() for s in skills.split(",") if s.strip()],
        "experience": [s.strip() for s in pengalaman.splitlines() if s.strip()],
        "education": [s.strip() for s in pendidikan.splitlines() if s.strip()],
        "raw_text": old.get("raw_text", ""),
    })
    return flash("/profil", "Profil berhasil disimpan.")


# ---------------------------------------------------------------------------
# Perusahaan: JD Writer, terbitkan lowongan, ranking pelamar
# ---------------------------------------------------------------------------
def _require_company(user):
    if not user:
        return flash("/masuk", "Silakan masuk dulu.")
    if user["role"] != "company":
        return flash("/", "Halaman ini khusus perusahaan.")
    return None


@app.get("/perusahaan", response_class=HTMLResponse)
def perusahaan_dash(request: Request, msg: str = "",
                    token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    user = auth.get_session_user(token)
    redir = _require_company(user)
    if redir:
        return redir
    conn = db.connect()
    try:
        jobs = conn.execute(
            "SELECT j.*, (SELECT COUNT(*) FROM applications a WHERE a.job_id=j.id) AS n_apply"
            " FROM jobs j WHERE j.company_id=? ORDER BY j.created_at DESC", (user["id"],)).fetchall()
    finally:
        conn.close()
    ctx = base_ctx(request, user, msg)
    ctx.update(jobs=jobs)
    return tr(request, "perusahaan_dashboard.html", ctx)


@app.get("/perusahaan/loker/baru", response_class=HTMLResponse)
def loker_baru_form(request: Request, msg: str = "",
                    token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    user = auth.get_session_user(token)
    redir = _require_company(user)
    if redir:
        return redir
    return tr(request, "loker_baru.html", base_ctx(request, user, msg))


@app.post("/perusahaan/loker/buat-jd", response_class=HTMLResponse)
def buat_jd(request: Request, judul: str = Form(...), lokasi: str = Form(""),
            tipe: str = Form("Penuh Waktu"), gaji_min: str = Form("0"),
            gaji_max: str = Form("0"), poin: str = Form(...),
            token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    user = auth.get_session_user(token)
    redir = _require_company(user)
    if redir:
        return redir
    company = user["company_name"] or user["name"]
    jd = ai.write_jd(poin, judul.strip(), company)
    description = jd.get("description", "")
    fraud = ai.detect_fraud({"title": judul, "location": lokasi, "description": description,
                             "salary_min": gaji_min, "salary_max": gaji_max})
    ctx = base_ctx(request, user)
    ctx.update(judul=judul, lokasi=lokasi, tipe=tipe, gaji_min=gaji_min, gaji_max=gaji_max,
               poin=poin, description=description, fraud=fraud)
    return tr(request, "loker_preview.html", ctx)


@app.post("/perusahaan/loker/terbitkan")
def terbitkan(judul: str = Form(...), lokasi: str = Form(""), tipe: str = Form("Penuh Waktu"),
              gaji_min: str = Form("0"), gaji_max: str = Form("0"),
              deskripsi: str = Form(...), abaikan_peringatan: str = Form(""),
              token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    user = auth.get_session_user(token)
    redir = _require_company(user)
    if redir:
        return redir
    fraud = ai.detect_fraud({"title": judul, "description": deskripsi,
                             "salary_min": gaji_min, "salary_max": gaji_max})
    if fraud.get("flagged") and not abaikan_peringatan:
        # Minta perbaikan dulu: kembali ke form dengan alasan yang jelas.
        return flash("/perusahaan/loker/baru",
                     "Terdeteksi pola bermasalah: " + "; ".join(fraud["reasons"][:2])
                     + ". Perbaiki deskripsi lalu coba lagi.")
    try:
        smin, smax = int(gaji_min or 0), int(gaji_max or 0)
    except ValueError:
        smin, smax = 0, 0
    conn = db.connect()
    try:
        cur = conn.execute(
            "INSERT INTO jobs (company_id, title, location, job_type, salary_min, salary_max,"
            " description, points_raw, fraud_warning, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (user["id"], judul.strip(), lokasi.strip(), tipe, smin, smax, deskripsi,
             "", db.jdump(fraud.get("reasons", [])), db.now()),
        )
        conn.commit()
        jid = cur.lastrowid
    finally:
        conn.close()
    return flash("/perusahaan", f"Lowongan '{judul.strip()}' berhasil diterbitkan!")


@app.get("/perusahaan/loker/{job_id}/pelamar", response_class=HTMLResponse)
def daftar_pelamar(request: Request, job_id: int, msg: str = "",
                   token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE)):
    user = auth.get_session_user(token)
    redir = _require_company(user)
    if redir:
        return redir
    conn = db.connect()
    try:
        job = conn.execute("SELECT * FROM jobs WHERE id=? AND company_id=?",
                           (job_id, user["id"])).fetchone()
        rows = conn.execute(
            "SELECT a.*, u.name AS nama FROM applications a JOIN users u ON u.id=a.user_id"
            " WHERE a.job_id=? ORDER BY a.created_at", (job_id,)).fetchall() if job else []
    finally:
        conn.close()
    if not job:
        return HTMLResponse("Lowongan tidak ditemukan", status_code=404)
    applicants = []
    for r in rows:
        applicants.append({
            "user_id": r["user_id"], "name": r["nama"],
            "profile": get_profile(r["user_id"]) or {},
            "applied_at": r["created_at"],
        })
    ranked = ai.screen_applicants(
        {"title": job["title"], "location": job["location"], "description": job["description"]},
        applicants)
    ctx = base_ctx(request, user, msg)
    ctx.update(job=job, ranked=ranked)
    return tr(request, "pelamar.html", ctx)


# ---------------------------------------------------------------------------
@app.on_event("startup")
def _startup():
    db.init_db()
    # Auto-seed saat database masih kosong (deploy fresh di hosting).
    # Nonaktifkan dengan AILOKER_AUTO_SEED=0 bila tidak diinginkan.
    if os.environ.get("AILOKER_AUTO_SEED", "1") == "1":
        try:
            conn = db.connect()
            try:
                n_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            finally:
                conn.close()
            if n_users == 0:
                from . import seed as seed_mod
                seed_mod.seed()
        except Exception as e:  # jangan gagalkan startup gara-gara seed
            print(f"[startup] auto-seed dilewati/gagal: {e}")
