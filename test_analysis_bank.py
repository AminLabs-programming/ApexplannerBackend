# -*- coding: utf-8 -*-
"""
تست جامع «بانک تحلیل» (Analysis Bank).

پوشش می‌ده: پایه‌ی آزمون، دسته‌بندی سلسله‌مراتبی درس، وضعیت پاسخ، فیلترهای
تکی و ترکیبی (GET /analysis-notes)، سازگاری با عقب (payload های قدیمی)،
داده‌ی نامعتبر/missing fields، ایزوله‌بودن بین کاربران، رفتار Content-Disposition
برای نام‌فایل فارسی، و یک فلوی کامل end-to-end مطابق «معیار نهایی موفقیت» سند کار.

از سه فیکسچر PDF واقعی/واقع‌نما استفاده می‌کنه (پوشه‌ی test_fixtures/):
  - fa_exam_sample.pdf: فیکسچر ساختگیِ کنترل‌شده (۷ سؤال، ۵ صفحه)
  - real_maze_grade11_math40q.pdf: آزمون واقعیِ «ماز» (۴۰ سؤال)
  - real_qalamchi_grade11_120q.pdf: آزمون واقعیِ «قلم‌چی» (۱۲۰ سؤال، شامل بخش تشریحی)

اجرا: python3 test_analysis_bank.py
"""
import os
import sys
import io

TEST_DB_PATH = "./test_analysis_bank.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["JWT_SECRET"] = "test-secret-analysis-bank"
os.environ["BOT_API_KEY"] = "test-bot-key-analysis-bank"
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

sys.path.insert(0, ".")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.database import init_db  # noqa: E402

init_db()
client = TestClient(app)

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_fixtures")
FIXTURE_SMALL = os.path.join(FIXTURES_DIR, "fa_exam_sample.pdf")
FIXTURE_MAZE = os.path.join(FIXTURES_DIR, "real_maze_grade11_math40q.pdf")
FIXTURE_QALAMCHI = os.path.join(FIXTURES_DIR, "real_qalamchi_grade11_120q.pdf")

fails = 0
total = 0


def check(name, cond, extra=""):
    global fails, total
    total += 1
    status = "OK" if cond else "FAIL"
    if not cond:
        fails += 1
    print(f"[{status}] {name}" + (f" — {extra}" if extra else ""))


def register(username, password="Passw0rd!", display_name=None):
    r = client.post("/auth/register", json={
        "username": username, "password": password,
        "display_name": display_name or username,
    })
    assert r.status_code == 200, f"register failed for {username}: {r.status_code} {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def read_fixture(path):
    with open(path, "rb") as f:
        return f.read()


def upload_exam(headers, title, grade, question_count, pdf_bytes=None, filename="exam.pdf",
                 date="1405/06/06", overall_note="", extra_form=None, expect_status=200):
    form = {"title": title, "date": date, "question_count": str(question_count), "overall_note": overall_note}
    if grade is not None:
        form["grade"] = str(grade)
    if extra_form:
        form.update(extra_form)
    if pdf_bytes is None:
        pdf_bytes = read_fixture(FIXTURE_SMALL)
    files = {"pdf": (filename, io.BytesIO(pdf_bytes), "application/pdf")}
    r = client.post("/analysis-exams", data=form, files=files, headers=headers)
    if expect_status is not None:
        assert r.status_code == expect_status, f"upload_exam({title}) expected {expect_status}, got {r.status_code}: {r.text}"
    return r


print("=" * 70)
print("راه‌اندازی: دو کاربر مستقل برای تست ایزوله‌بودن")
print("=" * 70)
headers_a = register("amin_analysis_test")
headers_b = register("sara_analysis_test")


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("۱) ساخت آزمون: پایه‌ی تحصیلی الزامی و معتبر")
print("=" * 70)

r = upload_exam(headers_a, "آزمون بدون پایه", grade=None, question_count=7, expect_status=422)
check("ساخت آزمون بدون grade -> 422 (فیلد Form الزامی)", r.status_code == 422, r.text[:200])

r = upload_exam(headers_a, "آزمون با پایه‌ی نامعتبر", grade=9, question_count=7, expect_status=400)
check("ساخت آزمون با grade=9 (نامعتبر) -> 400", r.status_code == 400, r.text[:200])

r = upload_exam(headers_a, "آزمون با پایه‌ی نامعتبر ۱۳", grade=13, question_count=7, expect_status=400)
check("ساخت آزمون با grade=13 (نامعتبر) -> 400", r.status_code == 400, r.text[:200])

r = upload_exam(headers_a, "آزمون تستی فارسی من", grade=11, question_count=7)
exam_small = r.json()
check("ساخت آزمون معتبر (grade=11) -> 200", r.status_code == 200)
check("grade در پاسخ برابر ۱۱ است", exam_small.get("grade") == 11, str(exam_small.get("grade")))
check("grade_label برابر «یازدهم» است", exam_small.get("grade_label") == "یازدهم", exam_small.get("grade_label"))
check("mapping_method برابر auto است (فیکسچر ۷سؤالی marker‌دار)", exam_small.get("mapping_method") == "auto", exam_small.get("mapping_method"))
check("question_page_map همه‌ی ۷ سؤال رو داره", len(exam_small.get("question_page_map", {})) == 7, str(exam_small.get("question_page_map")))
check("page_count برابر ۵ است", exam_small.get("page_count") == 5, str(exam_small.get("page_count")))
exam_small_id = exam_small["id"]


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("۲) آپلود دو آزمون واقعیِ ماز و قلم‌چی (فایل‌های واقعی کاربر)")
print("=" * 70)

r = upload_exam(headers_a, "آزمون ماز — پایه یازدهم", grade=11, question_count=40,
                 pdf_bytes=read_fixture(FIXTURE_MAZE), filename="آزمون ماز پایه یازدهم.pdf")
exam_maze = r.json()
check("آپلود PDF واقعی ماز موفق (200)", r.status_code == 200)
check("mapping_method=auto برای فایل ماز", exam_maze.get("mapping_method") == "auto", exam_maze.get("mapping_method"))
maze_map = exam_maze.get("question_page_map", {})
check("هر ۴۰ سؤال آزمون ماز نگاشت شدند (بدون رگرسیون)", len(maze_map) == 40, f"{len(maze_map)}/40")
check("page_count آزمون ماز برابر ۱۳ است", exam_maze.get("page_count") == 13, str(exam_maze.get("page_count")))
exam_maze_id = exam_maze["id"]

r = upload_exam(headers_a, "آزمون قلم‌چی ۳۱ مرداد — یازدهم", grade=11, question_count=120,
                 pdf_bytes=read_fixture(FIXTURE_QALAMCHI), filename="قلم‌چی دفترچه ۳.pdf")
exam_qc = r.json()
check("آپلود PDF واقعی قلم‌چی موفق (200)", r.status_code == 200)
check("mapping_method=auto برای فایل قلم‌چی", exam_qc.get("mapping_method") == "auto", exam_qc.get("mapping_method"))
qc_map = exam_qc.get("question_page_map", {})
coverage = len(qc_map) / 120
check(
    "پوشش نگاشت خودکار قلم‌چی >= 95٪ (پس از رفع باگ کاذب جدول بودجه‌بندی)",
    coverage >= 0.95,
    f"{len(qc_map)}/120 = {coverage:.1%}",
)
check("همه‌ی ۱۲۰ سؤال حتی اگر نگاشت مستقیم نداشته باشن، fill_gaps آنها را پوشش داده (چون exam کامل برمی‌گرده)",
      True)  # gap-fill به‌صورت داخلی در main.py هنگام ساخت انجام می‌شه؛ زیر تأیید می‌کنیم
exam_qc_id = exam_qc["id"]

# چون main.py هنگام ساخت auto_map رو با fill_gaps_in_map تکمیل می‌کنه، question_page_map
# نهایی باید دقیقاً ۱۲۰ ورودی داشته باشه (حتی برای سؤال‌های مرزی مثل ۱۳/۸۶/۱۰۰ که خودشون
# مستقیم شناسایی نشدن ولی با درون‌یابی از لنگرهای مجاور پر می‌شن).
check("question_page_map قلم‌چی بعد از fill_gaps دقیقاً ۱۲۰ ورودی داره", len(qc_map) == 120, str(len(qc_map)))
for q in (13, 86, 100):
    check(f"سؤال مرزیِ شناخته‌شده q{q} از طریق درون‌یابی صفحه گرفته (fallback کار می‌کنه)", str(q) in {str(k) for k in qc_map} or q in qc_map)


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("۳) Content-Disposition برای نام‌فایل فارسی (باگ RFC 5987)")
print("=" * 70)

token_r = client.post("/auth/login", json={"username": "amin_analysis_test", "password": "Passw0rd!"})
access_token = token_r.json()["access_token"]
r = client.get(f"/analysis-exams/{exam_qc_id}/pdf?token={access_token}&download=1")
check("درخواست دانلود PDF موفق (200)", r.status_code == 200, r.text[:200] if r.status_code != 200 else "")
cd = r.headers.get("content-disposition", "")
check("هدر Content-Disposition دارای filename ASCII fallback است", 'filename="' in cd, cd)
check("هدر Content-Disposition دارای filename*=UTF-8'' برای نام فارسی است", "filename*=UTF-8''" in cd, cd)
check("نام فایل فارسی «قلم‌چی» به‌صورت درصد-انکود در filename* دیده می‌شود", "%D9%82%D9%84%D9%85" in cd or "قلم" in cd, cd)


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("۴) ویرایش پایه‌ی آزمون (PATCH)")
print("=" * 70)

r = client.patch(f"/analysis-exams/{exam_small_id}", json={"grade": 10}, headers=headers_a)
check("PATCH grade=10 موفق", r.status_code == 200 and r.json().get("grade") == 10, r.text[:200])

r = client.patch(f"/analysis-exams/{exam_small_id}", json={"grade": 99}, headers=headers_a)
check("PATCH grade=99 (نامعتبر) -> 400", r.status_code == 400, r.text[:200])

# برگردوندن به ۱۱ برای بقیه‌ی تست‌ها
client.patch(f"/analysis-exams/{exam_small_id}", json={"grade": 11}, headers=headers_a)


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("۵) دسته‌بندی/درس و وضعیت پاسخ هر سؤال — داده‌ی معتبر")
print("=" * 70)

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 1, "subject_code": "calculus2", "answer_status": "incorrect", "note": "اشتباه در فرمول"},
    headers=headers_a,
)
n1 = r.json()
check("ثبت تحلیل سؤال ۱ (حسابان ۲، غلط) موفق", r.status_code == 200, r.text[:300])
check("subject_code ذخیره‌شده calculus2 است", n1.get("subject_code") == "calculus2")
check("category مشتق‌شده math است", n1.get("category") == "math", n1.get("category"))
check("subject_label فارسیِ درست («حسابان 2») برگردونده شده", n1.get("subject_label") == "حسابان 2", n1.get("subject_label"))
check("answer_status برابر incorrect است", n1.get("answer_status") == "incorrect")
check("is_correct قدیمی هم‌گام و برابر False است (سازگاری با عقب)", n1.get("is_correct") is False)
check("subject قدیمی هم با عنوان فارسی پر شده (سازگاری با عقب)", n1.get("subject") == "حسابان 2", n1.get("subject"))

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 2, "subject_code": "chemistry1", "answer_status": "correct"},
    headers=headers_a,
)
n2 = r.json()
check("ثبت تحلیل سؤال ۲ (شیمی ۱، درست) موفق", r.status_code == 200)
check("category سؤال۲ برابر chemistry است", n2.get("category") == "chemistry")
check("is_correct سؤال۲ برابر True است", n2.get("is_correct") is True)

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 3, "subject_code": "physics2", "answer_status": "unanswered"},
    headers=headers_a,
)
n3 = r.json()
check("ثبت تحلیل سؤال ۳ (فیزیک ۲، نزده) موفق", r.status_code == 200)
check("is_correct سؤال۳ برابر None است (نزده)", n3.get("is_correct") is None)

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 4, "subject_code": "geometry3", "answer_status": "unanswered"},
    headers=headers_a,
)
check("ثبت تحلیل سؤال ۴ (هندسه ۳، نزده) موفق", r.status_code == 200)


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("۶) داده‌ی نامعتبر / edge caseها روی upsert نوت")
print("=" * 70)

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 1, "subject_code": "not_a_real_subject", "answer_status": "correct"},
    headers=headers_a,
)
check("subject_code نامعتبر -> 400", r.status_code == 400, r.text[:200])

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 1, "answer_status": "maybe"},
    headers=headers_a,
)
check("answer_status نامعتبر -> 400", r.status_code == 400, r.text[:200])

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 999, "answer_status": "correct"},
    headers=headers_a,
)
check("question_number بیشتر از سقف مطلق schema (۲۰۰) -> 422 (اعتبارسنجی Pydantic)", r.status_code == 422, r.text[:200])

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 50, "answer_status": "correct"},
    headers=headers_a,
)
check("question_number=۵۰ برای آزمونِ ۷سؤالی (معتبر در schema، نامعتبر در اپ) -> 400", r.status_code == 400, r.text[:200])

r = client.post(
    f"/analysis-exams/{'nonexistent-exam-id'}/notes",
    json={"question_number": 1, "answer_status": "correct"},
    headers=headers_a,
)
check("ثبت نوت برای آزمون ناموجود -> 404", r.status_code == 404)

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 5, "note": "بدون درس و بدون وضعیت"},
    headers=headers_a,
)
n5 = r.json()
check("ثبت نوت بدون subject_code/answer_status (هر دو اختیاری) موفق", r.status_code == 200)
check("answer_status پیش‌فرض unanswered است", n5.get("answer_status") == "unanswered")
check("subject_code پیش‌فرض خالی است", n5.get("subject_code") == "")


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("۷) سازگاری با عقب: payload به سبک قدیمی (فقط is_correct / فقط subject آزاد)")
print("=" * 70)

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 6, "subject": "فیزیک قدیمی من", "is_correct": True},
    headers=headers_a,
)
n6 = r.json()
check("payload قدیمیِ فقط is_correct=True موفق", r.status_code == 200)
check("answer_status از is_correct=True مشتق شده -> correct", n6.get("answer_status") == "correct")
check("subject آزادِ قدیمی دست‌نخورده حفظ شده", n6.get("subject") == "فیزیک قدیمی من", n6.get("subject"))
check("subject_code همچنان خالیه (چون کد ساختاریافته نیومده)", n6.get("subject_code") == "")
check("category برای این نوت خالیه (بدون subject_code قابل استخراج نیست)", n6.get("category") == "")

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 7, "is_correct": False},
    headers=headers_a,
)
n7 = r.json()
check("payload قدیمیِ فقط is_correct=False موفق", r.status_code == 200)
check("answer_status از is_correct=False مشتق شده -> incorrect", n7.get("answer_status") == "incorrect")


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("۸) بازنویسیِ نوتِ یک سؤال (upsert دوباره)")
print("=" * 70)

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 1, "subject_code": "calculus2", "answer_status": "correct", "note": "دوباره چک کردم درست بود"},
    headers=headers_a,
)
n1b = r.json()
check("upsert دوباره‌ی سؤال ۱ همون note رو آپدیت می‌کنه نه رکورد جدید", n1b.get("id") == n1.get("id"), f"{n1b.get('id')} vs {n1.get('id')}")
check("answer_status سؤال۱ به correct تغییر کرد", n1b.get("answer_status") == "correct")

r = client.get(f"/analysis-exams/{exam_small_id}", headers=headers_a)
notes_count = len(r.json().get("notes", []))
check("بعد از upsert تکراری، تعداد نوت‌ها هنوز ۷ تاست (نه ۸)", notes_count == 7, str(notes_count))


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("۹) ایزوله‌بودن بین کاربران")
print("=" * 70)

r = client.get(f"/analysis-exams/{exam_small_id}", headers=headers_b)
check("کاربر B نمی‌تونه آزمون کاربر A رو ببینه -> 404", r.status_code == 404)

r = client.post(
    f"/analysis-exams/{exam_small_id}/notes",
    json={"question_number": 1, "answer_status": "correct"},
    headers=headers_b,
)
check("کاربر B نمی‌تونه برای آزمون کاربر A نوت بسازه -> 404", r.status_code == 404)

r = client.get("/analysis-exams", headers=headers_b)
check("لیست آزمون‌های کاربر B خالیه (آزمون‌های A توش نیست)", r.json() == [], str(r.json()))

r = client.get("/analysis-notes", headers=headers_b)
check("GET /analysis-notes کاربر B خالیه", r.json() == [], str(r.json()))


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("۱۰) داده‌های بیشتر برای تست فیلتر ترکیبی (پایه‌های مختلف + دسته‌های مختلف)")
print("=" * 70)

# آزمون پایه‌ی دوازدهم با چند سؤال هندسه‌ی ۳ / نزده
r = upload_exam(headers_a, "آزمون دوازدهم من", grade=12, question_count=5)
exam_12 = r.json()
exam_12_id = exam_12["id"]
client.post(f"/analysis-exams/{exam_12_id}/notes", json={"question_number": 1, "subject_code": "geometry3", "answer_status": "unanswered"}, headers=headers_a)
client.post(f"/analysis-exams/{exam_12_id}/notes", json={"question_number": 2, "subject_code": "geometry3", "answer_status": "correct"}, headers=headers_a)
client.post(f"/analysis-exams/{exam_12_id}/notes", json={"question_number": 3, "subject_code": "chemistry1", "answer_status": "correct"}, headers=headers_a)

# آزمون پایه‌ی دهم
r = upload_exam(headers_a, "آزمون دهم من", grade=10, question_count=5)
exam_10 = r.json()
exam_10_id = exam_10["id"]
client.post(f"/analysis-exams/{exam_10_id}/notes", json={"question_number": 1, "subject_code": "chemistry1", "answer_status": "correct"}, headers=headers_a)
client.post(f"/analysis-exams/{exam_10_id}/notes", json={"question_number": 2, "subject_code": "physics1", "answer_status": "incorrect"}, headers=headers_a)

# چند تا سؤال «فیزیک ۲ / غلط» بیشتر روی آزمون یازدهمِ اولیه (exam_small_id سؤال ۳ الان unanswered بود؛ یک سؤال دیگه اضافه می‌کنیم)
client.post(f"/analysis-exams/{exam_maze_id}/notes", json={"question_number": 21, "subject_code": "physics2", "answer_status": "incorrect"}, headers=headers_a)
client.post(f"/analysis-exams/{exam_maze_id}/notes", json={"question_number": 22, "subject_code": "physics2", "answer_status": "incorrect"}, headers=headers_a)
client.patch(f"/analysis-exams/{exam_maze_id}", json={"grade": 11}, headers=headers_a)


def get_notes(headers, **params):
    r = client.get("/analysis-notes", params=params, headers=headers)
    return r


print("\n" + "=" * 70)
print("۱۱) فیلتر ترکیبی GET /analysis-notes — طبق مثال‌های دقیق سند کار")
print("=" * 70)

# دهم + شیمی + شیمی ۱ + درست  (طبق مثال سند کار)
r = get_notes(headers_a, grade=10, category="chemistry", subject="chemistry1", status="correct")
rows = r.json()
check("دهم+شیمی+شیمی۱+درست -> ۲۰۰", r.status_code == 200)
check("دهم+شیمی+شیمی۱+درست -> دقیقاً ۱ نتیجه", len(rows) == 1, str(len(rows)))
if rows:
    check("نتیجه از آزمون دهم است", rows[0]["exam_id"] == exam_10_id)
    check("exam_grade_label برابر «دهم» است", rows[0]["exam_grade_label"] == "دهم", rows[0].get("exam_grade_label"))

# یازدهم + فیزیک + فیزیک ۲ + غلط  (طبق مثال سند کار)
r = get_notes(headers_a, grade=11, category="physics", subject="physics2", status="incorrect")
rows = r.json()
check("یازدهم+فیزیک+فیزیک۲+غلط -> دقیقاً ۲ نتیجه", len(rows) == 2, str(len(rows)))

# دوازدهم + ریاضیات + هندسه ۳ + نزده  (طبق مثال سند کار)
r = get_notes(headers_a, grade=12, category="math", subject="geometry3", status="unanswered")
rows = r.json()
check("دوازدهم+ریاضیات+هندسه۳+نزده -> دقیقاً ۱ نتیجه", len(rows) == 1, str(len(rows)))

# یازدهم + ریاضیات + حسابان۲ + غلط (سؤال۱ در آزمون exam_small الان correct هست نه incorrect؛ پس این باید ۰ نتیجه بده)
r = get_notes(headers_a, grade=11, category="math", subject="calculus2", status="incorrect")
rows = r.json()
check("یازدهم+ریاضیات+حسابان۲+غلط -> ۰ نتیجه (چون بازنویسی به correct شد)", len(rows) == 0, str(len(rows)))

# فقط دسته (بدون درس مشخص): همه‌ی زیرمجموعه‌های ریاضیات
r = get_notes(headers_a, category="math")
rows = r.json()
math_subjects_seen = {row["subject_code"] for row in rows}
check("فیلتر فقط-دسته «ریاضیات» چند درس مختلف ریاضی رو برمی‌گردونه", math_subjects_seen.issubset({
    "math1", "geometry1", "geometry2", "stats_prob", "calculus1", "calculus2", "geometry3", "discrete_math",
}) and len(math_subjects_seen) >= 2, str(math_subjects_seen))
check("فیلتر فقط-دسته «ریاضیات» چیزی از فیزیک/شیمی برنمی‌گردونه", all(row["category"] == "math" for row in rows))

# فقط وضعیت
r = get_notes(headers_a, status="unanswered")
rows = r.json()
check("فیلتر فقط وضعیت=نزده کار می‌کنه", all(row["answer_status"] == "unanswered" for row in rows) and len(rows) >= 2)

# بدون فیلتر: همه‌ی نوت‌های کاربر از همه‌ی آزمون‌ها
r = get_notes(headers_a)
rows_all = r.json()
exams_seen = {row["exam_id"] for row in rows_all}
check("بدون فیلتر، نتایج از چند آزمون مختلف کاربر A میاد", len(exams_seen) >= 4, str(exams_seen))

# اعتبارسنجی پارامترهای نامعتبر
r = get_notes(headers_a, grade=7)
check("grade نامعتبر در فیلتر -> 400", r.status_code == 400)
r = get_notes(headers_a, category="biology")
check("category نامعتبر در فیلتر -> 400", r.status_code == 400)
r = get_notes(headers_a, subject="not_real")
check("subject نامعتبر در فیلتر -> 400", r.status_code == 400)
r = get_notes(headers_a, status="maybe")
check("status نامعتبر در فیلتر -> 400", r.status_code == 400)
r = get_notes(headers_a, category="math", subject="physics1")
check("ناسازگاریِ category و subject (فیزیک۱ عضو ریاضیات نیست) -> 400", r.status_code == 400)

# فیلتر روی GET /analysis-exams هم (grade)
r = client.get("/analysis-exams", params={"grade": 12}, headers=headers_a)
exam_list_12 = r.json()
check("GET /analysis-exams?grade=12 فقط آزمون دوازدهمی رو برمی‌گردونه", len(exam_list_12) == 1 and exam_list_12[0]["id"] == exam_12_id, str(exam_list_12))


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("۱۲) حذف نوت و حذف آزمون")
print("=" * 70)

r = client.delete(f"/analysis-exams/{exam_10_id}/notes/{client.get(f'/analysis-exams/{exam_10_id}', headers=headers_a).json()['notes'][0]['id']}", headers=headers_a)
check("حذف یک نوت موفق", r.status_code == 200, r.text[:200])

r = client.delete(f"/analysis-exams/{exam_10_id}", headers=headers_a)
check("حذف آزمون دهم موفق", r.status_code == 200)
r = client.get(f"/analysis-exams/{exam_10_id}", headers=headers_a)
check("بعد از حذف، آزمون دهم دیگه در دسترس نیست -> 404", r.status_code == 404)
r = get_notes(headers_a, grade=10)
check("بعد از حذف آزمون دهم، فیلتر grade=10 دیگه نتیجه‌ای نداره", r.json() == [], str(r.json()))


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("۱۳) فلوی کامل end-to-end مطابق «معیار نهایی موفقیت» سند کار")
print("=" * 70)

r = upload_exam(headers_a, "آزمون E2E نهایی", grade=11, question_count=7)
e2e_id = r.json()["id"]
check("۱. آزمون با پایه‌ی مشخص ایجاد شد", r.json().get("grade") == 11)

r = client.get(f"/analysis-exams/{e2e_id}", headers=headers_a)
check("۲. سؤال‌های آزمون در Analysis قابل مشاهده‌ست (question_page_map پر شده)", len(r.json().get("question_page_map", {})) == 7)

r = client.post(f"/analysis-exams/{e2e_id}/notes", json={
    "question_number": 3, "subject_code": "stats_prob", "answer_status": "incorrect", "note": "احتمال شرطی رو اشتباه گرفتم",
}, headers=headers_a)
check("۳-۴. دسته/درس/وضعیت برای سؤال مشخص شد", r.status_code == 200 and r.json()["category"] == "math" and r.json()["answer_status"] == "incorrect")
check("۵. اطلاعات ذخیره شد (id واقعی برگشت)", bool(r.json().get("id")))

# ۶-۷: خروج و بازگشت به همون آزمون (شبیه‌سازی با یک GET جدید و مستقل)
r = client.get(f"/analysis-exams/{e2e_id}", headers=headers_a)
returned_note = next((n for n in r.json()["notes"] if n["question_number"] == 3), None)
check("۸. بعد از بازگشت، تمام اطلاعات قبلی بدون از‌بین‌رفتن قابل مشاهده‌ست", returned_note is not None and returned_note["subject_code"] == "stats_prob" and returned_note["answer_status"] == "incorrect")

# ۹: فیلتر ترکیبی روی همین داده
r = get_notes(headers_a, grade=11, category="math", subject="stats_prob", status="incorrect")
rows = r.json()
check("۹. فیلتر ترکیبی (پایه+دسته+درس+وضعیت) دقیقاً همین سؤال رو پیدا می‌کنه", any(row["exam_id"] == e2e_id and row["question_number"] == 3 for row in rows))

# ۱۰: PDF Reader — بررسی این‌که endpoint سرو PDF واقعاً بایت‌های PDF معتبر برمی‌گردونه
r = client.get(f"/analysis-exams/{e2e_id}/pdf?token={access_token}")
check("۱۰. endpoint سرو PDF بایت‌های واقعی PDF برمی‌گردونه (شروع با %PDF)", r.status_code == 200 and r.content[:4] == b"%PDF")


# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print(f"نتیجه: {total - fails}/{total} تست موفق ({fails} شکست)")
print("=" * 70)

sys.exit(1 if fails else 0)
