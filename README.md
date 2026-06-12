# Internet Mobile Bot Platform

FastAPI backend, Telegram bot va Vite React frontenddan iborat ariza va chat platformasi.

## Tarkib

- `backend/` - API, database models, chat/application services.
- `bot/` - Telegram bot handlers, keyboards, states va middleware.
- `frontend/` - React frontend.
- `assets/` - tarif va scenario ma'lumotlari.
- `scripts/` - Excel import va database setup yordamchi scriptlari.
- `run.py` - backend, bot va background tasklarni bitta jarayonda ishga tushiradi.

## Talablar a

- Python 3.11+
- Node.js 18+
- PostgreSQL database
- Telegram bot tokeni va group/topic sozlamalari

## Sozlash

1. `.env.example` asosida `.env` faylini yarating.
2. `.env` ichida kamida `BOT_TOKEN` va `CHAT_GROUP_ID` qiymatlarini kiriting.
3. `DATABASE_URL` yoki `POSTGRES_*` qiymatlari orqali PostgreSQL ulanishini sozlang.
4. Kerak bo'lsa forum topic IDlari, role parollari va simulation sozlamalarini to'ldiring.

Loyiha PostgreSQL talab qiladi. `DATABASE_URL` qiymatini `postgresql+asyncpg://user:password@host:5432/database_name` formatida bering yoki `.env` ichida `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` qiymatlarini to'ldiring.

## Backend va bot

Python dependencylarini o'rnating:

```bash
pip install -r requirements.txt
```

Barcha asosiy servislarni ishga tushirish:

```bash
python run.py
```

Backend alohida ishga tushirilsa:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8100
```

## Frontend

Frontend papkasida dependencylarni o'rnating:

```bash
npm install
```

Development server:

```bash
npm run dev
```

Production build:

```bash
npm run build
```

Vite dev server `/api`, `/uploads` va `/ws` requestlarini `http://localhost:8100` backendiga proxy qiladi.

## Muhim xavfsizlik eslatmalari

- Haqiqiy `.env` faylini public repositoryga yuklamang.
- `logs/`, `storage/`, `backend/uploads/`, `frontend/node_modules/` va `frontend/dist/` generated yoki lokal fayllar hisoblanadi.
- `assets/excel/` ichidagi real Excel fayllar va parollar maxfiy bo'lishi mumkin, shuning uchun ular ignore qilingan.
- `.env.example` faqat placeholder qiymatlar bilan turishi kerak.
