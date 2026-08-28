/* =========================================================================
   لایه‌ی ذخیره‌سازی محلی (Offline-First)
   ---------------------------------------------------------------------
   این فایل مسئول دو چیزه:

   ۱) «کش کامل دیتا» (dbCache): بعد از هر سینک موفق با سرور یا هر تغییر
      محلی، کل DB (پروفایل/برنامه‌ها/سوالات/آزمون‌ها/آلارم‌ها) توی IndexedDB
      ذخیره می‌شه. دفعه‌ی بعد که کاربر (حتی کاملاً آفلاین) اپ رو باز می‌کنه،
      همین کش بارگذاری می‌شه و اپ بدون نیاز به اینترنت بالا میاد.

   ۲) «صف کارهای نشده» (outbox): هر عملیات نوشتن (ساخت/ویرایش/حذف) که به
      خاطر آفلاین‌بودن نتونسته به سرور برسه، اینجا صف می‌شه. با متصل شدن به
      اینترنت، این صف به ترتیب زمانی روی سرور اعمال می‌شه. این صف کاملاً از
      طریق IndexedDB نگه داشته می‌شه (نه فقط حافظه‌ی موقت) تا:
        - بستن تب/مرورگر یا کشتن اپ چیزی رو گم نکنه
        - پاک شدن کش سرویس‌ورکر (sw.js توی cache API) روی این صف اثری
          نذاره، چون outbox توی storage جدا (IndexedDB) نگه داشته می‌شه؛
          پاک‌کردن Cache Storage هیچ‌وقت IndexedDB رو پاک نمی‌کنه.

   نکته‌ی مهم امنیتی/تجربه‌ی کاربری: خودِ IndexedDB هم به‌ندرت ممکنه توسط
   مرورگر (مثلاً حافظه کم / حالت ناشناس / "Clear browsing data") پاک بشه؛
   طبق درخواست، هر جا از اپ که کاربر می‌تونه صریحاً «داده‌هام رو پاک کن»
   بزنه (مثل logout یا «پاک‌کردن همه‌داده‌ها» توی پروفایل)، outbox رو *قبل*
   از هر پاک‌سازی، خالی/سینک می‌کنیم (یا از پاک‌کردنش در صورت وجود صف
   pending جلوگیری می‌کنیم) — به این ترتیب کاربر هیچ‌وقت به‌طور تصادفی
   تغییرات سینک‌نشده‌شو از دست نمی‌ده.
   ========================================================================= */

const Store = (() => {
  const DB_NAME = 'apex_offline_db';
  const DB_VERSION = 1;
  const STORE_CACHE = 'db_cache';   // key: userId -> { db, savedAt }
  const STORE_OUTBOX = 'outbox';    // key: autoIncrement -> operation

  let _dbPromise = null;

  function openDb() {
    if (_dbPromise) return _dbPromise;
    _dbPromise = new Promise((resolve, reject) => {
      if (!window.indexedDB) { reject(new Error('IndexedDB در دسترس نیست')); return; }
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE_CACHE)) {
          db.createObjectStore(STORE_CACHE, { keyPath: 'userId' });
        }
        if (!db.objectStoreNames.contains(STORE_OUTBOX)) {
          const os = db.createObjectStore(STORE_OUTBOX, { keyPath: 'opId', autoIncrement: true });
          os.createIndex('by_userId', 'userId', { unique: false });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error('باز کردن IndexedDB شکست خورد'));
    });
    return _dbPromise;
  }

  async function tx(storeName, mode) {
    const db = await openDb();
    return db.transaction(storeName, mode).objectStore(storeName);
  }

  // ---------------------------------------------------------------------
  // کش کامل DB
  // ---------------------------------------------------------------------
  async function saveDbCache(userId, dbObj) {
    if (!userId) return;
    try {
      const store = await tx(STORE_CACHE, 'readwrite');
      await new Promise((res, rej) => {
        const r = store.put({ userId, db: dbObj, savedAt: Date.now() });
        r.onsuccess = res; r.onerror = () => rej(r.error);
      });
    } catch (e) {
      // ذخیره‌ی کش نباید هیچ‌وقت جریان اصلی اپ رو خراب کنه
      console.warn('[Store] ذخیره‌ی کش محلی ناموفق بود:', e);
    }
  }

  async function loadDbCache(userId) {
    if (!userId) return null;
    try {
      const store = await tx(STORE_CACHE, 'readonly');
      return await new Promise((res, rej) => {
        const r = store.get(userId);
        r.onsuccess = () => res(r.result ? r.result.db : null);
        r.onerror = () => rej(r.error);
      });
    } catch (e) {
      console.warn('[Store] خواندن کش محلی ناموفق بود:', e);
      return null;
    }
  }

  async function clearDbCache(userId) {
    if (!userId) return;
    try {
      const store = await tx(STORE_CACHE, 'readwrite');
      await new Promise((res, rej) => {
        const r = store.delete(userId);
        r.onsuccess = res; r.onerror = () => rej(r.error);
      });
    } catch (e) { /* بی‌اهمیت */ }
  }

  // ---------------------------------------------------------------------
  // صف عملیات آفلاین (outbox)
  // هر آیتم: { opId, userId, kind, entity, tempId, payload, createdAt }
  //   kind: 'create' | 'update' | 'delete'
  //   entity: 'planItem' | 'question' | 'exam' | 'alarm' | 'profile'
  // ---------------------------------------------------------------------
  async function enqueueOp(userId, op) {
    const store = await tx(STORE_OUTBOX, 'readwrite');
    return new Promise((res, rej) => {
      const r = store.add({ ...op, userId, createdAt: Date.now() });
      r.onsuccess = () => res(r.result); // opId
      r.onerror = () => rej(r.error);
    });
  }

  async function listOps(userId) {
    const store = await tx(STORE_OUTBOX, 'readonly');
    return new Promise((res, rej) => {
      const idx = store.index('by_userId');
      const r = idx.getAll(userId);
      r.onsuccess = () => res((r.result || []).sort((a, b) => a.opId - b.opId));
      r.onerror = () => rej(r.error);
    });
  }

  async function removeOp(opId) {
    const store = await tx(STORE_OUTBOX, 'readwrite');
    return new Promise((res, rej) => {
      const r = store.delete(opId);
      r.onsuccess = res; r.onerror = () => rej(r.error);
    });
  }

  async function updateOp(opId, patch) {
    const store = await tx(STORE_OUTBOX, 'readwrite');
    return new Promise((res, rej) => {
      const getR = store.get(opId);
      getR.onsuccess = () => {
        const existing = getR.result;
        if (!existing) { res(null); return; }
        const merged = { ...existing, ...patch };
        const putR = store.put(merged);
        putR.onsuccess = () => res(merged);
        putR.onerror = () => rej(putR.error);
      };
      getR.onerror = () => rej(getR.error);
    });
  }

  async function countPending(userId) {
    const ops = await listOps(userId);
    return ops.length;
  }

  async function clearOutbox(userId) {
    const ops = await listOps(userId);
    const store = await tx(STORE_OUTBOX, 'readwrite');
    await Promise.all(ops.map(op => new Promise((res, rej) => {
      const r = store.delete(op.opId);
      r.onsuccess = res; r.onerror = () => rej(r.error);
    })));
  }

  return {
    saveDbCache, loadDbCache, clearDbCache,
    enqueueOp, listOps, removeOp, updateOp, countPending, clearOutbox,
  };
})();

if (typeof window !== 'undefined') window.Store = Store;
