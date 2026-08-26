# راهنمای اتصال ناتیون و سیستم Restore Point

## خلاصه تغییرات
این نسخه قابلیت‌های زیر را به بکند اضافه کرده است:

1. **اتصال به Notion**: امکان همگام‌سازی برنامه‌ها از دیتابیس ناتیون به اپلیکیشن
2. **سیستم Restore Point**: ایجاد نقاط بازیابی برای جلوگیری از خرابی داده‌ها
3. **مدیریت داده‌ها**: امکان بازیابی داده‌ها از restore pointها

---

## متغیرهای محیطی مورد نیاز

برای استفاده از قابلیت اتصال به ناتیون، باید متغیرهای زیر را در Railway تنظیم کنید:

```
NOTION_API_KEY=your_notion_api_key_here
NOTION_DATABASE_ID=your_database_id_here
```

### دریافت NOTION_API_KEY:
1. به https://www.notion.so/my-integrations بروید
2. روی "+ New integration" کلیک کنید
3. نام integration را وارد کنید (مثلاً: Apex Planner Bot)
4. Workspace مورد نظر را انتخاب کنید
5. پس از ساخت، کلید API را کپی کنید

### دریافت NOTION_DATABASE_ID:
1. به صفحه دیتابیس ناتیون که بات به آن متصل است بروید
2. روی سه نقطه (...) بالای سمت راست کلیک کنید
3. گزینه "Copy link" را بزنید
4. لینک کپی شده به این شکل است: `https://www.notion.so/your-workspace/DATABASE_ID?v=...`
5. بخش `DATABASE_ID` (بین اسلش‌ها) را کپی کنید

### اتصال Integration به دیتابیس:
1. در صفحه integration ساخته شده، روی "Configure" کلیک کنید
2. در بخش "Capabilities"، گزینه "Read content" و "Insert content" را فعال کنید
3. در بخش "Content capabilities"، دیتابیس مورد نظر را انتخاب و اجازه دسترسی بدهید

---

## API Endpoints جدید

### ۱. راهنمای اتصال به ناتیون
```
GET /admin/notion/guide
Headers: Authorization: Bearer <admin_token>
```
برمی‌گرداند: لینک ساخت integration، راهنمای دریافت Database ID، و متغیرهای محیطی مورد نیاز

---

### ۲. همگام‌سازی از ناتیون
```
POST /admin/notion/sync
Headers: Authorization: Bearer <admin_token>
Content-Type: application/json
Body (اختیاری): {"date": "2025-01-15"}
```
برنامه‌ها را از ناتیون خوانده و به دیتابیس PostgreSQL اضافه می‌کند.
قبل از همگام‌سازی، یک restore point خودکار ایجاد می‌شود.

پارامتر اختیاری `date`: اگر مشخص شود، فقط برنامه‌های آن تاریخ همگام می‌شوند.

---

### ۳. لیست restore pointها
```
GET /admin/restore-points?limit=50
Headers: Authorization: Bearer <admin_token>
```
لیست restore pointهای کاربر را برمی‌گرداند.

---

### ۴. جزئیات یک restore point
```
GET /admin/restore-points/{rp_id}
Headers: Authorization: Bearer <admin_token>
```
جزئیات کامل یک restore point شامل داده‌های قبل و بعد از عملیات را برمی‌گرداند.

---

### ۵. ایجاد دستی restore point
```
POST /admin/restore-points
Headers: Authorization: Bearer <admin_token>
Content-Type: application/json
Body: {
    "operation_type": "manual_backup",
    "description": "پشتیبان قبل از حذف گروهی",
    "data_before": {...},
    "data_after": {...}
}
```
یک restore point دستی ایجاد می‌کند.

---

### ۶. اعمال restore point (بازیابی داده‌ها)
```
POST /admin/restore-points/{rp_id}/apply
Headers: Authorization: Bearer <admin_token>
```
داده‌ها را از restore point بازیابی می‌کند.

**توجه**: قبل از بازیابی، یک restore point از وضعیت فعلی ایجاد می‌شود تا بتوانید در صورت نیاز به عقب برگردید.

---

## ساختار دیتابیس ناتیون پیشنهادی

برای بهترین نتیجه، دیتابیس ناتیون شما باید ستون‌های زیر را داشته باشد:

| Property Name | Type | توضیحات |
|--------------|------|---------|
| Name (یا Task) | Title | نام فعالیت |
| Date | Date | تاریخ فعالیت (فرمت YYYY-MM-DD) |
| Category (یا Type) | Select | دسته‌بندی (مثلاً: درسی، ورزش، سایر) |
| Status | Select | وضعیت (Not started, In progress, Completed) |
| Study Minutes (یا Minutes) | Number | زمان مطالعه به دقیقه |
| Test Count (یا Tests) | Number | تعداد تست‌ها |
| Notes (یا Description) | Text | یادداشت‌ها |

---

## سناریوهای استفاده

### سناریو ۱: همگام‌سازی روزانه از ناتیون
1. برنامه روزانه خود را در ناتیون وارد کنید
2. از طریق اپ یا مستقیماً API، endpoint `/admin/notion/sync` را صدا بزنید
3. برنامه‌ها به صورت خودکار به دیتابیس اضافه می‌شوند
4. یک restore point خودکار ایجاد می‌شود

### سناریو ۲: بازیابی بعد از خطا
1. اگر داده‌ها به اشتباه حذف یا تغییر کردند، به لیست restore pointها بروید
2. restore point مورد نظر را انتخاب کنید
3. endpoint `/admin/restore-points/{rp_id}/apply` را صدا بزنید
4. داده‌ها به وضعیت قبلی برمی‌گردند

### سناریو ۳: پشتیبان‌گیری قبل از عملیات حساس
1. قبل از انجام هر عملیات حساس (مثل حذف گروهی)، یک restore point دستی ایجاد کنید
2. از endpoint `/admin/restore-points` با payload مناسب استفاده کنید
3. در صورت بروز مشکل، می‌توانید به این نقطه بازگردید

---

## نکات امنیتی

- تمام endpointهای مربوط به ناتیون و restore point فقط برای کاربران **ادمین** قابل دسترسی هستند
- قبل از هر عملیات بازیابی، یک backup خودکار از وضعیت فعلی گرفته می‌شود
- داده‌های restore pointها تا ۵۰ آیتم اول را ذخیره می‌کنند تا از حجم زیاد جلوگیری شود
- کلید API ناتیون را هرگز در کد یا ریپو ذخیره نکنید — فقط از متغیرهای محیطی Railway استفاده کنید

---

## عیب‌یابی

### خطا: "تنظیمات ناتیون پیکربندی نشده است"
- مطمئن شوید `NOTION_API_KEY` و `NOTION_DATABASE_ID` در Railway تنظیم شده‌اند
- سرویس بکند را ری‌استارت کنید

### خطا: "خطا در ارتباط با ناتیون"
- بررسی کنید integration به دیتابیس دسترسی دارد
- مطمئن شوید دیتابیس ID صحیح است
- بررسی کنید ناتیون از IP Railway بلاک نشده باشد

### خطا: "Restore point یافت نشد"
- مطمئن شوید rp_id صحیح است
- بررسی کنید restore point متعلق به کاربر لاگین‌شده باشد

---

## سوالات متداول

**آیا می‌توانم از چند دیتابیس ناتیون استفاده کنم؟**
در حال حاضر فقط یک دیتابیس پشتیبانی می‌شود. برای تغییر دیتابیس، `NOTION_DATABASE_ID` را تغییر دهید.

**آیا restore pointها تاریخ انقضا دارند؟**
خیر، اما توصیه می‌شود restore pointهای قدیمی را به صورت دستی پاک کنید تا دیتابیس شلوغ نشود.

**آیا می‌توانم بات تلگرام را نیز به این سیستم وصل کنم؟**
بله، بات می‌تواند از endpointهای `/bot/*` استفاده کند، اما قابلیت‌های ناتیون فقط از طریق ادمین در دسترس هستند.
