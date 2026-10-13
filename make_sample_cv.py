"""Membuat contoh CV PDF sederhana untuk pengujian upload (tanpa dependensi tambahan).

Jalankan:  .venv/bin/python make_sample_cv.py   -> menghasilkan sample_cv.pdf
"""
import os

LINES = [
    "BUDI SANTOSO",
    "budi.santoso@email.com | 0812-3456-7890 | Jakarta",
    "",
    "RINGKASAN",
    "Fresh graduate Informatika dengan pengalaman magang web development.",
    "Terbiasa membangun aplikasi web modern menggunakan React dan Python.",
    "",
    "PENGALAMAN",
    "Magang Web Developer - PT Startup Kita (Jan 2025 - Jun 2025)",
    "Membangun dashboard admin dengan React, TypeScript, dan integrasi REST API.",
    "Asisten Praktikum Pemrograman Web - Universitas Indonesia (2024)",
    "Membimbing 40 mahasiswa dalam praktikum JavaScript dan SQL.",
    "",
    "PENDIDIKAN",
    "S1 Informatika - Universitas Indonesia (2021 - 2025), IPK 3.62",
    "SMA Negeri 1 Jakarta (2018 - 2021)",
    "",
    "KEAHLIAN",
    "JavaScript, React, TypeScript, Python, SQL, Git, Figma, Komunikasi, Excel",
]

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_cv.pdf")


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(lines, path):
    content_lines = ["BT", "/F1 11 Tf", "50 770 Td", "14 TL"]
    for i, line in enumerate(lines):
        if i:
            content_lines.append("T*")
        content_lines.append(f"({_escape(line)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1")

    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>")
    objs.append(b"<< /Type /Subtype /Type1 /BaseFont /Helvetica >>")
    objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")

    out = [b"%PDF-1.4"]
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(sum(len(x) + 1 for x in out))
        out.append(b"%d 0 obj\n" % i + body + b"\nendobj")
    xref_pos = sum(len(x) + 1 for x in out)
    out.append(b"xref")
    out.append(b"0 %d" % (len(objs) + 1))
    out.append(b"0000000000 65535 f ")
    for off in offsets:
        out.append(b"%010d 00000 n " % off)
    out.append(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF"
               % (len(objs) + 1, xref_pos))
    with open(path, "wb") as f:
        f.write(b"\n".join(out))
    print("Ditulis:", path, f"({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    build_pdf(LINES, OUT)
