# AILoker — Dokumen Konsep Produk
Domain: ailoker.com · Dibuat: 13 Okt 2026 · Status: draf konsep (pra-MVP)

## 1. Satu kalimat
AILoker adalah platform lowongan kerja Indonesia yang AI-native: bukan sekadar papan lowongan, tapi **kopilot karier** untuk pencari kerja dan **asisten rekrutmen** untuk perusahaan — semuanya ditenagai Claude.

## 2. Masalah yang dipecahkan
- **Pencari kerja:** melamar membabi-buta ke ratusan lowongan tanpa tahu kecocokannya; CV tidak teroptimasi; tidak tahu skill apa yang kurang; interview gagal tanpa feedback.
- **Perusahaan (terutama UMKM):** kebanjiran lamaran yang tidak relevan; tidak punya tim HR untuk screening; menulis deskripsi lowongan yang bagus itu susah dan lama.
- **Kepercayaan:** lowongan palsu/penipuan masih jadi masalah besar di portal Indonesia.

## 3. Target pengguna
1. **Pencari kerja** usia 18–35, entry hingga mid-level, melek digital (segmen terbesar pasar loker Indonesia).
2. **Perusahaan/UMKM** yang rekrut rutin tapi tidak punya tim HRD besar — segmen yang paling terbebani biaya screening.

## 4. Diferensiasi vs kompetitor
| Kompetitor | Fokus AI mereka | Celah yang diambil AILoker |
|---|---|---|
| KitaLulus (10 jt+ pencari kerja) | AI untuk *screening pelamar* (sisi perusahaan) | AI untuk *sisi pencari kerja*: match score, skill gap, latihan interview |
| Glints | "Rekomendasi AI" kandidat untuk employer (fitur premium) | Match dua arah + explainability: kandidat tahu *kenapa* cocok/tidak |
| JobStreet / Kalibrr | Notifikasi & filter konvensional | Pengalaman AI-first sejak hari pertama, bukan tempelan |
| Portal generik | Daftar lowongan | Kopilot karier: CV → match → persiapan interview → diterima |

**Posisi:** kompetitor menaruh AI di sisi perusahaan. AILoker menaruh AI di **kedua sisi**, dengan keunggulan di sisi pencari kerja yang belum digarap serius.

## 5. Fitur

### Fase 1 — MVP (target 3–4 minggu)
**Sisi pencari kerja**
1. **Upload CV → profil pintar.** Claude mengekstrak pengalaman, skill, pendidikan dari PDF/DOC (document understanding), membangun profil terstruktur otomatis.
2. **Match score per lowongan.** Setiap lowongan menampilkan skor kecocokan 0–100 **beserta penjelasan** ("kamu cocok karena X, kurang di Y"). Ini fitur pembeda utama.
3. **Skill gap analysis.** "Untuk lolos ke posisi ini, kamu perlu menambah: skill A, sertifikasi B" + rekomendasi belajar.
4. **Pencarian & daftar lowongan** yang bersih, mobile-first, Bahasa Indonesia.

**Sisi perusahaan**
5. **JD Writer.** Perusahaan tulis 3–5 poin kasar → Claude menghasilkan deskripsi lowongan profesional dalam Bahasa Indonesia yang menarik.
6. **Screening & ranking pelamar.** Setiap pelamar masuk langsung ter-ranking dengan ringkasan alasan — hemat 80% waktu sortir manual.
7. **Deteksi lowongan bermasalah.** Klasifikasi otomatis menandai pola lowongan palsu/penipuan sebelum tayang (menjawab isu kepercayaan pasar).

### Fase 2 — setelah MVP jalan
8. **Mock interview AI.** Chat simulasi interview per posisi, dengan feedback terstruktur (isi jawaban, bahasa tubuh tidak dinilai — fokus ke konten).
9. **CV rewriter & cover letter generator** (freemium → premium).
10. **Interview question generator** untuk perusahaan + penjadwalan.
11. **Notifikasi WhatsApp** untuk lowongan yang match-nya tinggi (jalur distribusi khas Indonesia).

## 6. Bagaimana Claude dipakai (inti aplikasi Claude Startups)
Setiap fitur AI di atas memanggil Claude API secara langsung — bukan tempelan:
- **Document understanding:** parsing CV multiformat.
- **Reasoning + explainability:** match score yang bisa dijelaskan, bukan black box.
- **Generation (Bahasa Indonesia):** JD writer, CV rewrite, cover letter, pertanyaan interview.
- **Classification:** deteksi lowongan palsu, kategorisasi skill.
- **Conversational:** mock interview multi-turn.

Rencana penggunaan kredit $1.000: inferensi match/scoring (volume tinggi, pakai model efisien + prompt caching), fitur generation premium (model lebih besar). Estimasi kasar akan dihitung saat MVP — arsitektur dibuat hemat token sejak awal (caching, batch, ekstraksi sekali-simpan).

## 7. Model bisnis
- **Pencari kerja:** gratis untuk fitur inti (match score dasar, pencarian). Premium (langganan bulanan): analisis mendalam, mock interview tanpa batas, CV rewrite.
- **Perusahaan:** gratis pasang 1 lowongan (akuisisi). Berbayar: paket lowongan + kuota AI screening; tier enterprise untuk volume besar.
- Prinsip: sisi pencari kerja murah/gratis untuk membangun likuiditas; monetisasi utama dari perusahaan.

## 8. Go-to-market awal
1. Launch MVP dengan 50–100 lowongan (ajak UMKM lewat jaringan + scraping agregasi berizin).
2. Konten SEO Bahasa Indonesia: "contoh CV", "cara lolos interview" — digerakkan AI, ditinjau manusia.
3. Komunitas: grup Telegram/Discord pencari kerja; referral "undang teman dapat premium".

## 9. Kenapa cocok untuk Claude Startups
- AI-native sejak hari pertama, bukan fitur tempelan — seluruh value proposition bergantung pada Claude API.
- Memenuhi syarat: startup baru (< 5 tahun), bootstrapped boleh, butuh akun Claude Console + email domain perusahaan (siapkan: halo@ailoker.com).
- Narasi aplikasi: "membawa manfaat AI ke jutaan pencari kerja Indonesia lewat perusahaan yang dibangun di atas Claude" — selaras dengan misi program.
- ⚠️ UPDATE 2026-10-13: sejak 9 Okt 2026 Anthropic mem-PAUSE benefit $1.000 kredit API dan gratis Claude Team setahun (kelebihan pendaftar; ratusan ribu aplikasi). Pendaftaran tetap dibuka — yang didapat saat ini: Claude Startup Stack (penawaran partner s.d. $45K), office hours, events. Tetap daftar untuk antrean & manfaatkan Stack; jangan rencanakan budget dengan asumsi $1.000 akan kembali.

## 10. Risiko & mitigasi
- **Biaya inferensi** membengkak saat skala → prompt caching, model tiering (Haiku untuk volume, Sonnet/Opus untuk premium), rate limit per user.
- **Cold start dua sisi** (butuh lowongan + pelamar sekaligus) → mulai dari sisi perusahaan/UMKM dengan JD writer gratis sebagai umpan.
- **Kompetitor meniru fitur AI** → kecepatan eksekusi + data match lokal sebagai moat.

## 11. Langkah selanjutnya
1. Finalisasi konsep ini (revisi bila perlu).
2. Setup: email halo@ailoker.com + akun Claude Console atas nama perusahaan.
3. Bangun MVP Fase 1 (landing + auth + CV upload + match score + JD writer + job board).
4. Isi 50+ lowongan awal, uji dengan 20–50 pengguna beta.
5. Daftar Claude Startups dengan produk yang sudah bisa dicoba.
