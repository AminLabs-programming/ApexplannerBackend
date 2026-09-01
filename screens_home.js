/* =========================================================================
   صفحه خانه (داشبورد)
   ========================================================================= */
SCREENS.home = function (root) {
  const today = Jalali.todayStr();
  const items = getItemsForDate(today);
  const lessonItems = items.filter(i => i.category === 'درسی');
  const doneCount = items.filter(i => i.status).length;
  const totalCount = items.length;
  const percent = totalCount ? Math.round((doneCount / totalCount) * 100) : 0;
  const studyMinutesToday = lessonItems.reduce((s, i) => s + (i.status || i.studyMinutes > 0 ? i.studyMinutes : 0), 0);
  const testsToday = lessonItems.reduce((s, i) => s + (i.status || i.testCount > 0 ? i.testCount : 0), 0);
  const goalHours = DB.profile.goalHoursPerDay || 5;

  // streak: consecutive days (up to 7 shown) where at least 1 item completed
  const last7 = [];
  for (let i = 6; i >= 0; i--) {
    const d = Jalali.addDays(today, -i);
    const dItems = getItemsForDate(d);
    const done = dItems.length > 0 && dItems.every(x => x.status) && dItems.length > 0;
    const anyDone = dItems.some(x => x.status);
    last7.push({ date: d, anyDone, isToday: d === today });
  }
  let streak = 0;
  for (let i = 6; i >= 0; i--) {
    if (last7[i].anyDone) streak++; else if (last7[i].date !== today) break; else continue;
  }

  const circumference = 2 * Math.PI * 26;
  const ringOffset = circumference - (percent / 100) * circumference;

  root.innerHTML = `
    <h1 class="page-title">سلام ${escapeHtml(DB.profile.name)} 👋</h1>
    <p class="page-sub">امروز برای رسیدن به هدفت آماده‌ای؟</p>

    <div class="grid-2">
      <div class="card stat-card">
        <div class="stat-icon"><span class="material-symbols-rounded">flag</span></div>
        <div class="stat-label">هدف امروز</div>
        <div class="stat-value">${fa(goalHours)} ساعت</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon"><span class="material-symbols-rounded">hourglass_top</span></div>
        <div class="stat-label">مطالعه امروز</div>
        <div class="stat-value">${formatMinutes(studyMinutesToday)}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon"><span class="material-symbols-rounded">progress_activity</span></div>
        <div class="stat-label">اجرای برنامه</div>
        <div style="display:flex; align-items:center; gap:10px;">
          <div class="ring-wrap" style="width:52px;height:52px;">
            <svg viewBox="0 0 60 60" width="52" height="52">
              <circle class="ring-bg" cx="30" cy="30" r="26"></circle>
              <circle class="ring-fg" cx="30" cy="30" r="26" stroke-dasharray="${circumference}" stroke-dashoffset="${ringOffset}"></circle>
            </svg>
            <div class="ring-label">${fa(percent)}٪</div>
          </div>
        </div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon"><span class="material-symbols-rounded">edit_note</span></div>
        <div class="stat-label">تست امروز</div>
        <div class="stat-value">${fa(testsToday)}</div>
      </div>
    </div>

    <div class="card" style="margin-top:12px;">
      <div style="display:flex; align-items:center; gap:6px; font-weight:700; font-size:14px;">
        <span style="color:var(--warning);">🔥</span> ${fa(streak)} روز استمرار
      </div>
      <div class="streak-row">
        ${last7.map(d => {
          const { y, m, d: dd } = Jalali.strToDate(d.date);
          const wd = Jalali.weekdayOf(y, m, dd);
          const jp = Jalali.gregorianStrToJalaliParts(d.date);
          const cls = d.isToday ? 'today' : (d.anyDone ? 'done' : '');
          const inner = d.isToday ? fa(jp.jd) : (d.anyDone ? '✓' : fa(jp.jd));
          return `<div class="streak-day"><span class="d-lbl">${Jalali.WEEKDAYS[wd][0]}</span><div class="streak-dot ${cls}">${inner}</div></div>`;
        }).join('')}
      </div>
    </div>

    <div class="btn-row" style="margin-top:16px;">
      <button class="btn btn-primary" onclick="openAddPlanSheet()">
        <span class="material-symbols-rounded" style="font-size:19px;">add</span> افزودن برنامه
      </button>
      <button class="btn btn-ghost" onclick="go('timer')">
        <span class="material-symbols-rounded" style="font-size:19px;">timer</span> ثبت مطالعه
      </button>
    </div>

    <div class="section-head">
      <h3>برنامه امروز</h3>
      <span class="more" onclick="go('plan')">مشاهده همه ›</span>
    </div>
    <div id="homePlanList"></div>
  `;

  const listEl = root.querySelector('#homePlanList');
  if (!items.length) {
    listEl.innerHTML = emptyState('event_busy', 'برای امروز برنامه‌ای ثبت نشده', 'با دکمه «افزودن برنامه» شروع کن');
  } else {
    const sorted = [...items].sort((a, b) => (a.status === b.status ? 0 : a.status ? 1 : -1));
    listEl.innerHTML = sorted.slice(0, 6).map(renderPlanItemRow).join('');
  }
};

function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function emptyState(icon, title, sub) {
  return `<div class="empty"><span class="material-symbols-rounded">${icon}</span><div style="font-weight:700; font-size:14px; color:var(--text-1);">${title}</div><p>${sub}</p></div>`;
}

function categoryClass(cat) {
  return 'cat-' + cat.replace(/\s/g, '_');
}

function renderPlanItemRow(item) {
  return `
    <div class="plan-item ${item.status ? 'done' : ''}" data-id="${item.id}">
      <div class="check-circle ${item.status ? 'done' : ''}" onclick="openEditPlanSheet('${item.id}')">
        <span class="material-symbols-rounded" style="font-size:15px;">check</span>
      </div>
      <div style="flex:1; min-width:0;" onclick="openEditPlanSheet('${item.id}')">
        <div class="plan-title">${escapeHtml(item.name)}</div>
        <div class="plan-meta">
          <span><span class="cat-dot ${categoryClass(item.category)}"></span>${item.category}</span>
          ${item.timeLabel ? `<span><span class="material-symbols-rounded" style="font-size:13px;">schedule</span>${escapeHtml(item.timeLabel)}</span>` : ''}
          ${item.status ? `<span><span class="material-symbols-rounded" style="font-size:13px;">hourglass_top</span>${fa(item.studyMinutes)} دقیقه</span>` : ''}
        </div>
      </div>
    </div>`;
}
