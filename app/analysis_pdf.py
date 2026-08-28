"""
بانک تحلیل — تشخیص خودکار «شماره سوال -> صفحه» از روی متن PDF دفترچه‌ی آزمون.

این تشخیص OCR تصویری نیست (که نیاز به کتابخونه‌های سنگین و کند داره)، بلکه
استخراج متن مستقیم PDF است: دفترچه‌های آزمون معمولاً با متن قابل‌انتخاب
(نه اسکن خام) تولید می‌شن، پس pdfplumber می‌تونه متن هر صفحه رو بخونه و با
چند الگوی رایج («سوال ۱»، «۱-»، «۱.») شماره‌ی هر سوال و صفحه‌اش رو پیدا کنه.

اگه این روش نتیجه‌ی قابل‌اعتماد نداد (مثلاً کمتر از نصف سوالات پیدا شدن یا
ترتیب شماره‌ها بهم‌ریخته بود)، به بک‌اند خبر می‌دیم که auto detection شکست
خورده، تا بقیه‌ی مسیر (mapping خطی دستی) استفاده بشه.
"""
import re
from typing import Dict, List, Optional, Tuple

try:
    import pdfplumber
except ImportError:  # اگه به هر دلیلی نصب نبود، اپ نباید کلاً بالا نیاد
    pdfplumber = None


# فارسی/عربی ارقام هم توی خیلی از دفترچه‌ها استفاده می‌شه؛ اینا رو به عدد لاتین تبدیل می‌کنیم
_FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"


def _normalize_digits(s: str) -> str:
    out = []
    for ch in s:
        if ch in _FA_DIGITS:
            out.append(str(_FA_DIGITS.index(ch)))
        elif ch in _AR_DIGITS:
            out.append(str(_AR_DIGITS.index(ch)))
        else:
            out.append(ch)
    return "".join(out)


# الگوهای رایج شروع سوال در دفترچه‌های آزمون فارسی:
#   "سوال 1"، "سؤال ۱"، "1-"، "1."، "1)"  در ابتدای خط
_PATTERNS = [
    re.compile(r"^\s*سوال\s*[:\-]?\s*(\d{1,3})\b"),
    re.compile(r"^\s*سؤال\s*[:\-]?\s*(\d{1,3})\b"),
    re.compile(r"^\s*(\d{1,3})\s*[-–.\)]\s+\S"),
]


def _extract_page_texts(pdf_path: str) -> List[str]:
    if pdfplumber is None:
        return []
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw = page.extract_text() or ""
            texts.append(_normalize_digits(raw))
    return texts


def get_page_count(pdf_path: str) -> int:
    if pdfplumber is None:
        return 0
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)


def detect_question_page_map(pdf_path: str, expected_question_count: Optional[int] = None) -> Tuple[Dict[int, int], int]:
    """تلاش برای استخراج خودکار نگاشت شماره‌سوال -> صفحه (۱-بیس).

    خروجی: (mapping, page_count)
    mapping ممکنه خالی باشه (یعنی تشخیص خودکار شکست خورد).
    """
    if pdfplumber is None:
        return {}, 0

    page_texts = _extract_page_texts(pdf_path)
    page_count = len(page_texts)
    if page_count == 0:
        return {}, 0

    found: Dict[int, int] = {}
    for page_idx, text in enumerate(page_texts, start=1):
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            for pattern in _PATTERNS:
                m = pattern.match(line)
                if m:
                    try:
                        qnum = int(m.group(1))
                    except ValueError:
                        continue
                    # فقط شماره‌های معقول (۱ تا ۲۰۰) رو قبول کن تا شماره‌گذاری
                    # گزینه‌ها یا صفحات یا تاریخ به‌اشتباه به‌عنوان سوال شناخته نشه
                    if 1 <= qnum <= 200:
                        # اگه این شماره قبلاً با صفحه‌ی زودتری پیدا شده، همون رو نگه دار
                        # (اولین‌باری که شماره‌ی سوال ظاهر می‌شه معمولاً شروع خود سواله)
                        if qnum not in found:
                            found[qnum] = page_idx
                    break  # یک الگو برای این خط کافیه

    if not found:
        return {}, page_count

    # اعتبارسنجی کیفیت تشخیص: باید حداقل نیمی از سوالات موردانتظار پیدا شده
    # باشن و ترتیب صفحه‌ها هم صعودی (یا مساوی) با شماره‌ی سوال باشه، وگرنه
    # احتمالاً چیزی که پیدا کردیم شماره‌ی گزینه یا موارد دیگه بوده، نه سوال.
    numbers_sorted = sorted(found.keys())
    if expected_question_count and len(numbers_sorted) < max(3, expected_question_count * 0.5):
        return {}, page_count

    pages_in_order = [found[n] for n in numbers_sorted]
    non_decreasing = all(pages_in_order[i] <= pages_in_order[i + 1] for i in range(len(pages_in_order) - 1))
    if not non_decreasing:
        return {}, page_count

    return found, page_count


def build_linear_map(question_count: int, start_page: int, end_page: int) -> Dict[int, int]:
    """نگاشت خطی (proportional) بین صفحه‌ی شروع سوال ۱ و صفحه‌ی سوال آخر.

    مثال: سوال ۱ از صفحه ۳، سوال ۷۵ توی صفحه ۱۸ -> بقیه‌ی سوالات به‌نسبت
    بین این دو صفحه پخش می‌شن (خطی، نه لزوماً دقیق تک‌تک، اما تخمین معقول).
    """
    if question_count <= 0:
        return {}
    if question_count == 1 or end_page <= start_page:
        return {1: start_page}

    mapping: Dict[int, int] = {}
    span_pages = end_page - start_page
    span_questions = question_count - 1
    for q in range(1, question_count + 1):
        ratio = (q - 1) / span_questions
        page = start_page + round(ratio * span_pages)
        mapping[q] = max(start_page, min(end_page, page))
    return mapping


def fill_gaps_in_map(mapping: Dict[int, int], question_count: int) -> Dict[int, int]:
    """اگه تشخیص خودکار فقط بعضی شماره‌ها رو پیدا کرده، بقیه رو با درون‌یابی
    خطی بین نزدیک‌ترین شماره‌های پیداشده پر می‌کنیم."""
    if not mapping:
        return {}
    known_numbers = sorted(mapping.keys())
    full: Dict[int, int] = {}
    for q in range(1, question_count + 1):
        if q in mapping:
            full[q] = mapping[q]
            continue
        # نزدیک‌ترین شماره‌ی قبلی و بعدی که مقدارشون معلومه
        prev_n = max([n for n in known_numbers if n < q], default=None)
        next_n = min([n for n in known_numbers if n > q], default=None)
        if prev_n is not None and next_n is not None:
            ratio = (q - prev_n) / (next_n - prev_n)
            page = mapping[prev_n] + round(ratio * (mapping[next_n] - mapping[prev_n]))
        elif prev_n is not None:
            page = mapping[prev_n]
        elif next_n is not None:
            page = mapping[next_n]
        else:
            page = 1
        full[q] = page
    return full
