/* =========================================================================
   صفحه پروفایل — تنظیمات، هدف روزانه، گزارش کار درسی (متن آماده برای مشاور)
   ========================================================================= */
SCREENS.profile = function (root) {
  const totalMinutesAllTime = DB.planItems.filter(i=>i.category==='درسی').reduce((s,i)=>s+(i.studyMinutes||0),0);
  const totalTestsAllTime = DB.planItems.filter(i=>i.category==='درسی').reduce((s,i)=>s+(i.testCount||0),0);

  root.innerHTML = `
    <h1 class="page-title">پروفایل</h1>

    <div class="card glass" style="text-align:center; padding:26px 16px;">
      <div style="width:64px;height:64px;border-radius:50%; margin:0 auto 12px; background:linear-gradient(135deg,var(--primary-bright),var(--primary-dim)); display:flex; align-items:center; justify-content:center; font-size:26px; font-weight:800;">
        ${escapeHtml((DB.profile.name||'د')[0])}
      </div>
      <div style="font-weight:800; font-size:16px;">${escapeHtml(DB.profile.name)}</div>
      <div style="font-size:12px; color:var(--text-2); margin-top:2px;">${DB.profile.examTargetLabel ? escapeHtml(DB.profile.examTargetLabel) : 'هدف کنکور ثبت نشده'}</div>
      <div class="grid-2" style="margin-top:18px; text-align:center;">
        <div><div style="font-weight:800; font-size:16px;">${formatMinutes(totalMinutesAllTime)}</div><div style="font-size:11px; color:var(--text-3);">کل مطالعه</div></div>
        <div><div style="font-weight:800; font-size:16px;">${fa(totalTestsAllTime)}</div><div style="font-size:11px; color:var(--text-3);">کل تست‌ها</div></div>
      </div>
    </div>

    <div class="section-head"><h3>تنظیمات</h3></div>
    <div class="card">
      <div class="list-row" onclick="openEditProfileSheet()" style="cursor:pointer;">
        <div class="li-icon"><span class="material-symbols-rounded">edit</span></div>
        <div class="li-body"><div class="li-title">ویرایش اطلاعات</div><div class="li-sub">نام و هدف روزانه</div></div>
        <span class="material-symbols-rounded" style="color:var(--text-3);">chevron_left</span>
      </div>
      <div class="list-row" onclick="openChangePasswordSheet()" style="cursor:pointer;">
        <div class="li-icon"><span class="material-symbols-rounded">password</span></div>
        <div class="li-body"><div class="li-title">تغییر رمز عبور</div><div class="li-sub">رمز فعلی رو وارد کن و رمز جدید بساز</div></div>
        <span class="material-symbols-rounded" style="color:var(--text-3);">chevron_left</span>
      </div>
      <div class="list-row" onclick="openAlarmsSheet()" style="cursor:pointer;">
        <div class="li-icon"><span class="material-symbols-rounded">alarm</span></div>
        <div class="li-body"><div class="li-title">آلارم‌ها</div><div class="li-sub">${fa(DB.alarms.length)} آلارم فعال</div></div>
        <span class="material-symbols-rounded" style="color:var(--text-3);">chevron_left</span>
      </div>
      <div class="list-row" onclick="openStudyReportSheet()" style="cursor:pointer;">
        <div class="li-icon"><span class="material-symbols-rounded">description</span></div>
        <div class="li-body"><div class="li-title">گزارش کار درسی امروز</div><div class="li-sub">متن آماده برای فرستادن به مشاور</div></div>
        <span class="material-symbols-rounded" style="color:var(--text-3);">chevron_left</span>
      </div>
      <div class="list-row" onclick="installPWA()" style="cursor:pointer;">
        <div class="li-icon"><span class="material-symbols-rounded">install_mobile</span></div>
        <div class="li-body"><div class="li-title">نصب روی صفحه اصلی</div><div class="li-sub">استفاده مثل یک اپ واقعی</div></div>
        <span class="material-symbols-rounded" style="color:var(--text-3);">chevron_left</span>
      </div>
      <div class="list-row" onclick="requestNotifPermission()" style="cursor:pointer;">
        <div class="li-icon"><span class="material-symbols-rounded">notifications_active</span></div>
        <div class="li-body"><div class="li-title">مجوز اعلان</div><div class="li-sub">برای دریافت هشدار آلارم‌ها</div></div>
        <span class="material-symbols-rounded" style="color:var(--text-3);">chevron_left</span>
      </div>
    </div>

    ${DB.profile.role === 'admin' ? `
    <div class="section-head"><h3>مدیریت</h3></div>
    <div class="card">
      <div class="list-row" onclick="go('admin')" style="cursor:pointer;">
        <div class="li-icon" style="color:var(--primary-bright);"><span class="material-symbols-rounded">admin_panel_settings</span></div>
        <div class="li-body"><div class="li-title">پنل ادمین</div><div class="li-sub">مدیریت اعضا و مسدودسازی</div></div>
        <span class="material-symbols-rounded" style="color:var(--text-3);">chevron_left</span>
      </div>
    </div>` : ''}

    <div class="section-head"><h3>داده‌ها و حساب</h3></div>
    <div class="card">
      <div class="list-row" onclick="confirmClearAllData()" style="cursor:pointer;">
        <div class="li-icon" style="color:var(--danger);"><span class="material-symbols-rounded">delete_forever</span></div>
        <div class="li-body"><div class="li-title" style="color:var(--danger);">پاک‌کردن همه داده‌ها</div><div class="li-sub">برنامه، سوالات و آزمون‌ها حذف می‌شن</div></div>
      </div>
      <div class="list-row" onclick="logout()" style="cursor:pointer;">
        <div class="li-icon"><span class="material-symbols-rounded">logout</span></div>
        <div class="li-body"><div class="li-title">خروج از حساب</div></div>
      </div>
    </div>

    <p style="text-align:center; font-size:11px; color:var(--text-3); margin-top:20px;">اپکس پلنر — نسخه اپ · متصل به بکند مشترک</p>
  `;
};

function openEditProfileSheet() {
  openSheet(`
    <h2>ویرایش اطلاعات</h2>
    <div class="field"><label>نام</label><input id="pName" type="text" value="${escapeHtml(DB.profile.name)}" /></div>
    <div class="field"><label>هدف کنکور (اختیاری)</label><input id="pGoalLabel" type="text" placeholder="مثلاً تجربی ۱۴۰۵" value="${escapeHtml(DB.profile.examTargetLabel||'')}" /></div>
    <div class="field"><label>هدف مطالعه روزانه (ساعت)</label><input id="pGoalHours" type="number" min="1" max="16" value="${DB.profile.goalHoursPerDay}" /></div>
    <button class="btn btn-primary" onclick="submitProfile()">ذخیره</button>
  `);
}
async function submitProfile() {
  const name = document.getElementById('pName').value.trim() || DB.profile.name;
  const examTargetLabel = document.getElementById('pGoalLabel').value.trim();
  const goalHoursPerDay = parseInt(document.getElementById('pGoalHours').value) || DB.profile.goalHoursPerDay;
  const payload = { display_name: name, exam_target_label: examTargetLabel, goal_hours_per_day: goalHoursPerDay };
  const backup = { ...DB.profile };
  // optimistic: فوراً روی صفحه اعمال می‌شه
  await withDbLock(async () => {
    DB.profile.name = name;
    DB.profile.examTargetLabel = examTargetLabel;
    DB.profile.goalHoursPerDay = goalHoursPerDay;
    await persistDbNow();
  });
  closeSheet();
  rerender();
  try {
    await Api.updateMe(payload);
    await persistDbNow();
    showToast('ذخیره شد');
  } catch (e) {
    if (isOfflineError(e)) {
      await queueOp('update', 'profile', { payload });
      showToast('آفلاین ذخیره شد — با وصل‌شدن اینترنت سینک می‌شه', 'cloud_off');
      return;
    }
    await withDbLock(async () => { Object.assign(DB.profile, backup); await persistDbNow(); });
    rerender();
    showToast('خطا: ' + e.message, 'error');
  }
}

// ---------------------------------------------------------------------------
// تغییر رمز عبور (وقتی لاگین هستی و رمز فعلی رو بلدی)
// ---------------------------------------------------------------------------
function openChangePasswordSheet() {
  openSheet(`
    <h2>تغییر رمز عبور</h2>
    <div class="field"><label>رمز فعلی</label><input id="pCurPass" type="password" placeholder="رمز الان" /></div>
    <div class="field"><label>رمز جدید</label><input id="pNewPass" type="password" placeholder="حداقل ۴ کاراکتر" /></div>
    <div class="field"><label>تکرار رمز جدید</label><input id="pNewPass2" type="password" placeholder="دوباره رمز جدید" /></div>
    <div id="pPassErr" style="display:none; background:rgba(239,68,68,.12); border:1px solid rgba(239,68,68,.3); color:var(--danger); font-size:12.5px; padding:10px 12px; border-radius:10px; margin-bottom:8px;"></div>
    <button class="btn btn-primary" onclick="submitChangePassword()">ذخیره رمز جدید</button>
  `);
}

async function submitChangePassword() {
  const cur = document.getElementById('pCurPass').value;
  const n1 = document.getElementById('pNewPass').value;
  const n2 = document.getElementById('pNewPass2').value;
  const errBox = document.getElementById('pPassErr');
  const showErr = (msg) => { errBox.textContent = msg; errBox.style.display = 'block'; };

  if (!cur) { showErr('رمز فعلی رو وارد کن'); return; }
  if (!n1 || n1.length < 4) { showErr('رمز جدید باید حداقل ۴ کاراکتر باشه'); return; }
  if (n1 !== n2) { showErr('تکرار رمز جدید با رمز جدید یکی نیست'); return; }
  if (n1 === cur) { showErr('رمز جدید نمی‌تونه همون رمز فعلی باشه'); return; }

  try {
    await Api.changePassword(cur, n1);
    closeSheet();
    showToast('رمز عبور با موفقیت تغییر کرد ✅');
  } catch (e) {
    showErr(e.message || 'خطایی پیش اومد');
  }
}

function requestNotifPermission() {
  if (!window.Notification) { showToast('این مرورگر از اعلان پشتیبانی نمی‌کنه'); return; }
  Notification.requestPermission().then(p => {
    showToast(p === 'granted' ? 'مجوز اعلان فعال شد ✅' : 'مجوز داده نشد');
  });
}

function installPWA() {
  openDialog({
    icon: 'install_mobile', title: 'نصب روی صفحه اصلی',
    text: 'از منوی مرورگر (⋮ یا دکمه اشتراک‌گذاری) گزینه «افزودن به صفحه اصلی» یا «Add to Home Screen» رو بزن تا اپکس پلنر مثل یک اپ واقعی روی گوشیت نصب بشه.',
    confirmText: 'متوجه شدم', confirmClass: 'btn-primary', cancelText: 'بستن',
    onConfirm: () => closeDialog()
  });
}

async function confirmClearAllData() {
  // این عملیات مخرب و برگشت‌ناپذیره، پس اگه آفلاینیم یا تغییرات
  // سینک‌نشده‌ای در صفن، اصلاً اجازه نمی‌دیم شروع بشه — چون هم نمی‌شه
  // مطمئن شد همه‌چیز واقعاً از سرور پاک شده، هم ممکنه یه تغییر آفلاینِ
  // قدیمی بعداً به‌اشتباه روی یه دیتای نیمه‌پاک‌شده اعمال بشه.
  const uid_ = currentUserId();
  const pending = uid_ ? await Store.countPending(uid_) : 0;
  if (!navigator.onLine || pending > 0) {
    openDialog({
      icon: 'cloud_off', title: 'الان امکانش نیست',
      text: pending > 0
        ? `${fa(pending)} تغییر هنوز آفلاینه و به سرور نرسیده. برای جلوگیری از تداخل، اول باید این تغییرات سینک بشن (به محض وصل‌شدن اینترنت خودکار انجام می‌شه)، بعد دوباره امتحان کن.`
        : 'برای پاک‌کردن همه‌ی داده‌ها باید آنلاین باشی تا مطمئن بشیم همه‌چیز واقعاً از سرور هم حذف می‌شه.',
      confirmText: 'باشه', cancelText: null,
    });
    return;
  }

  openDialog({
    icon: 'delete_forever', title: 'پاک‌کردن همه داده‌ها',
    text: 'همه برنامه‌ها، سوالات و آزمون‌های حساب تو برای همیشه حذف می‌شن (روی همه‌ی دستگاه‌ها و توی بات هم). این کار قابل بازگشت نیست.',
    confirmText: 'همه‌چیز رو پاک کن', confirmClass: 'btn-danger-ghost',
    onConfirm: async () => {
      closeDialog();
      showToast('در حال پاک‌کردن...');
      try {
        await Promise.all([
          ...DB.planItems.map(i => Api.deletePlanItem(i.id)),
          ...DB.questions.map(q => Api.deleteQuestion(q.id)),
          ...DB.exams.map(e => Api.deleteExam(e.id)),
          ...DB.alarms.map(a => Api.deleteAlarm(a.id)),
        ]);
        await syncFromServer(); // این خودش کش محلی رو هم با نسخه‌ی خالی جدید بازنویسی می‌کنه
        showToast('پاک شد');
        go('home');
      } catch (e) {
        showToast('بعضی موارد پاک نشدن: ' + e.message, 'error');
        await syncFromServer();
        rerender();
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Study report (mirrors send_study_report_for) — shown as read-to-copy text
// ---------------------------------------------------------------------------
function openStudyReportSheet() {
  const text = buildStudyReportText(Jalali.todayStr());
  openSheet(`
    <h2>گزارش کار درسی</h2>
    <p style="font-size:12px; color:var(--text-2); margin-top:-10px; margin-bottom:14px;">این متن رو کپی کن و برای مشاورت بفرست</p>
    <div class="card" style="background:var(--surface-2); white-space:pre-line; font-size:13px; line-height:2; direction:rtl;">${escapeHtml(text)}</div>
    <button class="btn btn-primary" style="margin-top:14px;" onclick="copyReportText()">
      <span class="material-symbols-rounded" style="font-size:18px;">content_copy</span> کپی متن
    </button>
  `);
  window._currentReportText = text;
}
function copyReportText() {
  const text = window._currentReportText || '';
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => showToast('کپی شد ✅')).catch(() => showToast('کپی نشد، دستی کپی کن'));
  } else {
    showToast('کپی نشد، دستی کپی کن');
  }
}
