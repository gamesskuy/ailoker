# DRAF aplikasi Claude Startups — AILoker
> Status: draf, Bahasa Inggris. Sesuaikan/diisi yang bertanda [isi] sebelum submit.
> Form aslinya mungkin menanyakan hal yang sedikit berbeda — pakai teks ini sebagai bahan.

## Company one-liner
AILoker (ailoker.com) — Indonesia's AI-native job platform: a career copilot for job seekers and an AI recruiting assistant for employers, built on Claude.

## What are you building? (jawaban panjang)
AILoker is an AI-native job platform for Indonesia. For job seekers (18–35, entry to mid-level), it's a career copilot: upload a CV and Claude builds a smart profile, every job listing shows an explainable 0–100 match score ("you fit because of X, you're missing Y"), plus skill-gap analysis. For employers (especially SMEs without HR teams), it's a recruiting assistant: a Bahasa Indonesia JD writer, automatic applicant ranking with reasons, and fraud detection that blocks scam listings before they go live. Unlike incumbents (KitaLulus, Glints) that put AI on the employer side, AILoker puts AI on both sides — with the job-seeker side as the key differentiator.

## How do you use Claude?
Every AI feature calls the Claude API directly — it is the product, not an add-on:
- **Document understanding:** CV parsing (PDF) into structured profiles.
- **Reasoning + explainability:** match scores with human-readable explanations, never a black box.
- **Generation (Bahasa Indonesia):** JD writer, CV rewrite, cover letters, interview questions.
- **Classification:** scam/fraudulent job detection, skill categorization.
- **Conversational (roadmap):** multi-turn mock interviews with structured feedback.

Architecture is token-efficient by design: CV parse results cached in DB, match scores cached per user×job, applicant scores stored at apply-time (no recomputation), with model tiering planned (efficient model for high-volume scoring, larger model for generation).

The MVP is live in demo mode at https://ailoker.com and the Claude integration is verified end-to-end (parse CV, match score, fraud detection, JD writer all tested against real Claude responses via our gateway during development).

## Why Claude specifically?
Explainable matching is our core differentiator — it needs strong reasoning plus fluent Bahasa Indonesia generation, which is exactly where Claude leads for our use case. We also plan to use prompt caching for high-volume scoring to keep unit economics viable in an emerging market.

## Company facts
- Founded: October 2026, Indonesia [isi: bentuk badan usaha, bila ada]
- Team: solo founder (Ariev) [isi bila berubah]
- Funding: bootstrapped, $0 external funding
- Website: https://ailoker.com · Contact: halo@ailoker.com [pastikan email aktif]
- What we're applying for: Claude for Startups membership — Startup Stack partner offers, office hours, events (we understand the $1,000 API credit and free Team year are currently paused since Oct 9, 2026; we're applying for the remaining benefits and queue position).
