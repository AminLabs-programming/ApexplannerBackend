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
