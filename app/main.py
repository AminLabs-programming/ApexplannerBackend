"""
اپکس پلنر — بکند مشترک بین اپ و بات تلگرام.

اجرای محلی برای تست:
    uvicorn app.main:app --reload --port 8000

روی Railway:
    Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    و پلاگین PostgreSQL رو به این سرویس وصل کن (DATABASE_URL خودکار ست می‌شه).
    متغیرهای محیطی لازم: JWT_SECRET ، BOT_API_KEY (هر دو رشته‌ی تصادفی طولانی بساز).
"""
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import models, schemas, auth, notion_sync, analysis_pdf
from .database import get_db, init_db

app = FastAPI(title="Apex Planner API", version="1.0.0")

# ---------------------------------------------------------------------------
# بانک تحلیل: پوشه‌ی ذخیره‌ی PDF آزمون‌ها روی دیسک سرور.
# ⚠️ روی Railway، دیسک سرویس به‌طور پیش‌فرض ephemeral است؛ یعنی با هر
# دیپلوی جدید یا ری‌استارت سرویس، فایل‌های این پوشه از بین می‌رن (چون
# ایمیج کانتینر از نو ساخته می‌شه). برای این‌که فایل‌های آپلودشده همیشگی
# بمونن، باید از Railway Volume استفاده کنی: Settings → Volumes → یک
# Volume جدید بساز و Mount Path رو دقیقاً همون چیزی بذار که در متغیر
# محیطی ANALYSIS_UPLOAD_DIR ست می‌کنی (پیش‌فرض زیر همون‌جا که کد اجرا
# می‌شه). بدون Volume، فقط برای تست محلی/کوتاه‌مدت مناسبه.
ANALYSIS_UPLOAD_DIR = os.environ.get("ANALYSIS_UPLOAD_DIR", os.path.join(os.getcwd(), "uploads", "analysis"))
os.makedirs(ANALYSIS_UPLOAD_DIR, exist_ok=True)
ANALYSIS_MAX_PDF_MB = 30

# CORS: چون اپ (PWA) از یک دامنه‌ی دیگر (GitHub Pages) به این API درخواست می‌زند
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # برای شروع باز؛ بعداً می‌تونی به دامنه‌ی خودت محدودش کنی
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


def new_id() -> str:
    return "x" + uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> models.User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="توکن ارسال نشده")
    token = authorization.split(" ", 1)[1]
    payload = auth.decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="توکن نامعتبر یا منقضی شده")
    user = db.query(models.User).filter(models.User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="کاربر یافت نشد")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="دسترسی شما مسدود شده است")
    return user


def get_current_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="فقط ادمین اجازه دارد")
    return user


def verify_bot_key(x_bot_key: Optional[str] = Header(None)):
    if not x_bot_key or x_bot_key != auth.BOT_API_KEY:
        raise HTTPException(status_code=401, detail="کلید بات نامعتبر است")
    return True


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    # صفحه‌ی خالی روی آدرس اصلی سرویس، فقط برای این‌که وقتی کسی مستقیم
    # https://diplomatic-prosperity-production.up.railway.app/ رو باز می‌کنه
    # به‌جای 404، تأیید بگیره سرویس بالاست. خود اپ (PWA) از این مسیر استفاده
    # نمی‌کنه؛ اپ روی GitHub Pages جداست و فقط درخواست‌های API رو به اینجا می‌زنه.
    return {"service": "Apex Planner API", "status": "ok", "docs": "/docs"}


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.post("/auth/register", response_model=schemas.TokenResponse)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="این نام کاربری قبلاً گرفته شده")

    is_first_user = db.query(models.User).count() == 0
    user = models.User(
        username=payload.username,
        password_hash=auth.hash_password(payload.password),
        display_name=payload.display_name,
        role="admin" if is_first_user else "member",  # اولین کاربر ثبت‌شده خودکار ادمین می‌شود
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = auth.create_access_token(user.id, user.role)
    return schemas.TokenResponse(access_token=token, user=schemas.UserOut.model_validate(user))


@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="دسترسی شما مسدود شده است")
    token = auth.create_access_token(user.id, user.role)
    return schemas.TokenResponse(access_token=token, user=schemas.UserOut.model_validate(user))


@app.get("/auth/me", response_model=schemas.UserOut)
def get_me(user: models.User = Depends(get_current_user)):
    return user


@app.patch("/auth/me", response_model=schemas.UserOut)
def update_me(payload: schemas.UpdateProfileRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.goal_hours_per_day is not None:
        user.goal_hours_per_day = payload.goal_hours_per_day
    if payload.exam_target_label is not None:
        user.exam_target_label = payload.exam_target_label
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Password: change (logged-in) / forgot+reset via Telegram bot / admin reset
# ---------------------------------------------------------------------------
@app.patch("/auth/change-password")
def change_password(payload: schemas.ChangePasswordRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """کاربر لاگین‌شده، رمز فعلی رو تایید می‌کنه و رمز جدید می‌ذاره (سوتیِ رمز)."""
    if not auth.verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="رمز فعلی اشتباه است")
    user.password_hash = auth.hash_password(payload.new_password)
    # کد بازیابی احتمالاً معلق رو هم باطل کن، چون رمز عوض شد
    user.password_reset_code = None
    user.password_reset_expires = None
    db.commit()
    return {"message": "رمز عبور با موفقیت تغییر کرد"}


@app.post("/auth/forgot-password", response_model=schemas.ForgotPasswordResponse)
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """قدم اول بازیابی. اگه حساب به بات تلگرام وصل باشه (telegram_chat_id ست شده)،
    یک کد ۶ رقمی به همون چت فرستاده می‌شه. اگه وصل نباشه، کاربر راهنمایی می‌شه که
    از ادمین بخواد رمزش رو ریست کنه — SMS یا ایمیل در کار نیست."""
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    # برای جلوگیری از فاش‌شدن اینکه یوزرنیم وجود داره یا نه، پیام یکسان برمی‌گردونیم
    generic_not_linked_msg = (
        "این حساب به بات تلگرام وصل نیست، پس نمی‌تونیم کد رو خودکار بفرستیم. "
        "از ادمین بخواه از پنل مدیریت رمزت رو ریست کنه."
    )
    if not user:
        return schemas.ForgotPasswordResponse(telegram_linked=False, message=generic_not_linked_msg)

    if not user.telegram_chat_id:
        return schemas.ForgotPasswordResponse(telegram_linked=False, message=generic_not_linked_msg)

    code = auth.generate_reset_code()
    user.password_reset_code = code
    user.password_reset_expires = datetime.utcnow() + timedelta(minutes=auth.RESET_CODE_EXPIRE_MINUTES)
    db.commit()

    sent = auth.send_telegram_message(
        user.telegram_chat_id,
        f"🔐 کد بازیابی رمز عبور اپکس پلنر: {code}\n"
        f"این کد تا {auth.RESET_CODE_EXPIRE_MINUTES} دقیقه معتبره. اگه خودت درخواست ندادی، این پیام رو نادیده بگیر.",
    )
    if not sent:
        # توکن بات ست نشده یا ارسال به هر دلیلی شکست خورد
        raise HTTPException(status_code=503, detail="ارسال کد به تلگرام ممکن نشد. بعداً دوباره امتحان کن یا از ادمین بخواه رمزت رو ریست کنه.")

    return schemas.ForgotPasswordResponse(
        telegram_linked=True,
        message="کد ۶ رقمی به چت تلگرام بات برات فرستاده شد.",
    )


@app.post("/auth/reset-password", response_model=schemas.TokenResponse)
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    """قدم دوم بازیابی: کد + رمز جدید. اگه درست باشه، لاگین هم می‌کنیم (توکن برمی‌گردونیم)."""
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not user.password_reset_code or not user.password_reset_expires:
        raise HTTPException(status_code=400, detail="کد نامعتبر است یا هنوز درخواست بازیابی نزدی")
    if datetime.utcnow() > user.password_reset_expires:
        user.password_reset_code = None
        user.password_reset_expires = None
        db.commit()
        raise HTTPException(status_code=400, detail="کد منقضی شده، دوباره درخواست بده")
    if payload.code.strip() != user.password_reset_code:
        raise HTTPException(status_code=400, detail="کد وارد شده اشتباه است")

    user.password_hash = auth.hash_password(payload.new_password)
    user.password_reset_code = None
    user.password_reset_expires = None
    db.commit()
    db.refresh(user)
    token = auth.create_access_token(user.id, user.role)
    return schemas.TokenResponse(access_token=token, user=schemas.UserOut.model_validate(user))


# ---------------------------------------------------------------------------
# Plan items
# ---------------------------------------------------------------------------
def _plan_item_out(item: models.PlanItem) -> schemas.PlanItemOut:
    return schemas.PlanItemOut.model_validate(item)


@app.get("/plan-items", response_model=List[schemas.PlanItemOut])
def list_plan_items(
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.PlanItem).filter(models.PlanItem.owner_id == user.id)
    if date:
        q = q.filter(models.PlanItem.date == date)
    if date_from:
        q = q.filter(models.PlanItem.date >= date_from)
    if date_to:
        q = q.filter(models.PlanItem.date <= date_to)
    return [_plan_item_out(i) for i in q.all()]


@app.post("/plan-items", response_model=schemas.PlanItemOut)
def create_plan_item(payload: schemas.PlanItemCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = models.PlanItem(
        id=new_id(), owner_id=user.id, name=payload.name, date=payload.date,
        category=payload.category, time_label=payload.time_label or "",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    # طبق تصمیم محصول: فقط برنامه‌ی خودِ ادمین با Notion سینک می‌شه (چون
    # دیتابیس Notion مشترکه و مخصوص گزارش/پیگیریِ ادمینه، نه هر عضو گروه).
    # اگه Notion کانفیگ شده، همین‌جا یک صفحه‌ی متناظر هم توی Notion ساخته
    # می‌شه تا از همون لحظه‌ی ساخت، دو طرف سینک باشن.
    if user.role == "admin" and notion_sync.is_configured():
        try:
            page_id = notion_sync.create_plan_item_page(item)
            if page_id:
                item.notion_page_id = page_id
                db.commit()
                db.refresh(item)
        except Exception as e:
            print(f"[notion create failed] item={item.id} err={e}")  # توی Railway logs دیده می‌شه
    return _plan_item_out(item)


@app.patch("/plan-items/{item_id}", response_model=schemas.PlanItemOut)
def update_plan_item(item_id: str, payload: schemas.PlanItemUpdate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(models.PlanItem).filter(models.PlanItem.id == item_id, models.PlanItem.owner_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="پارت برنامه یافت نشد")
    for field in ("name", "date", "category", "status", "study_minutes", "test_count", "time_label", "notes"):
        val = getattr(payload, field)
        if val is not None:
            setattr(item, field, val)
    db.commit()
    db.refresh(item)
    if item.notion_page_id and notion_sync.is_configured():
        try:
            notion_sync.push_plan_item(item)
        except Exception as e:
            print(f"[notion push failed] item={item.id} err={e}")  # توی Railway logs دیده می‌شه
    return _plan_item_out(item)


@app.delete("/plan-items/{item_id}")
def delete_plan_item(item_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(models.PlanItem).filter(models.PlanItem.id == item_id, models.PlanItem.owner_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="پارت برنامه یافت نشد")
    notion_page_id = item.notion_page_id
    db.delete(item)
    db.commit()
    # صفحه‌ی متناظر توی Notion هم حذف بشه تا از اپ خارج نشه.
    if notion_page_id and notion_sync.is_configured():
        try:
            notion_sync.delete_plan_item_page(notion_page_id)
        except Exception as e:
            print(f"[notion delete failed] page={notion_page_id} err={e}")  # توی Railway logs دیده می‌شه
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------
def _question_out(q: models.Question) -> schemas.QuestionOut:
    return schemas.QuestionOut(
        id=q.id, owner_id=q.owner_id, text=q.text,
        options=[schemas.QuestionOption(**o) for o in json.loads(q.options_json or "[]")],
        subject=q.subject or "", topic=q.topic or "", difficulty=q.difficulty or "mid",
        created_at=q.created_at,
    )


@app.get("/questions", response_model=List[schemas.QuestionOut])
def list_questions(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(models.Question).filter(models.Question.owner_id == user.id).order_by(models.Question.created_at.desc()).all()
    return [_question_out(q) for q in items]


@app.post("/questions", response_model=schemas.QuestionOut)
def create_question(payload: schemas.QuestionCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = models.Question(
        id=new_id(), owner_id=user.id, text=payload.text,
        options_json=json.dumps([o.model_dump() for o in payload.options], ensure_ascii=False),
        subject=payload.subject, topic=payload.topic, difficulty=payload.difficulty,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return _question_out(q)


@app.patch("/questions/{q_id}", response_model=schemas.QuestionOut)
def update_question(q_id: str, payload: schemas.QuestionCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(models.Question).filter(models.Question.id == q_id, models.Question.owner_id == user.id).first()
    if not q:
        raise HTTPException(status_code=404, detail="سوال یافت نشد")
    q.text = payload.text
    q.options_json = json.dumps([o.model_dump() for o in payload.options], ensure_ascii=False)
    q.subject = payload.subject
    q.topic = payload.topic
    q.difficulty = payload.difficulty
    db.commit()
    db.refresh(q)
    return _question_out(q)


@app.delete("/questions/{q_id}")
def delete_question(q_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(models.Question).filter(models.Question.id == q_id, models.Question.owner_id == user.id).first()
    if not q:
        raise HTTPException(status_code=404, detail="سوال یافت نشد")
    db.delete(q)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Exams
# ---------------------------------------------------------------------------
def _exam_out(e: models.Exam) -> schemas.ExamOut:
    return schemas.ExamOut(
        id=e.id, owner_id=e.owner_id, name=e.name, date=e.date,
        subjects=[schemas.ExamSubject(**s) for s in json.loads(e.subjects_json or "[]")],
    )


@app.get("/exams", response_model=List[schemas.ExamOut])
def list_exams(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(models.Exam).filter(models.Exam.owner_id == user.id).order_by(models.Exam.date.desc()).all()
    return [_exam_out(e) for e in items]


@app.post("/exams", response_model=schemas.ExamOut)
def create_exam(payload: schemas.ExamCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = models.Exam(
        id=new_id(), owner_id=user.id, name=payload.name, date=payload.date,
        subjects_json=json.dumps([s.model_dump() for s in payload.subjects], ensure_ascii=False),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _exam_out(e)


@app.patch("/exams/{e_id}", response_model=schemas.ExamOut)
def update_exam(e_id: str, payload: schemas.ExamCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(models.Exam).filter(models.Exam.id == e_id, models.Exam.owner_id == user.id).first()
    if not e:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    e.name = payload.name
    e.date = payload.date
    e.subjects_json = json.dumps([s.model_dump() for s in payload.subjects], ensure_ascii=False)
    db.commit()
    db.refresh(e)
    return _exam_out(e)


@app.delete("/exams/{e_id}")
def delete_exam(e_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(models.Exam).filter(models.Exam.id == e_id, models.Exam.owner_id == user.id).first()
    if not e:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    db.delete(e)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Alarms
# ---------------------------------------------------------------------------
def _alarm_out(a: models.Alarm) -> schemas.AlarmOut:
    return schemas.AlarmOut(id=a.id, owner_id=a.owner_id, label=a.label, time=a.time, days=json.loads(a.days_json or "[]"), enabled=a.enabled)


@app.get("/alarms", response_model=List[schemas.AlarmOut])
def list_alarms(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(models.Alarm).filter(models.Alarm.owner_id == user.id).all()
    return [_alarm_out(a) for a in items]


@app.post("/alarms", response_model=schemas.AlarmOut)
def create_alarm(payload: schemas.AlarmCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = models.Alarm(
        id=new_id(), owner_id=user.id, label=payload.label, time=payload.time,
        days_json=json.dumps(payload.days), enabled=payload.enabled,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _alarm_out(a)


@app.patch("/alarms/{a_id}", response_model=schemas.AlarmOut)
def update_alarm(a_id: str, payload: schemas.AlarmCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.query(models.Alarm).filter(models.Alarm.id == a_id, models.Alarm.owner_id == user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="آلارم یافت نشد")
    a.label = payload.label
    a.time = payload.time
    a.days_json = json.dumps(payload.days)
    a.enabled = payload.enabled
    db.commit()
    db.refresh(a)
    return _alarm_out(a)


@app.delete("/alarms/{a_id}")
def delete_alarm(a_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.query(models.Alarm).filter(models.Alarm.id == a_id, models.Alarm.owner_id == user.id).first()
    if not a:
        raise HTTPException(status_code=404, detail="آلارم یافت نشد")
    db.delete(a)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# بانک تحلیل (Analysis Bank)
# ---------------------------------------------------------------------------
def _analysis_exam_path(pdf_filename: str) -> str:
    return os.path.join(ANALYSIS_UPLOAD_DIR, pdf_filename)


def _analysis_note_out(n: models.AnalysisQuestionNote, page_map: dict) -> schemas.AnalysisQuestionNoteOut:
    return schemas.AnalysisQuestionNoteOut(
        id=n.id, exam_id=n.exam_id, question_number=n.question_number,
        subject=n.subject or "", note=n.note or "", is_correct=n.is_correct,
        page=page_map.get(str(n.question_number)) or page_map.get(n.question_number),
        created_at=n.created_at, updated_at=n.updated_at,
    )


def _analysis_exam_out(e: models.AnalysisExam, db: Session) -> schemas.AnalysisExamOut:
    page_map_raw = json.loads(e.question_page_map_json or "{}")
    page_map_int = {int(k): v for k, v in page_map_raw.items()}
    notes = (
        db.query(models.AnalysisQuestionNote)
        .filter(models.AnalysisQuestionNote.exam_id == e.id)
        .order_by(models.AnalysisQuestionNote.question_number.asc())
        .all()
    )
    return schemas.AnalysisExamOut(
        id=e.id, owner_id=e.owner_id, title=e.title, date=e.date or "",
        original_filename=e.original_filename or "", page_count=e.page_count,
        question_count=e.question_count, question_page_map=page_map_int,
        mapping_method=e.mapping_method,
        manual_start_page=e.manual_start_page, manual_end_page=e.manual_end_page,
        overall_note=e.overall_note or "", created_at=e.created_at,
        notes=[_analysis_note_out(n, page_map_raw) for n in notes],
    )


def _analysis_exam_list_out(e: models.AnalysisExam, notes_count: int) -> schemas.AnalysisExamListOut:
    return schemas.AnalysisExamListOut(
        id=e.id, owner_id=e.owner_id, title=e.title, date=e.date or "",
        page_count=e.page_count, question_count=e.question_count,
        mapping_method=e.mapping_method, overall_note=e.overall_note or "",
        notes_count=notes_count, created_at=e.created_at,
    )


@app.get("/analysis-exams", response_model=List[schemas.AnalysisExamListOut])
def list_analysis_exams(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = (
        db.query(models.AnalysisExam)
        .filter(models.AnalysisExam.owner_id == user.id)
        .order_by(models.AnalysisExam.created_at.desc())
        .all()
    )
    out = []
    for e in items:
        cnt = db.query(models.AnalysisQuestionNote).filter(models.AnalysisQuestionNote.exam_id == e.id).count()
        out.append(_analysis_exam_list_out(e, cnt))
    return out


@app.get("/analysis-exams/{exam_id}", response_model=schemas.AnalysisExamOut)
def get_analysis_exam(exam_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(models.AnalysisExam).filter(models.AnalysisExam.id == exam_id, models.AnalysisExam.owner_id == user.id).first()
    if not e:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    return _analysis_exam_out(e, db)


@app.post("/analysis-exams", response_model=schemas.AnalysisExamOut)
async def create_analysis_exam(
    title: str = Form(...),
    date: str = Form(""),
    question_count: int = Form(...),
    manual_start_page: Optional[int] = Form(None),
    manual_end_page: Optional[int] = Form(None),
    overall_note: str = Form(""),
    pdf: UploadFile = File(...),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (1 <= question_count <= 200):
        raise HTTPException(status_code=400, detail="تعداد سوال باید بین ۱ تا ۲۰۰ باشد")
    if pdf.content_type not in ("application/pdf", "application/octet-stream") and not (pdf.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="فقط فایل PDF مجاز است")

    exam_id = new_id()
    pdf_filename = f"{exam_id}.pdf"
    dest_path = _analysis_exam_path(pdf_filename)

    size = 0
    max_bytes = ANALYSIS_MAX_PDF_MB * 1024 * 1024
    try:
        with open(dest_path, "wb") as out_f:
            while True:
                chunk = await pdf.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    out_f.close()
                    os.remove(dest_path)
                    raise HTTPException(status_code=400, detail=f"حجم فایل نباید بیشتر از {ANALYSIS_MAX_PDF_MB} مگابایت باشد")
                out_f.write(chunk)
    finally:
        await pdf.close()

    if size == 0:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(status_code=400, detail="فایل آپلودشده خالی است")

    # ۱) اول تلاش برای تشخیص خودکار نگاشت شماره‌سوال -> صفحه از روی متن PDF
    auto_map, page_count = analysis_pdf.detect_question_page_map(dest_path, expected_question_count=question_count)
    mapping_method = "manual"
    final_map = {}
    used_start = manual_start_page
    used_end = manual_end_page

    if auto_map:
        final_map = analysis_pdf.fill_gaps_in_map(auto_map, question_count)
        mapping_method = "auto"
    elif manual_start_page and manual_end_page:
        final_map = analysis_pdf.build_linear_map(question_count, manual_start_page, manual_end_page)
        mapping_method = "manual"
    else:
        # نه تشخیص خودکار جواب داد، نه نقطه‌ی دستی داده شده؛ فایل رو نگه
        # می‌داریم ولی بدون نگاشت — کاربر بعداً می‌تونه با
        # /analysis-exams/{id}/remap دستی تنظیمش کنه.
        final_map = {}
        mapping_method = "manual"

    if page_count == 0:
        page_count = analysis_pdf.get_page_count(dest_path)

    e = models.AnalysisExam(
        id=exam_id, owner_id=user.id, title=title, date=date or "",
        pdf_filename=pdf_filename, original_filename=pdf.filename or "",
        page_count=page_count, question_count=question_count,
        question_page_map_json=json.dumps({str(k): v for k, v in final_map.items()}, ensure_ascii=False),
        mapping_method=mapping_method,
        manual_start_page=used_start, manual_end_page=used_end,
        overall_note=overall_note or "",
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _analysis_exam_out(e, db)


@app.patch("/analysis-exams/{exam_id}", response_model=schemas.AnalysisExamOut)
def update_analysis_exam(exam_id: str, payload: schemas.AnalysisExamUpdate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(models.AnalysisExam).filter(models.AnalysisExam.id == exam_id, models.AnalysisExam.owner_id == user.id).first()
    if not e:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    if payload.title is not None:
        e.title = payload.title
    if payload.date is not None:
        e.date = payload.date
    if payload.overall_note is not None:
        e.overall_note = payload.overall_note
    db.commit()
    db.refresh(e)
    return _analysis_exam_out(e, db)


@app.post("/analysis-exams/{exam_id}/remap", response_model=schemas.AnalysisExamOut)
def remap_analysis_exam(exam_id: str, payload: schemas.AnalysisRemapRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """اصلاح دستی نگاشت صفحات — وقتی تشخیص خودکار غلط بوده یا کاربر می‌خواد
    خودش دقیق‌تر (با دو نقطه‌ی جدید) نگاشت خطی رو بازسازی کنه."""
    e = db.query(models.AnalysisExam).filter(models.AnalysisExam.id == exam_id, models.AnalysisExam.owner_id == user.id).first()
    if not e:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    if payload.manual_end_page < payload.manual_start_page:
        raise HTTPException(status_code=400, detail="صفحه‌ی پایان نمی‌تواند قبل از صفحه‌ی شروع باشد")
    if e.page_count and payload.manual_end_page > e.page_count:
        raise HTTPException(status_code=400, detail=f"این PDF فقط {e.page_count} صفحه دارد")

    new_map = analysis_pdf.build_linear_map(e.question_count, payload.manual_start_page, payload.manual_end_page)
    e.question_page_map_json = json.dumps({str(k): v for k, v in new_map.items()}, ensure_ascii=False)
    e.mapping_method = "manual"
    e.manual_start_page = payload.manual_start_page
    e.manual_end_page = payload.manual_end_page
    db.commit()
    db.refresh(e)
    return _analysis_exam_out(e, db)


@app.delete("/analysis-exams/{exam_id}")
def delete_analysis_exam(exam_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(models.AnalysisExam).filter(models.AnalysisExam.id == exam_id, models.AnalysisExam.owner_id == user.id).first()
    if not e:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    pdf_path = _analysis_exam_path(e.pdf_filename)
    db.delete(e)
    db.commit()
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except OSError:
            pass
    return {"deleted": True}


@app.get("/analysis-exams/{exam_id}/pdf")
def get_analysis_exam_pdf(exam_id: str, token: Optional[str] = None, download: Optional[int] = None, db: Session = Depends(get_db)):
    # <iframe>/<embed> و دکمه‌ی دانلود امکان فرستادن هدر Authorization رو
    # ندارن، پس اینجا (فقط همین route) توکن رو به‌عنوان query param هم
    # قبول می‌کنیم — نه فقط هدر Bearer معمول.
    payload = auth.decode_access_token(token) if token else None
    if not payload:
        raise HTTPException(status_code=401, detail="توکن نامعتبر یا منقضی شده")
    user = db.query(models.User).filter(models.User.id == int(payload["sub"])).first()
    if not user or user.is_banned:
        raise HTTPException(status_code=401, detail="دسترسی مجاز نیست")

    e = db.query(models.AnalysisExam).filter(models.AnalysisExam.id == exam_id, models.AnalysisExam.owner_id == user.id).first()
    if not e:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    pdf_path = _analysis_exam_path(e.pdf_filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="فایل PDF روی سرور پیدا نشد (احتمالاً بعد از دیپلوی پاک شده)")
    filename = e.original_filename or f"{e.title}.pdf"

    # -----------------------------------------------------------------------
    # نکته‌ی مهم: FileResponse با پارامتر filename به‌صورت خودکار هدر
    # Content-Disposition: attachment می‌فرسته. این باعث می‌شه مرورگر به‌جای
    # نمایش PDF داخل <iframe> (preview)، همیشه بخواد فایل رو دانلود کنه —
    # که دقیقاً همون چیزیه که باعث «صفحه‌ی سفید» و «دانلود مجدد کل PDF»
    # موقع کلیک روی پرش به سوال می‌شد.
    # پیش‌فرض این route حالا inline (برای iframe/viewer) هست؛ فقط وقتی
    # صریحاً download=1 پاس داده بشه (دکمه‌ی «دانلود PDF»)، attachment
    # می‌فرستیم.
    # -----------------------------------------------------------------------
    disposition_type = "attachment" if download else "inline"
    response = FileResponse(pdf_path, media_type="application/pdf")
    safe_filename = filename.replace('"', "")
    response.headers["Content-Disposition"] = f'{disposition_type}; filename="{safe_filename}"'
    return response


@app.get("/analysis-exams/{exam_id}/notes", response_model=List[schemas.AnalysisQuestionNoteOut])
def list_analysis_notes(exam_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(models.AnalysisExam).filter(models.AnalysisExam.id == exam_id, models.AnalysisExam.owner_id == user.id).first()
    if not e:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    page_map = json.loads(e.question_page_map_json or "{}")
    notes = (
        db.query(models.AnalysisQuestionNote)
        .filter(models.AnalysisQuestionNote.exam_id == exam_id)
        .order_by(models.AnalysisQuestionNote.question_number.asc())
        .all()
    )
    return [_analysis_note_out(n, page_map) for n in notes]


@app.post("/analysis-exams/{exam_id}/notes", response_model=schemas.AnalysisQuestionNoteOut)
def upsert_analysis_note(exam_id: str, payload: schemas.AnalysisQuestionNoteCreate, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """ساخت یا به‌روزرسانی تحلیل یک سوال مشخص. اگه از قبل برای همون شماره‌سوال
    تحلیلی ثبت شده باشه، بازنویسی می‌شه (چون هر سوال فقط یک تحلیل داره)."""
    e = db.query(models.AnalysisExam).filter(models.AnalysisExam.id == exam_id, models.AnalysisExam.owner_id == user.id).first()
    if not e:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    if payload.question_number > e.question_count:
        raise HTTPException(status_code=400, detail=f"این آزمون فقط {e.question_count} سوال دارد")

    existing = (
        db.query(models.AnalysisQuestionNote)
        .filter(models.AnalysisQuestionNote.exam_id == exam_id, models.AnalysisQuestionNote.question_number == payload.question_number)
        .first()
    )
    now = datetime.utcnow()
    if existing:
        existing.subject = payload.subject or ""
        existing.note = payload.note or ""
        existing.is_correct = payload.is_correct
        existing.updated_at = now
        n = existing
    else:
        n = models.AnalysisQuestionNote(
            id=new_id(), exam_id=exam_id, question_number=payload.question_number,
            subject=payload.subject or "", note=payload.note or "",
            is_correct=payload.is_correct, created_at=now, updated_at=now,
        )
        db.add(n)
    db.commit()
    db.refresh(n)
    page_map = json.loads(e.question_page_map_json or "{}")
    return _analysis_note_out(n, page_map)


@app.delete("/analysis-exams/{exam_id}/notes/{note_id}")
def delete_analysis_note(exam_id: str, note_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(models.AnalysisExam).filter(models.AnalysisExam.id == exam_id, models.AnalysisExam.owner_id == user.id).first()
    if not e:
        raise HTTPException(status_code=404, detail="آزمون یافت نشد")
    n = db.query(models.AnalysisQuestionNote).filter(models.AnalysisQuestionNote.id == note_id, models.AnalysisQuestionNote.exam_id == exam_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="تحلیل یافت نشد")
    db.delete(n)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Admin: member management (also usable from the bot's admin commands)
# ---------------------------------------------------------------------------
def _last_7_days_range():
    from datetime import date, timedelta
    today = date.today()
    return (today - timedelta(days=6)).isoformat(), today.isoformat()


def _member_stats(db: Session, u: models.User) -> schemas.AdminMemberOut:
    d_from, d_to = _last_7_days_range()
    items = db.query(models.PlanItem).filter(
        models.PlanItem.owner_id == u.id,
        models.PlanItem.category == "درسی",
        models.PlanItem.date >= d_from,
        models.PlanItem.date <= d_to,
    ).all()
    minutes = sum(i.study_minutes for i in items)
    tests = sum(i.test_count for i in items)
    return schemas.AdminMemberOut(
        id=u.id, username=u.username, display_name=u.display_name, role=u.role,
        is_banned=u.is_banned, telegram_chat_id=u.telegram_chat_id,
        total_minutes_last_7d=minutes, total_tests_last_7d=tests,
    )


@app.get("/admin/members", response_model=List[schemas.AdminMemberOut])
def admin_list_members(admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [_member_stats(db, u) for u in users]


@app.post("/admin/members/{user_id}/ban", response_model=schemas.AdminMemberOut)
def admin_set_ban(user_id: int, payload: schemas.BanRequest, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    if u.id == admin.id:
        raise HTTPException(status_code=400, detail="نمی‌تونی خودت رو بن کنی")
    u.is_banned = payload.banned
    db.commit()
    db.refresh(u)
    return _member_stats(db, u)


@app.delete("/admin/members/{user_id}")
def admin_delete_member(user_id: int, admin: models.User = Depends(get_current_admin), db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    if u.id == admin.id:
        raise HTTPException(status_code=400, detail="نمی‌تونی خودت رو حذف کنی")
    db.delete(u)
    db.commit()
    return {"deleted": True}


@app.post("/admin/members/{user_id}/reset-password", response_model=schemas.AdminResetPasswordResponse)
def admin_reset_password(
    user_id: int,
    payload: schemas.AdminResetPasswordRequest,
    admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """برای کاربرهایی که به بات وصل نیستن (یا هر کاربری)، ادمین دستی رمز رو ریست
    می‌کنه. اگه رمز جدید داده نشه، یک رمز موقت تصادفی ساخته می‌شه — ادمین باید
    این رمز رو خودش (مثلاً توی گروه یا پیوی) به کاربر بگه."""
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")

    new_password = payload.new_password or auth.generate_temp_password()
    u.password_hash = auth.hash_password(new_password)
    u.password_reset_code = None
    u.password_reset_expires = None
    db.commit()
    return schemas.AdminResetPasswordResponse(new_password=new_password)


# ---------------------------------------------------------------------------
# Notion sync — فقط ادمین. برنامه‌ی خودِ ادمین (owner_id = admin.id) از دیتابیس
# Notion خونده و توی جدول plan_items درج/آپدیت می‌شه. اگه آیتمی قبلاً از همین
# Notion page سینک شده باشه (notion_page_id ذخیره‌شده)، به‌جای ساختن رکورد
# تکراری، همون رکورد آپدیت می‌شه.
# ---------------------------------------------------------------------------
@app.get("/admin/notion/status", response_model=schemas.NotionStatusOut)
def admin_notion_status(admin: models.User = Depends(get_current_admin)):
    return schemas.NotionStatusOut(
        configured=notion_sync.is_configured(),
        database_id_set=bool(notion_sync.NOTION_DATABASE_ID),
    )


@app.post("/admin/notion/sync", response_model=schemas.NotionSyncOut)
def admin_notion_sync(
    payload: schemas.NotionSyncRequest,
    admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not notion_sync.is_configured():
        raise HTTPException(
            status_code=400,
            detail="تنظیمات Notion پیکربندی نشده است. NOTION_API_KEY و NOTION_DATABASE_ID را در Railway ست کنید.",
        )
    try:
        notion_items = notion_sync.fetch_plan_items(date_filter=payload.date)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"خطا در ارتباط با Notion: {e}")

    created = 0
    updated = 0
    for it in notion_items:
        if not it["date"]:
            continue  # آیتم بدون تاریخ (ناقص) رد می‌شه
        existing = (
            db.query(models.PlanItem)
            .filter(
                models.PlanItem.owner_id == admin.id,
                models.PlanItem.notion_page_id == it["notion_page_id"],
            )
            .first()
        )
        if existing:
            existing.name = it["name"]
            existing.date = it["date"]
            existing.category = it["category"]
            existing.status = it["status"]
            existing.study_minutes = it["study_minutes"]
            existing.test_count = it["test_count"]
            existing.time_label = it["time_label"]
            updated += 1
        else:
            db.add(models.PlanItem(
                id=new_id(),
                owner_id=admin.id,
                name=it["name"],
                date=it["date"],
                category=it["category"],
                status=it["status"],
                study_minutes=it["study_minutes"],
                test_count=it["test_count"],
                time_label=it["time_label"],
                notion_page_id=it["notion_page_id"],
            ))
            created += 1

    db.commit()
    return schemas.NotionSyncOut(created=created, updated=updated, total_from_notion=len(notion_items))


# ---------------------------------------------------------------------------
# Bot-facing routes — authenticated with X-Bot-Key header instead of JWT,
# چون خود بات کاربری نیست که لاگین کند؛ این کلید فقط بین دو سرویس Railway
# (بات و بکند) رد و بدل می‌شود و کاربر نهایی هرگز آن را نمی‌بیند.
# ---------------------------------------------------------------------------
@app.post("/bot/link-account", response_model=schemas.UserOut)
def bot_link_account(payload: schemas.BotLinkRequest, _=Depends(verify_bot_key), db: Session = Depends(get_db)):
    """وقتی کاربر توی بات دستور /link username password را می‌زند، بات این اندپوینت را
    صدا می‌زند تا chat_id تلگرام را به حساب اپ او وصل کند.
    بدون تأیید رمز عبور، هیچ‌کس نمی‌تواند حساب دیگری را به چت خود متصل کند."""
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="کاربری با این نام کاربری در اپ ثبت‌نام نکرده")
    if not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="رمز عبور اشتباه است")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="این حساب مسدود شده است")
    # اگه این chat_id قبلاً به حساب دیگری وصل بود، اول جدا می‌کنیم
    existing = db.query(models.User).filter(
        models.User.telegram_chat_id == payload.telegram_chat_id,
        models.User.id != user.id
    ).first()
    if existing:
        existing.telegram_chat_id = None
        db.flush()
    user.telegram_chat_id = payload.telegram_chat_id
    db.commit()
    db.refresh(user)
    return user


@app.get("/bot/user-by-chat/{chat_id}", response_model=schemas.UserOut)
def bot_get_user_by_chat(chat_id: int, _=Depends(verify_bot_key), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_chat_id == chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="این چت به هیچ حسابی وصل نشده — با /link در بات وصل کن")
    return user


@app.get("/bot/plan-items/{chat_id}", response_model=List[schemas.PlanItemOut])
def bot_list_plan_items(chat_id: int, date: Optional[str] = None, _=Depends(verify_bot_key), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_chat_id == chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="این چت به هیچ حسابی وصل نشده")
    q = db.query(models.PlanItem).filter(models.PlanItem.owner_id == user.id)
    if date:
        q = q.filter(models.PlanItem.date == date)
    return [_plan_item_out(i) for i in q.all()]


@app.post("/bot/plan-items/{chat_id}", response_model=schemas.PlanItemOut)
def bot_create_plan_item(chat_id: int, payload: schemas.PlanItemCreate, _=Depends(verify_bot_key), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_chat_id == chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="این چت به هیچ حسابی وصل نشده")
    item = models.PlanItem(
        id=new_id(), owner_id=user.id, name=payload.name, date=payload.date,
        category=payload.category, time_label=payload.time_label or "",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _plan_item_out(item)


@app.patch("/bot/plan-items/{chat_id}/{item_id}", response_model=schemas.PlanItemOut)
def bot_update_plan_item(chat_id: int, item_id: str, payload: schemas.PlanItemUpdate, _=Depends(verify_bot_key), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_chat_id == chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="این چت به هیچ حسابی وصل نشده")
    item = db.query(models.PlanItem).filter(models.PlanItem.id == item_id, models.PlanItem.owner_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="پارت برنامه یافت نشد")
    for field in ("name", "date", "category", "status", "study_minutes", "test_count", "time_label", "notes"):
        val = getattr(payload, field)
        if val is not None:
            setattr(item, field, val)
    db.commit()
    db.refresh(item)
    return _plan_item_out(item)


@app.get("/bot/plan-items/{chat_id}/{item_id}", response_model=schemas.PlanItemOut)
def bot_get_plan_item(chat_id: int, item_id: str, _=Depends(verify_bot_key), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_chat_id == chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="این چت به هیچ حسابی وصل نشده")
    item = db.query(models.PlanItem).filter(models.PlanItem.id == item_id, models.PlanItem.owner_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="پارت برنامه یافت نشد")
    return _plan_item_out(item)


@app.delete("/bot/plan-items/{chat_id}/{item_id}")
def bot_delete_plan_item(chat_id: int, item_id: str, _=Depends(verify_bot_key), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.telegram_chat_id == chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="این چت به هیچ حسابی وصل نشده")
    item = db.query(models.PlanItem).filter(models.PlanItem.id == item_id, models.PlanItem.owner_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="پارت برنامه یافت نشد")
    db.delete(item)
    db.commit()
    return {"deleted": True}


@app.post("/bot/set-group/{chat_id}")
def bot_set_group(chat_id: int, group_id: int, _=Depends(verify_bot_key), db: Session = Depends(get_db)):
    """وقتی کاربر توی یک گروه تلگرام دستور مرتبط با «مقصد گزارش» رو می‌زنه،
    بات این اندپوینت رو صدا می‌زنه تا telegram_group_id حساب کاربر ست بشه."""
    user = db.query(models.User).filter(models.User.telegram_chat_id == chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="این چت به هیچ حسابی وصل نشده — اول با /link در بات وصل کن")
    user.telegram_group_id = group_id
    db.commit()
    db.refresh(user)
    return {"ok": True, "telegram_group_id": user.telegram_group_id}


@app.post("/bot/ban-by-chat/{chat_id}")
def bot_ban_by_chat(chat_id: int, banned: bool, requester_chat_id: int, _=Depends(verify_bot_key), db: Session = Depends(get_db)):
    """دستور /ban و /unban داخل بات از این اندپوینت استفاده می‌کند. فقط کسی که
    خودش role=admin دارد (requester_chat_id) اجازه‌ی این کار را دارد."""
    requester = db.query(models.User).filter(models.User.telegram_chat_id == requester_chat_id).first()
    if not requester or requester.role != "admin":
        raise HTTPException(status_code=403, detail="فقط ادمین می‌تونه این کار رو بکنه")
    target = db.query(models.User).filter(models.User.telegram_chat_id == chat_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    target.is_banned = banned
    db.commit()
    return {"ok": True, "banned": target.is_banned}


@app.get("/bot/group-report/{group_id}", response_model=List[schemas.BotGroupReportMember])
def bot_group_report(group_id: int, date: str, _=Depends(verify_bot_key), db: Session = Depends(get_db)):
    """برای job شبانه‌ی ساعت ۱: خلاصه‌ی کار همه‌ی اعضایی که این گروه را
    به‌عنوان مقصد گزارش‌شان ثبت کرده‌اند، برای تاریخ داده‌شده."""
    users = db.query(models.User).filter(models.User.telegram_group_id == group_id, models.User.is_banned == False).all()
    result = []
    for u in users:
        items = db.query(models.PlanItem).filter(
            models.PlanItem.owner_id == u.id,
            models.PlanItem.category == "درسی",
            models.PlanItem.date == date,
        ).all()
        minutes = sum(i.study_minutes for i in items)
        tests = sum(i.test_count for i in items)
        completed = sum(1 for i in items if i.status)
        result.append(schemas.BotGroupReportMember(
            display_name=u.display_name, username=u.username,
            total_minutes=minutes, total_tests=tests,
            completed_items=completed, total_items=len(items),
        ))
    return result


@app.get("/bot/active-groups", response_model=List[int])
def bot_active_groups(_=Depends(verify_bot_key), db: Session = Depends(get_db)):
    """لیست یکتای group_id هایی که حداقل یک عضو (غیر بن‌شده) بهشون وصله —
    Job گزارش شبانه‌ی گروهی این رو صدا می‌زنه تا بدونه به کدوم گروه‌ها پیام
    بفرسته، بدون نیاز به هاردکد کردن group_id توی کد بات."""
    rows = (
        db.query(models.User.telegram_group_id)
        .filter(models.User.telegram_group_id.isnot(None), models.User.is_banned == False)
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


@app.get("/bot/active-chat-ids", response_model=List[int])
def bot_active_chat_ids(_=Depends(verify_bot_key), db: Session = Depends(get_db)):
    """لیست همه‌ی telegram_chat_id هایی که به یک حساب وصل شدن (با /link) و
    بن نشدن. جاب‌های زمان‌بندی‌شده‌ی بات (چک‌لیست صبح، چک‌این‌ها، گزارش شب و
    غیره) این رو صدا می‌زنن تا بدونن به کدوم چت‌های خصوصی پیام بفرستن —
    قبلاً این کار با یک دیتابیس محلی SQLite انجام می‌شد؛ حالا منبع حقیقت
    همین بکنده."""
    rows = (
        db.query(models.User.telegram_chat_id)
        .filter(models.User.telegram_chat_id.isnot(None), models.User.is_banned == False)
        .all()
    )
    return [r[0] for r in rows]
