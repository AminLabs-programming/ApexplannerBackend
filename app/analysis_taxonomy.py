# -*- coding: utf-8 -*-
"""
تاکسونومی ثابتِ «بانک تحلیل» (Analysis Bank).

این فایل تنها منبع حقیقت (single source of truth) برای سه چیز است:
  ۱. پایه‌های تحصیلی معتبر (grade)
  ۲. ساختار سلسله‌مراتبی دسته‌ی اصلی → درس (category → subject)
  ۳. وضعیت‌های معتبر پاسخ هر سؤال (answer_status)

نکته‌ی مهم برای نگه‌داری آینده:
  یک نسخه‌ی معادل (و باید هم‌گام نگه داشته شود) از همین تاکسونومی در
  فرانت‌اند در فایل `screens_analysis.js` به‌صورت ثابت `ANALYSIS_TAXONOMY`
  تعریف شده. اگر اینجا درس یا کدی اضافه/تغییر داد شود، باید همان تغییر
  را در `screens_analysis.js` هم اعمال کرد. این کدها (کلیدهای دیکشنری)
  فقط داخلی هستند و هرگز مستقیم به کاربر نمایش داده نمی‌شوند؛ آنچه
  به کاربر نشان داده می‌شود همیشه مقدار «label» فارسی است.
"""

from typing import Dict, List, Optional

# پایه‌های تحصیلی معتبر
VALID_GRADES: List[int] = [10, 11, 12]

GRADE_LABELS: Dict[int, str] = {
    10: "دهم",
    11: "یازدهم",
    12: "دوازدهم",
}

# وضعیت‌های معتبر پاسخ هر سؤال
VALID_ANSWER_STATUSES: List[str] = ["correct", "incorrect", "unanswered"]

ANSWER_STATUS_LABELS: Dict[str, str] = {
    "correct": "درست زدم",
    "incorrect": "غلط زدم",
    "unanswered": "نزدم",
}

# ساختار سلسله‌مراتبی: دسته‌ی اصلی -> {label, subjects: {کد -> عنوان فارسی}}
SUBJECT_TAXONOMY: Dict[str, Dict] = {
    "math": {
        "label": "ریاضیات",
        "subjects": {
            "math1": "ریاضی 1",
            "geometry1": "هندسه 1",
            "geometry2": "هندسه 2",
            "stats_prob": "آمار و احتمال",
            "calculus1": "حسابان 1",
            "calculus2": "حسابان 2",
            "geometry3": "هندسه 3",
            "discrete_math": "ریاضیات گسسته",
        },
    },
    "physics": {
        "label": "فیزیک",
        "subjects": {
            "physics1": "فیزیک 1",
            "physics2": "فیزیک 2",
            "physics3": "فیزیک 3",
        },
    },
    "chemistry": {
        "label": "شیمی",
        "subjects": {
            "chemistry1": "شیمی 1",
            "chemistry2": "شیمی 2",
            "chemistry3": "شیمی 3",
        },
    },
}

# نگاشت مستقیم کد درس -> کد دسته‌ی اصلی (برای جست‌وجوی سریع، از روی
# SUBJECT_TAXONOMY ساخته می‌شود تا هیچ داده‌ی تکراری‌ای دستی نوشته نشود)
_SUBJECT_TO_CATEGORY: Dict[str, str] = {
    subj_code: cat_code
    for cat_code, cat in SUBJECT_TAXONOMY.items()
    for subj_code in cat["subjects"]
}


def is_valid_grade(grade) -> bool:
    try:
        return int(grade) in VALID_GRADES
    except (TypeError, ValueError):
        return False


def is_valid_category(category: Optional[str]) -> bool:
    return bool(category) and category in SUBJECT_TAXONOMY


def is_valid_subject_code(code: Optional[str]) -> bool:
    return bool(code) and code in _SUBJECT_TO_CATEGORY


def is_valid_answer_status(status: Optional[str]) -> bool:
    return status in VALID_ANSWER_STATUSES


def category_of(subject_code: Optional[str]) -> str:
    """کد دسته‌ی اصلیِ متعلق به یک کد درس؛ اگر کد نامعتبر/خالی بود رشته‌ی خالی."""
    if not subject_code:
        return ""
    return _SUBJECT_TO_CATEGORY.get(subject_code, "")


def category_label(category_code: Optional[str]) -> str:
    if not category_code or category_code not in SUBJECT_TAXONOMY:
        return ""
    return SUBJECT_TAXONOMY[category_code]["label"]


def subject_label(subject_code: Optional[str]) -> str:
    """عنوان فارسیِ یک کد درس؛ اگر کد نامعتبر/خالی بود رشته‌ی خالی."""
    if not subject_code:
        return ""
    cat_code = _SUBJECT_TO_CATEGORY.get(subject_code)
    if not cat_code:
        return ""
    return SUBJECT_TAXONOMY[cat_code]["subjects"].get(subject_code, "")


def subject_codes_for_category(category_code: Optional[str]) -> List[str]:
    if not category_code or category_code not in SUBJECT_TAXONOMY:
        return []
    return list(SUBJECT_TAXONOMY[category_code]["subjects"].keys())


def grade_label(grade) -> str:
    try:
        g = int(grade)
    except (TypeError, ValueError):
        return ""
    return GRADE_LABELS.get(g, "")


def answer_status_from_legacy(is_correct: Optional[bool]) -> str:
    """تبدیل مقدار قدیمیِ is_correct (True/False/None) به answer_status جدید."""
    if is_correct is True:
        return "correct"
    if is_correct is False:
        return "incorrect"
    return "unanswered"


def legacy_is_correct_from_status(answer_status: str) -> Optional[bool]:
    """مشتق‌کردن مقدار قدیمیِ is_correct از answer_status جدید (برای سازگاری با عقب)."""
    if answer_status == "correct":
        return True
    if answer_status == "incorrect":
        return False
    return None
