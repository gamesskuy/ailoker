"""Seed database: akun demo + ~12 lowongan realistis Indonesia.

Jalankan dari folder ~/workspace/ailoker:
    .venv/bin/python -m app.seed

Kredensial demo (juga didokumentasikan di README.md):
    Perusahaan : perusahaan@ailoker.com / demo1234
    Pencari    : pencari@ailoker.com    / demo1234
    Pencari 2  : sinta@ailoker.com      / demo1234
"""
from . import auth, db

JOBS = [
    ("Frontend Developer (React)", "Jakarta Selatan", "Penuh Waktu", 8000000, 14000000,
     "Membangun dan memelihara antarmuka web menggunakan React dan TypeScript. "
     "Berkolaborasi dengan desainer UI/UX dan backend developer. Skill: javascript, react, typescript, git, figma."),
    ("Backend Developer Python", "Bandung", "Remote", 9000000, 15000000,
     "Mengembangkan API dengan Python (FastAPI/Django), mengelola database PostgreSQL, "
     "dan deployment dengan Docker. Skill: python, fastapi, sql, postgresql, docker, git, linux."),
    ("Data Analyst", "Jakarta Pusat", "Penuh Waktu", 7000000, 12000000,
     "Menganalisis data bisnis, membuat dashboard, dan menyusun laporan berkala. "
     "Skill: sql, excel, data analysis, tableau, power bi, analisis, komunikasi."),
    ("Digital Marketing Specialist", "Surabaya", "Penuh Waktu", 6000000, 10000000,
     "Mengelola kampanye iklan digital, SEO, dan media sosial perusahaan. "
     "Skill: digital marketing, seo, social media, meta ads, google ads, content writing."),
    ("Content Writer", "Remote", "Kontrak", 5000000, 8000000,
     "Menulis artikel SEO, copywriting untuk media sosial, dan materi pemasaran. "
     "Skill: content writing, copywriting, copywriter, seo, bahasa inggris."),
    ("UI/UX Designer", "Jakarta Selatan", "Penuh Waktu", 8000000, 13000000,
     "Merancang wireframe, prototype, dan design system untuk aplikasi mobile dan web. "
     "Skill: figma, ui/ux, ui ux, photoshop, illustrator, canva."),
    ("Customer Service", "Tangerang", "Penuh Waktu", 4500000, 6000000,
     "Melayani pertanyaan pelanggan via chat, telepon, dan email dengan ramah dan solutif. "
     "Skill: customer service, komunikasi, problem solving, ms office."),
    ("Staff Administrasi", "Bekasi", "Penuh Waktu", 4800000, 6500000,
     "Mengelola dokumen, data entry, arsip, dan administrasi operasional kantor. "
     "Skill: administrasi, excel, microsoft office, ms office, teliti, manajemen waktu."),
    ("Sales Executive", "Jakarta Barat", "Penuh Waktu", 5000000, 12000000,
     "Mencari pelanggan baru, presentasi produk, dan mencapai target penjualan. "
     "Skill: sales, penjualan, negosiasi, komunikasi, public speaking."),
    ("Staff Accounting", "Jakarta Utara", "Penuh Waktu", 6000000, 9000000,
     "Menyusun laporan keuangan, jurnal, dan rekonsiliasi bank. "
     "Skill: akuntansi, accounting, keuangan, finance, excel, teliti."),
    ("Social Media Specialist", "Yogyakarta", "Penuh Waktu", 5500000, 8500000,
     "Mengelola konten Instagram dan TikTok, analisis performa, dan community management. "
     "Skill: social media, tiktok, instagram, content writing, canva, branding."),
    ("Barista", "Denpasar", "Paruh Waktu", 3000000, 4500000,
     "Menyajikan kopi dan minuman, menjaga kebersihan bar, melayani pelanggan kafe. "
     "Skill: komunikasi, kerja tim, teliti, public speaking."),
]


def seed():
    db.init_db()
    # --- akun demo ---
    company_id = auth.create_user("perusahaan@ailoker.com", "demo1234", "company",
                                  "Admin", "PT Maju Digital Nusantara")
    seeker_id = auth.create_user("pencari@ailoker.com", "demo1234", "seeker", "Budi Santoso")
    seeker2_id = auth.create_user("sinta@ailoker.com", "demo1234", "seeker", "Sinta Maharani")

    conn = db.connect()
    try:
        for title, loc, jtype, smin, smax, desc in JOBS:
            conn.execute(
                "INSERT INTO jobs (company_id, title, location, job_type, salary_min, salary_max,"
                " description, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (company_id, title, loc, jtype, smin, smax, desc, db.now()),
            )
        conn.commit()
    finally:
        conn.close()

    # --- profil contoh untuk 2 pencari kerja ---
    from . import main as app_main
    app_main.save_profile(seeker_id, {
        "name": "Budi Santoso",
        "summary": "Fresh graduate Informatika dengan pengalaman magang web development. "
                   "Terbiasa membangun aplikasi dengan React dan Python.",
        "skills": ["javascript", "react", "python", "git", "sql", "figma", "komunikasi"],
        "experience": ["Magang Web Developer di PT Startup Kita (2025): membangun dashboard admin dengan React",
                       "Asisten praktikum Pemrograman Web, Universitas Indonesia (2024)"],
        "education": ["S1 Informatika, Universitas Indonesia (2021-2025)"],
        "raw_text": "",
    })
    app_main.save_profile(seeker2_id, {
        "name": "Sinta Maharani",
        "summary": "Digital marketer dengan 2 tahun pengalaman mengelola kampanye iklan dan media sosial.",
        "skills": ["digital marketing", "seo", "social media", "content writing", "meta ads",
                   "tiktok", "instagram", "copywriting", "komunikasi"],
        "experience": ["Digital Marketing Staff di PT Kreatif Bangsa (2023-sekarang): mengelola budget iklan Rp 50jt/bulan",
                       "Content Writer freelance (2022)"],
        "education": ["S1 Komunikasi, Universitas Gadjah Mada (2019-2023)"],
        "raw_text": "",
    })
    print("Seed selesai: 3 akun demo + 12 lowongan.")


if __name__ == "__main__":
    seed()
