"""
بانک تحلیل (Analysis Bank) — تشخیص خودکار نگاشت «شماره‌سؤال -> صفحه‌ی PDF»

این ماژول برای دفترچه‌های آزمون (کانون/قلم‌چی/ماز و مشابه) طراحی شده که در آن‌ها
شماره‌ی هر سؤال معمولاً به‌صورت «-N» (خط تیره + عدد، با یا بدون فاصله) درست قبل از
متن سؤال چاپ می‌شود. تلاش می‌کنیم این الگو را از روی متن استخراج‌شده‌ی PDF (با
pdfplumber) پیدا کنیم؛ اگر تشخیص خودکار به اندازه‌ی کافی مطمئن نبود، دیکشنری خالی
برمی‌گردانیم تا main.py به نگاشت خطی دستی (build_linear_map) سقوط کند.

نکات مهمی که در طراحی الگو در نظر گرفته شده (بر اساس بررسی نمونه‌های واقعی):

1) بسیاری از دفترچه‌های ناشران ایرانی (به‌خصوص قلم‌چی) فونت فارسیِ بدون جدول
   ToUnicode دارند؛ یعنی متن فارسی به‌صورت اشیاء "(cid:N)" بی‌معنی استخراج می‌شود،
   اما ارقام لاتین («0-9») که معمولاً با فونت جداگانه‌ای چاپ شده‌اند، سالم و قابل
   خواندن استخراج می‌شوند. بنابراین الگوریتم فقط به دنبال ارقام کنار خط تیره
   می‌گردد و کاری به معنای متن اطراف (که ممکن است بی‌معنی باشد) ندارد.

2) خط تیره‌ی نشانه‌ی سؤال معمولاً کاراکتر ASCII hyphen-minus («-», U+002D) است،
   در حالی‌که علامت منفی داخل گزینه‌های عددی در بسیاری از دفترچه‌ها (مثلاً ماز) از
   کاراکتر یونیکد MINUS SIGN («−», U+2212) استفاده می‌کند. بنابراین صرفاً hyphen
   ASCII را به‌عنوان نشانه‌ی سؤال در نظر می‌گیریم؛ این به‌تنهایی بخش بزرگی از
   مقادیر منفیِ گزینه‌ها را فیلتر می‌کند.

3) در برخی دفترچه‌ها (قلم‌چی)، عدد گزینه‌ی چندگزینه‌ای بلافاصله بعد از مقدار
   می‌آید: «-2 (4» یعنی «گزینه‌ی ۴: مقدار −۲». چنین الگویی را که بلافاصله با
   پرانتز و یک رقم دنبال شده باشد، به‌عنوان نشانه‌ی سؤال نمی‌پذیریم.

4) شماره‌ی سؤال‌ها باید به‌ترتیب صعودی و در محدوده‌ی [1, تعداد سؤال] ظاهر شوند؛
   یک اسکن حریصانه (greedy) با تحمل جهش کوچک (حداکثر ۲ شماره‌ی جاافتاده، مثلاً به
   خاطر باگ افتادن گلیف یک رقم خاص در فونت) انجام می‌شود تا از جهش‌های بزرگ و
   نادرست (که می‌تواند ناشی از نویز باشد) جلوگیری شود.

5) اگر پوشش (تعداد سؤال‌های پیدا‌شده نسبت به کل) خیلی کم بود، تشخیص خودکار را رد
   می‌کنیم تا main.py به نگاشت دستی (خطی) سقوط کند.
"""
import re
from typing import Dict, Tuple

try:
    import pdfplumber
except ImportError:  # pragma: no cover - در محیط استقرار همیشه نصب است (requirements.txt)
    pdfplumber = None


# فاصله‌ی مجاز برای «جاافتادگی» شماره‌سؤال (مثلاً به‌خاطر باگ فونت که یک رقم خاص را
# می‌اندازد). بزرگ‌تر از این مقدار به‌عنوان نویز/جهش نامعتبر رد می‌شود.
_MAX_GAP = 2

# حداقل نسبت پوشش (سؤال‌های پیداشده / کل سؤال‌ها) برای این‌که تشخیص خودکار
# «قابل‌اعتماد» در نظر گرفته شود.
_MIN_COVERAGE_RATIO = 0.5

# جدول تبدیل ارقام فارسی/عربی به ارقام لاتین
_DIGIT_MAP = {}
for _i, _ch in enumerate("۰۱۲۳۴۵۶۷۸۹"):  # ارقام فارسی
    _DIGIT_MAP[_ch] = str(_i)
for _i, _ch in enumerate("٠١٢٣٤٥٦٧٨٩"):  # ارقام عربی (Arabic-Indic)
    _DIGIT_MAP[_ch] = str(_i)

# نشانه‌ی سؤال: خط‌تیره‌ی ASCII + عدد ۱ تا ۳ رقمی (یا برعکس: عدد + خط‌تیره)،
# با یا بدون فاصله بین آن‌ها. هم‌زمان مطمئن می‌شویم عدد بخشی از یک عدد بزرگ‌تر نیست.
_MARKER_RE = re.compile(
    r"(?<!\d)-\s?(\d{1,3})(?!\d)"   # -12  یا  - 12
    r"|"
    r"(?<!\d)(\d{1,3})\s?-(?!\d)"   # 12-  یا  12 -
)

# اگر بلافاصله بعد از عدد (با نادیده گرفتن فاصله‌ی خالی) یک پرانتز و رقم بیاید،
# این احتمالاً برچسب گزینه‌ی چندگزینه‌ای است («-2 (4») نه نشانه‌ی سؤال.
_OPTION_LABEL_AFTER_RE = re.compile(r"^\s?\(\s?\d")
# و به همین ترتیب برای حالت برعکس (اگر بلافاصله قبل از عدد یک ")رقم" آمده باشد).
_OPTION_LABEL_BEFORE_RE = re.compile(r"\d\s?\)\s?$")


def _normalize_digits(text: str) -> str:
    """ارقام فارسی/عربی را به ارقام لاتین تبدیل می‌کند تا الگوی جست‌وجو ساده بماند."""
    if not text:
        return text
    return "".join(_DIGIT_MAP.get(ch, ch) for ch in text)


# در دفترچه‌هایی که فونت فارسیِ آن‌ها فاقد جدول ToUnicode است (خیلی رایج در
# دفترچه‌های قلم‌چی/کانون)، pdfplumber به‌جای گلیف واقعی، متن خام‌ "(cid:NNN)"
# تولید می‌کند. این نویز هیچ اطلاعات مفیدی ندارد و چون خودش شامل الگوی
# «رقم + پرانتز» است می‌تواند فیلترهای تشخیص برچسب گزینه را گول بزند؛ پس قبل از
# هر پردازشی حذفش می‌کنیم.
_CID_NOISE_RE = re.compile(r"\(cid:\d+\)")


def _strip_cid_noise(text: str) -> str:
    return _CID_NOISE_RE.sub(" ", text)


def get_page_count(pdf_path: str) -> int:
    """تعداد صفحات PDF را برمی‌گرداند؛ در صورت خطا صفر."""
    if pdfplumber is None:
        return 0
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0


def _extract_candidates(pdf) -> list:
    """برای هر صفحه، فهرست (شماره‌ی صفحه، عدد پیدا‌شده) را به ترتیب ظهور در متن
    برمی‌گرداند."""
    candidates = []
    for page_index, page in enumerate(pdf.pages):
        page_number = page_index + 1
        try:
            text = page.extract_text() or ""
        except Exception:
            continue
        text = _strip_cid_noise(_normalize_digits(text))

        for m in _MARKER_RE.finditer(text):
            num_str = m.group(1) or m.group(2)
            if not num_str:
                continue

            # رد کردن الگوهایی که در واقع برچسب گزینه‌ی چندگزینه‌ای هستند
            # («-2 (4» یا «(4) 2-»).
            after = text[m.end():m.end() + 4]
            before = text[max(0, m.start() - 4):m.start()]
            if _OPTION_LABEL_AFTER_RE.match(after) or _OPTION_LABEL_BEFORE_RE.search(before):
                continue

            try:
                number = int(num_str)
            except ValueError:
                continue
            if number <= 0:
                continue

            candidates.append((page_number, m.start(), number))
    return candidates


def detect_question_page_map(pdf_path: str, expected_question_count: int) -> Tuple[Dict[int, int], int]:
    """تلاش می‌کند نگاشت «شماره‌سؤال -> صفحه» را از روی متن PDF تشخیص دهد.

    خروجی: (auto_map, page_count)
    auto_map دیکشنری خالی است اگر تشخیص خودکار به اندازه‌ی کافی مطمئن نبود؛ در این
    صورت main.py به نگاشت دستی (خطی) سقوط می‌کند.
    """
    if pdfplumber is None or not pdf_path:
        return {}, 0

    expected_question_count = max(1, int(expected_question_count or 1))

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            candidates = _extract_candidates(pdf)
    except Exception:
        return {}, 0

    # اسکن حریصانه: به ترتیب (صفحه، موقعیت در متن)، فقط اعدادی را می‌پذیریم که
    # شماره‌ی بعدیِ منتظرمانده (یا با فاصله‌ی کم بعد از آن، برای جبران جاافتادگی
    # احتمالی یک شماره به‌خاطر باگ فونت) باشند.
    result: Dict[int, int] = {}
    next_expected = 1
    for page_number, _pos, number in candidates:
        if next_expected > expected_question_count:
            break
        if number < next_expected:
            continue  # قبلاً از این شماره گذشته‌ایم یا نویز است
        if number > next_expected + _MAX_GAP:
            continue  # جهش خیلی بزرگ؛ احتمالاً نویز است، رد می‌شود
        if number > expected_question_count:
            continue
        if number in result:
            continue
        result[number] = page_number
        next_expected = number + 1

    min_required = max(1, -(-expected_question_count // 2))  # ceil(count/2) با ratio=0.5
    min_required = max(min_required, int(expected_question_count * _MIN_COVERAGE_RATIO))
    if len(result) < min_required:
        return {}, page_count

    return result, page_count


def fill_gaps_in_map(auto_map: Dict[int, int], question_count: int) -> Dict[int, int]:
    """نگاشت جزئی auto_map را برای همه‌ی سؤال‌های ۱ تا question_count کامل می‌کند؛
    شماره‌سؤال‌های جاافتاده بین دو «لنگر» شناخته‌شده، به‌نسبت (proportional) صفحه‌بندی
    می‌شوند، و قبل از اولین/بعد از آخرین لنگر با نزدیک‌ترین لنگر پر می‌شوند."""
    question_count = max(1, int(question_count or 1))
    if not auto_map:
        return {}

    known = sorted((int(k), int(v)) for k, v in auto_map.items() if 1 <= int(k) <= question_count)
    if not known:
        return {}

    result: Dict[int, int] = {}
    for q in range(1, question_count + 1):
        # اگر خودش لنگر شناخته‌شده است
        exact = next((p for k, p in known if k == q), None)
        if exact is not None:
            result[q] = exact
            continue

        lower = None  # (k, page) نزدیک‌ترین لنگر کوچک‌تر
        upper = None  # (k, page) نزدیک‌ترین لنگر بزرگ‌تر
        for k, p in known:
            if k < q:
                lower = (k, p)
            elif k > q and upper is None:
                upper = (k, p)

        if lower is not None and upper is not None:
            qa, pa = lower
            qb, pb = upper
            if qb == qa:
                page = pa
            else:
                frac = (q - qa) / (qb - qa)
                page = round(pa + frac * (pb - pa))
        elif lower is not None:
            page = lower[1]
        elif upper is not None:
            page = upper[1]
        else:
            page = 1

        result[q] = max(1, int(page))

    return result


def build_linear_map(question_count: int, start_page: int, end_page: int) -> Dict[int, int]:
    """نگاشت خطی (proportional) بین صفحه‌ی شروع سؤال ۱ و صفحه‌ی سؤال آخر می‌سازد؛
    برای زمانی که تشخیص خودکار جواب نداده و کاربر دو نقطه‌ی دستی داده است."""
    question_count = max(1, int(question_count or 1))
    start_page = max(1, int(start_page or 1))
    end_page = max(start_page, int(end_page or start_page))

    result: Dict[int, int] = {}
    if question_count == 1:
        result[1] = start_page
        return result

    span = end_page - start_page
    for i in range(question_count):
        q = i + 1
        frac = i / (question_count - 1)
        page = start_page + round(frac * span)
        result[q] = max(start_page, min(end_page, int(page)))

    return result
