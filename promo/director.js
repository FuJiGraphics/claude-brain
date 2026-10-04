'use strict';
// 홍보 영상 연출 - 앱(iframe)을 가짜 커서로 직접 눌러 가며 장면을 넘긴다. record.py 가 화면을 녹화한다.
// window.__ready (앱 준비) → window.__go (녹화 시작 신호) → 장면들 → window.__done
const $ = (s, el = document) => el.querySelector(s);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const frame = $('#app');
const SCALE = 0.84;
const F = () => frame.contentDocument;
const FW = () => frame.contentWindow;
const q = (s) => F().querySelector(s);
const qa = (s) => Array.from(F().querySelectorAll(s));
async function until(fn, ms = 15000) { const end = Date.now() + ms; while (Date.now() < end) { try { const v = fn(); if (v) return v; } catch (e) { /* 아직 */ } await sleep(60); } return null; }

const Q = new URLSearchParams(location.search);
const T = Q.get('t') || '';
const LANG = ['ko', 'en', 'ja', 'zh'].includes(Q.get('lang')) ? Q.get('lang') : 'ko';
document.documentElement.dataset.lang = LANG;
document.documentElement.lang = { ko: 'ko', en: 'en', ja: 'ja', zh: 'zh-CN' }[LANG];
// 장면 자막 - [작은 표, 제목(HTML), 설명]
const C = {
  ko: { tag: 'Claude Code 에 장기 기억을 달아 주세요', ask: '세이브 구조 바꿀 때 조심할 거 있어?', s: [
    ['🧠 brain', '프로젝트마다<br><span class="hl">뇌가 하나씩</span> 자라요', 'Claude Code 가 일하면서 배운 걸\n알아서 기억하고, 알아서 떠올려요'],
    ['💬 한눈에', '말풍선은<br>이 뇌가 <span class="hl">아끼는 것</span>', '무엇을 중요하게 기억하는지\n단어로 바로 보여요'],
    ['📖 쉬운 말', 'AI 가 남긴 메모를<br><span class="hl">쉬운 말</span>로', '왜 기억하는지, 언제 떠올리는지\n어려운 낱말까지 풀어 줘요'],
    ['📮 피드백', '맞는지 답만 하면<br><span class="hl">피드백 끝</span>', '우체통에 모았다가\n한 번에 해마에게 보내요'],
    ['🗣️ 물어보기', '궁금하면<br><span class="hl">뇌한테 물어보세요</span>', '자기 기억 안에서만,\n근거를 달아서 대답해요'],
    ['✨ 최적화', '머리가 꽉 차면<br><span class="hl">해마가 정리</span>해요', '겹친 건 합치고, 긴 건 줄이고\n지우지 않고 보관해요'],
    ['🎭 성격', '일하는 성격도<br><span class="hl">골라 주세요</span>', '🔒 꼭 지켜야 할 건\n앱이 대신 지켜요']] },
  en: { tag: 'Give Claude Code a long-term memory', ask: 'Anything to watch out for when changing the save format?', s: [
    ['🧠 brain', 'Every project grows<br><span class="hl">its own brain</span>', 'Claude Code remembers what it learns\nand recalls it when it matters'],
    ['💬 At a glance', 'Bubbles show<br>what it <span class="hl">cares about</span>', 'What this brain values,\nin just a few words'],
    ['📖 Plain words', 'AI notes,<br>in <span class="hl">plain words</span>', 'Why it remembers, when it recalls,\neven the jargon explained'],
    ['📮 Feedback', 'Just answer<br><span class="hl">yes or no</span>', 'Feedback piles up in a mailbox\nand goes out all at once'],
    ['🗣️ Ask', 'Curious?<br><span class="hl">Ask the brain</span>', 'Answers only from its memories,\nwith sources attached'],
    ['✨ Tidy up', 'Head too full?<br><span class="hl">It tidies up</span>', 'Merges overlaps, trims long ones,\narchives instead of deleting'],
    ['🎭 Persona', 'Choose how<br><span class="hl">it works</span>', '🔒 Must-keep rules\nare enforced by the app']] },
  ja: { tag: 'Claude Code に長期記憶を', ask: 'セーブ形式を変えるとき、気をつけることある?', s: [
    ['🧠 brain', 'プロジェクトごとに<br><span class="hl">脳がひとつ</span>育つ', 'Claude Code が働きながら学んだことを\n自分で覚えて、自分で思い出す'],
    ['💬 ひと目で', '吹き出しは<br>この脳が<span class="hl">大事にするもの</span>', '何を大切に覚えているか\n言葉ですぐわかる'],
    ['📖 わかりやすく', 'AI のメモを<br><span class="hl">やさしい言葉</span>で', 'なぜ覚えるのか、いつ思い出すのか\n難しい言葉まで説明'],
    ['📮 フィードバック', '合っているか<br><span class="hl">答えるだけ</span>', 'ポストに集めて\nまとめて海馬に届ける'],
    ['🗣️ 質問', '気になったら<br><span class="hl">脳に聞いてみて</span>', '自分の記憶の中だけで、\n根拠つきで答える'],
    ['✨ 整理', '頭がいっぱいなら<br><span class="hl">海馬が整理</span>', '重なりはまとめ、長いものは縮め\n消さずに保管'],
    ['🎭 性格', '働く性格も<br><span class="hl">選べる</span>', '🔒 必ず守ることは\nアプリが代わりに守らせる']] },
  zh: { tag: '给 Claude Code 装上长期记忆', ask: '改存档格式时要注意什么?', s: [
    ['🧠 brain', '每个项目都会<br>长出<span class="hl">一个大脑</span>', 'Claude Code 会自己记住工作中学到的,\n需要时自己想起来'],
    ['💬 一目了然', '气泡是<br>这个大脑<span class="hl">珍视的东西</span>', '它重视什么,\n几个词就看得出'],
    ['📖 简单易懂', 'AI 写的笔记<br>换成<span class="hl">简单的话</span>', '为什么记住、什么时候想起,\n连难懂的词都解释'],
    ['📮 反馈', '只要回答<br><span class="hl">对不对</span>', '反馈放进信箱,\n一次性交给海马'],
    ['🗣️ 提问', '好奇的话<br><span class="hl">问问大脑</span>', '只根据自己的记忆,\n附上依据来回答'],
    ['✨ 整理', '脑袋满了<br><span class="hl">海马来整理</span>', '合并重复、精简冗长,\n不删除而是归档'],
    ['🎭 性格', '工作性格<br>也能<span class="hl">挑选</span>', '🔒 必须遵守的事\n由应用替它守住']] },
}[LANG];
const S = (i) => cap(C.s[i][0], C.s[i][1], C.s[i][2]);
try {
  localStorage.setItem('brainWelcomed', '1');
  localStorage.setItem('brainTheme', 'light');
  localStorage.setItem('brainExplain', 'on');
  localStorage.setItem('brainCoach', '1');   // 영상에서는 말풍선 안내 대신 뇌의 한마디를 보인다
} catch (e) { /* 촬영용 */ }
frame.src = '/?t=' + encodeURIComponent(T) + '#/';

// ---------------------------------------------------------------- 커서
const cur = $('#cursor');
let cx = 1100, cy = 760;
function local(x, y) { const fr = frame.getBoundingClientRect(); return { x: (x - fr.left) / SCALE, y: (y - fr.top) / SCALE }; }
function feedEyes(x, y) {
  const l = local(x, y);
  try { F().dispatchEvent(new (FW().PointerEvent)('pointermove', { clientX: l.x, clientY: l.y, bubbles: true })); } catch (e) { /* 앱이 아직 없다 */ }
}
function center(el) {
  const r = el.getBoundingClientRect(), fr = frame.getBoundingClientRect();
  return { x: fr.left + (r.left + r.width / 2) * SCALE, y: fr.top + (r.top + r.height / 2) * SCALE };
}
async function moveTo(x, y, dur = 650) {
  const sx = cx, sy = cy, t0 = performance.now();
  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  await new Promise((done) => {
    const step = (now) => {
      const t = Math.min(1, (now - t0) / dur), e = ease(t);
      cx = sx + (x - sx) * e; cy = sy + (y - sy) * e;
      cur.style.transform = `translate(${cx - 6}px, ${cy - 4}px)`;
      feedEyes(cx, cy);
      if (t < 1) requestAnimationFrame(step); else done();
    };
    requestAnimationFrame(step);
  });
}
async function hover(el, dur) {
  if (!el) return;
  const c = center(el);
  await moveTo(c.x, c.y, dur);
  ['pointerover', 'pointerenter', 'mouseover'].forEach((t) => el.dispatchEvent(new (FW().PointerEvent)(t, { bubbles: t !== 'pointerenter' })));
}
async function unhover(el) { if (el) el.dispatchEvent(new (FW().PointerEvent)('pointerleave')); }
async function click(el, dur) {
  if (!el) throw new Error('누를 것이 없다');
  await hover(el, dur);
  await sleep(140);
  cur.classList.add('down');
  const r = document.createElement('div');
  r.className = 'ripple'; r.style.left = cx + 'px'; r.style.top = cy + 'px';
  document.body.appendChild(r); setTimeout(() => r.remove(), 700);
  await sleep(110);
  el.click();
  cur.classList.remove('down');
  unhover(el);
}
function key(code, keyName, label) {
  const kc = $('#keycap');
  if (label) { kc.textContent = label; kc.classList.add('on'); setTimeout(() => kc.classList.remove('on'), 900); }
  F().body.dispatchEvent(new (FW().KeyboardEvent)('keydown', { key: keyName, code, bubbles: true }));
}
async function type(el, text) {
  el.focus();
  for (const ch of text) {
    el.value += ch;
    el.dispatchEvent(new (FW().Event)('input', { bubbles: true }));
    await sleep(55 + Math.random() * 45);
  }
}

// ---------------------------------------------------------------- 자막
async function cap(k, t, s) {
  const c = $('#cap');
  c.classList.add('out');
  await sleep(360);
  $('#ck').textContent = k; $('#ct').innerHTML = t; $('#cs').textContent = s;
  c.classList.remove('out');
}

// ---------------------------------------------------------------- 장면
async function run() {
  const pet = (m, st) => FW().pet(m, st);
  $('#intro').innerHTML = `${pet('happy', 'adult')}<div class="logo">brain</div><div class="tag">${C.tag}</div>`;
  $('#outro').innerHTML = `${pet('happy', 'sage')}<div class="logo">brain</div><div class="tag">make Claude Code remember!</div><div class="cmd">/claude-brain-app</div><div class="url">github.com/FuJiGraphics/claude-brain</div>`;
  window.__ready = true;
  await until(() => window.__go, 600000);

  // 0. 인트로
  await sleep(2600);
  $('#intro').classList.add('hide');
  $('#device').classList.add('on');
  await sleep(500);

  // 1. 뇌들
  await S(0);
  const tiles = qa('.pet-tile');
  await hover(tiles[1], 900); await sleep(700);
  await hover(tiles[2], 700); await sleep(600);
  await hover(tiles[3], 700); await sleep(500);
  await moveTo(700, 420, 900); await sleep(400);   // 눈이 커서를 따라온다

  // 2. 말풍선
  await click(tiles[0], 800);
  await until(() => qa('.bubble.on').length >= 3, 8000);
  await S(1);
  await sleep(900);
  const bubs = qa('.bubble');
  await hover(bubs[0], 800); await sleep(1300); await unhover(bubs[0]);
  await hover(bubs[2] || bubs[1], 700); await sleep(1200); await unhover(bubs[2] || bubs[1]);

  // 3. 쉬운 말
  await click(bubs[1], 600);
  await until(() => q('#memList .mem'), 5000);
  await sleep(500);
  await S(2);
  await click(q('#memList .mem'), 700);
  await until(() => q('.plain .pr'), 20000);
  await sleep(2600);

  // 4. 피드백
  await S(3);
  await click(q('.fbb[data-k=confirm]'), 800);
  await sleep(1000);
  await hover(q('.fbb[data-k=important]'), 600); await sleep(500);
  await click(q('.fbb[data-k=important]'), 300);
  await sleep(1300);
  key('Escape', 'Escape', 'Esc'); await sleep(450); key('Escape', 'Escape', 'Esc'); await sleep(700);
  await hover(q('#trayBar'), 700); await sleep(900);

  // 5. 물어보기
  await S(4);
  await click(q('#aAsk'), 900);
  const ta = await until(() => q('#chatIn'), 4000);
  await sleep(500);
  await moveTo(center(ta).x, center(ta).y, 500);
  await type(ta, C.ask);
  await sleep(300);
  await click(q('#chatGo'), 400);
  await until(() => q('.chat .refs button') || (qa('.chat .msg').length >= 3 && !q('.typing')), 30000);
  await sleep(3200);
  key('Escape', 'Escape', 'Esc'); await sleep(700);

  // 6. 최적화
  await S(5);
  await click(q('#aOpt'), 800);
  await until(() => q('#optPlan b'), 8000);
  await sleep(2400);
  key('Escape', 'Escape', 'Esc'); await sleep(700);

  // 7. 성격
  await S(6);
  await click(q('#aPersona'), 800);
  await until(() => q('.breed'), 5000);
  await sleep(700);
  const breeds = qa('.breed');
  await hover(breeds[0], 600); await sleep(400);
  await click(breeds[1], 500);
  await until(() => q('#pNow .fc'), 5000);
  await sleep(1300);
  await click(breeds[2], 700);
  await sleep(2300);

  // 8. 아웃트로
  $('#outro').classList.remove('hide');
  $('#outro').querySelectorAll(':scope > *').forEach((x) => { x.style.animation = 'none'; void x.offsetWidth; x.style.animation = ''; });
  await moveTo(1300, 760, 600);
  await sleep(4200);
  window.__done = true;
}

until(() => frame.contentWindow && frame.contentWindow.pet && F().querySelector('.pet-tile'), 30000)
  .then(() => sleep(800)).then(run)
  .catch((e) => { window.__error = String(e && e.stack || e); window.__done = true; });
