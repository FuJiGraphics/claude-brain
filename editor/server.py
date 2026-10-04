#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 에디터 서버 - 기억 저장소(cortex)를 보여 주고, 돌보기(먹이, 정정, 정리, 재우기)와 성격 설정을 받는 로컬 웹 서버.

실행: scripts/editor.sh 가 세션과 무관한 프로세스로 띄운다(직접: python3 editor/server.py [--port N]).
지키는 것:
  - cortex 는 읽기만 한다. 기억을 바꾸는 일은 전부 기존 통로로 넘긴다 - 먹이,정정은 remember.sh(해마 record),
    정리는 slices.py 조각을 해마 sweep 큐로, 잠은 sleep.sh. cortex 쓰기 주체는 hippocampus 하나다.
  - 성격(persona/<슬러그>.json)은 기억이 아니라 사용자 설정이라 여기서 직접 쓴다(persona.py).
  - 127.0.0.1 에만 열고, 실행 때 만든 토큰이 있어야 API 가 답한다. Host 머리도 확인한다(DNS 재바인딩 방지).
  - 2시간 동안 요청이 없으면 스스로 끝난다.
상태 파일: <brain>/.active/editor.json {pid, port, token, started}
"""
import datetime
import glob
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
SCRIPTS = os.path.join(BRAIN, 'scripts')
# 데모,시험용으로 다른 기억 저장소를 바라볼 수 있다(홍보 영상은 가상의 데모 뇌로 찍는다 - promo/)
CX = os.environ.get('BRAIN_CORTEX') or os.path.join(BRAIN, 'cortex')
HC = os.path.join(CX, '.hippocampus')
ACTIVE = os.environ.get('BRAIN_ACTIVE') or os.path.join(BRAIN, '.active')
PROMO = os.path.join(BRAIN, 'promo')
WEB = os.path.join(HERE, 'web')
STATE = os.path.join(ACTIVE, 'editor.json')
sys.path.insert(0, SCRIPTS)
import persona  # noqa: E402
import slices  # noqa: E402

IDLE_EXIT = 2 * 3600
DRYRUN = os.environ.get('BRAIN_EDITOR_DRYRUN') == '1'   # 시험용 - 기억,설정,큐를 건드리는 동작을 흉내만 낸다
FAKEAI = os.environ.get('BRAIN_EDITOR_FAKEAI', '1' if DRYRUN else '0') == '1'   # 시험용 - Haiku 대신 정해진 답(데모 촬영은 0)
TOKEN = secrets.token_urlsafe(18)
LAST_HIT = [time.time()]

# 용량 기준 - agents/hippocampus.md §5 와 같은 값(인덱스당 1만 자, 60항목), 프로젝트 INDEX 는 세션 시작에 2,500자까지 실린다
INDEX_CAP = 2500
FILE_CAP = 10000
ITEM_CAP = 60

FIRST_MD = re.compile(r'\]\(([^() ]+\.md)\)')
TITLE_RE = re.compile(r'^#\s+(.+)$', re.M)
CATEGORY_RE = slices.CATEGORY_RE

# 뇌 영역 - 기억 종류. 파일 이름과 인덱스 줄, 본문 머리의 낱말로 추정한다(forget.py 가 '함정', '사용자 결정' 을 가리는 방식과 같다)
REGIONS = [
    ('decision', '결정과 선호', re.compile(r'decision|user-pref|사용자 ?(결정|지시|선호|요청|요구)|번복', re.I)),
    ('trap', '함정', re.compile(r'gotcha|함정|안 ?됨|안 ?된다|깨짐|깨진다|실패|오류|에러|버그|주의|금지|crash|\bbug|fail|막힘|터짐|사고|손실', re.I)),
    ('procedure', '절차와 요령', re.compile(r'phases/|pattern|handoff|scripts/|절차|단계|how-?to|방법|요령|레시피|명령|배포|release|빌드|build', re.I)),
    ('fact', '구조와 사실', re.compile(r'facts?\b|facts-|api-facts|구조|structure|router|경로|위치|아키텍처|스키마|포맷|형식|매핑', re.I)),
    ('decision', '결정과 선호', re.compile(r'선호|결정|컨벤션|convention|원칙|정책', re.I)),
]
REGION_NAMES = dict((k, n) for k, n, _ in REGIONS)
REGION_NAMES['other'] = '그 밖의 교훈'


# ---------------------------------------------------------------- 읽기 도우미
def _read(p, limit=None):
    try:
        with open(p, encoding='utf-8', errors='replace') as f:
            return f.read(limit) if limit else f.read()
    except (IOError, OSError):
        return ''


def _json(p, default=None):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except (IOError, OSError, ValueError):
        return default


def registry():
    """[registry 행] [{root, slug, stack, ver, note}]"""
    rows = []
    for line in _read(os.path.join(CX, 'registry.md')).splitlines():
        if not line.startswith('|'):
            continue
        c = [x.strip().strip('`') for x in line.strip().strip('|').split('|')]
        if len(c) >= 3 and c[0].startswith('/'):
            c += [''] * (5 - len(c))
            rows.append({'root': c[0].rstrip('/'), 'slug': c[1], 'stack': c[2], 'ver': c[3],
                         'note': re.sub(r'\s+', ' ', '|'.join(c[4:]).replace('**', '')).strip()})
    return rows


def strength():
    return (_json(os.path.join(HC, 'strength.json'), {}) or {}).get('memories') or {}


def is_index_name(f):
    return f.endswith('.md') and f != 'dormant.md' and (f == 'INDEX.md' or 'index' in f.lower() or 'router' in f or bool(CATEGORY_RE.match(f)))


def migrated_before():
    """[이주 시각] brain 설치(brain-born 파일 생성) 직후까지 수정된 본문은 옛 저장소에서 옮겨 온 기억이라 '새로 배움' 으로 세지 않는다"""
    try:
        return os.path.getmtime(os.path.join(ACTIVE, 'brain-born')) + 600
    except OSError:
        return 0


def classify(text):
    for key, _, rx in REGIONS:
        if rx.search(text):
            return key
    return 'other'


_CACHE = {}
LAYER_RE = re.compile(r'^(common|stacks/[A-Za-z0-9_.-]+|projects/[A-Za-z0-9_.-]+)$')


def check_layer(layer):
    if not LAYER_RE.match(layer or '') or '..' in layer:
        raise ValueError('레이어 이름이 아니다: %s' % layer)
    return layer


def layer_data(layer):
    """[레이어 하나의 기억 목록과 인덱스 크기]
    - 기억 하나 = 인덱스 줄의 첫 링크가 가리키는 본문(forget.py, slices.py 와 같은 정의). 인덱스를 가리키는 링크(라우터)는 기억이 아니다
    - 5초 캐시
    """
    check_layer(layer)
    hit = _CACHE.get(layer)
    if hit and time.time() - hit[0] < 5:
        return hit[1]
    root = os.path.join(CX, layer)
    mems, order, idx_info, dormant = {}, [], [], []
    if os.path.isdir(root):
        names = sorted(os.listdir(root))
        idx_files = [f for f in names if is_index_name(f)]
        idx_set = set(idx_files)
        for f in idx_files:
            t = _read(os.path.join(root, f))
            links = set()
            for line in t.splitlines():
                m = FIRST_MD.search(line)
                if not m:
                    continue
                target = os.path.normpath(os.path.join(layer, m.group(1)))
                base = os.path.basename(target)
                if os.path.dirname(target) == layer and (base in idx_set or is_index_name(base)):
                    continue
                if not os.path.isfile(os.path.join(CX, target)):
                    continue
                links.add(target)
                if target not in mems:
                    mems[target] = {'path': target, 'index': f, 'line': re.sub(r'\s+', ' ', line.strip().lstrip('-* '))[:400]}
                    order.append(target)
            idx_info.append({'file': f, 'chars': len(t), 'items': len(links),
                             'cap': INDEX_CAP if f == 'INDEX.md' else FILE_CAP})
        for line in _read(os.path.join(root, 'dormant.md')).splitlines():
            m = FIRST_MD.search(line)
            if m:
                dm = re.search(r'<!-- dormant \S+ (\S+) -->', line)
                dormant.append({'path': os.path.normpath(os.path.join(layer, m.group(1))),
                                'line': re.sub(r'<!--.*?-->', '', line).strip().lstrip('-* ')[:300],
                                'since': dm.group(1) if dm else ''})
    st = strength()
    heads = {}
    for rel in order:
        m = mems[rel]
        p = os.path.join(CX, rel)
        head = _read(p, 1500)
        tm = TITLE_RE.search(head)
        m['title'] = (tm.group(1).strip() if tm else os.path.splitext(os.path.basename(rel))[0])[:200]
        try:
            m['mtime'] = int(os.path.getmtime(p))
        except OSError:
            m['mtime'] = 0
        # 인덱스 줄(요지)이 본문 머리보다 강한 신호다 - 줄에서 못 가르면 본문 머리로
        heads[rel] = head[:900]
        m['region'] = classify(' '.join((m['index'], rel, m['line'])))
        if m['region'] == 'other':
            m['region'] = classify(head[:600])
        s = st.get(rel) or {}
        m['used'] = (s.get('shown', 0) or 0) + (s.get('opened', 0) or 0) + (s.get('grepped', 0) or 0)
        m['last'] = s.get('last', '')
    data = {'layer': layer, 'memories': [mems[r] for r in order], 'indexes': idx_info, 'dormant': dormant,
            'has_strength': bool(st), 'heads': heads}
    _CACHE[layer] = (time.time(), data)
    return data


# ---------------------------------------------------------------- 해마, 잠, 설정
def pid_alive(pid):
    try:
        pid = int(pid)
        os.kill(pid, 0)
        return True
    except (ValueError, OSError, TypeError):
        return False


def hippo():
    lock = os.path.join(HC, 'lock')
    pid = _read(os.path.join(lock, 'pid')).strip()
    alive = bool(pid) and pid_alive(pid)
    q = sorted(glob.glob(os.path.join(HC, 'queue', '*.json')))
    pr = glob.glob(os.path.join(HC, 'processing', '*.json'))
    results = []
    for p in sorted(glob.glob(os.path.join(HC, 'done', '*.json')))[-200:]:
        if p.endswith('.request.json'):
            continue
        r = _json(p, {}) or {}
        rq = _json(p[:-5] + '.request.json', {}) or {}
        summ = (r.get('summary') or '').strip()
        results.append({'id': r.get('id') or os.path.basename(p), 'status': r.get('status') or '?',
                        'finished': (r.get('finished_at') or '')[:19], 'mode': rq.get('mode') or '',
                        'slug': rq.get('slug') or '', 'caller': rq.get('caller') or '',
                        'first': next((l for l in summ.splitlines() if l.strip()), '')[:200], 'summary': summ[:3000]})
    queued = []
    for p in q:
        r = _json(p, {}) or {}
        queued.append({'id': os.path.basename(p)[:-5], 'mode': r.get('mode'), 'slug': r.get('slug')})
    return {'alive': alive, 'pid': pid if alive else '', 'current': _read(os.path.join(lock, 'current')).strip() if alive else '',
            'queue': queued, 'processing': len(pr), 'results': results}


def config():
    c = {}
    for line in _read(os.path.join(ACTIVE, 'config')).splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            c[k.strip()] = v.strip()
    last = _read(os.path.join(HC, 'sleep', 'last')).strip()
    return {'enabled': c.get('enabled', '1') != '0', 'model': c.get('hippocampus_model', 'claude-sonnet-5-5'),
            'effort': c.get('hippocampus_effort', 'medium'), 'born': _read(os.path.join(ACTIVE, 'brain-born')).strip(),
            'last_sleep': int(last) if last.isdigit() else 0,
            'sleep_summary': _read(os.path.join(HC, 'sleep', 'last-summary.txt')).strip()[:300]}


# ---------------------------------------------------------------- 상태 계산 (캐릭터)
STAGES = [(0, 'egg', '알'), (1, 'baby', '아기'), (10, 'kid', '어린이'), (50, 'adult', '어른'), (200, 'sage', '현자')]


def stage_of(n):
    cur = STAGES[0]
    for s in STAGES:
        if n >= s[0]:
            cur = s
    nxt = next((s for s in STAGES if s[0] > n), None)
    return {'key': cur[1], 'name': cur[2], 'next': nxt[0] if nxt else None, 'next_name': nxt[2] if nxt else None}


def summarize(layer, slug=None, hp=None, cfg=None):
    """[레이어 요약] 기억 수, 영역, 용량, 학습, 기분 - 카드와 상세 화면이 같이 쓴다"""
    d = layer_data(layer)
    mems = d['memories']
    now = time.time()
    regions = {}
    for m in mems:
        regions[m['region']] = regions.get(m['region'], 0) + 1
    # 용량: 항목별 비율 중 가장 큰 것
    parts = []
    for ix in d['indexes']:
        parts.append({'file': ix['file'], 'ratio': round(ix['chars'] / float(ix['cap']), 3), 'chars': ix['chars'],
                      'cap': ix['cap'], 'items': ix['items'], 'item_ratio': round(ix['items'] / float(ITEM_CAP), 3)})
    parts.sort(key=lambda x: -max(x['ratio'], x['item_ratio']))
    cap = max([max(p['ratio'], p['item_ratio']) for p in parts] or [0])
    total_chars = sum(ix['chars'] for ix in d['indexes'])
    mig = migrated_before()
    learned = [m for m in mems if m['mtime'] > mig]
    week = [m for m in learned if now - m['mtime'] < 7 * 86400]
    last_learn = max([m['mtime'] for m in learned] or [0])
    # 활용도: 강도 기록이 있으면 최근 14일 안에 떠오르거나 열린 기억 비율
    usage = None
    if d['has_strength'] and mems:
        cut = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
        usage = round(sum(1 for m in mems if m['last'] and m['last'] >= cut) / float(len(mems)), 3)
    hp = hp or hippo()
    cfg = cfg or config()
    busy = any(q.get('slug') == slug for q in hp['queue']) if slug else False
    busy = busy or bool(slug and hp['alive'] and slug in hp['current'])
    recent_fail = [r for r in hp['results'][-30:] if r['slug'] == slug and r['status'] in ('failed', 'denied', 'timeout')] if slug else []
    sleepy = cfg['last_sleep'] and now - cfg['last_sleep'] > 36 * 3600
    if not cfg['enabled']:
        mood = ('off', '꺼져 있어요', 'brain 이 꺼져 있어 떠올리지도 배우지도 않아요')
    elif not mems:
        mood = ('egg', '알 속에서 꿈틀', '아직 기억이 없어요. 이 프로젝트에서 일하면 깨어나요')
    elif cap > 1.0:
        mood = ('overload', '머리가 꽉 찼어요', '기억 지도가 기준을 넘었어요. 정리하면 떠올림이 다시 정확해져요')
    elif recent_fail:
        mood = ('sick', '배탈 났어요', '최근 해마 작업 %d건이 실패했어요' % len(recent_fail))
    elif busy:
        mood = ('study', '공부 중', '해마가 이 프로젝트 기억을 새기고 있어요')
    elif sleepy:
        mood = ('sleepy', '졸려요', '마지막 잠이 하루 반 넘게 지났어요')
    elif now - (last_learn or mig) > 14 * 86400:
        mood = ('bored', '심심해요', '2주 넘게 새로 배운 게 없어요')
    elif cap > 0.85:
        mood = ('full', '배불러요', '곧 정리가 필요해요')
    else:
        mood = ('happy', '쌩쌩해요', '잘 배우고 잘 떠올리고 있어요')
    return {'layer': layer, 'count': len(mems), 'regions': regions, 'capacity': round(cap, 3), 'capacity_parts': parts[:8],
            'index_chars': total_chars, 'learned_week': len(week), 'last_learn': last_learn, 'usage': usage,
            'dormant': len(d['dormant']), 'stage': stage_of(len(mems)),
            'mood': {'key': mood[0], 'name': mood[1], 'why': mood[2]}, 'busy': busy}


def overview():
    hp, cfg = hippo(), config()
    projects = []
    for r in registry():
        s = summarize('projects/' + r['slug'], r['slug'], hp, cfg)
        pg = persona.load(r['slug'])
        s.update(r)
        s['persona'] = {'name': pg.get('name') or '', 'breed': pg.get('breed') or '', 'enabled': pg.get('enabled') is not False} if pg else None
        projects.append(s)
    shared = [summarize('common', None, hp, cfg)]
    for d in sorted(glob.glob(os.path.join(CX, 'stacks', '*'))):
        if os.path.isdir(d):
            shared.append(summarize('stacks/' + os.path.basename(d), None, hp, cfg))
    born = cfg['born']
    age = None
    try:
        age = (datetime.date.today() - datetime.date.fromisoformat(born)).days
    except ValueError:
        pass
    return {'projects': projects, 'shared': shared, 'config': cfg, 'age': age,
            'hippo': {k: hp[k] for k in ('alive', 'current', 'processing')}, 'queue': len(hp['queue']),
            'results': hp['results'][-8:][::-1]}


def layer_detail(layer):
    d = layer_data(layer)
    hp = hippo()
    slug = layer.split('/', 1)[1] if layer.startswith('projects/') else None
    s = summarize(layer, slug, hp)
    mig = migrated_before()
    for m in d['memories']:
        m['migrated'] = m['mtime'] <= mig
    mems = sorted([m for m in d['memories'] if not m['migrated']], key=lambda m: -m['mtime'])
    s['recent'] = mems[:12]
    s['migrated'] = sum(1 for m in d['memories'] if m['migrated'])
    s['memories'] = d['memories']   # heads 는 data 쪽에만 있다
    s['dormant_list'] = d['dormant'][:200]
    s['region_names'] = REGION_NAMES
    s['results'] = [r for r in hp['results'] if (slug and r['slug'] == slug)][-10:][::-1]
    s['queue'] = [q for q in hp['queue'] if slug and q.get('slug') == slug]
    if slug:
        row = next((r for r in registry() if r['slug'] == slug), None)
        if row:
            s.update(row)
        s['persona'] = persona.load(slug)
    return s


def read_memory(rel):
    p = os.path.realpath(os.path.join(CX, rel))
    root = os.path.realpath(CX)
    if not p.startswith(root + os.sep) or not p.endswith('.md') or os.sep + '.hippocampus' + os.sep in p:
        raise ValueError('기억 저장소 밖의 경로')
    st = strength().get(os.path.relpath(p, root)) or {}
    return {'path': os.path.relpath(p, root), 'text': _read(p)[:60000], 'mtime': int(os.path.getmtime(p)), 'strength': st}


def search(q, layers):
    terms = [t.lower() for t in q.split() if t.strip()]
    if not terms:
        return []
    out = []
    for lay in layers:
        for m in layer_data(lay)['memories']:
            hay = (m['title'] + ' ' + m['line'] + ' ' + m['path']).lower()
            if all(t in hay for t in terms):
                out.append(dict(m, layer=lay))
                if len(out) >= 60:
                    return out
    return out


# ---------------------------------------------------------------- 주제 (이 뇌가 중시하는 것 - 말풍선)
# 기억 제목과 색인 요지를 Haiku 에 주고 사람이 읽는 주제 단어(예: '유니티 스크립트 구조')와 뇌의 한마디를 받는다.
# 결과는 .active/topics/ 에 캐시하고, 기억 목록이 바뀌었어도 6시간 안에는 다시 만들지 않는다(그동안 옛 결과를 쓴다).
# 해마와 같은 방식으로 띄운다 - cortex 폴더에서(thalamus 가 건너뛴다), 도구 없음, 플러그인,MCP 끔, 부모 세션 변수 지움.
TOPICS_DIR = os.path.join(ACTIVE, 'topics')
TOPIC_MODEL = 'claude-haiku-4-5-20251001'
TOPIC_EVERY = 6 * 3600
TOPIC_INPUT = 28000
_TOPIC_JOBS = {}
_TOPIC_LOCK = threading.Lock()


def _topics_path(layer):
    return os.path.join(TOPICS_DIR, re.sub(r'[^A-Za-z0-9_.-]', '_', layer) + '.json')


def _mem_hash(mems):
    import hashlib
    return hashlib.sha1('\n'.join(m['path'] for m in mems).encode('utf-8')).hexdigest()[:16]


def _claude_bin():
    import shutil
    c = shutil.which('claude')
    if c:
        return c
    for p in ('~/.local/bin/claude', '~/.claude/local/claude', '/opt/homebrew/bin/claude', '/usr/local/bin/claude'):
        p = os.path.expanduser(p)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    raise RuntimeError('claude 실행 파일을 찾지 못했다')


def _plugins_off():
    cfg = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude')
    on = set()
    for n in ('settings.json', 'settings.local.json'):
        d = _json(os.path.join(cfg, n), {}) or {}
        on |= set(k for k, v in (d.get('enabledPlugins') or {}).items() if v)
    return json.dumps({'enabledPlugins': dict((k, False) for k in sorted(on))}) if on else ''


def haiku(prompt, system, timeout=120):
    """[Haiku 한 번] 도구 없음, 플러그인,MCP 끔, 기본 시스템 프롬프트를 바꿔 끼운다(약 7천 토큰이 빠져 한 번에 0.001달러 안팎).
    cortex 폴더에서 돌린다 - thalamus 가 brain 폴더 아래 세션을 건너뛴다. 결과 글(result)을 돌려준다"""
    env = dict(os.environ)
    for k in ('CLAUDECODE', 'CLAUDE_CODE_SESSION_ID', 'CLAUDE_CODE_CHILD_SESSION', 'CLAUDE_CODE_MESSAGING_SOCKET',
              'CLAUDE_CODE_MESSAGING_TOKEN', 'CLAUDE_PID', 'CLAUDE_EFFORT', 'CLAUDE_CODE_ENTRYPOINT'):
        env.pop(k, None)
    env['MAX_THINKING_TOKENS'] = '0'   # 요약,짧은 답에는 생각이 필요 없다 - 끄면 38초 -> 6초, 비용 6분의 1 (2026-10-05 실측)
    args = [_claude_bin(), '-p', prompt, '--model', TOPIC_MODEL, '--effort', 'low', '--tools', '', '--system-prompt', system,
            '--disable-slash-commands', '--strict-mcp-config', '--output-format', 'json', '--max-turns', '1', '--name', 'brain-app']
    po = _plugins_off()
    if po:
        args += ['--settings', po]
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=CX, env=env, stdin=subprocess.DEVNULL)
    if p.returncode != 0 and not p.stdout.strip():
        raise RuntimeError((p.stderr or 'claude 종료 코드 %d' % p.returncode).strip()[:300])
    return json.loads(p.stdout or '{}').get('result') or ''


def json_in(text):
    a, b = text.find('{'), text.rfind('}')
    if a < 0 or b < a:
        raise ValueError('JSON 이 없는 응답')
    return json.loads(text[a:b + 1])


def _topic_prompt(layer, mems):
    name = layer.split('/', 1)[1] if '/' in layer else '공용'
    rows, size = [], 0
    for i, m in enumerate(mems, 1):
        r = '%d. %s | %s' % (i, m['title'][:120], m['line'][:160])
        size += len(r)
        if size > TOPIC_INPUT:
            break
        rows.append(r)
    return ('아래는 "%s" 의 장기 기억 목록이다(번호. 제목 | 색인 요지). 이 기억들이 주로 무엇을 중요하게 다루는지 주제 %s개로 묶어라. 주제 하나에는 기억이 되도록 2개 이상 들어간다.\n'
            '- label: 한눈에 알아보는 짧은 한국어 명사구 4~14자. 예: "유니티 스크립트 구조", "ECS 구조", "원본 충실 이식", "배포 절차", "판정 타이밍". '
            '파일 이름이나 영어 슬러그를 그대로 쓰지 않는다. Unity, ECS, UGUI, FMOD 같은 고유 기술 이름은 그대로 쓴다.\n'
            '- emoji: 주제에 맞는 이모지 하나\n'
            '- ids: 그 주제에 속하는 기억 번호. 기억 하나는 가장 맞는 주제 하나에만 넣는다\n'
            '- 기억이 많은 주제부터 적는다\n'
            '- motto: 이 뇌가 제일 중요하게 여기는 것을 뇌 자신이 말하듯 한 문장, 해요체, 28자 이내. 예: "원본 그대로 옮기는 게 제일 중요해요"\n'
            'JSON 만 출력한다: {"motto":"...","topics":[{"label":"...","emoji":"...","ids":[1,2]}]}\n\n%s') % (
        name, '2~3' if len(rows) < 8 else '3~5' if len(rows) < 25 else '6~8', '\n'.join(rows))


def _topic_job(layer, mems, h):
    try:
        d = json_in(haiku(_topic_prompt(layer, mems), '너는 개발 메모 목록을 주제로 묶어 JSON 으로만 답하는 도우미다.', timeout=180))
        topics = []
        for t in d.get('topics') or []:
            ids = [i for i in t.get('ids') or [] if isinstance(i, int) and 1 <= i <= len(mems)]
            if t.get('label') and ids:
                topics.append({'label': str(t['label'])[:20], 'emoji': str(t.get('emoji') or '💭')[:4],
                               'paths': [mems[i - 1]['path'] for i in ids]})
        out = {'layer': layer, 'hash': h, 'generated': int(time.time()), 'model': TOPIC_MODEL,
               'motto': str(d.get('motto') or '')[:40], 'topics': topics[:8]}
        os.makedirs(TOPICS_DIR, exist_ok=True)
        tmp = _topics_path(layer) + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, _topics_path(layer))
        try:
            os.remove(_topics_path(layer) + '.err')
        except OSError:
            pass
    except Exception as e:
        os.makedirs(TOPICS_DIR, exist_ok=True)
        with open(_topics_path(layer) + '.err', 'w', encoding='utf-8') as f:
            f.write('%s: %s' % (e.__class__.__name__, e))
    finally:
        with _TOPIC_LOCK:
            _TOPIC_JOBS.pop(layer, None)


def _guess_topics(d):
    """[AI 결과가 없을 때] 색인 파일별로 묶은 추정 주제 - 색인 이름을 사람 말에 가깝게 다듬는다"""
    by = {}
    slug = d['layer'].split('/', 1)[1] if '/' in d['layer'] else ''
    for m in d['memories']:
        by.setdefault(m['index'], []).append(m)
    out = []
    for f, ms in sorted(by.items(), key=lambda kv: -len(kv[1])):
        n = re.sub(r'\.md$', '', f)
        n = re.sub(r'^(lessons-)?index-?', '', n).replace(slug + '-', '') if n != 'INDEX' else '프로젝트 지도'
        n = n.replace('lessons-index', '교훈').replace('-', ' ').strip() or '교훈'
        regs = {}
        for m in ms:
            regs[m['region']] = regs.get(m['region'], 0) + 1
        top = max(regs, key=regs.get)
        out.append({'label': n[:20], 'emoji': {'trap': '⚠️', 'decision': '⭐', 'procedure': '🧰', 'fact': '🧱'}.get(top, '💭'),
                    'paths': [m['path'] for m in ms]})
    return out[:8]


def topics(layer, force=False):
    d = layer_data(layer)
    mems = d['memories']
    cache = _json(_topics_path(layer))
    h = _mem_hash(mems)
    with _TOPIC_LOCK:
        running = layer in _TOPIC_JOBS
        need = bool(mems) and (force or not cache or (cache.get('hash') != h and time.time() - cache.get('generated', 0) > TOPIC_EVERY))
        if need and not running and not FAKEAI:
            t = threading.Thread(target=_topic_job, args=(layer, mems, h), daemon=True)
            _TOPIC_JOBS[layer] = t
            t.start()
            running = True
    live = set(m['path'] for m in mems)
    st = dict((m['path'], m['used']) for m in mems)
    src = cache.get('topics') if cache else None
    items = []
    for t in (src or _guess_topics(d)):
        ps = [p for p in t['paths'] if p in live]
        if ps:
            items.append({'label': t['label'], 'emoji': t['emoji'], 'paths': ps, 'count': len(ps), 'used': sum(st.get(p, 0) for p in ps)})
    items.sort(key=lambda x: -(x['count'] + x['used'] * 0.2))
    err = _read(_topics_path(layer) + '.err').strip() if not cache else ''
    return {'status': 'running' if running else ('ready' if cache else 'none'), 'source': 'ai' if src else 'guess',
            'motto': (cache or {}).get('motto') or '', 'generated': (cache or {}).get('generated') or 0, 'topics': items, 'error': err}


# ---------------------------------------------------------------- 쉬운 말 풀이
# AI 가 전보체로 남긴 기억을 한 줄 요약, 왜, 언제, 확인 질문으로 풀어 준다. 기억 경로와 수정 시각으로 캐시한다.
EXPLAIN_DIR = os.path.join(ACTIVE, 'explain')
EXPLAIN_SYS = ('너는 AI 가 개발 중에 남긴 기술 메모를, 그 프로젝트 주인인 개발자가 한눈에 이해하도록 쉬운 한국어로 풀어 주는 도우미다. '
               '메모에 없는 사실은 지어내지 않는다. JSON 만 출력한다.')


def explain(rel):
    import hashlib
    m = read_memory(rel)
    key = hashlib.sha1(('%s|%d' % (m['path'], m['mtime'])).encode('utf-8')).hexdigest()[:20]
    cp = os.path.join(EXPLAIN_DIR, key + '.json')
    c = _json(cp)
    if c:
        return c
    if FAKEAI:
        return {'summary': '(모의) %s' % m['path'].split('/')[-1], 'why': '모의 설명이에요.', 'when': '모의로 떠올려요.',
                'check': '아직도 맞나요?', 'terms': []}
    prompt = ('아래 메모를 풀어라. 출력 JSON:\n'
              '{"summary":"무엇을 기억하는지 한 줄, 해요체, 45자 이내",'
              '"why":"왜 기억해 두는지 - 모르면 무슨 일이 생기는지, 해요체 1~2문장",'
              '"when":"Claude 가 언제 이 기억을 떠올리는지 - 어떤 파일, 작업, 에러에서. 해요체 1문장",'
              '"check":"메모 내용이 지금도 맞는지 개발자가 예/아니요로 답할 수 있는 질문 하나, 해요체, 40자 이내",'
              '"terms":[{"word":"메모에 나온 어려운 낱말","meaning":"쉬운 뜻 25자 이내"}]}\n'
              'terms 는 최대 3개, 없으면 빈 배열. 파일 경로나 식별자는 필요할 때만 짧게 쓴다.\n\n--- 메모 (%s)\n%s') % (
        m['path'], m['text'][:6000])
    d = json_in(haiku(prompt, EXPLAIN_SYS, timeout=90))
    out = {'summary': str(d.get('summary') or '')[:80], 'why': str(d.get('why') or '')[:300], 'when': str(d.get('when') or '')[:200],
           'check': str(d.get('check') or '')[:80],
           'terms': [{'word': str(t.get('word', ''))[:30], 'meaning': str(t.get('meaning', ''))[:60]} for t in (d.get('terms') or [])[:3] if isinstance(t, dict)]}
    os.makedirs(EXPLAIN_DIR, exist_ok=True)
    with open(cp + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False)
    os.replace(cp + '.tmp', cp)
    return out


# ---------------------------------------------------------------- 피드백 우체통
# 기억 하나하나에 대한 피드백(맞아요, 달라졌어요, 중요해요, 필요 없어요)을 모았다가 한 번에 remember.sh 로 넘긴다 - 해마가 한 번만 일한다.
FEEDBACK_DIR = os.path.join(ACTIVE, 'feedback')
FB_KINDS = {
    'confirm': '확인: 기억 `%s` 는 지금도 맞다(사용자가 직접 확인) - verified 를 오늘로 갱신한다',
    'important': '중요: 기억 `%s` 는 사용자에게 중요하다 - 사용자 결정으로 표시해 쉽게 잊히지 않게 한다',
    'outdated': '정정: 기억 `%s` 의 내용이 틀렸거나 낡았다 - %s',
    'forget': '필요 없음: 사용자가 기억 `%s` 를 더는 필요 없다고 했다 - 아카이브한다(하드 삭제 아님)',
}
_FB_LOCK = threading.Lock()


def _fb_path(layer):
    return os.path.join(FEEDBACK_DIR, re.sub(r'[^A-Za-z0-9_.-]', '_', check_layer(layer)) + '.json')


def feedback_list(layer):
    return _json(_fb_path(layer), []) or []


def _fb_save(layer, items):
    os.makedirs(FEEDBACK_DIR, exist_ok=True)
    p = _fb_path(layer)
    with open(p + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    os.replace(p + '.tmp', p)


def feedback_add(layer, rel, title, kind, text):
    if kind not in FB_KINDS:
        raise ValueError('모르는 피드백')
    if kind == 'outdated' and not (text or '').strip():
        raise ValueError('무엇이 달라졌는지 적어 주세요')
    read_memory(rel)
    with _FB_LOCK:
        items = [x for x in feedback_list(layer) if x['path'] != rel]   # 기억 하나에는 마지막 피드백 하나만
        items.append({'id': secrets.token_hex(4), 'path': rel, 'title': (title or '')[:120], 'kind': kind,
                      'text': (text or '').strip()[:1500], 'at': int(time.time())})
        _fb_save(layer, items)
    return items


def feedback_remove(layer, fid):
    with _FB_LOCK:
        items = [x for x in feedback_list(layer) if x['id'] != fid]
        _fb_save(layer, items)
    return items


def feedback_send(layer):
    with _FB_LOCK:
        items = feedback_list(layer)
        if not items:
            return {'ok': True, 'count': 0, 'out': ''}
        today = datetime.date.today().isoformat()
        args = []
        for x in items:
            t = FB_KINDS[x['kind']]
            body = t % ((x['path'], x['text']) if x['kind'] == 'outdated' else (x['path'],))
            args.append('%s - 근거: 사용자가 brain 앱에서 직접 남김 %s' % (body, today))
        root = root_of(layer[9:]) if layer.startswith('projects/') else '/'
        if DRYRUN:
            out, rc = '(모의) 큐 투입: %d건' % len(args), 0
        else:
            out, rc = run(['bash', os.path.join(SCRIPTS, 'remember.sh'), '--root', root] + args)
        if rc == 0:
            _fb_save(layer, [])
    return {'ok': rc == 0, 'count': len(items), 'out': out}


# ---------------------------------------------------------------- 물어보기
# 질문과 겹치는 기억을 파이썬이 고르고(한글 두 글자 조각 + 영문 낱말, 드문 조각일수록 무겁게), Haiku 가 그 기억만 보고 답한다.
# recall.sh 를 쓰지 않는다 - 검색 기록이 기억 강도에 쌓여 망각 판정이 흐려진다.
ASK_SYS = ('너는 "%s" 프로젝트의 뇌 캐릭터다. 귀엽고 다정한 해요체로 짧게(2~5문장) 답한다. '
           '아래에 주어진 기억에 있는 내용만 근거로 답하고, 기억에 없으면 "그건 기억에 없어요"라고 솔직하게 말한다. 지어내지 않는다. '
           '근거로 쓴 기억 번호를 refs 에 넣는다. JSON 만 출력한다: {"answer":"...","refs":[1,2]}')
TOKEN_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_.]{2,}|[가-힣]+')


def _grams(text):
    out = set()
    for w in TOKEN_RE.findall(text.lower()):
        if w[0] >= '가':
            out.update(w[i:i + 2] for i in range(max(1, len(w) - 1)))
        else:
            out.add(w)
    return out


def ask(layer, q, history):
    import math
    q = (q or '').strip()[:500]
    if not q:
        raise ValueError('질문이 비었어요')
    d = layer_data(layer)
    mems = d['memories']
    if not mems:
        return {'answer': '아직 아무것도 기억하지 못해요. 이 프로젝트에서 같이 일하면 하나씩 배울게요!', 'refs': []}
    docs = [_grams(' '.join((m['title'], m['line'], d['heads'].get(m['path'], '')))) for m in mems]
    qg = _grams(q + ' ' + ' '.join(h.get('q', '') for h in (history or [])[-2:]))
    df = {}
    for g in docs:
        for t in g & qg:
            df[t] = df.get(t, 0) + 1
    n = len(docs)
    scored = sorted(((sum(math.log(1 + n / df[t]) for t in g & qg), i) for i, g in enumerate(docs)), reverse=True)
    top = [i for sc, i in scored[:6] if sc > 0]
    if FAKEAI:
        return {'answer': '(모의) %s 에 대해 기억 %d개를 찾았어요.' % (q[:20], len(top)),
                'refs': [{'path': mems[i]['path'], 'title': mems[i]['title']} for i in top[:3]]}
    rows = []
    for k, i in enumerate(top, 1):
        m = mems[i]
        body = _read(os.path.join(CX, m['path']))[:1800]
        rows.append('[%d] %s\n%s' % (k, m['title'], body))
    hist = '\n'.join('사용자: %s\n뇌: %s' % (h.get('q', '')[:200], h.get('a', '')[:300]) for h in (history or [])[-3:])
    prompt = ('%s\n\n--- 기억\n%s\n\n--- 질문\n%s') % (('--- 앞선 대화\n' + hist) if hist else '', '\n\n'.join(rows) or '(관련 기억 없음)', q)
    name = layer.split('/', 1)[1] if '/' in layer else '공용'
    r = json_in(haiku(prompt, ASK_SYS % name, timeout=90))
    refs = []
    for k in r.get('refs') or []:
        if isinstance(k, int) and 1 <= k <= len(top):
            m = mems[top[k - 1]]
            refs.append({'path': m['path'], 'title': m['title']})
    return {'answer': str(r.get('answer') or '음… 잘 모르겠어요')[:800], 'refs': refs[:4]}


# ---------------------------------------------------------------- 동작 (기존 통로로만)
def run(args, timeout=30, cwd=None):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=cwd or BRAIN,
                       env=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8'))
    return ((p.stdout or '') + (p.stderr or '')).strip(), p.returncode


def root_of(slug):
    row = next((r for r in registry() if r['slug'] == slug), None)
    if not row:
        raise ValueError('registry 에 없는 프로젝트: %s' % slug)
    return row['root']


def feed(slug, text):
    text = (text or '').strip()
    if not text:
        raise ValueError('새길 내용이 비었어요')
    if DRYRUN:
        root_of(slug)
        return {'ok': True, 'out': '(모의) 큐 투입: %s' % text[:40]}
    out, rc = run(['bash', os.path.join(SCRIPTS, 'remember.sh'), '--root', root_of(slug),
                   '%s - 근거: 사용자가 brain 에디터에서 직접 남김 %s' % (text[:2000], datetime.date.today().isoformat())])
    return {'ok': rc == 0, 'out': out}


def correct(slug, rel, text):
    text = (text or '').strip()
    if not text:
        raise ValueError('정정 내용이 비었어요')
    read_memory(rel)   # 경로 검사
    root = root_of(slug) if slug else '/'   # 공용,스택 기억은 프로젝트 밖(/)으로 넘긴다 - 레이어는 해마가 정한다
    if DRYRUN:
        return {'ok': True, 'out': '(모의) 정정 투입: %s' % rel}
    out, rc = run(['bash', os.path.join(SCRIPTS, 'remember.sh'), '--root', root,
                   '정정: 기억 `%s` 의 내용이 틀렸거나 낡았다 - %s - 근거: 사용자가 brain 에디터에서 직접 정정 %s' % (
                       rel, text[:2000], datetime.date.today().isoformat())])
    return {'ok': rc == 0, 'out': out}


def tidy(layer, mode, dry):
    """[정리] 그 레이어의 조각을 해마 sweep 큐로 넣는다. mode=over 면 기준을 넘은 인덱스와 미등록 조각만, all 이면 전부"""
    check_layer(layer)
    sl = [s for s in slices.compute(CX, 40000) if s['layer'] == layer and not s['id'].endswith(':dormant.md')]
    if mode == 'over':
        over = set()
        for ix in layer_data(layer)['indexes']:
            if ix['chars'] > ix['cap'] or ix['items'] > ITEM_CAP:
                over.add(ix['file'])
        sl = [s for s in sl if s['id'].split(':', 1)[1].split('#')[0] in over or '(미등록)' in s['id']]
    plan = [{'id': s['id'], 'tok': s['tok'], 'files': len(s['files'])} for s in sl]
    res = {'slices': plan, 'tok': sum(s['tok'] for s in sl), 'count': len(sl)}
    if dry or not sl:
        return res
    if DRYRUN:
        res['enqueued'] = ['(모의) 큐 투입: %s' % s['id'] for s in sl]
        return res
    tmp = os.path.join(HC, 'editor-req')
    os.makedirs(tmp, exist_ok=True)
    for f in glob.glob(os.path.join(tmp, 'req-*.json')):
        os.remove(f)
    due = os.path.join(tmp, 'due.json')
    with open(due, 'w', encoding='utf-8') as f:
        json.dump(sl, f, ensure_ascii=False)
    out, rc = run([sys.executable, os.path.join(SCRIPTS, 'slices.py'), '--make-requests', due, '--registry',
                   os.path.join(CX, 'registry.md'), '--out', tmp, '--caller', 'brain-editor-tidy'])
    if rc != 0:
        raise RuntimeError(out)
    logs = []
    for r in sorted(glob.glob(os.path.join(tmp, 'req-*.json'))):
        o, _ = run(['bash', os.path.join(SCRIPTS, 'hippocampus-enqueue.sh'), r])
        logs.append(o.splitlines()[0] if o else '')
    res['enqueued'] = logs
    return res


def sleep_now():
    if DRYRUN:
        return {'ok': True}
    lg = os.path.join(HC, 'logs')
    os.makedirs(lg, exist_ok=True)
    with open(os.path.join(lg, 'sleep-manual.out'), 'a') as out:
        subprocess.Popen(['bash', os.path.join(SCRIPTS, 'sleep.sh')], stdin=subprocess.DEVNULL, stdout=out,
                         stderr=subprocess.STDOUT, cwd=BRAIN, start_new_session=True)
    return {'ok': True}


def set_config(action, value):
    allowed = {'on': [], 'off': [], 'preset': ['default', 'eco', 'quality']}
    if action not in allowed or (allowed[action] and value not in allowed[action]):
        raise ValueError('모르는 설정')
    if DRYRUN:
        return {'ok': True, 'out': '(모의) %s %s' % (action, value or '')}
    out, rc = run(['bash', os.path.join(SCRIPTS, 'config.sh'), action] + ([value] if value else []))
    return {'ok': rc == 0, 'out': out}


# ---------------------------------------------------------------- HTTP
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
         '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon'}


class H(BaseHTTPRequestHandler):
    server_version = 'brain-editor'

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self):
        host = (self.headers.get('Host') or '').split(':')[0]
        return host in ('127.0.0.1', 'localhost')

    def _auth(self, qs):
        return secrets.compare_digest(self.headers.get('X-Brain-Token') or (qs.get('t') or [''])[0], TOKEN)

    def do_GET(self):
        LAST_HIT[0] = time.time()
        if not self._host_ok():
            return self._send(403, {'error': 'host'})
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if not u.path.startswith('/api/'):
            base = WEB
            rel = 'index.html' if u.path in ('/', '') else u.path.lstrip('/')
            if rel.startswith('promo/') and os.environ.get('BRAIN_EDITOR_PROMO') == '1':   # 홍보 영상 촬영 때만
                base, rel = PROMO, rel[6:]
            p = os.path.realpath(os.path.join(base, rel))
            if not p.startswith(os.path.realpath(base) + os.sep) or not os.path.isfile(p):
                return self._send(404, {'error': 'not found'})
            with open(p, 'rb') as f:
                return self._send(200, f.read(), TYPES.get(os.path.splitext(p)[1], 'application/octet-stream'))
        if not self._auth(qs):
            return self._send(401, {'error': '토큰이 맞지 않아요. /claude-brain-app 로 다시 여세요'})
        try:
            q = lambda k, d='': (qs.get(k) or [d])[0]  # noqa: E731
            if u.path == '/api/overview':
                return self._send(200, overview())
            if u.path == '/api/layer':
                return self._send(200, layer_detail(q('l')))
            if u.path == '/api/memory':
                return self._send(200, read_memory(q('p')))
            if u.path == '/api/search':
                lays = [x for x in q('l').split(',') if x]
                return self._send(200, {'items': search(q('q'), lays)})
            if u.path == '/api/topics':
                return self._send(200, topics(q('l'), q('force') == '1'))
            if u.path == '/api/explain':
                return self._send(200, explain(q('p')))
            if u.path == '/api/feedback':
                return self._send(200, {'items': feedback_list(q('l'))})
            if u.path == '/api/hippo':
                return self._send(200, hippo())
            if u.path == '/api/persona':
                slug = q('slug')
                g = persona.load(slug)
                cat = persona.catalog()
                for k in cat['breeds']:
                    cat['breeds'][k]['effective'] = persona.compile_graph(persona.from_breed(k))['effective']
                return self._send(200, {'graph': g, 'compiled': persona.compile_graph(g) if g else None, 'catalog': cat})
            if u.path == '/api/breed':
                g = persona.from_breed(q('b'))
                return self._send(200, {'graph': g, 'compiled': persona.compile_graph(g)})
            return self._send(404, {'error': 'no api'})
        except Exception as e:
            return self._send(400, {'error': '%s: %s' % (e.__class__.__name__, e)})

    def do_POST(self):
        LAST_HIT[0] = time.time()
        if not self._host_ok():
            return self._send(403, {'error': 'host'})
        u = urlparse(self.path)
        if not self._auth({}):
            return self._send(401, {'error': '토큰이 맞지 않아요'})
        try:
            n = int(self.headers.get('Content-Length') or 0)
            body = json.loads(self.rfile.read(min(n, 2 * 1024 * 1024)).decode('utf-8') or '{}')
            if u.path == '/api/persona/preview':
                return self._send(200, {'compiled': persona.compile_graph(body.get('graph'))})
            if u.path == '/api/persona/save':
                slug = body.get('slug') or ''
                root_of(slug)
                g = persona.save(slug, body.get('graph'))
                return self._send(200, {'graph': g, 'compiled': persona.compile_graph(g)})
            if u.path == '/api/persona/delete':
                slug = body.get('slug') or ''
                root_of(slug)
                p = persona.path_of(slug)
                if os.path.exists(p):
                    os.remove(p)
                return self._send(200, {'ok': True})
            if u.path == '/api/feed':
                return self._send(200, feed(body.get('slug'), body.get('text')))
            if u.path == '/api/correct':
                return self._send(200, correct(body.get('slug'), body.get('path'), body.get('text')))
            if u.path == '/api/tidy':
                return self._send(200, tidy(body.get('layer') or '', body.get('mode') or 'over', bool(body.get('dry'))))
            if u.path == '/api/sleep':
                return self._send(200, sleep_now())
            if u.path == '/api/feedback/add':
                return self._send(200, {'items': feedback_add(body.get('layer') or '', body.get('path') or '', body.get('title') or '',
                                                              body.get('kind') or '', body.get('text') or '')})
            if u.path == '/api/feedback/remove':
                return self._send(200, {'items': feedback_remove(body.get('layer') or '', body.get('id') or '')})
            if u.path == '/api/feedback/send':
                return self._send(200, feedback_send(body.get('layer') or ''))
            if u.path == '/api/ask':
                return self._send(200, ask(body.get('layer') or '', body.get('q') or '', body.get('history') or []))
            if u.path == '/api/config':
                return self._send(200, set_config(body.get('action'), body.get('value')))
            if u.path == '/api/quit':
                threading.Thread(target=lambda: (time.sleep(0.3), self.server.shutdown()), daemon=True).start()
                return self._send(200, {'ok': True})
            return self._send(404, {'error': 'no api'})
        except Exception as e:
            return self._send(400, {'error': '%s: %s' % (e.__class__.__name__, e)})


def idle_watch(srv):
    while True:
        time.sleep(60)
        if time.time() - LAST_HIT[0] > IDLE_EXIT:
            srv.shutdown()
            return


def main():
    a = sys.argv[1:]
    want = int(a[a.index('--port') + 1]) if '--port' in a else 7457
    srv = None
    for port in ((want,) if '--port' in a else (want, 0)):
        try:
            srv = ThreadingHTTPServer(('127.0.0.1', port), H)
            break
        except OSError:
            continue
    if srv is None:
        print('포트를 열지 못했다')
        return 1
    srv.daemon_threads = True
    port = srv.server_address[1]
    if '--no-state' not in a:   # 시험용 서버는 상태 파일을 남기지 않는다(진짜 에디터의 주소를 덮지 않게)
        os.makedirs(ACTIVE, exist_ok=True)
        tmp = STATE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({'pid': os.getpid(), 'port': port, 'token': TOKEN, 'started': int(time.time())}, f)
        os.chmod(tmp, 0o600)
        os.replace(tmp, STATE)
    threading.Thread(target=idle_watch, args=(srv,), daemon=True).start()
    print('brain 에디터: http://127.0.0.1:%d/?t=%s' % (port, TOKEN), flush=True)
    try:
        srv.serve_forever()
    finally:
        try:
            if (_json(STATE, {}) or {}).get('pid') == os.getpid():
                os.remove(STATE)
        except OSError:
            pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
