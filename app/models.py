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


class RestorePoint(Base):
    """سیستم restore point برای بازیابی داده‌ها در صورت خرابی یا عملیات حساس.
    
    این جدول قبل از عملیات مهم (مثل همگام‌سازی با ناتیون، حذف گروهی، و غیره)
    یک نقطه بازیابی ایجاد می‌کند تا بتوان در صورت نیاز داده‌ها را بازگرداند.
    """
    __tablename__ = "restore_points"

    id = Column(String(64), primary_key=True)  # هش یکتا برای هر restore point
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    operation_type = Column(String(32), nullable=False, index=True)  # نوع عملیات
    restore_data_json = Column(Text, nullable=False, default="{}")  # داده‌های قابل بازیابی
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    owner = relationship("User", backref="restore_points")
