/* =========================================================================
   اپکس پلنر — منطق برنامه
   منطق برنامه‌ریزی/چک‌لیست/گزارش کار درسی/آمار هفتگی مستقیماً بر اساس
   همون قوانینی نوشته شده که تو بات تلگرامی Apex Planner (Python) بود:
   - دسته‌ها: درسی / توسعه فردی / غیردرسی
   - هر پارت «درسی» وقتی تیک می‌خوره، دقیقه مطالعه + تعداد تست ثبت می‌شه
   - هفته‌ی شمسی از شنبه تا جمعه؛ بازه‌ی «آمار هفتگی» از پنجشنبه تا پنجشنبه بعد
   - پارت‌های انجام‌نشده‌ی آخر شب به‌صورت خودکار «(جبرانی)» برای فردا کپی می‌شن
   ========================================================================= */

// ---------------------------------------------------------------------------
// Jalali <-> Gregorian (self-contained, no deps)
// ---------------------------------------------------------------------------
const Jalali = (() => {
  // Public-domain algorithm (jalaali-js / Borkowski), astronomically accurate
  // 1000+ years out, verified below against the Python `jdatetime` library.
  function div(a, b) { return ~~(a / b); }
  function mod(a, b) { return a - ~~(a / b) * b; }

  const breaks = [-61,9,38,199,426,686,756,818,1111,1181,1210,1635,2060,2097,2192,2262,2324,2394,2456,3178];

  function jalCalLeap(jy) {
    const bl = breaks.length;
    let gy = jy + 621, leapJ = -14, jp = breaks[0], jm, jump = 0, n, leap;
    if (jy < jp || jy >= breaks[bl - 1]) throw new Error('year out of range: ' + jy);
    for (let i = 1; i < bl; i += 1) {
      jm = breaks[i];
      jump = jm - jp;
      if (jy < jm) break;
      leapJ = leapJ + div(jump, 33) * 8 + div(mod(jump, 33), 4);
      jp = jm;
    }
    n = jy - jp;
    leapJ = leapJ + div(n, 33) * 8 + div(mod(n, 33) + 3, 4);
    if (mod(jump, 33) === 4 && jump - n === 4) leapJ += 1;
    const leapG = div(gy, 4) - div((div(gy, 100) + 1) * 3, 4) - 150;
    const march = 20 + leapJ - leapG;
    if (jump - n < 6) n = n - jump + div(jump + 4, 33) * 33;
    leap = mod(mod(n + 1, 33) - 1, 4);
    if (leap === -1) leap = 4;
    return { leap, gy, march };
  }

  function isLeapGregorian(gy) { return (gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0; }

  function g2d(gy, gm, gd) {
    let d = div((gy + div(gm - 8, 6) + 100100) * 1461, 4)
      + div(153 * mod(gm + 9, 12) + 2, 5)
      + gd - 34840408;
    d = d - div(div(gy + 100100 + div(gm - 8, 6), 100) * 3, 4) + 752;
    return d;
  }
  function d2g(jdn) {
    let j = 4 * jdn + 139361631;
    j = j + div(div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908;
    const i = div(mod(j, 1461), 4) * 5 + 308;
    const gd = div(mod(i, 153), 5) + 1;
    const gm = mod(div(i, 153), 12) + 1;
    const gy = div(j, 1461) - 100100 + div(8 - gm, 6);
    return [gy, gm, gd];
  }
  function j2d(jy, jm, jd) {
    const r = jalCalLeap(jy);
    return g2d(r.gy, 3, r.march) + (jm - 1) * 31 - div(jm, 7) * (jm - 7) + jd - 1;
  }
  function d2j(jdn) {
    const gy = d2g(jdn)[0];
    let jy = gy - 621;
    let r = jalCalLeap(jy);
    let jdn1f = g2d(r.gy, 3, r.march);
    let k = jdn - jdn1f;
    if (k >= 0) {
      if (k <= 185) {
        return [jy, 1 + div(k, 31), mod(k, 31) + 1];
      }
      k -= 186;
    } else {
      jy -= 1;
      k += 179;
      r = jalCalLeap(jy);
      if (r.leap === 1) k += 1;
    }
    return [jy, 7 + div(k, 30), mod(k, 30) + 1];
  }

  function toJalali(gy, gm, gd) { return d2j(g2d(gy, gm, gd)); }
  function toGregorian(jy, jm, jd) { return d2g(j2d(jy, jm, jd)); }

  const faDigits = '۰۱۲۳۴۵۶۷۸۹';
  function toFaNum(str) {
    return String(str).replace(/[0-9]/g, d => faDigits[d]);
  }
  function toEnNum(str) {
    return String(str).replace(/[۰-۹]/g, d => faDigits.indexOf(d));
  }

  const MONTHS = ['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'];
  const WEEKDAYS = ['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه','پنجشنبه','جمعه'];

  // weekday: 0=Saturday ... 6=Friday, based on gregorian date
  function weekdayOf(gy, gm, gd) {
    const jsDate = new Date(Date.UTC(gy, gm - 1, gd));
    const jsDow = jsDate.getUTCDay(); // 0=Sun..6=Sat
    return (jsDow + 1) % 7; // 0=Sat
  }

  function dateToStr(gy, gm, gd) {
    const p = n => String(n).padStart(2, '0');
    return `${gy}-${p(gm)}-${p(gd)}`;
  }
  function strToDate(str) {
    const [y, m, d] = str.split('-').map(Number);
    return { y, m, d };
  }
  function gregorianStrToJalaliStr(gStr) {
    const { y, m, d } = strToDate(gStr);
    const [jy, jm, jd] = toJalali(y, m, d);
    return `${toFaNum(jy)}/${toFaNum(String(jm).padStart(2,'0'))}/${toFaNum(String(jd).padStart(2,'0'))}`;
  }
  function gregorianStrToJalaliParts(gStr) {
    const { y, m, d } = strToDate(gStr);
    const [jy, jm, jd] = toJalali(y, m, d);
    return { jy, jm, jd };
  }
  function addDays(gStr, days) {
    const { y, m, d } = strToDate(gStr);
    const dt = new Date(Date.UTC(y, m - 1, d));
    dt.setUTCDate(dt.getUTCDate() + days);
    return dateToStr(dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate());
  }
  function todayStr() {
    const now = new Date();
    return dateToStr(now.getFullYear(), now.getMonth() + 1, now.getDate());
  }
  function todayJalaliStr() {
    return gregorianStrToJalaliStr(todayStr());
  }
  // week range: Saturday..Friday (jalali week) containing reference gStr
  function weekRange(gStr) {
    const wd = (() => { const {y,m,d}=strToDate(gStr); return weekdayOf(y,m,d); })();
    const start = addDays(gStr, -wd);
    const end = addDays(start, 6);
    return [start, end];
  }
  // "weekly stats" range per bot logic: Thursday to next Thursday (8 days inclusive)
  function weeklyStatsRange(gStr) {
    const THU = 5; // 0=Sat..6=Fri, Thursday=5
    const wd = (() => { const {y,m,d}=strToDate(gStr); return weekdayOf(y,m,d); })();
    const daysSinceThu = ((wd - THU) % 7 + 7) % 7;
    const start = addDays(gStr, -daysSinceThu);
    const end = addDays(start, 7);
    return [start, end];
  }
  function formatJalaliRange(startStr, endStr) {
    return `${gregorianStrToJalaliStr(startStr)} تا ${gregorianStrToJalaliStr(endStr)}`;
  }

  return {
    toJalali, toGregorian, toFaNum, toEnNum, MONTHS, WEEKDAYS, weekdayOf,
    dateToStr, strToDate, gregorianStrToJalaliStr, gregorianStrToJalaliParts,
    addDays, todayStr, todayJalaliStr, weekRange, weeklyStatsRange, formatJalaliRange
  };
})();

function formatMinutes(total) {
  total = Math.round(total || 0);
  const h = Math.floor(total / 60), m = total % 60;
  if (h && m) return `${Jalali.toFaNum(h)} ساعت و ${Jalali.toFaNum(m)} دقیقه`;
  if (h) return `${Jalali.toFaNum(h)} ساعت`;
  return `${Jalali.toFaNum(m)} دقیقه`;
}
function fa(n) { return Jalali.toFaNum(n); }

// ---------------------------------------------------------------------------
// Storage layer (persistent, per-account — از طریق API بکند، نه window.storage)
// ---------------------------------------------------------------------------
let DB = null; // کش محلی از دیتای کاربر لاگین‌شده؛ از بکند پر می‌شه و باهاش سینک می‌مونه
let IS_OFFLINE_BOOT = false; // true اگه اپ این بار بدون تماس موفق با سرور بالا اومده (کاملاً از کش)

function uid() { return 'x' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36); }
function currentUserId() { return (DB && DB.profile && DB.profile.userId) || Api.getCachedUser()?.id || null; }

// هر تغییر (create/update/delete روی هر موجودیتی) بلافاصله و به‌صورت
// await-پذیر توی IndexedDB نوشته می‌شه (نه دیبانس‌شده) — چون این عملیات
// دیسکریت و کم‌تعدادن (یه تیک، یه حذف، یه ثبت‌نمره)، نه تایپ پیوسته، پس
// هزینه‌ی نوشتن فوری ناچیزه، در حالی که یه نوشتن دیبانس‌شده ریسک واقعی
// گم‌شدن آخرین تغییر موقع بسته‌شدن ناگهانی تب/اپ رو داره. این تابع تنها
// نقطه‌ی نوشتن کش محلیه.
async function persistDbNow() {
  const uid_ = currentUserId();
  if (uid_ && DB) await Store.saveDbCache(uid_, DB);
}
// برای هماهنگی با هر جای احتمالی که فراموش بشه await بشه (مثل رویدادهای
// DOM سینک)، یه نسخه‌ی «فایر-اند-فراموش» هم نگه می‌داریم که همون کار رو
// می‌کنه ولی promise ـش رو برنمی‌گردونه.
function persistDbSoon() { persistDbNow(); }

function setupPersistFlushGuards() {
  // یه لایه‌ی دفاعی اضافه: اگه به‌هر دلیلی یه‌جا await نشده باشه و صفحه
  // داره بسته/مخفی می‌شه، یه تلاش آخر برای نوشتن می‌کنیم. چون DB از قبل
  // با persistDbNow به‌روز نگه داشته می‌شه، این معمولاً کاری نداره؛ فقط
  // یه شبکه‌ی ایمنیه.
  const flush = () => { const uid_ = currentUserId(); if (uid_ && DB) Store.saveDbCache(uid_, DB); };
  window.addEventListener('pagehide', flush);
  window.addEventListener('beforeunload', flush);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush();
  });
}

function defaultDB() {
  return {
    profile: { name: 'دانش‌آموز', goalHoursPerDay: 5, examTargetLabel: '', role: 'member', userId: null },
    planItems: [],      // {id,name,date,category,status,studyMinutes,testCount,timeLabel,notes}
    questions: [],       // {id,text,options:[{text,correct}],subject,topic,difficulty,createdAt}
    exams: [],            // {id,name,date,subjects:[{name,percent}]}
    alarms: [],           // {id,label,time:'HH:MM',days:[0..6],enabled}
    sessions: [],          // completed study sessions {id,date,subject,minutes,mode} — فقط محلی (تایمر)
  };
}

// ---- تبدیل شکل داده‌ی API (snake_case) به شکل داخلی اپ (camelCase) ----
function planItemFromApi(i) {
  return {
    id: i.id, name: i.name, date: i.date, category: i.category, status: i.status,
    studyMinutes: i.study_minutes, testCount: i.test_count, timeLabel: i.time_label || '', notes: i.notes || '',
  };
}
function planItemToApiCreate(i) {
  return { name: i.name, date: i.date, category: i.category, time_label: i.timeLabel || '' };
}
function planItemToApiUpdate(patch) {
  const out = {};
  if ('name' in patch) out.name = patch.name;
  if ('date' in patch) out.date = patch.date;
  if ('category' in patch) out.category = patch.category;
  if ('status' in patch) out.status = patch.status;
  if ('studyMinutes' in patch) out.study_minutes = patch.studyMinutes;
  if ('testCount' in patch) out.test_count = patch.testCount;
  if ('timeLabel' in patch) out.time_label = patch.timeLabel;
  if ('notes' in patch) out.notes = patch.notes;
  return out;
}
function questionFromApi(q) {
  return { id: q.id, text: q.text, options: q.options || [], subject: q.subject || '', topic: q.topic || '', difficulty: q.difficulty || 'mid', createdAt: q.created_at };
}
function examFromApi(e) {
  return { id: e.id, name: e.name, date: e.date, subjects: e.subjects || [] };
}
function alarmFromApi(a) {
  return { id: a.id, label: a.label, time: a.time, days: a.days || [], enabled: a.enabled };
}

// ---------------------------------------------------------------------------
// قفل ساده برای جلوگیری از رقابت هم‌زمان روی DB
// ---------------------------------------------------------------------------
// چون syncFromServer کل DB رو بازنویسی می‌کنه (DB = defaultDB(); ...)، اگه
// دقیقاً همون لحظه یک عملیات CRUD محلی (که از قبل شروع شده) بخواد روی
// شیء قدیمی DB بنویسه، اون تغییر گم می‌شه. برای جلوگیری از این مسابقه،
// هر عملیاتی که DB رو می‌خونه/می‌نویسه از withDbLock عبور می‌کنه تا
// تضمین بشه هیچ‌وقت دو تا از این عملیات هم‌زمان اجرا نمی‌شن.
let _dbLockChain = Promise.resolve();
function withDbLock(fn) {
  const run = _dbLockChain.then(fn, fn);
  // زنجیره رو ادامه بده حتی اگه fn رد بشه، وگرنه قفل برای همیشه گیر می‌کنه
  _dbLockChain = run.then(() => {}, () => {});
  return run;
}

// بارگذاری کامل دیتا از بکند بعد از لاگین موفق (فقط وقتی آنلاینیم صدا زده می‌شه)
async function syncFromServer() {
  return withDbLock(async () => {
    const [me, items, questions, exams, alarms] = await Promise.all([
      Api.me(),
      Api.listPlanItems(),
      Api.listQuestions(),
      Api.listExams(),
      Api.listAlarms(),
    ]);
    // sessions محلیه (فقط تایمر) و از سرور نمیاد؛ اگه از قبل کش داشتیم حفظش می‌کنیم
    const prevSessions = (DB && DB.sessions) ? DB.sessions : [];
    DB = defaultDB();
    DB.sessions = prevSessions;
    DB.profile = {
      name: me.display_name, goalHoursPerDay: me.goal_hours_per_day,
      examTargetLabel: me.exam_target_label || '', role: me.role, userId: me.id,
    };
    DB.planItems = items.map(planItemFromApi);
    DB.questions = questions.map(questionFromApi);
    DB.exams = exams.map(examFromApi);
    DB.alarms = alarms.map(alarmFromApi);
    Api.setCachedUser(me);
    IS_OFFLINE_BOOT = false;
    await persistDbNow();
    return DB;
  });
}

// بارگذاری DB از کش محلی (IndexedDB) — برای بوت آفلاین یا وقتی سرور جواب
// نمی‌ده اما قبلاً حداقل یک‌بار با موفقیت سینک شده بودیم.
async function loadFromLocalCache() {
  const cachedUser = Api.getCachedUser();
  if (!cachedUser || !cachedUser.id) return null;
  const cached = await Store.loadDbCache(cachedUser.id);
  if (!cached) return null;
  DB = cached;
  // اطمینان از وجود همه‌ی فیلدها حتی اگه نسخه‌ی قدیمی‌تر کش شده باشه
  const fresh = defaultDB();
  for (const k of Object.keys(fresh)) if (!(k in DB)) DB[k] = fresh[k];
  IS_OFFLINE_BOOT = true;
  return DB;
}

// ---------------------------------------------------------------------------
// Outbox — موتور عمومی برای صف‌کردن و پردازش عملیات نوشتنِ آفلاین
// ---------------------------------------------------------------------------
let _outboxProcessing = false;
let _outboxListenersReady = false;

// آیا خطا یعنی «نتونستیم به سرور برسیم» (باید صف بشه) یا خطای واقعی سرور
// (اعتبارسنجی/دسترسی/و...، باید به کاربر نشون داده بشه و rollback بشه)?
function isOfflineError(e) {
  return (e instanceof Api.ApiError) ? e.isNetworkError : !navigator.onLine;
}

// ثبت یک عملیات در outbox و برنامه‌ریزی برای تلاش بعدی.
// اگه خودِ IndexedDB هم در دسترس نباشه (خیلی نادر: مثلاً حالت ناشناسِ
// بعضی مرورگرها)، به‌جای اینکه تغییر کاربر کاملاً گم بشه، حداقل توی یک
// آرایه‌ی درون‌حافظه‌ای (که تا وقتی تب بازه زنده می‌مونه) نگه می‌داریم و
// با صدای بلند به کاربر هشدار می‌دیم که این دستگاه رو نبنده تا آنلاین بشه.
let _memoryFallbackOutbox = [];
async function queueOp(kind, entity, { tempId = null, realId = null, payload = null } = {}) {
  const uid_ = currentUserId();
  if (!uid_) return null;
  try {
    const opId = await Store.enqueueOp(uid_, { kind, entity, tempId, realId, payload });
    updateSyncBadge();
    return opId;
  } catch (e) {
    console.error('[Outbox] ذخیره‌ی محلی صف ممکن نشد، fallback به حافظه‌ی موقت:', e);
    _memoryFallbackOutbox.push({ userId: uid_, kind, entity, tempId, realId, payload });
    showToast('حافظه‌ی محلی مرورگر در دسترس نیست؛ تا وصل‌شدن اینترنت این تب رو نبند', 'warning');
    updateSyncBadge();
    return 'mem-' + _memoryFallbackOutbox.length;
  }
}

// resolve می‌کنه که آیا یک id هنوز «موقتیه» (منتظر شناسه‌ی واقعی سرور) یا نه.
// موقع پردازش صف، اگه یک create هنوز واقعی نشده و بعدش یک update/delete
// برای همون tempId اومده باشه، باید صبر کنه create اول پردازش بشه.
async function processOutbox() {
  if (_outboxProcessing) return;
  if (!navigator.onLine) return;
  const uid_ = currentUserId();
  if (!uid_) return;
  _outboxProcessing = true;
  let processedCount = 0;
  try {
    // نگاشت موقتی از tempId به realId برای همین دور پردازش
    const idMap = {};

    // اول هر چیزی که به‌خاطر خرابیِ IndexedDB توی fallback حافظه‌ای مونده
    // بود رو امتحان کن (اگه بتونیم دوباره بنویسیمش تو IndexedDB، بهتره؛
    // وگرنه مستقیم پردازشش می‌کنیم چون در حافظه‌ست و از دست نمی‌ره تا تب بازه).
    const memOps = _memoryFallbackOutbox.filter(o => o.userId === uid_);
    for (const op of memOps) {
      try {
        await applyOutboxOp(op, idMap);
        _memoryFallbackOutbox = _memoryFallbackOutbox.filter(o => o !== op);
        processedCount++;
      } catch (e) {
        if (isOfflineError(e)) break;
        _memoryFallbackOutbox = _memoryFallbackOutbox.filter(o => o !== op);
        showToast('یک تغییر آفلاین با سرور همخوانی نداشت و نادیده گرفته شد', 'error');
      }
    }

    let ops = await Store.listOps(uid_);
    for (const op of ops) {
      try {
        await applyOutboxOp(op, idMap);
        await Store.removeOp(op.opId);
        processedCount++;
      } catch (e) {
        if (isOfflineError(e)) {
          // دوباره آفلاین شدیم وسط پردازش؛ همین‌جا متوقف شو، بقیه صف می‌مونه
          break;
        } else {
          // خطای واقعی سرور (مثلاً آیتم قبلاً حذف شده، اعتبارسنجی و...)
          // برای جلوگیری از قفل‌شدن دائمیِ صف، این عملیات رو حذف می‌کنیم
          // و به کاربر اطلاع می‌دیم، ولی بقیه‌ی صف رو ادامه می‌دیم.
          console.warn('[Outbox] عملیات رد شد و از صف حذف شد:', op, e);
          await Store.removeOp(op.opId);
          processedCount++;
          showToast('یک تغییر آفلاین با سرور همخوانی نداشت و نادیده گرفته شد', 'error');
        }
      }
    }
  } finally {
    _outboxProcessing = false;
    updateSyncBadge();
  }
  // فقط اگه واقعاً چیزی پردازش شد یک سینک کامل بگیر تا هر چیزی که سرور
  // خودش تغییر داده (مثلاً از بات تلگرام یا Notion) هم بیاد تو. اگه صف
  // از اول خالی بود، نیازی به این سینکِ اضافه نیست — و مهم‌تر از اون،
  // فراخوانی بی‌دلیلش می‌تونه با یک عملیات محلیِ هم‌زمانِ کاربر رقابت کنه
  // و DB رو وسط یک تغییرِ در حال انجام بازنویسی کنه.
  if (processedCount > 0) {
    try {
      if (navigator.onLine) {
        await syncFromServer();
        rerenderIfMounted();
      }
    } catch (e) { /* بی‌اهمیت؛ دفعه‌ی بعد امتحان می‌شه */ }
  }
}

async function applyOutboxOp(op, idMap) {
  const resolveId = (id) => (id && idMap[id]) ? idMap[id] : id;

  if (op.entity === 'planItem') {
    if (op.kind === 'create') {
      const created = await Api.createPlanItem(op.payload);
      idMap[op.tempId] = created.id;
      remapLocalId('planItems', op.tempId, created.id, planItemFromApi(created));
    } else if (op.kind === 'update') {
      const realId = resolveId(op.realId);
      await Api.updatePlanItem(realId, op.payload);
    } else if (op.kind === 'delete') {
      const realId = resolveId(op.realId);
      await Api.deletePlanItem(realId);
    }
  } else if (op.entity === 'question') {
    if (op.kind === 'create') {
      const created = await Api.createQuestion(op.payload);
      idMap[op.tempId] = created.id;
      remapLocalId('questions', op.tempId, created.id, questionFromApi(created));
    } else if (op.kind === 'update') {
      await Api.updateQuestion(resolveId(op.realId), op.payload);
    } else if (op.kind === 'delete') {
      await Api.deleteQuestion(resolveId(op.realId));
    }
  } else if (op.entity === 'exam') {
    if (op.kind === 'create') {
      const created = await Api.createExam(op.payload);
      idMap[op.tempId] = created.id;
      remapLocalId('exams', op.tempId, created.id, examFromApi(created));
    } else if (op.kind === 'update') {
      await Api.updateExam(resolveId(op.realId), op.payload);
    } else if (op.kind === 'delete') {
      await Api.deleteExam(resolveId(op.realId));
    }
  } else if (op.entity === 'alarm') {
    if (op.kind === 'create') {
      const created = await Api.createAlarm(op.payload);
      idMap[op.tempId] = created.id;
      remapLocalId('alarms', op.tempId, created.id, alarmFromApi(created));
    } else if (op.kind === 'update') {
      await Api.updateAlarm(resolveId(op.realId), op.payload);
    } else if (op.kind === 'delete') {
      await Api.deleteAlarm(resolveId(op.realId));
    }
  } else if (op.entity === 'profile') {
    await Api.updateMe(op.payload);
  }
  await persistDbNow();
}

// وقتی یک آیتمی که قبلاً با tempId ساخته شده بود، حالا id واقعی از سرور
// گرفت، همه‌جا (لیست محلی) رو با شناسه‌ی واقعی جایگزین می‌کنیم تا هر
// عملیات بعدی (که هنوز روی صفحه با id قدیمی رفرنس داره) درست کار کنه.
function remapLocalId(listName, tempId, realId, freshRecord) {
  const list = DB[listName];
  const idx = list.findIndex(x => x.id === tempId);
  if (idx >= 0) {
    list[idx] = { ...list[idx], ...freshRecord, id: realId };
  }
  // هر عملیات دیگه‌ی هنوز در صف که به tempId اشاره می‌کنه (realId=tempId)
  // هم باید آپدیت بشه تا وقتی نوبتش می‌رسه با id درست بره.
  Store.listOps(currentUserId()).then(ops => {
    ops.forEach(op => {
      if (op.realId === tempId) Store.updateOp(op.opId, { realId });
    });
  }).catch(() => {});
}

function rerenderIfMounted() {
  if (typeof render === 'function' && document.getElementById('screens')) rerender();
}

// ---- کمک‌تابع‌ها برای وقتی که یک آیتم هنوز روی سرور "متولد" نشده ----
// (یعنی هنوز یک عملیات create برای همون tempId توی outbox صف‌شده). توی
// این حالت، update/delهایی که کاربر روی همین آیتم آفلاین می‌زنه نباید
// عملیات جدا صف بشن (چون سرور اصلاً این id رو نمی‌شناسه)؛ به‌جاش باید
// مستقیماً payload خودِ create رو اصلاح کنن یا کلاً لغوش کنن.
async function findPendingCreateOp(entity, tempId) {
  const uid_ = currentUserId();
  if (!uid_) return null;
  const ops = await Store.listOps(uid_);
  return ops.find(o => o.entity === entity && o.kind === 'create' && o.tempId === tempId) || null;
}
async function hasPendingCreate(entity, tempId) {
  return !!(await findPendingCreateOp(entity, tempId));
}
async function cancelPendingCreate(entity, tempId) {
  const op = await findPendingCreateOp(entity, tempId);
  if (op) { await Store.removeOp(op.opId); updateSyncBadge(); }
}
async function mergeIntoPendingCreate(entity, tempId, patchInApiShape) {
  const op = await findPendingCreateOp(entity, tempId);
  if (!op) return;
  await Store.updateOp(op.opId, { payload: { ...op.payload, ...patchInApiShape } });
}

// نشانگر کوچیک برای اینکه کاربر بدونه تغییراتی هست که هنوز سینک نشده
async function updateSyncBadge() {
  try {
    const uid_ = currentUserId();
    const memCount = uid_ ? _memoryFallbackOutbox.filter(o => o.userId === uid_).length : 0;
    const count = (uid_ ? await Store.countPending(uid_) : 0) + memCount;
    const badge = document.getElementById('syncBadge');
    if (badge) {
      badge.style.display = count > 0 ? 'flex' : 'none';
      badge.textContent = count > 9 ? '۹+' : fa(count);
    }
    window.__apexPendingSync = count;
    updateSyncStatusIcon(count);
  } catch (e) { /* بی‌اهمیت */ }
}

function updateSyncStatusIcon(pendingCount) {
  const icon = document.getElementById('syncStatusIcon');
  const wrap = document.getElementById('syncStatus');
  if (!icon || !wrap) return;
  if (!navigator.onLine) {
    icon.textContent = 'cloud_off';
    icon.style.color = 'var(--text-3)';
    wrap.title = pendingCount > 0 ? `آفلاین — ${fa(pendingCount)} تغییر منتظر ارسال` : 'آفلاین';
  } else if (pendingCount > 0) {
    icon.textContent = 'cloud_sync';
    icon.style.color = 'var(--primary-bright)';
    wrap.title = `${fa(pendingCount)} تغییر در حال ارسال`;
  } else {
    icon.textContent = 'cloud_done';
    icon.style.color = 'var(--text-3)';
    wrap.title = 'همه‌چیز سینک شده';
  }
}

function setupOutboxAutoSync() {
  if (_outboxListenersReady) return;
  _outboxListenersReady = true;
  setupPersistFlushGuards();
  window.addEventListener('online', () => { updateSyncBadge(); processOutbox(); });
  window.addEventListener('offline', () => { updateSyncBadge(); });
  // بعضی مرورگرها (خصوصاً موبایل) رویداد online رو همیشه دقیق شلیک
  // نمی‌کنن؛ برای اطمینان هر ۲۰ ثانیه هم (فقط وقتی navigator.onLine
  // true هست) یک تلاش سبک می‌زنیم.
  setInterval(() => { if (navigator.onLine) processOutbox(); }, 20000);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && navigator.onLine) processOutbox();
  });
  // اگه (به‌ندرت) IndexedDB در دسترس نبوده و تغییرات فقط توی حافظه‌ی
  // موقتِ همین تب مونده باشن، با بستن تب از دست می‌رن — پس صریحاً هشدار
  // می‌دیم. تغییراتی که با موفقیت توی IndexedDB ذخیره شدن نیاز به این
  // هشدار ندارن چون با باز کردن دوباره‌ی اپ هم می‌مونن.
  window.addEventListener('beforeunload', (e) => {
    const uid_ = currentUserId();
    const hasMemFallback = uid_ && _memoryFallbackOutbox.some(o => o.userId === uid_);
    if (hasMemFallback) {
      e.preventDefault();
      e.returnValue = '';
    }
  });
}

// ---------------------------------------------------------------------------
// Plan item helpers — بهینه‌گرا (optimistic): اول کش محلی آپدیت می‌شه که UI
// فوری واکنش نشون بده، بعد درخواست به سرور می‌ره؛ اگه سرور خطا داد، تغییر
// برمی‌گرده و پیام خطا نشون داده می‌شه.
// ---------------------------------------------------------------------------
const CATEGORIES = ['درسی', 'توسعه فردی', 'غیردرسی'];

async function addPlanItem({ name, date, category, timeLabel }) {
  const tempId = uid();
  const optimistic = { id: tempId, name, date, category: category || 'درسی', status: false, studyMinutes: 0, testCount: 0, timeLabel: timeLabel || '', notes: '' };
  await withDbLock(async () => { DB.planItems.push(optimistic); await persistDbNow(); });
  try {
    const created = await Api.createPlanItem(planItemToApiCreate(optimistic));
    const real = planItemFromApi(created);
    await withDbLock(async () => {
      const idx = DB.planItems.findIndex(i => i.id === tempId);
      if (idx >= 0) DB.planItems[idx] = real;
      await persistDbNow();
    });
    return real;
  } catch (e) {
    if (isOfflineError(e)) {
      // آفلاینیم: آیتم optimistic توی UI می‌مونه، ساخت واقعیش صف می‌شه
      await queueOp('create', 'planItem', { tempId, payload: planItemToApiCreate(optimistic) });
      return optimistic;
    }
    await withDbLock(async () => {
      DB.planItems = DB.planItems.filter(i => i.id !== tempId);
      await persistDbNow();
    });
    showToast('خطا در افزودن برنامه: ' + e.message, 'error');
    throw e;
  }
}
function getItemsForDate(dateStr) {
  return DB.planItems.filter(i => i.date === dateStr);
}
function getItemsBetween(start, end) {
  return DB.planItems.filter(i => i.date >= start && i.date <= end);
}
function getItemById(id) { return DB.planItems.find(i => i.id === id); }

async function deleteItem(id) {
  let backup;
  await withDbLock(async () => {
    backup = DB.planItems.find(i => i.id === id);
    DB.planItems = DB.planItems.filter(i => i.id !== id);
    await persistDbNow();
  });
  try {
    if (await hasPendingCreate('planItem', id)) {
      // آیتم هنوز حتی روی سرور ساخته نشده (create هنوز توی صفه)؛ کافیه
      // همون عملیات create رو از صف پاک کنیم، نیازی به delete نیست.
      await cancelPendingCreate('planItem', id);
      return;
    }
    await Api.deletePlanItem(id);
  } catch (e) {
    if (isOfflineError(e)) {
      await queueOp('delete', 'planItem', { realId: id });
      return;
    }
    if (backup) await withDbLock(async () => { DB.planItems.push(backup); await persistDbNow(); });
    showToast('خطا در حذف: ' + e.message, 'error');
    throw e;
  }
}
async function updatePlanItemRemote(id, patch) {
  if (!getItemById(id)) return;
  let backup;
  await withDbLock(async () => {
    const item = getItemById(id);
    if (!item) return;
    backup = { ...item };
    Object.assign(item, patch);
    await persistDbNow();
  });
  if (!backup) return; // آیتم بین این‌مدت (نادر) حذف شده بود
  try {
    if (await hasPendingCreate('planItem', id)) {
      // هنوز create صف شده؛ به‌جای update جدا، همون payload ساخت رو
      // به‌روز می‌کنیم تا وقتی سینک شد، نسخه‌ی نهایی درست بره.
      await mergeIntoPendingCreate('planItem', id, planItemToApiUpdate(patch));
      return;
    }
    const updated = await Api.updatePlanItem(id, planItemToApiUpdate(patch));
    await withDbLock(async () => {
      const item = getItemById(id);
      if (item) Object.assign(item, planItemFromApi(updated));
      await persistDbNow();
    });
  } catch (e) {
    if (isOfflineError(e)) {
      await queueOp('update', 'planItem', { realId: id, payload: planItemToApiUpdate(patch) });
      return;
    }
    await withDbLock(async () => {
      const item = getItemById(id);
      if (item) Object.assign(item, backup);
      await persistDbNow();
    });
    showToast('خطا در ذخیره: ' + e.message, 'error');
    throw e;
  }
}
async function markItemDone(id, done) {
  return updatePlanItemRemote(id, { status: done });
}
async function saveStudyData(id, minutes, tests, markDone = true) {
  return updatePlanItemRemote(id, { studyMinutes: minutes, testCount: tests, status: markDone ? true : getItemById(id)?.status });
}
async function createMakeupItem(original, dateStr) {
  const title = original.name.includes('(جبرانی)') ? original.name : `${original.name} (جبرانی)`;
  return addPlanItem({ name: title, date: dateStr, category: original.category });
}
// carry over unfinished items from a date to the next day, tagging as makeup — run lazily
async function runCarryOverIfNeeded() {
  const today = Jalali.todayStr();
  const lastRun = localStorage.getItem('apex_carry_last') || '';
  if (lastRun === today) return;
  const yesterday = Jalali.addDays(today, -1);
  const items = getItemsForDate(yesterday);
  let count = 0;
  for (const it of items) {
    if (!it.status) {
      const already = getItemsForDate(today).some(x => x.name === (it.name.includes('(جبرانی)') ? it.name : it.name + ' (جبرانی)'));
      if (!already) { await createMakeupItem(it, today); count++; }
    }
  }
  localStorage.setItem('apex_carry_last', today);
  if (count > 0) { setTimeout(() => showToast(`${fa(count)} پارت مونده دیروز، برای امروز منتقل شد`), 800); }
}

// ---------------------------------------------------------------------------
// موتور عمومی CRUD آفلاین‌-اول برای موجودیت‌های ساده (question/exam/alarm)
// که همه یک الگوی یکسان دارن: create/update/delete + آرایه‌ی محلی در DB.
// ---------------------------------------------------------------------------
function makeOfflineCrud({ entity, listName, fromApi, apiCreate, apiUpdate, apiDelete, addMode = 'push' }) {
  async function add(payload) {
    const tempId = uid();
    const optimistic = fromApi({ ...payload, id: tempId });
    await withDbLock(async () => {
      if (addMode === 'unshift') DB[listName].unshift(optimistic); else DB[listName].push(optimistic);
      await persistDbNow();
    });
    try {
      const created = await apiCreate(payload);
      const real = fromApi(created);
      await withDbLock(async () => {
        const idx = DB[listName].findIndex(x => x.id === tempId);
        if (idx >= 0) DB[listName][idx] = real;
        await persistDbNow();
      });
      return real;
    } catch (e) {
      if (isOfflineError(e)) {
        await queueOp('create', entity, { tempId, payload });
        return optimistic;
      }
      await withDbLock(async () => {
        DB[listName] = DB[listName].filter(x => x.id !== tempId);
        await persistDbNow();
      });
      showToast('خطا در ذخیره: ' + e.message, 'error');
      throw e;
    }
  }

  async function update(id, payload) {
    let backup = null, optimistic = null;
    await withDbLock(async () => {
      const idx = DB[listName].findIndex(x => x.id === id);
      if (idx < 0) return;
      backup = { ...DB[listName][idx] };
      optimistic = fromApi({ ...backup, ...payload, id });
      DB[listName][idx] = optimistic;
      await persistDbNow();
    });
    if (!backup) return; // آیتم پیدا نشد (مثلاً هم‌زمان حذف شده بود)
    try {
      if (await hasPendingCreate(entity, id)) {
        await mergeIntoPendingCreate(entity, id, payload);
        return optimistic;
      }
      const updated = await apiUpdate(id, payload);
      const real = fromApi(updated);
      await withDbLock(async () => {
        const idx = DB[listName].findIndex(x => x.id === id);
        if (idx >= 0) DB[listName][idx] = real;
        await persistDbNow();
      });
      return real;
    } catch (e) {
      if (isOfflineError(e)) {
        await queueOp('update', entity, { realId: id, payload });
        return optimistic;
      }
      await withDbLock(async () => {
        const idx = DB[listName].findIndex(x => x.id === id);
        if (idx >= 0) DB[listName][idx] = backup;
        await persistDbNow();
      });
      showToast('خطا در ذخیره: ' + e.message, 'error');
      throw e;
    }
  }

  async function del(id) {
    let backup = null;
    await withDbLock(async () => {
      backup = DB[listName].find(x => x.id === id) || null;
      DB[listName] = DB[listName].filter(x => x.id !== id);
      await persistDbNow();
    });
    try {
      if (await hasPendingCreate(entity, id)) {
        await cancelPendingCreate(entity, id);
        return;
      }
      await apiDelete(id);
    } catch (e) {
      if (isOfflineError(e)) {
        await queueOp('delete', entity, { realId: id });
        return;
      }
      if (backup) await withDbLock(async () => { DB[listName].push(backup); await persistDbNow(); });
      showToast('خطا در حذف: ' + e.message, 'error');
      throw e;
    }
  }

  return { add, update, del };
}

// ---------------------------------------------------------------------------
// Questions
// ---------------------------------------------------------------------------
const _questionCrud = makeOfflineCrud({
  entity: 'question', listName: 'questions', fromApi: questionFromApi,
  apiCreate: Api.createQuestion, apiUpdate: Api.updateQuestion, apiDelete: Api.deleteQuestion,
  addMode: 'unshift',
});
async function apiAddQuestion(payload) { return _questionCrud.add(payload); }
async function apiUpdateQuestion(id, payload) { return _questionCrud.update(id, payload); }
async function apiDeleteQuestion(id) { return _questionCrud.del(id); }

// ---------------------------------------------------------------------------
// Exams
// ---------------------------------------------------------------------------
const _examCrud = makeOfflineCrud({
  entity: 'exam', listName: 'exams', fromApi: examFromApi,
  apiCreate: Api.createExam, apiUpdate: Api.updateExam, apiDelete: Api.deleteExam,
});
async function apiAddExam(payload) { return _examCrud.add(payload); }
async function apiUpdateExam(id, payload) { return _examCrud.update(id, payload); }
async function apiDeleteExam(id) { return _examCrud.del(id); }

// ---------------------------------------------------------------------------
// Alarms
// ---------------------------------------------------------------------------
const _alarmCrud = makeOfflineCrud({
  entity: 'alarm', listName: 'alarms', fromApi: alarmFromApi,
  apiCreate: Api.createAlarm, apiUpdate: Api.updateAlarm, apiDelete: Api.deleteAlarm,
});
async function apiAddAlarm(payload) { return _alarmCrud.add(payload); }
async function apiUpdateAlarm(id, payload) { return _alarmCrud.update(id, payload); }
async function apiDeleteAlarm(id) { return _alarmCrud.del(id); }

// ---------------------------------------------------------------------------
// Study report text builder (mirrors build_study_report_text_for_date)
// ---------------------------------------------------------------------------
function buildStudyReportText(dateStr) {
  const items = getItemsBetween(dateStr, dateStr).filter(i => i.category === 'درسی');
  const studied = [], partial = [], missed = [];
  let totalMin = 0, totalTests = 0;
  items.forEach(it => {
    if (it.status) {
      studied.push(it.name); totalMin += it.studyMinutes; totalTests += it.testCount;
    } else if (it.studyMinutes > 0 || it.testCount > 0) {
      partial.push(`${it.name} (${fa(it.studyMinutes)} دقیقه، ${fa(it.testCount)} تست)`);
      totalMin += it.studyMinutes; totalTests += it.testCount;
    } else {
      missed.push(it.name);
    }
  });
  const lines = [
    'به نام خدا',
    `تاریخ: ${Jalali.gregorianStrToJalaliStr(dateStr)}`,
    `درس‌های مطالعه‌شده: ${studied.length ? studied.join('، ') : 'ندارد'}`,
    `ساعت مطالعه: ${totalMin ? formatMinutes(totalMin) : '۰ دقیقه'}`,
    `تعداد تست: ${fa(totalTests)}`,
    `پارت‌های ناقص: ${partial.length ? partial.join('، ') : 'ندارد'}`,
    `پارت‌های انجام‌نشده: ${missed.length ? missed.join('، ') : 'ندارد'}`
  ];
  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// Weekly stats builder (mirrors build_weekly_pdf_data)
// ---------------------------------------------------------------------------
function extractSubjectName(title) {
  const parts = title.trim().split(/\s+/);
  return parts[0] || 'نامشخص';
}
function buildWeeklyStats(weekStart, weekEnd) {
  const items = getItemsBetween(weekStart, weekEnd).filter(i => i.category === 'درسی');
  const perDayMinutes = {}, studiedDays = new Set();
  let totalMinutes = 0, totalTests = 0, completed = 0, partialCount = 0, missedCount = 0;
  const missedItems = [], partialItems = [];
  const subjectStats = {};

  items.forEach(it => {
    const subject = extractSubjectName(it.name);
    if (!subjectStats[subject]) subjectStats[subject] = { minutes: 0, tests: 0, total: 0, done: 0 };
    subjectStats[subject].total++;

    if (it.status) {
      completed++; subjectStats[subject].done++;
      subjectStats[subject].minutes += it.studyMinutes;
      subjectStats[subject].tests += it.testCount;
      totalMinutes += it.studyMinutes; totalTests += it.testCount;
      perDayMinutes[it.date] = (perDayMinutes[it.date] || 0) + it.studyMinutes;
      if (it.studyMinutes > 0) studiedDays.add(it.date);
    } else if (it.studyMinutes > 0 || it.testCount > 0) {
      partialCount++;
      partialItems.push(`${it.name} «${fa(it.studyMinutes)} دقیقه، ${fa(it.testCount)} تست»`);
      subjectStats[subject].minutes += it.studyMinutes;
      subjectStats[subject].tests += it.testCount;
      totalMinutes += it.studyMinutes; totalTests += it.testCount;
      perDayMinutes[it.date] = (perDayMinutes[it.date] || 0) + it.studyMinutes;
      if (it.studyMinutes > 0) studiedDays.add(it.date);
    } else {
      missedCount++; missedItems.push(it.name);
    }
  });

  const daysWithStudy = studiedDays.size || 1;
  const avgMinutes = Math.round(totalMinutes / daysWithStudy);

  const dayLabels = [], dayHours = [];
  let d = weekStart;
  while (d <= weekEnd) {
    const minutes = perDayMinutes[d] || 0;
    dayHours.push(Math.round((minutes / 60) * 10) / 10);
    const { y, m, d: dd } = Jalali.strToDate(d);
    const wd = Jalali.weekdayOf(y, m, dd);
    dayLabels.push(Jalali.WEEKDAYS[wd]);
    d = Jalali.addDays(d, 1);
  }

  let bestIdx = 0, worstIdx = 0;
  if (dayHours.some(h => h > 0)) {
    bestIdx = dayHours.indexOf(Math.max(...dayHours));
    worstIdx = dayHours.indexOf(Math.min(...dayHours));
  }

  const subjects = Object.entries(subjectStats).map(([name, s]) => ({
    name, minutes: s.minutes, tests: s.tests,
    percent: s.total ? Math.round((s.done / s.total) * 100) : 0
  })).sort((a, b) => b.minutes - a.minutes);

  return {
    totalMinutes, avgMinutes, studiedDaysCount: studiedDays.size, totalTests,
    completed, partialCount, missedCount, missedItems, partialItems,
    dayLabels, dayHours, subjects,
    bestDay: dayLabels[bestIdx], bestDayHours: dayHours[bestIdx],
    worstDay: dayLabels[worstIdx], worstDayHours: dayHours[worstIdx]
  };
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------
let toastTimer = null;
function showToast(msg, icon = 'check_circle') {
  const t = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  t.querySelector('.material-symbols-rounded').textContent = icon;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2200);
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------
const SCREENS = {}; // name -> render function
let currentScreen = 'home';

function go(name) {
  currentScreen = name;
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.nav === name);
  });
  render();
  window.scrollTo(0, 0);
}
function render() {
  const container = document.getElementById('screens');
  container.innerHTML = '';
  const el = document.createElement('div');
  el.className = 'screen active';
  el.id = 'screen-' + currentScreen;
  container.appendChild(el);
  if (SCREENS[currentScreen]) SCREENS[currentScreen](el);
}
function rerender() { render(); }

// ---------------------------------------------------------------------------
// Boot — چک لاگین قبل از هر چیز
// ---------------------------------------------------------------------------
window.addEventListener('DOMContentLoaded', async () => {
  if (!Api.isLoggedIn()) {
    showAuthScreen();
    return;
  }
  await bootAfterLogin();
});

// بعد از اولین لاگین/ثبت‌نام موفق (که حتماً آنلاین انجام شده)، همیشه یک
// کش محلی کامل داریم. از این به بعد، حتی اگه اینترنت نباشه یا توکن سرور
// موقتاً قابل‌اعتبارسنجی نباشه (مثلاً خودِ سرور خوابیده)، کاربر رو با
// همون کش وارد اپ می‌کنیم — نه به صفحه‌ی لاگین برش می‌گردونیم و نه چیزی
// پاک می‌کنیم. فقط وقتی سرور *صراحتاً* با ۴۰۱ بگه توکن نامعتبر/منقضیه
// (یعنی واقعاً آنلاین بودیم و جواب گرفتیم)، کاربر رو به لاگین برمی‌گردونیم.
async function bootAfterLogin() {
  setupOutboxAutoSync();
  let onlineSyncFailed = false;
  let authRejected = false;
  let authRejectMsg = '';

  try {
    await syncFromServer();
  } catch (e) {
    onlineSyncFailed = true;
    if (e instanceof Api.ApiError && e.status === 401) {
      authRejected = true;
      authRejectMsg = e.message;
    }
  }

  if (onlineSyncFailed) {
    const cached = await loadFromLocalCache();
    if (!cached) {
      // هیچ کش محلی‌ای نداریم (مثلاً اولین ورود روی این دستگاه و همزمان
      // قطعی شبکه، یا واقعاً توکن نامعتبره) — چاره‌ای جز صفحه‌ی لاگین نیست.
      if (authRejected) Api.clearToken();
      showAuthScreen(authRejected ? authRejectMsg : 'اتصال به سرور برقرار نشد. دوباره امتحان کن.');
      return;
    }
    if (authRejected) {
      // سرور صراحتاً گفته توکن نامعتبره (نه یک خطای شبکه). این تنها حالتیه
      // که با وجود داشتن کش، باز هم به کاربر اطلاع می‌دیم و اجازه می‌دیم
      // خودش تصمیم بگیره — چون شاید همین الان رمزش عوض شده یا اکانتش
      // جای دیگه‌ای لاگ‌اوت شده. با این‌حال، هیچ داده‌ای پاک نمی‌کنیم.
      showToast('اتصال به حساب دوباره برقرار نشد؛ در حالت آفلاین با آخرین اطلاعات ذخیره‌شده کار می‌کنی', 'wifi_off');
    } else {
      showToast('آفلاینی — با آخرین اطلاعات ذخیره‌شده کار می‌کنی', 'wifi_off');
    }
  }

  hideAuthScreen();
  await runCarryOverIfNeeded();
  checkAlarmsLoop();
  updateSyncBadge();
  go('home');

  // اگه آنلاین بودیم، هر تغییر آفلاین قبلی رو الان بفرست
  if (!onlineSyncFailed) processOutbox();
}

// expose module-scope bindings for debugging/testing convenience
window.__apex = { get DB() { return DB; }, get Jalali() { return Jalali; }, get TimerState() { return typeof TimerState !== 'undefined' ? TimerState : null; } };
Object.defineProperty(window, 'DB', { get() { return DB; }, configurable: true });
Object.defineProperty(window, 'Jalali', { get() { return Jalali; }, configurable: true });
