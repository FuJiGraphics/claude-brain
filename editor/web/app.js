'use strict';
// brain - 폰 앱처럼 생긴 데스크톱용 기억 돌보기 화면. 서버(editor/server.py)의 API 만 쓴다.
// 기억(cortex)을 바꾸는 동작(먹이, 정정, 최적화, 잠)은 서버가 해마 큐와 기존 스크립트로 넘긴다. 성격만 여기서 직접 저장한다.
// 문자열은 i18n.js 의 사전에서 t(키, 값) 으로 꺼낸다(ko, en, ja, zh). 언어는 brain 설정(.active/config 의 lang)을 따른다.

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const phone = $('#phone');
const screen = $('#screen');
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
// 답 글의 `코드` 를 <code> 로 - 이스케이프한 뒤 바꾼다
const inlineCode = (s) => esc(s).replace(/`([^`\n]{1,120})`/g, '<code>$1</code>').replace(/\*\*([^*\n]{1,120})\*\*/g, '<b>$1</b>');

// ---------------------------------------------------------------- 언어
const LANGS = ['ko', 'en', 'ja', 'zh'];
const LOCALE = { ko: 'ko', en: 'en', ja: 'ja', zh: 'zh-CN' };
let LANG = 'ko';
// {n|memory|memories} - 값이 1 이면 앞 낱말, 아니면 뒤 낱말(영어 단복수). 다른 언어는 쓰지 않는다
const plural = (s, v) => String(s).replace(/\{(\w+)\|([^|{}]*)\|([^|{}]*)\}/g, (m, k, one, many) => (v && k in v ? (Number(String(v[k]).replace(/[^0-9.-]/g, '')) === 1 ? one : many) : m));
const fill = (s, v, escape) => plural(s, v).replace(/\{(\w+)\}/g, (m, k) => (v && k in v ? (escape ? esc(v[k]) : String(v[k])) : m));
const raw = (k) => { const d = I18N[LANG] || I18N.ko; return k in d ? d[k] : (k in I18N.ko ? I18N.ko[k] : k); };
const t = (k, v) => fill(raw(k), v, true);     // HTML 자리 - 값은 이스케이프한다
const tp = (k, v) => fill(raw(k), v, false);   // 글자 자리(textContent, 알림, 제목)
const kbdTip = (text, key) => `${esc(text)}${key ? `<kbd>${esc(key)}</kbd>` : ''}`;
function navLang() {
  for (const l of navigator.languages || [navigator.language || 'en']) {
    const k = String(l).toLowerCase().slice(0, 2);
    if (LANGS.includes(k)) return k;
  }
  return 'en';
}
function setLang(l) {
  LANG = LANGS.includes(l) ? l : 'en';
  document.documentElement.lang = LOCALE[LANG];
  document.documentElement.dataset.lang = LANG;
  $$('#tabbar a').forEach((a) => { a.lastElementChild.textContent = tp('tab.' + a.dataset.tab); });
  const bar = $('#trayBar');
  if (bar) { $('.tb-d', bar).textContent = tp('tray.bar.d'); $('.tb-go', bar).textContent = tp('tray.go'); }
}

// ---------------------------------------------------------------- 토큰, API
let TOKEN = '';
(function initToken() {
  const u = new URL(location.href);
  const tk = u.searchParams.get('t');
  if (tk) {
    TOKEN = tk;
    try { sessionStorage.setItem('brainToken', tk); } catch (e) { /* 이 탭에서는 메모리로 쓴다 */ }
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
  try { r = await fetch(path, opt); } catch (e) { throw new Error(tp('err.conn')); }
  const j = await r.json().catch(() => ({ error: tp('err.read') }));
  if (r.status === 401) throw new Error(tp('err.token'));
  if (!r.ok) throw new Error(j.error || ('HTTP ' + r.status));
  return j;
}
const L = () => 'lang=' + LANG;

let toastTimer = 0;
function toast(msg, ms = 2600) {
  const el = $('#toast');
  el.textContent = msg;
  el.classList.remove('on'); void el.offsetWidth; el.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('on'), ms);
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
  const diff = Date.now() / 1000 - ts;
  if (diff < 60) return tp('time.now');
  const rtf = new Intl.RelativeTimeFormat(LOCALE[LANG], { numeric: 'auto' });
  if (diff < 3600) return rtf.format(-Math.floor(diff / 60), 'minute');
  if (diff < 86400) return rtf.format(-Math.floor(diff / 3600), 'hour');
  if (diff < 86400 * 14) return rtf.format(-Math.floor(diff / 86400), 'day');
  return new Intl.DateTimeFormat(LOCALE[LANG], { month: 'short', day: 'numeric' }).format(new Date(ts * 1000));
};
const num = (n) => (n || 0).toLocaleString(LOCALE[LANG]);
const pct = (x) => Math.round((x || 0) * 100) + '%';
const kTok = (n) => new Intl.NumberFormat(LOCALE[LANG], { notation: 'compact', maximumFractionDigits: 1 }).format(n || 0);
const barCls = (r) => (r > 1 ? 'hi' : r > 0.85 ? 'mid' : '');
const LV = { egg: 0, baby: 1, kid: 2, adult: 3, sage: 4 };
const stageName = (k) => tp('stage.' + k);
const REGION = {
  trap: { e: '⚠️', c: 'var(--r-trap)' },
  decision: { e: '⭐', c: 'var(--r-decision)' },
  procedure: { e: '🧰', c: 'var(--r-procedure)' },
  fact: { e: '🧱', c: 'var(--r-fact)' },
  other: { e: '📎', c: 'var(--r-other)' },
};
const regionName = (k) => tp('region.' + k);
const REGION_ORDER = ['trap', 'decision', 'procedure', 'fact', 'other'];
const TINTS = ['--pink-l', '--lav-l', '--mint-l', '--sky-l', '--lemon-l', '--peach-l'];
const tintOf = (s) => { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) >>> 0; return 'var(' + TINTS[h % TINTS.length] + ')'; };
const MOOD_EMOJI = { happy: '😆', full: '😋', overload: '😵', sleepy: '😪', study: '🤓', sick: '🤢', bored: '🥱', egg: '🥚', off: '😶' };
const moodName = (m) => tp('mood.' + m.key);
const moodWhy = (m) => tp('mood.' + m.key + '.why', { n: m.n || 0 });
const layerName = (l) => (l === 'common' ? tp('layer.common') : l.startsWith('stacks/') ? tp('layer.stack', { name: l.slice(7) }) : l.replace(/^projects\//, ''));
const modeName = (m) => (I18N.ko['mode.' + m] ? tp('mode.' + m) : (m || ''));
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
  el.innerHTML = `<div class="grab" data-tip="${esc(t('grab'))}"><i></i></div>
    <div class="sh"><div class="t">${title}</div><button class="x" aria-label="${esc(t('close'))}" data-tip="${esc(kbdTip(tp('close'), 'Esc'))}">✕</button></div>
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
const noConn = () => `<div class="empty" style="padding-top:120px"><span class="big">🔌</span>${t('noconn')}<br><span class="hint">${t('noconn.hint')}</span></div>`;

// ---------------------------------------------------------------- 홈
function careItems(ov) {
  const out = [];
  if (!ov.config.enabled) out.push({ e: '😶', bg: 'var(--bg2)', t: tp('care.off'), d: tp('care.off.d'), go: tp('care.on'), act: 'on' });
  const all = ov.projects.map((p) => Object.assign({ layer: 'projects/' + p.slug }, p)).concat(ov.shared);
  all.filter((p) => p.capacity > 1).sort((a, b) => b.capacity - a.capacity).slice(0, 2).forEach((p) =>
    out.push({ e: '💦', bg: 'var(--peach-l)', t: tp('care.full', { name: layerName(p.layer) }), d: tp('care.full.d', { w: pct(p.capacity) }), go: tp('care.opt'), href: `#/p/${p.layer}?open=opt` }));
  const fails = (ov.results || []).filter((r) => ['failed', 'denied', 'timeout'].includes(r.status)).length;
  if (fails) out.push({ e: '💥', bg: 'var(--pink-l)', t: tp('care.fail', { n: fails }), d: tp('care.fail.d'), go: tp('care.see'), href: '#/journal' });
  const ls = ov.config.last_sleep;
  if (ov.config.enabled && (!ls || Date.now() / 1000 - ls > 36 * 3600)) {
    out.push({ e: '🌙', bg: 'var(--lav-l)', t: tp(ls ? 'care.sleepy' : 'care.nosleep'), d: tp('care.sleep.d'), go: tp('care.sleep'), act: 'sleep' });
  }
  if (ov.config.update) out.unshift({ e: '🎁', bg: 'var(--mint-l)', t: tp('care.update'), d: tp('care.update.d', { n: ov.config.update.n, s: ov.config.update.subject }), go: tp('care.update.go'), act: 'update' });
  if (ov.projects.length && !ov.projects.some((p) => p.persona)) {
    const big = ov.projects.slice().sort((a, b) => b.count - a.count)[0];
    out.push({ e: '🎭', bg: 'var(--lav-l)', t: tp('care.persona'), d: tp('care.persona.d', { name: big.slug }), go: tp('care.persona.go'), href: `#/p/projects/${encodeURIComponent(big.slug)}?open=persona` });
  }
  return out.slice(0, 4);
}
async function doCare(act, btn) {
  btn.disabled = true;
  try {
    if (act === 'sleep') { await api('/api/sleep', {}); toast(tp('toast.sleep')); }
    if (act === 'on') { await api('/api/config', { action: 'on' }); toast(tp('toast.on')); }
    if (act === 'update') { btn.disabled = false; updateSheet(); return; }
    btn.style.opacity = '.4';
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
    const alert = p.muted ? `<span class="alert" data-tip="${esc(t('tile.muted'))}">😴</span>` : p.capacity > 1 ? '<span class="alert">💦</span>' : '';
    const ps = p.persona ? `<span class="ps">${breedIcon(p.persona.breed)}</span>` : '';
    const tip = t('home.tile.tip', { mood: moodName(p.mood), n: num(p.count), w: pct(p.capacity) }) + (p.persona ? '<br>' + t('home.tile.persona', { name: p.persona.name || tp('act.persona.has') }) : '');
    return `<a class="pet-tile${p.muted ? ' muted' : ''}" href="#/p/projects/${encodeURIComponent(p.slug)}" style="--t:${tintOf(p.slug)};animation-delay:${i * 60}ms" data-tip="${esc(tip)}">
      <span class="lv">Lv.${LV[p.stage.key]} ${esc(stageName(p.stage.key))}</span>${alert || ps}
      ${pet(p.mood.key, p.stage.key)}
      <span class="nm">${esc(p.slug)}</span>
      <span class="md">${p.muted ? esc(tp('tile.muted')) : `${MOOD_EMOJI[p.mood.key] || ''} ${esc(moodName(p.mood))}`}</span>
      <span class="minibar ${barCls(p.capacity)}"><i style="width:${Math.min(100, p.capacity * 100)}%"></i></span>
    </a>`;
  }).join('');
  const shared = ov.shared.map((s) => `<a href="#/p/${s.layer}" data-tip="${esc(t('home.shared.tip', { mood: moodName(s.mood), w: pct(s.capacity) }))}">${pet(s.mood.key, s.stage.key)}
      <span><span class="t">${esc(layerName(s.layer))}</span><br><span class="s">${t('home.memories', { n: num(s.count) })}</span></span></a>`).join('');
  const total = ov.projects.reduce((a, p) => a + p.count, 0) + ov.shared.reduce((a, s) => a + s.count, 0);
  const care = careItems(ov);
  screen.innerHTML = `
    <div class="top">
      <div class="logo">${pet(ov.config.enabled ? 'happy' : 'off', 'adult')}<b>brain</b></div>
      <a class="pill${h.alive ? ' busy' : ''}" href="#/journal" data-tip="${esc(t('hippo.tip'))}"><span class="dot"></span>${t(h.alive ? 'hippo.busy' : 'hippo.idle')}${ov.queue ? ` ${ov.queue}` : ''}</a>
    </div>
    <div class="hello">${!ov.config.enabled ? t('home.off') : ov.projects.length ? t('home.hello', { n: ov.projects.length }) : t('home.hello0')}</div>
    <p class="sub">${ov.age != null ? t('home.age', { n: ov.age + 1 }) : ''}${t('home.total', { n: num(total) })}</p>
    ${care.length ? `<div class="h2" style="margin-top:4px">${t('home.care')}</div><div class="care">${care.map((c) => `
      ${c.href ? `<a class="care-item" href="${c.href}">` : `<button class="care-item" data-act="${c.act}">`}
        <span class="ce" style="background:${c.bg}">${c.e}</span><span><span class="ct">${esc(c.t)}</span><br><span class="cd">${esc(c.d)}</span></span><span class="go">${esc(c.go)} ›</span>
      ${c.href ? '</a>' : '</button>'}`).join('')}</div>` : ''}
    <div class="h2" style="margin-top:4px">${t('home.mine')} <small>${t('home.mine.hint')}</small></div>
    <div class="pets">${tiles || `<div class="empty" style="grid-column:1/-1"><span class="big">🥚</span>${t('home.none')}<br><span class="hint" id="noneHint">${t('home.none.hint')}</span></div>`}</div>
    <div id="newBox"></div>
    <div class="h2">${t('home.shared')} <small>${t('home.shared.hint')}</small></div>
    <div class="shared">${shared}</div>`;
  $$('.care-item[data-act]').forEach((b) => b.addEventListener('click', () => doCare(b.dataset.act, b)));
  updateEyes();
  loadCandidates(alive, !ov.projects.length);
}

// 아직 모르는 프로젝트 - 최근 Claude Code 로 일했지만 등록 안 된 git 폴더. '키우기' 로 바로 등록을 맡긴다
const HATCHING = new Set();
async function loadCandidates(alive, empty) {
  let r;
  try { r = await api('/api/candidates'); } catch (e) { return; }
  if (!alive() || !$('#newBox')) return;
  const items = (r.items || []).slice(0, 5);
  if (!items.length) return;
  if (empty && $('#noneHint')) $('#noneHint').textContent = tp('home.none.new');
  $('#newBox').innerHTML = `<div class="h2">${t('home.new')} <small>${t('home.new.hint')}</small></div>
    <div class="care">${items.map((c, i) => `<button class="care-item cand" data-i="${i}" data-tip="${esc(t('home.new.tip'))}" ${HATCHING.has(c.root) ? 'disabled' : ''}>
      <span class="ce" style="background:var(--lemon-l)">🥚</span><span style="min-width:0"><span class="ct">${esc(c.name)}</span><br><span class="cd">${esc(tp('home.new.meta', { n: c.sessions, ago: fmtAgo(c.last) }))}</span></span>
      <span class="go">${HATCHING.has(c.root) ? t('home.new.wait') : t('home.new.go')}</span></button>`).join('')}</div>`;
  $$('#newBox .cand').forEach((b) => b.addEventListener('click', async () => {
    const c = items[+b.dataset.i];
    b.disabled = true;
    try {
      const x = await api('/api/register', { root: c.root });
      if (x.code === 0) { HATCHING.add(c.root); $('.go', b).textContent = tp('home.new.wait'); burst(['🥚', '✨']); }
      else b.disabled = false;
      toast(x.message || '', 4200);
    } catch (e) { toast(e.message); b.disabled = false; }
  }));
}

// 새 버전 받는 법 - 명령 하나를 보여 주고 복사하게 한다
function updateSheet() {
  openSheet({
    title: `<span>🎁</span><span>${t('upd.title')}</span>`,
    kind: 'update',
    body: (el) => {
      el.innerHTML = `<p class="sub">${t('upd.body')}</p>${copyBox('/claude-brain-update')}`;
      bindCopy(el);
    },
  });
}
const copyBox = (text) => `<div class="copy-box"><code>${esc(text)}</code><button class="btn soft small" data-copy="${esc(text)}">${t('copy')}</button></div>`;
function bindCopy(root) {
  $$('[data-copy]', root).forEach((b) => b.addEventListener('click', async () => {
    const v = b.dataset.copy;
    try { await navigator.clipboard.writeText(v); } catch (e) {
      const ta = document.createElement('textarea'); ta.value = v; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch (e2) { /* 직접 고른다 */ } ta.remove();
    }
    toast(tp('copied'));
  }));
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
    if (alive()) screen.innerHTML = e.message === tp('err.conn') || e.message === tp('err.token') ? noConn()
      : `<div class="empty" style="padding-top:120px"><span class="big">🔍</span>${t('notfound')}<br><a class="btn soft small" href="#/" style="margin-top:14px">${t('home')}</a></div>`;
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
  SAY_DEFAULT = moodWhy(d.mood);
  const wkey = d.capacity > 1 ? 'weight.hi' : d.capacity > 0.85 ? 'weight.mid' : 'weight.lo';
  const name = layerName(layer);
  screen.innerHTML = `
    <div class="top">
      <a class="round" href="#/" aria-label="${esc(t('back'))}" data-tip="${esc(kbdTip(tp('back'), 'Esc'))}">‹</a>
      <div class="jua" style="font-size:22px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(name)}</div>
      <span class="lv" data-tip="${esc(st.next ? t('lv.next', { name: stageName(st.next_key || ''), n: st.next - d.count }) : t('lv.done'))}">Lv.${LV[st.key]} ${esc(stageName(st.key))}</span>
    </div>
    <div class="stage" id="stage" style="--stage-c:${tintOf(layer)}">
      <span class="pill mood-chip" data-tip="${esc(moodWhy(d.mood))}">${MOOD_EMOJI[d.mood.key] || ''} ${esc(moodName(d.mood))}</span>
      ${d.muted ? `<span class="pill muted-chip">${t('mute.badge')}</span>` : ''}
      <button class="pill ai-chip" id="aiChip" ${d.count ? '' : 'hidden'}><span class="shimmer">${t('ai.busy')}</span></button>
      <button class="pet-wrap" id="petWrap" aria-label="${esc(t('pet.aria'))}" data-tip="${esc(t('pet.pat'))}">${pet(d.mood.key, st.key)}</button>
      <div class="hearts" id="hearts"></div>
      <div class="say" id="say">${esc(SAY_DEFAULT)}</div>
    </div>
    <div class="stats">
      <div class="stat" data-tip="${esc(t('stat.count.tip'))}"><div class="k">${t('stat.count')}</div><div class="v">${num(d.count)}</div></div>
      <div class="stat" data-tip="${esc(t('stat.week.tip'))}"><div class="k">${t('stat.week')}</div><div class="v">+${num(d.learned_week)}</div></div>
      <div class="stat" data-tip="${esc(t(d.usage == null ? 'stat.usage.tip.wait' : 'stat.usage.tip'))}"><div class="k">${t('stat.usage')}</div><div class="v">${d.usage == null ? `<small>${t('stat.usage.wait')}</small>` : pct(d.usage)}</div></div>
      <div class="stat" data-tip="${esc(d.hit ? tp('stat.hit.tip', { n: d.hit.n, o: d.hit.opened }) : tp('stat.hit.tip.wait'))}"><div class="k">${t('stat.hit')}</div><div class="v">${d.hit ? pct(d.hit.rate) : `<small>${t('stat.hit.wait')}</small>`}</div></div>
    </div>
    <button class="weight card" id="weightBtn" data-tip="${esc(t(wkey))}">
      <div class="row"><span>${t('weight')}</span><span style="color:${d.capacity > 1 ? 'var(--bad)' : 'inherit'}">${pct(d.capacity)}</span></div>
      <div class="bar ${barCls(d.capacity)}"><i style="width:${Math.min(100, d.capacity * 100)}%"></i></div>
      <div class="hint" style="margin-top:6px">${t(wkey)}</div>
    </button>
    <div class="actions">
      ${isProj ? `<button class="act" id="aFeed" data-say="${esc(t('act.feed.say'))}" data-tip="${esc(kbdTip(tp('act.feed.s'), 'F'))}"><span class="ai">🍙</span><span class="al">${t('act.feed')}</span><span class="as">${t('act.feed.s')}</span><span class="kbd">F</span></button>` : ''}
      <button class="act lemon" id="aOpt" data-say="${esc(t(d.capacity > 1 ? 'act.opt.say.hi' : 'act.opt.say'))}" data-tip="${esc(kbdTip(tp('act.opt.s'), 'O'))}"><span class="ai">✨</span><span class="al">${t('act.opt')}</span><span class="as">${t('act.opt.s')}</span>${d.capacity > 1 ? '<span class="badge-n">!</span>' : ''}<span class="kbd">O</span></button>
      ${isProj ? `<button class="act lav" id="aPersona" data-say="${esc(t('act.persona.say'))}" data-tip="${esc(kbdTip(tp('act.persona.tip'), 'P'))}"><span class="ai">${ps ? breedIcon(ps.breed) : '🎭'}</span><span class="al">${t('act.persona')}</span><span class="as">${ps ? esc((ps.name || tp('act.persona.has')) + (ps.enabled === false ? tp('act.persona.off') : '')) : t('act.persona.s')}</span><span class="kbd">P</span></button>` : ''}
      <button class="act mint" id="aMem" data-say="${esc(t('act.mem.say'))}" data-tip="${esc(kbdTip(tp('act.mem.tip'), 'M'))}"><span class="ai">📚</span><span class="al">${t('act.mem')}</span><span class="as">${t('act.mem.s', { n: num(d.count) })}</span><span class="kbd">M</span></button>
    </div>
    <button class="ask-btn" id="aAsk" data-say="${esc(t('act.ask.say'))}" data-tip="${esc(kbdTip(tp('act.ask.tip'), 'C'))}">${pet('happy', st.key === 'egg' ? 'baby' : st.key)}
      <span><span class="al">${t('act.ask', { name })}</span><span class="as">${t('act.ask.s')}</span></span><span class="kbd">C</span></button>
    ${isProj ? `<div class="card set" style="margin-top:14px"><div><div class="st">😴 ${t('mute.t')}</div><div class="sd">${t('mute.d')}</div></div>
      <label class="switch"><input type="checkbox" id="pMute" ${d.muted ? 'checked' : ''} aria-label="${esc(t('mute.t'))}"><span></span></label></div>` : ''}
    ${kinds.length ? `<div class="h2">${t('kinds')}</div>
      <div class="kinds">${kinds.map((k) => `<i style="flex:${d.regions[k]};background:${REGION[k].c}" data-tip="${esc(t('kinds.tip', { name: regionName(k), n: d.regions[k] }))}"></i>`).join('')}</div>
      <div class="legend">${kinds.map((k) => `<span><i style="background:${REGION[k].c}"></i>${esc(regionName(k))} ${d.regions[k]}</span>`).join('')}</div>` : ''}
    <div class="h2">${t('recent')} <small>${d.migrated ? t('recent.migrated', { n: d.migrated }) : ''}</small></div>
    <div class="list" id="recent">${(d.recent || []).slice(0, 5).map(memRow).join('') || `<div class="empty"><span class="big">🌱</span>${t('recent.none')}</div>`}</div>`;
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
    $('#pMute').addEventListener('change', async (e) => {
      const on = e.target.checked;
      try { await api('/api/config', { action: on ? 'mute' : 'unmute', value: slug }); toast(tp(on ? 'mute.on' : 'mute.off')); if (alive()) route(); }
      catch (err) { toast(err.message); e.target.checked = !on; }
    });
  }
  // 버튼에 올리면 뇌가 반응한다
  $$('[data-say]').forEach((b) => {
    const line = b.getAttribute('data-say');
    b.addEventListener('pointerenter', () => sayTemp(line, 0));
    b.addEventListener('focus', () => { if (phone.classList.contains('kbd-mode')) sayTemp(line, 0); });
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
  let r;
  try { r = await api('/api/topics?l=' + encodeURIComponent(layer) + '&' + L() + (force ? '&force=1' : '')); } catch (e) { return; }
  if (!CUR || CUR.layer !== layer || !$('#stage')) return;
  const changed = !TOP || JSON.stringify(TOP.topics) !== JSON.stringify(r.topics) || TOP.motto !== r.motto || TOP.source !== r.source;
  TOP = r;
  const chip = $('#aiChip');
  if (r.status === 'running') {
    chip.innerHTML = `<span class="shimmer">${t('ai.busy')}</span>`;
    chip.dataset.tip = t('ai.busy.tip');
    chip.disabled = true;
  } else {
    chip.disabled = false;
    if (r.source === 'ai') { chip.innerHTML = t('ai.redo'); chip.dataset.tip = t('ai.redo.tip', { when: fmtAgo(r.generated) }); }
    else if (r.error) { chip.innerHTML = t('ai.retry'); chip.dataset.tip = t('ai.retry.tip', { err: r.error.slice(0, 120) }); }
    else { chip.innerHTML = t('ai.guess'); chip.dataset.tip = t('ai.guess.tip'); }
  }
  chip.onclick = r.status === 'running' ? null : () => { chip.disabled = true; loadTopics(layer, true); };
  if (changed) {
    drawBubbles(r, true);
    if (!coachDone() && r.topics.length) { SAY_DEFAULT = tp('coach'); say(SAY_DEFAULT); }
    else if (r.motto) { SAY_DEFAULT = r.motto; say(r.motto); }
  }
  if (r.status === 'running') topicTimer = setTimeout(() => loadTopics(layer, false), 3000);
}

function drawBubbles(tp0, animate) {
  const stage = $('#stage');
  if (!stage) return;
  $$('.bubble', stage).forEach((b) => b.remove());
  stage.classList.remove('focusing');
  const items = (tp0.topics || []).slice(0, 8);
  if (!items.length) return;
  const max = Math.max(...items.map((x) => x.count));
  const els = items.map((x, i) => {
    const b = document.createElement('button');
    b.className = 'bubble' + (tp0.source === 'ai' ? '' : ' ghost');
    b.style.setProperty('--fs', (13 + 4 * (x.count / max)).toFixed(1) + 'px');
    b.style.setProperty('--dur', (3.2 + (i % 3) * 0.6) + 's');
    b.style.setProperty('--dl', (i * 0.25) + 's');
    b.dataset.tip = t('bubble.tip', { n: x.count, used: x.used ? tp('bubble.used', { n: x.used }) : '' });
    b.innerHTML = `<span>${esc(x.emoji)}</span><span>${esc(x.label)}</span><span class="n">${x.count}</span>`;
    b.addEventListener('click', () => {
      if (!coachDone()) { try { localStorage.setItem('brainCoach', '1'); } catch (e) { /* 다음에도 안내한다 */ } SAY_DEFAULT = (TOP && TOP.motto) || moodWhy(CUR.mood); }
      memorySheet({ topic: x });
    });
    const on = () => { stage.classList.add('focusing'); b.classList.add('hot'); sayTemp(tp('bubble.say', { label: x.label, n: x.count }), 0); };
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
    tp('tap.count', { n: num(d.count) }),
    d.learned_week ? tp('tap.week', { n: d.learned_week }) : tp('tap.quiet'),
    top ? tp('tap.top', { label: top.label }) : null,
    tp('tap.tickle'),
    tp(d.capacity > 1 ? 'tap.heavy' : 'tap.light'),
    TOP && TOP.motto,
  ].filter(Boolean);
  sayTemp(lines[tapN++ % lines.length]);
  if (Math.random() < 0.4) burst(['💕', '✨', '💗']);
}

function memRow(m) {
  const r = REGION[m.region] || REGION.other;
  return `<button class="mem" data-path="${esc(m.path)}" data-tip="${esc(regionName(m.region in REGION ? m.region : 'other'))}">
    <span class="em" style="background:color-mix(in srgb, ${r.c} 22%, transparent)">${r.e}</span>
    <span style="min-width:0"><span class="tt">${esc(m.title)}</span>
    <span class="mt" style="display:block">${m.migrated ? t('mem.migrated') : esc(fmtAgo(m.mtime))}${m.used ? t('mem.used', { n: m.used }) : ''}</span></span></button>`;
}
function bindMemRows(root) { $$('.mem', root).forEach((el) => el.addEventListener('click', () => memoryDetail(el.dataset.path))); }

// ---------------------------------------------------------------- 시트: 먹이
function feedSheet(slug) {
  const examples = [tp('feed.ex1'), tp('feed.ex2'), tp('feed.ex3')];
  openSheet({
    title: `<span>🍙</span><span>${t('feed.title')}</span>`,
    body: (el) => {
      el.innerHTML = `<p class="sub" style="margin-bottom:10px">${t('feed.sub')}</p>
        <textarea id="feedText" placeholder="${esc(t('feed.ph'))}" maxlength="2000"></textarea>
        <div class="examples">${examples.map((x) => `<button data-tip="${esc(t('feed.ex.tip'))}" data-ex="${esc(x)}">💡 ${esc(x)}</button>`).join('')}</div>`;
      $$('.examples button', el).forEach((b) => b.addEventListener('click', () => { const ta = $('#feedText', el); ta.value = b.dataset.ex; ta.focus(); }));
    },
    foot: (el, sh) => {
      el.innerHTML = `<button class="btn block" id="feedGo" data-tip="${esc(kbdTip(tp('feed.go.tip'), '⌘ Enter'))}">${t('feed.go')}</button>`;
      const go = async () => {
        const btn = $('#feedGo', el);
        const text = $('#feedText', sh.el).value.trim();
        if (!text) { toast(tp('feed.empty')); $('#feedText', sh.el).focus(); return; }
        if (btn.disabled) return;
        btn.disabled = true;
        try {
          const r = await api('/api/feed', { slug, text });
          if (!r.ok) { console.warn(r.out); throw new Error(tp('feed.fail')); }
          closeSheet(sh, true);
          await wait(250);
          jump(); burst(['🍙', '💕', '😋']); sayTemp(tp('feed.say'), 3200);
          toast(tp('feed.toast'));
        } catch (e) { toast(e.message); btn.disabled = false; }
      };
      $('#feedGo', el).addEventListener('click', go);
      sh.submit = go;
    },
  });
}

// ---------------------------------------------------------------- 시트: 최적화
function prettyIdx(f) {
  if (f === 'INDEX.md') return tp('opt.map');
  if (/^\(미등록\)/.test(f)) return tp('opt.unindexed');
  return f.replace(/\.md(#\d+)?$/, '').replace(/^lessons-index-?/, '').replace(/-/g, ' ') || tp('opt.lessons');
}
function gaugeSvg(r) {
  const v = Math.min(1.5, r) / 1.5;
  const a = Math.PI * (1 - v);
  const x = 110 + 90 * Math.cos(a), y = 120 - 90 * Math.sin(a);
  const col = r > 1 ? 'var(--bad)' : r > 0.85 ? 'var(--lemon)' : 'var(--mint)';
  const k = Math.PI * (1 - 1 / 1.5);
  return `<svg viewBox="0 0 220 130"><path d="M20 120 A90 90 0 0 1 200 120" fill="none" stroke="var(--bg2)" stroke-width="20" stroke-linecap="round"/>
    ${v > 0.001 ? `<path d="M20 120 A90 90 0 0 1 ${x.toFixed(1)} ${y.toFixed(1)}" fill="none" stroke="${col}" stroke-width="20" stroke-linecap="round"/>` : ''}
    <line x1="${(110 + 76 * Math.cos(k)).toFixed(1)}" y1="${(120 - 76 * Math.sin(k)).toFixed(1)}" x2="${(110 + 104 * Math.cos(k)).toFixed(1)}" y2="${(120 - 104 * Math.sin(k)).toFixed(1)}" stroke="var(--ink3)" stroke-width="2" stroke-dasharray="3 3"/></svg>`;
}
function optimizeSheet() {
  const d = CUR;
  if (!d) return;
  let mode = d.capacity > 0.7 ? 'over' : 'all';   // 70% 를 넘은 색인이 있으면 그곳만 (서버 TIDY_TARGET)
  let plan = null;
  let seq = 0;
  const sh = openSheet({
    title: `<span>✨</span><span>${t('opt.title')}</span>`,
    body: (el) => {
      const parts = (d.capacity_parts || []).slice(0, 5).map((p) => {
        const r = Math.max(p.ratio, p.item_ratio);
        return `<div class="part" data-tip="${esc(t('opt.part.tip', { chars: num(p.chars), cap: num(p.cap), items: p.items }))}"><div class="pn"><span>${esc(prettyIdx(p.file))}</span><span>${pct(r)}</span></div><div class="bar ${barCls(r)}"><i style="width:${Math.min(100, r * 100)}%"></i></div></div>`;
      }).join('');
      el.innerHTML = `
        <div class="gauge-big">${gaugeSvg(d.capacity)}<div class="gv">${pct(d.capacity)}</div>
          <div class="gl">${t(d.capacity > 1 ? 'opt.hi' : d.capacity > 0.85 ? 'opt.mid' : 'opt.lo')}</div></div>
        <p class="sub center" style="margin:6px 0 14px">${t('opt.sub')}</p>
        <div style="margin-top:4px"><div class="seg" id="optSeg"><button data-m="over" data-tip="${esc(t('opt.over.tip'))}">${t('opt.over')}</button><button data-m="all" data-tip="${esc(t('opt.all.tip'))}">${t('opt.all')}</button></div></div>
        <div class="box" id="optPlan" style="margin-top:10px"><p class="hint">${t('opt.calc')}</p></div>
        <details class="more" style="margin-top:12px"><summary>${t('opt.where')}</summary>
          <div class="box" style="margin-top:6px">${parts || `<p class="hint">${t('opt.where.none')}</p>`}
          <p class="hint" style="margin:10px 0 0">${t('opt.where.hint')}</p></div></details>`;
      $$('#optSeg button', el).forEach((b) => b.addEventListener('click', () => { if (mode !== b.dataset.m) { mode = b.dataset.m; dry(); } }));
    },
    foot: (el) => {
      el.innerHTML = `<button class="btn lemon block" id="optGo" disabled>${t('opt.go')}</button>`;
      $('#optGo', el).addEventListener('click', go);
    },
  });
  sh.submit = () => { const b = $('#optGo', sh.el); if (b && !b.disabled) go(); };
  async function dry() {
    const my = ++seq;
    $$('#optSeg button', sh.el).forEach((b) => b.classList.toggle('on', b.dataset.m === mode));
    const box = $('#optPlan', sh.el);
    const btn = $('#optGo', sh.el);
    box.innerHTML = `<p class="hint">${t('opt.calc')}</p>`;
    if (btn) btn.disabled = true;
    try {
      const p = await api('/api/tidy', { layer: d.layer, mode, dry: true });
      if (my !== seq || !sh.el.isConnected) return;
      plan = p;
      if (p.busy) {
        box.innerHTML = `<div class="center" style="padding:6px 0"><span style="font-size:30px">🧹</span><br><b>${t('opt.busy', { n: p.busy })}</b><p class="hint" style="margin:4px 0 0">${t('opt.busy.hint')}</p></div>`;
        plan = null;
        return;
      }
      if (!p.count) {
        box.innerHTML = `<div class="center" style="padding:6px 0"><span style="font-size:30px">🫧</span><br><b>${t(mode === 'over' ? 'opt.none.over' : 'opt.none.all')}</b>${mode === 'over' ? `<p class="hint" style="margin:4px 0 0">${t('opt.none.over.hint')}</p>` : ''}</div>`;
        return;
      }
      box.innerHTML = `<b style="font-size:15px">${t('opt.plan', { n: p.count })}</b>
        <p class="hint" style="margin:4px 0 0">${t('opt.plan.hint')}</p>
        <details class="more" style="margin-top:6px"><summary style="font-size:12.5px">${t('opt.detail')}</summary>
          ${p.slices.map((s) => `<div style="display:flex;justify-content:space-between;gap:8px;font-size:12.5px;color:var(--ink2)"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(prettyIdx(s.id.split(':')[1] || s.id))}</span><span style="flex:none">${t('opt.tok', { n: kTok(s.tok) })}</span></div>`).join('')}
          <p class="hint" style="margin:6px 0 0">${t('opt.tok.sum', { n: kTok(p.tok) })}</p></details>`;
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
        <div class="jua" style="font-size:22px;margin-top:8px">${t('opt.done')}</div>
        <p class="sub">${t('opt.done.sub', { n: g.count })}</p></div>`;
      btn.outerHTML = `<a class="btn soft block" href="#/journal">${t('opt.journal')}</a>`;
      sh.submit = null;
      SAY_DEFAULT = tp('opt.say');
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
    title: `<span>📚</span><span>${t('mem.title')}</span><span class="hint" style="font-family:'Pretendard Variable';font-size:13px">${t('mem.count', { n: num(d.count) })}</span>`,
    full: true,
    kind: 'memory',
    body: (el) => {
      el.innerHTML = `<input class="input" id="memQ" placeholder="${esc(t('mem.search'))}" ${opt.topic ? '' : 'data-autofocus'}>
        <div class="chips" id="memChips" style="margin-top:10px"></div>
        <div class="hint" id="memCount" style="margin:0 2px 8px"></div>
        <div class="list" id="memList"></div>
        <button class="btn soft small more-btn" id="memMore" hidden></button>
        ${d.dormant_list && d.dormant_list.length ? `<details class="more" style="margin-top:16px"><summary>${t('mem.dormant', { n: d.dormant_list.length })}</summary>
          <p class="hint">${t('mem.dormant.hint')}</p>
          <div class="list">${d.dormant_list.map((x) => `<button class="mem" data-path="${esc(x.path)}"><span class="em" style="background:var(--bg2)">💤</span><span><span class="tt">${esc(x.line.replace(/\[([^\]]*)\]\([^)]*\)/g, '$1'))}</span><span class="mt" style="display:block">${t('mem.dormant.since', { date: x.since })}</span></span></button>`).join('')}</div></details>` : ''}
        <details class="more" id="archBox" style="margin-top:12px"><summary>${t('arch.h')}</summary>
          <p class="hint">${t('arch.hint')}</p><div class="list" id="archList"><p class="hint shimmer">${t('detail.loading')}</p></div></details>`;
      $('#archBox', el).addEventListener('toggle', async (ev) => {
        if (!ev.target.open || ev.target.dataset.loaded) return;
        ev.target.dataset.loaded = '1';
        try {
          const r = await api('/api/archive?l=' + encodeURIComponent(d.layer));
          $('#archList', el).innerHTML = r.items.map((x, i) => `<button class="mem arch" data-i="${i}"><span class="em" style="background:var(--bg2)">🗂</span><span style="min-width:0"><span class="tt">${esc(x.title)}</span><span class="mt" style="display:block">${esc(archReason(x.reason))}${x.when ? ', ' + esc(x.when) : ''}</span></span></button>`).join('')
            || `<div class="empty"><span class="big">🗂</span>${t('arch.none')}</div>`;
          $$('#archList .arch', el).forEach((b) => b.addEventListener('click', () => archiveDetail(r.items[+b.dataset.i])));
        } catch (e) { $('#archList', el).innerHTML = `<div class="out">${esc(e.message)}</div>`; }
      });
      const chips = () => {
        const all = [{ label: tp('mem.all'), on: !f.topic && !f.region }]
          .concat(topics.map((x) => ({ label: x.emoji + ' ' + x.label, on: !!(f.topic && f.topic.label === x.label), topic: x })))
          .concat(REGION_ORDER.filter((k) => d.regions[k]).map((k) => ({ label: REGION[k].e + ' ' + regionName(k), on: f.region === k, r: k })));
        $('#memChips', el).innerHTML = all.map((c) => `<button class="chip${c.on ? ' on' : ''}" aria-pressed="${c.on}">${esc(c.label)}</button>`).join('');
        $$('#memChips .chip', el).forEach((b, i) => b.addEventListener('click', () => {
          const c = all[i];
          f.topic = c.topic || null; f.region = c.r || ''; shown = PAGE;
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
          q.every((w) => (m.title + ' ' + m.line + ' ' + m.path).toLowerCase().includes(w)));
        $('#memCount', el).textContent = tp('mem.count', { n: num(list.length) });
        $('#memList', el).innerHTML = list.slice(0, shown).map(memRow).join('') || `<div class="empty"><span class="big">🫥</span>${t('mem.none')}</div>`;
        bindMemRows($('#memList', el));
        const more = $('#memMore', el);
        more.hidden = list.length <= shown;
        more.textContent = tp('mem.more', { n: num(list.length - shown) });
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
const FB_ICON = { confirm: '👍', outdated: '✏️', important: '⭐', forget: '🗑', restore: '♻️' };
const archReason = (r) => tp(I18N.ko['arch.r.' + r] ? 'arch.r.' + r : 'arch.r.other');

// 보관한 기억 - 왜 보관했는지와 원문을 보이고, 되살리기는 우체통으로 해마에게 맡긴다
function archiveDetail(x) {
  openSheet({
    title: `<span>🗂</span><span>${t('arch.title')}</span>`,
    full: true,
    kind: 'detail',
    body: async (el) => {
      const inTray = () => TRAY.items.find((y) => y.path === x.path);
      el.innerHTML = `<div class="plain"><div class="ps">${esc(x.title)}</div>
          <div class="pr"><span class="pi" style="background:var(--bg2)">🗂</span><div><b>${t('arch.why')}</b><p>${esc(archReason(x.reason))}${x.note ? ': ' + esc(x.note) : ''}</p></div></div></div>
        <div id="archAct" style="margin:12px 0"></div>
        <details class="more" open><summary>${t('detail.orig')}</summary><div id="archBody" style="margin-top:6px"><p class="hint">${t('detail.opening')}</p></div></details>`;
      const act = () => {
        $('#archAct', el).innerHTML = inTray() ? `<div class="fb-state">${t('arch.in')}</div>` : `<button class="btn block mint" id="archGo">${t('arch.go')}</button>`;
        const b = $('#archGo', el);
        if (b) b.addEventListener('click', async () => {
          b.disabled = true;
          try {
            const r = await api('/api/feedback/add', { layer: CUR.layer, path: x.path, title: x.title, kind: 'restore', text: '' });
            TRAY.items = r.items; updateTrayBar(true); toast(tp('arch.in')); act();
          } catch (e) { toast(e.message); b.disabled = false; }
        });
      };
      act();
      try {
        const m = await api('/api/memory?p=' + encodeURIComponent(x.path));
        if (el.isConnected) $('#archBody', el).innerHTML = `<article class="md box">${md(m.text, m.path.split('/').slice(0, -1).join('/'))}</article>`;
      } catch (e) { if (el.isConnected) $('#archBody', el).innerHTML = `<div class="out">${esc(e.message)}</div>`; }
    },
  });
}
const SKEL = () => `<div class="skel big"></div><div class="skel"></div><div class="skel half"></div><div class="skel"></div><p class="hint shimmer" style="margin:8px 0 0">${t('detail.loading')}</p>`;

function memoryDetail(path) {
  const mem = CUR && CUR.memories.find((m) => m.path === path);
  const title = mem ? mem.title : path.split('/').pop().replace(/\.md$/, '');
  openSheet({
    title: `<span>📖</span><span>${t('detail.title')}</span>`,
    full: true,
    kind: 'detail',
    body: async (el, sh) => {
      el.innerHTML = `<div class="plain" id="plain">${EXPLAIN_ON ? SKEL() : ''}</div>
        <div class="fb" id="fb"></div>
        <details class="more" id="orig" style="margin-top:14px"><summary>${t('detail.orig')}</summary><div id="origBody" style="margin-top:6px"><p class="hint">${t('detail.opening')}</p></div></details>`;
      let check = '';
      const fbBox = $('#fb', el);
      renderFb(fbBox, sh, path, title, check);
      const plain = $('#plain', el);
      const showPlain = (x) => {
        check = x.check || '';
        plain.innerHTML = `<div class="ps">${esc(x.summary || title)}</div>
          ${x.why ? `<div class="pr"><span class="pi" style="background:var(--lemon-l)">💡</span><div><b>${t('detail.why')}</b><p>${esc(x.why)}</p></div></div>` : ''}
          ${x.when ? `<div class="pr"><span class="pi" style="background:var(--sky-l)">⏰</span><div><b>${t('detail.when')}</b><p>${esc(x.when)}</p></div></div>` : ''}
          ${(x.terms || []).length ? `<div class="terms">${x.terms.map((w) => `<span class="term">${esc(w.word)}<small>${esc(w.meaning)}</small></span>`).join('')}</div>` : ''}`;
        renderFb(fbBox, sh, path, title, check);
      };
      const doExplain = async () => {
        plain.innerHTML = SKEL();
        try { const x = await api('/api/explain?p=' + encodeURIComponent(path) + '&' + L()); if (el.isConnected) showPlain(x); }
        catch (e) { if (!el.isConnected) return; plain.innerHTML = `<div class="ps">${esc(title)}</div><p class="hint" style="margin:0">${t('detail.fail', { err: e.message.slice(0, 80) })}</p>`; $('#orig', el).open = true; }
      };
      if (EXPLAIN_ON) doExplain();
      else {
        plain.innerHTML = `<div class="ps">${esc(title)}</div><button class="btn sky small" id="doExp">${t('detail.explain')}</button>`;
        $('#doExp', el).addEventListener('click', doExplain);
        $('#orig', el).open = true;
      }
      try {
        const m = await api('/api/memory?p=' + encodeURIComponent(path));
        if (!el.isConnected) return;
        const s = m.strength || {};
        $('#origBody', el).innerHTML = `<p class="hint" style="margin:0 0 6px;word-break:break-all">${esc(m.path)}</p>
          <div class="chips"><span class="chip" data-tip="${esc(t('detail.mtime'))}">✏️ ${esc(fmtAgo(m.mtime))}</span><span class="chip" data-tip="${esc(t('detail.shown'))}">💭 ${s.shown || 0}</span><span class="chip" data-tip="${esc(t('detail.opened'))}">👀 ${s.opened || 0}</span><span class="chip" data-tip="${esc(t('detail.grepped'))}">🔍 ${s.grepped || 0}</span></div>
          <article class="md box">${md(m.text, m.path.split('/').slice(0, -1).join('/'))}</article>`;
        $$('[data-mem]', el).forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); memoryDetail(a.dataset.mem); }));
      } catch (e) { $('#origBody', el).innerHTML = `<div class="out">${esc(e.message)}</div>`; }
    },
  });
}

function renderFb(box, sh, path, title, check) {
  const cur = TRAY.items.find((x) => x.path === path);
  const on = (k) => (cur && cur.kind === k ? ' on' : '');
  box.innerHTML = `<div class="fq">🤔 ${esc(check || tp('fb.default'))}</div>
    <div class="fb-row"><button class="fbb${on('confirm')}" data-k="confirm">${t('fb.confirm')}</button><button class="fbb${on('outdated')}" data-k="outdated">${t('fb.outdated')}</button></div>
    <div class="fb-row"><button class="fbb sm${on('important')}" data-k="important">${t('fb.important')}</button><button class="fbb sm${on('forget')}" data-k="forget">${t('fb.forget')}</button></div>
    <div class="fb-text" hidden><textarea placeholder="${esc(t('fb.ph'))}" maxlength="1500">${cur && cur.kind === 'outdated' ? esc(cur.text) : ''}</textarea>
      <button class="btn small lav fb-put" style="margin-top:8px" data-tip="${esc(kbdTip(tp('fb.put.tip'), '⌘ Enter'))}">${t('fb.put')}</button></div>
    ${cur ? `<div class="fb-state">${t('fb.in', { what: FB_ICON[cur.kind] + ' ' + tp('fbk.' + cur.kind) })} <button class="fb-rm">${t('fb.rm')}</button></div>`
      : `<p class="hint" style="margin:10px 2px 0">${t('fb.hint')}</p>`}`;
  const put = async (kind, text) => {
    try {
      const r = await api('/api/feedback/add', { layer: CUR.layer, path, title, kind, text: text || '' });
      TRAY.items = r.items;
      updateTrayBar(true);
      toast(tp('fb.added', { n: r.items.length }));
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
    const v = $('.fb-text textarea', box).value.trim();
    if (!v) { toast(tp('fb.need')); return; }
    put('outdated', v);
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
    $('.tb-t', bar).textContent = tp('tray.bar', { n });
    if (bump) { bar.classList.remove('bump'); void bar.offsetWidth; bar.classList.add('bump'); }
  }
}
$('#trayBar').addEventListener('click', () => traySheet());
function traySheet() {
  const sh = openSheet({
    title: `<span>📮</span><span>${t('tray.title')}</span>`,
    kind: 'tray',
    body: (el) => {
      const draw = () => {
        el.innerHTML = `<p class="sub" style="margin-bottom:10px">${t('tray.sub')}</p>
          <div class="list">${TRAY.items.map((x) => `<div class="tray-item"><span class="ti-k">${FB_ICON[x.kind]}</span>
            <span style="min-width:0"><span class="ti-t">${esc(x.title || x.path)}</span><br><span class="ti-d">${t('fbk.' + x.kind)}${x.text ? ': ' + esc(x.text.slice(0, 60)) : ''}</span></span>
            <button class="x" data-id="${x.id}" aria-label="${esc(t('fb.rm'))}" data-tip="${esc(t('fb.rm'))}">✕</button></div>`).join('') || `<div class="empty"><span class="big">📭</span>${t('tray.empty')}</div>`}</div>`;
        $$('.x[data-id]', el).forEach((b) => b.addEventListener('click', async () => {
          try { TRAY.items = (await api('/api/feedback/remove', { layer: CUR.layer, id: b.dataset.id })).items; updateTrayBar(false); draw(); if (!TRAY.items.length) closeSheet(sh, true); }
          catch (e) { toast(e.message); }
        }));
      };
      draw();
    },
    foot: (el) => {
      el.innerHTML = `<button class="btn block" id="traySend" data-tip="${esc(kbdTip(tp('tray.send.tip'), '⌘ Enter'))}">${t('tray.send')}</button>`;
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
      if (!r.ok) { console.warn(r.out); throw new Error(tp('tray.fail')); }
      TRAY.items = [];
      updateTrayBar(false);
      closeSheet(sh, true);
      await wait(250);
      jump(); burst(['📮', '💌', '✨']); sayTemp(tp('tray.say'), 3200);
      toast(tp('tray.toast', { n: r.count }));
    } catch (e) { toast(e.message); b.disabled = false; }
  }
}

// ---------------------------------------------------------------- 시트: 물어보기 (뇌와 대화)
const CHATS = {};
function chatSheet() {
  const d = CUR;
  if (!d) return;
  const name = layerName(d.layer);
  const key = d.layer + '|' + LANG;
  const hist = CHATS[key] || (CHATS[key] = []);
  let busy = false;
  const av = () => `<span class="av">${pet('happy', d.stage.key === 'egg' ? 'baby' : d.stage.key)}</span>`;
  const sh = openSheet({
    title: `<span>💬</span><span>${t('chat.title', { name })}</span>`,
    full: true,
    kind: 'chat',
    body: (el) => { el.innerHTML = '<div class="chat" id="chat"></div>'; },
    foot: (el) => {
      el.innerHTML = `<div class="chat-in"><textarea id="chatIn" rows="1" placeholder="${esc(t('chat.ph'))}" maxlength="500" data-autofocus></textarea>
        <button class="send" id="chatGo" aria-label="${esc(t('chat.send'))}" data-tip="${esc(kbdTip(tp('chat.send'), 'Enter'))}">➤</button></div>
        <p class="hint" style="margin:6px 4px 0">${t('chat.hint')}</p>`;
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
  const sugs = topics.map((x) => ({ show: x.emoji + ' ' + tp('chat.sug.topic', { label: x.label }), q: tp('chat.sug.topic', { label: x.label }) }))
    .concat([tp('chat.sug.new'), tp('chat.sug.risk')].map((s) => ({ show: s, q: s.replace(/^\S+\s/, '') })));
  function draw() {
    const chat = $('#chat', sh.el);
    if (!chat) return;
    let html = `<div class="msg">${av()}<div class="bb">${t('chat.hello', { name })}</div></div>`;
    if (!hist.length) html += `<div class="sugs">${sugs.map((x, i) => `<button data-i="${i}">${esc(x.show)}</button>`).join('')}</div>`;
    hist.forEach((h) => {
      html += `<div class="msg me"><div class="bb">${esc(h.q)}</div></div>`;
      if (h.a != null) {
        html += `<div class="msg">${av()}<div class="bb">${inlineCode(h.a)}${(h.refs || []).length ? `<div class="refs">${h.refs.map((r) => `<button data-path="${esc(r.path)}" data-tip="${esc(t('chat.ref.tip'))}">📖 ${esc(r.title)}</button>`).join('')}</div>` : ''}</div></div>`;
      }
    });
    if (busy) html += `<div class="msg">${av()}<div class="bb"><span class="typing"><i></i><i></i><i></i></span></div></div>`;
    chat.innerHTML = html;
    $$('.sugs button', chat).forEach((b) => b.addEventListener('click', () => send(sugs[+b.dataset.i].q)));
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
      const r = await api('/api/ask', { layer: d.layer, q, lang: LANG, history: hist.filter((h) => h.a && !h.err).slice(-3).map((h) => ({ q: h.q, a: h.a })) });
      turn.a = r.answer; turn.refs = r.refs || [];
    } catch (e) { turn.a = tp('chat.err', { err: e.message.slice(0, 100) }); turn.err = true; }
    busy = false;
    if (sh.el.isConnected) { draw(); ta.focus(); }
  }
  draw();
}

// ---------------------------------------------------------------- 시트: 성격 (노드 에디터)
const BREED_ICON = { squirrel: '🐿️', owl: '🦉', cat: '🐱', turtle: '🐢' };
const breedIcon = (b) => BREED_ICON[b] || '🎭';
const LVW = () => [tp('p.lv1'), tp('p.lv2'), tp('p.lv3')];
function friendlyHtml(eff, cat) {
  const order = Object.keys(cat.situations);
  const gates = new Set(cat.gates);
  const rows = order.filter((s) => eff && eff[s] && Object.keys(eff[s]).length).map((s) => {
    const sit = cat.situations[s];
    const items = Object.entries(eff[s]).sort((a, b) => b[1] - a[1]).map(([k, lv]) => {
      const tr = cat.traits[k];
      const lock = lv >= 3 && gates.has(k + '+' + s);
      return `<span class="fc${lock ? ' lock' : ''}">${tr.icon} ${esc((cat.special_short && cat.special_short[k + '+' + s]) || tr.short)}${lock ? ' 🔒' : ''}</span>`;
    }).join(' ');
    return `<div class="fl"><span class="fh">${sit.icon} ${s === 'normal' ? t('p.normal') : t('p.sitpre', { name: sit.short })}</span>${items}</div>`;
  });
  return rows.join('');
}
let P = null;
let previewTimer = 0;
let nid = 0;
const newId = (p) => p + Date.now().toString(36) + (nid++);

async function personaSheet(slug) {
  if (P) return;   // 이미 열려 있다
  let r;
  try { r = await api('/api/persona?slug=' + encodeURIComponent(slug) + '&' + L()); } catch (e) { toast(e.message); return; }
  const g = r.graph || { version: 1, breed: '', name: '', enabled: true, nodes: [], edges: [], verify_re: '', big_files: 5 };
  P = { slug, graph: g, cat: r.catalog, compiled: r.compiled, dirty: false, saved: !!r.graph, picked: null, armed: false, focusId: null };
  ensureHub();
  const cat = P.cat;
  const sh = openSheet({
    title: `<span>🎭</span><span>${t('p.title')}</span>`,
    full: true,
    kind: 'persona',
    beforeClose: () => {
      if (!P || !P.dirty || P.armed) return true;
      P.armed = true;
      toast(tp('p.dirty'), 3000);
      setTimeout(() => { if (P) P.armed = false; }, 3000);
      return false;
    },
    onClose: () => { if (P && P.dirty) toast(tp('p.dropped')); P = null; },
    body: (el) => {
      el.innerHTML = `
        <p class="sub" style="margin-bottom:10px">${t('p.sub')}</p>
        <div class="now" id="pNow"></div>
        <div class="breeds">${Object.entries(cat.breeds).map(([k, b]) => `<button class="breed${g.breed === k ? ' on' : ''}" data-b="${k}" data-tip="${esc(t('p.breed.tip', { fit: b.fit }))}">
          <span class="bi">${b.icon}</span><div class="bn">${esc(b.name)}</div><div class="bd">${esc(b.desc)}</div></button>`).join('')}</div>
        <details class="more custom" id="pCustom" ${!g.breed && g.nodes.some((n) => n.kind === 'trait') ? 'open' : ''}><summary>${t('p.custom')}</summary>
        <div class="hint" style="margin:2px 2px 6px">${t('p.custom.hint')}</div>
        <div class="canvas" id="canvas" aria-label="${esc(t('p.canvas'))}"><svg class="wires" id="wires"></svg></div>
        <div class="h2" style="margin-top:18px">${t('p.addtrait')} <small>${t('p.addtrait.hint')}</small></div>
        <div class="axes">${cat.axes.map((a) => `<div class="axis">
          ${[a.left, a.right].map((k, i) => `${i ? '<span class="vs">↔</span>' : ''}<button data-add="trait" data-k="${k}" data-tip="${esc(cat.traits[k].firm)}">${cat.traits[k].icon} ${esc(cat.traits[k].name)}</button>`).join('')}</div>`).join('')}</div>
        <div class="h2">${t('p.addsit')} <small>${t('p.addsit.hint')}</small></div>
        <div class="sits">${Object.entries(cat.situations).filter(([k]) => k !== 'normal').map(([k, s]) =>
          `<button data-add="situation" data-k="${k}" data-tip="${esc(t('p.sittip.' + k))}">${s.icon} ${esc(s.name)}${s.forceable ? ' 🔒' : ''}</button>`).join('')}</div>
        <div class="h2">${t('p.raw')}</div>
        <div id="pPreview"></div>
        <details class="more" style="margin-top:14px"><summary>${t('p.more')}</summary>
          <div class="box" style="margin-top:6px">
            <div class="set"><div><div class="st">${t('p.on')}</div><div class="sd">${t('p.on.d')}</div></div>
              <label class="switch"><input type="checkbox" id="pEnabled" ${g.enabled !== false ? 'checked' : ''}><span></span></label></div>
            <label class="field">${t('p.name')}<input class="input" id="pName" value="${esc(g.name || '')}" placeholder="${esc(t('p.name.ph'))}" maxlength="40"></label>
            <label class="field">${t('p.big')}<input class="input" id="pBig" type="number" min="2" max="50" value="${g.big_files || 5}"></label>
            <label class="field">${t('p.verify')}<input class="input" id="pVerify" value="${esc(g.verify_re || '')}" placeholder="${esc(t('p.verify.ph'))}"></label>
            ${P.saved ? `<button class="btn soft small" id="pDel" style="margin-top:12px;color:var(--bad)">${t('p.del')}</button>` : ''}
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
        if (del.dataset.sure !== '1') { del.dataset.sure = '1'; del.textContent = tp('p.del.sure'); setTimeout(() => { del.dataset.sure = ''; del.textContent = tp('p.del'); }, 3000); return; }
        try { await api('/api/persona/delete', { slug }); P.dirty = false; closeSheet(sh, true); toast(tp('p.deleted')); route(); } catch (e) { toast(e.message); }
      });
      // 빈 곳을 누르면 고른 성향이 풀린다
      el.addEventListener('click', (e) => { if (P && P.picked && !e.target.closest('.node, [data-add], .port')) { P.picked = null; drawGraph(); } });
    },
    foot: (el) => {
      el.innerHTML = `<button class="btn lav block" id="pSave" data-tip="${esc(kbdTip(tp('p.save.tip'), '⌘ S'))}">${t('p.save')}</button>`;
      $('#pSave', el).addEventListener('click', save);
    },
  });
  async function save() {
    if (!P) return;
    const btn = $('#pSave', sh.el);
    if (btn.disabled) return;
    btn.disabled = true;
    try {
      const r2 = await api('/api/persona/save', { slug, graph: P.graph, lang: LANG });
      P.dirty = false;
      closeSheet(sh, true);
      toast(tp('p.saved', { icon: breedIcon(r2.graph.breed) }), 3200);
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
    const r = await api('/api/breed?b=' + k + '&' + L());
    if (!P) return;
    const keep = { enabled: P.graph.enabled, verify_re: P.graph.verify_re, big_files: P.graph.big_files };
    P.graph = Object.assign(r.graph, keep);
    P.picked = null;
    ensureHub();
    $$('.breed', P.sheet.el).forEach((b) => b.classList.toggle('on', b.dataset.b === k));
    $('#pName', P.sheet.el).value = P.graph.name || '';
    drawGraph(); changed();
    toast(tp('p.breed.loaded', { icon: breedIcon(k), name: r.graph.name }));
  } catch (e) { toast(e.message); }
}
function addNode(kind, k) {
  const g = P.graph;
  if (kind === 'situation') {
    const ex = g.nodes.find((n) => n.kind === 'situation' && n.situation === k);
    if (ex) { toast(tp('p.sit.exists')); flashNode(ex.id); return; }
    const n = { id: newId('s'), kind: 'situation', situation: k, x: 0, y: 0 };
    g.nodes.push(n);
    if (P.picked) { connect(P.picked, n.id); toast(tp('p.sit.linked')); }
  } else {
    const n = { id: newId('t'), kind: 'trait', trait: k, level: 2, x: 0, y: 0 };
    g.nodes.push(n);
    P.picked = n.id;   // 바로 이을 수 있게 골라 둔다
    toast(tp('p.pick'));
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
    .map((n, i) => ({ n, i, k: Math.min(99, ...g.edges.filter((e) => e.from === n.id).map((e) => sIdx(e.to)).filter((x) => x >= 0)) }))
    .sort((a, b) => a.k - b.k || a.i - b.i).map((x) => x.n);
  const ROW = 96, SROW = 78, TOPY = 16;
  traits.forEach((n, i) => { n.x = 14; n.y = TOPY + i * ROW; });
  let last = -1e9;
  sits.forEach((s, i) => {
    const ys = g.edges.filter((e) => e.to === s.id).map((e) => g.nodes.find((n) => n.id === e.from)).filter(Boolean).map((n) => n.y + 10);
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
  const W3 = LVW();
  g.nodes.forEach((n) => {
    const el = document.createElement('div');
    el.dataset.id = n.id;
    el.tabIndex = 0;
    el.style.left = n.x + 'px'; el.style.top = n.y + 'px';
    if (n.kind === 'trait') {
      const tr = cat.traits[n.trait];
      el.className = 'node trait' + (P.picked === n.id ? ' picked' : '') + (linked.has(n.id) ? '' : ' loose');
      el.setAttribute('role', 'button');
      el.setAttribute('aria-label', `${tr.name} ${tp('p.lv.aria', { w: W3[n.level - 1] })}`);
      el.dataset.tip = `${esc(n.level >= 2 ? tr.firm : tr.soft)}<br><span style="opacity:.7">${t('p.node.keys')}</span>`;
      el.innerHTML = `<button class="x" aria-label="${esc(t('p.node.rm'))}" tabindex="-1">✕</button>
        <div class="nt"><span class="ic">${tr.icon}</span>${esc(tr.name)}</div>
        <div class="ns">${linked.has(n.id) ? esc(tr.short) : t('p.node.loose')}</div>
        <div class="lvw">${[1, 2, 3].map((l) => `<button class="${l === n.level ? 'on' : ''}${l === 3 ? ' l3' : ''}" data-l="${l}" tabindex="-1" aria-label="${esc(t('p.lv.aria', { w: W3[l - 1] }))}" data-tip="${esc(t('p.lv' + l + '.tip'))}">${esc(W3[l - 1])}</button>`).join('')}</div>
        <span class="port" data-tip="${esc(t('p.node.out'))}"></span>`;
    } else {
      const s = cat.situations[n.situation];
      el.className = 'node sit' + (n.situation === 'normal' ? ' hub' : '') + (P.picked ? ' target' : '');
      el.setAttribute('role', 'button');
      el.setAttribute('aria-label', s.name);
      el.dataset.tip = t('p.sittip.' + n.situation) + (P.picked ? '<br>' + t('p.sit.click') : '');
      el.innerHTML = `${n.situation === 'normal' ? '' : `<button class="x" aria-label="${esc(t('p.node.rm'))}" tabindex="-1">✕</button>`}
        <div class="nt"><span class="ic">${s.icon}</span>${esc(s.name)}</div>
        <div class="ns">${n.situation === 'normal' ? t('p.sit.always') : s.forceable ? `<span class="lock">${t('p.sit.lock')}</span>` : t('p.sit.model')}</div>
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
    return a && b ? `<path class="${lv(e.from) === 3 ? 'strong' : ''}" d="${curve(a, b)}" data-i="${i}"><title>${t('p.wire')}</title></path>` : '';
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
      if (!moved) { P.picked = P.picked === n.id ? null : n.id; drawGraph(); if (P.picked) toast(tp('p.pick')); return; }
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
    try { const c = (await api('/api/persona/preview', { graph: mine.graph, lang: LANG })).compiled; if (P === mine) { P.compiled = c; renderPreview(); } } catch (e) { /* 저장 때 다시 확인된다 */ }
  }, ms);
}
function renderPreview() {
  const el = $('#pPreview');
  if (!el || !P || !P.compiled) return;
  const c = P.compiled;
  const now = $('#pNow');
  if (now) {
    const f = friendlyHtml(c.effective, P.cat);
    now.innerHTML = `<div class="nh">${t(P.dirty ? 'p.now.dirty' : P.saved ? 'p.now.saved' : 'p.now.base')}</div>
      ${f || `<p class="hint" style="margin:0">${t('p.now.empty')}</p>`}
      ${c.enabled === false ? `<p class="hint" style="margin:6px 0 0;color:var(--bad)">${t('p.now.off')}</p>` : ''}
      ${Object.keys(c.gate_notes || {}).length ? `<p class="hint" style="margin:6px 0 0">${t('p.now.lock')}</p>` : ''}`;
  }
  const gates = Object.values(c.gate_notes || {});
  el.innerHTML = `${(c.warnings || []).map((w) => `<div class="warn">⚠️ ${esc(w)}</div>`).join('')}
    <div class="say-box">
      <div class="k" style="margin-top:0">${t('p.raw.start')}</div><pre>${esc(c.session || tp('p.raw.start.none'))}</pre>
      <div class="k">${t('p.raw.turn')}</div><pre>${esc(c.turn || tp('p.raw.turn.none'))}</pre>
      <div class="k">${t('p.raw.gate')}</div>${gates.length ? gates.map((v) => `<div class="gate">• ${esc(v)}</div>`).join('') : `<pre>${t('p.raw.gate.none')}</pre>`}
    </div>
    ${c.enabled === false ? `<div class="warn" style="margin-top:8px">${t('p.raw.off')}</div>` : ''}`;
}

// ---------------------------------------------------------------- 해마 일지
async function pageJournal(alive) {
  let h;
  try { h = await api('/api/hippo'); } catch (e) { if (alive()) screen.innerHTML = noConn(); return; }
  if (!alive()) return;
  document.title = 'brain - ' + tp('j.title');
  const rs = h.results.slice(-40).reverse();
  const counts = {};
  h.results.forEach((r) => { counts[r.status] = (counts[r.status] || 0) + 1; });
  const who = (r) => (r.slug && r.slug !== '-' ? r.slug : tp('shared'));
  screen.innerHTML = `
    <div class="top"><div class="jua" style="font-size:28px">${t('j.title')}</div></div>
    <div class="card hippo${h.alive ? ' busy' : ''}"><div class="av">${h.alive ? '✍️' : '😴'}</div>
      <div><div class="jua" style="font-size:20px">${t(h.alive ? 'j.busy' : 'j.idle')}</div>
      <div class="hint">${h.alive && h.current ? esc(h.current.slice(0, 60)) + '<br>' : ''}${t('j.stats', { q: h.queue.length, n: h.results.length, ok: counts.done || 0, bad: (counts.failed || 0) + (counts.timeout || 0) + (counts.denied || 0) })}</div></div></div>
    ${h.alive || h.queue.length ? `<div class="j-ctl">
      ${h.alive ? (h.stopping ? `<span class="pill">${t('j.stopping')}</span>` : `<button class="btn soft small" id="jStop" data-tip="${esc(t('j.stop.tip'))}">${t('j.stop')}</button>`) : ''}
      ${h.queue.length ? `<button class="btn soft small" id="jClear" data-tip="${esc(t('j.clear.tip'))}">${t('j.clear', { n: h.queue.length })}</button>` : ''}</div>` : ''}
    ${h.queue.length ? `<div class="h2">${t('j.wait')} <small>${t('j.wait.n', { n: h.queue.length })}</small></div><div class="chips">${h.queue.map((x) => `<span class="chip">${esc(who(x) + ' ' + modeName(x.mode))}</span>`).join('')}</div>` : ''}
    <p class="sub" style="margin-top:12px">${t('j.sub')}</p>
    <div class="list" id="entries">${rs.map((r, i) => `<button class="entry" data-i="${i}"><span class="st ${esc(r.status)}">${ST_ICON[r.status] || '📝'}</span>
      <span style="min-width:0"><span class="et">${esc(who(r))} ${esc(modeName(r.mode))}</span>
      <span class="ed">${esc(r.first)}</span><span class="hint">${esc((r.finished || '').replace('T', ' ').slice(5, 16))}</span></span></button>`).join('') ||
      `<div class="empty"><span class="big">📓</span>${t('j.empty')}<br><span class="hint">${t('j.empty.hint')}</span></div>`}</div>`;
  const jStop = $('#jStop');
  if (jStop) jStop.addEventListener('click', async () => {
    jStop.disabled = true;
    try { await api('/api/hippo/stop', {}); toast(tp('j.stop.done')); setTimeout(route, 600); } catch (e) { toast(e.message); jStop.disabled = false; }
  });
  const jClear = $('#jClear');
  if (jClear) jClear.addEventListener('click', async () => {
    if (jClear.dataset.sure !== '1') { jClear.dataset.sure = '1'; jClear.textContent = tp('j.clear.sure'); setTimeout(() => { if (jClear.isConnected) { jClear.dataset.sure = ''; jClear.textContent = tp('j.clear', { n: h.queue.length }); } }, 3000); return; }
    jClear.disabled = true;
    try { const r = await api('/api/hippo/clear', {}); toast(tp('j.clear.done', { n: r.moved })); setTimeout(route, 600); } catch (e) { toast(e.message); jClear.disabled = false; }
  });
  $$('#entries .entry').forEach((b) => b.addEventListener('click', () => {
    const r = rs[+b.dataset.i];
    openSheet({ title: `<span>${ST_ICON[r.status] || '📝'}</span><span>${esc(modeName(r.mode))}</span>`, full: true,
      body: (el) => { el.innerHTML = `<p class="hint">${esc(r.id)}</p><div class="box md">${md(r.summary || tp('j.nosum'))}</div>`; } });
  }));
}

// ---------------------------------------------------------------- 설정
async function pageSettings(alive) {
  const ov = await loadOverview();
  if (!alive()) return;
  if (!ov) { screen.innerHTML = noConn(); return; }
  document.title = 'brain - ' + tp('s.title');
  const c = ov.config;
  const preset = c.model === 'claude-sonnet-5-5' && c.effort === 'medium' ? 'default'
    : c.model === 'claude-sonnet-5-5' && c.effort === 'low' ? 'eco' : c.model === 'claude-opus-5-5' && c.effort === 'high' ? 'quality' : '';
  const kb = (k) => `<span class="kbd">${k}</span>`;
  screen.innerHTML = `
    <div class="top"><div class="jua" style="font-size:28px">${t('s.title')}</div></div>
    <div class="card set"><div><div class="st">${t('s.on')}</div><div class="sd">${t('s.on.d')}</div></div>
      <label class="switch"><input type="checkbox" id="sOn" ${c.enabled ? 'checked' : ''} aria-label="${esc(t('s.on'))}"><span></span></label></div>
    <div class="h2">${t('s.lang')}</div>
    <div class="card"><div class="seg" id="sLang">${LANGS.map((l) => `<button data-l="${l}" class="${l === LANG ? 'on' : ''}">${esc(I18N[l]['lang.name'])}</button>`).join('')}</div>
      <p class="hint" style="margin:10px 2px 0">${t('s.lang.d')}</p></div>
    <div class="h2">${t('s.head')} <small>${esc(c.model.replace('claude-', ''))}, ${esc(c.effort)}</small></div>
    <div class="card"><div class="seg" id="sPreset">
      <button data-p="eco" class="${preset === 'eco' ? 'on' : ''}" data-tip="${esc(t('s.eco.tip'))}">${t('s.eco')}</button><button data-p="default" class="${preset === 'default' ? 'on' : ''}" data-tip="${esc(t('s.def.tip'))}">${t('s.def')}</button><button data-p="quality" class="${preset === 'quality' ? 'on' : ''}" data-tip="${esc(t('s.q.tip'))}">${t('s.q')}</button></div>
      <p class="hint" style="margin:10px 2px 0">${t('s.head.d')}</p></div>
    <div class="h2">${t('s.sleep.h')}</div>
    <div class="card set"><div><div class="st">${t('s.sleep')}</div><div class="sd">${t('s.sleep.d', { when: c.last_sleep ? fmtAgo(c.last_sleep) : tp('s.sleep.never') })}</div></div>
      <button class="btn sky small" id="sSleep">${t('s.sleep.btn')}</button></div>
    <div class="h2">${t('us.h')}</div>
    <div class="card">${['week', 'month'].map((k) => { const u = (ov.usage || {})[k] || {}; return `<div class="set us-row"><div><div class="st">${t('us.' + k)}</div>
      <div class="sd">${u.runs ? t('us.line', { h: num(u.hippo), a: num(u.app) }) : t('us.none')}</div></div><b class="us-cost">${u.runs ? t('us.cost', { c: (u.cost || 0).toFixed(2) }) : ''}</b></div>`; }).join('')}
      <p class="hint" style="margin:8px 2px 0">${t('us.hint')}</p></div>
    <div class="h2">${t('bk.h')}</div>
    <div class="card"><div class="set"><div><div class="st">${t('bk.t')}</div><div class="sd">${t('bk.d')}</div></div>
      <button class="btn mint small" id="sBackup">${t('bk.btn')}</button></div><div id="bkOut"></div></div>
    <div class="h2">${t('s.view')}</div>
    <div class="card set"><div><div class="st">${t('s.explain')}</div><div class="sd">${t('s.explain.d')}</div></div>
      <label class="switch"><input type="checkbox" id="sExplain" ${EXPLAIN_ON ? 'checked' : ''} aria-label="${esc(t('s.explain'))}"><span></span></label></div>
    <div class="h2">${t('s.screen')}</div>
    <div class="card"><div class="seg" id="sTheme"><button data-t="auto">${t('s.auto')}</button><button data-t="light">${t('s.light')}</button><button data-t="dark">${t('s.dark')}</button></div></div>
    <div class="h2">${t('s.keys')}</div>
    <div class="card" style="font-size:13px;line-height:2">
      ${kb('1')}${kb('2')}${kb('3')} ${t('s.keys.tabs')}<br>
      ${t('s.keys.proj')} ${kb('C')} ${t('s.keys.ask')} ${kb('F')} ${t('s.keys.feed')} ${kb('O')} ${t('s.keys.opt')} ${kb('P')} ${t('s.keys.persona')} ${kb('M')} ${t('s.keys.mem')}<br>
      ${kb('Esc')} ${t('s.keys.esc')} ${kb('⌘ Enter')} ${t('s.keys.send')} ${kb('⌘ S')} ${t('s.keys.save')}</div>
    <div class="card set" style="margin-top:20px"><div><div class="st">${t('s.quit')}</div><div class="sd">${t('s.quit.d')}</div></div>
      <button class="btn soft small" id="sQuit">${t('s.quit.btn')}</button></div>
    <button class="btn soft small" id="sWelcome" style="margin:16px auto 0;display:flex">${t('s.welcome')}</button>
    <p class="hint center" style="margin-top:20px">${t('s.foot')}${c.version ? '<br>' + t('s.ver', { v: c.version }) : ''}</p>`;
  $('#sBackup').addEventListener('click', async (e) => {
    const b = e.target; b.disabled = true;
    try {
      const r = await api('/api/backup', {});
      $('#bkOut').innerHTML = `<p class="hint" style="margin:10px 2px 4px">✅ ${t('bk.done')} (${num(r.n)})</p>${copyBox(r.path)}
        <p class="hint" style="margin:10px 2px 4px">${t('bk.restore')}</p>${copyBox(r.restore)}`;
      bindCopy($('#bkOut'));
      toast(tp('bk.done'));
    } catch (err) { toast(err.message); }
    b.disabled = false;
  });
  $('#sOn').addEventListener('change', async (e) => {
    try { await api('/api/config', { action: e.target.checked ? 'on' : 'off' }); toast(tp(e.target.checked ? 'toast.on' : 'toast.off')); }
    catch (err) { toast(err.message); e.target.checked = !e.target.checked; }
  });
  $$('#sLang button').forEach((b) => b.addEventListener('click', async () => {
    if (b.dataset.l === LANG) return;
    try { await api('/api/config', { action: 'lang', value: b.dataset.l }); setLang(b.dataset.l); toast(tp('s.lang.toast')); route(); }
    catch (e) { toast(e.message); }
  }));
  $$('#sPreset button').forEach((b) => b.addEventListener('click', async () => {
    try { await api('/api/config', { action: 'preset', value: b.dataset.p }); $$('#sPreset button').forEach((x) => x.classList.toggle('on', x === b)); toast(tp('s.head.toast')); }
    catch (e) { toast(e.message); }
  }));
  $('#sSleep').addEventListener('click', async (e) => {
    e.target.disabled = true;
    try { await api('/api/sleep', {}); toast(tp('toast.sleep')); } catch (err) { toast(err.message); }
    setTimeout(() => { e.target.disabled = false; }, 3000);
  });
  $('#sExplain').addEventListener('change', (e) => {
    EXPLAIN_ON = e.target.checked;
    try { localStorage.setItem('brainExplain', EXPLAIN_ON ? 'on' : 'off'); } catch (err) { /* 이번만 적용 */ }
    toast(tp(EXPLAIN_ON ? 's.explain.on' : 's.explain.off'));
  });
  $('#sWelcome').addEventListener('click', welcomeSheet);
  $('#sQuit').addEventListener('click', async (e) => {
    const b = e.target;
    if (b.dataset.sure !== '1') { b.dataset.sure = '1'; b.textContent = tp('s.quit.sure'); setTimeout(() => { b.dataset.sure = ''; b.textContent = tp('s.quit.btn'); }, 3000); return; }
    try { await api('/api/quit', {}); } catch (err) { /* 이미 꺼졌다 */ }
    screen.innerHTML = `<div class="empty" style="padding-top:140px"><span class="big">👋</span>${t('s.quit.done')}<br><span class="hint">/claude-brain-app</span></div>`;
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
function welcomeSheet() {
  let i = 0;
  const pages = [{ i: '🧠', k: 'w.1' }, { i: '💬', k: 'w.2' }, { i: '🍙', k: 'w.3' }];
  const done = () => { try { localStorage.setItem('brainWelcomed', '1'); } catch (e) { /* 다음에 또 보여도 괜찮다 */ } };
  const sh = openSheet({
    title: `<span>👋</span><span>${t('w.title')}</span>`,
    kind: 'welcome',
    onClose: done,
    body: (el) => { el.innerHTML = '<div class="welcome" id="wel"></div>'; },
    foot: (el) => {
      el.innerHTML = `<div class="row" style="display:flex;gap:8px"><button class="btn soft small" id="wSkip" style="flex:none">${t('w.skip')}</button><button class="btn block" id="wNext" data-autofocus></button></div>`;
      $('#wSkip', el).addEventListener('click', () => closeSheet(sh));
      $('#wNext', el).addEventListener('click', () => { if (i < pages.length - 1) { i++; draw(); } else closeSheet(sh); });
    },
  });
  sh.submit = () => $('#wNext', sh.el).click();
  function draw() {
    const w = pages[i];
    $('#wel', sh.el).innerHTML = `<span class="wi">${w.i}</span><div class="wt">${t(w.k + '.t')}</div><p class="wd">${t(w.k + '.d')}</p>
      <div class="dots">${pages.map((x, k) => `<i class="${k === i ? 'on' : ''}"></i>`).join('')}</div>`;
    $('#wNext', sh.el).textContent = tp(i < pages.length - 1 ? 'w.next' : 'w.start');
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
  const sig = ov ? JSON.stringify([ov.hippo, ov.queue, ov.config.enabled, ov.config.lang, ov.projects.map((p) => [p.count, p.mood.key, p.capacity, !!p.persona])]) : '';
  if (sig && sig !== lastSig) { if (lastSig) { if (ov.config.lang !== LANG) setLang(ov.config.lang); route(); } lastSig = sig; }
}, 10000);

// 맡긴 일이 끝나면 한 번 알린다(먹이, 우체통, 정리, 등록). 알린 것은 서버에 확인해 다시 뜨지 않게 한다
async function checkApplied() {
  if (document.hidden || !TOKEN) return;
  let r;
  try { r = await api('/api/applied'); } catch (e) { return; }
  const done = (r.done || []).slice(0, 3);
  if (!done.length) return;
  done.forEach((x, i) => setTimeout(() => {
    const head = x.status !== 'done' ? tp('ap.fail') : x.kind === 'tidy' && x.before != null && x.after != null ? tp('ap.tidy.w', { b: pct(x.before), a: pct(x.after) })
      : tp('ap.' + (I18N.ko['ap.' + x.kind] ? x.kind : 'tidy'), { n: x.n, slug: x.slug });
    toast(x.first && x.status === 'done' && x.first !== '(dry-run)' ? head + '\n' + x.first : head, 5200);
    if (x.status === 'done' && i === 0 && $('#stage')) { jump(); burst(['✨', '💡']); }
  }, i * 5600));
  try { await api('/api/applied/ack', { keys: done.map((x) => x.key) }); } catch (e) { /* 다음에 다시 알린다 */ }
  if (done.some((x) => x.kind === 'register') && !CUR && !SHEETS.length) setTimeout(route, 800);
}
setInterval(checkApplied, 15000);

// 시작 - 언어(brain 설정, 없으면 브라우저 언어)를 먼저 정하고 그린다
(async function boot() {
  setLang(navLang());
  if (TOKEN) { await loadOverview(); if (OV && OV.config && OV.config.lang) setLang(OV.config.lang); }
  route();
})();
