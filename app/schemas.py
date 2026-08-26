from datetime import datetime
from typing import Optional, List
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
# Bot-facing (uses BOT_API_KEY instead of JWT)
# ---------------------------------------------------------------------------
class BotLinkRequest(BaseModel):
    username: str
    telegram_chat_id: int


class BotGroupReportMember(BaseModel):
    display_name: str
    username: str
    total_minutes: int
    total_tests: int
    completed_items: int
    total_items: int
