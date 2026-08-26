"""
ماژول اتصال به Notion برای ادمین پلنر.

این ماژول به ادمین اجازه می‌دهد از طریق Notion برنامه‌های خود را وارد دیتابیس کند.
همچنین یک سیستم Restore Point ایجاد می‌کند تا در صورت خرابی اپلیکیشن، بتوان داده‌ها را بازیابی کرد.

متغیرهای محیطی مورد نیاز:
- NOTION_API_KEY: کلید API ناتیون (از https://www.notion.so/my-integrations)
- NOTION_DATABASE_ID: آی‌دی دیتابیس ناتیون که بات به آن متصل است
"""
import os
import json
import hashlib
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from notion_client import Client
from sqlalchemy.orm import Session
from . import models


def get_notion_client() -> Optional[Client]:
    """ایجاد کلاینت ناتیون با استفاده از متغیر محیطی."""
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        return None
    return Client(auth=api_key)


def get_notion_database_id() -> Optional[str]:
    """دریافت آی‌دی دیتابیس ناتیون از متغیر محیطی."""
    return os.getenv("NOTION_DATABASE_ID")


def _generate_restore_point_hash(data: Dict[str, Any]) -> str:
    """تولید هش یکتا برای هر restore point."""
    data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return "rp_" + hashlib.sha256(data_str.encode()).hexdigest()[:32]


def create_restore_point(
    db: Session,
    user_id: int,
    operation_type: str,
    data_before: Optional[Dict[str, Any]] = None,
    data_after: Optional[Dict[str, Any]] = None,
    description: str = ""
) -> models.RestorePoint:
    """
    ایجاد یک restore point قبل از انجام عملیات حساس.
    
    Args:
        db: سشن دیتابیس
        user_id: آی‌دی کاربری که عملیات را انجام می‌دهد
        operation_type: نوع عملیات (مثلاً 'notion_sync', 'bulk_delete', 'update_all')
        data_before: داده‌های قبل از عملیات (اختیاری)
        data_after: داده‌های بعد از عملیات (اختیاری)
        description: توضیحات اضافی درباره restore point
    
    Returns:
        آبجکت RestorePoint ایجاد شده
    """
    restore_data = {
        "operation_type": operation_type,
        "data_before": data_before,
        "data_after": data_after,
        "description": description,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    rp = models.RestorePoint(
        id=_generate_restore_point_hash(restore_data),
        owner_id=user_id,
        operation_type=operation_type,
        restore_data_json=json.dumps(restore_data, ensure_ascii=False),
        created_at=datetime.utcnow(),
    )
    db.add(rp)
    db.commit()
    db.refresh(rp)
    return rp


def list_restore_points(
    db: Session,
    user_id: int,
    limit: int = 50
) -> List[models.RestorePoint]:
    """دریافت لیست restore pointهای یک کاربر."""
    return db.query(models.RestorePoint).filter(
        models.RestorePoint.owner_id == user_id
    ).order_by(
        models.RestorePoint.created_at.desc()
    ).limit(limit).all()


def restore_from_point(
    db: Session,
    restore_point_id: str,
    user_id: int
) -> Dict[str, Any]:
    """
    بازیابی داده‌ها از یک restore point.
    
    این تابع داده‌های ذخیره شده در restore point را برمی‌گرداند،
    اما عملیات واقعی بازیابی باید توسط caller انجام شود.
    
    Returns:
        دیکشنری شامل اطلاعات restore point و داده‌های قابل بازیابی
    """
    rp = db.query(models.RestorePoint).filter(
        models.RestorePoint.id == restore_point_id,
        models.RestorePoint.owner_id == user_id
    ).first()
    
    if not rp:
        raise ValueError("Restore point یافت نشد یا متعلق به شما نیست")
    
    restore_data = json.loads(rp.restore_data_json)
    
    return {
        "id": rp.id,
        "operation_type": rp.operation_type,
        "created_at": rp.created_at.isoformat(),
        "description": restore_data.get("description", ""),
        "data_before": restore_data.get("data_before"),
        "data_after": restore_data.get("data_after"),
    }


def sync_plan_from_notion(
    db: Session,
    user: models.User,
    notion_date_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    همگام‌سازی برنامه‌ها از ناتیون به دیتابیس برای کاربر ادمین.
    
    این تابع صفحات دیتابیس ناتیون را می‌خواند و به عنوان plan_items ذخیره می‌کند.
    
    Args:
        db: سشن دیتابیس
        user: کاربر ادمین
        notion_date_filter: فیلتر تاریخ اختیاری (فرمت YYYY-MM-DD)
    
    Returns:
        دیکشنری شامل آمار همگام‌سازی
    """
    client = get_notion_client()
    database_id = get_notion_database_id()
    
    if not client or not database_id:
        raise RuntimeError("تنظیمات ناتیون پیکربندی نشده است. لطفاً NOTION_API_KEY و NOTION_DATABASE_ID را تنظیم کنید.")
    
    # ساخت کوئری برای دریافت صفحات از ناتیون
    query_params = {
        "database_id": database_id,
        "filter": {
            "property": "Status",
            "select": {
                "equals": "Not started"
            }
        }
    }
    
    # اگر فیلتر تاریخ مشخص شده، اضافه کن
    if notion_date_filter:
        query_params["filter"] = {
            "and": [
                query_params["filter"],
                {
                    "property": "Date",
                    "date": {
                        "equals": notion_date_filter
                    }
                }
            ]
        }
    
    try:
        response = client.databases.query(**query_params)
    except Exception as e:
        raise RuntimeError(f"خطا در ارتباط با ناتیون: {str(e)}")
    
    # ذخیره restore point قبل از همگام‌سازی
    existing_items = db.query(models.PlanItem).filter(
        models.PlanItem.owner_id == user.id
    ).all()
    data_before = {
        "items_count": len(existing_items),
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "date": item.date,
                "status": item.status,
            }
            for item in existing_items[:50]  # فقط ۵۰ تای اول برای جلوگیری از حجم زیاد
        ]
    }
    
    created_count = 0
    updated_count = 0
    synced_items = []
    
    for page in response.get("results", []):
        # استخراج داده‌ها از صفحه ناتیون
        properties = page.get("properties", {})
        
        # دریافت نام (Title)
        title_property = properties.get("Name", {}) or properties.get("Task", {})
        name = ""
        if "title" in title_property and title_property["title"]:
            name = title_property["title"][0].get("plain_text", "")
        
        # دریافت تاریخ
        date_property = properties.get("Date", {})
        date_value = ""
        if "date" in date_property and date_property["date"]:
            date_obj = date_property["date"].get("start")
            if date_obj:
                date_value = date_obj
        
        # دریافت دسته‌بندی
        category_property = properties.get("Category", {}) or properties.get("Type", {})
        category = "درسی"
        if "select" in category_property and category_property["select"]:
            category = category_property["select"].get("name", "درسی")
        
        # دریافت وضعیت
        status_property = properties.get("Status", {})
        status = False
        if "select" in status_property and status_property["select"]:
            status_name = status_property["select"].get("name", "")
            status = status_name.lower() in ["completed", "done", "انجام شده"]
        
        # دریافت زمان مطالعه
        minutes_property = properties.get("Study Minutes", {}) or properties.get("Minutes", {})
        study_minutes = 0
        if "number" in minutes_property and minutes_property["number"]:
            study_minutes = minutes_property["number"]
        
        # دریافت تعداد تست
        tests_property = properties.get("Test Count", {}) or properties.get("Tests", {})
        test_count = 0
        if "number" in tests_property and tests_property["number"]:
            test_count = tests_property["number"]
        
        # دریافت یادداشت‌ها
        notes_property = properties.get("Notes", {}) or properties.get("Description", {})
        notes = ""
        if "rich_text" in notes_property and notes_property["rich_text"]:
            notes = "".join(rt.get("plain_text", "") for rt in notes_property["rich_text"])
        
        # بررسی وجود آیتم با همین نام و تاریخ
        existing_item = db.query(models.PlanItem).filter(
            models.PlanItem.owner_id == user.id,
            models.PlanItem.name == name,
            models.PlanItem.date == date_value,
        ).first()
        
        if existing_item:
            # بروزرسانی آیتم موجود
            existing_item.status = status
            existing_item.study_minutes = study_minutes
            existing_item.test_count = test_count
            existing_item.notes = notes
            existing_item.category = category
            db.commit()
            updated_count += 1
            synced_items.append({"id": existing_item.id, "action": "updated", "name": name})
        else:
            # ایجاد آیتم جدید
            from .main import new_id
            item = models.PlanItem(
                id=new_id(),
                owner_id=user.id,
                name=name or "بدون نام",
                date=date_value or datetime.utcnow().strftime("%Y-%m-%d"),
                category=category,
                status=status,
                study_minutes=study_minutes,
                test_count=test_count,
                notes=notes,
            )
            db.add(item)
            db.commit()
            db.refresh(item)
            created_count += 1
            synced_items.append({"id": item.id, "action": "created", "name": name})
    
    # ذخیره restore point بعد از همگام‌سازی
    data_after = {
        "created_count": created_count,
        "updated_count": updated_count,
        "synced_items": synced_items[:50]  # فقط ۵۰ تای اول
    }
    
    create_restore_point(
        db=db,
        user_id=user.id,
        operation_type="notion_sync",
        data_before=data_before,
        data_after=data_after,
        description=f"همگام‌سازی از ناتیون: {created_count} ایجاد، {updated_count} بروزرسانی"
    )
    
    return {
        "success": True,
        "created": created_count,
        "updated": updated_count,
        "total_synced": len(synced_items),
        "items": synced_items,
    }


def get_notion_integration_url() -> str:
    """برگرداندن URL برای ساخت integration در ناتیون."""
    return "https://www.notion.so/my-integrations"


def get_notion_database_guide() -> str:
    """راهنمای دریافت Database ID از ناتیون."""
    return """
برای دریافت Database ID ناتیون:
1. به صفحه دیتابیس مورد نظر در ناتیون بروید
2. روی سه نقطه (...) بالای سمت راست کلیک کنید
3. گزینه Copy link را بزنید
4. لینک کپی شده به این شکل است: https://www.notion.so/your-workspace/DATABASE_ID?v=...
5. بخش DATABASE_ID (بین اسلش‌ها) را کپی کنید
"""
