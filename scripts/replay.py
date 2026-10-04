#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 대화록 재생 - 세션 대화록(Claude Code 가 실시간으로 쓰는 단기 기억 버퍼)에서 기억할 만한 장면만 추려 hippocampus 에게 넘긴다.

두 속도(사람의 해마와 같다):
  awake  깨어 있는 중 되짚기. thalamus 가 턴 끝, 압축 직전, 세션 끝에 부른다. 지난번 처리 위치 뒤의 새 구간만 본다.
  scan   잠자며 되짚기. sleep.sh 가 밤에 부른다. 아직 처리 안 된 구간 전부 + 활발한 미등록 프로젝트 등록 제안.
처리 위치(대화록별 바이트 위치)는 .active/replay-marks.json 하나를 둘이 같이 쓴다 - 같은 구간을 두 번 넘기지 않는다.

사용법:
  replay.py awake --transcript <jsonl> --cwd <경로> --sid <세션> [--force] [--min-score S]
  replay.py scan --out <요약 폴더> --reqs <요청 폴더> [--max N] [--min-score S] [--first-days D]
  replay.py digest <jsonl> [--from <바이트>]      요약 한 건을 표준 출력으로(시험용)
점수 = 정정 3 + 결정 3 + 기억 요청 5 + 거부 2 + 도구 실패(최대 5) + 반복 조사(최대 3) + 요청 5개 이상이면 1(두드러짐 - 편도체 구실).
"""
import glob
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plat  # noqa: E402  경로 비교(macOS, Linux, Windows)

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
CX = os.path.join(BRAIN, 'cortex')
ACTIVE = os.path.join(BRAIN, '.active')
MARKS = os.path.join(ACTIVE, 'replay-marks.json')
AWAKE_LOG = os.path.join(ACTIVE, 'awake.json')
REPLAY_DIR = os.path.join(CX, '.hippocampus', 'replay')
# 대화록 폴더 - Claude Code 설정 폴더(CLAUDE_CONFIG_DIR, 없으면 ~/.claude)의 projects/
PROJECTS = os.path.join(os.environ.get('CLAUDE_CONFIG_DIR') or os.path.expanduser('~/.claude'), 'projects')

AWAKE_MIN = 6            # 깨어 있는 중 재생을 부를 점수 하한(압축 직전,세션 끝은 FORCE_MIN)
FORCE_MIN = 3
AWAKE_GAP = 20 * 60      # 같은 대화록의 깨어 있는 중 재생 사이 최소 간격(초)
AWAKE_PER_HOUR = 4       # 모든 세션을 합친 깨어 있는 중 재생 상한(한 시간) - 사용량 보호
MAX_CHARS = 36000
A_CHARS = 1500           # 어시스턴트 답 하나를 담는 글자 상한 - 세션은 알아낸 수치, 메커니즘, 파일 위치를 답에 쓴다(판정: 앞 500자만 담으면 사실의 절반을 놓쳤다)
EVIDENCE_RE = re.compile(r'(\.cs:\d|\.py:\d|:\d{2,}|\d+(?:\.\d+)?\s*(?:ms|초|%|Hz|px|배)|원인|결론|실측|측정|확인했|때문|함정|재현|수치|근거)')
CORRECT_RE = re.compile(r'(아니[야요,. ]|아닌데|아니라|틀렸|틀린|잘못|다시 해|그게 아니|하지 ?마|말했잖|이미 말|원래는|그렇게 하면 안|왜 .{0,20}(했|안 ?했|없))')
DECIDE_RE = re.compile(r'(앞으로|항상|절대|반드시|무조건|기본으로|규칙|정책|결정|하자$|로 하자|쓰지 ?마|쓰자|금지)')
REMEMBER_RE = re.compile(r'(기억해|기억하|잊지 ?마|잊어먹|메모해|노트북에|기억에)')
SYS_PREFIX = ('Caveat:', '<task-notification', '<local-command', '[Request interrupted', '[SYSTEM NOTIFICATION',
              'This session is being continued', 'Base directory for this skill')


# ---------------------------------------------------------------- 공용
def jload(p, default):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except (IOError, OSError, ValueError):
        return default


def jsave(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = '%s.%d.tmp' % (p, os.getpid())
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, p)


def registry():
    rows = []
    try:
        for line in open(os.path.join(CX, 'registry.md'), encoding='utf-8'):
            if not line.startswith('|'):
                continue
            c = [x.strip().strip('`') for x in line.strip().strip('|').split('|')]
            if len(c) >= 3 and plat.is_abs(c[0]):
                rows.append((plat.norm(c[0]), c[1], c[2]))
    except OSError:
        pass
    return rows


def scope(cwd):
    cwd = plat.norm(cwd)
    best = None
    for root, slug, stack in registry():
        if plat.under(root, cwd) and (best is None or len(root) > len(best[0])):
            best = (root, slug, stack)
    return best


def clean(t):
    t = re.sub(r'<system-reminder>.*?</system-reminder>', '', t, flags=re.S)
    t = re.sub(r'<ide_[a-z_]+>.*?</ide_[a-z_]+>', '', t, flags=re.S)
    # 슬래시 명령(/n-worker <요청>)은 요청이 <command-args> 안에 있다 - 명령 이름과 인자는 살리고 태그만 뗀다
    t = re.sub(r'<command-name>(.*?)</command-name>', r'\1 ', t, flags=re.S)
    t = re.sub(r'<command-args>(.*?)</command-args>', r'\1', t, flags=re.S)
    t = re.sub(r'<command-[a-z]+>.*?</command-[a-z]+>', '', t, flags=re.S)
    return t.strip()


def text_of(c):
    if isinstance(c, str):
        return c
    return '\n'.join(b.get('text') or '' for b in c or [] if isinstance(b, dict) and b.get('type') == 'text')


def one_line(s, n):
    s = ' '.join((s or '').split())
    return s if len(s) <= n else s[:n] + '…'


SKIP_FILE = os.path.join(ACTIVE, 'skip-sessions.txt')   # 기억하지 않을 세션 id(한 줄에 하나, # 은 설명) - 시험 세션 등. 대화록은 지우지 않는다
_skip = None


def skipped_sessions():
    global _skip
    if _skip is None:
        try:
            _skip = set(l.strip() for l in open(SKIP_FILE, encoding='utf-8') if l.strip() and not l.lstrip().startswith('#'))
        except OSError:
            _skip = set()
    return _skip


def automated(path):
    """[사람 없는 자동 실행 대화록인가]
    - 머리 줄의 entrypoint 가 sdk-cli 면 헤드리스 자동 실행(hippocampus 자신, 스크립트, 예약 작업)이다. 기억할 사람의 경험이 아니다
    - .active/skip-sessions.txt 에 적힌 세션(시험 세션 등)도 같은 취급이다 - 재생, 연합 학습, 등록 제안에서 빠진다
    """
    if os.path.splitext(os.path.basename(path))[0] in skipped_sessions():
        return True
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f):
                if i > 40:
                    break
                if '"entrypoint"' in line:
                    try:
                        return json.loads(line).get('entrypoint') == 'sdk-cli'
                    except ValueError:
                        continue
    except OSError:
        pass
    return False


def first_request(path):
    """[세션의 첫 사람 요청] - 구간 요약의 맥락 한 줄"""
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f):
                if i > 400:
                    break
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get('type') == 'user' and not d.get('isMeta') and not d.get('isSidechain'):
                    c = (d.get('message') or {}).get('content')
                    if isinstance(c, list) and any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in c):
                        continue
                    t = clean(text_of(c))
                    if t and not t.startswith(SYS_PREFIX):
                        return one_line(t, 400)
    except OSError:
        pass
    return ''


# ---------------------------------------------------------------- 요약
def digest(path, slug='?', start=0):
    """[대화록 구간 요약]
    - start 바이트부터 끝까지. 반환: (요약 markdown, 점수, 세부 수, 끝 바이트) 또는 None(새 사람 요청이 없는 구간)
    """
    flow = []
    pend = {}
    touch = {}
    n = {'정정': 0, '결정': 0, '기억 요청': 0, '도구 실패': 0, '거부': 0, '반복 조사': 0, '요청': 0}
    first = last = None
    last_text = None
    try:
        fh = open(path, 'rb')
    except OSError:
        return None
    size = os.fstat(fh.fileno()).st_size
    if start > size:
        start = 0   # 대화록이 새로 쓰였다
    fh.seek(start)
    if start:
        fh.readline()   # 걸친 줄은 건너뛴다(앞 구간이 끝까지 읽었다)
    end = start
    for raw in fh:
        if not raw.endswith(b'\n'):
            break       # 아직 쓰는 중인 마지막 줄은 다음 구간으로
        end = fh.tell()
        try:
            d = json.loads(raw.decode('utf-8', 'replace'))
        except ValueError:
            continue
        if d.get('isSidechain'):
            continue
        ts = d.get('timestamp') or ''
        if ts:
            first = first or ts
            last = ts
        m = d.get('message') or {}
        t = d.get('type')
        if t == 'user':
            c = m.get('content')
            if isinstance(c, list) and any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in c):
                for b in c:
                    if not (isinstance(b, dict) and b.get('type') == 'tool_result'):
                        continue
                    p = pend.pop(b.get('tool_use_id'), None)
                    rc = b.get('content')
                    if isinstance(rc, list):
                        rc = '\n'.join(x.get('text', '') for x in rc if isinstance(x, dict))
                    rc = rc or ''
                    if p and p.startswith('AskUserQuestion') and not b.get('is_error'):
                        # 질문 창 답 = 사용자 결정. 도구 결과로 들어오므로 따로 사람 요청으로 싣는다
                        ans = one_line(rc, 900)
                        n['결정'] += 1
                        n['요청'] += 1
                        flow.append(('U', ts, '(질문 답, 결정) ' + ans))
                    elif rc.startswith("The user doesn't want to proceed") or 'tool use was rejected' in rc[:200]:
                        n['거부'] += 1
                        flow.append(('D', ts, '거부된 도구 호출: %s' % (p or '?')))
                    elif b.get('is_error'):
                        n['도구 실패'] += 1
                        errl = [l for l in rc.splitlines() if l.strip()][:3]
                        flow.append(('E', ts, '%s → %s' % (p or '?', one_line(' / '.join(errl), 300))))
                continue
            if d.get('isMeta') or d.get('isCompactSummary'):
                continue
            txt = clean(text_of(m.get('content')))
            if not txt or txt.startswith(SYS_PREFIX) or '<task-id>' in txt[:300]:
                continue
            if last_text:
                flow.append(('A', last_text[0], last_text[1]))
                last_text = None
            tags = []
            if CORRECT_RE.search(txt):
                tags.append('정정')
            if DECIDE_RE.search(txt):
                tags.append('결정')
            if REMEMBER_RE.search(txt):
                tags.append('기억 요청')
            for tg in tags:
                n[tg] += 1
            n['요청'] += 1
            flow.append(('U', ts, ('(%s) ' % ', '.join(tags) if tags else '') + one_line(txt, 900)))
        elif t == 'assistant':
            for b in m.get('content') or []:
                if not isinstance(b, dict):
                    continue
                if b.get('type') == 'text' and (b.get('text') or '').strip():
                    if last_text:
                        flow.append(('A', last_text[0], last_text[1]))   # 한 턴 안의 앞 답도 버리지 않는다
                    last_text = (ts, one_line(b['text'], A_CHARS))
                elif b.get('type') == 'tool_use':
                    nm = b.get('name') or ''
                    inp = b.get('input') or {}
                    tgt = inp.get('file_path') or inp.get('notebook_path') or inp.get('command') or inp.get('pattern') or ''
                    if nm == 'AskUserQuestion':
                        tgt = ' / '.join(q.get('question', '') for q in inp.get('questions') or [] if isinstance(q, dict))
                    pend[b.get('id')] = '%s `%s`' % (nm, one_line(tgt, 160))
                    if nm in ('Read', 'Grep', 'Glob'):
                        key = inp.get('file_path') or inp.get('path') or inp.get('pattern') or ''
                        if key:
                            touch[key] = touch.get(key, 0) + 1
    fh.close()
    if last_text:
        flow.append(('A', last_text[0], last_text[1]))
    if n['요청'] == 0:
        return None
    reps = sorted(((k, v) for k, v in touch.items() if v >= 6), key=lambda kv: -kv[1])[:8]
    n['반복 조사'] = len(reps)
    score = 3 * n['정정'] + 3 * n['결정'] + 5 * n['기억 요청'] + 2 * n['거부'] + min(5, n['도구 실패']) + min(3, n['반복 조사']) + (1 if n['요청'] >= 5 else 0)
    hm = lambda ts: (ts or '')[11:16]
    head = ['# 대화록 요약 - %s%s' % (os.path.splitext(os.path.basename(path))[0], ' (구간, %d 바이트부터)' % start if start else ''),
            '프로젝트 %s, %s ~ %s, 원본 %s' % (slug, (first or '')[:16].replace('T', ' '), (last or '')[:16].replace('T', ' '), path),
            '점수 %d (%s)' % (score, ', '.join('%s %d' % (k, v) for k, v in n.items())),
            '표기: U 사람 요청, A 어시스턴트 결론 앞부분, E 도구 실패, D 거부. 괄호 표시는 규칙 기반 추정이라 틀릴 수 있다.']
    if start:
        fr = first_request(path)
        if fr:
            head.append('세션 첫 요청(맥락): %s' % fr)
    head.append('')
    if reps:
        head.append('## 반복 조사 (같은 대상 6회 이상 읽기,검색)')
        head += ['- %s (%d회)' % (one_line(k, 160), v) for k, v in reps]
        head.append('')
    head.append('## 흐름 (시간순)')
    body = ['- [%s %s] %s' % (hm(ts), k, s) for k, ts, s in flow]
    out = '\n'.join(head + body)
    if len(out) > MAX_CHARS:
        keep = set()
        for i, (k, ts, s) in enumerate(flow):
            if k in ('E', 'D', 'U') or (k == 'A' and EVIDENCE_RE.search(s)):
                keep.add(i)
        size = sum(len(flow[i][2]) + 20 for i in keep)
        if size > MAX_CHARS:   # 그래도 넘으면 근거 없는 사람 요청,결론부터 뺀다
            for i in sorted(keep, key=lambda i: (flow[i][0] == 'U' and flow[i][2].startswith('('), flow[i][0] in ('E', 'D'), EVIDENCE_RE.search(flow[i][2]) is not None, i)):
                if size <= MAX_CHARS:
                    break
                keep.discard(i)
                size -= len(flow[i][2]) + 20
        body = []
        skipped = 0
        for i, (k, ts, s) in enumerate(flow):
            if i in keep:
                if skipped:
                    body.append('- (… %d개 생략)' % skipped)
                    skipped = 0
                body.append('- [%s %s] %s' % (hm(ts), k, s))
            else:
                skipped += 1
        if skipped:
            body.append('- (… %d개 생략)' % skipped)
        out = '\n'.join(head + body)
        if len(out) > MAX_CHARS:
            out = out[:MAX_CHARS] + '\n- (… 길이 상한으로 잘림)'
    return out, score, n, end


def write_request(reqs, root, slug, stack, sid, path, text, score, kind, start, end):
    os.makedirs(REPLAY_DIR, exist_ok=True)
    dp = os.path.join(REPLAY_DIR, '%s-%d.md' % (sid, start))
    with open(dp, 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    req = {'mode': 'replay', 'project_root': root, 'slug': slug, 'stack': stack, 'caller': 'brain-%s' % kind,
           'payload': {'kind': kind, 'digest': dp, 'session': sid, 'transcript': path, 'score': score, 'bytes': [start, end]}}
    os.makedirs(reqs, exist_ok=True)
    rp = os.path.join(reqs, 'replay-%s-%d.json' % (sid[:8], start))
    with open(rp, 'w', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=1)
    return rp


def rollback(a):
    """[실패한 재생 요청의 위치 되돌리기] - 해마가 끝내지 못한 구간(실패, 시간 초과, 거부)을 다음 재생이 다시 가져가게 한다
    - 지금 위치가 그 요청의 끝일 때만 시작으로 되돌린다(그 뒤에 더 진행됐으면 건드리지 않는다)
    - 같은 대화록은 3번까지만 되돌린다 - 늘 실패하는 구간이 밤마다 다시 돌지 않게
    """
    try:
        req = json.load(open(a[0], encoding='utf-8'))
    except (IndexError, OSError, ValueError):
        return 0
    pl = req.get('payload') or {}
    path, rng = pl.get('transcript'), pl.get('bytes') or []
    if req.get('mode') != 'replay' or not path or len(rng) != 2:
        return 0
    marks = jload(MARKS, {})
    mk = marks.get(path) or {}
    if mk.get('pos') != rng[1] or mk.get('rollbacks', 0) >= 3:
        return 0
    mk['pos'] = rng[0]
    mk['rollbacks'] = mk.get('rollbacks', 0) + 1
    marks[path] = mk
    jsave(MARKS, marks)
    print('재생 위치 되돌림: %s %d -> %d' % (os.path.basename(path), rng[1], rng[0]))
    return 0


def enqueue(rp):
    subprocess.call(plat.argv(['bash', os.path.join(HERE, 'hippocampus-enqueue.sh'), rp]), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def arg(a, k, dflt=None):
    return a[a.index(k) + 1] if k in a else dflt


# ---------------------------------------------------------------- 깨어 있는 중
def awake(a):
    """[깨어 있는 중 되짚기]
    - 지난 처리 위치 뒤 새 구간의 점수가 하한 이상이고 간격,시간당 상한 안이면 요약을 만들어 큐에 넣고 위치를 옮긴다
    """
    path = arg(a, '--transcript')
    sc = scope(arg(a, '--cwd', ''))
    if not path or not os.path.isfile(path) or sc is None:
        return 0
    root, slug, stack = sc
    if automated(path):
        return 0
    force = '--force' in a
    min_score = int(arg(a, '--min-score', str(FORCE_MIN if force else AWAKE_MIN)))
    now = time.time()
    marks = jload(MARKS, {})
    mk = marks.get(path) or {}
    if not force and now - mk.get('t', 0) < AWAKE_GAP:
        return 0
    hist = [t for t in jload(AWAKE_LOG, []) if now - t < 3600]
    if len(hist) >= AWAKE_PER_HOUR:
        return 0
    r = digest(path, slug, mk.get('pos', 0))
    if r is None:
        return 0
    text, score, n, end = r
    if score < min_score:
        return 0
    sid = arg(a, '--sid') or os.path.splitext(os.path.basename(path))[0]
    rp = write_request(os.path.join(REPLAY_DIR, 'req'), root, slug, stack, sid, path, text, score, 'awake', mk.get('pos', 0), end)
    marks = jload(MARKS, {})
    marks[path] = {'pos': end, 't': now}
    jsave(MARKS, marks)
    jsave(AWAKE_LOG, hist + [now])
    enqueue(rp)
    return 0


# ---------------------------------------------------------------- 잠
def project_dirs(root):
    base = PROJECTS
    key = re.sub(r'[^A-Za-z0-9]', '-', root)
    return [os.path.join(base, key)] + glob.glob(os.path.join(base, key + '-*'))


def suggest_register(since_days=7, min_sessions=3, min_prompts=10):
    """[활발한 미등록 프로젝트]
    - 최근 since_days 일 동안 대화록이 min_sessions 개 이상이고 사람 요청이 min_prompts 개 이상인 등록 안 된 폴더(.git 이 있는 곳)
    """
    base = PROJECTS
    now = time.time()
    regs = [r[0] for r in registry()]
    found = {}
    for p in glob.glob(os.path.join(base, '*', '*.jsonl')):
        try:
            if now - os.path.getmtime(p) > since_days * 86400:
                continue
        except OSError:
            continue
        if automated(p):
            continue
        cwd = None
        prompts = 0
        try:
            with open(p, encoding='utf-8', errors='replace') as f:
                for i, line in enumerate(f):
                    if i > 3000:
                        break
                    try:
                        d = json.loads(line)
                    except ValueError:
                        continue
                    cwd = cwd or d.get('cwd')
                    if d.get('type') == 'user' and not d.get('isMeta') and not d.get('isSidechain'):
                        c = (d.get('message') or {}).get('content')
                        if isinstance(c, str) or (isinstance(c, list) and not any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in c)):
                            prompts += 1
        except OSError:
            continue
        if not cwd or cwd.startswith(('/private/', '/tmp/', '/var/')) or '/.claude' in cwd:
            continue
        if any(cwd == r or cwd.startswith(r + '/') for r in regs):
            continue
        top = cwd
        while top and top != '/' and not os.path.isdir(os.path.join(top, '.git')):
            top = os.path.dirname(top)
        if not top or top == '/' or top == os.path.expanduser('~'):
            continue
        f = found.setdefault(top, [0, 0])
        f[0] += 1
        f[1] += prompts
    return [(top, s, pr) for top, (s, pr) in found.items() if s >= min_sessions and pr >= min_prompts]


def scan(a):
    out_reqs = arg(a, '--reqs')
    mx = int(arg(a, '--max', '4'))
    min_score = int(arg(a, '--min-score', str(AWAKE_MIN)))
    first_days = float(arg(a, '--first-days', '2'))
    now = time.time()
    marks = jload(MARKS, {})
    cand = []
    scanned = 0
    for root, slug, stack in registry():
        for dd in project_dirs(root):
            for p in glob.glob(os.path.join(dd, '*.jsonl')):
                try:
                    mt = os.path.getmtime(p)
                    size = os.path.getsize(p)
                except OSError:
                    continue
                mk = marks.get(p) or {}
                if mk.get('pos', 0) >= size or now - mt < 1800:
                    continue   # 다 처리했거나, 30분 안에 바뀌어 아직 진행 중일 수 있다(깨어 있는 중 재생의 몫)
                if not mk and now - mt > first_days * 86400:
                    continue   # 처음 보는 오래된 대화록은 건너뛴다(첫 수면의 홍수 방지)
                if automated(p):
                    marks[p] = {'pos': size, 't': mk.get('t', 0)}
                    continue
                scanned += 1
                r = digest(p, slug, mk.get('pos', 0))
                if r is None:
                    marks[p] = {'pos': size, 't': mk.get('t', 0)}
                    continue
                text, score, n, end = r
                if score < min_score:
                    marks[p] = {'pos': end, 't': mk.get('t', 0)}
                    continue
                cand.append((score, mt, p, root, slug, stack, text, mk.get('pos', 0), end))
    cand.sort(key=lambda x: (-x[0], -x[1]))
    made = 0
    for score, mt, p, root, slug, stack, text, start, end in cand[:mx]:
        sid = os.path.splitext(os.path.basename(p))[0]
        print(write_request(out_reqs, root, slug, stack, sid, p, text, score, 'sleep', start, end))
        marks[p] = {'pos': end, 't': now}
        made += 1
    for score, mt, p, root, slug, stack, text, start, end in cand[mx:]:
        if p not in marks:
            marks[p] = {'pos': start, 't': 0}   # 상한에 밀린 대화록도 본 것으로 남긴다 - 처음 보는 오래된 대화록으로 취급돼 이틀 뒤 빠지지 않게
    jsave(MARKS, marks)
    regs = suggest_register()
    for top, s, pr in regs[:1]:
        req = {'mode': 'register', 'project_root': top, 'slug': re.sub(r'[^a-z0-9-]', '-', os.path.basename(top).lower()).strip('-'),
               'stack': '?', 'caller': 'brain-sleep',
               'payload': {'auto': True, 'reason': '최근 7일 대화록 %d개, 사람 요청 %d개 - 자주 일하는 곳이라 기억 자리를 만든다' % (s, pr),
                           'instruction': '스택과 버전, 컨벤션 문서 위치는 프로젝트 파일(ProjectSettings/ProjectVersion.txt, package.json, CLAUDE.md 등)에서 확인한다. 확인이 안 되는 칸은 ? 로 둔다.'}}
        rp = os.path.join(out_reqs, 'register-%s.json' % req['slug'][:30])
        with open(rp, 'w', encoding='utf-8') as f:
            json.dump(req, f, ensure_ascii=False, indent=1)
        print(rp)
    print('# 훑음 %d, 후보 %d, 재생 요청 %d, 등록 제안 %d' % (scanned, len(cand), made, min(1, len(regs))))
    return 0


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 2
    if a[0] == 'awake':
        try:
            return awake(a[1:])
        except Exception:
            return 0
    if a[0] == 'scan':
        return scan(a[1:])
    if a[0] == 'rollback':
        try:
            return rollback(a[1:])
        except Exception:
            return 0
    if a[0] == 'digest' and len(a) > 1:
        r = digest(a[1], '?', int(arg(a, '--from', '0')))
        print(r[0] if r else '(새 사람 요청 없음)')
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
