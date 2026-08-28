/* =========================================================================
   صفحه‌ی ورود / ثبت‌نام — قبل از باز شدن اصل اپ نمایش داده می‌شه.
   اولین نفری که توی کل گروه ثبت‌نام کنه، خودکار ادمین می‌شه (طبق منطق بکند).
   ========================================================================= */
let authMode = 'login'; // 'login' | 'register'

function ensureAuthOverlay() {
  if (document.getElementById('authOverlay')) return;
  const el = document.createElement('div');
  el.id = 'authOverlay';
  el.style.cssText = `
    position:fixed; inset:0; z-index:500; background:var(--bg);
    background-image: radial-gradient(ellipse 600px 400px at 15% -10%, rgba(99,102,241,.18), transparent 60%),
      radial-gradient(ellipse 500px 400px at 100% 20%, rgba(129,140,248,.1), transparent 55%);
    display:flex; align-items:center; justify-content:center; padding:24px;
    font-family:'Vazirmatn',sans-serif; direction:rtl;
  `;
  document.body.appendChild(el);
}

function showAuthScreen(errorMsg) {
  ensureAuthOverlay();
  const el = document.getElementById('authOverlay');
  el.style.display = 'flex';
  renderAuthForm(errorMsg);
}
function hideAuthScreen() {
  const el = document.getElementById('authOverlay');
  if (el) el.style.display = 'none';
}

function renderAuthForm(errorMsg) {
  const el = document.getElementById('authOverlay');
  const isLogin = authMode === 'login';
  el.innerHTML = `
    <div style="width:100%; max-width:380px;">
      <div style="text-align:center; margin-bottom:28px;">
        <div style="width:64px;height:64px;border-radius:18px; margin:0 auto 14px; background:linear-gradient(135deg,var(--primary-bright),var(--primary-dim)); display:flex; align-items:center; justify-content:center; font-size:28px; box-shadow:0 10px 30px -6px var(--primary-glow);">🎯</div>
        <div style="font-weight:800; font-size:20px; color:var(--text-1);">اپکس پلنر</div>
        <div style="font-size:12.5px; color:var(--text-2); margin-top:4px;">دستیار کنکور — نسخه‌ی گروهی</div>
      </div>

      <div class="card glass" style="padding:22px 20px;">
        <div class="seg" style="margin-bottom:18px;">
          <button type="button" class="${isLogin ? 'active' : ''}" onclick="authMode='login'; renderAuthForm();">ورود</button>
          <button type="button" class="${!isLogin ? 'active' : ''}" onclick="authMode='register'; renderAuthForm();">ثبت‌نام</button>
        </div>

        ${errorMsg ? `<div style="background:rgba(239,68,68,.12); border:1px solid rgba(239,68,68,.3); color:var(--danger); font-size:12.5px; padding:10px 12px; border-radius:10px; margin-bottom:14px;">${escapeHtml(errorMsg)}</div>` : ''}

        ${!isLogin ? `
        <div class="field">
          <label>اسمت (چیزی که بقیه می‌بینن)</label>
          <input id="authDisplayName" type="text" placeholder="مثلاً امین" />
        </div>` : ''}

        <div class="field">
          <label>نام کاربری</label>
          <input id="authUsername" type="text" placeholder="مثلاً amin_ak" autocapitalize="off" autocorrect="off" />
        </div>
        <div class="field">
          <label>رمز عبور</label>
          <input id="authPassword" type="password" placeholder="حداقل ۴ کاراکتر" />
        </div>

        <button class="btn btn-primary" id="authSubmitBtn" onclick="submitAuthForm()">
          ${isLogin ? 'ورود' : 'ساخت حساب'}
        </button>

        ${isLogin ? `<p style="text-align:center; font-size:11.5px; color:var(--text-3); margin-top:14px;">هنوز حساب نساختی؟ از تب «ثبت‌نام» بالا شروع کن.</p>` : `<p style="text-align:center; font-size:11.5px; color:var(--text-3); margin-top:14px;">بعد از ساخت حساب، توی بات تلگرام هم بزن: <br/><code style="color:var(--primary-bright);">/link ${''}</code> + نام‌کاربریت</p>`}
      </div>
    </div>
  `;

  // enter key submits
  ['authUsername', 'authPassword', 'authDisplayName'].forEach(id => {
    const elInput = document.getElementById(id);
    if (elInput) elInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') submitAuthForm(); });
  });
}

async function submitAuthForm() {
  const username = document.getElementById('authUsername').value.trim();
  const password = document.getElementById('authPassword').value;
  const btn = document.getElementById('authSubmitBtn');

  if (!username || username.length < 3) { renderAuthForm('نام کاربری باید حداقل ۳ حرف باشه'); return; }
  if (!password || password.length < 4) { renderAuthForm('رمز عبور باید حداقل ۴ کاراکتر باشه'); return; }

  btn.disabled = true;
  btn.textContent = '...';

  try {
    let result;
    if (authMode === 'login') {
      result = await Api.login(username, password);
    } else {
      const displayName = document.getElementById('authDisplayName').value.trim();
      if (!displayName) { renderAuthForm('اسمت رو وارد کن'); btn.disabled = false; return; }
      result = await Api.register(username, password, displayName);
    }
    Api.setToken(result.access_token);
    Api.setCachedUser(result.user);
    await bootAfterLogin();
  } catch (e) {
    renderAuthForm(e.message || 'خطایی پیش اومد');
  }
}

async function logout() {
  const uid_ = currentUserId();
  const pending = uid_ ? await Store.countPending(uid_) : 0;

  // اگه هنوز تغییراتی داریم که به سرور نرسیده (آفلاین بودیم)، هیچ‌وقت
  // اجازه نمی‌دیم خروج باعث گم‌شدنشون بشه. یا باید صبر کنیم آنلاین بشه و
  // خودکار سینک بشه، یا با تایید صریح کاربر (که می‌دونه چیکار می‌کنه)
  // ادامه بدیم — ولی حتی در اون حالت هم outbox رو پاک نمی‌کنیم، فقط از
  // اکانت خارج می‌شیم؛ با ورود مجدد همون کاربر، همون صف باز پردازش می‌شه.
  if (pending > 0 && !navigator.onLine) {
    openDialog({
      icon: 'cloud_off', title: 'تغییرات سینک‌نشده داری',
      text: `${fa(pending)} تغییر هنوز آفلاینه و به سرور نرسیده. اگه الان خارج بشی، این تغییرات پاک نمی‌شن و با ورود بعدیِ همین حساب، خودکار ارسال می‌شن — ولی تا اون‌موقع روی این دستگاه توی حساب دیگه‌ای دیده نمی‌شن.`,
      confirmText: 'باز هم خارج شو', confirmClass: 'btn-danger-ghost', cancelText: 'صبر می‌کنم آنلاین بشه',
      onConfirm: () => { closeDialog(); doLogout(); }
    });
    return;
  }

  openDialog({
    icon: 'logout', title: 'خروج از حساب',
    text: pending > 0
      ? `${fa(pending)} تغییر در حال ارسال به سرور هست؛ چند لحظه صبر کن تموم بشه یا الان خارج شو (تغییرات با ورود بعدی همین حساب سینک می‌شن).`
      : 'مطمئنی می‌خوای خارج بشی؟',
    confirmText: 'خروج', confirmClass: 'btn-danger-ghost',
    onConfirm: () => { closeDialog(); doLogout(); }
  });
}

function doLogout() {
  // فقط توکن پاک می‌شه؛ کش محلی (db_cache) و صفِ‌ارسال‌نشده (outbox) عمداً
  // دست‌نخورده می‌مونن تا اگه همین کاربر دوباره وارد بشه (حتی آفلاین)،
  // چیزی گم نشده باشه. این کش‌ها فقط با «پاک‌کردن همه‌داده‌ها»ی صریح از
  // پروفایل، یا وقتی processOutbox موفق به سینک‌کامل بشه، جابه‌جا می‌شن.
  Api.clearToken();
  DB = null;
  authMode = 'login';
  showAuthScreen();
}
