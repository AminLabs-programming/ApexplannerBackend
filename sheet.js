/* =========================================================================
   Bottom sheet + center dialog primitives
   ========================================================================= */
function ensureOverlays() {
  if (!document.getElementById('sheetOverlay')) {
    const o = document.createElement('div');
    o.id = 'sheetOverlay';
    o.className = 'overlay';
    o.innerHTML = `<div class="sheet" id="sheetContent"><div class="sheet-handle"></div><div id="sheetBody"></div></div>`;
    o.addEventListener('click', (e) => { if (e.target === o) closeSheet(); });
    document.body.appendChild(o);
  }
  if (!document.getElementById('dialogOverlay')) {
    const o = document.createElement('div');
    o.id = 'dialogOverlay';
    o.className = 'overlay center';
    o.innerHTML = `<div class="dialog" id="dialogContent"></div>`;
    o.addEventListener('click', (e) => { if (e.target === o) closeDialog(); });
    document.body.appendChild(o);
  }
}

function openSheet(html) {
  ensureOverlays();
  document.getElementById('sheetBody').innerHTML = html;
  document.getElementById('sheetOverlay').classList.add('active');
}
function closeSheet() {
  const o = document.getElementById('sheetOverlay');
  if (o) o.classList.remove('active');
}

function openDialog({ icon = 'info', title, text, confirmText = 'تایید', confirmClass = 'btn-primary', cancelText = 'انصراف', onConfirm }) {
  ensureOverlays();
  document.getElementById('dialogContent').innerHTML = `
    <span class="material-symbols-rounded big">${icon}</span>
    <h3>${title}</h3>
    <p>${text}</p>
    <div class="btn-row">
      <button class="btn ${confirmClass}" id="dialogConfirmBtn">${confirmText}</button>
      <button class="btn btn-ghost" onclick="closeDialog()">${cancelText}</button>
    </div>
  `;
  document.getElementById('dialogConfirmBtn').onclick = onConfirm;
  document.getElementById('dialogOverlay').classList.add('active');
}
function closeDialog() {
  const o = document.getElementById('dialogOverlay');
  if (o) o.classList.remove('active');
}
