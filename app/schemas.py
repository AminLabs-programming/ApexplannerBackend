from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=4, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_banned: bool
    goal_hours_per_day: int
    exam_target_label: Optional[str] = ""
    telegram_chat_id: Optional[int] = None

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    goal_hours_per_day: Optional[int] = None
    exam_target_label: Optional[str] = None


# ---------------------------------------------------------------------------
# Password change / reset
# ---------------------------------------------------------------------------
class ChangePasswordRequest(BaseModel):
    """کاربرِ لاگین‌کرده، رمز فعلی رو وارد می‌کنه و رمز جدید می‌سازه (سوتیِ رمز رو خودش عوض می‌کنه)."""
    current_password: str
    new_password: str = Field(min_length=4, max_length=128)


class ForgotPasswordRequest(BaseModel):
    """قدم اول بازیابی: فقط یوزرنیم. اگه حساب به بات وصل باشه، کد به تلگرام فرستاده می‌شه."""
    username: str


class ForgotPasswordResponse(BaseModel):
    telegram_linked: bool
    message: str


class ResetPasswordRequest(BaseModel):
    """قدم دوم بازیابی: کدی که از بات گرفته + رمز جدید."""
    username: str
    code: str
    new_password: str = Field(min_length=4, max_length=128)


class AdminResetPasswordRequest(BaseModel):
    """ادمین برای کاربری که به بات وصل نیست (یا هر کاربری) رمز رو دستی ریست می‌کنه.
    اگه new_password خالی بمونه، یک رمز موقت تصادفی ساخته می‌شه و در پاسخ برگردونده می‌شه."""
    new_password: Optional[str] = Field(default=None, min_length=4, max_length=128)


class AdminResetPasswordResponse(BaseModel):
    new_password: str


# ---------------------------------------------------------------------------
# Plan items
# ---------------------------------------------------------------------------
class PlanItemCreate(BaseModel):
    name: str
    date: str
    category: str = "درسی"
    time_label: Optional[str] = ""


class PlanItemUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None
    category: Optional[str] = None
    status: Optional[bool] = None
    study_minutes: Optional[int] = None
    test_count: Optional[int] = None
    time_label: Optional[str] = None
    notes: Optional[str] = None


class PlanItemOut(BaseModel):
    id: str
    owner_id: int
    name: str
    date: str
    category: str
    status: bool
    study_minutes: int
    test_count: int
    time_label: Optional[str] = ""
    notes: Optional[str] = ""

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------
class QuestionOption(BaseModel):
    text: str
    correct: bool = False


class QuestionCreate(BaseModel):
    text: str
    options: List[QuestionOption] = []
    subject: str = ""
    topic: str = ""
    difficulty: str = "mid"


class QuestionOut(BaseModel):
    id: str
    owner_id: int
    text: str
    options: List[QuestionOption]
    subject: str
    topic: str
    difficulty: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Exams
# ---------------------------------------------------------------------------
class ExamSubject(BaseModel):
    name: str
    percent: int = 0


class ExamCreate(BaseModel):
    name: str
    date: str
    subjects: List[ExamSubject] = []


class ExamOut(BaseModel):
    id: str
    owner_id: int
    name: str
    date: str
    subjects: List[ExamSubject]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Alarms
# ---------------------------------------------------------------------------
class AlarmCreate(BaseModel):
    label: str
    time: str
    days: List[int] = []
    enabled: bool = True


class AlarmOut(BaseModel):
    id: str
    owner_id: int
    label: str
    time: str
    days: List[int]
    enabled: bool

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Analysis bank (بانک تحلیل)
# ---------------------------------------------------------------------------
class AnalysisQuestionNoteCreate(BaseModel):
    question_number: int = Field(ge=1, le=200)
    subject: str = ""  # قدیمی/آزاد؛ برای سازگاری نگه داشته شده، UI جدید آن را نمی‌نویسد
    subject_code: Optional[str] = None  # کد جدید از تاکسونومی ثابت (مثلاً "calculus2")
    note: str = ""
    is_correct: Optional[bool] = None  # قدیمی؛ اگر answer_status نیاید از این مشتق می‌شه
    answer_status: Optional[str] = None  # 'correct' | 'incorrect' | 'unanswered'


class AnalysisQuestionNoteOut(BaseModel):
    id: str
    exam_id: str
    question_number: int
    subject: str = ""
    subject_code: str = ""
    category: str = ""  # مشتق‌شده از subject_code، فقط برای نمایش/راحتیِ فرانت
    subject_label: str = ""  # عنوان فارسیِ درس (از subject_code یا از subject قدیمی)
    note: str = ""
    is_correct: Optional[bool] = None
    answer_status: str = "unanswered"
    page: Optional[int] = None  # از question_page_map گرفته و اینجا برای راحتی فرانت اضافه می‌شه
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnalysisExamCreateMeta(BaseModel):
    """متادیتای آزمون؛ همراه فایل PDF به‌صورت multipart/form-data فرستاده می‌شه
    (این اسکیما فقط برای مستندسازی/اعتبارسنجی مقادیر فرم است)."""
    title: str = Field(min_length=1, max_length=255)
    date: Optional[str] = ""
    grade: int = Field(..., ge=10, le=12)  # پایه‌ی تحصیلی: 10 | 11 | 12 — الزامی برای آزمون‌های جدید
    question_count: int = Field(ge=1, le=200)
    # اگر تشخیص خودکار جواب نداد، این دو مقدار برای نگاشت خطی استفاده می‌شن
    manual_start_page: Optional[int] = None
    manual_end_page: Optional[int] = None
    overall_note: Optional[str] = ""


class AnalysisExamUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    grade: Optional[int] = None
    overall_note: Optional[str] = None


class AnalysisRemapRequest(BaseModel):
    """اصلاح دستی نگاشت شماره‌سوال -> صفحه بعد از آپلود (وقتی تشخیص خودکار
    اشتباه بوده یا کاربر می‌خواد خودش دقیق‌تر تنظیم کنه)."""
    manual_start_page: int = Field(ge=1)
    manual_end_page: int = Field(ge=1)


class AnalysisExamOut(BaseModel):
    id: str
    owner_id: int
    title: str
    date: str = ""
    grade: Optional[int] = None
    grade_label: str = ""  # مثلاً «دوازدهم»؛ خالی یعنی نامشخص (آزمون قدیمی)
    original_filename: str = ""
    page_count: int
    question_count: int
    question_page_map: Dict[int, int]
    mapping_method: str
    manual_start_page: Optional[int] = None
    manual_end_page: Optional[int] = None
    overall_note: str = ""
    created_at: datetime
    notes: List[AnalysisQuestionNoteOut] = []

    class Config:
        from_attributes = True


class AnalysisExamListOut(BaseModel):
    """نسخه‌ی سبک برای لیست (بدون نگاشت کامل صفحات و بدون تک‌تک تحلیل‌ها)."""
    id: str
    owner_id: int
    title: str
    date: str = ""
    grade: Optional[int] = None
    grade_label: str = ""
    page_count: int
    question_count: int
    mapping_method: str
    overall_note: str = ""
    notes_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisNoteWithExamOut(BaseModel):
    """یک ردیف نتیجه‌ی جست‌وجوی ترکیبی در «بانک تحلیل» (GET /analysis-notes):
    تحلیلِ یک سؤال به‌همراه اطلاعات کافی از آزمونِ مادرش، تا فرانت بدون
    درخواست‌های اضافه بتونه هم فهرست رو نشون بده هم کاربر رو مستقیم به همون
    سؤال داخل همون آزمون ببره."""
    id: str
    exam_id: str
    exam_title: str
    exam_date: str = ""
    exam_grade: Optional[int] = None
    exam_grade_label: str = ""
    question_number: int
    subject: str = ""
    subject_code: str = ""
    category: str = ""
    category_label: str = ""
    subject_label: str = ""
    note: str = ""
    is_correct: Optional[bool] = None
    answer_status: str = "unanswered"
    page: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
class AdminMemberOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_banned: bool
    telegram_chat_id: Optional[int] = None
    total_minutes_last_7d: int = 0
    total_tests_last_7d: int = 0

    class Config:
        from_attributes = True


class BanRequest(BaseModel):
    banned: bool


# ---------------------------------------------------------------------------
# Notion sync (admin only)
# ---------------------------------------------------------------------------
class NotionStatusOut(BaseModel):
    configured: bool
    database_id_set: bool


class NotionSyncRequest(BaseModel):
    date: Optional[str] = None  # اگه ست بشه، فقط برنامه‌های همون تاریخ سینک می‌شن


class NotionSyncOut(BaseModel):
    created: int
    updated: int
    total_from_notion: int


# ---------------------------------------------------------------------------
# Bot-facing (uses BOT_API_KEY instead of JWT)
# ---------------------------------------------------------------------------
class BotLinkRequest(BaseModel):
    username: str
    password: str          # رمز عبور حساب اپ — بدون این نمی‌توان به چت تلگرام وصل کرد
    telegram_chat_id: int


class BotSendResetCodeRequest(BaseModel):
    """بکند از بات می‌خواد کد بازیابی رو به یک chat_id مشخص بفرسته."""
    telegram_chat_id: int
    code: str
    display_name: str


class BotGroupReportMember(BaseModel):
    display_name: str
    username: str
    total_minutes: int
    total_tests: int
    completed_items: int
    total_items: int
