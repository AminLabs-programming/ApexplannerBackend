# اپکس پلنر — بکند مشترک (Backend API)

این سرویس FastAPI + PostgreSQL دیتابیس مشترکی می‌سازه که هم بات تلگرام و
هم اپ (PWA) بهش وصل می‌شن. با آن، اعضای گروهت یک حساب واحد دارن که چه از
اپ چه از بات کار کنن، دیتاشون یکیه.

## چی داخل این پوشه‌ست
```
backend/
├── app/
│   ├── main.py          → همه‌ی route های API
│   ├── models.py        → جدول‌های دیتابیس (SQLAlchemy)
│   ├── schemas.py        → اعتبارسنجی ورودی/خروجی (Pydantic)
│   ├── database.py        → اتصال به Postgres/SQLite
│   └── auth.py              → هش رمز عبور + JWT
├── remote_db.py               → فایلی که باید کنار bot.py بذاری
├── requirements.txt
├── Procfile                     → دستور اجرا برای Railway
├── .env.example                  → لیست متغیرهای محیطی لازم
├── test_backend.py                → تست کامل API (۴۰ تست)
├── test_remote_db_integration.py    → تست یکپارچگی بات↔بکند
└── README-اتصال-بات.md               → راهنمای دقیق تغییرات bot.py
```

## دیپلوی روی Railway

1. یک سرویس جدید توی همون پروژه‌ی Railway که بات توشه بساز (New → Deploy
   from GitHub repo, یا Empty Service + آپلود دستی).
2. محتوای این پوشه (`backend/`) رو به یک ریپوی گیت‌هاب جدید پوش کن، یا
   مستقیم به Railway وصلش کن.
3. یک پلاگین **PostgreSQL** به همین سرویس اضافه کن (Railway خودش
   `DATABASE_URL` رو ست می‌کنه، نیازی به کار دستی نیست).
4. توی تنظیمات سرویس (Variables)، این دو مقدار رو اضافه کن:
   - `JWT_SECRET` → یک رشته‌ی تصادفی طولانی (با
     `python -c "import secrets; print(secrets.token_hex(32))"` بساز)
   - `BOT_API_KEY` → یک رشته‌ی تصادفی دیگر (این دقیقاً باید توی سرویس بات
     هم با همین اسم ست بشه)
5. Start Command (اگه از Procfile خودش نخوند):
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
6. بعد از دیپلوی، آدرس عمومی سرویس رو (چیزی شبیه
   `https://apex-backend-production.up.railway.app`) از تب Settings →
   Networking بردار.

## تست قبل از دیپلوی (اختیاری ولی توصیه‌شده)

```bash
cd backend
pip install -r requirements.txt
pip install httpx  # فقط برای تست
python3 test_backend.py
```

باید در آخر `✅ ALL TESTS PASSED` ببینی.

## اتصال اپ (PWA)

بعد از گرفتن آدرس سرویس بکند، باید توی فایل‌های اپ (`app.js` و بقیه)
آدرس `window.storage` رو با فراخوانی‌های `fetch` به این API عوض کنیم — این
کار در مرحله‌ی بعدی پروژه انجام می‌شه (هنوز انجام‌نشده).

## اتصال بات

فایل `README-اتصال-بات.md` رو کامل بخون — دقیقاً کدوم خط‌های `bot.py` باید
عوض بشن.

## نکته‌ی امنیتی

- `JWT_SECRET` و `BOT_API_KEY` رو هیچ‌وقت توی گیت‌هاب پابلیک کامیت نکن —
  فقط توی Variables خودِ Railway ست کن.
- الان CORS باز گذاشته شده (`allow_origins=["*"]`) تا اپت از GitHub Pages
  بتونه بهش وصل بشه. اگه بعداً خواستی محدودترش کنی، توی `app/main.py`
  دنبال `CORSMiddleware` بگرد.
