"""
همگام‌سازی دوطرفهٔ برنامه بین اپکس پلنر و Notion (فقط برای کاربر ادمین).

منطق خوندن/نوشتن property ها عیناً از bot.py (کانکور بات) پورت شده تا با
همون دیتابیس Notion که بات ادمین ازش استفاده می‌کنه سازگار باشه:
  Name (title), Date (date), Category (select), Status (checkbox),
  StudyMinutes (number), TestCount (number), Time (rich_text - اختیاری)

این ماژول هر دو جهت رو پوشش می‌ده:
  - خوندن از Notion و درج/آپدیت توی دیتابیس محلی (fetch_plan_items)
  - ساخت/آپدیت/حذف در Notion وقتی ادمین از خودِ اپ یک آیتم رو
    می‌سازه/ویرایش می‌کنه/حذف می‌کنه (create_plan_item_page,
    push_plan_item, delete_plan_item_page)
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


def _plan_item_properties(item) -> dict:
    """دیکشنری property های Notion از روی یک شیء PlanItem می‌سازه — برای
    استفاده‌ی مشترک در ساخت (create) و آپدیت (update) صفحه."""
    props = {
        "Name": {"title": [{"text": {"content": item.name or "بدون‌نام"}}]},
        "Category": {"select": {"name": item.category or "درسی"}},
        "Status": {"checkbox": bool(item.status)},
        "StudyMinutes": {"number": item.study_minutes or 0},
        "TestCount": {"number": item.test_count or 0},
    }
    if item.date:
        props["Date"] = {"date": {"start": item.date}}
    # فیلد Time توی دیتابیس Notion اختیاریه (ممکنه بعضی دیتابیس‌ها نداشته
    # باشنش)؛ همیشه می‌فرستیمش، اگه property وجود نداشته باشه Notion خودش
    # با خطای واضح جواب می‌ده که در push_plan_item/create_plan_item_page
    # گرفته و لاگ می‌شه، نه اینکه کل درخواست کاربر رو بشکنه.
    props["Time"] = {"rich_text": [{"text": {"content": item.time_label or ""}}]}
    return props


def create_plan_item_page(item) -> Optional[str]:
    """یک صفحه‌ی جدید توی دیتابیس Notion برای این PlanItem می‌سازه و
    notion_page_id ساخته‌شده رو برمی‌گردونه (یا None اگه Notion کانفیگ
    نشده باشه). صدازننده مسئوله این مقدار رو روی item.notion_page_id
    ذخیره و commit کنه."""
    if not is_configured():
        return None
    client = _get_client()
    page = client.pages.create(
        parent={"database_id": NOTION_DATABASE_ID},
        properties=_plan_item_properties(item),
    )
    return page["id"]


def push_plan_item(item) -> bool:
    """همه‌ی فیلدهای مرتبط یک PlanItem رو در Notion آپدیت می‌کنه (جهت
    اپ -> Notion). فقط وقتی آیتم notion_page_id داشته باشه کار می‌کنه؛
    یعنی صفحه‌ی متناظرش قبلاً (با create_plan_item_page یا سینک از
    Notion) ساخته شده."""
    if not is_configured() or not item.notion_page_id:
        return False
    client = _get_client()
    client.pages.update(
        page_id=item.notion_page_id,
        properties=_plan_item_properties(item),
    )
    return True


def delete_plan_item_page(notion_page_id: str) -> bool:
    """صفحه‌ی متناظر رو در Notion حذف می‌کنه. Notion API صفحات رو واقعاً
    برای همیشه پاک نمی‌کنه بلکه به سطل زباله (Trash) می‌فرسته — که از دید
    کاربر و از دید دیتابیس اصلی (query های بعدی) دقیقاً معادل «حذف‌شده»ست
    و از "Trash" هم قابل بازیابیه، دقیقاً مثل حذف یک صفحه از تو خودِ
    Notion. برای بازگردوندنش هم کاربر باید از داخل Notion اقدام کنه."""
    if not is_configured() or not notion_page_id:
        return False
    client = _get_client()
    client.pages.update(page_id=notion_page_id, archived=True)
    return True


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
