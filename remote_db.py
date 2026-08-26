"""
جایگزین remote (بکند مشترک) برای local_db.py — دقیقاً همون امضای توابع local_db
قدیمی رو حفظ می‌کند تا bot.py با کمترین تغییر (فقط عوض کردن import) کار کند.

طرز استفاده در bot.py:
    # import local_db  <- این خط رو کامنت/حذف کن
    import remote_db as local_db   # <- این خط رو اضافه کن

متغیرهای محیطی لازم (روی Railway برای سرویس بات ست کن):
    BACKEND_URL   = https://your-backend-service.up.railway.app
    BOT_API_KEY   = همون مقداری که توی سرویس بکند برای BOT_API_KEY ست کردی

نکته‌ی مهم درباره‌ی ثبت‌نام: چون حالا حساب کاربری اصلی توی اپ (با
یوزرنیم/رمز) ساخته می‌شود، register_user اینجا دیگر یک حساب واقعی نمی‌سازد؛
در عوض همان chat_id را به یک حساب از قبل ثبت‌شده در اپ وصل می‌کند (معادل
دستور /link). اگر آن username توی اپ وجود نداشته باشد، خطا می‌دهد.
جزئیات این تغییر رفتار در README-اتصال-بات.md توضیح داده شده.
"""
import os
import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
BOT_API_KEY = os.environ.get("BOT_API_KEY", "dev-only-bot-key-change-me")

_HEADERS = {"X-Bot-Key": BOT_API_KEY}
_TIMEOUT = 15


def _get(path, **kwargs):
    r = requests.get(f"{BACKEND_URL}{path}", headers=_HEADERS, timeout=_TIMEOUT, **kwargs)
    return r


def _post(path, **kwargs):
    r = requests.post(f"{BACKEND_URL}{path}", headers=_HEADERS, timeout=_TIMEOUT, **kwargs)
    return r


def _patch(path, **kwargs):
    r = requests.patch(f"{BACKEND_URL}{path}", headers=_HEADERS, timeout=_TIMEOUT, **kwargs)
    return r


def _delete(path, **kwargs):
    r = requests.delete(f"{BACKEND_URL}{path}", headers=_HEADERS, timeout=_TIMEOUT, **kwargs)
    return r


def _item_to_dict(item: dict) -> dict:
    """خروجی API را به همون شکل dict قدیمی local_db (کلیدهای SQLite-style) تبدیل می‌کند."""
    return {
        "id": item["id"],
        "chat_id": None,  # دیگه مستقیم استفاده نمی‌شه، ولی برای سازگاری کلید نگه داشته شده
        "name": item["name"],
        "date": item["date"],
        "category": item["category"],
        "status": 1 if item["status"] else 0,
        "study_minutes": item["study_minutes"],
        "test_count": item["test_count"],
        "notes": item.get("notes") or "",
    }


def init_db():
    """با معماری جدید نیازی به ساخت جدول محلی نیست؛ بکند خودش روی استارت
    جدول‌ها رو می‌سازه. این تابع فقط برای سازگاری با bot.py نگه داشته شده
    (که در ابتدای main() صداش می‌زنه) و یک health-check ساده انجام می‌دهد."""
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if r.status_code != 200:
            print(f"⚠️ هشدار: بکند در دسترس نیست ({BACKEND_URL}) — status {r.status_code}")
    except Exception as e:
        print(f"⚠️ هشدار: اتصال به بکند برقرار نشد ({BACKEND_URL}): {e}")


# ---------------------------------------------------------------------------
# مدیریت کاربران
# ---------------------------------------------------------------------------
def is_registered(chat_id: int) -> bool:
    r = _get(f"/bot/user-by-chat/{chat_id}")
    return r.status_code == 200


def register_user(chat_id: int, name: str):
    """معادل قدیمی این تابع دیگر کار نمی‌کند چون حساب باید اول توی اپ ساخته
    بشه. این تابع را در بات دیگر مستقیم صدا نزن — به‌جاش از link_account
    استفاده کن (که با دستور /link در بات صدا زده می‌شود)."""
    raise NotImplementedError(
        "ثبت‌نام مستقیم از بات دیگه پشتیبانی نمی‌شه. "
        "کاربر باید اول توی اپ (وب) حساب بسازه، بعد با دستور /link <username> "
        "توی بات وصلش کنه."
    )


def link_account(chat_id: int, username: str) -> dict:
    """معادل جدید register_user: chat_id تلگرام را به یک حساب از قبل
    ثبت‌شده در اپ وصل می‌کند. دستور /link در bot.py این را صدا می‌زند."""
    r = _post("/bot/link-account", json={"username": username, "telegram_chat_id": chat_id})
    if r.status_code == 404:
        raise ValueError("کاربری با این نام کاربری توی اپ ثبت‌نام نکرده. اول توی اپ حساب بساز.")
    r.raise_for_status()
    return r.json()


def get_all_local_chat_ids() -> list:
    """قبلاً از دیتابیس محلی SQLite لیست chat_id های ثبت‌شده رو می‌داد.
    حالا منبع حقیقت بکنده: لیست همه‌ی telegram_chat_id هایی که به یک حساب
    اپ وصل شدن (با /link) و بن نشدن برمی‌گرده. جاب‌های زمان‌بندی‌شده‌ی بات
    (چک‌لیست صبح، چک‌این‌ها، گزارش شب) این رو با chat_id ادمین ترکیب می‌کنن."""
    r = _get("/bot/active-chat-ids")
    r.raise_for_status()
    return r.json()


def get_active_group_ids() -> list:
    """لیست یکتای group_id هایی که حداقل یک عضو (غیر بن‌شده) گزارشش رو
    بهشون وصل کرده. برای job گزارش شبانه‌ی گروهی استفاده می‌شه."""
    r = _get("/bot/active-groups")
    r.raise_for_status()
    return r.json()


def get_user_name(chat_id: int) -> str:
    r = _get(f"/bot/user-by-chat/{chat_id}")
    if r.status_code != 200:
        return "دانش‌آموز"
    return r.json().get("display_name", "دانش‌آموز")


# ---------------------------------------------------------------------------
# مدیریت پارت‌های برنامه
# ---------------------------------------------------------------------------
def add_plan_item(chat_id: int, name: str, date: str, category: str = "درسی") -> str:
    r = _post(f"/bot/plan-items/{chat_id}", json={"name": name, "date": date, "category": category})
    r.raise_for_status()
    return r.json()["id"]


def get_items_for_date(chat_id: int, date: str) -> list:
    r = _get(f"/bot/plan-items/{chat_id}", params={"date": date})
    r.raise_for_status()
    return [_item_to_dict(i) for i in r.json()]


def get_items_between(chat_id: int, start_date: str, end_date: str) -> list:
    # بکند فعلاً فیلتر بازه رو مستقیم برای مسیر bot/ نداره؛ همه رو می‌گیریم و
    # اینجا فیلتر می‌کنیم (برای حجم کوچیک گروه دوستانه کاملاً کافیه).
    r = _get(f"/bot/plan-items/{chat_id}")
    r.raise_for_status()
    items = r.json()
    return [_item_to_dict(i) for i in items if start_date <= i["date"] <= end_date]


def get_item_by_id_for_chat(chat_id: int, item_id: str) -> dict | None:
    """نسخه‌ی صریح (با chat_id مشخص) — bot.py معمولاً chat_id رو در دسترس داره،
    پس این تابع رو صدا بزن، نه get_item_by_id بدون chat_id."""
    r = _get(f"/bot/plan-items/{chat_id}/{item_id}")
    if r.status_code != 200:
        return None
    return _item_to_dict(r.json())


def get_item_by_id(item_id: str) -> dict | None:
    """امضای قدیمی local_db این تابع را بدون chat_id صدا می‌زد (چون SQLite
    محلی می‌توانست مستقیم با id جستجو کند). در معماری جدید API بر اساس
    chat_id کار می‌کند، پس این تابع دیگر مستقیماً کار نمی‌کند — bot.py باید
    برای این مسیرها به get_item_by_id_for_chat(chat_id, item_id) سوییچ کند.
    این نسخه‌ی قدیمی صرفاً برای جلوگیری از کرش، خطای واضح می‌دهد."""
    raise NotImplementedError(
        "get_item_by_id بدون chat_id در معماری جدید پشتیبانی نمی‌شود. "
        "به‌جاش از get_item_by_id_for_chat(chat_id, item_id) استفاده کن."
    )


def delete_item_for_chat(chat_id: int, item_id: str):
    """نسخه‌ی صریح حذف — bot.py باید این را با chat_id صدا بزند."""
    r = _delete(f"/bot/plan-items/{chat_id}/{item_id}")
    return r.status_code == 200


def delete_item(item_id: str):
    raise NotImplementedError(
        "delete_item بدون chat_id در معماری جدید پشتیبانی نمی‌شود. "
        "به‌جاش از delete_item_for_chat(chat_id, item_id) استفاده کن."
    )


def update_item_full_for_chat(chat_id: int, item_id: str, status: bool = None, minutes: int = None, tests: int = None):
    payload = {}
    if status is not None:
        payload["status"] = status
    if minutes is not None:
        payload["study_minutes"] = minutes
    if tests is not None:
        payload["test_count"] = tests
    r = _patch(f"/bot/plan-items/{chat_id}/{item_id}", json=payload)
    r.raise_for_status()
    return _item_to_dict(r.json())


def update_item_full(item_id: str, status: bool = None, minutes: int = None, tests: int = None):
    raise NotImplementedError(
        "update_item_full بدون chat_id در معماری جدید پشتیبانی نمی‌شود. "
        "به‌جاش از update_item_full_for_chat(chat_id, item_id, ...) استفاده کن."
    )


def mark_item_done_for_chat(chat_id: int, item_id: str, done: bool = True):
    return update_item_full_for_chat(chat_id, item_id, status=done)


def mark_item_done(item_id: str, done: bool = True):
    raise NotImplementedError(
        "mark_item_done بدون chat_id در معماری جدید پشتیبانی نمی‌شود. "
        "به‌جاش از mark_item_done_for_chat(chat_id, item_id, done) استفاده کن."
    )


def save_study_data_for_chat(chat_id: int, item_id: str, minutes: int, tests: int, mark_done: bool = True):
    return update_item_full_for_chat(chat_id, item_id, status=mark_done, minutes=minutes, tests=tests)


def save_study_data(item_id: str, minutes: int, tests: int, mark_done: bool = True):
    raise NotImplementedError(
        "save_study_data بدون chat_id در معماری جدید پشتیبانی نمی‌شود. "
        "به‌جاش از save_study_data_for_chat(chat_id, item_id, minutes, tests, mark_done) استفاده کن."
    )


def create_makeup_item(chat_id: int, original_item: dict, tomorrow_date: str) -> str:
    title = original_item["name"]
    if "(جبرانی)" not in title:
        title = f"{title} (جبرانی)"
    return add_plan_item(chat_id, title, tomorrow_date, category=original_item.get("category", "درسی"))


# ---------------------------------------------------------------------------
# کش قالب هفتگی/روزانه — فعلاً به‌صورت in-memory ساده (چون کم‌اهمیت‌تره و
# اگه بات ری‌استارت بشه، فقط یک‌بار دوباره سوال می‌پرسه؛ قابل ارتقا به بکند
# با اضافه‌کردن دو اندپوینت /bot/template-cache در آینده)
# ---------------------------------------------------------------------------
_template_cache = {}


def get_template_meta_cache(chat_id: int, scope: str, period_key: str) -> dict | None:
    return _template_cache.get((chat_id, scope, period_key))


def save_template_meta_cache(chat_id: int, scope: str, period_key: str, data: dict):
    _template_cache[(chat_id, scope, period_key)] = data
