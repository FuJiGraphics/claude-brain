'use strict';
// brain - 폰 앱처럼 생긴 데스크톱용 기억 돌보기 화면. 서버(editor/server.py)의 API 만 쓴다.
// 기억(cortex)을 바꾸는 동작(먹이, 정정, 최적화, 잠)은 서버가 해마 큐와 기존 스크립트로 넘긴다. 성격만 여기서 직접 저장한다.

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const phone = $('#phone');
const screen = $('#screen');
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const kbdTip = (text, key) => `${esc(text)}${key ? `<kbd>${esc(key)}</kbd>` : ''}`;

// ---------------------------------------------------------------- 토큰, API
let TOKEN = '';
(function initToken() {
  const u = new URL(location.href);
  const t = u.searchParams.get('t');
  if (t) {
    TOKEN = t;
    try { sessionStorage.setItem('brainToken', t); } catch (e) { /* 이 탭에서는 메모리로 쓴다 */ }
    u.searchParams.delete('t');
    history.replaceState(null, '', u.pathname + u.search + u.hash);
  } else {
    try { TOKEN = sessionStorage.getItem('brainToken') || ''; } catch (e) { TOKEN = ''; }
  }
})();

async function api(path, body) {
  const opt = { headers: { 'X-Brain-Token': TOKEN } };
  if (body !== undefined) {
    opt.method = 'POST';
    opt.headers['Content-Type'] = 'application/json';
    opt.body = JSON.stringify(body);
  }
  let r;
  try { r = await fetch(path, opt); } catch (e) { throw new Error('서버와 연결이 끊겼어요'); }
  const j = await r.json().catch(() => ({ error: '응답을 읽지 못했어요' }));
  if (!r.ok) throw new Error(j.error || ('HTTP ' + r.status));
  return j;
}

let toastTimer = 0;
function toast(msg, ms = 2600) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.remove('on'); void t.offsetWidth; t.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('on'), ms);
}

// ---------------------------------------------------------------- 테마
function applyTheme(v) {
  if (v === 'light' || v === 'dark') document.documentElement.dataset.theme = v;
  else delete document.documentElement.dataset.theme;
}
let THEME = 'auto';
try { THEME = localStorage.getItem('brainTheme') || 'auto'; } catch (e) { THEME = 'auto'; }
applyTheme(THEME);

// ---------------------------------------------------------------- 형식
const fmtAgo = (ts) => {
  if (!ts) return '-';
  const diff = (Date.now() - ts * 1000) / 1000;
  if (diff < 60) return '방금';
  if (diff < 3600) return Math.floor(diff / 60) + '분 전';
  if (diff < 86400) return Math.floor(diff / 3600) + '시간 전';
  if (diff < 86400 * 14) return Math.floor(diff / 86400) + '일 전';
  const d = new Date(ts * 1000);
  return (d.getMonth() + 1) + '월 ' + d.getDate() + '일';
};
const pct = (x) => Math.round((x || 0) * 100) + '%';
const kTok = (n) => (n >= 10000 ? (n / 10000).toFixed(1).replace(/\.0$/, '') + '만' : (n || 0).toLocaleString());
const barCls = (r) => (r > 1 ? 'hi' : r > 0.85 ? 'mid' : '');
const LV = { egg: 0, baby: 1, kid: 2, adult: 3, sage: 4 };
const REGION = {
  trap: { n: '함정', e: '⚠️', c: 'var(--r-trap)' },
  decision: { n: '결정과 선호', e: '⭐', c: 'var(--r-decision)' },
  procedure: { n: '절차와 요령', e: '🧰', c: 'var(--r-procedure)' },
  fact: { n: '구조와 사실', e: '🧱', c: 'var(--r-fact)' },
  other: { n: '그 밖의 교훈', e: '📎', c: 'var(--r-other)' },
};
const REGION_ORDER = ['trap', 'decision', 'procedure', 'fact', 'other'];
const TINTS = ['--pink-l', '--lav-l', '--mint-l', '--sky-l', '--lemon-l', '--peach-l'];
const tintOf = (s) => { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) >>> 0; return 'var(' + TINTS[h % TINTS.length] + ')'; };
const MOOD_EMOJI = { happy: '😆', full: '😋', overload: '😵', sleepy: '😪', study: '🤓', sick: '🤢', bored: '🥱', egg: '🥚', off: '😶' };
const layerName = (l) => (l === 'common' ? '공용 뇌' : l.startsWith('stacks/') ? l.slice(7) + ' 스택' : l.replace(/^projects\//, ''));
const MODE_NAME = { replay: '대화 되짚기', record: '새기기', sweep: '정리', targeted: '검색 실패 학습', register: '프로젝트 등록', 'harness-refresh': '도구 재검증' };
const ST_ICON = { done: '✅', partial: '🌓', failed: '💥', denied: '🚫', timeout: '⏰' };

// ---------------------------------------------------------------- 캐릭터
function pet(mood, stage, cls = '') {
  const m = mood || 'happy';
  const st = stage || 'adult';
  const scale = { egg: 1, baby: 0.78, kid: 0.88, adult: 1, sage: 1 }[st] || 1;
  const ink = '#3a2533';
  if (st === 'egg' || m === 'egg') {
    return `<svg class="pet ${cls} egg" viewBox="0 0 120 120" aria-hidden="true"><g class="body">
      <ellipse cx="60" cy="100" rx="26" ry="5" fill="rgba(0,0,0,.08)"/>
      <path d="M60 18 C82 18 94 52 94 70 C94 88 80 98 60 98 C40 98 26 88 26 70 C26 52 38 18 60 18 Z" fill="#fff6e8" stroke="#f0d9b5" stroke-width="2.5"/>
      <path d="M32 62 l9 -6 l7 7 l8 -8 l8 8 l8 -7 l8 7 l9 -5" fill="none" stroke="#d9b98a" stroke-width="2.5" stroke-linejoin="round"/>
      <g class="eyes"><circle class="eye" cx="50" cy="72" r="3" fill="${ink}"/><circle class="eye" cx="70" cy="72" r="3" fill="${ink}"/></g>
      <ellipse cx="44" cy="79" rx="4" ry="2.5" fill="#ff8fab" opacity=".35"/><ellipse cx="76" cy="79" rx="4" ry="2.5" fill="#ff8fab" opacity=".35"/>
    </g></svg>`;
  }
  const S = `stroke="${ink}" stroke-linecap="round"`;
  const eyes = {
    happy: `<path d="M41 61 q5 -6 10 0" ${S} stroke-width="3" fill="none"/><path d="M69 61 q5 -6 10 0" ${S} stroke-width="3" fill="none"/>`,
    full: `<circle class="eye" cx="46" cy="60" r="3.4" fill="${ink}"/><circle class="eye" cx="74" cy="60" r="3.4" fill="${ink}"/>`,
    study: `<circle class="eye" cx="46" cy="60" r="3" fill="${ink}"/><circle class="eye" cx="74" cy="60" r="3" fill="${ink}"/>`,
    overload: `<path d="M42 56 l8 8 M50 56 l-8 8 M70 56 l8 8 M78 56 l-8 8" ${S} stroke-width="3"/>`,
    sleepy: `<path d="M41 60 q5 4 10 0" ${S} stroke-width="3" fill="none"/><path d="M69 60 q5 4 10 0" ${S} stroke-width="3" fill="none"/>`,
    off: `<path d="M41 61 h10 M69 61 h10" ${S} stroke-width="3"/>`,
    sick: `<path d="M42 57 l8 3 l-8 3 M78 57 l-8 3 l8 3" ${S} stroke-width="2.6" fill="none" stroke-linejoin="round"/>`,
    bored: `<circle cx="46" cy="62" r="2.6" fill="${ink}"/><circle cx="74" cy="62" r="2.6" fill="${ink}"/>`,
  }[m] || '';
  const lids = {
    study: `<circle cx="46" cy="60" r="8" fill="none" stroke="${ink}" stroke-width="2"/><circle cx="74" cy="60" r="8" fill="none" stroke="${ink}" stroke-width="2"/><path d="M54 60 h12" stroke="${ink}" stroke-width="2"/>`,
    bored: `<path d="M40 58 h12 M68 58 h12" ${S} stroke-width="2.6"/>`,
  }[m] || '';
  const mouth = {
    happy: `<path d="M53 69 q7 8 14 0" ${S} stroke-width="3" fill="#ff7a9a" stroke-linejoin="round"/>`,
    full: `<path d="M55 70 q5 4 10 0" ${S} stroke-width="2.6" fill="none"/>`,
    study: `<path d="M56 72 h8" ${S} stroke-width="2.6"/>`,
    overload: `<path d="M50 73 q2.5 -3 5 0 q2.5 3 5 0 q2.5 -3 5 0 q2.5 3 5 0" ${S} stroke-width="2.4" fill="none"/>`,
    sleepy: `<ellipse cx="60" cy="72" rx="3" ry="3.6" fill="${ink}"/>`,
    off: `<path d="M56 72 h8" ${S} stroke-width="2.4"/>`,
    sick: `<path d="M52 74 q4 -4 8 0 q4 4 8 0" ${S} stroke-width="2.4" fill="none"/>`,
    bored: `<path d="M54 73 h12" ${S} stroke-width="2.6"/>`,
  }[m] || '';
  const extra = {
    overload: `<path d="M98 34 q4 7 0 10 q-4 -3 0 -10 Z" fill="#7cc7ff"/><g class="steam" fill="#c9c2cf"><circle cx="40" cy="14" r="5"/><circle cx="48" cy="9" r="4"/><circle cx="76" cy="12" r="5"/><circle cx="84" cy="7" r="3.5"/></g>`,
    sleepy: `<text class="zz" x="92" y="30" font-size="16" font-weight="800" fill="#9c7dff">z</text><text class="zz" x="100" y="20" font-size="11" font-weight="800" fill="#9c7dff" style="animation-delay:.8s">z</text>`,
    study: `<g transform="translate(86 74) rotate(-12)"><rect x="0" y="0" width="18" height="14" rx="2" fill="#4fb1ff"/><path d="M9 0 v14" stroke="#fff" stroke-width="1.5"/></g>`,
    sick: `<ellipse cx="60" cy="56" rx="30" ry="26" fill="#9be7a6" opacity=".22"/>`,
    happy: `<path d="M100 30 l2 5 l5 2 l-5 2 l-2 5 l-2 -5 l-5 -2 l5 -2 Z" fill="#ffcf3f"/>`,
  }[m] || '';
  const cap = st === 'sage'
    ? `<g transform="translate(60 18)"><path d="M-22 0 L0 -10 L22 0 L0 10 Z" fill="${ink}"/><rect x="-10" y="2" width="20" height="9" rx="2" fill="${ink}"/><path d="M18 1 v12" stroke="#ffcf3f" stroke-width="2"/><circle cx="18" cy="14" r="2.5" fill="#ffcf3f"/></g>` : '';
  const grey = m === 'off' ? ' style="filter:grayscale(1);opacity:.75"' : '';
  return `<svg class="pet ${cls} ${m}" viewBox="0 0 120 120" aria-hidden="true"${grey}>
    <ellipse cx="60" cy="100" rx="${30 * scale}" ry="5" fill="rgba(0,0,0,.08)"/>
    <g transform="translate(60 100) scale(${scale}) translate(-60 -100)"><g class="body">
      <ellipse cx="47" cy="94" rx="8" ry="5" fill="var(--brain-d)"/><ellipse cx="73" cy="94" rx="8" ry="5" fill="var(--brain-d)"/>
      <path d="M30 78 C14 76 10 56 22 48 C18 32 34 20 48 26 C54 14 74 14 80 26 C96 20 110 36 102 50 C114 58 108 80 92 80 C88 92 70 96 60 88 C50 96 34 92 30 78 Z"
        fill="var(--brain)" stroke="var(--brain-d)" stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M60 22 C56 34 64 40 59 48" stroke="var(--brain-d)" stroke-width="2.2" fill="none" stroke-linecap="round" opacity=".75"/>
      <path d="M30 44 C36 38 42 44 38 50 M82 40 C88 36 94 42 90 48 M44 32 c4 -3 9 0 8 4 M70 30 c3 -3 8 -1 8 3" stroke="var(--brain-d)" stroke-width="2" fill="none" stroke-linecap="round" opacity=".55"/>
      <ellipse cx="38" cy="69" rx="5.5" ry="3.5" fill="#ff6f91" opacity=".32"/><ellipse cx="82" cy="69" rx="5.5" ry="3.5" fill="#ff6f91" opacity=".32"/>
      <g class="eyes">${eyes}</g>${lids}${mouth}${extra}${cap}
    </g></g></svg>`;
}

// 눈이 마우스를 따라간다 - 화면에 보이는 모든 뇌가 커서 쪽을 본다
let mouse = null;
let eyeRaf = 0;
function updateEyes() {
  eyeRaf = 0;
  $$('.pet .eyes').forEach((g) => {
    const svg = g.ownerSVGElement;
    if (!svg) return;
    if (!mouse) { g.style.transform = ''; return; }
    const r = svg.getBoundingClientRect();
    if (!r.width) return;
    const dx = mouse.x - (r.left + r.width / 2), dy = mouse.y - (r.top + r.height * 0.5);
    const d = Math.hypot(dx, dy) || 1;
    const k = Math.min(1, d / 260) * 3.2;
    g.style.transform = `translate(${(dx / d * k).toFixed(2)}px, ${(dy / d * k * 0.8).toFixed(2)}px)`;
  });
}
document.addEventListener('pointermove', (e) => { mouse = { x: e.clientX, y: e.clientY }; if (!eyeRaf) eyeRaf = requestAnimationFrame(updateEyes); });
window.addEventListener('mouseout', (e) => { if (!e.relatedTarget) { mouse = null; if (!eyeRaf) eyeRaf = requestAnimationFrame(updateEyes); } });

// 폰 틀은 스크롤되면 안 된다(포커스 이동이나 스크롤 호출이 overflow:hidden 틀도 움직인다) - 움직이면 바로 되돌린다
phone.addEventListener('scroll', () => { if (phone.scrollTop || phone.scrollLeft) { phone.scrollTop = 0; phone.scrollLeft = 0; } });
window.addEventListener('scroll', () => { if (window.scrollY || window.scrollX) window.scrollTo(0, 0); });

// ---------------------------------------------------------------- 툴팁
const tipEl = document.createElement('div');
tipEl.className = 'tip';
tipEl.setAttribute('role', 'tooltip');
phone.appendChild(tipEl);
let tipFor = null;
let tipTimer = 0;
function showTip(t) {
  if (!t.isConnected || !t.dataset.tip) return;
  tipEl.innerHTML = t.dataset.tip;
  const pr = phone.getBoundingClientRect(), r = t.getBoundingClientRect();
  tipEl.style.left = '0px'; tipEl.style.top = '0px';
  const w = tipEl.offsetWidth, h = tipEl.offsetHeight;
  let x = r.left - pr.left + r.width / 2 - w / 2;
  x = Math.max(8, Math.min(pr.width - w - 8, x));
  let y = r.top - pr.top - h - 8;
  if (y < 8) y = r.bottom - pr.top + 8;
  tipEl.style.left = x + 'px'; tipEl.style.top = y + 'px';
  tipEl.classList.add('on');
}
function hideTip() { clearTimeout(tipTimer); tipFor = null; tipEl.classList.remove('on'); }
phone.addEventListener('pointerover', (e) => {
  const t = e.target.closest('[data-tip]');
  if (t === tipFor) return;
  hideTip();
  if (t) { tipFor = t; tipTimer = setTimeout(() => showTip(t), 380); }
});
phone.addEventListener('pointerout', (e) => { if (tipFor && !tipFor.contains(e.relatedTarget)) hideTip(); });
phone.addEventListener('pointerdown', () => { hideTip(); phone.classList.remove('kbd-mode'); });
phone.addEventListener('focusin', (e) => {
  const t = e.target.closest('[data-tip]');
  hideTip();
  if (t && phone.classList.contains('kbd-mode')) { tipFor = t; showTip(t); }
});
phone.addEventListener('focusout', hideTip);
screen.addEventListener('scroll', hideTip, { passive: true });

// ---------------------------------------------------------------- 마크다운 (기억 본문)
function normPath(base, rel) {
  const out = [];
  (base ? base.split('/') : []).concat(rel.split('/')).forEach((p) => { if (p === '..') out.pop(); else if (p && p !== '.') out.push(p); });
  return out.join('/');
}
function md(src, baseDir) {
  const inline = (s) => esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (all, t, href) => {
      const h = href.replace(/&amp;/g, '&');
      if (/\.md(#.*)?$/.test(h) && !/^https?:/.test(h)) return `<a href="#" data-mem="${esc(normPath(baseDir, h.replace(/#.*$/, '')))}">${t}</a>`;
      return `<u title="${esc(h)}">${t}</u>`;
    });
  let html = '', code = null, list = false;
  const closeList = () => { if (list) { html += '</ul>'; list = false; } };
  for (const ln of String(src || '').replace(/\r/g, '').split('\n')) {
    if (code !== null) {
      if (/^```/.test(ln)) { html += `<pre><code>${esc(code.join('\n'))}</code></pre>`; code = null; } else code.push(ln);
      continue;
    }
    if (/^```/.test(ln)) { closeList(); code = []; continue; }
    const h = ln.match(/^(#{1,3})\s+(.*)$/);
    if (h) { closeList(); html += `<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`; continue; }
    const li = ln.match(/^\s*[-*]\s+(.*)$/);
    if (li) { if (!list) { html += '<ul>'; list = true; } html += `<li>${inline(li[1])}</li>`; continue; }
    closeList();
    if (/^>\s?/.test(ln)) { html += `<blockquote>${inline(ln.replace(/^>\s?/, ''))}</blockquote>`; continue; }
    if (ln.trim()) html += `<p>${inline(ln)}</p>`;
  }
  if (code !== null) html += `<pre><code>${esc(code.join('\n'))}</code></pre>`;
  closeList();
  return html;
}

// ---------------------------------------------------------------- 시트 (아래에서 올라오는 패널)
const SHEETS = [];
const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), textarea:not([disabled]), select, [tabindex]:not([tabindex="-1"])';
function syncSheetState() {
  phone.classList.toggle('sheet-open', SHEETS.length > 0);
  phone.classList.toggle('stack2', SHEETS.length > 1);
  $('#sheetBg').classList.toggle('on', SHEETS.length > 0);
  screen.inert = SHEETS.length > 0;
  $('#tabbar').inert = SHEETS.length > 0;
  SHEETS.forEach((s, i) => { s.el.inert = i !== SHEETS.length - 1; });
}
function openSheet({ title, full = false, body, foot, onClose, beforeClose, kind }) {
  hideTip();
  const el = document.createElement('section');
  el.className = 'sheet' + (full ? ' full' : '');
  el.setAttribute('role', 'dialog');
  el.setAttribute('aria-modal', 'true');
  el.innerHTML = `<div class="grab" data-tip="끌어내려서 닫기"><i></i></div>
    <div class="sh"><div class="t">${title}</div><button class="x" aria-label="닫기" data-tip="${kbdTip('닫기', 'Esc')}">✕</button></div>
    <div class="sb"></div>${foot ? '<div class="foot"></div>' : ''}`;
  $('#sheets').appendChild(el);
  const sh = { el, sb: $('.sb', el), foot: $('.foot', el), onClose, beforeClose, kind, opener: document.activeElement, submit: null };
  SHEETS.push(sh);
  syncSheetState();
  $('.x', el).addEventListener('click', () => closeSheet(sh));
  // 손잡이를 끌어내리면 닫힌다
  const grab = $('.grab', el);
  grab.addEventListener('pointerdown', (e) => {
    grab.setPointerCapture(e.pointerId);
    el.classList.add('drag');
    const sy = e.clientY;
    let dy = 0;
    const mv = (ev) => { dy = Math.max(0, ev.clientY - sy); el.style.transform = `translateY(${dy}px)`; };
    const up = () => {
      grab.removeEventListener('pointermove', mv); grab.removeEventListener('pointerup', up); grab.removeEventListener('pointercancel', up);
      el.classList.remove('drag'); el.style.transform = '';
      if (dy > 110) closeSheet(sh);
    };
    grab.addEventListener('pointermove', mv); grab.addEventListener('pointerup', up); grab.addEventListener('pointercancel', up);
  });
  if (body) body(sh.sb, sh);
  if (foot) foot(sh.foot, sh);
  requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add('on')));
  // 열리고 나면 첫 입력칸(없으면 닫기 버튼)에 포커스
  setTimeout(() => {
    if (!el.isConnected) return;
    const f = $('[data-autofocus]', el) || $('.sb textarea, .sb input:not([type=checkbox])', el) || $('.x', el);
    if (f) f.focus({ preventScroll: true });
  }, 320);
  return sh;
}
function closeSheet(sh, force) {
  const s = sh || SHEETS[SHEETS.length - 1];
  const i = SHEETS.indexOf(s);
  if (i < 0) return false;
  if (!force && s.beforeClose && s.beforeClose() === false) return false;
  SHEETS.splice(i, 1);
  hideTip();
  s.el.classList.remove('on');
  setTimeout(() => s.el.remove(), 450);
  syncSheetState();
  if (s.onClose) s.onClose();
  if (s.opener && s.opener.isConnected && !s.opener.closest('[inert]')) s.opener.focus({ preventScroll: true });
  return true;
}
function closeAllSheets() { while (SHEETS.length) closeSheet(SHEETS[SHEETS.length - 1], true); }
$('#sheetBg').addEventListener('click', () => closeSheet());
// 맨 위 시트 안에서만 Tab 이 돈다
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Tab' || !SHEETS.length) return;
  const el = SHEETS[SHEETS.length - 1].el;
  const f = $$(FOCUSABLE, el).filter((x) => x.offsetParent !== null || x === document.activeElement);
  if (!f.length) return;
  if (!el.contains(document.activeElement)) { e.preventDefault(); f[0].focus(); return; }
  const first = f[0], last = f[f.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
});

// ---------------------------------------------------------------- 공통 상태
let OV = null;
async function loadOverview() {
  try { OV = await api('/api/overview'); } catch (e) { OV = null; }
  return OV;
}
const noConn = () => `<div class="empty" style="padding-top:120px"><span class="big">🔌</span>서버에 연결하지 못했어요<br><span class="hint">Claude Code 에서 /claude-brain-app 로 다시 열어 주세요</span></div>`;

// ---------------------------------------------------------------- 홈
function careItems(ov) {
  const out = [];
  if (!ov.config.enabled) out.push({ e: '😶', bg: 'var(--bg2)', t: 'brain 이 꺼져 있어요', d: '떠올리지도 배우지도 않아요', go: '켜기', act: 'on' });
  const all = ov.projects.map((p) => Object.assign({ layer: 'projects/' + p.slug }, p)).concat(ov.shared);
  all.filter((p) => p.capacity > 1).sort((a, b) => b.capacity - a.capacity).slice(0, 2).forEach((p) =>
    out.push({ e: '💦', bg: 'var(--peach-l)', t: `${layerName(p.layer)} 머리가 꽉 찼어요`, d: `머리 무게 ${pct(p.capacity)}`, go: '최적화', href: `#/p/${p.layer}?open=opt` }));
  const fails = (ov.results || []).filter((r) => ['failed', 'denied', 'timeout'].includes(r.status)).length;
  if (fails) out.push({ e: '💥', bg: 'var(--pink-l)', t: `해마가 ${fails}건 실패했어요`, d: '일지에서 이유를 볼 수 있어요', go: '보기', href: '#/journal' });
  const ls = ov.config.last_sleep;
  if (ov.config.enabled && (!ls || Date.now() / 1000 - ls > 36 * 3600)) {
    out.push({ e: '🌙', bg: 'var(--lav-l)', t: ls ? '하루 넘게 못 잤어요' : '아직 한 번도 안 잤어요', d: '재우면 정리하고 오래된 건 잊어요', go: '재우기', act: 'sleep' });
  }
  if (ov.projects.length && !ov.projects.some((p) => p.persona)) {
    const big = ov.projects.slice().sort((a, b) => b.count - a.count)[0];
    out.push({ e: '🎭', bg: 'var(--lav-l)', t: '성격을 정한 뇌가 아직 없어요', d: `${big.slug} 부터 정해 볼까요?`, go: '정하기', href: `#/p/projects/${encodeURIComponent(big.slug)}?open=persona` });
  }
  return out.slice(0, 4);
}
async function doCare(act, btn) {
  btn.disabled = true;
  try {
    if (act === 'sleep') { await api('/api/sleep', {}); toast('🌙 쿨쿨… 정리하고 잊을 건 잊어요'); }
    if (act === 'on') { await api('/api/config', { action: 'on' }); toast('🧠 brain 이 깨어났어요'); }
    btn.closest('.care-item').style.opacity = '.4';
    setTimeout(route, 1200);
  } catch (e) { toast(e.message); btn.disabled = false; }
}

async function pageHome(alive) {
  const ov = await loadOverview();
  if (!alive()) return;
  if (!ov) { screen.innerHTML = noConn(); return; }
  document.title = 'brain';
  const h = ov.hippo;
  const tiles = ov.projects.map((p, i) => {
    const alert = p.capacity > 1 ? '<span class="alert">💦</span>' : '';
    const ps = p.persona ? `<span class="ps">${breedIcon(p.persona.breed)}</span>` : '';
    const tip = `${esc(p.mood.name)}, 기억 ${p.count}개, 머리 무게 ${pct(p.capacity)}${p.persona ? `<br>성격: ${esc(p.persona.name || '있음')}` : ''}`;
    return `<a class="pet-tile" href="#/p/projects/${encodeURIComponent(p.slug)}" style="--t:${tintOf(p.slug)};animation-delay:${i * 60}ms" data-tip="${esc(tip)}">
      <span class="lv">Lv.${LV[p.stage.key]} ${esc(p.stage.name)}</span>${alert || ps}
      ${pet(p.mood.key, p.stage.key)}
      <span class="nm">${esc(p.slug)}</span>
      <span class="md">${MOOD_EMOJI[p.mood.key] || ''} ${esc(p.mood.name)}</span>
      <span class="minibar ${barCls(p.capacity)}"><i style="width:${Math.min(100, p.capacity * 100)}%"></i></span>
    </a>`;
  }).join('');
  const shared = ov.shared.map((s) => `<a href="#/p/${s.layer}" data-tip="${esc(`${s.mood.name}, 머리 무게 ${pct(s.capacity)}`)}">${pet(s.mood.key, s.stage.key)}
      <span><span class="t">${esc(layerName(s.layer))}</span><br><span class="s">기억 ${s.count}</span></span></a>`).join('');
  const total = ov.projects.reduce((a, p) => a + p.count, 0) + ov.shared.reduce((a, s) => a + s.count, 0);
  const care = careItems(ov);
  screen.innerHTML = `
    <div class="top">
      <div class="logo">${pet(ov.config.enabled ? 'happy' : 'off', 'adult')}<b>brain</b></div>
      <a class="pill${h.alive ? ' busy' : ''}" href="#/journal" data-tip="해마 일지 보기"><span class="dot"></span>${h.alive ? '해마 공부 중' : '해마 쉬는 중'}${ov.queue ? ` ${ov.queue}` : ''}</a>
    </div>
    <div class="hello">${ov.config.enabled ? `뇌 ${ov.projects.length}개가 자라고 있어요` : 'brain 이 잠시 꺼져 있어요'}</div>
    <p class="sub">${ov.age != null ? `태어난 지 ${ov.age + 1}일째, ` : ''}모두 합쳐 기억 ${total.toLocaleString()}개</p>
    ${care.length ? `<div class="h2" style="margin-top:4px">오늘의 돌봄</div><div class="care">${care.map((c, i) => `
      ${c.href ? `<a class="care-item" href="${c.href}">` : `<button class="care-item" data-act="${c.act}" data-i="${i}">`}
        <span class="ce" style="background:${c.bg}">${c.e}</span><span><span class="ct">${esc(c.t)}</span><br><span class="cd">${esc(c.d)}</span></span><span class="go">${esc(c.go)} ›</span>
      ${c.href ? '</a>' : '</button>'}`).join('')}</div>` : ''}
    <div class="h2" style="margin-top:4px">내 뇌들 <small>눌러서 들어가기</small></div>
    <div class="pets">${tiles || '<div class="empty">아직 등록된 프로젝트가 없어요</div>'}</div>
    <div class="h2">물려받는 뇌 <small>여러 프로젝트가 같이 써요</small></div>
    <div class="shared">${shared}</div>`;
  $$('.care-item[data-act]').forEach((b) => b.addEventListener('click', () => doCare(b.dataset.act, b)));
  updateEyes();
}

// ---------------------------------------------------------------- 프로젝트 (뇌 하나)
let CUR = null;   // 지금 보는 레이어 데이터
let TOP = null;   // 지금 보는 레이어의 주제
let topicTimer = 0;
let SAY_DEFAULT = '';
let sayTimer = 0;

async function pageProject(layer, alive, openWhat) {
  clearTimeout(topicTimer);
  let d;
  try { d = await api('/api/layer?l=' + encodeURIComponent(layer)); } catch (e) {
    if (alive()) screen.innerHTML = /연결|토큰/.test(e.message) ? noConn()
      : `<div class="empty" style="padding-top:120px"><span class="big">🔍</span>이 뇌를 찾지 못했어요<br><a class="btn soft small" href="#/" style="margin-top:14px">홈으로</a></div>`;
    return;
  }
  if (!alive()) return;
  CUR = d; TOP = null;
  document.title = 'brain - ' + layerName(layer);
  const isProj = layer.startsWith('projects/');
  const slug = isProj ? layer.slice(9) : '';
  const st = d.stage;
  const kinds = REGION_ORDER.filter((k) => d.regions[k]);
  const ps = d.persona;
  SAY_DEFAULT = d.mood.why;
  const weightTip = d.capacity > 1 ? '머리가 꽉 찼어요. 최적화하면 다시 또렷해져요' : d.capacity > 0.85 ? '조금 무거워요. 곧 최적화가 필요해요' : '가벼워요. 잘 떠올릴 수 있어요';
  screen.innerHTML = `
    <div class="top">
      <a class="round" href="#/" aria-label="뒤로" data-tip="${kbdTip('뒤로', 'Esc')}">‹</a>
      <div class="jua" style="font-size:22px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(layerName(layer))}</div>
      <span class="lv" data-tip="${st.next ? esc(`${st.next_name}까지 기억 ${st.next - d.count}개`) : '다 컸어요'}">Lv.${LV[st.key]} ${esc(st.name)}</span>
    </div>
    <div class="stage" id="stage" style="--stage-c:${tintOf(layer)}">
      <span class="pill mood-chip" data-tip="${esc(d.mood.why)}">${MOOD_EMOJI[d.mood.key] || ''} ${esc(d.mood.name)}</span>
      <button class="pill ai-chip" id="aiChip" ${d.count ? '' : 'hidden'}><span class="shimmer">단어 고르는 중…</span></button>
      <button class="pet-wrap" id="petWrap" aria-label="뇌 쓰다듬기" data-tip="쓰다듬기">${pet(d.mood.key, st.key)}</button>
      <div class="hearts" id="hearts"></div>
      <div class="say" id="say">${esc(SAY_DEFAULT)}</div>
    </div>
    <div class="stats">
      <div class="stat" data-tip="이 뇌에 든 기억 수"><div class="k">기억</div><div class="v">${d.count}</div></div>
      <div class="stat" data-tip="설치 뒤 이번 주에 새로 배운 기억"><div class="k">이번 주</div><div class="v">+${d.learned_week}</div></div>
      <div class="stat" data-tip="${d.usage == null ? '잠이 기억 강도를 모으면 보여요' : '최근 2주에 떠오르거나 열린 기억 비율'}"><div class="k">활용도</div><div class="v">${d.usage == null ? '<small>관찰 중</small>' : pct(d.usage)}</div></div>
    </div>
    <button class="weight card" id="weightBtn" data-tip="${esc(weightTip)}">
      <div class="row"><span>🎒 머리 무게</span><span style="color:${d.capacity > 1 ? 'var(--bad)' : 'inherit'}">${pct(d.capacity)}</span></div>
      <div class="bar ${barCls(d.capacity)}"><i style="width:${Math.min(100, d.capacity * 100)}%"></i></div>
      <div class="hint" style="margin-top:6px">${esc(weightTip)}</div>
    </button>
    <div class="actions">
      ${isProj ? `<button class="act" id="aFeed" data-say="배고파요! 꼭 기억할 걸 알려 주세요 🍙" data-tip="${kbdTip('꼭 기억할 것 알려 주기', 'F')}"><span class="ai">🍙</span><span class="al">먹이 주기</span><span class="as">꼭 기억할 것 알려 주기</span><span class="kbd">F</span></button>` : ''}
      <button class="act lemon" id="aOpt" data-say="${d.capacity > 1 ? '머리 좀 정리해 주세요… 😵' : '머리 정리해 줄 거예요? ✨'}" data-tip="${kbdTip('합치고 줄이고 정리하기', 'O')}"><span class="ai">✨</span><span class="al">뇌 최적화</span><span class="as">합치고 줄이고 정리하기</span>${d.capacity > 1 ? '<span class="badge-n">!</span>' : ''}<span class="kbd">O</span></button>
      ${isProj ? `<button class="act lav" id="aPersona" data-say="저는 어떤 성격이 될까요? 🎭" data-tip="${kbdTip('일하는 방식 정하기', 'P')}"><span class="ai">${ps ? breedIcon(ps.breed) : '🎭'}</span><span class="al">성격</span><span class="as">${ps ? esc((ps.name || '성격 있음') + (ps.enabled === false ? ' (꺼짐)' : '')) : '일하는 방식 정해 주기'}</span><span class="kbd">P</span></button>` : ''}
      <button class="act mint" id="aMem" data-say="제 기억 구경할래요? 📚" data-tip="${kbdTip('기억 들여다보기', 'M')}"><span class="ai">📚</span><span class="al">기억장</span><span class="as">${d.count}개 들여다보기</span><span class="kbd">M</span></button>
    </div>
    <button class="ask-btn" id="aAsk" data-say="궁금한 거 있어요? 물어보세요 💬" data-tip="${kbdTip('기억에 대해 물어보기', 'C')}">${pet('happy', st.key === 'egg' ? 'baby' : st.key)}
      <span><span class="al">${esc(layerName(layer))}한테 물어보기</span><span class="as">기억하는 걸 대화로 알려 줘요</span></span><span class="kbd">C</span></button>
    ${kinds.length ? `<div class="h2">기억 종류</div>
      <div class="kinds">${kinds.map((k) => `<i style="flex:${d.regions[k]};background:${REGION[k].c}" data-tip="${esc(REGION[k].n)} ${d.regions[k]}개"></i>`).join('')}</div>
      <div class="legend">${kinds.map((k) => `<span><i style="background:${REGION[k].c}"></i>${REGION[k].n} ${d.regions[k]}</span>`).join('')}</div>` : ''}
    <div class="h2">최근에 배운 것 <small>${d.migrated ? `옮겨 온 기억 ${d.migrated}개 빼고` : ''}</small></div>
    <div class="list" id="recent">${(d.recent || []).slice(0, 5).map(memRow).join('') || '<div class="empty"><span class="big">🌱</span>아직 새로 배운 게 없어요</div>'}</div>`;
  bindMemRows($('#recent'));
  $('#petWrap').addEventListener('click', petTap);
  $('#weightBtn').addEventListener('click', () => optimizeSheet());
  $('#aOpt').addEventListener('click', () => optimizeSheet());
  $('#aMem').addEventListener('click', () => memorySheet());
  $('#aAsk').addEventListener('click', () => chatSheet());
  loadTray(layer);
  if (isProj) {
    $('#aFeed').addEventListener('click', () => feedSheet(slug));
    $('#aPersona').addEventListener('click', () => personaSheet(slug));
  }
  // 버튼에 올리면 뇌가 반응한다
  $$('[data-say]').forEach((b) => {
    b.addEventListener('pointerenter', () => sayTemp(b.dataset.say, 0));
    b.addEventListener('focus', () => { if (phone.classList.contains('kbd-mode')) sayTemp(b.dataset.say, 0); });
    b.addEventListener('pointerleave', () => sayRestore(700));
    b.addEventListener('blur', () => sayRestore(700));
  });
  updateEyes();
  if (d.count) loadTopics(layer, false); else $('#aiChip').hidden = true;
  if (openWhat) {
    await wait(380);
    if (!alive()) return;
    if (openWhat === 'opt') optimizeSheet();
    else if (openWhat === 'feed' && isProj) feedSheet(slug);
    else if (openWhat === 'persona' && isProj) personaSheet(slug);
    else if (openWhat === 'mem') memorySheet();
  }
}

async function loadTopics(layer, force) {
  clearTimeout(topicTimer);
  let t;
  try { t = await api('/api/topics?l=' + encodeURIComponent(layer) + (force ? '&force=1' : '')); } catch (e) { return; }
  if (!CUR || CUR.layer !== layer || !$('#stage')) return;
  const changed = !TOP || JSON.stringify(TOP.topics) !== JSON.stringify(t.topics) || TOP.motto !== t.motto || TOP.source !== t.source;
  TOP = t;
  const chip = $('#aiChip');
  if (t.status === 'running') {
    chip.innerHTML = '<span class="shimmer">단어 고르는 중…</span>';
    chip.dataset.tip = 'Haiku 가 기억을 읽고 이 뇌가 중시하는 주제를 고르고 있어요';
    chip.disabled = true;
  } else {
    chip.disabled = false;
    if (t.source === 'ai') { chip.innerHTML = '🔄 새로 고르기'; chip.dataset.tip = `${esc(fmtAgo(t.generated))}에 고른 단어예요. 누르면 Haiku 가 다시 골라요 (몇십 원)`; }
    else if (t.error) { chip.innerHTML = '⚠️ 다시 시도'; chip.dataset.tip = esc('단어를 고르지 못했어요: ' + t.error.slice(0, 120)); }
    else { chip.innerHTML = '💭 추정 단어'; chip.dataset.tip = '아직 AI 가 고른 단어가 없어 색인 이름으로 추정했어요. 누르면 새로 골라요'; }
  }
  chip.onclick = t.status === 'running' ? null : () => { chip.disabled = true; loadTopics(layer, true); };
  if (changed) {
    drawBubbles(t, true);
    if (!coachDone() && t.topics.length) { SAY_DEFAULT = '👆 말풍선을 누르면 그 기억을 모아 봐요'; say(SAY_DEFAULT); }
    else if (t.motto) { SAY_DEFAULT = t.motto; say(t.motto); }
  }
  if (t.status === 'running') topicTimer = setTimeout(() => loadTopics(layer, false), 3000);
}

function drawBubbles(t, animate) {
  const stage = $('#stage');
  if (!stage) return;
  $$('.bubble', stage).forEach((b) => b.remove());
  stage.classList.remove('focusing');
  const items = (t.topics || []).slice(0, 8);
  if (!items.length) return;
  const max = Math.max(...items.map((x) => x.count));
  const els = items.map((x, i) => {
    const b = document.createElement('button');
    b.className = 'bubble' + (t.source === 'ai' ? '' : ' ghost');
    b.style.setProperty('--fs', (13 + 4 * (x.count / max)).toFixed(1) + 'px');
    b.style.setProperty('--dur', (3.2 + (i % 3) * 0.6) + 's');
    b.style.setProperty('--dl', (i * 0.25) + 's');
    b.dataset.tip = `기억 ${x.count}개${x.used ? `, 떠오른 횟수 ${x.used}` : ''}<br>눌러서 모아 보기`;
    b.innerHTML = `<span>${esc(x.emoji)}</span><span>${esc(x.label)}</span><span class="n">${x.count}</span>`;
    b.addEventListener('click', () => {
      if (!coachDone()) { try { localStorage.setItem('brainCoach', '1'); } catch (e) { /* 다음에도 안내한다 */ } SAY_DEFAULT = (TOP && TOP.motto) || CUR.mood.why; }
      memorySheet({ topic: x });
    });
    const on = () => { stage.classList.add('focusing'); b.classList.add('hot'); sayTemp(`${x.label} 기억이 ${x.count}개 있어요`, 0); };
    const off = () => { b.classList.remove('hot'); if (!$('.bubble.hot', stage)) stage.classList.remove('focusing'); sayRestore(900); };
    b.addEventListener('pointerenter', on); b.addEventListener('pointerleave', off);
    b.addEventListener('focus', on); b.addEventListener('blur', off);
    stage.appendChild(b);
    return b;
  });
  // 뇌 둘레의 타원에 고르게 놓고, 겹치면 밀어낸다
  const W = stage.clientWidth, H = stage.clientHeight;
  const cx = W / 2, cy = H * 0.52, rx = W * 0.34, ry = H * 0.37;
  const n = els.length;
  const R = els.map((b, i) => {
    const a = (-90 + (360 / n) * i + (n % 2 ? 0 : 180 / n)) * Math.PI / 180;
    const w = b.offsetWidth, h = b.offsetHeight;
    return { b, w, h, x: cx + rx * Math.cos(a) - w / 2, y: cy + ry * Math.sin(a) - h / 2 };
  });
  const clamp = (r) => { r.x = Math.max(8, Math.min(W - r.w - 8, r.x)); r.y = Math.max(48, Math.min(H - r.h - 64, r.y)); };
  R.forEach(clamp);
  for (let it = 0; it < 60; it++) {
    let moved = false;
    for (let i = 0; i < R.length; i++) for (let j = i + 1; j < R.length; j++) {
      const a = R[i], c = R[j];
      const ox = Math.min(a.x + a.w, c.x + c.w) - Math.max(a.x, c.x) + 6;
      const oy = Math.min(a.y + a.h, c.y + c.h) - Math.max(a.y, c.y) + 6;
      if (ox > 0 && oy > 0) {
        moved = true;
        if (oy < ox) { const s = (a.y < c.y ? -1 : 1) * oy / 2; a.y += s; c.y -= s; } else { const s = (a.x < c.x ? -1 : 1) * ox / 2; a.x += s; c.x -= s; }
        clamp(a); clamp(c);
      }
    }
    if (!moved) break;
  }
  R.forEach((r, i) => {
    const bx = r.x + r.w / 2, by = r.y + r.h / 2;
    const dx = cx - bx, dy = cy - by;
    let tail;
    if (Math.abs(dy) > Math.abs(dx) * 0.55) tail = dy > 0 ? 'tail-down' : 'tail-up';
    else tail = dx > 0 ? 'tail-right' : 'tail-left';
    r.b.classList.add(tail);
    if (tail === 'tail-down' || tail === 'tail-up') r.b.style.setProperty('--tx', Math.max(16, Math.min(r.w - 16, cx - r.x)) + 'px');
    r.b.style.left = r.x + 'px'; r.b.style.top = r.y + 'px';
    if (animate) setTimeout(() => r.b.classList.add('on'), 80 + i * 70); else r.b.classList.add('on');
  });
}

function coachDone() { try { return localStorage.getItem('brainCoach') === '1'; } catch (e) { return true; } }
function say(text) {
  const s = $('#say');
  if (!s || s.textContent === text) return;
  s.style.animation = 'none'; void s.offsetWidth; s.style.animation = '';
  s.textContent = text;
}
function sayTemp(text, hold = 2600) {
  clearTimeout(sayTimer);
  say(text);
  if (hold) sayTimer = setTimeout(() => say(SAY_DEFAULT), hold);
}
function sayRestore(ms) { clearTimeout(sayTimer); sayTimer = setTimeout(() => say(SAY_DEFAULT), ms); }
function burst(emojis) {
  const h = $('#hearts');
  const st = $('#stage');
  if (!h || !st) return;
  const cx = st.clientWidth / 2, cy = st.clientHeight * 0.48;
  for (let i = 0; i < 9; i++) {
    const s = document.createElement('span');
    s.textContent = emojis[i % emojis.length];
    s.style.left = (cx - 11 + (Math.random() * 40 - 20)) + 'px';
    s.style.top = cy + 'px';
    s.style.setProperty('--hx', (Math.random() * 120 - 60).toFixed(0) + 'px');
    s.style.animationDelay = (i * 70) + 'ms';
    h.appendChild(s);
    setTimeout(() => s.remove(), 1900);
  }
}
function jump() {
  const w = $('#petWrap');
  if (!w) return;
  w.classList.remove('jump'); void w.offsetWidth; w.classList.add('jump');
}
let tapN = 0;
function petTap() {
  jump();
  const d = CUR;
  if (!d) return;
  const top = TOP && TOP.topics && TOP.topics[0];
  const lines = [
    `기억 ${d.count}개가 들어 있어요!`,
    d.learned_week ? `이번 주에 ${d.learned_week}개 배웠어요` : '요즘은 조용해요',
    top ? `${top.label} 얘기가 제일 많아요` : null,
    '헤헤 간지러워요',
    d.capacity > 1 ? '머리가 무거워요… 최적화해 주세요' : '머리가 가벼워요 ✨',
    TOP && TOP.motto,
  ].filter(Boolean);
  sayTemp(lines[tapN++ % lines.length]);
  if (Math.random() < 0.4) burst(['💕', '✨', '💗']);
}

function memRow(m) {
  const r = REGION[m.region] || REGION.other;
  return `<button class="mem" data-path="${esc(m.path)}" data-tip="${esc(r.n)}">
    <span class="em" style="background:color-mix(in srgb, ${r.c} 22%, transparent)">${r.e}</span>
    <span style="min-width:0"><span class="tt">${esc(m.title)}</span>
    <span class="mt" style="display:block">${esc(m.migrated ? '옮겨 온 기억' : fmtAgo(m.mtime))}${m.used ? `, 떠올림 ${m.used}번` : ''}</span></span></button>`;
}
function bindMemRows(root) { $$('.mem', root).forEach((el) => el.addEventListener('click', () => memoryDetail(el.dataset.path))); }

// ---------------------------------------------------------------- 시트: 먹이
function feedSheet(slug) {
  const examples = ['배포는 꼭 release 스크립트로만 한다', '이 폴더 코드는 원본 구조를 그대로 따른다', '테스트는 실기기에서 다시 확인한다'];
  openSheet({
    title: '<span>🍙</span><span>먹이 주기</span>',
    body: (el) => {
      el.innerHTML = `<p class="sub" style="margin-bottom:10px">꼭 기억했으면 하는 것을 알려 주세요. 해마가 근거를 붙여서 알맞은 자리에 새겨요.</p>
        <textarea id="feedText" placeholder="무엇을, 왜 기억해야 하는지 적어 주세요" maxlength="2000"></textarea>
        <div class="examples">${examples.map((x) => `<button data-tip="눌러서 채우기">💡 ${esc(x)}</button>`).join('')}</div>`;
      $$('.examples button', el).forEach((b) => b.addEventListener('click', () => { const t = $('#feedText', el); t.value = b.textContent.replace(/^💡 /, ''); t.focus(); }));
    },
    foot: (el, sh) => {
      el.innerHTML = `<button class="btn block" id="feedGo" data-tip="${kbdTip('먹이기', '⌘ Enter')}">🍙 냠냠 먹이기</button>`;
      const go = async () => {
        const btn = $('#feedGo', el);
        const text = $('#feedText', sh.el).value.trim();
        if (!text) { toast('먹일 내용을 적어 주세요'); $('#feedText', sh.el).focus(); return; }
        if (btn.disabled) return;
        btn.disabled = true;
        try {
          const r = await api('/api/feed', { slug, text });
          if (!r.ok) throw new Error(r.out || '실패');
          closeSheet(sh, true);
          await wait(250);
          jump(); burst(['🍙', '💕', '😋']); sayTemp('냠냠! 해마가 곧 새겨 둘게요', 3200);
          toast('🍙 먹이를 줬어요. 몇 분 안에 기억이 돼요');
        } catch (e) { toast(e.message); btn.disabled = false; }
      };
      $('#feedGo', el).addEventListener('click', go);
      sh.submit = go;
    },
  });
}

// ---------------------------------------------------------------- 시트: 최적화
function gaugeSvg(r) {
  const v = Math.min(1.5, r) / 1.5;
  const a = Math.PI * (1 - v);
  const x = 110 + 90 * Math.cos(a), y = 120 - 90 * Math.sin(a);
  const col = r > 1 ? 'var(--bad)' : r > 0.85 ? 'var(--lemon)' : 'var(--mint)';
  const t = Math.PI * (1 - 1 / 1.5);
  return `<svg viewBox="0 0 220 130"><path d="M20 120 A90 90 0 0 1 200 120" fill="none" stroke="var(--bg2)" stroke-width="20" stroke-linecap="round"/>
    ${v > 0.001 ? `<path d="M20 120 A90 90 0 0 1 ${x.toFixed(1)} ${y.toFixed(1)}" fill="none" stroke="${col}" stroke-width="20" stroke-linecap="round"/>` : ''}
    <line x1="${(110 + 76 * Math.cos(t)).toFixed(1)}" y1="${(120 - 76 * Math.sin(t)).toFixed(1)}" x2="${(110 + 104 * Math.cos(t)).toFixed(1)}" y2="${(120 - 104 * Math.sin(t)).toFixed(1)}" stroke="var(--ink3)" stroke-width="2" stroke-dasharray="3 3"/></svg>`;
}
function prettyIdx(f) {
  if (f === 'INDEX.md') return '프로젝트 지도';
  return f.replace(/\.md(#\d+)?$/, '').replace(/^lessons-index-?/, '').replace(/^\(미등록\)#?\d*$/, '색인 없는 기억').replace(/-/g, ' ') || '교훈 목록';
}
function optimizeSheet() {
  const d = CUR;
  if (!d) return;
  let mode = d.capacity > 1 ? 'over' : 'all';
  let plan = null;
  let seq = 0;
  const sh = openSheet({
    title: '<span>✨</span><span>뇌 최적화</span>',
    body: (el) => {
      const parts = (d.capacity_parts || []).slice(0, 5).map((p) => {
        const r = Math.max(p.ratio, p.item_ratio);
        return `<div class="part" data-tip="${esc(`${p.chars.toLocaleString()} / ${p.cap.toLocaleString()}자, 항목 ${p.items}개`)}"><div class="pn"><span>${esc(prettyIdx(p.file))}</span><span>${pct(r)}</span></div><div class="bar ${barCls(r)}"><i style="width:${Math.min(100, r * 100)}%"></i></div></div>`;
      }).join('');
      el.innerHTML = `
        <div class="gauge-big">${gaugeSvg(d.capacity)}<div class="gv">${pct(d.capacity)}</div>
          <div class="gl">${d.capacity > 1 ? '머리가 꽉 찼어요 😵' : d.capacity > 0.85 ? '조금 무거워요 😋' : '가벼워요 😆'}</div></div>
        <p class="sub center" style="margin:6px 0 14px">해마가 기억을 다시 읽고 겹친 건 합치고, 긴 색인은 줄이고, 낡은 건 보관해요. 지우지는 않아요.</p>
        <div style="margin-top:4px"><div class="seg" id="optSeg"><button data-m="over" data-tip="꽉 찬 곳만 골라서 정리해요">🎯 꽉 찬 곳만</button><button data-m="all" data-tip="이 뇌 전체를 한 바퀴 정리해요">🧹 전체 대청소</button></div></div>
        <div class="box" id="optPlan" style="margin-top:10px"><p class="hint">계산 중…</p></div>
        <details class="more" style="margin-top:12px"><summary>어디가 무거운지 보기</summary>
          <div class="box" style="margin-top:6px">${parts || '<p class="hint">기억 목록이 없어요</p>'}
          <p class="hint" style="margin:10px 0 0">100% 를 넘으면 Claude 가 기억을 떠올리기 어려워져요</p></div></details>`;
      $$('#optSeg button', el).forEach((b) => b.addEventListener('click', () => { if (mode !== b.dataset.m) { mode = b.dataset.m; dry(); } }));
    },
    foot: (el) => {
      el.innerHTML = '<button class="btn lemon block" id="optGo" disabled>✨ 최적화 시작</button>';
      $('#optGo', el).addEventListener('click', go);
    },
  });
  sh.submit = () => { const b = $('#optGo', sh.el); if (b && !b.disabled) go(); };
  async function dry() {
    const my = ++seq;
    $$('#optSeg button', sh.el).forEach((b) => b.classList.toggle('on', b.dataset.m === mode));
    const box = $('#optPlan', sh.el);
    const btn = $('#optGo', sh.el);
    box.innerHTML = '<p class="hint">계산 중…</p>';
    if (btn) btn.disabled = true;
    try {
      const p = await api('/api/tidy', { layer: d.layer, mode, dry: true });
      if (my !== seq || !sh.el.isConnected) return;
      plan = p;
      if (!p.count) {
        box.innerHTML = `<div class="center" style="padding:6px 0"><span style="font-size:30px">🫧</span><br><b>${mode === 'over' ? '꽉 찬 곳이 없어요!' : '정리할 게 없어요'}</b>${mode === 'over' ? '<p class="hint" style="margin:4px 0 0">그래도 정리하고 싶으면 전체 대청소를 골라요</p>' : ''}</div>`;
        return;
      }
      box.innerHTML = `<b style="font-size:15px">🧹 해마가 ${p.count}번 나눠서 정리해요</b>
        <p class="hint" style="margin:4px 0 0">보통 몇 분 걸려요. 그동안에도 Claude 는 그대로 쓸 수 있어요</p>
        <details class="more" style="margin-top:6px"><summary style="font-size:12.5px">자세히</summary>
          ${p.slices.map((s) => `<div style="display:flex;justify-content:space-between;gap:8px;font-size:12.5px;color:var(--ink2)"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(prettyIdx(s.id.split(':')[1] || s.id))}</span><span style="flex:none">${kTok(s.tok)} 토큰</span></div>`).join('')}
          <p class="hint" style="margin:6px 0 0">해마 입력 합계 약 ${kTok(p.tok)} 토큰</p></details>`;
      if (btn) btn.disabled = false;
    } catch (e) { if (my === seq) box.innerHTML = `<div class="out">${esc(e.message)}</div>`; }
  }
  async function go() {
    const btn = $('#optGo', sh.el);
    if (!btn || btn.disabled || !plan || !plan.count) return;
    btn.disabled = true;
    try {
      const g = await api('/api/tidy', { layer: d.layer, mode, dry: false });
      sh.sb.innerHTML = `<div class="center" style="padding:30px 0"><div class="sweep">🧹</div>
        <div class="jua" style="font-size:22px;margin-top:8px">해마에게 맡겼어요!</div>
        <p class="sub">조각 ${g.count}개를 차례로 정리해요. 해마 일지에서 진행을 볼 수 있어요.</p></div>`;
      btn.outerHTML = '<a class="btn soft block" href="#/journal">📓 해마 일지 보기</a>';
      sh.submit = null;
      SAY_DEFAULT = '🧹 머리 정리 중이에요…';
      say(SAY_DEFAULT);
    } catch (e) { toast(e.message); btn.disabled = false; }
  }
  dry();
}

// ---------------------------------------------------------------- 시트: 기억장
function memorySheet(opt = {}) {
  const d = CUR;
  if (!d) return;
  const f = { topic: opt.topic || null, region: '', q: '' };
  const topics = (TOP && TOP.topics) || [];
  const PAGE = 120;
  let shown = PAGE;
  openSheet({
    title: `<span>📚</span><span>기억장</span><span class="hint" style="font-family:'Pretendard Variable';font-size:13px">${d.count}개</span>`,
    full: true,
    kind: 'memory',
    body: (el) => {
      el.innerHTML = `<input class="input" id="memQ" placeholder="🔍 기억 찾기 (/)" ${opt.topic ? '' : 'data-autofocus'}>
        <div class="chips" id="memChips" style="margin-top:10px"></div>
        <div class="hint" id="memCount" style="margin:0 2px 8px"></div>
        <div class="list" id="memList"></div>
        <button class="btn soft small more-btn" id="memMore" hidden>더 보기</button>
        ${d.dormant_list && d.dormant_list.length ? `<details class="more" style="margin-top:16px"><summary>💤 잠든 기억 ${d.dormant_list.length}개</summary>
          <p class="hint">오래 안 쓴 기억은 지우지 않고 재워 둬요. 다시 쓰이면 깨어나요.</p>
          <div class="list">${d.dormant_list.map((x) => `<button class="mem" data-path="${esc(x.path)}"><span class="em" style="background:var(--bg2)">💤</span><span><span class="tt">${esc(x.line.replace(/\[([^\]]*)\]\([^)]*\)/g, '$1'))}</span><span class="mt" style="display:block">${esc(x.since)}부터</span></span></button>`).join('')}</div></details>` : ''}`;
      const chips = () => {
        const all = [{ label: '전체', on: !f.topic && !f.region }]
          .concat(topics.map((t) => ({ label: t.emoji + ' ' + t.label, on: !!(f.topic && f.topic.label === t.label), t })))
          .concat(REGION_ORDER.filter((k) => d.regions[k]).map((k) => ({ label: REGION[k].e + ' ' + REGION[k].n, on: f.region === k, r: k })));
        $('#memChips', el).innerHTML = all.map((c) => `<button class="chip${c.on ? ' on' : ''}" aria-pressed="${c.on}">${esc(c.label)}</button>`).join('');
        $$('#memChips .chip', el).forEach((b, i) => b.addEventListener('click', () => {
          const c = all[i];
          f.topic = c.t || null; f.region = c.r || ''; shown = PAGE;
          chips(); draw();
          const nb = $$('#memChips .chip', el)[i];
          if (nb) nb.focus({ preventScroll: true });
        }));
        const on = $('#memChips .chip.on', el), row = $('#memChips', el);
        if (on) row.scrollLeft = on.offsetLeft - row.clientWidth / 2 + on.offsetWidth / 2;   // scrollIntoView 는 폰 틀까지 스크롤한다
      };
      const draw = () => {
        const q = f.q.trim().toLowerCase().split(/\s+/).filter(Boolean);
        const inTopic = f.topic ? new Set(f.topic.paths) : null;
        const list = d.memories.filter((m) => (!inTopic || inTopic.has(m.path)) && (!f.region || m.region === f.region) &&
          q.every((t) => (m.title + ' ' + m.line + ' ' + m.path).toLowerCase().includes(t)));
        $('#memCount', el).textContent = `${list.length}개`;
        $('#memList', el).innerHTML = list.slice(0, shown).map(memRow).join('') || '<div class="empty"><span class="big">🫥</span>맞는 기억이 없어요</div>';
        bindMemRows($('#memList', el));
        const more = $('#memMore', el);
        more.hidden = list.length <= shown;
        more.textContent = `더 보기 (${list.length - shown}개 남음)`;
      };
      $('#memMore', el).addEventListener('click', () => { shown += PAGE; draw(); });
      $('#memQ', el).addEventListener('input', (e) => { f.q = e.target.value; shown = PAGE; draw(); });
      chips(); draw();
      bindMemRows($('details.more', el) || document.createElement('div'));
    },
  });
}

// 쉬운 말 풀이 - 기본 켬, 설정에서 끈다
let EXPLAIN_ON = true;
try { EXPLAIN_ON = localStorage.getItem('brainExplain') !== 'off'; } catch (e) { EXPLAIN_ON = true; }
const FB = { confirm: { e: '👍', n: '맞아요' }, outdated: { e: '✏️', n: '달라졌어요' }, important: { e: '⭐', n: '중요해요' }, forget: { e: '🗑', n: '필요 없어요' } };
const SKEL = '<div class="skel big"></div><div class="skel"></div><div class="skel half"></div><div class="skel"></div><p class="hint shimmer" style="margin:8px 0 0">쉬운 말로 바꾸는 중…</p>';

function memoryDetail(path) {
  const mem = CUR && CUR.memories.find((m) => m.path === path);
  const title = mem ? mem.title : path.split('/').pop().replace(/\.md$/, '');
  openSheet({
    title: '<span>📖</span><span>기억 한 장</span>',
    full: true,
    kind: 'detail',
    body: async (el, sh) => {
      el.innerHTML = `<div class="plain" id="plain">${EXPLAIN_ON ? SKEL : ''}</div>
        <div class="fb" id="fb"></div>
        <details class="more" id="orig" style="margin-top:14px"><summary>📜 AI 가 저장한 원문</summary><div id="origBody" style="margin-top:6px"><p class="hint">불러오는 중…</p></div></details>`;
      let check = '';
      const fbBox = $('#fb', el);
      renderFb(fbBox, sh, path, title, check);
      const plain = $('#plain', el);
      const showPlain = (x) => {
        check = x.check || '';
        plain.innerHTML = `<div class="ps">${esc(x.summary || title)}</div>
          ${x.why ? `<div class="pr"><span class="pi" style="background:var(--lemon-l)">💡</span><div><b>왜 기억해요</b><p>${esc(x.why)}</p></div></div>` : ''}
          ${x.when ? `<div class="pr"><span class="pi" style="background:var(--sky-l)">⏰</span><div><b>언제 떠올려요</b><p>${esc(x.when)}</p></div></div>` : ''}
          ${(x.terms || []).length ? `<div class="terms">${x.terms.map((t) => `<span class="term">${esc(t.word)}<small>${esc(t.meaning)}</small></span>`).join('')}</div>` : ''}`;
        renderFb(fbBox, sh, path, title, check);
      };
      const doExplain = async () => {
        plain.innerHTML = SKEL;
        try { const x = await api('/api/explain?p=' + encodeURIComponent(path)); if (el.isConnected) showPlain(x); }
        catch (e) { if (!el.isConnected) return; plain.innerHTML = `<div class="ps">${esc(title)}</div><p class="hint" style="margin:0">쉬운 말로 풀지 못했어요. 아래 원문을 봐 주세요 (${esc(e.message.slice(0, 80))})</p>`; $('#orig', el).open = true; }
      };
      if (EXPLAIN_ON) doExplain();
      else {
        plain.innerHTML = `<div class="ps">${esc(title)}</div><button class="btn sky small" id="doExp">✨ 쉬운 말로 풀기</button>`;
        $('#doExp', el).addEventListener('click', doExplain);
        $('#orig', el).open = true;
      }
      try {
        const m = await api('/api/memory?p=' + encodeURIComponent(path));
        if (!el.isConnected) return;
        const s = m.strength || {};
        $('#origBody', el).innerHTML = `<p class="hint" style="margin:0 0 6px;word-break:break-all">${esc(m.path)}</p>
          <div class="chips"><span class="chip" data-tip="마지막으로 고친 때">✏️ ${fmtAgo(m.mtime)}</span><span class="chip" data-tip="세션에 저절로 떠오른 횟수">💭 ${s.shown || 0}</span><span class="chip" data-tip="세션이 직접 열어 본 횟수">👀 ${s.opened || 0}</span><span class="chip" data-tip="검색에 걸린 횟수">🔍 ${s.grepped || 0}</span></div>
          <article class="md box">${md(m.text, m.path.split('/').slice(0, -1).join('/'))}</article>`;
        $$('[data-mem]', el).forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); memoryDetail(a.dataset.mem); }));
      } catch (e) { $('#origBody', el).innerHTML = `<div class="out">${esc(e.message)}</div>`; }
    },
  });
}

function renderFb(box, sh, path, title, check) {
  const cur = TRAY.items.find((x) => x.path === path);
  const on = (k) => (cur && cur.kind === k ? ' on' : '');
  box.innerHTML = `<div class="fq">🤔 ${esc(check || '이 기억, 지금도 맞나요?')}</div>
    <div class="fb-row"><button class="fbb${on('confirm')}" data-k="confirm">👍 네, 맞아요</button><button class="fbb${on('outdated')}" data-k="outdated">✏️ 달라졌어요</button></div>
    <div class="fb-row"><button class="fbb sm${on('important')}" data-k="important">⭐ 중요해요</button><button class="fbb sm${on('forget')}" data-k="forget">🗑 이제 필요 없어요</button></div>
    <div class="fb-text" hidden><textarea placeholder="지금은 어떻게 됐나요? 예: 이제 배포는 GitHub Actions 가 해요" maxlength="1500">${cur && cur.kind === 'outdated' ? esc(cur.text) : ''}</textarea>
      <button class="btn small lav fb-put" style="margin-top:8px" data-tip="${kbdTip('우체통에 넣기', '⌘ Enter')}">📮 우체통에 넣기</button></div>
    ${cur ? `<div class="fb-state">📮 우체통에 있어요: ${FB[cur.kind].e} ${FB[cur.kind].n} <button class="fb-rm">빼기</button></div>`
      : '<p class="hint" style="margin:10px 2px 0">누르면 📮 우체통에 모였다가, 한 번에 해마에게 가요</p>'}`;
  const put = async (kind, text) => {
    try {
      const r = await api('/api/feedback/add', { layer: CUR.layer, path, title, kind, text: text || '' });
      TRAY.items = r.items;
      updateTrayBar(true);
      toast(`📮 우체통에 넣었어요 (${r.items.length}개)`);
      renderFb(box, sh, path, title, check);
    } catch (e) { toast(e.message); }
  };
  $$('.fbb', box).forEach((b) => b.addEventListener('click', () => {
    const k = b.dataset.k;
    if (k === 'outdated') {
      const tx = $('.fb-text', box);
      tx.hidden = false;
      $('textarea', tx).focus({ preventScroll: true });
      sh.submit = () => $('.fb-put', box).click();
      return;
    }
    put(k);
  }));
  $('.fb-put', box).addEventListener('click', () => {
    const t = $('.fb-text textarea', box).value.trim();
    if (!t) { toast('지금은 어떻게 됐는지 적어 주세요'); return; }
    put('outdated', t);
  });
  const rm = $('.fb-rm', box);
  if (rm) rm.addEventListener('click', async () => {
    try { TRAY.items = (await api('/api/feedback/remove', { layer: CUR.layer, id: cur.id })).items; updateTrayBar(false); renderFb(box, sh, path, title, check); }
    catch (e) { toast(e.message); }
  });
}

// ---------------------------------------------------------------- 우체통 (피드백을 모았다가 한 번에)
let TRAY = { layer: '', items: [] };
async function loadTray(layer) {
  try {
    const r = await api('/api/feedback?l=' + encodeURIComponent(layer));
    if (CUR && CUR.layer === layer) { TRAY = { layer, items: r.items }; updateTrayBar(false); }
  } catch (e) { /* 우체통은 없어도 된다 */ }
}
function updateTrayBar(bump) {
  const bar = $('#trayBar');
  const n = TRAY.items.length;
  const show = n > 0 && !!CUR && TRAY.layer === CUR.layer;
  bar.classList.toggle('on', show);
  bar.inert = !show;
  screen.classList.toggle('has-tray', show);
  if (show) {
    $('.tb-t', bar).textContent = `피드백 ${n}개 모였어요`;
    if (bump) { bar.classList.remove('bump'); void bar.offsetWidth; bar.classList.add('bump'); }
  }
}
$('#trayBar').addEventListener('click', () => traySheet());
function traySheet() {
  const sh = openSheet({
    title: '<span>📮</span><span>우체통</span>',
    kind: 'tray',
    body: (el) => {
      const draw = () => {
        el.innerHTML = `<p class="sub" style="margin-bottom:10px">모아서 한 번에 보내면 해마가 한 번만 일해요. 몇 분 안에 기억에 반영돼요.</p>
          <div class="list">${TRAY.items.map((x) => `<div class="tray-item"><span class="ti-k">${FB[x.kind].e}</span>
            <span style="min-width:0"><span class="ti-t">${esc(x.title || x.path)}</span><br><span class="ti-d">${esc(FB[x.kind].n)}${x.text ? ': ' + esc(x.text.slice(0, 60)) : ''}</span></span>
            <button class="x" data-id="${x.id}" aria-label="빼기" data-tip="빼기">✕</button></div>`).join('') || '<div class="empty"><span class="big">📭</span>우체통이 비었어요</div>'}</div>`;
        $$('.x[data-id]', el).forEach((b) => b.addEventListener('click', async () => {
          try { TRAY.items = (await api('/api/feedback/remove', { layer: CUR.layer, id: b.dataset.id })).items; updateTrayBar(false); draw(); if (!TRAY.items.length) closeSheet(sh, true); }
          catch (e) { toast(e.message); }
        }));
      };
      draw();
    },
    foot: (el) => {
      el.innerHTML = `<button class="btn block" id="traySend" data-tip="${kbdTip('보내기', '⌘ Enter')}">📮 해마에게 한 번에 보내기</button>`;
      $('#traySend', el).addEventListener('click', send);
    },
  });
  sh.submit = send;
  async function send() {
    const b = $('#traySend', sh.el);
    if (!b || b.disabled || !TRAY.items.length) return;
    b.disabled = true;
    try {
      const r = await api('/api/feedback/send', { layer: CUR.layer });
      if (!r.ok) throw new Error(r.out || '보내지 못했어요');
      TRAY.items = [];
      updateTrayBar(false);
      closeSheet(sh, true);
      await wait(250);
      jump(); burst(['📮', '💌', '✨']); sayTemp('피드백 고마워요! 해마가 곧 고칠게요', 3200);
      toast(`💌 피드백 ${r.count}개를 해마에게 보냈어요`);
    } catch (e) { toast(e.message); b.disabled = false; }
  }
}

// ---------------------------------------------------------------- 시트: 물어보기 (뇌와 대화)
const CHATS = {};
function chatSheet() {
  const d = CUR;
  if (!d) return;
  const name = layerName(d.layer);
  const hist = CHATS[d.layer] || (CHATS[d.layer] = []);
  let busy = false;
  const av = () => `<span class="av">${pet('happy', d.stage.key === 'egg' ? 'baby' : d.stage.key)}</span>`;
  const sh = openSheet({
    title: `<span>💬</span><span>${esc(name)}한테 물어보기</span>`,
    full: true,
    kind: 'chat',
    body: (el) => { el.innerHTML = '<div class="chat" id="chat"></div>'; },
    foot: (el) => {
      el.innerHTML = `<div class="chat-in"><textarea id="chatIn" rows="1" placeholder="기억에 대해 물어보세요" maxlength="500" data-autofocus></textarea>
        <button class="send" id="chatGo" aria-label="보내기" data-tip="${kbdTip('보내기', 'Enter')}">➤</button></div>
        <p class="hint" style="margin:6px 4px 0">이 뇌의 기억 안에서만 답해요. Shift+Enter 는 줄바꿈</p>`;
      const ta = $('#chatIn', el);
      ta.addEventListener('input', () => { ta.style.height = 'auto'; ta.style.height = Math.min(120, ta.scrollHeight) + 'px'; });
      ta.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) { e.preventDefault(); send(ta.value); }
      });
      $('#chatGo', el).addEventListener('click', () => send(ta.value));
    },
  });
  sh.submit = () => send($('#chatIn', sh.el).value);
  const topics = ((TOP && TOP.topics) || []).slice(0, 3);
  const sugs = topics.map((t) => `${t.emoji} ${t.label} 알려 줘`).concat(['🌱 요즘 뭘 배웠어?', '⚠️ 제일 조심할 건 뭐야?']);
  function draw() {
    const chat = $('#chat', sh.el);
    if (!chat) return;
    let html = `<div class="msg">${av()}<div class="bb">안녕하세요! 저는 ${esc(name)}의 뇌예요 🧠\n제가 기억하는 걸 물어보세요.</div></div>`;
    if (!hist.length) html += `<div class="sugs">${sugs.map((x) => `<button>${esc(x)}</button>`).join('')}</div>`;
    hist.forEach((h) => {
      html += `<div class="msg me"><div class="bb">${esc(h.q)}</div></div>`;
      if (h.a != null) {
        html += `<div class="msg">${av()}<div class="bb">${esc(h.a)}${(h.refs || []).length ? `<div class="refs">${h.refs.map((r) => `<button data-path="${esc(r.path)}" data-tip="이 기억 열기">📖 ${esc(r.title)}</button>`).join('')}</div>` : ''}</div></div>`;
      }
    });
    if (busy) html += `<div class="msg">${av()}<div class="bb"><span class="typing"><i></i><i></i><i></i></span></div></div>`;
    chat.innerHTML = html;
    $$('.sugs button', chat).forEach((b) => b.addEventListener('click', () => send(b.textContent.replace(/^\S+\s/, ''))));
    $$('.refs button', chat).forEach((b) => b.addEventListener('click', () => memoryDetail(b.dataset.path)));
    sh.sb.scrollTop = sh.sb.scrollHeight;
    updateEyes();
  }
  async function send(text) {
    const q = (text || '').trim();
    if (!q || busy) return;
    const ta = $('#chatIn', sh.el);
    ta.value = ''; ta.style.height = '';
    busy = true;
    const turn = { q, a: null, refs: [] };
    hist.push(turn);
    draw();
    try {
      const r = await api('/api/ask', { layer: d.layer, q, history: hist.filter((h) => h.a && !h.err).slice(-3).map((h) => ({ q: h.q, a: h.a })) });
      turn.a = r.answer; turn.refs = r.refs || [];
    } catch (e) { turn.a = '앗, 지금은 대답을 못 하겠어요 😢\n(' + e.message.slice(0, 100) + ')'; turn.err = true; }
    busy = false;
    if (sh.el.isConnected) { draw(); ta.focus(); }
  }
  draw();
}

// ---------------------------------------------------------------- 시트: 성격 (노드 에디터)
const BREED_ICON = { squirrel: '🐿️', owl: '🦉', cat: '🐱', turtle: '🐢' };
const breedIcon = (b) => BREED_ICON[b] || '🎭';
const LEVEL_TIP = ['살짝: 일을 시작할 때 한 번 알려 줘요', '보통: 요청할 때마다 다시 알려 줘요', '꼭!: 🔒 상황이면 진짜로 지키게 해요'];
const LEVEL_WORD = ['살짝', '보통', '꼭!'];
function friendlyHtml(eff, cat) {
  const order = Object.keys(cat.situations);
  const gates = new Set(cat.gates);
  const rows = order.filter((s) => eff && eff[s] && Object.keys(eff[s]).length).map((s) => {
    const sit = cat.situations[s];
    const items = Object.entries(eff[s]).sort((a, b) => b[1] - a[1]).map(([t, lv]) => {
      const tr = cat.traits[t];
      const lock = lv >= 3 && gates.has(t + '+' + s);
      return `<span class="fc${lock ? ' lock' : ''}">${tr.icon} ${esc(cat.special_short[t + '+' + s] || tr.short)}${lock ? ' 🔒' : ''}</span>`;
    }).join(' ');
    return `<div class="fl"><span class="fh">${sit.icon} ${s === 'normal' ? '평소엔' : esc(sit.short) + '엔'}</span>${items}</div>`;
  });
  return rows.join('');
}
const SIT_TIP = {
  normal: '늘 적용돼요',
  risky: '실행할 명령을 보고 알아차려요. 🔒 강제할 수 있어요',
  after_edit: '요청이 끝날 때 고친 파일과 검증 명령을 확인해요. 🔒 강제할 수 있어요',
  big_change: '한 요청에서 고친 파일 수를 세요. 🔒 강제할 수 있어요',
  ambiguous: 'Claude 가 스스로 판단해요. 강제는 못 해요',
  new_area: 'Claude 가 스스로 판단해요. 강제는 못 해요',
};
let P = null;
let previewTimer = 0;
let nid = 0;
const newId = (p) => p + Date.now().toString(36) + (nid++);

async function personaSheet(slug) {
  if (P) return;   // 이미 열려 있다
  let r;
  try { r = await api('/api/persona?slug=' + encodeURIComponent(slug)); } catch (e) { toast(e.message); return; }
  const g = r.graph || { version: 1, breed: '', name: '', enabled: true, nodes: [], edges: [], verify_re: '', big_files: 5 };
  P = { slug, graph: g, cat: r.catalog, compiled: r.compiled, dirty: false, saved: !!r.graph, picked: null, armed: false, focusId: null };
  ensureHub();
  const cat = P.cat;
  const sh = openSheet({
    title: '<span>🎭</span><span>성격</span>',
    full: true,
    kind: 'persona',
    beforeClose: () => {
      if (!P || !P.dirty || P.armed) return true;
      P.armed = true;
      toast('저장하지 않은 변경이 있어요. 한 번 더 닫으면 버려요', 3000);
      setTimeout(() => { if (P) P.armed = false; }, 3000);
      return false;
    },
    onClose: () => { if (P && P.dirty) toast('저장하지 않은 성격은 버렸어요'); P = null; },
    body: (el) => {
      el.innerHTML = `
        <p class="sub" style="margin-bottom:10px">Claude 가 이 프로젝트에서 <b>어떻게 일할지</b> 정해요. 마음에 드는 품종을 골라 보세요.</p>
        <div class="now" id="pNow"></div>
        <div class="breeds">${Object.entries(cat.breeds).map(([k, b]) => `<button class="breed${g.breed === k ? ' on' : ''}" data-b="${k}" data-tip="${esc(b.fit)}에 잘 맞아요">
          <span class="bi">${b.icon}</span><div class="bn">${esc(b.name)}</div><div class="bd">${esc(b.desc)}</div></button>`).join('')}</div>
        <details class="more custom" id="pCustom" ${!g.breed && g.nodes.some((n) => n.kind === 'trait') ? 'open' : ''}><summary>🛠 직접 꾸미기</summary>
        <div class="hint" style="margin:2px 2px 6px">성향을 누르고 상황을 누르면 이어져요 (분홍 점을 끌어도 돼요). 선을 누르면 끊겨요.<br>세기는 살짝, 보통, <b style="color:var(--bad)">꼭!</b> 🔒 상황에 꼭! 을 이으면 진짜로 지키게 해요.</div>
        <div class="canvas" id="canvas" aria-label="성향과 상황 연결도"><svg class="wires" id="wires"></svg></div>
        <div class="h2" style="margin-top:18px">성향 더하기 <small>같은 줄은 서로 반대예요</small></div>
        <div class="axes">${cat.axes.map((a) => `<div class="axis">
          ${[a.left, a.right].map((t, i) => `${i ? `<span class="vs">${esc(a.name)}</span>` : ''}<button data-add="trait" data-k="${t}" data-tip="${esc(cat.traits[t].firm)}">${cat.traits[t].icon} ${esc(cat.traits[t].name)}</button>`).join('')}</div>`).join('')}</div>
        <div class="h2">상황 더하기 <small>🔒 = 강제할 수 있어요</small></div>
        <div class="sits">${Object.entries(cat.situations).filter(([k]) => k !== 'normal').map(([k, s]) =>
          `<button data-add="situation" data-k="${k}" data-tip="${esc(SIT_TIP[k] || '')}">${s.icon} ${esc(s.name)}${s.forceable ? ' 🔒' : ''}</button>`).join('')}</div>
        <div class="h2">Claude 가 실제로 받는 말</div>
        <div id="pPreview"></div>
        <details class="more" style="margin-top:14px"><summary>세부 설정</summary>
          <div class="box" style="margin-top:6px">
            <div class="set"><div><div class="st">성격 켜기</div><div class="sd">끄면 아무것도 전해지지 않아요</div></div>
              <label class="switch"><input type="checkbox" id="pEnabled" ${g.enabled !== false ? 'checked' : ''}><span></span></label></div>
            <label class="field">이름<input class="input" id="pName" value="${esc(g.name || '')}" placeholder="예: 꼼꼼이" maxlength="40"></label>
            <label class="field">큰 변경으로 볼 파일 수 (2~50)<input class="input" id="pBig" type="number" min="2" max="50" value="${g.big_files || 5}"></label>
            <label class="field">검증 명령 패턴 (정규식)<input class="input" id="pVerify" value="${esc(g.verify_re || '')}" placeholder="비우면 기본: test, build, tsc, lint …"></label>
            ${P.saved ? '<button class="btn soft small" id="pDel" style="margin-top:12px;color:var(--bad)">성격 지우기</button>' : ''}
          </div></details>
        </details>`;
      $('#pCustom', el).addEventListener('toggle', () => { if ($('#pCustom', el).open) requestAnimationFrame(drawGraph); });
      $$('.breed', el).forEach((b) => b.addEventListener('click', () => loadBreed(b.dataset.b)));
      $$('[data-add]', el).forEach((b) => b.addEventListener('click', (e) => { e.stopPropagation(); addNode(b.dataset.add, b.dataset.k); }));
      $('#pEnabled', el).addEventListener('change', (e) => { P.graph.enabled = e.target.checked; changed(); });
      $('#pName', el).addEventListener('input', (e) => { P.graph.name = e.target.value; changed(); });
      $('#pBig', el).addEventListener('input', (e) => {
        const v = parseInt(e.target.value, 10);
        P.graph.big_files = v >= 2 && v <= 50 ? v : 5;
        e.target.style.borderColor = v >= 2 && v <= 50 ? '' : 'var(--bad)';
        changed();
      });
      $('#pVerify', el).addEventListener('input', (e) => {
        let ok = true;
        try { new RegExp(e.target.value); } catch (err) { ok = false; }
        e.target.style.borderColor = ok ? '' : 'var(--bad)';
        if (ok) { P.graph.verify_re = e.target.value; changed(); }
      });
      const del = $('#pDel', el);
      if (del) del.addEventListener('click', async () => {
        if (del.dataset.sure !== '1') { del.dataset.sure = '1'; del.textContent = '한 번 더 누르면 지워요'; setTimeout(() => { del.dataset.sure = ''; del.textContent = '성격 지우기'; }, 3000); return; }
        try { await api('/api/persona/delete', { slug }); P.dirty = false; closeSheet(sh, true); toast('성격을 지웠어요'); route(); } catch (e) { toast(e.message); }
      });
      // 빈 곳을 누르면 고른 성향이 풀린다
      el.addEventListener('click', (e) => { if (P && P.picked && !e.target.closest('.node, [data-add], .port')) { P.picked = null; drawGraph(); } });
    },
    foot: (el) => {
      el.innerHTML = `<button class="btn lav block" id="pSave" data-tip="${kbdTip('저장', '⌘ S')}">💾 이 성격으로 정하기</button>`;
      $('#pSave', el).addEventListener('click', save);
    },
  });
  async function save() {
    if (!P) return;
    const btn = $('#pSave', sh.el);
    if (btn.disabled) return;
    btn.disabled = true;
    try {
      const r2 = await api('/api/persona/save', { slug, graph: P.graph });
      P.dirty = false;
      closeSheet(sh, true);
      toast(`${breedIcon(r2.graph.breed)} 성격을 정했어요! 다음 요청부터 적용돼요`, 3200);
      await route();
      jump(); burst(['🎭', '✨', '💜']);
    } catch (e) { toast(e.message); btn.disabled = false; }
  }
  sh.submit = save;
  P.sheet = sh;
  if (P.compiled) renderPreview();
  requestAnimationFrame(() => { drawGraph(); schedulePreview(0); });
}

function ensureHub() {
  if (!P.graph.nodes.some((n) => n.kind === 'situation' && n.situation === 'normal')) {
    P.graph.nodes.unshift({ id: 's-normal', kind: 'situation', situation: 'normal', x: 0, y: 0 });
  }
}
async function loadBreed(k) {
  try {
    const r = await api('/api/breed?b=' + k);
    if (!P) return;
    const keep = { enabled: P.graph.enabled, verify_re: P.graph.verify_re, big_files: P.graph.big_files };
    P.graph = Object.assign(r.graph, keep);
    P.picked = null;
    ensureHub();
    $$('.breed', P.sheet.el).forEach((b) => b.classList.toggle('on', b.dataset.b === k));
    $('#pName', P.sheet.el).value = P.graph.name || '';
    drawGraph(); changed();
    toast(`${breedIcon(k)} ${r.graph.name}! 마음에 들면 아래에서 정해 주세요`);
  } catch (e) { toast(e.message); }
}
function addNode(kind, k) {
  const g = P.graph;
  if (kind === 'situation') {
    const ex = g.nodes.find((n) => n.kind === 'situation' && n.situation === k);
    if (ex) { toast('이미 있는 상황이에요'); flashNode(ex.id); return; }
    const n = { id: newId('s'), kind: 'situation', situation: k, x: 0, y: 0 };
    g.nodes.push(n);
    if (P.picked) { connect(P.picked, n.id); toast('새 상황에 이었어요'); }
  } else {
    const n = { id: newId('t'), kind: 'trait', trait: k, level: 2, x: 0, y: 0 };
    g.nodes.push(n);
    P.picked = n.id;   // 바로 이을 수 있게 골라 둔다
    toast('이을 상황을 눌러 주세요 👉');
  }
  g.breed = '';
  $$('.breed', P.sheet.el).forEach((b) => b.classList.remove('on'));
  drawGraph(); changed();
  const cv = $('#canvas');
  if (cv && P.sheet) {   // 시트 본문만 스크롤한다 - scrollIntoView 는 폰 틀까지 밀어 올린다
    const sb = P.sheet.sb;
    sb.scrollTo({ top: Math.max(0, cv.getBoundingClientRect().top - sb.getBoundingClientRect().top + sb.scrollTop - 60), behavior: 'smooth' });
  }
}
function flashNode(id) {
  const el = document.querySelector(`.node[data-id="${id}"]`);
  if (!el) return;
  el.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.1)' }, { transform: 'scale(1)' }], { duration: 400, easing: 'cubic-bezier(.34,1.56,.64,1)' });
}

// 자동 배치 - 성향은 왼쪽, 상황은 오른쪽. 상황은 이어진 성향들의 높이 가운데에 둔다
function layout(W) {
  const g = P.graph;
  const order = Object.keys(P.cat.situations);
  const sits = g.nodes.filter((n) => n.kind === 'situation').sort((a, b) => order.indexOf(a.situation) - order.indexOf(b.situation));
  const sIdx = (id) => sits.findIndex((s) => s.id === id);
  const traits = g.nodes.filter((n) => n.kind === 'trait')
    .map((t, i) => ({ t, i, k: Math.min(99, ...g.edges.filter((e) => e.from === t.id).map((e) => sIdx(e.to)).filter((x) => x >= 0)) }))
    .sort((a, b) => a.k - b.k || a.i - b.i).map((x) => x.t);
  const ROW = 96, SROW = 78, TOPY = 16;
  traits.forEach((t, i) => { t.x = 14; t.y = TOPY + i * ROW; });
  let last = -1e9;
  sits.forEach((s, i) => {
    const ys = g.edges.filter((e) => e.to === s.id).map((e) => g.nodes.find((n) => n.id === e.from)).filter(Boolean).map((t) => t.y + 10);
    const want = ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : TOPY + i * SROW;
    s.y = Math.max(want, last + SROW, TOPY);
    s.x = Math.max(180, W - 150 - 14);
    last = s.y;
  });
  return Math.max(TOPY + traits.length * ROW, last + SROW + 10, 170);
}

function drawGraph() {
  const cv = $('#canvas');
  if (!cv || !P) return;
  const keepFocus = document.activeElement && document.activeElement.closest('.node') ? document.activeElement.closest('.node').dataset.id : P.focusId;
  P.focusId = null;
  $$('.node', cv).forEach((n) => n.remove());
  const cat = P.cat;
  const g = P.graph;
  const H = layout(cv.clientWidth);
  cv.style.height = H + 'px';
  const linked = new Set(g.edges.map((e) => e.from));
  g.nodes.forEach((n) => {
    const el = document.createElement('div');
    el.dataset.id = n.id;
    el.tabIndex = 0;
    el.style.left = n.x + 'px'; el.style.top = n.y + 'px';
    if (n.kind === 'trait') {
      const t = cat.traits[n.trait];
      el.className = 'node trait' + (P.picked === n.id ? ' picked' : '') + (linked.has(n.id) ? '' : ' loose');
      el.setAttribute('role', 'button');
      el.setAttribute('aria-label', `${t.name} 세기 ${LEVEL_WORD[n.level - 1]}`);
      el.dataset.tip = `${esc(n.level >= 2 ? t.firm : t.soft)}<br><span style="opacity:.7">Enter 고르기, 1~3 세기, Delete 빼기</span>`;
      el.innerHTML = `<button class="x" aria-label="빼기" tabindex="-1">✕</button>
        <div class="nt"><span class="ic">${t.icon}</span>${esc(t.name)}</div>
        <div class="ns">${linked.has(n.id) ? esc(t.short) : '아직 안 이어졌어요'}</div>
        <div class="lvw">${[1, 2, 3].map((l) => `<button class="${l === n.level ? 'on' : ''}${l === 3 ? ' l3' : ''}" data-l="${l}" tabindex="-1" aria-label="세기 ${LEVEL_WORD[l - 1]}" data-tip="${esc(LEVEL_TIP[l - 1])}">${LEVEL_WORD[l - 1]}</button>`).join('')}</div>
        <span class="port" data-tip="끌거나 눌러서 상황에 잇기"></span>`;
    } else {
      const s = cat.situations[n.situation];
      el.className = 'node sit' + (n.situation === 'normal' ? ' hub' : '') + (P.picked ? ' target' : '');
      el.setAttribute('role', 'button');
      el.setAttribute('aria-label', s.name);
      el.dataset.tip = esc(SIT_TIP[n.situation] || '') + (P.picked ? '<br>눌러서 고른 성향을 이어요' : '');
      el.innerHTML = `${n.situation === 'normal' ? '' : '<button class="x" aria-label="빼기" tabindex="-1">✕</button>'}
        <div class="nt"><span class="ic">${s.icon}</span>${esc(s.name)}</div>
        <div class="ns">${n.situation === 'normal' ? '늘 적용' : s.forceable ? '<span class="lock">🔒 강제 가능</span>' : '모델이 판단'}</div>
        <span class="port-in"></span>`;
    }
    cv.appendChild(el);
    bindNode(el, n);
  });
  drawWires();
  if (keepFocus) { const f = cv.querySelector(`.node[data-id="${keepFocus}"]`); if (f) f.focus({ preventScroll: true }); }
}
function portPos(id, side) {
  const el = document.querySelector(`.node[data-id="${id}"]`);
  if (!el) return null;
  return { x: el.offsetLeft + (side === 'out' ? el.offsetWidth + 2 : -2), y: el.offsetTop + el.offsetHeight / 2 };
}
const curve = (a, b) => { const dx = Math.max(30, Math.abs(b.x - a.x) / 2); return `M${a.x} ${a.y} C${a.x + dx} ${a.y} ${b.x - dx} ${b.y} ${b.x} ${b.y}`; };
function drawWires(temp) {
  const svg = $('#wires');
  if (!svg || !P) return;
  const lv = (id) => (P.graph.nodes.find((n) => n.id === id) || {}).level;
  svg.innerHTML = P.graph.edges.map((e, i) => {
    const a = portPos(e.from, 'out'), b = portPos(e.to, 'in');
    return a && b ? `<path class="${lv(e.from) === 3 ? 'strong' : ''}" d="${curve(a, b)}" data-i="${i}"><title>눌러서 끊기</title></path>` : '';
  }).join('') + (temp ? `<path class="temp" d="${curve(temp.a, temp.b)}"/>` : '');
  $$('path[data-i]', svg).forEach((p) => p.addEventListener('click', (e) => { e.stopPropagation(); P.graph.edges.splice(+p.dataset.i, 1); drawGraph(); changed(); }));
}
function connect(from, to) {
  if (!P.graph.edges.some((e) => e.from === from && e.to === to)) { P.graph.edges.push({ from, to }); changed(); }
  P.picked = null;
  P.focusId = from;
  drawGraph();
}
function removeNode(n) {
  if (n.kind === 'situation' && n.situation === 'normal') return;
  P.graph.nodes = P.graph.nodes.filter((m) => m.id !== n.id);
  P.graph.edges = P.graph.edges.filter((ed) => ed.from !== n.id && ed.to !== n.id);
  if (P.picked === n.id) P.picked = null;
  drawGraph(); changed();
}
function bindNode(el, n) {
  const cv = $('#canvas');
  const x = el.querySelector('.x');
  if (x) x.addEventListener('click', (e) => { e.stopPropagation(); removeNode(n); });
  $$('.lvw button', el).forEach((b) => b.addEventListener('click', (e) => { e.stopPropagation(); n.level = +b.dataset.l; P.focusId = n.id; drawGraph(); changed(); }));
  el.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); el.click(); }
    else if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); removeNode(n); }
    else if (n.kind === 'trait' && /^Digit[123]$/.test(e.code)) { e.preventDefault(); n.level = +e.code.slice(5); P.focusId = n.id; drawGraph(); changed(); }
  });
  if (n.kind === 'situation') {
    el.addEventListener('click', (e) => { if (e.target.closest('.x')) return; if (P.picked) connect(P.picked, n.id); });
    return;
  }
  el.addEventListener('click', (e) => {
    if (e.target.closest('button, .port')) return;
    P.picked = P.picked === n.id ? null : n.id;
    P.focusId = n.id;
    drawGraph();
  });
  const port = el.querySelector('.port');
  port.addEventListener('pointerdown', (e) => {
    e.stopPropagation(); e.preventDefault();
    port.setPointerCapture(e.pointerId);
    hideTip();
    const sx = e.clientX, sy = e.clientY;
    let over = null, moved = false;
    const mv = (ev) => {
      if (Math.abs(ev.clientX - sx) + Math.abs(ev.clientY - sy) > 6) moved = true;
      if (!moved) return;
      const r = cv.getBoundingClientRect();
      drawWires({ a: portPos(n.id, 'out'), b: { x: ev.clientX - r.left, y: ev.clientY - r.top } });
      const hit = document.elementFromPoint(ev.clientX, ev.clientY);
      const tgt = hit && hit.closest('.node.sit');
      if (over && over !== tgt) over.classList.remove('target');
      over = tgt; if (over) over.classList.add('target');
    };
    const up = () => {
      port.removeEventListener('pointermove', mv); port.removeEventListener('pointerup', up); port.removeEventListener('pointercancel', up);
      if (!moved) { P.picked = P.picked === n.id ? null : n.id; drawGraph(); if (P.picked) toast('이을 상황을 눌러 주세요 👉'); return; }
      if (over) connect(n.id, over.dataset.id); else drawWires();
    };
    port.addEventListener('pointermove', mv); port.addEventListener('pointerup', up); port.addEventListener('pointercancel', up);
  });
}
function changed() { if (P) { P.dirty = true; P.armed = false; schedulePreview(180); } }
function schedulePreview(ms) {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(async () => {
    if (!P) return;
    const mine = P;
    try { const c = (await api('/api/persona/preview', { graph: mine.graph })).compiled; if (P === mine) { P.compiled = c; renderPreview(); } } catch (e) { /* 저장 때 다시 확인된다 */ }
  }, ms);
}
function renderPreview() {
  const el = $('#pPreview');
  if (!el || !P || !P.compiled) return;
  const c = P.compiled;
  const now = $('#pNow');
  if (now) {
    const f = friendlyHtml(c.effective, P.cat);
    now.innerHTML = `<div class="nh">${P.dirty ? '✨ 이렇게 일하게 돼요' : P.saved ? '🎭 지금 이렇게 일해요' : '🙂 지금은 기본 Claude 예요'}</div>
      ${f || '<p class="hint" style="margin:0">아직 정한 성격이 없어요. 위에서 품종을 골라 보세요</p>'}
      ${c.enabled === false ? '<p class="hint" style="margin:6px 0 0;color:var(--bad)">성격이 꺼져 있어요 (직접 꾸미기 > 세부 설정)</p>' : ''}
      ${Object.keys(c.gate_notes || {}).length ? '<p class="hint" style="margin:6px 0 0">🔒 은 Claude 가 잊어도 앱이 대신 지키게 해요</p>' : ''}`;
  }
  const gates = Object.values(c.gate_notes || {});
  el.innerHTML = `${(c.warnings || []).map((w) => `<div class="warn">⚠️ ${esc(w)}</div>`).join('')}
    <div class="say-box">
      <div class="k" style="margin-top:0">🌅 일을 시작할 때</div><pre>${esc(c.session || '아직 없어요. 성향을 상황에 이어 주세요')}</pre>
      <div class="k">💬 요청할 때마다</div><pre>${esc(c.turn || '없어요 (보통 이상이면 생겨요)')}</pre>
      <div class="k">🔒 진짜로 지키게 하는 것</div>${gates.length ? gates.map((v) => `<div class="gate">• ${esc(v)}</div>`).join('') : '<pre>없어요 (꼭! 을 🔒 상황에 이으면 생겨요)</pre>'}
    </div>
    ${c.enabled === false ? '<div class="warn" style="margin-top:8px">성격이 꺼져 있어서 아무것도 전해지지 않아요</div>' : ''}`;
}

// ---------------------------------------------------------------- 해마 일지
async function pageJournal(alive) {
  let h;
  try { h = await api('/api/hippo'); } catch (e) { if (alive()) screen.innerHTML = noConn(); return; }
  if (!alive()) return;
  document.title = 'brain - 해마 일지';
  const rs = h.results.slice(-40).reverse();
  const counts = {};
  h.results.forEach((r) => { counts[r.status] = (counts[r.status] || 0) + 1; });
  screen.innerHTML = `
    <div class="top"><div class="jua" style="font-size:28px">해마 일지</div></div>
    <div class="card hippo${h.alive ? ' busy' : ''}"><div class="av">${h.alive ? '✍️' : '😴'}</div>
      <div><div class="jua" style="font-size:20px">${h.alive ? '해마가 공부 중이에요' : '해마가 쉬고 있어요'}</div>
      <div class="hint">${h.alive && h.current ? esc(h.current.slice(0, 60)) + '<br>' : ''}대기 ${h.queue.length}건, 지금까지 ${h.results.length}건 (✅ ${counts.done || 0}, 💥 ${(counts.failed || 0) + (counts.timeout || 0) + (counts.denied || 0)})</div></div></div>
    ${h.queue.length ? `<div class="h2">기다리는 일 <small>${h.queue.length}건</small></div><div class="chips">${h.queue.map((q) => `<span class="chip">${esc((q.slug && q.slug !== '-' ? q.slug : '공용') + ' ' + (MODE_NAME[q.mode] || q.mode))}</span>`).join('')}</div>` : ''}
    <p class="sub" style="margin-top:12px">해마는 대화를 되짚어 기억을 새기고, 밤마다 정리해요. 여기에 그 기록이 쌓여요.</p>
    <div class="list" id="entries">${rs.map((r, i) => `<button class="entry" data-i="${i}"><span class="st ${esc(r.status)}">${ST_ICON[r.status] || '📝'}</span>
      <span style="min-width:0"><span class="et">${esc(r.slug && r.slug !== '-' ? r.slug : '공용')} ${esc(MODE_NAME[r.mode] || r.mode)}</span>
      <span class="ed">${esc(r.first)}</span><span class="hint">${esc((r.finished || '').replace('T', ' ').slice(5, 16))}</span></span></button>`).join('') ||
      '<div class="empty"><span class="big">📓</span>아직 일지가 비어 있어요<br><span class="hint">대화가 쌓이면 해마가 되짚어 새겨요</span></div>'}</div>`;
  $$('#entries .entry').forEach((b) => b.addEventListener('click', () => {
    const r = rs[+b.dataset.i];
    openSheet({ title: `<span>${ST_ICON[r.status] || '📝'}</span><span>${esc(MODE_NAME[r.mode] || r.mode)}</span>`, full: true,
      body: (el) => { el.innerHTML = `<p class="hint">${esc(r.id)}</p><div class="box md">${md(r.summary || '(요약 없음)')}</div>`; } });
  }));
}

// ---------------------------------------------------------------- 설정
async function pageSettings(alive) {
  const ov = await loadOverview();
  if (!alive()) return;
  if (!ov) { screen.innerHTML = noConn(); return; }
  document.title = 'brain - 설정';
  const c = ov.config;
  const preset = c.model === 'claude-sonnet-5-5' && c.effort === 'medium' ? 'default'
    : c.model === 'claude-sonnet-5-5' && c.effort === 'low' ? 'eco' : c.model === 'claude-opus-5-5' && c.effort === 'high' ? 'quality' : '';
  screen.innerHTML = `
    <div class="top"><div class="jua" style="font-size:28px">설정</div></div>
    <div class="card set"><div><div class="st">🧠 brain 켜기</div><div class="sd">끄면 떠올리기, 배우기, 밤 잠이 멈춰요. 기억은 남아요</div></div>
      <label class="switch"><input type="checkbox" id="sOn" ${c.enabled ? 'checked' : ''} aria-label="brain 켜기"><span></span></label></div>
    <div class="h2">해마 머리 <small>${esc(c.model.replace('claude-', ''))}, ${esc(c.effort)}</small></div>
    <div class="card"><div class="seg" id="sPreset">
      <button data-p="eco" class="${preset === 'eco' ? 'on' : ''}" data-tip="Sonnet, 낮은 노력">🌱 아껴서</button><button data-p="default" class="${preset === 'default' ? 'on' : ''}" data-tip="Sonnet, 중간 노력">🙂 보통</button><button data-p="quality" class="${preset === 'quality' ? 'on' : ''}" data-tip="Opus, 높은 노력">🎓 꼼꼼히</button></div>
      <p class="hint" style="margin:10px 2px 0">해마가 기억을 새기고 정리할 때 쓰는 모델이에요</p></div>
    <div class="h2">잠</div>
    <div class="card set"><div><div class="st">🌙 지금 재우기</div><div class="sd">마지막 잠: ${c.last_sleep ? fmtAgo(c.last_sleep) : '아직 없음'}. 밤마다 04:30 에 저절로 자요</div></div>
      <button class="btn sky small" id="sSleep">재우기</button></div>
    <div class="h2">기억 보기</div>
    <div class="card set"><div><div class="st">✨ 쉬운 말 풀이</div><div class="sd">기억을 열면 Haiku 가 쉬운 말로 풀어 줘요 (한 번에 1원 안팎, 한 번 푼 건 저장)</div></div>
      <label class="switch"><input type="checkbox" id="sExplain" ${EXPLAIN_ON ? 'checked' : ''} aria-label="쉬운 말 풀이"><span></span></label></div>
    <div class="h2">화면</div>
    <div class="card"><div class="seg" id="sTheme"><button data-t="auto">🌗 자동</button><button data-t="light">☀️ 밝게</button><button data-t="dark">🌙 어둡게</button></div></div>
    <div class="h2">단축키</div>
    <div class="card" style="font-size:13px;line-height:2">
      <span class="kbd">1</span><span class="kbd">2</span><span class="kbd">3</span> 탭 옮기기<br>
      프로젝트에서 <span class="kbd">C</span> 물어보기 <span class="kbd">F</span> 먹이 <span class="kbd">O</span> 최적화 <span class="kbd">P</span> 성격 <span class="kbd">M</span> 기억장<br>
      <span class="kbd">Esc</span> 닫기, 뒤로 <span class="kbd">⌘ Enter</span> 보내기 <span class="kbd">⌘ S</span> 성격 저장</div>
    <div class="card set" style="margin-top:20px"><div><div class="st">⏻ 앱 끄기</div><div class="sd">서버를 끝내요. 다시 열 땐 /claude-brain-app</div></div>
      <button class="btn soft small" id="sQuit">끄기</button></div>
    <button class="btn soft small" id="sWelcome" style="margin:16px auto 0;display:flex">👋 처음 안내 다시 보기</button>
    <p class="hint center" style="margin-top:20px">brain 기억 돌보기, 이 컴퓨터에서만 열려요<br>기억은 해마만 고치고, 여기서는 부탁만 해요</p>`;
  $('#sExplain').addEventListener('change', (e) => {
    EXPLAIN_ON = e.target.checked;
    try { localStorage.setItem('brainExplain', EXPLAIN_ON ? 'on' : 'off'); } catch (err) { /* 이번만 적용 */ }
    toast(EXPLAIN_ON ? '✨ 기억을 쉬운 말로 풀어 드릴게요' : '원문 그대로 보여 드릴게요');
  });
  $('#sWelcome').addEventListener('click', welcomeSheet);
  $('#sOn').addEventListener('change', async (e) => {
    try { await api('/api/config', { action: e.target.checked ? 'on' : 'off' }); toast(e.target.checked ? '🧠 brain 이 깨어났어요' : '😶 brain 을 껐어요. 기억은 그대로예요'); }
    catch (err) { toast(err.message); e.target.checked = !e.target.checked; }
  });
  $$('#sPreset button').forEach((b) => b.addEventListener('click', async () => {
    try { await api('/api/config', { action: 'preset', value: b.dataset.p }); $$('#sPreset button').forEach((x) => x.classList.toggle('on', x === b)); toast('해마 머리를 바꿨어요'); }
    catch (e) { toast(e.message); }
  }));
  $('#sSleep').addEventListener('click', async (e) => {
    e.target.disabled = true;
    try { await api('/api/sleep', {}); toast('🌙 쿨쿨… 정리하고 잊을 건 잊어요'); } catch (err) { toast(err.message); }
    setTimeout(() => { e.target.disabled = false; }, 3000);
  });
  $('#sQuit').addEventListener('click', async (e) => {
    const b = e.target;
    if (b.dataset.sure !== '1') { b.dataset.sure = '1'; b.textContent = '정말 끄기'; setTimeout(() => { b.dataset.sure = ''; b.textContent = '끄기'; }, 3000); return; }
    try { await api('/api/quit', {}); } catch (err) { /* 이미 꺼졌다 */ }
    screen.innerHTML = '<div class="empty" style="padding-top:140px"><span class="big">👋</span>앱을 껐어요. 창을 닫아도 돼요<br><span class="hint">다시 열 땐 /claude-brain-app</span></div>';
    setTimeout(() => window.close(), 1200);
  });
  $$('#sTheme button').forEach((b) => {
    b.classList.toggle('on', b.dataset.t === THEME);
    b.addEventListener('click', () => {
      THEME = b.dataset.t;
      try { localStorage.setItem('brainTheme', THEME); } catch (e) { /* 이번만 적용 */ }
      applyTheme(THEME);
      $$('#sTheme button').forEach((x) => x.classList.toggle('on', x === b));
    });
  });
}

// ---------------------------------------------------------------- 첫 안내
const WELCOME = [
  { i: '🧠', t: '프로젝트마다 뇌가 하나씩 자라요', d: 'Claude 가 일하면서 배운 걸 <b>저절로</b> 기억해요.<br>여기선 그 뇌를 구경하고 돌봐요.' },
  { i: '💬', t: '말풍선은 이 뇌가 아끼는 것', d: '말풍선을 누르면 그 기억을 모아 봐요.<br>기억은 <b>쉬운 말</b>로 풀어 주고,<br>궁금하면 뇌한테 <b>물어볼</b> 수도 있어요.' },
  { i: '🍙', t: '돌보기는 버튼 몇 개면 돼요', d: '🍙 꼭 기억할 걸 알려 주고, ✨ 머리를 정리하고,<br>🎭 일하는 성격을 정해요.<br>기억에 대한 피드백은 📮 에 모아 한 번에 보내요.' },
];
function welcomeSheet() {
  let i = 0;
  const done = () => { try { localStorage.setItem('brainWelcomed', '1'); } catch (e) { /* 다음에 또 보여도 괜찮다 */ } };
  const sh = openSheet({
    title: '<span>👋</span><span>반가워요</span>',
    kind: 'welcome',
    onClose: done,
    body: (el) => { el.innerHTML = '<div class="welcome" id="wel"></div>'; },
    foot: (el) => {
      el.innerHTML = '<div class="row" style="display:flex;gap:8px"><button class="btn soft small" id="wSkip" style="flex:none">건너뛰기</button><button class="btn block" id="wNext" data-autofocus></button></div>';
      $('#wSkip', el).addEventListener('click', () => closeSheet(sh));
      $('#wNext', el).addEventListener('click', () => { if (i < WELCOME.length - 1) { i++; draw(); } else closeSheet(sh); });
    },
  });
  sh.submit = () => $('#wNext', sh.el).click();
  function draw() {
    const w = WELCOME[i];
    $('#wel', sh.el).innerHTML = `<span class="wi">${w.i}</span><div class="wt">${esc(w.t)}</div><p class="wd">${w.d}</p>
      <div class="dots">${WELCOME.map((x, k) => `<i class="${k === i ? 'on' : ''}"></i>`).join('')}</div>`;
    $('#wNext', sh.el).textContent = i < WELCOME.length - 1 ? '다음' : '시작하기 🎉';
  }
  draw();
}
function welcomed() { try { return localStorage.getItem('brainWelcomed') === '1'; } catch (e) { return true; } }

// ---------------------------------------------------------------- 라우팅
let lastPath = '';
let SEQ = 0;
function curPath() { return (location.hash.replace(/^#/, '') || '/').split('?'); }
async function route() {
  const my = ++SEQ;
  const alive = () => my === SEQ;
  hideTip();
  if (!TOKEN) { screen.innerHTML = noConn(); return; }
  const [path, query] = curPath();
  const params = new URLSearchParams(query || '');
  const pushed = path.startsWith('/p/');
  const tab = path.startsWith('/journal') ? 'journal' : path.startsWith('/settings') ? 'settings' : 'home';
  $$('#tabbar a').forEach((a) => { const on = a.dataset.tab === tab && !pushed; a.classList.toggle('on', on); a.setAttribute('aria-current', on ? 'page' : 'false'); });
  $('#tabbar').classList.toggle('hide', pushed);
  const anim = lastPath !== path ? (pushed ? 'enter' : 'fade') : '';
  screen.className = 'screen' + (pushed ? ' pushed' : '');
  if (lastPath !== path) screen.scrollTop = 0;
  lastPath = path;
  const open = params.get('open');
  if (open) history.replaceState(null, '', '#' + path);   // 새로고침해도 다시 열리지 않게
  if (pushed) await pageProject(decodeURIComponent(path.slice(3)), alive, open);
  else {
    CUR = null; clearTimeout(topicTimer);
    TRAY = { layer: '', items: [] }; updateTrayBar(false);
    if (tab === 'journal') await pageJournal(alive); else if (tab === 'settings') await pageSettings(alive); else await pageHome(alive);
  }
  if (anim && alive()) { screen.classList.remove('enter', 'fade'); void screen.offsetWidth; screen.classList.add(anim); }
  if (alive() && !welcomed() && !SHEETS.length && $('.pets, #stage')) welcomeSheet();
}
window.addEventListener('hashchange', () => { closeAllSheets(); route(); });

// 키보드 - 한글 입력 상태에서도 먹도록 글자가 아니라 물리 키(e.code)로 본다
document.addEventListener('keydown', (e) => {
  if (e.key === 'Tab') phone.classList.add('kbd-mode');
  const typing = e.target.closest && e.target.closest('input, textarea, select, [contenteditable]');
  const top = SHEETS[SHEETS.length - 1];
  if (e.key === 'Escape') {
    if (e.isComposing) return;
    if (P && P.picked && top && top.kind === 'persona') { P.picked = null; drawGraph(); return; }
    if (top) { closeSheet(top); return; }
    if (curPath()[0].startsWith('/p/')) location.hash = '#/';
    return;
  }
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { if (top && top.submit) { e.preventDefault(); top.submit(); } return; }
  if ((e.metaKey || e.ctrlKey) && e.code === 'KeyS') { if (top && top.kind === 'persona' && top.submit) { e.preventDefault(); top.submit(); } return; }
  if (typing || e.metaKey || e.ctrlKey || e.altKey || e.isComposing) return;
  if (top) {
    if (top.kind === 'memory' && e.code === 'Slash') { e.preventDefault(); const q = $('#memQ', top.el); if (q) q.focus(); }
    return;
  }
  const path = curPath()[0];
  if (path.startsWith('/p/')) {
    const map = { KeyF: '#aFeed', KeyO: '#aOpt', KeyP: '#aPersona', KeyM: '#aMem', KeyC: '#aAsk' };
    if (map[e.code] && $(map[e.code])) { e.preventDefault(); $(map[e.code]).click(); return; }
    if (e.code === 'Slash' && $('#aMem')) { e.preventDefault(); $('#aMem').click(); return; }
  }
  const tabs = { Digit1: '#/', Digit2: '#/journal', Digit3: '#/settings' };
  if (tabs[e.code]) { e.preventDefault(); location.hash = tabs[e.code]; }
});

// 창 크기가 바뀌면 말풍선과 연결도를 다시 놓는다
let resizeTimer = 0;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    hideTip();
    if ($('#stage') && TOP) drawBubbles(TOP, false);
    if (P && $('#canvas')) drawGraph();
  }, 150);
});

// 홈과 일지는 가끔 새로 그린다(해마 상태가 바뀐다). 시트가 열려 있거나, 프로젝트를 보거나, 입력 중이면 건드리지 않는다
let lastSig = '';
setInterval(async () => {
  if (document.hidden || !TOKEN || SHEETS.length || CUR) return;
  if (curPath()[0].startsWith('/settings')) return;
  if (document.activeElement && screen.contains(document.activeElement) && phone.classList.contains('kbd-mode')) return;
  const ov = await loadOverview();
  const sig = ov ? JSON.stringify([ov.hippo, ov.queue, ov.config.enabled, ov.projects.map((p) => [p.count, p.mood.key, p.capacity, !!p.persona])]) : '';
  if (sig && sig !== lastSig) { if (lastSig) route(); lastSig = sig; }
}, 10000);

route();
