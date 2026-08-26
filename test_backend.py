"""
تست سراسری بکند: ثبت‌نام، لاگین، CRUD کامل، پنل ادمین، و مسیرهای بات.
اجرا: python3 test_backend.py
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_apex.db"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["BOT_API_KEY"] = "test-bot-key"

# clean slate
if os.path.exists("./test_apex.db"):
    os.remove("./test_apex.db")

sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

init_db()  # ensure tables exist before the TestClient issues any requests

client = TestClient(app)
failures = []


def check(name, cond, extra=""):
    status = "OK" if cond else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not cond:
        failures.append(name)


# ---------------------------------------------------------------------------
# 1. Health
# ---------------------------------------------------------------------------
r = client.get("/health")
check("health check", r.status_code == 200 and r.json()["status"] == "ok")

# ---------------------------------------------------------------------------
# 2. Register first user (should become admin automatically)
# ---------------------------------------------------------------------------
r = client.post("/auth/register", json={"username": "amin", "password": "1234", "display_name": "امین"})
check("register amin (first user -> admin)", r.status_code == 200, r.text[:200])
data = r.json()
amin_token = data["access_token"]
check("amin is admin", data["user"]["role"] == "admin", data["user"])

# ---------------------------------------------------------------------------
# 3. Register second user (should be plain member)
# ---------------------------------------------------------------------------
r = client.post("/auth/register", json={"username": "sara", "password": "abcd", "display_name": "سارا"})
check("register sara", r.status_code == 200, r.text[:200])
sara_token = r.json()["access_token"]
check("sara is member", r.json()["user"]["role"] == "member")

# duplicate username should fail
r = client.post("/auth/register", json={"username": "amin", "password": "xxxx", "display_name": "دوباره"})
check("duplicate username rejected", r.status_code == 400)

# ---------------------------------------------------------------------------
# 4. Login
# ---------------------------------------------------------------------------
r = client.post("/auth/login", json={"username": "amin", "password": "1234"})
check("login amin correct password", r.status_code == 200)
r = client.post("/auth/login", json={"username": "amin", "password": "wrong"})
check("login amin wrong password rejected", r.status_code == 401)

amin_headers = {"Authorization": f"Bearer {amin_token}"}
sara_headers = {"Authorization": f"Bearer {sara_token}"}

# ---------------------------------------------------------------------------
# 5. /auth/me
# ---------------------------------------------------------------------------
r = client.get("/auth/me", headers=amin_headers)
check("get me (amin)", r.status_code == 200 and r.json()["username"] == "amin")
r = client.get("/auth/me")
check("get me without token -> 401", r.status_code == 401)

# ---------------------------------------------------------------------------
# 6. Plan items CRUD (as sara)
# ---------------------------------------------------------------------------
r = client.post("/plan-items", headers=sara_headers, json={"name": "ریاضی فصل ۱", "date": "2026-08-24", "category": "درسی"})
check("sara creates plan item", r.status_code == 200, r.text[:200])
item = r.json()
item_id = item["id"]
check("plan item default status false", item["status"] == False)

r = client.get("/plan-items", headers=sara_headers)
check("sara sees her own item", r.status_code == 200 and len(r.json()) == 1)

# amin should NOT see sara's item (data isolation)
r = client.get("/plan-items", headers=amin_headers)
check("amin does not see sara's items (isolation)", r.status_code == 200 and len(r.json()) == 0)

r = client.patch(f"/plan-items/{item_id}", headers=sara_headers, json={"status": True, "study_minutes": 90, "test_count": 20})
check("sara marks item done with minutes/tests", r.status_code == 200 and r.json()["study_minutes"] == 90)

# sara cannot edit amin's nonexistent access to her item
r = client.patch(f"/plan-items/{item_id}", headers=amin_headers, json={"status": False})
check("amin cannot edit sara's item -> 404", r.status_code == 404)

r = client.delete(f"/plan-items/{item_id}", headers=sara_headers)
check("sara deletes her item", r.status_code == 200)
r = client.get("/plan-items", headers=sara_headers)
check("item gone after delete", len(r.json()) == 0)

# ---------------------------------------------------------------------------
# 7. Questions CRUD
# ---------------------------------------------------------------------------
r = client.post("/questions", headers=sara_headers, json={
    "text": "حاصل انتگرال؟", "subject": "ریاضی", "topic": "انتگرال", "difficulty": "hard",
    "options": [{"text": "الف", "correct": False}, {"text": "ب", "correct": True}]
})
check("create question", r.status_code == 200, r.text[:200])
q = r.json()
check("question options roundtrip correctly", len(q["options"]) == 2 and q["options"][1]["correct"] == True)

r = client.get("/questions", headers=sara_headers)
check("list questions", len(r.json()) == 1)

r = client.patch(f"/questions/{q['id']}", headers=sara_headers, json={
    "text": "حاصل انتگرال ویرایش‌شده؟", "subject": "ریاضی", "topic": "انتگرال", "difficulty": "mid", "options": []
})
check("update question", r.status_code == 200 and r.json()["difficulty"] == "mid")

r = client.delete(f"/questions/{q['id']}", headers=sara_headers)
check("delete question", r.status_code == 200)

# ---------------------------------------------------------------------------
# 8. Exams CRUD + persistence of subjects list
# ---------------------------------------------------------------------------
r = client.post("/exams", headers=sara_headers, json={
    "name": "آزمون جامع ۱", "date": "2026-08-20",
    "subjects": [{"name": "ریاضی", "percent": 70}, {"name": "فیزیک", "percent": 55}]
})
check("create exam", r.status_code == 200, r.text[:200])
exam = r.json()
check("exam subjects roundtrip", len(exam["subjects"]) == 2 and exam["subjects"][0]["percent"] == 70)

r = client.get("/exams", headers=sara_headers)
check("list exams", len(r.json()) == 1)

# ---------------------------------------------------------------------------
# 9. Alarms CRUD
# ---------------------------------------------------------------------------
r = client.post("/alarms", headers=sara_headers, json={"label": "شروع فیزیک", "time": "08:00", "days": [0, 1, 2], "enabled": True})
check("create alarm", r.status_code == 200, r.text[:200])
alarm = r.json()
check("alarm days roundtrip", alarm["days"] == [0, 1, 2])

# ---------------------------------------------------------------------------
# 10. Admin routes
# ---------------------------------------------------------------------------
r = client.get("/admin/members", headers=sara_headers)
check("non-admin blocked from admin routes -> 403", r.status_code == 403)

r = client.get("/admin/members", headers=amin_headers)
check("admin can list members", r.status_code == 200 and len(r.json()) == 2, r.text[:300])
members = {m["username"]: m for m in r.json()}
check("sara stats reflect her study minutes (should be 0 since item deleted)", members["sara"]["total_minutes_last_7d"] == 0)

sara_id = members["sara"]["id"]
r = client.post(f"/admin/members/{sara_id}/ban", headers=amin_headers, json={"banned": True})
check("admin bans sara", r.status_code == 200 and r.json()["is_banned"] == True)

# sara should now be blocked from all normal routes
r = client.get("/plan-items", headers=sara_headers)
check("banned sara blocked from plan-items -> 403", r.status_code == 403)

r = client.post("/auth/login", json={"username": "sara", "password": "abcd"})
check("banned sara cannot log in -> 403", r.status_code == 403)

# admin cannot ban self
r = client.post(f"/admin/members/{members['amin']['id']}/ban", headers=amin_headers, json={"banned": True})
check("admin cannot ban self -> 400", r.status_code == 400)

# unban
r = client.post(f"/admin/members/{sara_id}/ban", headers=amin_headers, json={"banned": False})
check("admin unbans sara", r.status_code == 200 and r.json()["is_banned"] == False)

# ---------------------------------------------------------------------------
# 11. Bot-facing routes
# ---------------------------------------------------------------------------
bot_headers = {"X-Bot-Key": "test-bot-key"}
bad_bot_headers = {"X-Bot-Key": "wrong-key"}

r = client.post("/bot/link-account", headers=bad_bot_headers, json={"username": "sara", "telegram_chat_id": 555})
check("wrong bot key rejected -> 401", r.status_code == 401)

r = client.post("/bot/link-account", headers=bot_headers, json={"username": "sara", "telegram_chat_id": 555})
check("bot links sara's telegram chat_id", r.status_code == 200 and r.json()["telegram_chat_id"] == 555, r.text[:200])

r = client.post("/bot/link-account", headers=bot_headers, json={"username": "ghost", "telegram_chat_id": 999})
check("linking nonexistent username -> 404", r.status_code == 404)

r = client.get("/bot/user-by-chat/555", headers=bot_headers)
check("bot fetches user by chat_id", r.status_code == 200 and r.json()["username"] == "sara")

r = client.get("/bot/user-by-chat/999999", headers=bot_headers)
check("bot fetch unknown chat_id -> 404", r.status_code == 404)

r = client.post("/bot/plan-items/555", headers=bot_headers, json={"name": "شیمی فصل ۳", "date": "2026-08-24", "category": "درسی"})
check("bot creates plan item for sara via chat_id", r.status_code == 200, r.text[:200])
bot_item_id = r.json()["id"]

r = client.patch(f"/bot/plan-items/555/{bot_item_id}", headers=bot_headers, json={"status": True, "study_minutes": 45, "test_count": 10})
check("bot updates plan item (study log)", r.status_code == 200 and r.json()["study_minutes"] == 45)

# this item should now ALSO be visible from the app side (same underlying user)
r = client.get("/plan-items", headers=sara_headers, params={"date": "2026-08-24"})
check("item created via bot visible in app (shared DB proof)", any(i["id"] == bot_item_id for i in r.json()), r.text[:300])

# set group + group report
r = client.post("/bot/set-group/555", headers=bot_headers, params={"group_id": 777})
check("bot sets sara's report group", r.status_code == 200)

r = client.get("/bot/group-report/777", headers=bot_headers, params={"date": "2026-08-24"})
check("group report returns sara's day", r.status_code == 200 and len(r.json()) == 1, r.text[:300])
report = r.json()[0]
check("group report has correct minutes", report["total_minutes"] == 45)

# ban-by-chat requires requester to be admin; link amin's chat too
client.post("/bot/link-account", headers=bot_headers, json={"username": "amin", "telegram_chat_id": 111})
r = client.post("/bot/ban-by-chat/555", headers=bot_headers, params={"banned": True, "requester_chat_id": 111})
check("admin (via bot) bans sara by chat_id", r.status_code == 200 and r.json()["banned"] == True, r.text[:200])

r = client.post("/bot/ban-by-chat/555", headers=bot_headers, params={"banned": True, "requester_chat_id": 555})
check("non-admin (sara) cannot ban via bot -> 403", r.status_code == 403)

# unban to leave clean state
client.post("/bot/ban-by-chat/555", headers=bot_headers, params={"banned": False, "requester_chat_id": 111})

# ---------------------------------------------------------------------------
print("\n" + "=" * 50)
if failures:
    print(f"❌ {len(failures)} TEST(S) FAILED:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
else:
    print("✅ ALL TESTS PASSED")
    sys.exit(0)
