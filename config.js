/* =========================================================================
   تنظیمات اتصال به بکند
   ⚠️ این آدرس باید دامنه‌ی سرویس FastAPI (بکند) باشه، نه دامنه‌ی همین سرویس
   فرانت‌اند. توی Railway هر سرویس (فرانت و بکند) دامنه‌ی عمومی جدا و
   مستقل خودش رو داره؛ اینجا نباید دامنه‌ی فرانت‌اند تکرار بشه.

   چطور آدرس درست رو پیدا کنم؟
   1) توی Railway وارد همون پروژه بشو (که هم سرویس فرانت هم بکند توشه).
   2) روی سرویس بکند (همونی که app/main.py و uvicorn توشه) کلیک کن —
      نه روی سرویس فرانت‌اند.
   3) برو تب Settings → Networking → اگه دامنه‌ای زیر Public Networking
      نیست، دکمه‌ی "Generate Domain" رو بزن.
   4) همون آدرس (چیزی شبیه xxxx-production.up.railway.app) رو دقیقاً
      اینجا جای مقدار زیر بذار.
   ========================================================================= */
const APEX_CONFIG = {
  BACKEND_URL: "https://apexplannerbackend-production.up.railway.app",
};
if (typeof window !== 'undefined') {
  window.APEX_CONFIG = APEX_CONFIG;
  // چک ایمنی: اگه یه روز دوباره BACKEND_URL رو اشتباهی روی دامنه‌ی خودِ
  // همین فرانت‌اند ست کردی، به‌جای یه 404 گنگ از فایل‌سرور Railway، همینجا
  // تو کنسول با یه پیام واضح فارسی بهت میگه دقیقاً مشکل چیه.
  try {
    const backendOrigin = new URL(APEX_CONFIG.BACKEND_URL).origin;
    if (backendOrigin === window.location.origin) {
      console.error(
        '[اپکس پلنر] BACKEND_URL روی همون دامنه‌ی فرانت‌اند تنظیم شده! ' +
        'این یعنی آدرس سرویس بکند (FastAPI) رو با آدرس همین فرانت‌اند اشتباه گرفتی. ' +
        'برو تو Railway، سرویس بکند رو باز کن → Settings → Networking → دامنه‌ی جداگانه‌شو کپی کن و اینجا بذار.'
      );
    }
  } catch (e) {
    console.error('[اپکس پلنر] مقدار BACKEND_URL توی config.js معتبر نیست: ' + APEX_CONFIG.BACKEND_URL);
  }
}
