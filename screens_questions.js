/* =========================================================================
   صفحه سوالات — بانک سوالات شخصی با تگ درس/مبحث/سطح سختی
   ========================================================================= */
const SUBJECTS = ['ریاضی', 'فیزیک', 'شیمی', 'زیست', 'ادبیات', 'عربی', 'دینی', 'زبان', 'سایر'];
const DIFFICULTIES = [
  { key: 'easy', label: 'آسان', cls: 'tag-diff-easy' },
  { key: 'mid', label: 'متوسط', cls: 'tag-diff-mid' },
  { key: 'hard', label: 'سخت', cls: 'tag-diff-hard' }
];

let qFilterSubject = 'all';
let qFilterDiff = 'all';
let qSearchTerm = '';

SCREENS.questions = function (root) {
  const filtered = DB.questions.filter(q => {
    if (qFilterSubject !== 'all' && q.subject !== qFilterSubject) return false;
    if (qFilterDiff !== 'all' && q.difficulty !== qFilterDiff) return false;
    if (qSearchTerm && !q.text.includes(qSearchTerm) && !(q.topic||'').includes(qSearchTerm)) return false;
    return true;
  }).sort((a,b) => (b.createdAt||'').localeCompare(a.createdAt||''));

  root.innerHTML = `
    <h1 class="page-title">سوالات من</h1>
    <p class="page-sub">${fa(DB.questions.length)} سوال ذخیره‌شده</p>

    <div class="field" style="margin-bottom:12px;">
      <input type="text" placeholder="جستجو در متن سوال یا مبحث…" value="${escapeHtml(qSearchTerm)}"
        oninput="qSearchTerm=this.value; rerender();" />
    </div>

    <div class="filter-scroll">
      <button class="chip ${qFilterSubject==='all'?'on':''}" onclick="qFilterSubject='all'; rerender();">همه دروس</button>
      ${SUBJECTS.map(s => `<button class="chip ${qFilterSubject===s?'on':''}" onclick="qFilterSubject='${s}'; rerender();">${s}</button>`).join('')}
    </div>
    <div class="filter-scroll" style="margin-top:-6px;">
      <button class="chip ${qFilterDiff==='all'?'on':''}" onclick="qFilterDiff='all'; rerender();">همه سطوح</button>
      ${DIFFICULTIES.map(d => `<button class="chip ${qFilterDiff===d.key?'on':''}" onclick="qFilterDiff='${d.key}'; rerender();">${d.label}</button>`).join('')}
    </div>

    <div id="qList" style="margin-top:14px;"></div>

    <button class="btn btn-primary" style="margin-top:16px;" onclick="openAddQuestionSheet()">
      <span class="material-symbols-rounded" style="font-size:19px;">add</span> افزودن سوال جدید
    </button>
  `;

  const listEl = root.querySelector('#qList');
  if (!filtered.length) {
    listEl.innerHTML = emptyState('quiz', 'سوالی پیدا نشد', 'سوالاتی که جمع می‌کنی رو اینجا ذخیره کن');
  } else {
    listEl.innerHTML = filtered.map(renderQuestionCard).join('');
  }
};

function renderQuestionCard(q) {
  const diff = DIFFICULTIES.find(d => d.key === q.difficulty) || DIFFICULTIES[1];
  return `
    <div class="qcard">
      <div class="chip-row" style="margin-bottom:9px;">
        <span class="chip tag-subject">${escapeHtml(q.subject)}</span>
        ${q.topic ? `<span class="chip">${escapeHtml(q.topic)}</span>` : ''}
        <span class="chip ${diff.cls}">${diff.label}</span>
      </div>
      <div class="qtext">${escapeHtml(q.text)}</div>
      ${q.options && q.options.length ? `
      <div class="qopts">
        ${q.options.map(o => `<div class="qopt ${o.correct ? 'correct' : ''}">${o.correct ? '✓ ' : ''}${escapeHtml(o.text)}</div>`).join('')}
      </div>` : ''}
      <div class="btn-row">
        <button class="btn-sm btn-ghost" style="flex:1;" onclick="openEditQuestionSheet('${q.id}')">ویرایش</button>
        <button class="btn-sm btn-danger-ghost" style="flex:1;" onclick="confirmDeleteQuestion('${q.id}')">حذف</button>
      </div>
    </div>`;
}

function openAddQuestionSheet() {
  openSheet(questionFormHtml());
  wireQuestionForm();
}

function questionFormHtml(existing) {
  const opts = existing?.options?.length ? existing.options : [{text:'',correct:false},{text:'',correct:false},{text:'',correct:false},{text:'',correct:false}];
  return `
    <h2>${existing ? 'ویرایش سوال' : 'افزودن سوال جدید'}</h2>
    <div class="field"><label>متن سوال</label><textarea id="qText" placeholder="متن کامل سوال رو اینجا بنویس یا کپی کن…">${escapeHtml(existing?.text||'')}</textarea></div>
    <div class="field">
      <label>گزینه‌ها (اختیاری — گزینه درست رو با تیک مشخص کن)</label>
      <div id="qOptsWrap">
        ${opts.map((o,i) => `
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <input type="checkbox" ${o.correct?'checked':''} data-opt-correct="${i}" style="width:20px;height:20px; accent-color:var(--primary); flex-shrink:0;" />
            <input type="text" data-opt-text="${i}" placeholder="گزینه ${fa(i+1)}" value="${escapeHtml(o.text)}" style="flex:1; padding:10px 12px; border-radius:8px; background:var(--surface-2); border:1px solid var(--border); color:var(--text-1);" />
          </div>`).join('')}
      </div>
    </div>
    <div class="field">
      <label>درس</label>
      <select id="qSubject">${SUBJECTS.map(s => `<option value="${s}" ${existing?.subject===s?'selected':''}>${s}</option>`).join('')}</select>
    </div>
    <div class="field"><label>مبحث</label><input id="qTopic" type="text" placeholder="مثلاً مثلثات، تعادل شیمیایی…" value="${escapeHtml(existing?.topic||'')}" /></div>
    <div class="field">
      <label>سطح سختی</label>
      <div class="seg" id="qDiffSeg">
        ${DIFFICULTIES.map(d => `<button type="button" class="${(existing?.difficulty||'mid')===d.key?'active':''}" data-diff="${d.key}">${d.label}</button>`).join('')}
      </div>
    </div>
    <button class="btn btn-primary" onclick="submitQuestion(${existing?`'${existing.id}'`:'null'})">${existing?'ذخیره تغییرات':'افزودن سوال'}</button>
  `;
}
function wireQuestionForm() { wireSeg('qDiffSeg'); }

async function submitQuestion(existingId) {
  const text = document.getElementById('qText').value.trim();
  if (!text) { showToast('متن سوال خالیه'); return; }
  const subject = document.getElementById('qSubject').value;
  const topic = document.getElementById('qTopic').value.trim();
  const difficulty = document.querySelector('#qDiffSeg button.active').dataset.diff;
  const texts = Array.from(document.querySelectorAll('[data-opt-text]'));
  const options = texts.map((el, i) => ({
    text: el.value.trim(),
    correct: document.querySelector(`[data-opt-correct="${i}"]`).checked
  })).filter(o => o.text);

  try {
    if (existingId) {
      await apiUpdateQuestion(existingId, { text, subject, topic, difficulty, options });
    } else {
      await apiAddQuestion({ text, subject, topic, difficulty, options });
    }
    closeSheet();
    showToast(existingId ? 'ذخیره شد' : 'سوال اضافه شد');
    rerender();
  } catch (e) {
    showToast('خطا: ' + e.message, 'error');
  }
}

function openEditQuestionSheet(id) {
  const q = DB.questions.find(x => x.id === id);
  if (!q) return;
  openSheet(questionFormHtml(q));
  wireQuestionForm();
}

function confirmDeleteQuestion(id) {
  openDialog({
    icon: 'delete', title: 'حذف سوال', text: 'این سوال برای همیشه حذف می‌شه.',
    confirmText: 'حذف کن', confirmClass: 'btn-danger-ghost',
    onConfirm: async () => {
      try {
        await apiDeleteQuestion(id);
        closeDialog(); showToast('حذف شد'); rerender();
      } catch (e) {
        showToast('خطا: ' + e.message, 'error');
        closeDialog();
      }
    }
  });
}
