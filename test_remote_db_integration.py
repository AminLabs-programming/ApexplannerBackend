"""
تست یکپارچگی: دقیقاً همون‌طوری که bot.py قراره از remote_db استفاده کنه،
اینجا صدا می‌زنیم — با یک سرور FastAPI واقعی (نه TestClient) که روی
127.0.0.1:8123 در حال اجراست.
"""
import os
os.environ["BACKEND_URL"] = "http://127.0.0.1:8123"
os.environ["BOT_API_KEY"] = "test-bot-key"

import requests
import remote_db

failures = []


def check(name, cond, extra=""):
    status = "OK" if cond else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not cond:
        failures.append(name)


# 0. health via init_db
remote_db.init_db()
print("(init_db ran without raising)")

# 1. First, create an app account directly via the public API (simulating
#    a user signing up through the web app)
r = requests.post("http://127.0.0.1:8123/auth/register", json={
    "username": "botuser1", "password": "1234", "display_name": "کاربر بات"
})
check("app registration works", r.status_code == 200, r.text[:200])

# 2. Bot: is_registered should be False before /link
check("not registered before link", remote_db.is_registered(999888) == False)

# 3. Bot: register_user should now raise NotImplementedError (old flow removed)
try:
    remote_db.register_user(999888, "کسی")
    check("register_user raises NotImplementedError", False)
except NotImplementedError:
    check("register_user raises NotImplementedError", True)

# 4. Bot: link_account (equivalent of /link command)
try:
    user = remote_db.link_account(999888, "botuser1")
    check("link_account succeeds", user["telegram_chat_id"] == 999888, user)
except Exception as e:
    check("link_account succeeds", False, str(e))

# linking a nonexistent username should raise ValueError with friendly message
try:
    remote_db.link_account(111222, "ghost_user_xyz")
    check("link nonexistent username raises ValueError", False)
except ValueError as e:
    check("link nonexistent username raises ValueError", True, str(e))

# 5. Bot: is_registered now True
check("registered after link", remote_db.is_registered(999888) == True)
check("get_user_name returns display_name", remote_db.get_user_name(999888) == "کاربر بات")

# 6. Bot: add_plan_item / get_items_for_date (exact bot.py call pattern)
item_id = remote_db.add_plan_item(999888, "فیزیک فصل ۴", "2026-08-24", category="درسی")
check("add_plan_item returns id", isinstance(item_id, str) and len(item_id) > 3, item_id)

items = remote_db.get_items_for_date(999888, "2026-08-24")
check("get_items_for_date finds it", len(items) == 1 and items[0]["name"] == "فیزیک فصل ۴")
check("dict has SQLite-style keys (status as int)", items[0]["status"] in (0, 1))

# 7. Bot: get_item_by_id_for_chat (new explicit version)
item = remote_db.get_item_by_id_for_chat(999888, item_id)
check("get_item_by_id_for_chat works", item is not None and item["id"] == item_id)

# old get_item_by_id should raise
try:
    remote_db.get_item_by_id(item_id)
    check("old get_item_by_id raises NotImplementedError", False)
except NotImplementedError:
    check("old get_item_by_id raises NotImplementedError", True)

# 8. Bot: save_study_data_for_chat (the exact call bot.py's save_study_data wrapper makes)
updated = remote_db.save_study_data_for_chat(999888, item_id, minutes=75, tests=15, mark_done=True)
check("save_study_data_for_chat updates minutes/tests/status", updated["study_minutes"] == 75 and updated["test_count"] == 15 and updated["status"] == 1, updated)

# 9. Bot: mark_item_done_for_chat
item_id2 = remote_db.add_plan_item(999888, "ورزش", "2026-08-24", category="غیردرسی")
result = remote_db.mark_item_done_for_chat(999888, item_id2, True)
check("mark_item_done_for_chat sets status", result["status"] == 1)

# 10. Bot: get_items_between
items_range = remote_db.get_items_between(999888, "2026-08-20", "2026-08-28")
check("get_items_between finds both items", len(items_range) == 2)

# 11. Bot: create_makeup_item (new chat_id-first signature)
makeup_id = remote_db.create_makeup_item(999888, {"name": "فیزیک فصل ۴", "category": "درسی"}, "2026-08-25")
makeup_items = remote_db.get_items_for_date(999888, "2026-08-25")
check("create_makeup_item creates '(جبرانی)' item", any("جبرانی" in i["name"] for i in makeup_items), makeup_items)

# 12. Bot: delete_item_for_chat
deleted_ok = remote_db.delete_item_for_chat(999888, item_id2)
check("delete_item_for_chat returns True", deleted_ok == True)
items_after_delete = remote_db.get_items_for_date(999888, "2026-08-24")
check("item actually gone after delete", not any(i["id"] == item_id2 for i in items_after_delete))

# 13. Template cache (in-memory fallback)
check("template cache initially empty", remote_db.get_template_meta_cache(999888, "weekly", "2026-08-22") is None)
remote_db.save_template_meta_cache(999888, "weekly", "2026-08-22", {"goal": "تست"})
check("template cache roundtrip", remote_db.get_template_meta_cache(999888, "weekly", "2026-08-22") == {"goal": "تست"})

# 14. Bot key mismatch protection
os.environ["BOT_API_KEY"] = "wrong-key"
import importlib
importlib.reload(remote_db)
try:
    remote_db.add_plan_item(999888, "x", "2026-08-24")
    r_check = False
except Exception:
    r_check = True
check("wrong bot key gets rejected end-to-end", r_check)

# restore
os.environ["BOT_API_KEY"] = "test-bot-key"
importlib.reload(remote_db)

print("\n" + "=" * 50)
if failures:
    print(f"❌ {len(failures)} TEST(S) FAILED:")
    for f in failures:
        print("  -", f)
    raise SystemExit(1)
else:
    print("✅ ALL INTEGRATION TESTS PASSED (bot <-> live backend)")
