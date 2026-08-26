# اتصال بات به بکند مشترک — راهنمای دقیق تغییرات bot.py

این فایل نسخه‌ی خیلی بزرگیه (۲۳۰۱ خط) که علاوه بر ذخیره‌سازی محلی، منطق Notion
هم داره. به‌جای بازنویسی کاملش (که ریسک خراب کردن چیزهایی که الان کار می‌کنه رو
داره)، این پچ **فقط ۷ نقطه‌ی مشخص** رو تغییر می‌ده. بقیه‌ی بات (منوها، Notion،
گزارش‌ها، همه) دست‌نخورده می‌مونه.

پیش‌نیاز: فایل `remote_db.py` (که در همین پوشه هست) رو کنار `bot.py` بذار.

---

## تغییر ۱: ایمپورت

```python
# قبل:
import local_db

# بعد:
import remote_db as local_db
```

همه‌جای بات که `local_db.X` صدا زده می‌شه، دیگه نیازی به تغییر نداره چون
`remote_db.py` همون اسم‌ها رو داره. **به‌جز ۶ تابعی که در ادامه اصلاح می‌شن،
چون امضای remote_db براشون نیاز به chat_id اضافه داره.**

---

## تغییر ۲: متغیرهای محیطی جدید

بالای فایل، کنار بقیه‌ی `os.environ`ها اضافه کن:

```python
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
BOT_API_KEY = os.environ.get("BOT_API_KEY", "")
```

(این‌ها در واقع خودِ `remote_db.py` می‌خونتشون؛ این خطوط فقط برای اینکه اگه
`BOT_API_KEY` خالی بود، بات همون اول با خطای واضح متوقف بشه، نه بعد از یک
ساعت دیباگ.) بعد از این خطوط اضافه کن:

```python
if not BOT_API_KEY:
    raise RuntimeError("BOT_API_KEY تنظیم نشده — این بات دیگه بدون بکند کار نمی‌کنه.")
```

---

## تغییر ۳: پنج تابع wrapper که نیاز به chat_id دارن (خط ۳۴۱ تا ۴۱۱)

این ۶ تابع رو دقیقاً پیدا کن و طبق زیر اصلاح کن — فقط شاخه‌ی `else` (غیر Notion)
عوض می‌شه، شاخه‌ی Notion دست‌نخورده می‌مونه:

```python
def mark_item_done(chat_id: int, item_id: str, done: bool = True):
    if _is_notion_user(chat_id):
        notion.pages.update(page_id=item_id, properties={"Status": {"checkbox": done}})
    else:
        local_db.mark_item_done_for_chat(chat_id, item_id, done)   # <-- تغییر


def save_study_data(chat_id: int, item_id: str, minutes: int, tests: int, mark_done: bool = True):
    if _is_notion_user(chat_id):
        properties = {
            "StudyMinutes": {"number": minutes},
            "TestCount": {"number": tests},
        }
        if mark_done:
            properties["Status"] = {"checkbox": True}
        notion.pages.update(page_id=item_id, properties=properties)
    else:
        local_db.save_study_data_for_chat(chat_id, item_id, minutes, tests, mark_done)   # <-- تغییر


def get_item_by_id(chat_id: int, item_id: str) -> dict:
    if _is_notion_user(chat_id):
        page = notion.pages.retrieve(page_id=item_id)
        return _notion_page_to_dict(page)
    else:
        return local_db.get_item_by_id_for_chat(chat_id, item_id)   # <-- تغییر


def delete_item(chat_id: int, item_id: str):
    if _is_notion_user(chat_id):
        notion.pages.update(page_id=item_id, archived=True)
    else:
        local_db.delete_item_for_chat(chat_id, item_id)   # <-- تغییر


def update_item_full(chat_id: int, item_id: str, status: bool = None, minutes: int = None, tests: int = None):
    if _is_notion_user(chat_id):
        properties = {}
        if status is not None:
            properties["Status"] = {"checkbox": status}
        if minutes is not None:
            properties["StudyMinutes"] = {"number": minutes}
        if tests is not None:
            properties["TestCount"] = {"number": tests}
        if properties:
            notion.pages.update(page_id=item_id, properties=properties)
    else:
        local_db.update_item_full_for_chat(chat_id, item_id, status=status, minutes=minutes, tests=tests)   # <-- تغییر


def create_makeup_item(chat_id: int, original_item: dict, tomorrow_date: str):
    if _is_notion_user(chat_id):
        title = original_item["name"]
        category = original_item.get("category", "درسی")
        new_title = title if "(جبرانی)" in title else f"{title} (جبرانی)"
        notion.pages.create(
            parent={"database_id": NOTION_PLAN_DATABASE_ID},
            properties={
                "Name": {"title": [{"text": {"content": new_title}}]},
                "Date": {"date": {"start": tomorrow_date}},
                "Category": {"select": {"name": category}},
                "Status": {"checkbox": False},
            },
        )
    else:
        local_db.create_makeup_item(chat_id, original_item, tomorrow_date)   # <-- تغییر (فقط ترتیب آرگومان‌ها)
```

---

## تغییر ۴: دستور `/link` برای وصل کردن حساب اپ به تلگرام

جایی که بقیه‌ی `CommandHandler`ها تعریف شدن (تابع `start` نزدیکشونه، خط ۱۸۲۱)،
این تابع جدید رو اضافه کن:

```python
async def link_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /link <username> — حساب اپ کاربر رو به همین چت تلگرام وصل می‌کنه."""
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text(
            "برای وصل کردن حسابت به بات، اول توی اپ اپکس پلنر ثبت‌نام کن، "
            "بعد اینجا بزن:\n/link username_خودت"
        )
        return
    username = context.args[0].strip()
    try:
        user = local_db.link_account(chat_id, username)
        await update.message.reply_text(
            f"✅ حساب «{user['display_name']}» با موفقیت به این چت وصل شد!\n"
            "حالا می‌تونی از همه‌ی امکانات بات استفاده کنی."
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ خطا در اتصال: {e}")
```

---

## تغییر ۵: دستورات ادمین `/ban` و `/unban`

همون نزدیکی اضافه کن:

```python
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _set_ban_status(update, context, banned=True)


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _set_ban_status(update, context, banned=False)


async def _set_ban_status(update: Update, context: ContextTypes.DEFAULT_TYPE, banned: bool):
    requester_chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("استفاده: /ban @username یا /ban با ریپلای روی پیام فرد")
        return
    target_username = context.args[0].strip().lstrip("@")

    # این دستور روی username کار می‌کنه؛ برای سادگی، از بکند می‌خوایم کاربر رو
    # با username پیدا کنه و ban کنه — یک اندپوینت کوچیک برای این لازمه که
    # می‌تونی بعداً به /admin/members/by-username/{username}/ban اضافه کنی.
    # فعلاً از طریق پنل ادمین توی اپ این کار راحت‌تره؛ این دستور فقط یک راهنماست:
    await update.message.reply_text(
        "برای بن/آنبن کردن اعضا، فعلاً از پنل ادمین توی اپ استفاده کن "
        "(تب پروفایل > مدیریت اعضا). دلیلش اینه که اونجا لیست کامل با آمار "
        "هر عضو رو هم می‌بینی، تصمیم‌گیری راحت‌تره."
    )
```

> **نکته:** بن‌کردن رو عمداً ساده نگه داشتم و به پنل ادمین اپ ارجاع دادم، چون
> برای گروه ۲-۵ نفره‌ی شما، مدیریت از طریق UI اپ (که آمار هر نفر رو هم نشون
> می‌ده) راحت‌تر و امن‌تر از تایپ دستور تو تلگرامه. اگه بعداً خواستی دستور
> مستقیم `/ban username` هم فعال بشه، به من بگو تا اندپوینت `by-username`
> رو به بکند اضافه کنم و این تابع رو کامل کنم.

---

## تغییر ۶: ثبت دستورهای جدید در `main()`

```python
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("today", today_plan))
application.add_handler(CommandHandler("checklist", manual_checklist))
application.add_handler(CommandHandler("report", manual_report))
application.add_handler(CommandHandler("weekly", send_weekly_stats))
application.add_handler(CommandHandler("link", link_account_command))      # <-- جدید
application.add_handler(CommandHandler("ban", ban_command))                # <-- جدید
application.add_handler(CommandHandler("unban", unban_command))            # <-- جدید
```

---

## تغییر ۷: گزارش خودکار ساعت ۱ بامداد به گروه

`send_study_report` که همین الان ساعت ۱ اجرا می‌شه رو طوری گسترش می‌دیم که
بعد از فرستادن گزارش خصوصی به هرکس، یک خلاصه هم به هر گروهی که عضوهاش بهش
وصلن بفرسته:

```python
async def send_study_report(context: ContextTypes.DEFAULT_TYPE):
    """Job زمان‌بندی‌شده: گزارش کار درسی ساعت ۱ بامداد را برای همه‌ی کاربران می‌فرستد،
    و بعد یک خلاصه‌ی گروهی هم برای هر گروه متصل پست می‌کند."""
    all_chat_ids = [int(TELEGRAM_CHAT_ID)] + local_db.get_all_local_chat_ids()
    for cid in all_chat_ids:
        await send_study_report_for(context, cid)

    await send_group_reports(context)


async def send_group_reports(context: ContextTypes.DEFAULT_TYPE):
    """برای هر گروهی که حداقل یک عضو بهش وصله، خلاصه‌ی کار امروز همه‌ی اون
    اعضا رو به‌صورت یک پیام واحد پست می‌کنه."""
    import requests
    from datetime import date

    today_str = date.today().isoformat()

    # لیست group_id های یکتا رو از بکند نمی‌گیریم چون مسیر مستقیمش نداریم؛
    # ساده‌ترین راه: خودت group_id گروه دوستانه‌تون رو اینجا هاردکد کن، یا
    # (بهتر) از طریق دستور /setgroup توی همون گروه به‌صورت پویا ثبتش کن.
    GROUP_IDS = []  # <-- بعد از راه‌اندازی /setgroup، اینجا دیگه لازم نیست

    for group_id in GROUP_IDS:
        try:
            r = requests.get(
                f"{BACKEND_URL}/bot/group-report/{group_id}",
                headers={"X-Bot-Key": BOT_API_KEY},
                params={"date": today_str},
                timeout=15,
            )
            r.raise_for_status()
            members = r.json()
        except Exception as e:
            logger.error("خطا در گرفتن گزارش گروهی برای %s: %s", group_id, e)
            continue

        if not members:
            continue

        lines = [f"📊 گزارش شب گروه — {today_jalali_str()}\n"]
        for m in members:
            pct = f"{m['completed_items']}/{m['total_items']}" if m["total_items"] else "بدون برنامه"
            lines.append(
                f"👤 {m['display_name']}: {m['total_minutes']} دقیقه، "
                f"{m['total_tests']} تست، {pct} پارت انجام‌شده"
            )
        await context.bot.send_message(chat_id=group_id, text="\n".join(lines))


async def setgroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """این دستور رو خودِ کاربر داخل گروه می‌زنه تا گزارش‌های شبانه‌ش
    برای همون گروه فرستاده بشه."""
    chat_id = update.effective_chat.id
    group_id = update.effective_chat.id if update.effective_chat.type in ("group", "supergroup") else None
    if not group_id:
        await update.message.reply_text("این دستور رو باید داخل خودِ گروه بزنی، نه توی چت خصوصی.")
        return
    import requests
    try:
        requests.post(
            f"{BACKEND_URL}/bot/set-group/{update.effective_user.id}",
            headers={"X-Bot-Key": BOT_API_KEY},
            params={"group_id": group_id},
            timeout=15,
        ).raise_for_status()
        await update.message.reply_text("✅ از حالا گزارش شبانه‌ات همین‌جا هم پست می‌شه.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ خطا: {e}")
```

و توی `main()`:
```python
application.add_handler(CommandHandler("setgroup", setgroup_command))
```

> **توضیح مهم درباره‌ی `/setgroup`:** توی این دستور از `update.effective_user.id`
> استفاده کردم نه `chat_id` گروه — چون باید بدونیم *کدوم کاربر* می‌خواد
> گزارشش بره تو گروه، نه اینکه گروه به خودش وصل بشه. یعنی هرکسی که عضو
> گروهه، یک‌بار داخل گروه `/setgroup` رو می‌زنه، و از اون به بعد گزارش
> شخصیش شب‌ها اونجا هم پست می‌شه.

---

## خلاصه: چک‌لیست نهایی قبل از دیپلوی

- [ ] `remote_db.py` رو کنار `bot.py` توی همون ریپو/فولدر بذار
- [ ] `requirements.txt` بات رو با `requests` آپدیت کن (اگه از قبل نداره)
- [ ] ۷ تغییر بالا رو توی `bot.py` اعمال کن
- [ ] روی Railway، تنظیمات سرویس بات، این دو متغیر رو اضافه کن:
      - `BACKEND_URL` = آدرس سرویس بکندی که جدا دیپلوی کردی
      - `BOT_API_KEY` = دقیقاً همون مقداری که توی سرویس بکند ست کردی
- [ ] هر عضو گروه اول باید توی اپ ثبت‌نام کنه (username/password)
- [ ] بعد توی بات بزنه: `/link username_خودش`
- [ ] داخل گروه دوستانه، هرکی بخواد گزارشش پست بشه بزنه: `/setgroup`
