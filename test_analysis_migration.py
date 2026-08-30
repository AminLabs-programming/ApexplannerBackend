# -*- coding: utf-8 -*-
"""
تست ایمنیِ migration بانک تحلیل.

برخلاف test_analysis_bank.py (که همیشه روی یک دیتابیس *تازه* اجرا می‌شه، یعنی
مسیر ALTER TABLE داخل `_run_lightweight_migrations` را عملاً تمرین نمی‌کنه، چون
create_all از ابتدا schema جدید رو می‌سازه)، این فایل یک دیتابیس *واقعاً قدیمی*
(دقیقاً با شکل جدول‌های قبل از افزوده‌شدن grade/subject_code/answer_status، با
sqlite3 خام و از صفر، بدون هیچ وابستگی بیرونی) می‌سازه و بررسی می‌کنه:

  ۱. بعد از init_db() جدید، ستون‌های تازه واقعاً اضافه شدن.
  ۲. answer_status برای رکوردهای قدیمی درست از is_correct backfill شده
     (True->correct, False->incorrect, None->unanswered).
  ۳. grade و subject_code برای رکوردهای قدیمی خالی/نامشخص می‌مونن (نه حدس زده
     می‌شن) — دقیقاً طبق دستور «مقادیر جدید را برای داده‌های قدیمی به شکل منطقی
     تعیین کن، داده‌های قبلی را خراب نکن».
  ۴. هیچ داده‌ی قدیمی‌ای (subject متن آزاد، title، overall_note، ...) دست‌خورده
     یا گم نشده.
  ۵. بعد از migration، endpointهای واقعی (از طریق TestClient) هنوز روی همین
     رکوردهای قدیمی درست کار می‌کنن (خواندن/فیلتر/آپدیت).

این تست کاملاً خودکفاست و هر بار از صفر دیتابیسِ قدیمیِ خودش رو می‌سازه، پس
هر چند بار که بخوای می‌تونی اجراش کنی (بدون وابستگی به اجرای قبلیِ خودش).

اجرا: python3 test_analysis_migration.py
"""
import os
import sys
import sqlite3
from datetime import datetime

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
LEGACY_DB_PATH = os.path.join(TEST_DIR, "test_legacy_prod_sim.db")

sys.path.insert(0, ".")
os.environ["DATABASE_URL"] = f"sqlite:///{LEGACY_DB_PATH}"
os.environ["JWT_SECRET"] = "test-secret-migration"
os.environ["BOT_API_KEY"] = "test-bot-key-migration"

fails = 0
total = 0


def check(name, cond, extra=""):
    global fails, total
    total += 1
    status = "OK" if cond else "FAIL"
    if not cond:
        fails += 1
    print(f"[{status}] {name}" + (f" — {extra}" if extra else ""))


print("=" * 70)
print("ساخت یک دیتابیسِ کاملاً تازه، سپس برگردوندنِ دستیِ دو جدولِ بانک تحلیل")
print("به شکل *قدیمی*شون (پیش از grade/subject_code/answer_status) — بدون هیچ")
print("وابستگی بیرونی، تا این تست از صفر تا صد قابل‌تکرار باشه.")
print("=" * 70)
if os.path.exists(LEGACY_DB_PATH):
    os.remove(LEGACY_DB_PATH)

# قدم ۱: می‌ذاریم خودِ اپِ فعلی (جدید) همه‌ی جدول‌ها رو با شکل درست و کامل
# بسازه (از جمله users، که ستون‌های زیادی داره و دستی نگه‌داشتنش شکننده‌ست).
# آزمون‌ها و نوت‌ها هم همین‌جا با شکل *جدید* ساخته می‌شن؛ در قدم بعد این دو
# جدول رو عمداً drop و با شکل قدیمی از نو می‌سازیم.
from app.database import init_db as _init_db_for_setup  # noqa: E402
_init_db_for_setup()

con = sqlite3.connect(LEGACY_DB_PATH)
cur = con.cursor()

# قدم ۲: دو جدول بانک تحلیل رو drop و با شکل *قدیمی* (بدون ستون‌های تازه) می‌سازیم
cur.execute("DROP TABLE analysis_question_notes")
cur.execute("DROP TABLE analysis_exams")

cur.execute("""
CREATE TABLE analysis_exams (
    id VARCHAR(32) PRIMARY KEY,
    owner_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    date VARCHAR(10),
    pdf_filename VARCHAR(64),
    original_filename VARCHAR(255),
    page_count INTEGER,
    question_count INTEGER,
    question_page_map_json TEXT,
    mapping_method VARCHAR(16),
    manual_start_page INTEGER,
    manual_end_page INTEGER,
    overall_note TEXT,
    created_at TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE analysis_question_notes (
    id VARCHAR(32) PRIMARY KEY,
    exam_id VARCHAR(32) NOT NULL,
    question_number INTEGER NOT NULL,
    subject VARCHAR(64),
    note TEXT,
    is_correct BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
""")

# قدم ۳: کاربر قدیمی + یک آزمون قدیمی + سه نوتِ قدیمی (سه حالت is_correct)
from app import auth as _auth  # noqa: E402  (فقط برای هش واقعی رمز عبور کاربر قدیمی)
password_hash = _auth.hash_password("OldPass123")
cur.execute(
    "INSERT INTO users (username, password_hash, display_name, role, is_banned, goal_hours_per_day, created_at) VALUES (?,?,?,?,?,?,?)",
    ("legacy_user", password_hash, "کاربر قدیمی", "member", 0, 4, datetime(2025, 1, 1).isoformat()),
)
user_id = cur.lastrowid

exam_id = "xlegacyexam000001"
cur.execute(
    """INSERT INTO analysis_exams
       (id, owner_id, title, date, pdf_filename, original_filename, page_count, question_count,
        question_page_map_json, mapping_method, overall_note, created_at)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
    (exam_id, user_id, "آزمون قدیمی قبل از آپدیت", "1404/02/15", "legacy.pdf", "آزمون قدیمی.pdf",
     3, 3, '{"1": 1, "2": 2, "3": 3}', "manual", "یادداشت کلی قدیمی", datetime(2025, 5, 10, 12, 0, 0).isoformat()),
)

legacy_notes = [
    ("xlegacynote01", exam_id, 1, "ریاضی", "یادداشت قدیمی درست", 1, datetime(2025, 5, 10, 12, 1).isoformat()),
    ("xlegacynote02", exam_id, 2, "فیزیک فصل دو", "یادداشت قدیمی غلط", 0, datetime(2025, 5, 10, 12, 2).isoformat()),
    ("xlegacynote03", exam_id, 3, "", "", None, datetime(2025, 5, 10, 12, 3).isoformat()),
]
for nid, eid, qn, subj, note, is_correct, ts in legacy_notes:
    cur.execute(
        "INSERT INTO analysis_question_notes (id, exam_id, question_number, subject, note, is_correct, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (nid, eid, qn, subj, note, is_correct, ts, ts),
    )
con.commit()
con.close()
print(f"دیتابیس قدیمیِ شبیه‌سازی‌شده ساخته شد: {LEGACY_DB_PATH}")


print("=" * 70)
print("قبل از migration: خواندن مستقیمِ رکوردهای قدیمی از دیتابیس (baseline)")
print("=" * 70)
con = sqlite3.connect(LEGACY_DB_PATH)
con.row_factory = sqlite3.Row
cur = con.cursor()
cur.execute("SELECT * FROM analysis_exams")
exams_before = [dict(r) for r in cur.fetchall()]
cur.execute("SELECT * FROM analysis_question_notes ORDER BY question_number")
notes_before = [dict(r) for r in cur.fetchall()]
con.close()

check("دقیقاً ۱ آزمون قدیمی قبل از migration وجود داره", len(exams_before) == 1, str(len(exams_before)))
check("دقیقاً ۳ نوت قدیمی قبل از migration وجود داره", len(notes_before) == 3, str(len(notes_before)))
check("ستون grade هنوز در جدول قدیمی وجود نداره (baseline درست ساخته شده)", "grade" not in exams_before[0])
check("ستون answer_status هنوز در جدول قدیمی وجود نداره (baseline درست ساخته شده)", "answer_status" not in notes_before[0])


print("\n" + "=" * 70)
print("اجرای init_db() جدید روی همین فایل (باید ALTER TABLE اجرا بشه)")
print("=" * 70)
from app.database import init_db  # noqa: E402
init_db()
print("init_db() کامل شد.")


print("\n" + "=" * 70)
print("بعد از migration: بررسی مستقیمِ schema و داده‌ها")
print("=" * 70)
con = sqlite3.connect(LEGACY_DB_PATH)
con.row_factory = sqlite3.Row
cur = con.cursor()

cur.execute("PRAGMA table_info(analysis_exams)")
exam_cols = {r["name"] for r in cur.fetchall()}
check("ستون grade به analysis_exams اضافه شد", "grade" in exam_cols, str(exam_cols))

cur.execute("PRAGMA table_info(analysis_question_notes)")
note_cols = {r["name"] for r in cur.fetchall()}
check("ستون subject_code به analysis_question_notes اضافه شد", "subject_code" in note_cols)
check("ستون answer_status به analysis_question_notes اضافه شد", "answer_status" in note_cols)

cur.execute("SELECT * FROM analysis_exams")
exams_after = [dict(r) for r in cur.fetchall()]
check("بعد از migration هنوز دقیقاً ۱ آزمون هست (چیزی گم/تکراری نشده)", len(exams_after) == 1, str(len(exams_after)))
e = exams_after[0]
check("grade آزمون قدیمی NULL است (حدس زده نشده، طبق دستور صریح کار)", e["grade"] is None, str(e["grade"]))
check("title آزمون قدیمی دست‌نخورده مونده", e["title"] == "آزمون قدیمی قبل از آپدیت", e["title"])
check("overall_note آزمون قدیمی دست‌نخورده مونده", e["overall_note"] == "یادداشت کلی قدیمی", e["overall_note"])
check("question_page_map_json آزمون قدیمی دست‌نخورده مونده", e["question_page_map_json"] == '{"1": 1, "2": 2, "3": 3}', e["question_page_map_json"])
check("mapping_method آزمون قدیمی دست‌نخورده مونده (manual)", e["mapping_method"] == "manual", e["mapping_method"])

cur.execute("SELECT * FROM analysis_question_notes ORDER BY question_number")
notes_after = [dict(r) for r in cur.fetchall()]
check("بعد از migration هنوز دقیقاً ۳ نوت هست", len(notes_after) == 3, str(len(notes_after)))

n1, n2, n3 = notes_after
check("نوتِ ۱ (is_correct=True قدیمی) -> answer_status='correct'", n1["answer_status"] == "correct", str(n1["answer_status"]))
check("نوتِ ۱: subject قدیمیِ آزاد («ریاضی») دست‌نخورده مونده", n1["subject"] == "ریاضی", n1["subject"])
check("نوتِ ۱: subject_code جدید خالی/NULL است (حدس زده نشده)", not n1["subject_code"], repr(n1["subject_code"]))
check("نوتِ ۱: is_correct قدیمی همچنان True است (دست‌نخورده)", bool(n1["is_correct"]) is True)

check("نوتِ ۲ (is_correct=False قدیمی) -> answer_status='incorrect'", n2["answer_status"] == "incorrect", str(n2["answer_status"]))
check("نوتِ ۲: subject قدیمیِ آزاد («فیزیک فصل دو») دست‌نخورده مونده", n2["subject"] == "فیزیک فصل دو", n2["subject"])
check("نوتِ ۲: note متنِ قدیمی دست‌نخورده مونده", n2["note"] == "یادداشت قدیمی غلط", n2["note"])

check("نوتِ ۳ (is_correct=NULL قدیمی) -> answer_status='unanswered'", n3["answer_status"] == "unanswered", str(n3["answer_status"]))
check("نوتِ ۳: is_correct قدیمی همچنان NULL است (دست‌نخورده)", n3["is_correct"] is None)

con.close()


print("\n" + "=" * 70)
print("بعد از migration: کارکردِ endpointهای واقعی روی این رکوردهای مهاجرت‌شده")
print("=" * 70)
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
login_r = client.post("/auth/login", json={"username": "legacy_user", "password": "OldPass123"})
check("لاگین با کاربر قدیمی (که قبل از تغییرات ساخته شده بود) موفقه", login_r.status_code == 200, login_r.text[:200])
headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}

r = client.get("/analysis-exams", headers=headers)
check("GET /analysis-exams برای کاربر قدیمی موفقه", r.status_code == 200)
listed = r.json()
check("آزمون قدیمی در لیست دیده می‌شه", len(listed) == 1 and listed[0]["title"] == "آزمون قدیمی قبل از آپدیت")
check("grade_label آزمون قدیمی در پاسخ API خالیه (نه یک مقدار جعلی)", listed[0]["grade_label"] == "", repr(listed[0]["grade_label"]))

exam_id = listed[0]["id"]
r = client.get(f"/analysis-exams/{exam_id}", headers=headers)
detail = r.json()
check("GET جزئیات آزمون قدیمی موفقه و ۳ نوت داره", len(detail.get("notes", [])) == 3)
note1 = next(n for n in detail["notes"] if n["question_number"] == 1)
check("نوتِ ۱ از API هم answer_status='correct' نشون می‌ده", note1["answer_status"] == "correct")
check("نوتِ ۱ از API هم subject_label قدیمی (fallback به متن آزاد) نشون می‌ده", note1["subject_label"] == "ریاضی", note1["subject_label"])

# حالا آزمون قدیمی رو ویرایش می‌کنیم: پایه‌ش رو مشخص می‌کنیم (سناریوی واقعی: کاربر
# بعد از آپدیت اپ، برمی‌گرده و پایه‌ی آزمون‌های قدیمیش رو دستی تنظیم می‌کنه)
r = client.patch(f"/analysis-exams/{exam_id}", json={"grade": 12}, headers=headers)
check("کاربر می‌تونه دستی grade رو برای آزمون قدیمی تنظیم کنه", r.status_code == 200 and r.json()["grade"] == 12)

# و می‌تونه یکی از نوت‌های قدیمی رو با دسته‌بندیِ جدید ساختاریافته آپدیت کنه، بدون
# اینکه نوت‌های دیگه دست‌نخورده بمونن
r = client.post(f"/analysis-exams/{exam_id}/notes", json={"question_number": 3, "subject_code": "chemistry2", "answer_status": "incorrect"}, headers=headers)
check("آپدیت نوت قدیمیِ شماره ۳ با دسته‌بندی جدید موفقه", r.status_code == 200 and r.json()["category"] == "chemistry")

r = client.get(f"/analysis-exams/{exam_id}", headers=headers)
notes_final = {n["question_number"]: n for n in r.json()["notes"]}
check("نوتِ ۱ و ۲ (که دست نخوردن) هنوز مقادیر قدیمی‌شون رو دارن", notes_final[1]["subject"] == "ریاضی" and notes_final[2]["subject"] == "فیزیک فصل دو")
check("نوتِ ۳ حالا دسته‌بندی جدید داره ولی همچنان همون رکورده", notes_final[3]["subject_code"] == "chemistry2")

r = client.get("/analysis-notes", params={"grade": 12, "category": "chemistry", "subject": "chemistry2", "status": "incorrect"}, headers=headers)
rows = r.json()
check("فیلتر ترکیبی روی داده‌ی مهاجرت‌شده هم درست کار می‌کنه", len(rows) == 1 and rows[0]["exam_id"] == exam_id, str(rows))


print("\n" + "=" * 70)
print(f"نتیجه: {total - fails}/{total} تست موفق ({fails} شکست)")
print("=" * 70)
sys.exit(1 if fails else 0)
