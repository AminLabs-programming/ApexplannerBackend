/* =========================================================================
   صفحه تحلیل — سه زیربخش: ساعت مطالعه / آزمون‌ها / مقایسه آزمون‌به‌آزمون
   ========================================================================= */
let statsTab = 'study';   // study | exams | compare
let statsWeekOffset = 0;   // 0 = current week

SCREENS.stats = function (root) {
  root.innerHTML = `
    <h1 class="page-title">تحلیل عملکرد</h1>
    <p class="page-sub">روند مطالعه و آزمون‌هات رو زیر ذره‌بین ببر</p>

    <div class="seg" style="margin-bottom:18px;">
      <button class="${statsTab==='study'?'active':''}" onclick="statsTab='study'; rerender();">ساعت مطالعه</button>
      <button class="${statsTab==='exams'?'active':''}" onclick="statsTab='exams'; rerender();">آزمون‌ها</button>
      <button class="${statsTab==='compare'?'active':''}" onclick="statsTab='compare'; rerender();">مقایسه</button>
    </div>

    <div id="statsBody"></div>
  `;
  const body = root.querySelector('#statsBody');
  if (statsTab === 'study') renderStudyTab(body);
  else if (statsTab === 'exams') renderExamsTab(body);
  else renderCompareTab(body);
};

// ---------------------------------------------------------------------------
// Tab 1: Study hours (mirrors build_weekly_pdf_data)
// ---------------------------------------------------------------------------
function renderStudyTab(root) {
  const today = Jalali.todayStr();
  const refDate = Jalali.addDays(today, -7 * statsWeekOffset);
  const [wStart, wEnd] = Jalali.weeklyStatsRange(refDate);
  const stats = buildWeeklyStats(wStart, wEnd);
  const maxHour = Math.max(1, ...stats.dayHours);

  root.innerHTML = `
    <div class="card" style="padding:12px 14px;">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <button class="icon-btn" onclick="statsWeekOffset++; rerender();"><span class="material-symbols-rounded">chevron_right</span></button>
        <div style="text-align:center; font-size:12.5px; font-weight:700;">${Jalali.formatJalaliRange(wStart, wEnd)}</div>
        <button class="icon-btn" ${statsWeekOffset<=0?'style="opacity:.3; pointer-events:none;"':''} onclick="statsWeekOffset--; rerender();"><span class="material-symbols-rounded">chevron_left</span></button>
      </div>
    </div>

    <div class="grid-2" style="margin-top:12px;">
      <div class="card stat-card">
        <div class="stat-icon"><span class="material-symbols-rounded">timer</span></div>
        <div class="stat-label">جمع ساعت هفته</div>
        <div class="stat-value">${formatMinutes(stats.totalMinutes)}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon"><span class="material-symbols-rounded">trending_up</span></div>
        <div class="stat-label">میانگین روزانه</div>
        <div class="stat-value">${formatMinutes(stats.avgMinutes)}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon"><span class="material-symbols-rounded">edit_note</span></div>
        <div class="stat-label">جمع تست‌ها</div>
        <div class="stat-value">${fa(stats.totalTests)}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon"><span class="material-symbols-rounded">task_alt</span></div>
        <div class="stat-label">پارت کامل‌شده</div>
        <div class="stat-value">${fa(stats.completed)}</div>
      </div>
    </div>

    <div class="card" style="margin-top:12px;">
      <div style="font-weight:700; font-size:14px; margin-bottom:14px;">ساعت مطالعه به تفکیک روز</div>
      <div class="barchart">
        ${stats.dayHours.map((h, i) => {
          const isToday = wStart && Jalali.addDays(wStart, i) === today;
          const pct = maxHour > 0 ? Math.max(4, (h / maxHour) * 100) : 4;
          return `<div class="barcol ${isToday?'today':''}">
            <div style="font-size:10px; color:var(--text-2); font-weight:700;">${h>0?fa(h):''}</div>
            <div class="bar" style="height:100px;"><div style="height:${pct}%"></div></div>
            <div class="bar-label">${stats.dayLabels[i]?.slice(0,1)||''}</div>
          </div>`;
        }).join('')}
      </div>
    </div>

    <div class="card" style="margin-top:12px; display:flex; justify-content:space-between; gap:10px;">
      <div style="text-align:center; flex:1;">
        <div style="font-size:11.5px; color:var(--text-2);">بهترین روز</div>
        <div style="font-weight:800; font-size:14px; margin-top:4px; color:var(--success);">${stats.bestDay||'-'}</div>
        <div style="font-size:11px; color:var(--text-3);">${fa(stats.bestDayHours||0)} ساعت</div>
      </div>
      <div style="width:1px; background:var(--border-soft);"></div>
      <div style="text-align:center; flex:1;">
        <div style="font-size:11.5px; color:var(--text-2);">کم‌کارترین روز</div>
        <div style="font-weight:800; font-size:14px; margin-top:4px; color:var(--warning);">${stats.worstDay||'-'}</div>
        <div style="font-size:11px; color:var(--text-3);">${fa(stats.worstDayHours||0)} ساعت</div>
      </div>
    </div>

    <div class="section-head"><h3>به تفکیک درس</h3></div>
    <div class="card">
      ${stats.subjects.length ? stats.subjects.map(s => `
        <div style="margin-bottom:14px;">
          <div style="display:flex; justify-content:space-between; font-size:13px; margin-bottom:6px;">
            <span style="font-weight:700;">${escapeHtml(s.name)}</span>
            <span style="color:var(--text-2);">${formatMinutes(s.minutes)} · ${fa(s.tests)} تست</span>
          </div>
          <div class="pbar thin"><div style="width:${s.percent}%"></div></div>
        </div>`).join('') : `<div style="color:var(--text-2); font-size:13px; text-align:center; padding:10px 0;">دیتایی برای این هفته نیست</div>`}
    </div>

    ${(stats.missedItems.length || stats.partialItems.length) ? `
    <div class="section-head"><h3>پارت‌های ناقص/جامانده</h3></div>
    <div class="card">
      ${stats.partialItems.map(t => `<div style="font-size:12.5px; color:var(--warning); padding:6px 0; border-bottom:1px solid var(--border-soft);">🟡 ${escapeHtml(t)}</div>`).join('')}
      ${stats.missedItems.map(t => `<div style="font-size:12.5px; color:var(--danger); padding:6px 0; border-bottom:1px solid var(--border-soft);">🔴 ${escapeHtml(t)}</div>`).join('')}
    </div>` : ''}
  `;
}

// ---------------------------------------------------------------------------
// Tab 2: Exams — درصد هر درس + فصل به فصل
// ---------------------------------------------------------------------------
function renderExamsTab(root) {
  const exams = [...DB.exams].sort((a,b) => b.date.localeCompare(a.date));
  root.innerHTML = `
    <div id="examList"></div>
    <button class="btn btn-primary" style="margin-top:14px;" onclick="openAddExamSheet()">
      <span class="material-symbols-rounded" style="font-size:19px;">add</span> ثبت آزمون جدید
    </button>
  `;
  const el = root.querySelector('#examList');
  if (!exams.length) {
    el.innerHTML = emptyState('assignment', 'هنوز آزمونی ثبت نشده', 'بعد از هر آزمون، درصدهات رو اینجا وارد کن');
    return;
  }
  el.innerHTML = exams.map(ex => {
    const avg = ex.subjects.length ? Math.round(ex.subjects.reduce((s,x)=>s+x.percent,0) / ex.subjects.length) : 0;
    return `
    <div class="card" style="margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <div style="font-weight:800; font-size:14.5px;">${escapeHtml(ex.name)}</div>
          <div style="font-size:11.5px; color:var(--text-3); margin-top:2px;">${Jalali.gregorianStrToJalaliStr(ex.date)}</div>
        </div>
        <div style="text-align:left;">
          <div style="font-size:20px; font-weight:800; color:var(--primary-bright);">${fa(avg)}٪</div>
          <div style="font-size:10.5px; color:var(--text-3);">میانگین</div>
        </div>
      </div>
      <div style="margin-top:12px;">
        ${ex.subjects.map(s => `
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
            <span style="font-size:12px; width:60px; flex-shrink:0; color:var(--text-2); font-weight:600;">${escapeHtml(s.name)}</span>
            <div class="pbar thin" style="flex:1;"><div style="width:${s.percent}%; background:${percentColor(s.percent)}"></div></div>
            <span style="font-size:12px; font-weight:700; width:34px; text-align:left;">${fa(s.percent)}٪</span>
          </div>`).join('')}
      </div>
      <div class="btn-row" style="margin-top:10px;">
        <button class="btn-sm btn-ghost" style="flex:1;" onclick="openEditExamSheet('${ex.id}')">ویرایش</button>
        <button class="btn-sm btn-danger-ghost" style="flex:1;" onclick="confirmDeleteExam('${ex.id}')">حذف</button>
      </div>
    </div>`;
  }).join('');
}
function percentColor(p) {
  if (p >= 70) return 'linear-gradient(90deg,#16a34a,#22c55e)';
  if (p >= 40) return 'linear-gradient(90deg,#d97706,#f59e0b)';
  return 'linear-gradient(90deg,#dc2626,#ef4444)';
}

function openAddExamSheet() { openSheet(examFormHtml()); wireExamForm(); }
function examFormHtml(existing) {
  const subs = existing?.subjects?.length ? existing.subjects : SUBJECTS.slice(0,4).map(s => ({name:s, correct:0, wrong:0, unanswered:0, total:0, percent:0}));
  return `
    <h2>${existing?'ویرایش آزمون':'ثبت آزمون جدید'}</h2>
    <div class="field"><label>نام آزمون</label><input id="exName" type="text" placeholder="مثلاً آزمون جامع قلم‌چی ۴" value="${escapeHtml(existing?.name||'')}" /></div>
    <div class="field"><label>تاریخ</label><input id="exDate" type="date" value="${existing?.date||Jalali.todayStr()}" /></div>
    <div class="field">
      <label>درس‌ها و درصدها</label>
      <div id="exSubjectsWrap">
        ${subs.map((s,i) => examSubjectRow(s,i)).join('')}
      </div>
      <button type="button" class="btn-sm btn-ghost" style="margin-top:6px;" onclick="addExamSubjectRow()">+ افزودن درس</button>
    </div>
    <button class="btn btn-primary" onclick="submitExam(${existing?`'${existing.id}'`:'null'})">${existing?'ذخیره تغییرات':'ثبت آزمون'}</button>
  `;
}
function examSubjectRow(s, i) {
  return `
    <div class="exam-sub-row" data-idx="${i}" style="display:flex; gap:6px; margin-bottom:8px; align-items:center;">
      <select data-ex-subject style="flex:1.2; padding:9px 8px; border-radius:8px; background:var(--surface-2); border:1px solid var(--border); color:var(--text-1); font-size:12.5px;">
        ${SUBJECTS.map(sub => `<option value="${sub}" ${s.name===sub?'selected':''}>${sub}</option>`).join('')}
      </select>
      <input data-ex-percent type="number" min="0" max="100" placeholder="درصد" value="${s.percent||''}" style="width:64px; padding:9px 8px; border-radius:8px; background:var(--surface-2); border:1px solid var(--border); color:var(--text-1); font-size:12.5px;" />
      <button type="button" class="icon-btn" style="width:32px;height:32px;" onclick="this.closest('.exam-sub-row').remove()"><span class="material-symbols-rounded" style="font-size:15px;">close</span></button>
    </div>`;
}
function addExamSubjectRow() {
  const wrap = document.getElementById('exSubjectsWrap');
  const idx = wrap.children.length;
  wrap.insertAdjacentHTML('beforeend', examSubjectRow({name:SUBJECTS[0],percent:0}, idx));
}
function wireExamForm() {}
async function submitExam(existingId) {
  const name = document.getElementById('exName').value.trim();
  const date = document.getElementById('exDate').value;
  if (!name || !date) { showToast('نام و تاریخ آزمون رو پر کن'); return; }
  const rows = Array.from(document.querySelectorAll('.exam-sub-row'));
  const subjects = rows.map(r => ({
    name: r.querySelector('[data-ex-subject]').value,
    percent: Math.max(0, Math.min(100, parseInt(r.querySelector('[data-ex-percent]').value) || 0))
  }));
  try {
    if (existingId) {
      await apiUpdateExam(existingId, { name, date, subjects });
    } else {
      await apiAddExam({ name, date, subjects });
    }
    closeSheet();
    showToast(existingId ? 'ذخیره شد' : 'آزمون ثبت شد');
    rerender();
  } catch (e) {
    showToast('خطا: ' + e.message, 'error');
  }
}
function openEditExamSheet(id) {
  const ex = DB.exams.find(x => x.id === id);
  if (!ex) return;
  openSheet(examFormHtml(ex));
  wireExamForm();
}
function confirmDeleteExam(id) {
  openDialog({
    icon: 'delete', title: 'حذف آزمون', text: 'اطلاعات این آزمون برای همیشه حذف می‌شه.',
    confirmText: 'حذف کن', confirmClass: 'btn-danger-ghost',
    onConfirm: async () => {
      try {
        await apiDeleteExam(id);
        closeDialog(); showToast('حذف شد'); rerender();
      } catch (e) {
        showToast('خطا: ' + e.message, 'error');
        closeDialog();
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Tab 3: Compare — آزمون‌به‌آزمون و فصل‌به‌فصل
// ---------------------------------------------------------------------------
function renderCompareTab(root) {
  const exams = [...DB.exams].sort((a,b) => a.date.localeCompare(b.date));
  if (exams.length < 2) {
    root.innerHTML = emptyState('compare_arrows', 'برای مقایسه حداقل دو آزمون لازمه', 'چند آزمون دیگه ثبت کن تا روند رو ببینی');
    return;
  }
  // overall average trend
  const avgSeries = exams.map(ex => ({
    name: ex.name, date: ex.date,
    avg: ex.subjects.length ? Math.round(ex.subjects.reduce((s,x)=>s+x.percent,0)/ex.subjects.length) : 0
  }));
  const maxAvg = Math.max(1, ...avgSeries.map(e => e.avg));

  // per-subject last two exams comparison
  const last = exams[exams.length - 1];
  const prev = exams[exams.length - 2];
  const subjectDeltas = last.subjects.map(s => {
    const prevSub = prev.subjects.find(p => p.name === s.name);
    const delta = prevSub ? s.percent - prevSub.percent : null;
    return { name: s.name, current: s.percent, delta };
  });

  root.innerHTML = `
    <div class="card">
      <div style="font-weight:700; font-size:14px; margin-bottom:14px;">روند میانگین کل آزمون‌ها</div>
      <div class="barchart" style="height:120px;">
        ${avgSeries.map(e => {
          const pct = Math.max(4, (e.avg / maxAvg) * 100);
          return `<div class="barcol">
            <div style="font-size:10px; color:var(--text-2); font-weight:700;">${fa(e.avg)}</div>
            <div class="bar" style="height:80px;"><div style="height:${pct}%"></div></div>
            <div class="bar-label" style="font-size:9px;">${e.name.slice(0,6)}</div>
          </div>`;
        }).join('')}
      </div>
    </div>

    <div class="section-head"><h3>آخرین آزمون نسبت به قبلی</h3></div>
    <p class="page-sub" style="margin-top:-8px;">${escapeHtml(prev.name)} ← ${escapeHtml(last.name)}</p>
    <div class="card">
      ${subjectDeltas.map(s => `
        <div style="display:flex; align-items:center; justify-content:space-between; padding:10px 0; border-bottom:1px solid var(--border-soft);">
          <span style="font-size:13px; font-weight:700;">${escapeHtml(s.name)}</span>
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:13px; color:var(--text-2);">${fa(s.current)}٪</span>
            ${s.delta === null ? `<span class="chip">جدید</span>` :
              s.delta > 0 ? `<span class="chip" style="background:rgba(34,197,94,.14); color:var(--success);">▲ ${fa(s.delta)}</span>` :
              s.delta < 0 ? `<span class="chip" style="background:rgba(239,68,68,.14); color:var(--danger);">▼ ${fa(Math.abs(s.delta))}</span>` :
              `<span class="chip">بدون تغییر</span>`}
          </div>
        </div>`).join('')}
    </div>

    <div class="section-head"><h3>همه آزمون‌ها</h3></div>
    <div class="card">
      ${[...exams].reverse().map(ex => {
        const avg = ex.subjects.length ? Math.round(ex.subjects.reduce((s,x)=>s+x.percent,0)/ex.subjects.length) : 0;
        return `<div style="display:flex; justify-content:space-between; padding:9px 0; border-bottom:1px solid var(--border-soft); font-size:12.5px;">
          <span style="font-weight:600;">${escapeHtml(ex.name)}</span>
          <span style="color:var(--text-2);">${Jalali.gregorianStrToJalaliStr(ex.date)} · ${fa(avg)}٪</span>
        </div>`;
      }).join('')}
    </div>
  `;
}
