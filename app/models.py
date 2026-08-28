"""
مدل‌های دیتابیس مشترک بین بات تلگرام و اپ اپکس پلنر.

نکته‌ی طراحی مهم: جدول plan_items عمداً هم‌ساختار با local_db.py قبلی بات نگه
داشته شده (name, date, category, status, study_minutes, test_count) تا منطق
موجود بات (build_weekly_pdf_data و غیره) با کمترین تغییر روی این دیتابیس هم کار کند.
تنها تفاوت: owner_id به‌جای chat_id، چون حالا کاربر می‌تواند از اپ هم وارد شود
و لزوماً chat_id تلگرام نیست (هرچند برای اعضایی که از بات استفاده می‌کنند همان
chat_id به‌عنوان telegram_chat_id در users ذخیره می‌شود).
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, BigInteger, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(128), nullable=False, default="دانش‌آموز")
    role = Column(String(16), nullable=False, default="member")  # 'member' | 'admin'
    is_banned = Column(Boolean, nullable=False, default=False)
    telegram_chat_id = Column(BigInteger, nullable=True, unique=True, index=True)
    telegram_group_id = Column(BigInteger, nullable=True, index=True)  # گروهی که گزارش‌ها براش فرستاده می‌شه
    goal_hours_per_day = Column(Integer, nullable=False, default=5)
    exam_target_label = Column(String(255), nullable=True, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # --- بازیابی رمز عبور از طریق بات تلگرام (به‌جای پیامک، چون رایگانه و
    # چون کاربرهایی که با /link به بات وصل شدن، از قبل امکان دریافت پیام از
    # بات رو دارن). فقط برای کاربرهای وصل‌شده (telegram_chat_id ست‌شده) کار
    # می‌کنه؛ برای بقیه، ادمین باید از پنل ادمین رمزشون رو دستی ریست کنه. ---
    # کد ۶ رقمی که موقع درخواست بازیابی ساخته و به چت تلگرام کاربر فرستاده می‌شه.
    # با استفاده یا منقضی‌شدن، مقدارش پاک می‌شه (یک‌بارمصرفه).
    password_reset_code = Column(String(6), nullable=True, default=None)
    password_reset_expires = Column(DateTime, nullable=True, default=None)

    plan_items = relationship("PlanItem", back_populates="owner", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="owner", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="owner", cascade="all, delete-orphan")
    alarms = relationship("Alarm", back_populates="owner", cascade="all, delete-orphan")


class PlanItem(Base):
    __tablename__ = "plan_items"

    id = Column(String(32), primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD میلادی
    category = Column(String(32), nullable=False, default="درسی")
    status = Column(Boolean, nullable=False, default=False)
    study_minutes = Column(Integer, nullable=False, default=0)
    test_count = Column(Integer, nullable=False, default=0)
    time_label = Column(String(64), nullable=True, default="")
    notes = Column(Text, nullable=True, default="")
    # اگه این آیتم از Notion همگام‌سازی شده، شناسه‌ی page نوشن اینجا ذخیره می‌شه
    # تا sync بعدی همون آیتم رو آپدیت کنه، نه این‌که یک کپی جدید بسازه.
    notion_page_id = Column(String(64), nullable=True, index=True, default=None)

    owner = relationship("User", back_populates="plan_items")


class Question(Base):
    __tablename__ = "questions"

    id = Column(String(32), primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    options_json = Column(Text, nullable=True, default="[]")  # [{"text":..,"correct":bool}]
    subject = Column(String(64), nullable=True, default="")
    topic = Column(String(128), nullable=True, default="")
    difficulty = Column(String(16), nullable=True, default="mid")  # easy|mid|hard
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    owner = relationship("User", back_populates="questions")


class Exam(Base):
    __tablename__ = "exams"

    id = Column(String(32), primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    date = Column(String(10), nullable=False)
    subjects_json = Column(Text, nullable=False, default="[]")  # [{"name":..,"percent":int}]

    owner = relationship("User", back_populates="exams")


class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(String(32), primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    label = Column(String(255), nullable=False)
    time = Column(String(5), nullable=False)  # "HH:MM"
    days_json = Column(String(64), nullable=False, default="[]")  # [0..6]
    enabled = Column(Boolean, nullable=False, default=True)

    owner = relationship("User", back_populates="alarms")


class TemplateMetaCache(Base):
    """کش متن‌های قالب هفتگی/روزانه بات (هدف، Level Up، نوت، اولویت‌ها) — پورت مستقیم
    از template_meta_cache قدیمی local_db.py."""
    __tablename__ = "template_meta_cache"

    owner_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    scope = Column(String(16), primary_key=True)       # 'weekly' | 'daily'
    period_key = Column(String(10), primary_key=True)   # تاریخ کلید دوره
    data_json = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
