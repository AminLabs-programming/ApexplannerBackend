/* =========================================================================
   پنل ادمین — لیست اعضا، آمار ۷ روز اخیر، بن/آنبن، حذف عضو
   فقط برای کاربری که role='admin' داره قابل دسترسیه (چک اصلی سمت بکنده،
   این صفحه فقط UI رو نشون نمی‌ده اگه دسترسی نداشته باشه).
   ========================================================================= */
let adminMembers = null;
let adminLoading = false;
let adminNotionStatus = null;
let adminNotionSyncing = false;
let adminNotionLastResult = null;

SCREENS.admin = function (root) {
  if (DB.profile.role !== 'admin') {
    root.innerHTML = emptyState('lock', 'دسترسی نداری', 'این بخش فقط برای ادمین گروهه');
    return;
  }
  if (!navigator.onLine) {
    root.innerHTML = `
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
        <button class="icon-btn" onclick="go('profile')"><span class="material-symbols-rounded">arrow_forward</span></button>
        <h1 class="page-title" style="margin:0;">پنل ادمین</h1>
      </div>
      ` + emptyState('cloud_off', 'نیاز به اینترنت', 'مدیریت اعضا و همگام‌سازی Notion فقط وقتی آنلاینی در دسترسه. بقیه‌ی بخش‌های اپ (برنامه، سوالات، تایمر و...) همچنان آفلاین کار می‌کنن.');
    return;
  }

  root.innerHTML = `
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
      <button class="icon-btn" onclick="go('profile')"><span class="material-symbols-rounded">arrow_forward</span></button>
      <h1 class="page-title" style="margin:0;">پنل ادمین</h1>
    </div>
    <p class="page-sub">مدیریت اعضای گروه</p>

    <div class="card" style="margin-top:14px;">
      <div style="display:flex; align-items:center; gap:8px;">
        <span class="material-symbols-rounded" style="color:var(--primary-bright);">sync</span>
        <div style="font-weight:800; font-size:14.5px;">همگام‌سازی از Notion</div>
      </div>
      <div id="adminNotionBody" style="margin-top:10px;"></div>
    </div>

    <div id="adminMembersList"></div>
  `;

  renderAdminNotionSection();
  loadAdminNotionStatus().then(() => { if (currentScreen === 'admin') renderAdminNotionSection(); });

  const listEl = root.querySelector('#adminMembersList');
  if (adminLoading) {
    listEl.innerHTML = `<div class="empty"><span class="material-symbols-rounded">hourglass_top</span><p>در حال بارگذاری...</p></div>`;
  }

  loadAdminMembers().then(() => {
    if (currentScreen === 'admin') renderAdminMembersList();
  });

  if (adminMembers) renderAdminMembersListInto(listEl);
};

async function loadAdminNotionStatus() {
  try {
    adminNotionStatus = await Api.adminNotionStatus();
  } catch (e) {
    adminNotionStatus = { configured: false, database_id_set: false };
  }
}

function renderAdminNotionSection() {
  const el = document.getElementById('adminNotionBody');
  if (!el) return;

  if (!adminNotionStatus) {
    el.innerHTML = `<p style="font-size:12.5px; color:var(--text-3);">در حال بررسی تنظیمات...</p>`;
    return;
  }

  if (!adminNotionStatus.configured) {
    el.innerHTML = `
      <p style="font-size:12.5px; color:var(--text-3); line-height:1.9;">
        هنوز به Notion وصل نشدی. توی تنظیمات سرویس بکند روی Railway، دو متغیر
        <code>NOTION_API_KEY</code> و <code>NOTION_DATABASE_ID</code> رو ست کن
        (همون‌هایی که بات تلگرام استفاده می‌کنه)، بعد سرویس رو ری‌استارت کن.
      </p>`;
    return;
  }

  el.innerHTML = `
    <p style="font-size:12.5px; color:var(--text-3); line-height:1.9;">
      برنامه‌های ثبت‌شده توی دیتابیس Notion رو می‌کشه و به برنامه‌ی خودت (ادمین) توی اپ اضافه/آپدیت می‌کنه.
      آیتم‌هایی که قبلاً سینک شدن دوباره تکراری نمی‌شن.
    </p>
    <div class="btn-row" style="margin-top:10px;">
      <button class="btn-sm btn-primary" style="flex:1;" ${adminNotionSyncing ? 'disabled' : ''} onclick="runAdminNotionSync()">
        ${adminNotionSyncing ? 'در حال همگام‌سازی...' : 'همگام‌سازی الان'}
      </button>
    </div>
    ${adminNotionLastResult ? `
      <div style="margin-top:10px; font-size:12px; color:var(--text-2);">
        ${fa(adminNotionLastResult.created)} آیتم جدید اضافه شد ·
        ${fa(adminNotionLastResult.updated)} آیتم آپدیت شد ·
        از ${fa(adminNotionLastResult.total_from_notion)} آیتم Notion
      </div>` : ''}
  `;
}

async function runAdminNotionSync() {
  adminNotionSyncing = true;
  renderAdminNotionSection();
  try {
    adminNotionLastResult = await Api.adminNotionSync();
    showToast('همگام‌سازی با Notion انجام شد');
    // آیتم‌های تازه از Notion اومدن؛ دیتای محلی اپ رو دوباره از سرور می‌کشیم
    // تا صفحه‌ی برنامه/خانه/آمار همون لحظه به‌روز باشن.
    await syncFromServer();
  } catch (e) {
    showToast('خطا در همگام‌سازی: ' + e.message, 'error');
  }
  adminNotionSyncing = false;
  renderAdminNotionSection();
}

async function loadAdminMembers() {
  adminLoading = true;
  try {
    adminMembers = await Api.adminListMembers();
  } catch (e) {
    showToast('خطا در بارگذاری اعضا: ' + e.message, 'error');
    adminMembers = [];
  }
  adminLoading = false;
}

function renderAdminMembersList() {
  const listEl = document.getElementById('adminMembersList');
  if (listEl) renderAdminMembersListInto(listEl);
}

function renderAdminMembersListInto(listEl) {
  if (!adminMembers || !adminMembers.length) {
    listEl.innerHTML = emptyState('group', 'عضوی پیدا نشد', '');
    return;
  }
  listEl.innerHTML = adminMembers.map(m => `
    <div class="card" style="margin-top:12px; ${m.is_banned ? 'opacity:.6;' : ''}">
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <div style="font-weight:800; font-size:14.5px; display:flex; align-items:center; gap:6px;">
            ${escapeHtml(m.display_name)}
            ${m.role === 'admin' ? '<span class="chip" style="background:rgba(251,191,36,.15); color:var(--gold);">ادمین</span>' : ''}
            ${m.is_banned ? '<span class="chip" style="background:rgba(239,68,68,.15); color:var(--danger);">مسدود</span>' : ''}
          </div>
          <div style="font-size:11.5px; color:var(--text-3); margin-top:2px;">@${escapeHtml(m.username)} ${m.telegram_chat_id ? '· وصل به تلگرام ✓' : '· به تلگرام وصل نیست'}</div>
        </div>
      </div>
      <div class="grid-2" style="margin-top:12px;">
        <div style="text-align:center;">
          <div style="font-weight:800; font-size:15px;">${formatMinutes(m.total_minutes_last_7d)}</div>
          <div style="font-size:10.5px; color:var(--text-3);">مطالعه ۷ روز اخیر</div>
        </div>
        <div style="text-align:center;">
          <div style="font-weight:800; font-size:15px;">${fa(m.total_tests_last_7d)}</div>
          <div style="font-size:10.5px; color:var(--text-3);">تست ۷ روز اخیر</div>
        </div>
      </div>
      ${m.role !== 'admin' ? `
      <div class="btn-row" style="margin-top:12px;">
        <button class="btn-sm ${m.is_banned ? 'btn-primary' : 'btn-danger-ghost'}" style="flex:1;" onclick="toggleMemberBan(${m.id}, ${!m.is_banned})">
          ${m.is_banned ? 'رفع مسدودیت' : 'مسدود کردن'}
        </button>
        <button class="btn-sm btn-ghost" style="flex:1;" onclick="confirmDeleteMember(${m.id}, '${escapeHtml(m.display_name)}')">حذف کامل</button>
      </div>` : ''}
    </div>
  `).join('');
}

async function toggleMemberBan(userId, banned) {
  try {
    await Api.adminSetBan(userId, banned);
    showToast(banned ? 'کاربر مسدود شد' : 'مسدودیت برداشته شد');
    await loadAdminMembers();
    renderAdminMembersList();
  } catch (e) {
    showToast('خطا: ' + e.message, 'error');
  }
}

function confirmDeleteMember(userId, name) {
  openDialog({
    icon: 'person_remove', title: `حذف ${name}`,
    text: 'حساب این عضو و تمام برنامه/سوال/آزمون‌هاش برای همیشه حذف می‌شه. مطمئنی؟',
    confirmText: 'حذف کن', confirmClass: 'btn-danger-ghost',
    onConfirm: async () => {
      try {
        await Api.adminDeleteMember(userId);
        closeDialog();
        showToast('عضو حذف شد');
        await loadAdminMembers();
        renderAdminMembersList();
      } catch (e) {
        showToast('خطا: ' + e.message, 'error');
      }
    }
  });
}
