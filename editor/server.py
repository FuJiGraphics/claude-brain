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
import lang as LANG  # noqa: E402
import plat  # noqa: E402  OS 차이(경로, bash, 프로세스) - macOS, Linux, Windows
import persona  # noqa: E402
import cli_i18n  # noqa: E402  사람이 읽는 오류 글
import usage  # noqa: E402  claude -p 사용량 기록
import recall_stats  # noqa: E402  떠올림 기록 집계 - 밤 잠과 같은 정의


def E(key, *args):
    """[오류 글] 서버가 바라보는 설정 언어로 - 앱이 토스트로 보여 준다"""
    return cli_i18n.m(key, *args, lang=config()['lang'])
import slices  # noqa: E402

TONE = {'ko': 'polite 해요체', 'en': 'friendly, plain English', 'ja': 'polite です/ます style', 'zh': 'friendly, plain Simplified Chinese'}


def lang_of(v):
    """[요청 언어] 앱이 보낸 값, 없으면 brain 언어 설정"""
    return v if v in LANG.LANGS else config()['lang']   # 서버가 바라보는 설정(데모면 데모 설정)

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
        if len(c) >= 3 and plat.is_abs(c[0]):
            c += [''] * (5 - len(c))
            rows.append({'root': plat.norm(c[0]), 'slug': c[1], 'stack': c[2], 'ver': c[3],
                         'note': re.sub(r'\s+', ' ', '|'.join(c[4:]).replace('**', '')).strip()})
    return rows


_STATS = {'sig': None, 'data': None}


def stats():
    """[기억 강도와 적중] 떠올림 기록(.active/recall.log)을 바로 센다
    - 밤 잠이 쓰는 strength.json 은 잠을 거른 밤(맥이 꺼져 있던 밤)이 있으면 낡아서, 새 프로젝트의 활용도가 0 으로 보였다
    - 기록이 바뀌었을 때만 다시 센다. 떠올림 기록이 없으면(데모 뇌) strength.json 으로
    """
    log = os.path.join(ACTIVE, 'recall.log')
    if not os.path.isfile(log):
        return {'memories': (_json(os.path.join(HC, 'strength.json'), {}) or {}).get('memories') or {}, 'hits': {}}
    cut = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
    sig = [cut]
    for p in [log] + glob.glob(os.path.join(ACTIVE, '*.checks.log')) + glob.glob(os.path.join(ACTIVE, 'legacy', '*.checks.log')):
        try:
            sig.append((p, os.path.getsize(p), os.path.getmtime(p)))
        except OSError:
            pass
    if _STATS['sig'] != sig:
        _STATS['data'] = recall_stats.collect(CX, ACTIVE, cut)
        _STATS['sig'] = sig
    return _STATS['data']


def strength():
    return stats()['memories']


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
        raise ValueError(E('srv.bad_layer'))
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
    return plat.pid_alive(pid)   # Windows 에서 os.kill(pid, 0) 은 그 프로세스를 끝내 버린다


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
        queued.append({'id': os.path.basename(p)[:-5], 'mode': r.get('mode'), 'slug': r.get('slug'), 'caller': r.get('caller'),
                       'slice': ((r.get('payload') or {}).get('slice') or {}).get('id', '')})
    return {'alive': alive, 'pid': pid if alive else '', 'current': _read(os.path.join(lock, 'current')).strip() if alive else '',
            'queue': queued, 'processing': len(pr), 'results': results, 'stopping': alive and os.path.exists(os.path.join(HC, 'stop'))}


def config():
    c = {}
    for line in _read(os.path.join(ACTIVE, 'config')).splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            c[k.strip()] = v.strip()
    last = _read(os.path.join(HC, 'sleep', 'last')).strip()
    return {'enabled': c.get('enabled', '1') != '0', 'lang': c.get('lang') if c.get('lang') in LANG.LANGS else 'ko',
            'model': c.get('hippocampus_model', 'claude-sonnet-5-5'),
            'effort': c.get('hippocampus_effort', 'medium'), 'born': _read(os.path.join(ACTIVE, 'brain-born')).strip(),
            'last_sleep': int(last) if last.isdigit() else 0,
            'sleep_summary': _read(os.path.join(HC, 'sleep', 'last-summary.txt')).strip()[:300],
            'mute': [x for x in c.get('mute', '').split(',') if x], 'update': update_info(), 'version': code_version_label()}


def update_info():
    """[새 버전] 밤 정리(update.py check)가 남긴 .active/update-available: <변경 수>\t<최근 제목>\t<시각>"""
    v = _read(os.path.join(ACTIVE, 'update-available')).strip().split('\t')
    return {'n': int(v[0]), 'subject': v[1] if len(v) > 1 else ''} if v and v[0].isdigit() and int(v[0]) > 0 else None


def code_version_label():
    """[지금 코드 버전] git HEAD 의 짧은 해시(.git 을 직접 읽는다 - git 을 부르지 않는다). 모르면 빈 글"""
    try:
        g = os.path.join(BRAIN, '.git')
        head = _read(os.path.join(g, 'HEAD')).strip()
        if head.startswith('ref: '):
            ref = head[5:]
            v = _read(os.path.join(g, *ref.split('/'))).strip()
            if not v:
                for line in _read(os.path.join(g, 'packed-refs')).splitlines():
                    if line.endswith(' ' + ref):
                        v = line.split(' ')[0]
            head = v
        return head[:7] if re.match(r'^[0-9a-f]{7,40}$', head or '') else ''
    except OSError:
        return ''


# ---------------------------------------------------------------- 상태 계산 (캐릭터)
# 이름은 앱이 키로 언어마다 붙인다(i18n.js stage.*) - 서버는 키만 보낸다
STAGES = [(0, 'egg'), (1, 'baby'), (10, 'kid'), (50, 'adult'), (200, 'sage')]


def stage_of(n):
    cur = STAGES[0]
    for s in STAGES:
        if n >= s[0]:
            cur = s
    nxt = next((s for s in STAGES if s[0] > n), None)
    return {'key': cur[1], 'next': nxt[0] if nxt else None, 'next_key': nxt[1] if nxt else None}


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
    # 적중률: 최근 14일 떠오른 기억을 같은 세션이 그 뒤 열어 본 비율 - 요지만 보고 충분하면 안 열고, 열어 보고 무관할 수도 있어 정확도 그 자체는 아니다
    hits = stats()['hits']
    hn = sum(hits[m['path']][0] for m in mems if m['path'] in hits)
    ho = sum(hits[m['path']][1] for m in mems if m['path'] in hits)
    hit = {'n': hn, 'opened': ho, 'rate': round(ho / float(hn), 3)} if hn else None
    hp = hp or hippo()
    cfg = cfg or config()
    busy = any(q.get('slug') == slug for q in hp['queue']) if slug else False
    busy = busy or bool(slug and hp['alive'] and slug in hp['current'])
    recent_fail = [r for r in hp['results'][-30:] if r['slug'] == slug and r['status'] in ('failed', 'denied', 'timeout')] if slug else []
    sleepy = cfg['last_sleep'] and now - cfg['last_sleep'] > 36 * 3600
    # 기분은 키와 숫자만 보낸다 - 문구는 화면이 언어별로 만든다
    if not cfg['enabled']:
        mood = 'off'
    elif not mems:
        mood = 'egg'
    elif cap > 1.0:
        mood = 'overload'
    elif recent_fail:
        mood = 'sick'
    elif busy:
        mood = 'study'
    elif sleepy:
        mood = 'sleepy'
    elif now - (last_learn or mig) > 14 * 86400:
        mood = 'bored'
    elif cap > 0.85:
        mood = 'full'
    else:
        mood = 'happy'
    return {'layer': layer, 'count': len(mems), 'regions': regions, 'capacity': round(cap, 3), 'capacity_parts': parts[:8],
            'index_chars': total_chars, 'learned_week': len(week), 'last_learn': last_learn, 'usage': usage, 'hit': hit,
            'dormant': len(d['dormant']), 'stage': stage_of(len(mems)),
            'mood': {'key': mood, 'n': len(recent_fail)}, 'busy': busy}


def overview():
    hp, cfg = hippo(), config()
    projects = []
    for r in registry():
        s = summarize('projects/' + r['slug'], r['slug'], hp, cfg)
        pg = persona.load(r['slug'])
        s.update(r)
        s['persona'] = {'name': pg.get('name') or '', 'breed': pg.get('breed') or '', 'enabled': pg.get('enabled') is not False} if pg else None
        s['muted'] = r['slug'] in cfg['mute']
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
            'results': hp['results'][-8:][::-1],
            'usage': {'week': usage.summary(7, ACTIVE), 'month': usage.summary(30, ACTIVE)}}


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
    s['results'] = [r for r in hp['results'] if (slug and r['slug'] == slug)][-10:][::-1]
    s['queue'] = [q for q in hp['queue'] if slug and q.get('slug') == slug]
    s['muted'] = bool(slug) and slug in config()['mute']
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
        raise ValueError(E('srv.outside'))
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


def _topics_path(layer, lang='ko'):
    return os.path.join(TOPICS_DIR, re.sub(r'[^A-Za-z0-9_.-]', '_', layer) + ('' if lang == 'ko' else '.' + lang) + '.json')


def _mem_hash(mems):
    import hashlib
    return hashlib.sha1('\n'.join(m['path'] for m in mems).encode('utf-8')).hexdigest()[:16]


def _claude_bin():
    import shutil
    c = shutil.which('claude')
    if c:
        return c
    for p in ('~/.local/bin/claude', '~/.local/bin/claude.exe', '~/.claude/local/claude', '~/AppData/Roaming/npm/claude.cmd',
              '/opt/homebrew/bin/claude', '/usr/local/bin/claude'):
        p = os.path.expanduser(p)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    raise RuntimeError(E('srv.no_claude'))


def _plugins_off():
    cfg = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude')
    on = set()
    for n in ('settings.json', 'settings.local.json'):
        d = _json(os.path.join(cfg, n), {}) or {}
        on |= set(k for k, v in (d.get('enabledPlugins') or {}).items() if v)
    return json.dumps({'enabledPlugins': dict((k, False) for k in sorted(on))}) if on else ''


def haiku(prompt, system, timeout=120, what='app'):
    """[Haiku 한 번] 도구 없음, 플러그인,MCP 끔, 기본 시스템 프롬프트를 바꿔 끼운다(약 7천 토큰이 빠진다. 2026-10-05 측정: 한 번에 0.002~0.004달러).
    cortex 폴더에서 돌린다 - thalamus 가 brain 폴더 아래 세션을 건너뛴다. 결과 글(result)을 돌려준다"""
    env = dict(os.environ)
    for k in ('CLAUDECODE', 'CLAUDE_CODE_SESSION_ID', 'CLAUDE_CODE_CHILD_SESSION', 'CLAUDE_CODE_MESSAGING_SOCKET',
              'CLAUDE_CODE_MESSAGING_TOKEN', 'CLAUDE_PID', 'CLAUDE_EFFORT', 'CLAUDE_CODE_ENTRYPOINT'):
        env.pop(k, None)
    env['MAX_THINKING_TOKENS'] = '0'   # 요약,짧은 답에는 생각이 필요 없다 - 끄면 38초 -> 6초, 비용 6분의 1 (2026-10-05 실측)
    args = [_claude_bin(), '-p', '--model', TOPIC_MODEL, '--effort', 'low', '--tools', '', '--system-prompt', system,
            '--disable-slash-commands', '--strict-mcp-config', '--output-format', 'json', '--max-turns', '1', '--name', 'brain-app']
    po = _plugins_off()
    if po:
        args += ['--settings', po]
    p = subprocess.run(args, input=prompt, capture_output=True, text=True, timeout=timeout, cwd=CX, env=env,
                       encoding='utf-8', errors='replace')   # 프롬프트는 stdin 으로 - Windows 명령줄은 3.2만 자가 상한이다
    if p.returncode != 0 and not p.stdout.strip():
        raise RuntimeError((E('srv.claude_rc', p.returncode) + ('\n' + p.stderr.strip()[:240] if (p.stderr or '').strip() else '')))
    d = json.loads(p.stdout or '{}')
    usage.record('app', what, d, active=ACTIVE)
    return d.get('result') or ''


def json_in(text):
    a, b = text.find('{'), text.rfind('}')
    if a < 0 or b < a:
        raise ValueError(E('srv.bad_reply'))
    return json.loads(text[a:b + 1])


def haiku_json(prompt, system, timeout=120, what='app'):
    """[Haiku 에 JSON 받기] 가끔 따옴표,줄바꿈이 깨진 JSON 이 온다 - 한 번 다시 묻는다. 두 번째도 깨지면 (None, 원문)"""
    raw = haiku(prompt, system, timeout, what)
    try:
        return json_in(raw), raw
    except ValueError:
        raw = haiku(prompt + '\n\nYour previous reply was not valid JSON. Reply again with valid JSON only (escape quotes and newlines).',
                    system, timeout, what)
        try:
            return json_in(raw), raw
        except ValueError:
            return None, raw


def _topic_prompt(layer, mems, lang='ko'):
    name = layer.split('/', 1)[1] if '/' in layer else 'shared'
    rows, size = [], 0
    for i, m in enumerate(mems, 1):
        r = '%d. %s | %s' % (i, m['title'][:120], m['line'][:160])
        size += len(r)
        if size > TOPIC_INPUT:
            break
        rows.append(r)
    n = '2-3' if len(rows) < 8 else '3-5' if len(rows) < 25 else '6-8'
    short = 'a short noun phrase of 2-5 words' if lang == 'en' else 'a short noun phrase of 4-14 characters'
    return ('Below is the long-term memory list of "%s" (number. title | index gist). Group these memories into %s topics that show what this brain '
            'cares about most. Each topic should hold 2 or more memories.\n'
            '- label: %s in %s, readable at a glance (e.g. "Unity script structure", "ECS structure", "faithful porting", "deploy steps"). '
            'Do not copy file names or slugs. Keep proper tech names like Unity, ECS, UGUI as is, but write every other word in %s '
            '(never mix languages, e.g. not "전투 mechanics").\n'
            '- emoji: one emoji that fits the topic\n'
            '- ids: memory numbers in that topic; each memory goes into only its best topic\n'
            '- order topics from most memories to fewest\n'
            '- motto: one sentence the brain itself says about what it values most, first person, %s, %s\n'
            'Output JSON only: {"motto":"...","topics":[{"label":"...","emoji":"...","ids":[1,2]}]}\n\n%s') % (
        name, n, short, LANG.NAMES[lang], LANG.NAMES[lang], TONE[lang], 'max 60 characters' if lang == 'en' else 'max 28 characters', '\n'.join(rows))


def _topic_job(layer, mems, h, lang='ko'):
    try:
        d, raw = haiku_json(_topic_prompt(layer, mems, lang), 'You group developer notes into topics and answer with JSON only.', timeout=180, what='topics')
        if d is None:
            raise ValueError(E('srv.bad_reply'))
        topics = []
        for t in d.get('topics') or []:
            ids = [i for i in t.get('ids') or [] if isinstance(i, int) and 1 <= i <= len(mems)]
            if t.get('label') and ids:
                topics.append({'label': str(t['label'])[:40 if lang == 'en' else 24], 'emoji': str(t.get('emoji') or '💭')[:4],
                               'paths': [mems[i - 1]['path'] for i in ids]})
        out = {'layer': layer, 'lang': lang, 'hash': h, 'generated': int(time.time()), 'model': TOPIC_MODEL,
               'motto': str(d.get('motto') or '')[:90 if lang == 'en' else 48], 'topics': topics[:8]}
        os.makedirs(TOPICS_DIR, exist_ok=True)
        tmp = _topics_path(layer, lang) + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, _topics_path(layer, lang))
        try:
            os.remove(_topics_path(layer, lang) + '.err')
        except OSError:
            pass
    except Exception as e:
        os.makedirs(TOPICS_DIR, exist_ok=True)
        with open(_topics_path(layer, lang) + '.err', 'w', encoding='utf-8') as f:
            f.write('%s: %s' % (e.__class__.__name__, e))
    finally:
        with _TOPIC_LOCK:
            _TOPIC_JOBS.pop((layer, lang), None)


GUESS = {'ko': ('프로젝트 지도', '교훈'), 'en': ('project map', 'lessons'), 'ja': ('プロジェクトマップ', '教訓'), 'zh': ('项目地图', '经验')}


def _guess_topics(d, lang='ko'):
    """[AI 결과가 없을 때] 색인 파일별로 묶은 추정 주제 - 색인 이름을 사람 말에 가깝게 다듬는다"""
    by = {}
    slug = d['layer'].split('/', 1)[1] if '/' in d['layer'] else ''
    for m in d['memories']:
        by.setdefault(m['index'], []).append(m)
    out = []
    for f, ms in sorted(by.items(), key=lambda kv: -len(kv[1])):
        n = re.sub(r'\.md$', '', f)
        n = re.sub(r'^(lessons-)?index-?', '', n).replace(slug + '-', '') if n != 'INDEX' else GUESS[lang][0]
        n = n.replace('lessons-index', GUESS[lang][1]).replace('-', ' ').strip() or GUESS[lang][1]
        regs = {}
        for m in ms:
            regs[m['region']] = regs.get(m['region'], 0) + 1
        top = max(regs, key=regs.get)
        out.append({'label': n[:20], 'emoji': {'trap': '⚠️', 'decision': '⭐', 'procedure': '🧰', 'fact': '🧱'}.get(top, '💭'),
                    'paths': [m['path'] for m in ms]})
    return out[:8]


def topics(layer, force=False, lang='ko'):
    d = layer_data(layer)
    mems = d['memories']
    cache = _json(_topics_path(layer, lang))
    h = _mem_hash(mems)
    with _TOPIC_LOCK:
        running = (layer, lang) in _TOPIC_JOBS
        need = bool(mems) and (force or not cache or (cache.get('hash') != h and time.time() - cache.get('generated', 0) > TOPIC_EVERY))
        if need and not running and not FAKEAI:
            t = threading.Thread(target=_topic_job, args=(layer, mems, h, lang), daemon=True)
            _TOPIC_JOBS[(layer, lang)] = t
            t.start()
            running = True
    live = set(m['path'] for m in mems)
    st = dict((m['path'], m['used']) for m in mems)
    src = cache.get('topics') if cache else None
    items = []
    for t in (src or _guess_topics(d, lang)):
        ps = [p for p in t['paths'] if p in live]
        if ps:
            items.append({'label': t['label'], 'emoji': t['emoji'], 'paths': ps, 'count': len(ps), 'used': sum(st.get(p, 0) for p in ps)})
    items.sort(key=lambda x: -(x['count'] + x['used'] * 0.2))
    err = _read(_topics_path(layer, lang) + '.err').strip() if not cache else ''
    return {'status': 'running' if running else ('ready' if cache else 'none'), 'source': 'ai' if src else 'guess',
            'motto': (cache or {}).get('motto') or '', 'generated': (cache or {}).get('generated') or 0, 'topics': items, 'error': err}


# ---------------------------------------------------------------- 쉬운 말 풀이
# AI 가 전보체로 남긴 기억을 한 줄 요약, 왜, 언제, 확인 질문으로 풀어 준다. 기억 경로와 수정 시각으로 캐시한다.
EXPLAIN_DIR = os.path.join(ACTIVE, 'explain')
EXPLAIN_SYS = ('You turn terse technical notes that an AI coding agent saved during development into plain words the project owner '
               'understands at a glance. Never invent facts that are not in the note. Output JSON only.')


def explain(rel, lang='ko'):
    import hashlib
    m = read_memory(rel)
    key = hashlib.sha1(('%s|%d|%s' % (m['path'], m['mtime'], lang)).encode('utf-8')).hexdigest()[:20]
    cp = os.path.join(EXPLAIN_DIR, key + '.json')
    c = _json(cp)
    if c:
        return c
    if FAKEAI:
        return {'summary': '(모의) %s' % m['path'].split('/')[-1], 'why': '모의 설명이에요.', 'when': '모의로 떠올려요.',
                'check': '아직도 맞나요?', 'terms': []}
    cjk = lang != 'en'
    prompt = ('Explain the note below. Write every value in %s (%s).\n'
              'Output JSON: {"summary":"what is remembered, one line, %s",'
              '"why":"why it is worth remembering - what goes wrong without it, 1-2 sentences",'
              '"when":"when Claude recalls it - which files, tasks or errors, 1 sentence",'
              '"check":"one yes/no question the developer can answer to confirm the note is still true, %s",'
              '"terms":[{"word":"a hard term from the note","meaning":"plain meaning, %s"}]}\n'
              'At most 3 terms, empty array if none. Mention file paths or identifiers only when needed.\n\n--- note (%s)\n%s') % (
        LANG.NAMES[lang], TONE[lang], 'max 45 characters' if cjk else 'max 90 characters', 'max 40 characters' if cjk else 'max 80 characters',
        'max 25 characters' if cjk else 'max 50 characters', m['path'], m['text'][:6000])
    d, raw = haiku_json(prompt, EXPLAIN_SYS, timeout=90, what='explain')
    if d is None:
        raise ValueError(E('srv.bad_reply'))
    out = {'summary': str(d.get('summary') or '')[:160], 'why': str(d.get('why') or '')[:500], 'when': str(d.get('when') or '')[:300],
           'check': str(d.get('check') or '')[:160],
           'terms': [{'word': str(t.get('word', ''))[:40], 'meaning': str(t.get('meaning', ''))[:100]} for t in (d.get('terms') or [])[:3] if isinstance(t, dict)]}
    os.makedirs(EXPLAIN_DIR, exist_ok=True)
    with open(cp + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False)
    os.replace(cp + '.tmp', cp)
    return out


# ---------------------------------------------------------------- 피드백 우체통
# 기억 하나하나에 대한 피드백(맞아요, 달라졌어요, 중요해요, 필요 없어요)을 모았다가 한 번에 remember.sh 로 넘긴다 - 해마가 한 번만 일한다.
FEEDBACK_DIR = os.path.join(ACTIVE, 'feedback')
FB_TEXTS = {   # 해마에게 넘기는 피드백 문장 - 설정 언어로 쓴다(해마가 근거로 인용해 기억 본문에 남을 수 있다)
    'ko': {'confirm': '확인: 기억 `%s` 는 지금도 맞다(사용자가 직접 확인) - verified 를 오늘로 갱신한다',
           'important': '중요: 기억 `%s` 는 사용자에게 중요하다 - 사용자 결정으로 표시해 쉽게 잊히지 않게 한다',
           'outdated': '정정: 기억 `%s` 의 내용이 틀렸거나 낡았다 - %s',
           'forget': '필요 없음: 사용자가 기억 `%s` 를 더는 필요 없다고 했다 - 아카이브한다(하드 삭제 아님)',
           'restore': '되살리기: 보관함(_archive)의 기억 `%s` 를 사용자가 다시 쓰겠다고 했다 - 원래 자리로 옮기고 ARCHIVED 머리줄을 지운 뒤 인덱스 줄을 다시 단다',
           'evidence': '근거: 사용자가 brain 앱에서 직접 남김 %s', 'tidy': '사용자가 brain 앱에서 머리 정리를 요청했다'},
    'en': {'confirm': 'Confirm: memory `%s` is still correct (confirmed by the user) - update its verified date to today',
           'important': 'Important: memory `%s` matters to the user - mark it as a user decision so it is not forgotten easily',
           'outdated': 'Correction: memory `%s` is wrong or out of date - %s',
           'forget': 'Not needed: the user said memory `%s` is no longer needed - archive it (no hard delete)',
           'restore': 'Restore: the user wants archived memory `%s` (in _archive) back - move it to its original place, remove the ARCHIVED header and add its index line again',
           'evidence': 'evidence: left by the user in the brain app on %s', 'tidy': 'the user asked for a tidy-up in the brain app'},
    'ja': {'confirm': '確認: 記憶 `%s` は今も正しい(ユーザーが直接確認) - verified を今日に更新する',
           'important': '重要: 記憶 `%s` はユーザーにとって大事 - ユーザーの決定として印を付け、忘れにくくする',
           'outdated': '訂正: 記憶 `%s` の内容が間違っているか古い - %s',
           'forget': '不要: ユーザーが記憶 `%s` はもういらないと言った - アーカイブする(完全には削除しない)',
           'restore': '復元: 保管庫(_archive)の記憶 `%s` をユーザーがまた使いたいと言った - 元の場所に戻し、ARCHIVED の見出し行を消して索引の行を付け直す',
           'evidence': '根拠: ユーザーが brain アプリで直接残した %s', 'tidy': 'ユーザーが brain アプリで頭の整理を頼んだ'},
    'zh': {'confirm': '确认: 记忆 `%s` 现在仍然正确(用户直接确认) - 把 verified 更新为今天',
           'important': '重要: 记忆 `%s` 对用户很重要 - 标记为用户决定,不要轻易遗忘',
           'outdated': '纠正: 记忆 `%s` 的内容错误或过时 - %s',
           'forget': '不再需要: 用户说记忆 `%s` 不再需要 - 归档(不彻底删除)',
           'restore': '找回: 用户想重新使用归档(_archive)中的记忆 `%s` - 移回原处,删除 ARCHIVED 标题行,重新加上索引行',
           'evidence': '依据: 用户在 brain 应用中直接留下 %s', 'tidy': '用户在 brain 应用中要求整理大脑'},
}
FB_KINDS = ('confirm', 'important', 'outdated', 'forget', 'restore')


def fb_text(key):
    return FB_TEXTS.get(config()['lang'], FB_TEXTS['ko'])[key]
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
        raise ValueError(E('srv.bad_feedback'))
    if kind == 'outdated' and not (text or '').strip():
        raise ValueError(E('srv.need_text'))
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
            t = fb_text(x['kind'])
            body = t % ((x['path'], x['text']) if x['kind'] == 'outdated' else (x['path'],))
            args.append('%s - %s' % (body, fb_text('evidence') % today))
        root = root_of(layer[9:]) if layer.startswith('projects/') else '/'
        if DRYRUN:
            out, rc = '(모의) 큐 투입: %d건' % len(args), 0
        else:
            out, rc = run(['bash', os.path.join(SCRIPTS, 'remember.sh'), '--root', root] + args)
        if rc == 0:
            _fb_save(layer, [])
            track('mailbox', out, layer[9:] if layer.startswith('projects/') else '', len(items))
    return {'ok': rc == 0, 'count': len(items), 'out': out}


# ---------------------------------------------------------------- 물어보기
# 질문과 겹치는 기억을 파이썬이 고르고(한글 두 글자 조각 + 영문 낱말, 드문 조각일수록 무겁게), Haiku 가 그 기억만 보고 답한다.
# recall.sh 를 쓰지 않는다 - 검색 기록이 기억 강도에 쌓여 망각 판정이 흐려진다.
ASK_SYS = ('You are the brain character of the "%s" project. Answer in %s, cute and warm (%s), short (2-5 sentences). '
           'Use only what is in the memories given below; if the answer is not in them, honestly say you don\'t remember that. Never make things up. '
           'Write plain sentences without Markdown (no **, no #, no lists); wrap code names in `backticks` only. '
           'Put the numbers of the memories you used in refs. Output JSON only: {"answer":"...","refs":[1,2]}')
ASK_EMPTY = {'ko': '아직 아무것도 기억하지 못해요. 이 프로젝트에서 같이 일하면 하나씩 배울게요!',
             'en': "I don't remember anything yet. I'll learn bit by bit as we work on this project together!",
             'ja': 'まだ何も覚えていません。このプロジェクトで一緒に働けば少しずつ覚えますね!',
             'zh': '我还什么都不记得。在这个项目里一起工作的话,我会一点点学起来!'}
ASK_UNSURE = {'ko': '음… 잘 모르겠어요', 'en': "Hmm... I'm not sure", 'ja': 'うーん…よくわかりません', 'zh': '嗯…我不太确定'}
# 영문 낱말(식별자)은 통째로, 한글, 가나, 한자는 두 글자 조각으로 - 일본어, 중국어 질문도 기억에 걸리게
TOKEN_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_.]{2,}|[가-힣]+|[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+')


def _grams(text):
    out = set()
    for w in TOKEN_RE.findall(text.lower()):
        if not w[0].isascii():
            out.update(w[i:i + 2] for i in range(max(1, len(w) - 1)))
        else:
            out.add(w)
    return out


def ask(layer, q, history, lang='ko'):
    import math
    q = (q or '').strip()[:500]
    if not q:
        raise ValueError(E('srv.empty'))
    d = layer_data(layer)
    mems = d['memories']
    if not mems:
        return {'answer': ASK_EMPTY[lang], 'refs': []}
    docs = [_grams(' '.join((m['title'], m['line'], d['heads'].get(m['path'], '')))) for m in mems]
    qg = _grams(q + ' ' + ' '.join(h.get('q', '') for h in (history or [])[-2:]))
    df = {}
    for g in docs:
        for t in g & qg:
            df[t] = df.get(t, 0) + 1
    n = len(docs)
    scored = sorted(((sum(math.log(1 + n / df[t]) for t in g & qg), i) for i, g in enumerate(docs)), reverse=True)
    top = [i for sc, i in scored[:6] if sc > 0]
    if len(top) < 3:
        # 걸린 기억이 적으면(다른 언어로 묻거나 낱말이 겹치지 않을 때) 최근 기억으로 채운다 - 답은 Haiku 가 기억 안에서만 고른다
        top += [i for i in sorted(range(n), key=lambda i: -mems[i].get('mtime', 0)) if i not in top][:6 - len(top)]
    if FAKEAI:
        return {'answer': '(모의) %s 에 대해 기억 %d개를 찾았어요.' % (q[:20], len(top)),
                'refs': [{'path': mems[i]['path'], 'title': mems[i]['title']} for i in top[:3]]}
    rows = []
    for k, i in enumerate(top, 1):
        m = mems[i]
        body = _read(os.path.join(CX, m['path']))[:1800]
        rows.append('[%d] %s\n%s' % (k, m['title'], body))
    hist = '\n'.join('User: %s\nBrain: %s' % (h.get('q', '')[:200], h.get('a', '')[:300]) for h in (history or [])[-3:])
    prompt = ('%s\n\n--- memories\n%s\n\n--- question\n%s') % (('--- earlier conversation\n' + hist) if hist else '', '\n\n'.join(rows) or '(no related memories)', q)
    name = layer.split('/', 1)[1] if '/' in layer else 'shared'
    r, raw = haiku_json(prompt, ASK_SYS % (name, LANG.NAMES[lang], TONE[lang]), timeout=90, what='ask')
    if r is None:   # 두 번 다 JSON 이 깨졌다 - 답 문장만이라도 살린다
        m = re.search(r'"answer"\s*:\s*"(.*?)"\s*,\s*"refs"\s*:\s*\[([^\]]*)\]', raw, re.S)
        if m:
            r = {'answer': m.group(1).replace('\\n', '\n').replace('\\"', '"'), 'refs': [int(x) for x in re.findall(r'\d+', m.group(2))]}
        else:
            r = {'answer': re.sub(r'^```\w*|```$', '', raw.strip()).strip(), 'refs': []}
    refs = []
    for k in r.get('refs') or []:
        if isinstance(k, int) and 1 <= k <= len(top):
            m = mems[top[k - 1]]
            refs.append({'path': m['path'], 'title': m['title']})
    return {'answer': str(r.get('answer') or ASK_UNSURE[lang])[:1000], 'refs': refs[:4]}


# ---------------------------------------------------------------- 동작 (기존 통로로만)
def run(args, timeout=30, cwd=None):
    args = plat.argv(args)   # Windows 는 Git Bash 를 고르고(WSL bash 가 아니라) 경로를 / 표기로
    p = subprocess.run(args, capture_output=True, timeout=timeout, cwd=cwd or BRAIN,
                       env=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8'))
    out = (p.stdout or b'') + (p.stderr or b'')
    return out.decode('utf-8', 'replace').strip(), p.returncode


def root_of(slug):
    row = next((r for r in registry() if r['slug'] == slug), None)
    if not row:
        raise ValueError(E('srv.bad_project'))
    return row['root']


def feed(slug, text):
    text = (text or '').strip()
    if not text:
        raise ValueError(E('srv.empty'))
    if DRYRUN:
        root_of(slug)
        track('feed', '', slug)
        return {'ok': True, 'out': '(모의) 큐 투입: %s' % text[:40]}
    out, rc = run(['bash', os.path.join(SCRIPTS, 'remember.sh'), '--root', root_of(slug),
                   '%s - %s' % (text[:2000], fb_text('evidence') % datetime.date.today().isoformat())])
    if rc == 0:
        track('feed', out, slug)
    return {'ok': rc == 0, 'out': out}


def correct(slug, rel, text):
    text = (text or '').strip()
    if not text:
        raise ValueError(E('srv.empty'))
    read_memory(rel)   # 경로 검사
    root = root_of(slug) if slug else '/'   # 공용,스택 기억은 프로젝트 밖(/)으로 넘긴다 - 레이어는 해마가 정한다
    if DRYRUN:
        return {'ok': True, 'out': '(모의) 정정 투입: %s' % rel}
    out, rc = run(['bash', os.path.join(SCRIPTS, 'remember.sh'), '--root', root,
                   '%s - %s' % (fb_text('outdated') % (rel, text[:2000]), fb_text('evidence') % datetime.date.today().isoformat())])
    return {'ok': rc == 0, 'out': out}


TIDY_TARGET = 0.7   # 앱 최적화의 목표: 색인 파일마다 글자 수와 항목 수가 상한의 70% 이하 (기억 본문은 줄이지 않는다)


def tidy(layer, mode, dry):
    """[정리] 그 레이어의 조각을 해마 sweep 큐로 넣는다
    - mode=over 면 목표(70%)를 넘은 색인과 색인 없는 기억 조각만, all 이면 전부
    - 목표를 넘은 색인은 payload.goal 로 넘긴다 - 해마가 압축하고 주제별로 나눠 그 파일을 목표 아래로 만든다(§5)
    """
    check_layer(layer)
    sl = [s for s in slices.compute(CX, 40000) if s['layer'] == layer and not s['id'].endswith(':dormant.md')]
    heavy = {}
    for ix in layer_data(layer)['indexes']:
        r = max(ix['chars'] / float(ix['cap']), ix['items'] / float(ITEM_CAP))
        if r > TIDY_TARGET:
            heavy[ix['file']] = {'file': ix['file'], 'chars': ix['chars'], 'cap': ix['cap'], 'items': ix['items'],
                                 'item_cap': ITEM_CAP, 'ratio': round(r, 3)}
    if mode == 'over':
        sl = [s for s in sl if s['id'].split(':', 1)[1].split('#')[0] in heavy or '(미등록)' in s['id']]
    for s in sl:
        f = s['id'].split(':', 1)[1].split('#')[0]
        if f in heavy:
            s['goal'] = {'kind': 'lighten', 'target_ratio': TIDY_TARGET, 'file': heavy[f],
                         'why': fb_text('tidy')}
    plan = [{'id': s['id'], 'tok': s['tok'], 'files': len(s['files']), 'goal': bool(s.get('goal'))} for s in sl]
    busy = sum(1 for q in hippo()['queue'] if q.get('mode') == 'sweep' and str(q.get('slice') or '').startswith(layer + ':'))
    res = {'slices': plan, 'tok': sum(s['tok'] for s in sl), 'count': len(sl), 'target': TIDY_TARGET, 'heavy': len(heavy), 'busy': busy}
    if dry or not sl or busy:   # 이미 이 뇌의 정리가 대기 중이면 다시 쌓지 않는다(여러 번 눌러 같은 일이 겹겹이 쌓이지 않게)
        return res
    if DRYRUN:
        res['enqueued'] = ['(모의) 큐 투입: %s' % s['id'] for s in sl]
        track('tidy', '', layer[9:] if layer.startswith('projects/') else '', len(sl), layer=layer, before=_weight(layer))
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
        raise RuntimeError(E('srv.queue_fail', out.strip()[:200]))
    logs = []
    for r in sorted(glob.glob(os.path.join(tmp, 'req-*.json'))):
        o, _ = run(['bash', os.path.join(SCRIPTS, 'hippocampus-enqueue.sh'), r])
        logs.append(o.splitlines()[0] if o else '')
    res['enqueued'] = logs
    track('tidy', '\n'.join(logs), layer[9:] if layer.startswith('projects/') else '', len(sl), layer=layer, before=_weight(layer))
    return res


def hippo_stop():
    """[해마 멈추기] 지금 하던 일만 끝내고 멈춘다 - 대기 중인 일은 그대로 남는다"""
    if DRYRUN:
        return {'ok': True}
    os.makedirs(HC, exist_ok=True)
    if hippo()['alive']:
        open(os.path.join(HC, 'stop'), 'w').close()
    return {'ok': True}


def hippo_clear():
    """[대기 비우기] 기다리는 일을 .hippocampus/held-<시각>/ 으로 옮긴다(지우지 않는다). 처리 중인 일은 건드리지 않는다"""
    qs = sorted(glob.glob(os.path.join(HC, 'queue', '*.json')))
    if DRYRUN or not qs:
        return {'ok': True, 'moved': 0 if not DRYRUN else len(qs)}
    held = os.path.join(HC, 'held-%s' % time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(held, exist_ok=True)
    moved = []
    for p in qs:
        try:
            os.replace(p, os.path.join(held, os.path.basename(p)))
            moved.append(os.path.basename(p)[:-5])
        except OSError:
            pass
    # 옮긴 일만 기다리던 알림은 지운다 - 끝나지 않을 일을 기다리지 않게
    with _PEND_LOCK:
        gone = set(moved)
        items = [x for x in (_json(PENDING, []) or []) if isinstance(x, dict) and not (set(x.get('ids') or []) & gone)]
        if os.path.exists(PENDING):
            with open(PENDING + '.tmp', 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False)
            os.replace(PENDING + '.tmp', PENDING)
    return {'ok': True, 'moved': len(moved), 'held': plat.norm(held)}


def sleep_now():
    if DRYRUN:
        return {'ok': True}
    lg = os.path.join(HC, 'logs')
    os.makedirs(lg, exist_ok=True)
    with open(os.path.join(lg, 'sleep-manual.out'), 'a') as out:
        subprocess.Popen(plat.argv(['bash', os.path.join(SCRIPTS, 'sleep.sh')]), stdin=subprocess.DEVNULL, stdout=out,
                         stderr=subprocess.STDOUT, cwd=BRAIN, **plat.detach_kw())
    return {'ok': True}


# ---------------------------------------------------------------- 맡긴 일의 반영 알림
# 앱에서 해마에게 맡긴 일(먹이, 우체통, 정리, 등록)의 큐 id 를 .active/pending.json 에 남기고, done 파일이 생기면 앱이 한 번 알린다.
PENDING = os.path.join(ACTIVE, 'pending.json')
QID_RE = re.compile(r'\d{8}T\d{6}Z-[A-Za-z0-9_-]+')
_PEND_LOCK = threading.Lock()


def _weight(layer):
    """[머리 무게] 그 레이어 색인들의 가장 큰 상한 비율 (summarize 의 capacity 와 같은 계산)"""
    try:
        return round(max([max(ix['chars'] / float(ix['cap']), ix['items'] / float(ITEM_CAP)) for ix in layer_data(layer)['indexes']] or [0]), 3)
    except Exception:
        return None


def track(kind, out, slug='', n=1, **extra):
    """[맡긴 일 남기기] out(큐 투입 출력)에서 큐 id 를 찾아 남긴다. 모의 실행은 가짜 id 로 3초 뒤 끝난 것으로 친다"""
    ids = QID_RE.findall(out or '')
    if DRYRUN:
        ids = ['dry-%s-%s' % (kind, secrets.token_hex(3))]
    if not ids:
        return
    with _PEND_LOCK:
        items = [x for x in (_json(PENDING, []) or []) if isinstance(x, dict) and time.time() - x.get('t', 0) < 3 * 86400]
        items.append(dict({'ids': ids, 'kind': kind, 'slug': slug or '', 'n': n, 't': int(time.time())}, **extra))
        os.makedirs(ACTIVE, exist_ok=True)
        with open(PENDING + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(items[-50:], f, ensure_ascii=False)
        os.replace(PENDING + '.tmp', PENDING)


def applied():
    """[끝난 일] 맡긴 일 가운데 큐 id 가 모두 done 이 된 것 - [{key, kind, slug, n, status, first}]. 아직이면 waiting 에 센다"""
    out, waiting = [], 0
    for x in _json(PENDING, []) or []:
        if not isinstance(x, dict) or not isinstance(x.get('ids'), list):
            continue
        sts, first = [], ''
        for i in x['ids']:
            if str(i).startswith('dry-'):
                sts.append('done' if time.time() - x.get('t', 0) > 3 else None)
                first = first or '(dry-run)'
                continue
            r = _json(os.path.join(HC, 'done', os.path.basename(str(i)) + '.json'))
            if not isinstance(r, dict):
                sts.append(None)
                continue
            sts.append(r.get('status') or '?')
            first = first or next((l for l in (r.get('summary') or '').splitlines() if l.strip()), '')[:160]
        if None in sts:
            waiting += 1
            continue
        bad = [st for st in sts if st not in ('done', 'partial')]
        row = {'key': '%s:%d' % (x['ids'][0], x.get('t', 0)), 'kind': x.get('kind'), 'slug': x.get('slug') or '',
               'n': x.get('n') or 1, 'status': bad[0] if bad else 'done', 'first': first}
        if x.get('kind') == 'tidy' and isinstance(x.get('layer'), str) and isinstance(x.get('before'), (int, float)):
            try:
                check_layer(x['layer'])
                row.update(before=x['before'], after=_weight(x['layer']))
            except ValueError:
                pass
        out.append(row)
    return {'done': out, 'waiting': waiting}


def applied_ack(keys):
    keys = set(k for k in (keys or []) if isinstance(k, str))
    with _PEND_LOCK:
        items = [x for x in (_json(PENDING, []) or []) if isinstance(x, dict) and isinstance(x.get('ids'), list)
                 and '%s:%d' % (x['ids'][0], x.get('t', 0)) not in keys]
        with open(PENDING + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False)
        os.replace(PENDING + '.tmp', PENDING)
    return {'ok': True}


# ---------------------------------------------------------------- 아직 모르는 프로젝트, 지금 등록
_CAND = {'t': 0, 'items': []}


def candidates(force=False):
    """[등록 후보] 최근 14일 Claude Code 대화록이 있는 등록 안 된 git 폴더(replay.suggest_register 를 느슨하게). 10분 캐시"""
    if DRYRUN:
        return [{'root': '/Users/demo/dev/new-app', 'name': 'new-app', 'sessions': 3, 'prompts': 12, 'last': int(time.time()) - 3600}]
    if not force and time.time() - _CAND['t'] < 600:
        return _CAND['items']
    try:
        import replay
        rows = replay.suggest_register(since_days=14, min_sessions=1, min_prompts=2, with_time=True)
    except Exception:
        rows = []
    items = [{'root': r, 'name': os.path.basename(r.rstrip('/')), 'sessions': s, 'prompts': pr, 'last': int(mt)} for r, s, pr, mt in rows[:8]]
    _CAND.update(t=time.time(), items=items)
    return items


def register_project(root):
    """[지금 등록] 후보 목록에 있는 폴더만 받는다(앱이 아무 경로나 등록시키지 않게)"""
    if not any(c['root'] == root for c in candidates()):
        raise ValueError(E('srv.bad_project'))
    if DRYRUN:
        track('register', '', os.path.basename(root))
        return {'code': 0, 'message': '(dry-run) %s' % root, 'slug': os.path.basename(root)}
    out, rc = run([sys.executable, os.path.join(SCRIPTS, 'register.py'), '--json', root], timeout=30)
    try:
        r = json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise RuntimeError(E('srv.queue_fail', out[:200]))
    if r.get('code') == 0 and r.get('id'):
        track('register', r['id'], r.get('slug') or '')
        _CAND['t'] = 0
    return r


# ---------------------------------------------------------------- 보관함 (잊은 기억)
ARCH_RE = re.compile(r'^>\s*ARCHIVED\s*\(([^)]*)\)\s*(?:@\s*(\S+))?\s*(?:-\s*(.*))?$', re.M)


def archive_list(layer):
    """[보관함] <레이어>/_archive/*.md - 해마가 잊으면서 옮긴 기억. [{path, title, reason, when, note, mtime}]"""
    check_layer(layer)
    base = os.path.join(CX, *layer.split('/'), '_archive')
    out = []
    for p in sorted(glob.glob(os.path.join(base, '**', '*.md'), recursive=True)):
        txt = _read(p, 4000)
        m = ARCH_RE.search(txt)
        title = next((l[2:].strip() for l in txt.splitlines() if l.startswith('# ')), os.path.basename(p)[:-3])
        reason = (m.group(1).strip() if m else '').split(':')[0]
        out.append({'path': os.path.relpath(p, CX).replace(os.sep, '/'), 'title': title[:160], 'reason': reason,
                    'when': (m.group(2) or '').strip()[:20] if m else '', 'note': (m.group(3) or '').strip()[:200] if m else '',
                    'mtime': int(os.path.getmtime(p))})
    out.sort(key=lambda x: -x['mtime'])
    return out[:300]


# ---------------------------------------------------------------- 백업
def make_backup():
    if DRYRUN:
        return {'path': os.path.join(os.path.expanduser('~'), 'Downloads', 'brain-backup-dry-run.zip'), 'n': 0,
                'restore': 'bash %s restore <zip>' % plat.norm(os.path.join(SCRIPTS, 'backup.sh'))}
    import backup
    path, n = backup.make()
    return {'path': plat.norm(path), 'n': n, 'restore': 'bash %s restore <zip>' % plat.norm(os.path.join(SCRIPTS, 'backup.sh'))}


def set_config(action, value):
    allowed = {'on': [], 'off': [], 'preset': ['default', 'eco', 'quality'], 'lang': list(LANG.LANGS),
               'mute': [r['slug'] for r in registry()], 'unmute': [r['slug'] for r in registry()]}
    if action not in allowed or (allowed[action] and value not in allowed[action]) or (action in ('mute', 'unmute') and not value):
        raise ValueError(E('srv.bad_feedback'))
    if DRYRUN:
        if action in ('mute', 'unmute'):
            p = os.path.join(ACTIVE, 'config')
            cur = [x for x in config()['mute'] if x != value] + ([value] if action == 'mute' else [])
            lines = [x for x in _read(p).splitlines() if x and not x.startswith('mute=')] + ['mute=' + ','.join(cur)]
            with open(p, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
        if action == 'lang':
            p = os.path.join(ACTIVE, 'config')
            lines = [x for x in _read(p).splitlines() if x and not x.startswith('lang=')] + ['lang=' + value]
            with open(p, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
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
            return self._send(401, {'error': 'token'})
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
                return self._send(200, topics(q('l'), q('force') == '1', lang_of(q('lang'))))
            if u.path == '/api/explain':
                return self._send(200, explain(q('p'), lang_of(q('lang'))))
            if u.path == '/api/feedback':
                return self._send(200, {'items': feedback_list(q('l'))})
            if u.path == '/api/hippo':
                return self._send(200, hippo())
            if u.path == '/api/applied':
                return self._send(200, applied())
            if u.path == '/api/candidates':
                return self._send(200, {'items': candidates(q('force') == '1')})
            if u.path == '/api/archive':
                return self._send(200, {'items': archive_list(q('l'))})
            if u.path == '/api/persona':
                slug, L = q('slug'), lang_of(q('lang'))
                g = persona.load(slug)
                cat = persona.catalog(L)
                return self._send(200, {'graph': g, 'compiled': persona.compile_graph(g, L) if g else None, 'catalog': cat})
            if u.path == '/api/breed':
                L = lang_of(q('lang'))
                g = persona.from_breed(q('b'), L)
                return self._send(200, {'graph': g, 'compiled': persona.compile_graph(g, L)})
            return self._send(404, {'error': 'no api'})
        except Exception as e:
            return self._send(400, {'error': err_text(e)})

    def do_POST(self):
        LAST_HIT[0] = time.time()
        if not self._host_ok():
            return self._send(403, {'error': 'host'})
        u = urlparse(self.path)
        if not self._auth({}):
            return self._send(401, {'error': 'token'})
        try:
            n = int(self.headers.get('Content-Length') or 0)
            body = json.loads(self.rfile.read(min(n, 2 * 1024 * 1024)).decode('utf-8') or '{}')
            if u.path == '/api/persona/preview':
                return self._send(200, {'compiled': persona.compile_graph(body.get('graph'), lang_of(body.get('lang')))})
            if u.path == '/api/persona/save':
                slug = body.get('slug') or ''
                root_of(slug)
                g = persona.save(slug, body.get('graph'))
                return self._send(200, {'graph': g, 'compiled': persona.compile_graph(g, lang_of(body.get('lang')))})
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
                return self._send(200, ask(body.get('layer') or '', body.get('q') or '', body.get('history') or [], lang_of(body.get('lang'))))
            if u.path == '/api/config':
                return self._send(200, set_config(body.get('action'), body.get('value')))
            if u.path == '/api/hippo/stop':
                return self._send(200, hippo_stop())
            if u.path == '/api/hippo/clear':
                return self._send(200, hippo_clear())
            if u.path == '/api/applied/ack':
                return self._send(200, applied_ack(body.get('keys')))
            if u.path == '/api/register':
                return self._send(200, register_project(body.get('root') or ''))
            if u.path == '/api/backup':
                return self._send(200, make_backup())
            if u.path == '/api/quit':
                threading.Thread(target=lambda: (time.sleep(0.3), self.server.shutdown()), daemon=True).start()
                return self._send(200, {'ok': True})
            return self._send(404, {'error': 'no api'})
        except Exception as e:
            return self._send(400, {'error': err_text(e)})


def err_text(e):
    """[사용자에게 보일 오류 글] 우리가 낸 오류(ValueError, RuntimeError)는 글만, 그 밖은 종류까지"""
    if isinstance(e, (ValueError, RuntimeError)) and str(e) and not isinstance(e, json.JSONDecodeError):
        return str(e)
    return '%s: %s' % (e.__class__.__name__, e)


def idle_watch(srv):
    while True:
        time.sleep(60)
        if time.time() - LAST_HIT[0] > IDLE_EXIT:
            srv.shutdown()
            return


def code_stamp():
    """[코드 도장] 서버, 화면, 스크립트 파일의 가장 늦은 수정 시각 - editor.sh 가 같은 계산으로 비교해 바뀌었으면 서버를 다시 띄운다"""
    fs = [os.path.abspath(__file__)] + glob.glob(os.path.join(HERE, 'web', '*')) + glob.glob(os.path.join(SCRIPTS, '*.py'))
    return int(max((os.path.getmtime(f) for f in fs if os.path.isfile(f)), default=0))


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
            json.dump({'pid': os.getpid(), 'port': port, 'token': TOKEN, 'started': int(time.time()), 'code': code_stamp()}, f)
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
