"""
همگام‌سازی برنامه از Notion به دیتابیس اپکس پلنر (برای ادمین).

منطق خوندن/نوشتن property ها عیناً از bot.py (کانکور بات) پورت شده تا با
همون دیتابیس Notion که بات ادمین ازش استفاده می‌کنه سازگار باشه:
  Name (title), Date (date), Category (select), Status (checkbox),
  StudyMinutes (number), TestCount (number), Time (rich_text - اختیاری)

این ماژول فقط "خوندن از Notion و درج/آپدیت توی دیتابیس محلی" رو انجام می‌ده؛
نوشتن به Notion (مثل بات) اینجا لازم نیست چون جهت داده از Notion -> اپه.
"""
import os
from typing import Optional

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")

_notion_client = None


def is_configured() -> bool:
    return bool(NOTION_API_KEY and NOTION_DATABASE_ID)


def _get_client():
    global _notion_client
    if _notion_client is None:
        from notion_client import Client
        _notion_client = Client(auth=NOTION_API_KEY)
    return _notion_client


def _get_text_prop(props: dict, name: str, default: str = "") -> str:
    prop = props.get(name, {})
    ptype = prop.get("type")
    if ptype == "title":
        arr = prop.get("title", [])
    elif ptype == "rich_text":
        arr = prop.get("rich_text", [])
    else:
        return default
    return arr[0]["plain_text"] if arr else default


def _get_select_prop(props: dict, name: str, default: str = "") -> str:
    sel = props.get(name, {}).get("select")
    return sel["name"] if sel else default


def _get_checkbox_prop(props: dict, name: str, default: bool = False) -> bool:
    val = props.get(name, {}).get("checkbox")
    return val if val is not None else default


def _get_number_prop(props: dict, name: str, default: int = 0) -> int:
    val = props.get(name, {}).get("number")
    return int(val) if val is not None else default


def _get_date_prop(props: dict, default: str = "") -> str:
    date_prop = props.get("Date", {}).get("date")
    return date_prop["start"][:10] if date_prop and date_prop.get("start") else default


def page_to_plan_dict(page: dict) -> dict:
    """یک page خام Notion را به دیکشنری سازگار با مدل PlanItem تبدیل می‌کند."""
    props = page.get("properties", {})
    return {
        "notion_page_id": page["id"],
        "name": _get_text_prop(props, "Name", "بدون‌نام"),
        "date": _get_date_prop(props, ""),
        "category": _get_select_prop(props, "Category", "درسی"),
        "status": _get_checkbox_prop(props, "Status", False),
        "study_minutes": _get_number_prop(props, "StudyMinutes", 0),
        "test_count": _get_number_prop(props, "TestCount", 0),
        "time_label": _get_text_prop(props, "Time", ""),
    }


def fetch_plan_items(date_filter: Optional[str] = None) -> list:
    """آیتم‌های برنامه را از دیتابیس Notion می‌خواند (در صورت نیاز فیلترشده روی تاریخ)."""
    if not is_configured():
        raise RuntimeError("تنظیمات Notion پیکربندی نشده است (NOTION_API_KEY / NOTION_DATABASE_ID)")

    client = _get_client()
    query_kwargs = {"database_id": NOTION_DATABASE_ID}
    if date_filter:
        query_kwargs["filter"] = {"property": "Date", "date": {"equals": date_filter}}

    results = []
    cursor = None
    while True:
        if cursor:
            query_kwargs["start_cursor"] = cursor
        response = client.databases.query(**query_kwargs)
        results.extend(response.get("results", []))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")

    return [page_to_plan_dict(p) for p in results]
