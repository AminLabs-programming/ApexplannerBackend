const CACHE_NAME = 'apex-planner-v3';
const ASSETS = [
  './index.html',
  './config.js',
  './store.js',
  './api.js',
  './app.js',
  './auth.js',
  './sheet.js',
  './screens_home.js',
  './screens_plan.js',
  './screens_timer.js',
  './screens_questions.js',
  './screens_stats.js',
  './screens_profile.js',
  './screens_admin.js',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  './icon-maskable-192.png',
  './icon-maskable-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  // فقط فایل‌های خودِ اپ (همین دامنه) هندل می‌شن. درخواست‌های API به بکند
  // (دامنه‌ی دیگه، مثل Railway) همیشه مستقیم از شبکه می‌رن.
  if (!event.request.url.startsWith(self.location.origin)) {
    return; // بدون respondWith یعنی مرورگر خودش عادی fetch می‌کنه
  }

  // ⚠️ استراتژی «اول شبکه، بعد کش» (Network-First) — قبلاً اینجا «اول
  // کش» بود که باعث می‌شد بعد از هر تغییر توی config.js یا هر فایل دیگه
  // (حتی بعد از دیپلوی جدید روی Railway)، کاربرهایی که قبلاً اپ رو باز
  // کرده بودن همچنان نسخه‌ی قدیمیِ کش‌شده رو می‌دیدن — چون خودِ sw.js
  // عوض نشده بود، مرورگر هیچ‌وقت install جدید رو اجرا نمی‌کرد تا کش رو
  // تازه کنه. با Network-First همیشه اول شبکه امتحان می‌شه (پس تغییرات
  // فوری دیده می‌شن) و کش فقط برای حالت آفلاین/قطعی شبکه است.
  event.respondWith(
    fetch(event.request)
      .then((networkResp) => {
        if (networkResp && networkResp.status === 200) {
          const clone = networkResp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return networkResp;
      })
      .catch(() => caches.match(event.request))
  );
});
