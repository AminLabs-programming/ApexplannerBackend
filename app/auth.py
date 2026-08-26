"""
احراز هویت: هش کردن رمز عبور (bcrypt مستقیم — نه از طریق passlib، چون
passlib 1.7.4 با نسخه‌های جدید bcrypt ناسازگاره) و توکن JWT برای session اپ.
همچنین یک «کلید مخصوص بات» جدا داریم تا خود بات تلگرام (که کاربر با آن
لاگین نمی‌کند) بتواند مستقیماً و امن به API وصل شود.
"""
import os
import bcrypt
from datetime import datetime, timedelta
from jose import jwt, JWTError

# این مقادیر را روی Railway، در تنظیمات Environment Variables سرویس ست کن.
# اگر ست نشوند، مقدار پیش‌فرض فقط برای تست محلی است و نباید در Production استفاده شود.
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-change-me-in-railway-env")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30

# کلید مخصوص ارتباط بات↔بکند (یک رشته‌ی تصادفی طولانی که در هر دو سرویس
# روی Railway یکسان ست می‌شود؛ هیچ کاربری آن را نمی‌بیند)
BOT_API_KEY = os.environ.get("BOT_API_KEY", "dev-only-bot-key-change-me")


def hash_password(plain: str) -> str:
    # bcrypt فقط تا ۷۲ بایت اول رمز رو در نظر می‌گیره؛ برای رمزهای طولانی‌تر
    # (که بعیده اینجا پیش بیاد ولی برای اطمینان) truncate می‌کنیم.
    pw_bytes = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pw_bytes = plain.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
