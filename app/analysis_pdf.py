/* =========================================================================
   بانک تحلیل (Analysis Bank)
   =========================================================================
   باگ‌های رفع‌شده:
   ۱. PDF همیشه نمایش داده می‌شه — حتی اگه mapping هنوز تنظیم نشده باشه،
      PDF viewer نشان داده می‌شه و فقط یه کارت هشدار برای تنظیم mapping بالاش میاد.
   ۲. کلیک روی شماره سوال دیگه PDF رو دانلود نمی‌کنه — فقط iframe رو
      آپدیت می‌کنه (src#page=N) یا اگه mapping نداره toast نشون می‌ده.
   ۳. OCR بهبود یافته — پشتیبانی از ارقام فارسی و الگوهای آزمون ماز
      مثل «-۱» یا «1-» با یا بدون فاصله.
   ========================================================================= */

let analysisSelectedExamId = null;
let analysisDetailCache = {};
let analysisPdfPageGoto = 1;

SCREENS.analysisBank = function (root) {
  if (analysisSelectedExamId) {
    renderAnalysisDetail(root, analysisSelectedExamId);
  } else {
    renderAnalysisList(root);
  }
};

// ---------------------------------------------------------------------------
// لیست آزمون‌های بانک تحلیل
// ---------------------------------------------------------------------------
function renderAnalysisList(root) {
  root.innerHTML = `
    <h1 class="page-title">بانک تحلیل</h1>
    <p class="page-sub">دفترچه‌ی PDF آزمون‌هات رو آپلود کن و تحلیل هر سوال رو اینجا نگه دار</p>
    <div id="analysisListBody"></div>
    <button class="btn btn-primary" style="margin-top:16px;" onclick="openUploadAnalysisSheet()">
      <span class="material-symbols-rounded" style="font-size:19px;">upload_file</span> آپلود آزمون جدید
    </button>
  `;
  const body = root.querySelector('#analysisListBody');
  body.innerHTML = `<div class="empty"><span class="material-symbols-rounded">hourglass_top</span><p>در حال بارگذاری…</p></div>`;

  loadAnalysisExamsIfNeeded().then(() => {
    if (currentScreen !== 'analysisBank' || analysisSelectedExamId) return;
    const list = [...DB.analysisExams].sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
    if (!list.length) {
      body.innerHTML = emptyState('folder_open', 'هنوز آزمونی آپلود نشده', 'دفترچه‌ی PDF یک آزمون رو آپلود کن تا تحلیلش رو اینجا بنویسی');
    } else {
      body.innerHTML = list.map(renderAnalysisExamCard).join('');
    }
  });
}

function renderAnalysisExamCard(e) {
  const methodLabel = e.mappingMethod === 'auto' ? 'تشخیص خودکار صفحات' : 'نگاشت دستی صفحات';
  const methodIcon = e.mappingMethod === 'auto' ? 'auto_awesome' : 'tune';
  return `
    <div class="qcard" style="cursor:pointer;" onclick="openAnalysisExam('${e.id}')">
      <div class="chip-row" style="margin-bottom:9px;">
        ${e.date ? `<span class="chip">${escapeHtml(Jalali.gregorianStrToJalaliStr(e.date))}</span>` : ''}
        <span class="chip"><span class="material-symbols-rounded" style="font-size:13px; vertical-align:-2px;">${methodIcon}</span> ${methodLabel}</span>
      </div>
      <div class="qtext">${escapeHtml(e.title)}</div>
      <div class="li-sub" style="margin-top:4px;">${fa(e.questionCount)} سوال · ${fa(e.pageCount)} صفحه · ${fa(e.notesCount)} تحلیل ثبت‌شده</div>
    </div>`;
}

function openAnalysisExam(id) {
  analysisSelectedExamId = id;
  analysisPdfPageGoto = 1;
  rerender();
}

function closeAnalysisExam() {
  analysisSelectedExamId = null;
  rerender();
}

// ---------------------------------------------------------------------------
// آپلود آزمون جدید
// ---------------------------------------------------------------------------
function openUploadAnalysisSheet() {
  openSheet(`
    <h2>آپلود آزمون جدید</h2>
    <div class="field"><label>عنوان آزمون</label><input id="anTitle" type="text" placeholder="مثلاً آزمون جامع شماره ۳ — کانون" /></div>
    <div class="field"><label>تاریخ آزمون (اختیاری)</label><input id="anDate" type="date" /></div>
    <div class="field"><label>تعداد کل سوالات</label><input id="anQCount" type="number" min="1" max="200" placeholder="مثلاً 75" /></div>

    <div class="field">
      <label>فایل PDF دفترچه‌ی آزمون</label>
      <input id="anPdfFile" type="file" accept="application/pdf" style="padding:10px 12px; border-radius:8px; background:var(--surface-2); border:1px solid var(--border); color:var(--text-1); width:100%;" />
    </div>

    <div style="background:var(--surface-2); border:1px solid var(--border-soft); border-radius:10px; padding:12px; margin-bottom:14px;">
      <div style="font-size:12.5px; font-weight:700; color:var(--text-2); margin-bottom:8px; display:flex; align-items:center; gap:6px;">
        <span class="material-symbols-rounded" style="font-size:16px;">auto_awesome</span>
        تشخیص خودکار شماره‌ی صفحه‌ی هر سوال
      </div>
      <p style="font-size:12.5px; color:var(--text-3); line-height:1.8; margin:0 0 10px;">
        اول خودکار روی متن PDF امتحان می‌کنیم. اگه جواب نداد، فقط کافیه بگی سوال ۱ از کدوم صفحه شروع می‌شه
        و سوال آخر توی کدوم صفحه‌ست؛ بقیه‌ی سوالات به‌نسبت بین این دو صفحه تخمین زده می‌شن.
      </p>
      <div style="display:flex; gap:10px;">
        <div class="field" style="flex:1; margin-bottom:0;"><label>صفحه‌ی شروع سوال ۱</label><input id="anStartPage" type="number" min="1" placeholder="مثلاً 3" /></div>
        <div class="field" style="flex:1; margin-bottom:0;"><label>صفحه‌ی سوال آخر</label><input id="anEndPage" type="number" min="1" placeholder="مثلاً 18" /></div>
      </div>
    </div>

    <div class="field"><label>تحلیل کلی آزمون (اختیاری)</label><textarea id="anOverallNote" placeholder="جمع‌بندی کلی از عملکردت توی این آزمون…"></textarea></div>

    <button class="btn btn-primary" id="anSubmitBtn" onclick="submitUploadAnalysisExam()">آپلود و ذخیره</button>
  `);
}

async function submitUploadAnalysisExam() {
  const title = document.getElementById('anTitle').value.trim();
  const date = document.getElementById('anDate').value || '';
  const qCountRaw = document.getElementById('anQCount').value;
  const qCount = parseInt(qCountRaw, 10);
  const fileInput = document.getElementById('anPdfFile');
  const file = fileInput.files && fileInput.files[0];
  const startPageRaw = document.getElementById('anStartPage').value;
  const endPageRaw = document.getElementById('anEndPage').value;
  const overallNote = document.getElementById('anOverallNote').value.trim();

  if (!title) { showToast('عنوان آزمون رو وارد کن', 'error'); return; }
  if (!qCount || qCount < 1 || qCount > 200) { showToast('تعداد سوالات باید بین ۱ تا ۲۰۰ باشه', 'error'); return; }
  if (!file) { showToast('فایل PDF رو انتخاب کن', 'error'); return; }
  if (file.type && file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
    showToast('فقط فایل PDF قابل قبوله', 'error'); return;
  }

  const btn = document.getElementById('anSubmitBtn');
  btn.disabled = true;
  btn.textContent = 'در حال آپلود…';

  try {
    const meta = {
      title, date, question_count: qCount,
      manual_start_page: startPageRaw ? parseInt(startPageRaw, 10) : null,
      manual_end_page: endPageRaw ? parseInt(endPageRaw, 10) : null,
      overall_note: overallNote,
    };
    const full = await apiUploadAnalysisExam(meta, file);
    closeSheet();
    if (full.mappingMethod === 'auto') {
      showToast('آپلود شد — شماره‌ی صفحه‌ی سوالات به‌صورت خودکار تشخیص داده شد');
    } else if (Object.keys(full.questionPageMap || {}).length) {
      showToast('آپلود شد — نگاشت صفحات از روی مقادیر دستی ساخته شد');
    } else {
      showToast('آپلود شد — نگاشت صفحات رو از داخل آزمون تنظیم کن', 'info');
    }
    analysisDetailCache[full.id] = full;
    openAnalysisExam(full.id);
  } catch (e) {
    if (e instanceof Api.ApiError && e.isNetworkError) {
      showToast('برای آپلود آزمون به اینترنت نیاز داری', 'error');
    } else {
      showToast('خطا در آپلود: ' + e.message, 'error');
    }
    btn.disabled = false;
    btn.textContent = 'آپلود و ذخیره';
  }
}

// ---------------------------------------------------------------------------
// جزئیات یک آزمون
// ---------------------------------------------------------------------------
function renderAnalysisDetail(root, examId) {
  root.innerHTML = `
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
      <button class="icon-btn" onclick="closeAnalysisExam()"><span class="material-symbols-rounded" style="font-size:19px;">arrow_forward</span></button>
      <h1 class="page-title" style="margin:0;">جزئیات آزمون</h1>
    </div>
    <div id="analysisDetailBody" style="margin-top:14px;">
      <div class="empty"><span class="material-symbols-rounded">hourglass_top</span><p>در حال بارگذاری…</p></div>
    </div>
  `;

  const body = root.querySelector('#analysisDetailBody');
  const cached = analysisDetailCache[examId];
  if (cached) renderAnalysisDetailBody(body, cached);

  apiGetAnalysisExamFull(examId).then(full => {
    analysisDetailCache[examId] = full;
    if (analysisSelectedExamId === examId) {
      const el = document.getElementById('analysisDetailBody') || body;
      renderAnalysisDetailBody(el, full);
    }
  }).catch(e => {
    if (!cached) {
      body.innerHTML = `<div class="empty"><span class="material-symbols-rounded">error</span><p>بارگذاری این آزمون ممکن نشد: ${escapeHtml(e.message)}</p></div>`;
    } else if (!(e instanceof Api.ApiError && e.isNetworkError)) {
      showToast('خطا در به‌روزرسانی: ' + e.message, 'error');
    }
  });
}

function renderAnalysisDetailBody(body, exam) {
  const hasMap = Object.keys(exam.questionPageMap || {}).length > 0;
  const noteByQ = {};
  (exam.notes || []).forEach(n => { noteByQ[n.questionNumber] = n; });

  const questionChips = [];
  for (let q = 1; q <= exam.questionCount; q++) {
    const has = !!noteByQ[q];
    const correctCls = has && noteByQ[q].isCorrect === true ? 'tag-diff-easy' :
      (has && noteByQ[q].isCorrect === false ? 'tag-diff-hard' : '');
    questionChips.push(`
      <button class="chip ${has ? 'on ' + correctCls : ''}" onclick="openAnalysisQuestionSheet('${exam.id}', ${q})">${fa(q)}</button>
    `);
  }

  // ========================================================
  // FIX ۱: PDF viewer همیشه نمایش داده می‌شه
  // حتی اگه mapping نداره، iframe رو نشون می‌دیم تا کاربر
  // بتونه PDF رو ببینه. کارت هشدار mapping فقط بالای PDF میاد.
  // ========================================================
  const pdfUrl = Api.getAnalysisPdfUrl(exam.id);

  body.innerHTML = `
    <div class="qcard" style="margin-bottom:14px;">
      <div class="qtext" style="margin-bottom:6px;">${escapeHtml(exam.title)}</div>
      <div class="li-sub">
        ${exam.date ? escapeHtml(Jalali.gregorianStrToJalaliStr(exam.date)) + ' · ' : ''}
        ${fa(exam.questionCount)} سوال · ${fa(exam.pageCount)} صفحه
      </div>
      ${exam.overallNote ? `<div style="margin-top:10px; font-size:13.5px; line-height:1.9; color:var(--text-2); background:var(--surface-3); border-radius:8px; padding:10px;">${escapeHtml(exam.overallNote)}</div>` : ''}
      <div class="btn-row" style="margin-top:12px;">
        <button class="btn-sm btn-ghost" style="flex:1;" onclick="openEditAnalysisMetaSheet('${exam.id}')">ویرایش اطلاعات</button>
        <a class="btn-sm btn-ghost" style="flex:1; text-align:center; text-decoration:none; display:flex; align-items:center; justify-content:center;" href="${pdfUrl}" download="${escapeHtml(exam.originalFilename || exam.title + '.pdf')}">
          <span class="material-symbols-rounded" style="font-size:17px;">download</span> دانلود PDF
        </a>
        <button class="btn-sm btn-danger-ghost" style="flex:1;" onclick="confirmDeleteAnalysisExam('${exam.id}')">حذف آزمون</button>
      </div>
    </div>

    ${!hasMap ? `
    <div class="qcard" style="margin-bottom:14px; border-color:rgba(239,68,68,.35);">
      <div style="font-size:13px; color:var(--danger); font-weight:700; margin-bottom:8px;">نگاشت شماره‌سوال به صفحه هنوز مشخص نیست</div>
      <p style="font-size:12.5px; color:var(--text-3); line-height:1.8; margin-bottom:10px;">
        تشخیص خودکار برای این فایل جواب نداد. صفحه‌ی شروع سوال ۱ و صفحه‌ی سوال آخر رو وارد کن تا نگاشت ساخته بشه.
        <br/>PDF آزمونت رو پایین می‌تونی ببینی تا شماره صفحه‌ها رو چک کنی.
      </p>
      <div style="display:flex; gap:10px;">
        <div class="field" style="flex:1; margin-bottom:0;"><label>صفحه‌ی شروع سوال ۱</label><input id="remapStart" type="number" min="1" max="${exam.pageCount}" /></div>
        <div class="field" style="flex:1; margin-bottom:0;"><label>صفحه‌ی سوال آخر</label><input id="remapEnd" type="number" min="1" max="${exam.pageCount}" /></div>
      </div>
      <button class="btn btn-primary" style="margin-top:10px;" onclick="submitRemapAnalysisExam('${exam.id}')">محاسبه‌ی نگاشت صفحات</button>
    </div>` : `
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
      <span style="font-size:13px; font-weight:700; color:var(--text-2);">مشاهده‌ی دفترچه‌ی آزمون</span>
      <button class="btn-sm btn-ghost" onclick="openAnalysisRemapSheet('${exam.id}')"><span class="material-symbols-rounded" style="font-size:15px;">tune</span> اصلاح نگاشت صفحات</button>
    </div>
    `}

    <!-- =====================================================
         FIX ۱: PDF viewer همیشه نمایش می‌شه (با یا بدون mapping)
         ===================================================== -->
    <div class="pdf-viewer-wrap" style="margin-bottom:18px;">
      <iframe id="analysisPdfFrame" class="pdf-viewer"
        src="${pdfUrl}#page=${analysisPdfPageGoto}"
        title="دفترچه‌ی آزمون">
      </iframe>
    </div>

    ${hasMap ? `
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
      <span style="font-size:13px; font-weight:700; color:var(--text-2);">سوال‌ها — بزن تا تحلیل بنویسی و به صفحه‌ش بپری</span>
      <span style="font-size:11px; color:var(--text-3);">🟢 درست · 🔴 غلط · خاکستری = بدون تحلیل</span>
    </div>` : `
    <div style="font-size:13px; font-weight:700; color:var(--text-2); margin-bottom:8px;">
      سوال‌ها — بزن تا تحلیل بنویسی (بعد از تنظیم نگاشت صفحات، به صفحه‌ی سوال هم می‌پری)
    </div>`}
    <div class="chip-row" style="flex-wrap:wrap;">${questionChips.join('')}</div>
  `;
}

// ---------------------------------------------------------------------------
// FIX ۲ (اصلاح‌شده): پرش قابل‌اعتماد به صفحه‌ی سوال داخل iframe
// نسخه‌ی قبلی فقط #page=N رو روی src فعلی عوض می‌کرد که باعث می‌شد در
// خیلی از مرورگرها/WebViewها هیچ navigation جدیدی رخ نده و صفحه سفید
// بمونه. حالا iframe رو موقتاً خالی می‌کنیم تا navigation واقعی انجام بشه.
// ---------------------------------------------------------------------------
function jumpToAnalysisQuestionPage(examId, qNum) {
  const exam = analysisDetailCache[examId];
  if (!exam) return;
  const page = (exam.questionPageMap || {})[qNum] || (exam.questionPageMap || {})[String(qNum)];
  if (!page) { showToast('صفحه‌ی این سوال هنوز از نگاشت مشخص نیست', 'error'); return; }
  analysisPdfPageGoto = page;
  const frame = document.getElementById('analysisPdfFrame');
  if (!frame) return;

  // فقط عوض کردن fragment (#page=N) روی src فعلی، در خیلی از مرورگرها
  // (به‌خصوص Chrome موبایل/WebView) هیچ navigation جدیدی راه نمی‌ندازه،
  // چون از دید مرورگر URL بدون احتساب fragment فرقی نکرده. نتیجه‌ش
  // این می‌شه که PDF viewer داخلی گاهی صفحه‌ی سفید نشون می‌ده یا
  // اصلاً به صفحه‌ی جدید نمی‌پره.
  // راه‌حل: iframe رو اول خالی (about:blank) می‌کنیم تا مرورگر مطمئن
  // بشه سند فعلی عوض شده، بعد با یه تأخیر کوتاه src واقعی رو ست می‌کنیم
  // تا یه navigation واقعی و کامل انجام بشه.
  const baseUrl = Api.getAnalysisPdfUrl(examId);
  const targetSrc = `${baseUrl}#page=${page}`;
  frame.src = 'about:blank';
  setTimeout(() => {
    // اگه کاربر سریع چند بار پشت‌سرهم کلیک کرد، فقط جدیدترین درخواست
    // اجرا بشه (analysisPdfPageGoto همیشه آخرین صفحه‌ی خواسته‌شده رو داره)
    if (analysisPdfPageGoto === page) {
      frame.src = targetSrc;
    }
  }, 50);
}

// ---------------------------------------------------------------------------
// تحلیل یک سوال مشخص (باز شدن در بات‌شیت)
// ---------------------------------------------------------------------------
function openAnalysisQuestionSheet(examId, qNum) {
  const exam = analysisDetailCache[examId];
  if (!exam) return;
  const existing = (exam.notes || []).find(n => n.questionNumber === qNum);
  const hasMap = Object.keys(exam.questionPageMap || {}).length > 0;
  const page = hasMap ? ((exam.questionPageMap || {})[qNum] || (exam.questionPageMap || {})[String(qNum)]) : null;

  openSheet(`
    <h2>سوال ${fa(qNum)}</h2>
    ${page ? `
    <button class="btn-sm btn-ghost" style="width:100%; margin-bottom:14px;" onclick="closeSheet(); jumpToAnalysisQuestionPage('${examId}', ${qNum});">
      <span class="material-symbols-rounded" style="font-size:16px;">visibility</span> پرش به این سوال در PDF (صفحه‌ی ${fa(page)})
    </button>` : (hasMap ? `<p style="font-size:12.5px; color:var(--text-3); margin-bottom:14px;">صفحه‌ی این سوال از نگاشت مشخص نیست.</p>` :
    `<p style="font-size:12.5px; color:var(--text-3); margin-bottom:14px;">برای پریدن به صفحه، ابتدا نگاشت صفحات آزمون رو تنظیم کن.</p>`)}

    <div class="field"><label>درس (اختیاری)</label><input id="anqSubject" type="text" placeholder="مثلاً ریاضی" value="${escapeHtml(existing?.subject || '')}" /></div>
    <div class="field">
      <label>وضعیت من توی این سوال</label>
      <div class="seg" id="anqCorrectSeg">
        <button type="button" data-val="unknown" class="${existing?.isCorrect == null ? 'active' : ''}">نامشخص</button>
        <button type="button" data-val="correct" class="${existing?.isCorrect === true ? 'active' : ''}">درست زدم</button>
        <button type="button" data-val="wrong" class="${existing?.isCorrect === false ? 'active' : ''}">غلط زدم</button>
      </div>
    </div>
    <div class="field"><label>تحلیل</label><textarea id="anqNote" placeholder="چرا غلط زدم، چه نکته‌ای رو باید مرور کنم…">${escapeHtml(existing?.note || '')}</textarea></div>

    <div class="btn-row">
      <button class="btn btn-primary" style="flex:1;" onclick="submitAnalysisQuestionNote('${examId}', ${qNum})">ذخیره تحلیل</button>
      ${existing ? `<button class="btn-sm btn-danger-ghost" onclick="confirmDeleteAnalysisNote('${examId}', '${existing.id}')">حذف</button>` : ''}
    </div>
  `);
  wireSeg('anqCorrectSeg');
}

async function submitAnalysisQuestionNote(examId, qNum) {
  const subject = document.getElementById('anqSubject').value.trim();
  const note = document.getElementById('anqNote').value.trim();
  const correctVal = document.querySelector('#anqCorrectSeg button.active')?.dataset.val || 'unknown';
  const isCorrect = correctVal === 'unknown' ? null : (correctVal === 'correct');

  try {
    const saved = await apiUpsertAnalysisNote(examId, { question_number: qNum, subject, note, is_correct: isCorrect });
    const exam = analysisDetailCache[examId];
    if (exam) {
      const idx = exam.notes.findIndex(n => n.questionNumber === qNum);
      if (idx >= 0) exam.notes[idx] = saved; else exam.notes.push(saved);
    }
    closeSheet();
    showToast('تحلیل ذخیره شد');
    if (analysisSelectedExamId === examId) rerender();
  } catch (e) {
    showToast('خطا در ذخیره: ' + e.message, 'error');
  }
}

function confirmDeleteAnalysisNote(examId, noteId) {
  openDialog({
    icon: 'delete', title: 'حذف تحلیل', text: 'تحلیل این سوال پاک می‌شه.',
    confirmText: 'حذف کن', confirmClass: 'btn-danger-ghost',
    onConfirm: async () => {
      try {
        await apiDeleteAnalysisNote(examId, noteId);
        const exam = analysisDetailCache[examId];
        if (exam) exam.notes = exam.notes.filter(n => n.id !== noteId);
        closeDialog(); closeSheet();
        showToast('حذف شد');
        if (analysisSelectedExamId === examId) rerender();
      } catch (e) {
        showToast('خطا: ' + e.message, 'error');
        closeDialog();
      }
    }
  });
}

// ---------------------------------------------------------------------------
// ویرایش اطلاعات آزمون
// ---------------------------------------------------------------------------
function openEditAnalysisMetaSheet(examId) {
  const exam = analysisDetailCache[examId];
  if (!exam) return;
  openSheet(`
    <h2>ویرایش اطلاعات آزمون</h2>
    <div class="field"><label>عنوان</label><input id="anEditTitle" type="text" value="${escapeHtml(exam.title)}" /></div>
    <div class="field"><label>تاریخ</label><input id="anEditDate" type="date" value="${escapeHtml(exam.date || '')}" /></div>
    <div class="field"><label>تحلیل کلی</label><textarea id="anEditOverall" placeholder="جمع‌بندی کلی…">${escapeHtml(exam.overallNote || '')}</textarea></div>
    <button class="btn btn-primary" onclick="submitEditAnalysisMeta('${examId}')">ذخیره تغییرات</button>
  `);
}

async function submitEditAnalysisMeta(examId) {
  const title = document.getElementById('anEditTitle').value.trim();
  const date = document.getElementById('anEditDate').value || '';
  const overall_note = document.getElementById('anEditOverall').value.trim();
  if (!title) { showToast('عنوان نمی‌تونه خالی باشه', 'error'); return; }
  try {
    const updated = await apiUpdateAnalysisExamMeta(examId, { title, date, overall_note });
    analysisDetailCache[examId] = { ...analysisDetailCache[examId], ...updated, notes: analysisDetailCache[examId].notes };
    closeSheet();
    showToast('ذخیره شد');
    rerender();
  } catch (e) {
    showToast('خطا: ' + e.message, 'error');
  }
}

// ---------------------------------------------------------------------------
// اصلاح دستی نگاشت صفحات
// ---------------------------------------------------------------------------
function openAnalysisRemapSheet(examId) {
  const exam = analysisDetailCache[examId];
  if (!exam) return;
  openSheet(`
    <h2>اصلاح نگاشت صفحات</h2>
    <p style="font-size:12.5px; color:var(--text-3); line-height:1.8; margin-bottom:14px;">
      اگه شماره‌ی صفحه‌ی بعضی سوالات درست نیست، صفحه‌ی شروع سوال ۱ و صفحه‌ی سوال آخر رو دوباره وارد کن.
    </p>
    <div style="display:flex; gap:10px;">
      <div class="field" style="flex:1;"><label>صفحه‌ی شروع سوال ۱</label><input id="remapStart2" type="number" min="1" max="${exam.pageCount}" value="${exam.manualStartPage || ''}" /></div>
      <div class="field" style="flex:1;"><label>صفحه‌ی سوال آخر</label><input id="remapEnd2" type="number" min="1" max="${exam.pageCount}" value="${exam.manualEndPage || ''}" /></div>
    </div>
    <button class="btn btn-primary" onclick="submitRemapAnalysisExam('${examId}', true)">محاسبه‌ی دوباره</button>
  `);
}

async function submitRemapAnalysisExam(examId, fromSheet) {
  const startEl = document.getElementById(fromSheet ? 'remapStart2' : 'remapStart');
  const endEl = document.getElementById(fromSheet ? 'remapEnd2' : 'remapEnd');
  const start = parseInt(startEl.value, 10);
  const end = parseInt(endEl.value, 10);
  if (!start || !end) { showToast('هر دو صفحه رو وارد کن', 'error'); return; }
  if (end < start) { showToast('صفحه‌ی سوال آخر نمی‌تونه قبل از صفحه‌ی شروع باشه', 'error'); return; }
  try {
    const updated = await apiRemapAnalysisExam(examId, start, end);
    analysisDetailCache[examId] = { ...analysisDetailCache[examId], ...updated, notes: analysisDetailCache[examId].notes };
    if (fromSheet) closeSheet();
    showToast('نگاشت صفحات به‌روز شد');
    rerender();
  } catch (e) {
    showToast('خطا: ' + e.message, 'error');
  }
}

// ---------------------------------------------------------------------------
// حذف کل آزمون
// ---------------------------------------------------------------------------
function confirmDeleteAnalysisExam(examId) {
  openDialog({
    icon: 'delete', title: 'حذف آزمون', text: 'این آزمون، فایل PDF و همه‌ی تحلیل‌های ثبت‌شده‌ش برای همیشه حذف می‌شن.',
    confirmText: 'حذف کن', confirmClass: 'btn-danger-ghost',
    onConfirm: async () => {
      try {
        await apiDeleteAnalysisExam(examId);
        delete analysisDetailCache[examId];
        closeDialog();
        showToast('حذف شد');
        closeAnalysisExam();
      } catch (e) {
        showToast('خطا در حذف: ' + e.message, 'error');
        closeDialog();
      }
    }
  });
}
