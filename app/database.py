"""
اتصال به دیتابیس. روی Railway، متغیر محیطی DATABASE_URL به‌صورت خودکار
ست می‌شود وقتی پلاگین PostgreSQL رو به این سرویس وصل کنی. برای تست محلی
می‌توانی DATABASE_URL را ست نکنی تا از SQLite فایل محلی استفاده شود.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./apex_local.db")

# Railway/Heroku-style URLs sometimes come as postgres:// which SQLAlchemy's
# psycopg2 driver no longer accepts directly — normalize to postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models
    models.Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()


def _run_lightweight_migrations():
    """create_all فقط جدول‌های جدید رو می‌سازه، نه ستون جدید روی جدول موجود.
    چون این سرویس روی Railway از قبل دیتابیس داره، اینجا با یک کوئری ساده
    چک می‌کنیم ستون‌های جدید هست یا نه و در صورت نیاز اضافه‌شون می‌کنیم
    (بدون نیاز به Alembic برای این تغییرات کوچیک)."""
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "plan_items" in table_names:
        existing_cols = {c["name"] for c in inspector.get_columns("plan_items")}
        if "notion_page_id" not in existing_cols:
            with engine.connect() as conn:
                col_type = "VARCHAR(64)" if not DATABASE_URL.startswith("sqlite") else "TEXT"
                conn.execute(text(f"ALTER TABLE plan_items ADD COLUMN notion_page_id {col_type}"))
                conn.commit()

    if "users" in table_names:
        existing_user_cols = {c["name"] for c in inspector.get_columns("users")}
        with engine.connect() as conn:
            if "password_reset_code" not in existing_user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_reset_code VARCHAR(6)"))
                conn.commit()
            if "password_reset_expires" not in existing_user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_reset_expires TIMESTAMP"))
                conn.commit()

    # --- بانک تحلیل: پایه‌ی تحصیلی آزمون ---
    if "analysis_exams" in table_names:
        existing_exam_cols = {c["name"] for c in inspector.get_columns("analysis_exams")}
        if "grade" not in existing_exam_cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE analysis_exams ADD COLUMN grade INTEGER"))
                conn.commit()
            # داده‌ی قدیمی: هیچ پایه‌ای برای آزمون‌های قبلی قابل‌استنتاج نیست، پس
            # NULL (= «نامشخص») می‌ماند؛ کاربر می‌تواند بعداً از UI ویرایش کند.

    # --- بانک تحلیل: دسته‌بندی درس و وضعیت پاسخ هر سؤال ---
    if "analysis_question_notes" in table_names:
        existing_note_cols = {c["name"] for c in inspector.get_columns("analysis_question_notes")}
        col_type_str32 = "VARCHAR(32)" if not DATABASE_URL.startswith("sqlite") else "TEXT"
        col_type_str16 = "VARCHAR(16)" if not DATABASE_URL.startswith("sqlite") else "TEXT"

        if "subject_code" not in existing_note_cols:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE analysis_question_notes ADD COLUMN subject_code {col_type_str32}"))
                conn.commit()
            # داده‌ی قدیمی: متن آزادِ subject قابل نگاشت مطمئن به کدهای تاکسونومی
            # جدید نیست (هر چیزی می‌توانست باشد)، پس subject_code خالی می‌ماند و
            # ستون قدیمی subject دست‌نخورده باقی می‌ماند تا چیزی گم نشود.

        if "answer_status" not in existing_note_cols:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE analysis_question_notes ADD COLUMN answer_status {col_type_str16}"))
                conn.commit()
                # Backfill از روی ستون قدیمیِ is_correct، برای هر سه حالت به‌صورت
                # صریح (IS TRUE/IS FALSE/IS NULL برای سازگاری هم با SQLite هم Postgres):
                conn.execute(text(
                    "UPDATE analysis_question_notes SET answer_status = 'correct' WHERE is_correct IS TRUE"
                ))
                conn.execute(text(
                    "UPDATE analysis_question_notes SET answer_status = 'incorrect' WHERE is_correct IS FALSE"
                ))
                conn.execute(text(
                    "UPDATE analysis_question_notes SET answer_status = 'unanswered' WHERE is_correct IS NULL"
                ))
                conn.commit()
