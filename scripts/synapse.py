#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain synapse - 단서와 기억 사이의 연결을 경험으로 배운다(헤브 학습: 함께 발화한 것끼리 연결이 강해진다).

세션이 기억(lesson 본문)을 연 순간, 그 직전 WINDOW 개 사건 안에 있던 단서(만진 파일 이름, 그 폴더, 새로 부른 API,
에러의 식별자, 요청 속 식별자)와 그 기억을 짝지어 '몇 개 세션에서 함께 일어났나'를 센다.
  지지도 = 짝이 함께 일어난 세션 수, 확신도 = 지지도 / 그 단서가 나온 세션 수,
  향상도 = 확신도 / (그 기억이 열린 세션 수 / 전체 세션 수) - 단서와 무관하게 늘 열리는 기억(절차 카드, 사실 파일)을 거른다.
  SUPPORT_MIN 개 세션 이상, 확신도 CONF_MIN 이상, 향상도 LIFT_MIN 이상인 연결만 남긴다. 대상은 lessons/ 본문만. 단서마다 강한 순으로 PER_CUE 개.
thalamus 는 단서가 오면 이 표에서 연결된 기억을 함께 떠올린다(인덱스 줄 일치로는 못 찾는 개념 수준의 기억).

사용법:
  synapse.py learn [--days 120] [--out <synapses.json>]     registry 프로젝트의 대화록에서 배운다(sleep.sh 가 밤마다)
  synapse.py learn --events <assoc.jsonl> --until <ISO 시각> --out <파일>   평가용: 미리 뽑은 사건 열에서 그 시각 전 세션으로만
  synapse.py cues --path <파일> | --api <이름> | --error <글>   단서 뽑기 시험
표 형식: {"generated": 날짜, "cues": {단서: [[기억 상대 경로, 지지도, 확신도], ...]}}
"""
import collections
import glob
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
CX = os.path.join(BRAIN, 'cortex')
OUT = os.path.join(CX, '.hippocampus', 'synapses.json')
# 대화록 폴더 - Claude Code 설정 폴더(CLAUDE_CONFIG_DIR, 없으면 ~/.claude)의 projects/
PROJECTS = os.path.join(os.environ.get('CLAUDE_CONFIG_DIR') or os.path.expanduser('~/.claude'), 'projects')

WINDOW = 25
SUPPORT_MIN = 2
CONF_MIN = 0.15
LIFT_MIN = 3.0
PER_CUE = 3
MEM_MARKS = ('/brain/cortex/', '/n-worker/notebook/')
TMP = ('/tmp/', '/private/tmp/', '/var/folders/', '/private/var/folders/')
API_RE = re.compile(r'\b([A-Z][A-Za-z0-9_]*(?:\.[A-Z][A-Za-z0-9_]*)+)\s*[(<]')
MEM_PATH = re.compile(r'/(?:brain/cortex|n-worker/notebook)/([^\s\'"`|;&>)\]]+\.md)')
FILE_TOK = re.compile(r'[\w@+./-]+\.(?:cs|prefab|asset|unity|mat|shader|anim|controller|uss|uxml|asmdef|json|ojn|ojm|py|ts|js|sh)\b')
EXC_RE = re.compile(r'\b([A-Z][A-Za-z0-9_]*(?:Exception|Error))\b|\b(CS\d{4})\b')
ID_RE = re.compile(r'`([A-Za-z_][\w.]{3,60})`|\b([A-Z][a-z]+[A-Z][A-Za-z0-9]{2,})\b')
GENERIC = frozenset('fileID guid PrefabInstance MonoBehaviour RectTransform GameObject Transform SerializeField Assets Scripts '
                    'NullReferenceException InvalidOperationException ArgumentException MissingReferenceException Exception Error'.split())
SYS_PREFIX = ('Caveat:', '<task-notification', '<local-command', '[Request interrupted', '[SYSTEM NOTIFICATION',
              'This session is being continued', 'Base directory for this skill')


def norm(c):
    return c.lower()


def file_cues(path):
    """[파일 하나의 단서] 줄기 + 부모 폴더 둘(file:NotePlaneView, dir:Play/View)"""
    p = path.replace('\\', '/').rstrip('/')
    parts = [x for x in p.split('/') if x]
    if not parts:
        return []
    stem = os.path.splitext(parts[-1])[0]
    if stem.endswith('.cs'):
        stem = stem[:-3]
    out = []
    if len(stem) >= 4 and not (stem.isalpha() and stem.islower()):
        out.append('file:' + norm(stem))
    if len(parts) >= 3:
        out.append('dir:' + norm('/'.join(parts[-3:-1])))
    return out


def api_cues(text):
    out = []
    for a in API_RE.findall(text or ''):
        if a in GENERIC:
            continue
        out.append('api:' + norm(a))
        m = a.rsplit('.', 1)[-1]
        if len(m) >= 6 and any(ch.isupper() for ch in m[1:]):
            out.append('api:' + norm(m))
    return out


def err_cues(text):
    out = []
    for m in EXC_RE.finditer((text or '')[:4000]):
        c = m.group(1) or m.group(2)
        if c and c not in GENERIC:
            out.append('err:' + norm(c))
    return out


def prompt_cues(text):
    out = []
    for m in ID_RE.finditer((text or '')[:4000]):
        c = m.group(1) or m.group(2)
        if c and c not in GENERIC and len(c) >= 5:
            out.append('id:' + norm(c.rsplit('/', 1)[-1]))
    return out


# ---------------------------------------------------------------- 사건 열
def text_of(c):
    if isinstance(c, str):
        return c
    return '\n'.join(b.get('text') or '' for b in c or [] if isinstance(b, dict) and b.get('type') == 'text')


def is_index(rel):
    b = os.path.basename(rel).lower()
    return 'index' in b or 'router' in b or b in ('registry.md', '.pending.md', 'dormant.md')


def events_of(path):
    """[대화록 하나 -> 사건 열] [('c', 단서) | ('L', 기억 상대 경로)]"""
    ev = []
    pend = {}
    import replay
    if replay.automated(path):
        return ev, None   # 사람 없는 자동 실행 대화록은 배우지 않는다
    try:
        fh = open(path, encoding='utf-8', errors='replace')
    except OSError:
        return ev, None
    t0 = None
    for line in fh:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get('isSidechain'):
            continue
        t0 = t0 or d.get('timestamp')
        m = d.get('message') or {}
        if d.get('type') == 'user':
            c = m.get('content')
            if isinstance(c, list) and any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in c):
                for b in c:
                    if isinstance(b, dict) and b.get('type') == 'tool_result' and b.get('is_error') and pend.pop(b.get('tool_use_id'), None):
                        rc = b.get('content')
                        rc = '\n'.join(x.get('text', '') for x in rc if isinstance(x, dict)) if isinstance(rc, list) else (rc or '')
                        ev += [('c', x) for x in err_cues(rc)]
                continue
            if d.get('isMeta') or d.get('isCompactSummary'):
                continue
            t = text_of(m.get('content'))
            if t and not t.lstrip().startswith(SYS_PREFIX):
                ev += [('c', x) for x in prompt_cues(re.sub(r'<system-reminder>.*?</system-reminder>', '', t, flags=re.S))]
        elif d.get('type') == 'assistant':
            for b in m.get('content') or []:
                if not (isinstance(b, dict) and b.get('type') == 'tool_use'):
                    continue
                nm, inp = b.get('name'), b.get('input') or {}
                if nm == 'Read':
                    fp = inp.get('file_path') or ''
                    mm = MEM_PATH.search(fp)
                    if mm:
                        if not is_index(mm.group(1)):
                            ev.append(('L', mm.group(1)))
                    elif not fp.startswith(TMP) and '/.claude/' not in fp:
                        ev += [('c', x) for x in file_cues(fp)]
                elif nm in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
                    fp = inp.get('file_path') or inp.get('notebook_path') or ''
                    new = (inp.get('new_string') or inp.get('content') or '') + ''.join('\n' + (x.get('new_string') or '') for x in inp.get('edits') or [])
                    ev += [('c', x) for x in api_cues(new)]
                    if fp and not fp.startswith(TMP) and '/.claude/' not in fp and not MEM_PATH.search(fp):
                        ev += [('c', x) for x in file_cues(fp)]
                elif nm == 'Bash':
                    cmd = inp.get('command') or ''
                    hits = MEM_PATH.findall(cmd)
                    if hits:
                        ev += [('L', h) for h in hits if not is_index(h)]
                    else:
                        ev += [('c', x) for x in api_cues(cmd)]
                        for fm in FILE_TOK.finditer(cmd):
                            if not fm.group(0).startswith(TMP):
                                ev += [('c', x) for x in file_cues(fm.group(0))]
                    pend[b.get('id')] = True
    return ev, t0


def assoc_events(d):
    """[extract_assoc.py 형식 -> 사건 열] 평가용"""
    ev = []
    for e in d['ev']:
        k = e['k']
        if k == 'L':
            ev.append(('L', e['rel']))
        elif k == 'f':
            ev += [('c', x) for x in file_cues(e['path'])]
        elif k == 'api':
            ev += [('c', x) for x in api_cues(e['name'] + '(')]
        elif k == 'err':
            ev += [('c', x) for x in err_cues(e['text'])]
        elif k == 'p':
            ev += [('c', x) for x in prompt_cues(e['text'])]
    return ev


# ---------------------------------------------------------------- 배우기
def current_paths():
    base = collections.defaultdict(list)
    for dp, dn, fn in os.walk(CX):
        dn[:] = [x for x in dn if x not in ('_archive', '.hippocampus', 'scripts')]
        for f in fn:
            if f.endswith('.md'):
                base[f].append(os.path.relpath(os.path.join(dp, f), CX))
    return base


def learn_from(sessions):
    """[사건 열들 -> 연결 표] sessions = [[('c', 단서) | ('L', 옛 경로)]]"""
    base = current_paths()
    co = collections.defaultdict(collections.Counter)
    seen_cue = collections.Counter()
    opened = collections.Counter()
    for ev in sessions:
        ls = set()
        for k, x in ev:
            if k == 'L':
                cand = base.get(os.path.basename(x), [])
                if len(cand) == 1:
                    ls.add(cand[0])
        for rel in ls:
            opened[rel] += 1
        cues_in = set(x for k, x in ev if k == 'c')
        for c in cues_in:
            seen_cue[c] += 1
        pairs = set()
        for i, (k, x) in enumerate(ev):
            if k != 'L':
                continue
            cand = base.get(os.path.basename(x), [])
            if len(cand) != 1:
                continue
            rel = cand[0]
            if '/lessons/' not in '/' + rel:
                continue
            for j in range(max(0, i - WINDOW), i):
                if ev[j][0] == 'c':
                    pairs.add((ev[j][1], rel))
        for c, rel in pairs:
            co[c][rel] += 1
    table = {}
    total = float(max(1, len(sessions)))
    for c, cnt in co.items():
        n = seen_cue[c] or 1
        keep = [(rel, s, round(s / float(n), 3)) for rel, s in cnt.items()
                if s >= SUPPORT_MIN and s / float(n) >= CONF_MIN and (s / float(n)) / (opened[rel] / total) >= LIFT_MIN]
        if keep:
            keep.sort(key=lambda x: (-(x[1] * x[2]), x[0]))
            table[c] = [list(x) for x in keep[:PER_CUE]]
    return table


def registry_roots():
    rows = []
    try:
        for line in open(os.path.join(CX, 'registry.md'), encoding='utf-8'):
            c = [x.strip().strip('`') for x in line.strip().strip('|').split('|')]
            if line.startswith('|') and len(c) >= 3 and c[0].startswith('/'):
                rows.append(c[0].rstrip('/'))
    except OSError:
        pass
    return rows


def arg(a, k, d=None):
    return a[a.index(k) + 1] if k in a else d


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 2
    if a[0] == 'learn':
        out = arg(a, '--out', OUT)
        if '--events' in a:
            until = arg(a, '--until', '9999')
            sessions = []
            for line in open(arg(a, '--events'), encoding='utf-8'):
                d = json.loads(line)
                if (d.get('t0') or '') < until:
                    sessions.append(assoc_events(d))
        else:
            days = float(arg(a, '--days', '120'))
            now = time.time()
            base = PROJECTS
            sessions = []
            for root in registry_roots():
                key = re.sub(r'[^A-Za-z0-9]', '-', root)
                for dd in [os.path.join(base, key)] + glob.glob(os.path.join(base, key + '-*')):
                    for p in glob.glob(os.path.join(dd, '*.jsonl')):
                        try:
                            if now - os.path.getmtime(p) > days * 86400:
                                continue
                        except OSError:
                            continue
                        ev, _ = events_of(p)
                        if ev:
                            sessions.append(ev)
        table = learn_from(sessions)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        tmp = out + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({'generated': time.strftime('%Y-%m-%d'), 'sessions': len(sessions), 'cues': table}, f, ensure_ascii=False)
        os.replace(tmp, out)
        print('# 세션 %d, 연결 단서 %d, 연결 %d' % (len(sessions), len(table), sum(len(v) for v in table.values())))
        return 0
    if a[0] == 'cues':
        if '--path' in a:
            print(file_cues(arg(a, '--path')))
        if '--api' in a:
            print(api_cues(arg(a, '--api') + '('))
        if '--error' in a:
            print(err_cues(arg(a, '--error')))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
