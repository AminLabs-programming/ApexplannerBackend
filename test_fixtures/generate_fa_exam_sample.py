# -*- coding: utf-8 -*-
"""
تولید یک PDF فارسیِ واقع‌نمای «دفترچه‌ی آزمون» برای تست بانک تحلیل.
هر سؤال دقیقاً با الگوی «-N» (که analysis_pdf.py دنبالش می‌گرده) شروع می‌شه،
و طیف کاملی از سناریوهای فارسی/RTL که در مرحله‌ی ۱۲ سندِ کار خواسته شده رو
پوشش می‌ده: متن ساده، عدد فارسی/انگلیسی، فرمول، ترکیب با انگلیسی، چندخطی،
طولانی، گزینه‌های فارسی و گزینه‌های دارای عدد/نماد.
"""
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

FONT_PATH = "/home/claude/work/fonts/Vazirmatn-Regular.ttf"
pdfmetrics.registerFont(TTFont("Vazirmatn", FONT_PATH))

PAGE_W, PAGE_H = A4
RIGHT_MARGIN = PAGE_W - 50
LEFT_MARGIN = 50


def rtl(text: str) -> str:
    """متن منطقی فارسی -> ترتیب دیداری (shaping + bidi) برای رسم صحیح در reportlab."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def draw_rtl_line(c, text, y, size=13, font="Vazirmatn"):
    c.setFont(font, size)
    c.drawRightString(RIGHT_MARGIN, y, rtl(text))


def draw_ltr_marker(c, text, y, size=13, font="Helvetica-Bold"):
    # نشانه‌ی سؤال ("-1" و مثل آن) عمداً با فونت/جهت لاتین ساده رسم می‌شه،
    # دقیقاً مثل خیلی از دفترچه‌های واقعی که شماره‌ی سؤال چاپی لاتینه.
    c.setFont(font, size)
    c.drawString(LEFT_MARGIN, y, text)


questions = [
    # (marker, [lines], [options] or None)
    ("-1", ["سؤال فارسی ساده: پایتخت ایران کدام شهر است؟"],
     ["تهران", "اصفهان", "شیراز", "مشهد"]),

    ("-2", ["اگر عدد 25 را به توان 2 برسانیم، حاصل چند رقمی می‌شود؟ (عدد انگلیسی)"],
     ["2 رقمی", "3 رقمی", "4 رقمی", "5 رقمی"]),

    ("-3", ["حاصل جمع ۱۲۳۴ و ۵۶۷۸ کدام است؟ (عدد فارسی)"],
     ["۶۹۱۲", "۷۹۱۲", "۶۸۱۲", "۷۸۱۲"]),

    ("-4", ["اگر f(x) = 2x\u00b2 + 3x \u2212 5 باشد، مقدار f(2) کدام است؟ (فرمول ریاضی)"],
     ["9", "11", "13", "\u221217"]),

    ("-5", ["کدام گزینه معادل صحیح Photosynthesis در زیست‌شناسی است؟ (ترکیب با انگلیسی)"],
     ["فتوسنتز", "تنفس سلولی", "اسمز", "تعریق"]),

    ("-6", [
        "این یک سؤال چندخطی و نسبتاً طولانی است که باید در چند سطر جداگانه",
        "روی صفحه‌ی PDF چاپ شود تا رفتار متن چندخطیِ راست‌به‌چپ و شکستن خط",
        "را به‌درستی بررسی کنیم؛ ترکیب فارسی، اعداد ۱۲۳ و کلمات انگلیسی test",
        "همگی باید بدون جابه‌جاییِ نادرست ترتیب حروف نمایش داده شوند.",
    ], ["گزینه‌ی (۱) با نماد٪", "گزینه‌ی (۲) با نماد ±", "گزینه‌ی (۳): 3.14", "گزینه‌ی (۴): −7.5"]),

    ("-7", ["علامت نگارشی: آیا این جمله با «گیومه»، ویرگول، و علامت سؤال؟ بله!"],
     None),
]

c = canvas.Canvas("/home/claude/work/fixtures_fa_exam.pdf", pagesize=A4)

# --- صفحه‌ی ۱: توضیحات کلی آزمون (بدون نشانه‌ی سؤال) ---
draw_rtl_line(c, "آزمون جامع شماره ۳ — پایه‌ی دوازدهم — کانون فرهنگی آموزش", PAGE_H - 60, size=15)
draw_rtl_line(c, "زمان پاسخ‌گویی: ۹۰ دقیقه — تعداد سؤالات: ۷", PAGE_H - 90, size=12)
c.showPage()

# --- صفحات ۲ به بعد: سؤالات (حداکثر ۲ سؤال در هر صفحه، تا نگاشت چندصفحه‌ای
# واقعاً تست بشه، نه اینکه همه‌ی سؤال‌ها تصادفاً روی یک صفحه بیفتن) ---
y = PAGE_H - 70
page_num = 2
q_on_this_page = 0
for marker, lines, options in questions:
    if y < 140 or q_on_this_page >= 2:
        c.showPage()
        y = PAGE_H - 70
        page_num += 1
        q_on_this_page = 0
    q_on_this_page += 1
    draw_ltr_marker(c, marker, y)
    draw_rtl_line(c, lines[0], y)
    y -= 22
    for extra in lines[1:]:
        draw_rtl_line(c, extra, y)
        y -= 22
    if options:
        opt_line = "   ".join(options)
        draw_rtl_line(c, opt_line, y, size=11)
        y -= 22
    y -= 18

c.showPage()
c.save()
print("PDF written.")
