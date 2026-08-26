/* =========================================================================
   صفحه مطالعه — تایمر (پومودورو/شمارش‌معکوس/آزاد) + هشدار پایان
   ========================================================================= */
const TimerState = {
  mode: 'pomodoro',       // pomodoro | countdown | stopwatch
  totalSeconds: 25 * 60,
  remainingSeconds: 25 * 60,
  running: false,
  subject: '',
  intervalId: null,
  startedAt: null
};

const POMO_PRESETS = { pomodoro: 25 * 60, short: 5 * 60, long: 15 * 60 };

SCREENS.timer = function (root) {
  const percent = TimerState.totalSeconds > 0
    ? Math.max(0, Math.min(1, (TimerState.totalSeconds - TimerState.remainingSeconds) / TimerState.totalSeconds))
    : 0;
  const circumference = 2 * Math.PI * 125;
  const offset = circumference * (1 - percent);
  const mm = String(Math.floor(TimerState.remainingSeconds / 60)).padStart(2, '0');
  const ss = String(TimerState.remainingSeconds % 60).padStart(2, '0');

  const recentSessions = [...DB.sessions].reverse().slice(0, 5);

  root.innerHTML = `
    <h1 class="page-title">تایمر مطالعه</h1>
    <p class="page-sub">تمرکز کن، زمان رو بسپار به ما</p>

    <div class="card glass" style="text-align:center; padding:8px 12px 18px;">
      <input id="timerSubject" type="text" placeholder="روی چه درسی کار می‌کنی؟" value="${escapeHtml(TimerState.subject)}"
        style="background:transparent; border:none; text-align:center; font-size:14px; font-weight:700; color:var(--text-1); width:100%; padding:14px 6px 0; outline:none;"
        oninput="TimerState.subject=this.value" />

      <div class="timer-orbit">
        <div class="timer-ring-wrap">
          <svg viewBox="0 0 270 270">
            <defs>
              <linearGradient id="timerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#818cf8"/>
                <stop offset="100%" stop-color="#6366f1"/>
              </linearGradient>
            </defs>
            <circle class="timer-ring-bg" cx="135" cy="135" r="125"></circle>
            <circle class="timer-ring-fg" cx="135" cy="135" r="125"
              stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"></circle>
          </svg>
          <div class="timer-center">
            <div class="timer-display">${fa(mm)}:${fa(ss)}</div>
            <div class="timer-label">${TimerState.running ? 'در حال مطالعه…' : (TimerState.remainingSeconds===TimerState.totalSeconds ? 'آماده شروع' : 'مکث شده')}</div>
          </div>
        </div>
      </div>

      <div class="mode-pills">
        <button class="chip ${TimerState.mode==='pomodoro'?'on':''}" onclick="setTimerMode('pomodoro')">پومودورو ۲۵</button>
        <button class="chip ${TimerState.mode==='countdown'?'on':''}" onclick="setTimerMode('countdown')">شمارش‌معکوس</button>
        <button class="chip ${TimerState.mode==='stopwatch'?'on':''}" onclick="setTimerMode('stopwatch')">آزاد</button>
      </div>

      ${TimerState.mode==='countdown' ? `
      <div class="chip-row" style="justify-content:center; margin-top:10px;">
        <button class="chip" onclick="setCountdownMinutes(15)">۱۵ د</button>
        <button class="chip" onclick="setCountdownMinutes(30)">۳۰ د</button>
        <button class="chip" onclick="setCountdownMinutes(45)">۴۵ د</button>
        <button class="chip" onclick="setCountdownMinutes(60)">۶۰ د</button>
      </div>` : ''}

      <div class="timer-controls">
        <button class="timer-btn-round" onclick="resetTimer()"><span class="material-symbols-rounded">refresh</span></button>
        <button class="timer-btn-round main" onclick="toggleTimer()">
          <span class="material-symbols-rounded" style="font-size:32px;">${TimerState.running ? 'pause' : 'play_arrow'}</span>
        </button>
        <button class="timer-btn-round" onclick="finishTimerSession()"><span class="material-symbols-rounded">stop</span></button>
      </div>
    </div>

    <button class="btn btn-ghost" style="margin-top:14px;" onclick="openManualStudyLogSheet()">
      <span class="material-symbols-rounded" style="font-size:19px;">edit_calendar</span>
      ثبت دستی مطالعه (بدون تایمر)
    </button>

    <div class="section-head"><h3>یادآورها و آلارم‌ها</h3><span class="more" onclick="openAlarmsSheet()">مدیریت ›</span></div>
    <div id="alarmSummary"></div>

    <div class="section-head"><h3>جلسات اخیر</h3></div>
    <div id="recentSessions"></div>
  `;

  const alarmEl = root.querySelector('#alarmSummary');
  if (!DB.alarms.length) {
    alarmEl.innerHTML = emptyState('alarm_add', 'آلارمی تنظیم نشده', 'برای یادآوری زمان مطالعه یه آلارم اضافه کن');
  } else {
    alarmEl.innerHTML = `<div class="card">${DB.alarms.slice(0,3).map(a => `
      <div class="list-row">
        <div class="li-icon"><span class="material-symbols-rounded">${a.enabled ? 'alarm_on' : 'alarm_off'}</span></div>
        <div class="li-body">
          <div class="li-title">${fa(a.time)} — ${escapeHtml(a.label)}</div>
          <div class="li-sub">${a.days.length===7 ? 'هر روز' : a.days.map(d=>Jalali.WEEKDAYS[d]).join('، ')}</div>
        </div>
        <label class="switch"><input type="checkbox" ${a.enabled?'checked':''} onchange="toggleAlarm('${a.id}')"><span class="slider"></span></label>
      </div>`).join('')}</div>`;
  }

  const sessEl = root.querySelector('#recentSessions');
  if (!recentSessions.length) {
    sessEl.innerHTML = emptyState('history', 'هنوز جلسه‌ای ثبت نشده', 'اولین تایمرت رو الان بزن');
  } else {
    sessEl.innerHTML = recentSessions.map(s => `
      <div class="plan-item">
        <div class="li-icon" style="width:36px;height:36px;border-radius:10px;background:var(--surface-3); display:flex;align-items:center;justify-content:center;">
          <span class="material-symbols-rounded" style="font-size:18px; color:var(--primary-bright);">check</span>
        </div>
        <div style="flex:1;">
          <div class="plan-title">${escapeHtml(s.subject || 'بدون‌عنوان')}</div>
          <div class="plan-meta"><span>${Jalali.gregorianStrToJalaliStr(s.date)}</span><span>${formatMinutes(s.minutes)}</span></div>
        </div>
      </div>`).join('');
  }
};

function setTimerMode(mode) {
  stopInterval();
  TimerState.mode = mode;
  TimerState.running = false;
  if (mode === 'pomodoro') { TimerState.totalSeconds = POMO_PRESETS.pomodoro; TimerState.remainingSeconds = POMO_PRESETS.pomodoro; }
  else if (mode === 'countdown') { TimerState.totalSeconds = 30*60; TimerState.remainingSeconds = 30*60; }
  else { TimerState.totalSeconds = 0; TimerState.remainingSeconds = 0; }
  rerender();
}
function setCountdownMinutes(min) {
  stopInterval();
  TimerState.totalSeconds = min*60; TimerState.remainingSeconds = min*60; TimerState.running = false;
  rerender();
}
function resetTimer() {
  stopInterval();
  TimerState.running = false;
  if (TimerState.mode === 'stopwatch') TimerState.remainingSeconds = 0;
  else TimerState.remainingSeconds = TimerState.totalSeconds;
  rerender();
}
function toggleTimer() {
  if (TimerState.running) { stopInterval(); TimerState.running = false; rerender(); return; }
  TimerState.running = true;
  TimerState.startedAt = TimerState.startedAt || Date.now();
  TimerState.intervalId = setInterval(() => {
    if (TimerState.mode === 'stopwatch') {
      TimerState.remainingSeconds += 1;
      TimerState.totalSeconds = TimerState.remainingSeconds; // keep ring meaningful-ish
    } else {
      TimerState.remainingSeconds -= 1;
      if (TimerState.remainingSeconds <= 0) {
        TimerState.remainingSeconds = 0;
        stopInterval(); TimerState.running = false;
        playChime();
        showToast('زمان تموم شد! دمت گرم 🎉', 'celebration');
        finishTimerSession(true);
        return;
      }
    }
    if (currentScreen === 'timer') updateTimerDisplayOnly();
  }, 1000);
  rerender();
}
function stopInterval() {
  if (TimerState.intervalId) { clearInterval(TimerState.intervalId); TimerState.intervalId = null; }
}
function updateTimerDisplayOnly() {
  const disp = document.querySelector('.timer-display');
  const ring = document.querySelector('.timer-ring-fg');
  if (!disp) return;
  const mm = String(Math.floor(TimerState.remainingSeconds / 60)).padStart(2, '0');
  const ss = String(TimerState.remainingSeconds % 60).padStart(2, '0');
  disp.textContent = `${fa(mm)}:${fa(ss)}`;
  if (ring && TimerState.totalSeconds > 0) {
    const percent = Math.max(0, Math.min(1, (TimerState.totalSeconds - TimerState.remainingSeconds) / TimerState.totalSeconds));
    const circumference = 2 * Math.PI * 125;
    ring.style.strokeDashoffset = circumference * (1 - percent);
  }
}
function finishTimerSession(auto) {
  const elapsedSeconds = TimerState.mode === 'stopwatch'
    ? TimerState.remainingSeconds
    : (TimerState.totalSeconds - TimerState.remainingSeconds);
  const minutes = Math.round(elapsedSeconds / 60);
  stopInterval();
  TimerState.running = false;
  if (minutes >= 1) {
    DB.sessions.push({ id: uid(), date: Jalali.todayStr(), subject: TimerState.subject || 'مطالعه آزاد', minutes, mode: TimerState.mode });
    if (!auto) showToast(`${formatMinutes(minutes)} ثبت شد`);
  }
  TimerState.remainingSeconds = TimerState.mode === 'stopwatch' ? 0 : TimerState.totalSeconds;
  if (!auto) rerender();
}
function playChime() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    [880, 1108, 1318].forEach((freq, i) => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.type = 'sine'; o.frequency.value = freq;
      o.connect(g); g.connect(ctx.destination);
      const t0 = ctx.currentTime + i * 0.18;
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(0.2, t0 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.3);
      o.start(t0); o.stop(t0 + 0.32);
    });
  } catch (e) {}
}

// ---------------------------------------------------------------------------
// Alarms
// ---------------------------------------------------------------------------
function openAlarmsSheet() {
  renderAlarmsSheetBody();
}
function renderAlarmsSheetBody() {
  openSheet(`
    <h2>یادآورها و آلارم‌ها</h2>
    <div id="alarmListInSheet"></div>
    <button class="btn btn-primary" style="margin-top:14px;" onclick="openNewAlarmForm()">
      <span class="material-symbols-rounded" style="font-size:19px;">add_alarm</span> آلارم جدید
    </button>
  `);
  fillAlarmList();
}
function fillAlarmList() {
  const el = document.getElementById('alarmListInSheet');
  if (!el) return;
  if (!DB.alarms.length) { el.innerHTML = emptyState('alarm', 'آلارمی نداری', 'یکی اضافه کن تا یادت نره بخونی'); return; }
  el.innerHTML = DB.alarms.map(a => `
    <div class="list-row">
      <div class="li-icon"><span class="material-symbols-rounded">${a.enabled ? 'alarm_on' : 'alarm_off'}</span></div>
      <div class="li-body">
        <div class="li-title">${fa(a.time)} — ${escapeHtml(a.label)}</div>
        <div class="li-sub">${a.days.length===7 ? 'هر روز' : (a.days.length ? a.days.map(d=>Jalali.WEEKDAYS[d]).join('، ') : 'یک‌بار')}</div>
      </div>
      <label class="switch"><input type="checkbox" ${a.enabled?'checked':''} onchange="toggleAlarm('${a.id}')"><span class="slider"></span></label>
      <button class="icon-btn" style="width:30px;height:30px;" onclick="deleteAlarm('${a.id}')"><span class="material-symbols-rounded" style="font-size:15px;">close</span></button>
    </div>`).join('');
}
function openNewAlarmForm() {
  openSheet(`
    <h2>آلارم جدید</h2>
    <div class="field"><label>عنوان</label><input id="aLabel" type="text" placeholder="مثلاً شروع مطالعه فیزیک" /></div>
    <div class="field"><label>ساعت</label><input id="aTime" type="time" value="08:00" /></div>
    <div class="field">
      <label>روزهای هفته</label>
      <div class="chip-row" id="aDays">
        ${Jalali.WEEKDAYS.map((w,i) => `<button type="button" class="chip" data-d="${i}" onclick="this.classList.toggle('on')">${w}</button>`).join('')}
      </div>
    </div>
    <button class="btn btn-primary" onclick="submitNewAlarm()">ذخیره آلارم</button>
  `);
}
async function submitNewAlarm() {
  const label = document.getElementById('aLabel').value.trim() || 'یادآوری مطالعه';
  const time = document.getElementById('aTime').value || '08:00';
  const days = Array.from(document.querySelectorAll('#aDays .chip.on')).map(b => parseInt(b.dataset.d));
  try {
    await apiAddAlarm({ label, time, days, enabled: true });
    showToast('آلارم اضافه شد');
    renderAlarmsSheetBody();
    if (currentScreen === 'timer') rerender();
  } catch (e) {
    showToast('خطا: ' + e.message, 'error');
  }
}
async function toggleAlarm(id) {
  const a = DB.alarms.find(x => x.id === id); if (!a) return;
  try {
    await apiUpdateAlarm(id, { label: a.label, time: a.time, days: a.days, enabled: !a.enabled });
    fillAlarmList();
    if (currentScreen === 'timer') rerender();
  } catch (e) {
    showToast('خطا: ' + e.message, 'error');
  }
}
async function deleteAlarm(id) {
  try {
    await apiDeleteAlarm(id);
    fillAlarmList();
    if (currentScreen === 'timer') rerender();
  } catch (e) {
    showToast('خطا: ' + e.message, 'error');
  }
}

// check alarms once a minute against system clock
let lastAlarmMinuteKey = '';
function checkAlarmsLoop() {
  setInterval(() => {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, '0');
    const mi = String(now.getMinutes()).padStart(2, '0');
    const key = `${hh}:${mi}`;
    if (key === lastAlarmMinuteKey) return;
    lastAlarmMinuteKey = key;
    const dow = (now.getDay() + 1) % 7; // convert JS Sun=0 to Sat=0 scheme
    DB.alarms.forEach(a => {
      if (!a.enabled) return;
      if (a.time !== key) return;
      if (a.days.length && !a.days.includes(dow)) return;
      playChime();
      showToast(`⏰ ${a.label}`, 'alarm');
      if (window.Notification && Notification.permission === 'granted') {
        try { new Notification('اپکس پلنر', { body: a.label }); } catch (e) {}
      }
    });
  }, 15000);
}

Object.defineProperty(window, 'TimerState', { get() { return TimerState; }, configurable: true });

// ---------------------------------------------------------------------------
// ثبت دستی مطالعه — برای وقتی که با کرنومتر شخصی/خارج از اپ خوندی و فقط
// می‌خوای دقیقه و تعداد تست رو ثبت کنی، بدون اینکه تایمر داخل اپ رو زده باشی.
// دو حالت داره: وصل‌کردن به یه پارت برنامه‌ی موجود، یا ساخت یه پارت جدید و
// تکمیل فوری‌ش در همون لحظه.
// ---------------------------------------------------------------------------
function openManualStudyLogSheet() {
  const today = Jalali.todayStr();
  // پارت‌های درسیِ چند روز اخیر که هنوز تکمیل نشدن، برای انتخاب راحت‌تر
  const recentOpenItems = DB.planItems
    .filter(i => i.category === 'درسی' && !i.status && i.date >= Jalali.addDays(today, -7) && i.date <= today)
    .sort((a, b) => b.date.localeCompare(a.date));

  openSheet(`
    <h2>ثبت دستی مطالعه</h2>
    <p style="font-size:12.5px; color:var(--text-2); margin-top:-10px; margin-bottom:16px;">
      اگه با کرنومتر خودت یا خارج از اپ خوندی، همینجا ثبتش کن.
    </p>

    ${recentOpenItems.length ? `
    <div class="field">
      <label>یه پارت موجود رو انتخاب کن (اختیاری)</label>
      <select id="manualExistingItem" onchange="onManualExistingItemChange()">
        <option value="">— پارت جدید بساز —</option>
        ${recentOpenItems.map(i => `<option value="${i.id}">${escapeHtml(i.name)} (${Jalali.gregorianStrToJalaliStr(i.date)})</option>`).join('')}
      </select>
    </div>` : ''}

    <div id="manualNewItemFields">
      <div class="field"><label>نام درس/پارت</label><input id="manualSubjectName" type="text" placeholder="مثلاً فیزیک فصل ۳" /></div>
      <div class="field"><label>تاریخ</label><input id="manualDate" type="date" value="${today}" /></div>
    </div>

    <div class="field"><label>دقیقه مطالعه</label><input id="manualMinutes" type="number" min="0" placeholder="مثلاً ۶۰" /></div>
    <div class="field"><label>تعداد تست</label><input id="manualTests" type="number" min="0" placeholder="مثلاً ۱۵" /></div>

    <button class="btn btn-primary" onclick="submitManualStudyLog()">ثبت و تکمیل ✅</button>
  `);
}

function onManualExistingItemChange() {
  const sel = document.getElementById('manualExistingItem');
  const newFields = document.getElementById('manualNewItemFields');
  newFields.style.display = sel.value ? 'none' : 'block';
}

async function submitManualStudyLog() {
  const minutes = parseInt(document.getElementById('manualMinutes').value) || 0;
  const tests = parseInt(document.getElementById('manualTests').value) || 0;
  if (minutes <= 0 && tests <= 0) { showToast('حداقل دقیقه یا تعداد تست رو وارد کن'); return; }

  const existingSel = document.getElementById('manualExistingItem');
  const existingId = existingSel ? existingSel.value : '';

  try {
    if (existingId) {
      await saveStudyData(existingId, minutes, tests, true);
    } else {
      const name = document.getElementById('manualSubjectName').value.trim();
      const date = document.getElementById('manualDate').value || Jalali.todayStr();
      if (!name) { showToast('نام درس رو وارد کن'); return; }
      const created = await addPlanItem({ name, date, category: 'درسی' });
      await saveStudyData(created.id, minutes, tests, true);
    }
    closeSheet();
    showToast('ثبت شد 🎉');
    rerender();
  } catch (e) { /* توست خطا داخل saveStudyData/addPlanItem نمایش داده می‌شه */ }
}
