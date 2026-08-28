/* =========================================================================
   لایه‌ی ارتباط با بکند
   تمام درخواست‌ها از اینجا رد می‌شن. توکن JWT توی localStorage مرورگر نگه
   داشته می‌شه تا بین باز کردن‌های بعدی اپ هم کاربر لاگین بمونه. چون این اپ
   یک فایل مستقل روی گیت‌هاب پیجزه (نه آرتیفکت داخل چت کلود)، استفاده از
   localStorage اینجا کاملاً پشتیبانی می‌شه و محدودیت آرتیفکت‌ها صدق نمی‌کنه.
   ========================================================================= */

const Api = (() => {
  const TOKEN_KEY = "apex_token";
  const USER_CACHE_KEY = "apex_user_cache";

  function getToken() {
    try { return localStorage.getItem(TOKEN_KEY); } catch (e) { return null; }
  }
  function setToken(token) {
    try { localStorage.setItem(TOKEN_KEY, token); } catch (e) {}
  }
  function clearToken() {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_CACHE_KEY);
    } catch (e) {}
  }
  function getCachedUser() {
    try {
      const raw = localStorage.getItem(USER_CACHE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }
  function setCachedUser(user) {
    try { localStorage.setItem(USER_CACHE_KEY, JSON.stringify(user)); } catch (e) {}
  }

  class ApiError extends Error {
    constructor(message, status) {
      super(message);
      this.status = status;
    }
    // status===0 یعنی اصلاً به سرور نرسیدیم (آفلاین / DNS / تایم‌اوت و...)؛
    // این با خطاهای واقعی سرور (۴xx/۵xx) فرق داره و باید به‌جای نمایش خطا
    // به کاربر، باعث صف‌شدنِ عملیات توی outbox بشه.
    get isNetworkError() { return this.status === 0; }
  }

  async function request(method, path, { json, params, auth = true } = {}) {
    // آدرس بکند رو نرمالایز می‌کنیم تا اگه کاربر با یا بدون "/" آخر ست
    // کرده باشه، همیشه یه اسلش تمیز بین دامنه و مسیر باشه (نه صفر، نه دوتا)
    const base = (APEX_CONFIG.BACKEND_URL || "").replace(/\/+$/, "");
    let url = base + path;
    if (params) {
      const qs = new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== undefined && v !== null)
      ).toString();
      if (qs) url += "?" + qs;
    }
    const headers = { "Content-Type": "application/json" };
    if (auth) {
      const token = getToken();
      if (token) headers["Authorization"] = "Bearer " + token;
    }
    let res;
    try {
      res = await fetch(url, {
        method,
        headers,
        body: json !== undefined ? JSON.stringify(json) : undefined,
      });
    } catch (networkErr) {
      throw new ApiError("اتصال به سرور برقرار نشد. اینترنتت یا آدرس بکند رو چک کن.", 0);
    }
    let body = null;
    try { body = await res.json(); } catch (e) {}
    if (!res.ok) {
      const detail = (body && body.detail) || `خطای سرور (${res.status})`;
      if (res.status === 401) {
        clearToken();
      }
      throw new ApiError(detail, res.status);
    }
    return body;
  }

  return {
    ApiError,
    getToken, setToken, clearToken, getCachedUser, setCachedUser,
    isLoggedIn: () => !!getToken(),

    // ---- connectivity ----
    // یه درخواست سبک برای چک واقعی «آیا سرور جواب می‌ده؟». برخلاف
    // navigator.onLine (که فقط یعنی کارت شبکه روشنه، نه اینکه واقعاً
    // اینترنت/سرور در دسترسه)، این یکی واقعاً به بکند سر می‌زنه.
    ping: () => request("GET", "/auth/me").then(() => true).catch((e) => {
      if (e instanceof ApiError && !e.isNetworkError) return true; // سرور جواب داد (حتی خطا) یعنی آنلاینیم
      return false;
    }),

    // ---- auth ----
    register: (username, password, display_name) =>
      request("POST", "/auth/register", { json: { username, password, display_name }, auth: false }),
    login: (username, password) =>
      request("POST", "/auth/login", { json: { username, password }, auth: false }),
    me: () => request("GET", "/auth/me"),
    updateMe: (payload) => request("PATCH", "/auth/me", { json: payload }),
    changePassword: (currentPassword, newPassword) =>
      request("PATCH", "/auth/change-password", { json: { current_password: currentPassword, new_password: newPassword } }),
    forgotPassword: (username) =>
      request("POST", "/auth/forgot-password", { json: { username }, auth: false }),
    resetPassword: (username, code, newPassword) =>
      request("POST", "/auth/reset-password", { json: { username, code, new_password: newPassword }, auth: false }),

    // ---- plan items ----
    listPlanItems: (params) => request("GET", "/plan-items", { params }),
    createPlanItem: (payload) => request("POST", "/plan-items", { json: payload }),
    updatePlanItem: (id, payload) => request("PATCH", `/plan-items/${id}`, { json: payload }),
    deletePlanItem: (id) => request("DELETE", `/plan-items/${id}`),

    // ---- questions ----
    listQuestions: () => request("GET", "/questions"),
    createQuestion: (payload) => request("POST", "/questions", { json: payload }),
    updateQuestion: (id, payload) => request("PATCH", `/questions/${id}`, { json: payload }),
    deleteQuestion: (id) => request("DELETE", `/questions/${id}`),

    // ---- exams ----
    listExams: () => request("GET", "/exams"),
    createExam: (payload) => request("POST", "/exams", { json: payload }),
    updateExam: (id, payload) => request("PATCH", `/exams/${id}`, { json: payload }),
    deleteExam: (id) => request("DELETE", `/exams/${id}`),

    // ---- alarms ----
    listAlarms: () => request("GET", "/alarms"),
    createAlarm: (payload) => request("POST", "/alarms", { json: payload }),
    updateAlarm: (id, payload) => request("PATCH", `/alarms/${id}`, { json: payload }),
    deleteAlarm: (id) => request("DELETE", `/alarms/${id}`),

    // ---- admin ----
    adminListMembers: () => request("GET", "/admin/members"),
    adminSetBan: (userId, banned) => request("POST", `/admin/members/${userId}/ban`, { json: { banned } }),
    adminDeleteMember: (userId) => request("DELETE", `/admin/members/${userId}`),
    adminResetPassword: (userId, newPassword) =>
      request("POST", `/admin/members/${userId}/reset-password`, { json: { new_password: newPassword || null } }),

    // ---- admin: notion sync ----
    adminNotionStatus: () => request("GET", "/admin/notion/status"),
    adminNotionSync: (date) => request("POST", "/admin/notion/sync", { json: { date: date || null } }),
  };
})();

// در محیط‌های واقعی مرورگر، `const Api` در بالای فایل به‌صورت خودکار به‌عنوان
// یک global در دسترسه (چون این کد به‌صورت <script> معمولی، نه ماژول، لود
// می‌شه). این خط صرفاً برای اطمینان و سازگاری با ابزارهای تست/دیباگ اضافه
// شده که ممکنه از vm context جدا به این متغیر نیاز داشته باشن.
if (typeof window !== 'undefined') window.Api = Api;
