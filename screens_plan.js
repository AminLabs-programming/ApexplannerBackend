/* =========================================================================
   صفحه برنامه — چک‌لیست روز با ناوبری تاریخ
   ========================================================================= */
let planViewDate = null;

SCREENS.plan = function (root) {
  if (!planViewDate) planViewDate = Jalali.todayStr();
  const dateStr = planViewDate;
  const items = getItemsForDate(dateStr);
  const isToday = dateStr === Jalali.todayStr();
  const jp = Jalali.gregorianStrToJalaliParts(dateStr);
  const { y, m, d: dd } = Jalali.strToDate(dateStr);
  const wd = Jalali.weekdayOf(y, m, dd);

  const doneCount = items.filter(i => i.status).length;
  const percent = items.length ? Math.round((doneCount / items.length) * 100) : 0;

  root.innerHTML = `
    <h1 class="page-title">برنامه</h1>
    <p class="page-sub">مدیریت روزانه پارت‌های درسی و کارها</p>

    <div class="card" style="padding:12px 14px;">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <button class="icon-btn" onclick="shiftPlanDate(1)"><span class="material-symbols-rounded">chevron_right</span></button>
        <div style="text-align:center;">
          <div style="font-weight:800; font-size:15px;">${isToday ? 'امروز' : Jalali.WEEKDAYS[wd]}</div>
          <div style="font-size:12px; color:var(--text-2); margin-top:2px;">${fa(jp.jd)} ${Jalali.MONTHS[jp.jm - 1]} ${fa(jp.jy)}</div>
        </div>
        <button class="icon-btn" onclick="shiftPlanDate(-1)"><span class="material-symbols-rounded">chevron_left</span></button>
      </div>
    </div>

    ${items.length ? `
    <div class="card" style="margin-top:12px;">
      <div style="display:flex; justify-content:space-between; font-size:12.5px; color:var(--text-2); margin-bottom:8px;">
        <span>${fa(doneCount)} از ${fa(items.length)} انجام شد</span>
        <span>${fa(percent)}٪</span>
      </div>
      <div class="pbar"><div style="width:${percent}%"></div></div>
    </div>` : ''}

    <div class="filter-scroll" style="margin-top:16px;">
      <button class="chip ${planFilter==='all'?'on':''}" onclick="setPlanFilter('all')">همه</button>
      <button class="chip ${planFilter==='درسی'?'on':''}" onclick="setPlanFilter('درسی')">درسی</button>
      <button class="chip ${planFilter==='توسعه فردی'?'on':''}" onclick="setPlanFilter('توسعه فردی')">توسعه فردی</button>
      <button class="chip ${planFilter==='غیردرسی'?'on':''}" onclick="setPlanFilter('غیردرسی')">غیردرسی</button>
    </div>

    <div id="planList"></div>

    <button class="btn btn-primary" style="margin-top:18px;" onclick="openAddPlanSheet('${dateStr}')">
      <span class="material-symbols-rounded" style="font-size:19px;">add</span> افزودن پارت جدید
    </button>
  `;

  const filtered = planFilter === 'all' ? items : items.filter(i => i.category === planFilter);
  const listEl = root.querySelector('#planList');
  if (!filtered.length) {
    listEl.innerHTML = emptyState('event_busy', 'برنامه‌ای برای این روز نیست', 'با دکمه پایین یه پارت جدید اضافه کن');
  } else {
    const sorted = [...filtered].sort((a, b) => (a.status === b.status ? 0 : a.status ? 1 : -1));
    listEl.innerHTML = sorted.map(it => renderPlanItemRowFull(it)).join('');
  }
};

let planFilter = 'all';
function setPlanFilter(f) { planFilter = f; rerender(); }
function shiftPlanDate(delta) {
  planViewDate = Jalali.addDays(planViewDate, delta);
  rerender();
}

function renderPlanItemRowFull(item) {
  return `
    <div class="plan-item ${item.status ? 'done' : ''}" data-id="${item.id}">
      <div class="check-circle ${item.status ? 'done' : ''}" onclick="onTogglePlanItem('${item.id}')">
        <span class="material-symbols-rounded" style="font-size:15px;">check</span>
      </div>
      <div style="flex:1; min-width:0;" onclick="openEditPlanSheet('${item.id}')">
        <div class="plan-title">${escapeHtml(item.name)}</div>
        <div class="plan-meta">
          <span><span class="cat-dot ${categoryClass(item.category)}"></span>${item.category}</span>
          ${item.timeLabel ? `<span><span class="material-symbols-rounded" style="font-size:13px;">schedule</span>${escapeHtml(item.timeLabel)}</span>` : ''}
          ${item.status ? `<span><span class="material-symbols-rounded" style="font-size:13px;">hourglass_top</span>${fa(item.studyMinutes)} دقیقه</span><span><span class="material-symbols-rounded" style="font-size:13px;">edit_note</span>${fa(item.testCount)} تست</span>` : ''}
        </div>
      </div>
      <button class="icon-btn" style="width:30px;height:30px;" onclick="event.stopPropagation(); confirmDeleteItem('${item.id}')">
        <span class="material-symbols-rounded" style="font-size:16px;">delete</span>
      </button>
    </div>`;
}

// ---------------------------------------------------------------------------
// Add / Edit plan item sheet
// ---------------------------------------------------------------------------
function openAddPlanSheet(dateStr) {
  const date = dateStr || planViewDate || Jalali.todayStr();
  openSheet(`
    <h2>افزودن پارت برنامه</h2>
    <div class="field">
      <label>عنوان (مثلاً «فیزیک فصل ۲»)</label>
      <input id="fName" type="text" placeholder="نام درس یا فعالیت" />
    </div>
    <div class="field">
      <label>تاریخ</label>
      <input id="fDate" type="date" value="${toIsoForInput(date)}" />
    </div>
    <div class="field">
      <label>دسته</label>
      <div class="seg" id="fCatSeg">
        ${CATEGORIES.map((c, i) => `<button type="button" class="${i===0?'active':''}" data-cat="${c}">${c}</button>`).join('')}
      </div>
    </div>
    <div class="field">
      <label>بازه زمانی (اختیاری، مثلاً ۰۸:۰۰-۰۹:۳۰)</label>
      <input id="fTime" type="text" placeholder="۰۸:۰۰-۰۹:۳۰" />
    </div>
    <button class="btn btn-primary" onclick="submitAddPlan()">افزودن به برنامه</button>
  `);
  wireSeg('fCatSeg');
}

function wireSeg(id) {
  const seg = document.getElementById(id);
  seg.querySelectorAll('button').forEach(b => {
    b.onclick = () => { seg.querySelectorAll('button').forEach(x => x.classList.remove('active')); b.classList.add('active'); };
  });
}

async function submitAddPlan() {
  const name = document.getElementById('fName').value.trim();
  const isoDate = document.getElementById('fDate').value;
  const cat = document.querySelector('#fCatSeg button.active').dataset.cat;
  const timeLabel = document.getElementById('fTime').value.trim();
  if (!name) { showToast('عنوان رو وارد کن', 'error'); return; }
  if (!isoDate) { showToast('تاریخ رو انتخاب کن', 'error'); return; }
  try {
    await addPlanItem({ name, date: isoDate, category: cat, timeLabel });
    closeSheet();
    showToast('پارت جدید اضافه شد');
    rerender();
  } catch (e) { /* توست خطا داخل addPlanItem نمایش داده می‌شه */ }
}

function toIsoForInput(gStr) { return gStr; } // already YYYY-MM-DD

function openEditPlanSheet(id) {
  const item = getItemById(id);
  if (!item) return;
  openSheet(`
    <h2>ویرایش پارت</h2>
    <div class="field"><label>عنوان</label><input id="eName" type="text" value="${escapeHtml(item.name)}" /></div>
    <div class="field"><label>تاریخ</label><input id="eDate" type="date" value="${toIsoForInput(item.date)}" /></div>
    <div class="field">
      <label>دسته</label>
      <div class="seg" id="eCatSeg">
        ${CATEGORIES.map(c => `<button type="button" class="${c===item.category?'active':''}" data-cat="${c}">${c}</button>`).join('')}
      </div>
    </div>
    ${item.category === 'درسی' ? `
    <div class="field"><label>دقیقه مطالعه</label><input id="eMinutes" type="number" min="0" value="${item.studyMinutes}" /></div>
    <div class="field"><label>تعداد تست</label><input id="eTests" type="number" min="0" value="${item.testCount}" /></div>
    ` : ''}
    <div class="btn-row">
      <button class="btn btn-primary" onclick="submitEditPlan('${id}')">ذخیره</button>
      <button class="btn btn-danger-ghost" onclick="confirmDeleteItem('${id}')">حذف</button>
    </div>
  `);
  wireSeg('eCatSeg');
}

async function submitEditPlan(id) {
  const item = getItemById(id);
  if (!item) return;
  const patch = {
    name: document.getElementById('eName').value.trim() || item.name,
    date: document.getElementById('eDate').value || item.date,
    category: document.querySelector('#eCatSeg button.active').dataset.cat,
  };
  const mEl = document.getElementById('eMinutes');
  const tEl = document.getElementById('eTests');
  if (mEl) patch.studyMinutes = parseInt(mEl.value) || 0;
  if (tEl) patch.testCount = parseInt(tEl.value) || 0;
  try {
    await updatePlanItemRemote(id, patch);
    closeSheet();
    showToast('ذخیره شد');
    rerender();
  } catch (e) { /* توست خطا داخل updatePlanItemRemote نمایش داده می‌شه */ }
}

function confirmDeleteItem(id) {
  openDialog({
    icon: 'delete', title: 'حذف پارت برنامه',
    text: 'مطمئنی می‌خوای این پارت رو حذف کنی؟ این کار قابل بازگشت نیست.',
    confirmText: 'حذف کن', confirmClass: 'btn-danger-ghost',
    onConfirm: async () => {
      try {
        await deleteItem(id);
        closeSheet(); showToast('حذف شد', 'delete'); rerender();
      } catch (e) { closeDialog(); }
    }
  });
}

// ---------------------------------------------------------------------------
// Study log sheet — when checking off a "درسی" item, ask minutes + tests
// (mirrors the bot's _study_report_state flow)
// ---------------------------------------------------------------------------
function openStudyLogSheet(id) {
  const item = getItemById(id);
  if (!item) return;
  openSheet(`
    <h2>ثبت مطالعه — ${escapeHtml(item.name)}</h2>
    <p style="font-size:12.5px; color:var(--text-2); margin-top:-10px; margin-bottom:16px;">چند دقیقه خوندی و چند تا تست زدی؟</p>
    <div class="field"><label>دقیقه مطالعه</label><input id="sMinutes" type="number" min="0" placeholder="مثلاً ۹۰" autofocus /></div>
    <div class="field"><label>تعداد تست</label><input id="sTests" type="number" min="0" placeholder="مثلاً ۲۰" /></div>
    <div class="btn-row">
      <button class="btn btn-primary" onclick="submitStudyLog('${id}', true)">تکمیل شد ✅</button>
      <button class="btn btn-ghost" onclick="submitStudyLog('${id}', false)">ناقص، فعلاً همین</button>
    </div>
  `);
}
async function submitStudyLog(id, markDone) {
  const minutes = parseInt(document.getElementById('sMinutes').value) || 0;
  const tests = parseInt(document.getElementById('sTests').value) || 0;
  try {
    await saveStudyData(id, minutes, tests, markDone);
    closeSheet();
    showToast(markDone ? 'عالی بود! ثبت شد 🎉' : 'ثبت شد، بعداً ادامه بده');
    rerender();
  } catch (e) { /* توست خطا داخل saveStudyData نمایش داده می‌شه */ }
}
