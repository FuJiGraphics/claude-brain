#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 벤치 - 매번 깨끗한 환경에서 같은 과제를 brain 없이, 지금 brain 으로(깊이 high 면 비교 기준 brain 도) 실제 claude 세션으로 돌려 비교한다.

사용: python3 bench.py [low|medium|high] [--ref <git ref>] [--models haiku,sonnet,opus] [--reps 2] [--jobs 4] [--out <폴더>] [--keep]
  low     과제 2개(기억 과제 gen-rates, 대조 과제 format-cents) x 갈래 2(brain 끔, 지금 brain) x 모델 3 x 2회 = 24회
  medium  과제 3개(split-bill 추가) x 갈래 2 x 모델 3 x 2회 = 36회
  high    과제 3개 x 갈래 3(비교 기준 brain 추가) x 모델 3 x 2회 = 54회. 기준은 --ref, 없으면 scripts/ 에 커밋 안 한 변경이
          있을 때 HEAD, 없을 때 HEAD~1

공정성과 투명성 - 보고서에 그대로 싣는다
- 같은 입력: 갈래끼리 픽스처(fixture/project, fixture/cortex), 과제 글, 모델, 턴 상한, 도구, 덧붙이는 시스템 문구가 같다.
  `[기억]` 안내 한 줄(lang.py claude_md)도 모든 갈래에 넣는다 - 갈래 차이는 훅 등록 하나다
- 격리: 사용자 설정, 플러그인, 사용자 스킬, MCP, CLAUDE.md 를 싣지 않는다(--setting-sources project,local, --strict-mcp-config).
  Claude Code 자동 기억도 끈다. 실행마다 시작 이벤트로 격리를 검사하고 어긋나면 그 실행을 무효로 표시한다
- 매번 새 환경: 실행마다 픽스처를 새 임시 폴더에 복사하고 git 저장소로 만든다. brain 갈래는 그 실행만의 brain 사본(scripts + 기억
  사본 + 빈 상태)을 쓴다. 갈래마다 훅 목록은 그 버전의 install.sh 와 같다(쉬는 순간 훅 Stop, PreCompact, SessionEnd 는 뺀다 -
  해마 재생이 따로 모델을 부른다)
- 순서: 모든 실행을 시드로 섞어 돌린다(시간대에 따른 API 속도 차이가 한 갈래에 몰리지 않게)
- 채점: 과제마다 미리 정한 기준(tasks/*.json 의 criteria)을 채점 스크립트(checks/)가 기계적으로 본다. 채점 스크립트는 작업 폴더
  밖에 있어 모델이 볼 수 없다. 모델 판정관은 쓰지 않는다
- 기록: 모든 실행(실패, 시간 초과, 무효 포함)을 표로 싣는다. 비용, 턴, 시간은 claude 의 결과 이벤트 값 그대로다
- 흔적 없음: 임시 폴더는 끝나면 지운다. 세션 저장을 끄고(--no-session-persistence) 자동 기억을 꺼서 ~/.claude/projects 에 아무것도
  남지 않게 하고, 혹시 생기면 지우고 보고서에 적는다. 결과는 --out(기본 바탕화면) 아래 brain-bench-<시각>/ 폴더 하나뿐이다
"""
import concurrent.futures
import datetime
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
FIX_PROJECT = os.path.join(HERE, 'fixture', 'project')
FIX_CORTEX = os.path.join(HERE, 'fixture', 'cortex')
SLUG = 'ledger'
DEPTH_TASKS = {'low': ['gen-rates', 'format-cents'], 'medium': ['gen-rates', 'split-bill', 'format-cents'],
               'high': ['gen-rates', 'split-bill', 'format-cents']}
RUN_TIMEOUT = 900         # 실행 하나의 시간 상한(초)
BUDGET_USD = 2.0          # 실행 하나의 비용 상한(claude --max-budget-usd)
TOOLS = 'Bash,Read,Edit,Write,Glob,Grep'
REST_EVENTS = ('Stop', 'PreCompact', 'SessionEnd')
SEED = 20261028


# ---------------------------------------------------------------- 준비
def sh(args, cwd=None, check=True):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError('%s: %s' % (' '.join(args), (p.stderr or p.stdout).strip()[:500]))
    return p.stdout.strip()


def tree_hash(root):
    h = hashlib.sha256()
    for dp, dn, fn in sorted(os.walk(root)):
        dn.sort()
        for f in sorted(fn):
            if f.endswith('.pyc') or f == '.DS_Store':
                continue
            p = os.path.join(dp, f)
            h.update(os.path.relpath(p, root).encode('utf-8'))
            h.update(open(p, 'rb').read())
    return h.hexdigest()[:12]


def hook_events(scripts_dir):
    """[그 버전의 install.sh 가 등록하는 훅] [(사건, matcher)] - 쉬는 순간 훅은 뺀다"""
    text = open(os.path.join(os.path.dirname(scripts_dir), 'scripts', 'install.sh'), encoding='utf-8').read()
    m = re.search(r'want = (\[.*?\])\n', text, re.S)
    want = eval(m.group(1), {'__builtins__': {}}, {'None': None})   # 리터럴 목록이다
    return [(ev, mt) for ev, mt in want if ev not in REST_EVENTS]


def prepare_arm(name, tmp, ref=None):
    """[갈래의 brain 코드] 지금 저장소의 scripts/ 또는 git ref 의 scripts/ 를 임시 폴더에 둔다"""
    dst = os.path.join(tmp, 'arms', name)
    os.makedirs(dst)
    if ref:
        arc = subprocess.run(['git', '-C', REPO, 'archive', ref, 'scripts'], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', dst], input=arc, check=True)
        commit = sh(['git', '-C', REPO, 'rev-parse', '--short', ref])
    else:
        shutil.copytree(os.path.join(REPO, 'scripts'), os.path.join(dst, 'scripts'),
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        commit = sh(['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'])
        if sh(['git', '-C', REPO, 'status', '--porcelain', '--', 'scripts']):
            commit += '+작업트리'
    return {'name': name, 'dir': dst, 'commit': commit, 'hash': tree_hash(os.path.join(dst, 'scripts')),
            'events': hook_events(os.path.join(dst, 'scripts'))}


def claude_md_line():
    sys.path.insert(0, os.path.join(REPO, 'scripts'))
    import lang
    return lang.T[lang.current()]['claude_md']


def setup_run(run, tmp):
    """[실행 하나의 새 환경] 프로젝트 복사 + git, brain 갈래면 brain 사본과 훅 설정"""
    base = os.path.join(tmp, 'runs', run['id'])
    ws = os.path.join(base, 'ledger')
    shutil.copytree(FIX_PROJECT, ws)
    ws = os.path.realpath(ws)
    env = dict(os.environ, GIT_AUTHOR_NAME='bench', GIT_AUTHOR_EMAIL='bench@localhost',
               GIT_COMMITTER_NAME='bench', GIT_COMMITTER_EMAIL='bench@localhost')
    for args in (['git', 'init', '-q'], ['git', 'add', '-A'], ['git', 'commit', '-q', '-m', 'init']):
        subprocess.run(args, cwd=ws, check=True, env=env, capture_output=True)
    for args in run['task'].get('setup') or []:   # 과제의 시작 상태(예: 생성 파일 만들기 - .gitignore 대상이라 커밋에는 안 든다)
        subprocess.run([sys.executable if a == 'python3' else a for a in args], cwd=ws, check=True, capture_output=True)
    settings = {'autoMemoryEnabled': False, 'hooks': {}}
    brain = None
    if run['arm'] != 'off':
        arm = run['arm_info']
        brain = os.path.join(base, 'brain')
        shutil.copytree(os.path.join(arm['dir'], 'scripts'), os.path.join(brain, 'scripts'))
        shutil.copytree(FIX_CORTEX, os.path.join(brain, 'cortex'))
        reg = os.path.join(brain, 'cortex', 'registry.md')
        rows = '| %s | %s | python | 3 | 가계부 정산 도구(정수 센트, 환율 표는 생성 파일). |' % (ws, SLUG)
        text = open(reg, encoding='utf-8').read().replace('{{ROWS}}', rows)
        open(reg, 'w', encoding='utf-8').write(text)
        os.makedirs(os.path.join(brain, '.active'))
        cmd = 'f=%s; [ -f "$f" ] && %s "$f" hook; exit 0' % (shlex_quote(os.path.join(brain, 'scripts', 'thalamus.py')), sys.executable)
        for ev, matcher in arm['events']:
            g = {'hooks': [{'type': 'command', 'command': cmd, 'timeout': 5}]}
            if matcher:
                g['matcher'] = matcher
            settings['hooks'].setdefault(ev, []).append(g)
    sp = os.path.join(base, 'settings.json')
    json.dump(settings, open(sp, 'w'), ensure_ascii=False, indent=1)
    return ws, brain, sp, base


def shlex_quote(s):
    import shlex
    return shlex.quote(s)


# ---------------------------------------------------------------- 실행
def encoded_project_dir(ws):
    return os.path.join(os.path.expanduser('~/.claude/projects'), re.sub(r'[^A-Za-z0-9]', '-', ws))


def run_one(run, tmp, sysline):
    t0 = time.time()
    rec = {'id': run['id'], 'task': run['task']['id'], 'arm': run['arm'], 'model': run['model'], 'rep': run['rep']}
    try:
        ws, brain, sp, base = setup_run(run, tmp)
        args = ['claude', '-p', run['task']['prompt'], '--model', run['model'], '--setting-sources', 'project,local',
                '--strict-mcp-config', '--no-session-persistence', '--settings', sp, '--output-format', 'stream-json',
                '--verbose', '--append-system-prompt', sysline, '--permission-mode', 'acceptEdits', '--allowedTools', TOOLS,
                '--max-turns', str(run['task']['max_turns']), '--max-budget-usd', str(BUDGET_USD)]
        env = dict(os.environ)
        for k in ('CLAUDE_CODE_SESSION_ID', 'CLAUDE_PROJECT_DIR'):
            env.pop(k, None)
        out_path = os.path.join(base, 'stream.jsonl')
        with open(out_path, 'w') as out:
            try:
                p = subprocess.run(args, cwd=ws, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                   timeout=RUN_TIMEOUT, env=env)
                rec['exit'] = p.returncode
            except subprocess.TimeoutExpired:
                rec['exit'] = 'timeout'
        parse_stream(out_path, rec)
        rec['isolation'] = isolation(rec, ws, brain)
        ck = subprocess.run([sys.executable, os.path.join(HERE, 'checks', run['task']['id'] + '.py'), ws],
                            capture_output=True, text=True, timeout=300)
        try:
            rec['check'] = json.loads(ck.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            rec['check'] = {'pass': False, 'checks': [['채점 실패', False, (ck.stderr or ck.stdout)[-300:]]]}
        rec['pass'] = bool(rec['check'].get('pass'))
        brain_metrics(rec, brain, run['task'])
    except Exception as e:   # 실행 준비나 분석 실패도 표에 남긴다
        rec['error'] = '%s: %s' % (e.__class__.__name__, e)
        rec['pass'] = False
    rec['wall_s'] = round(time.time() - t0, 1)
    return rec


def parse_stream(path, rec):
    tools = {}
    rec['init'] = {}
    rec['result'] = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get('type') == 'system' and d.get('subtype') == 'init':
            rec['init'] = {k: d.get(k) for k in ('model', 'skills', 'plugins', 'mcp_servers', 'memory_paths', 'agents', 'cwd', 'session_id',
                                                  'claude_code_version')}
        elif d.get('type') == 'assistant':
            for x in (d.get('message') or {}).get('content') or []:
                if isinstance(x, dict) and x.get('type') == 'tool_use':
                    tools[x.get('name')] = tools.get(x.get('name'), 0) + 1
        elif d.get('type') == 'result':
            u = d.get('usage') or {}
            rec['result'] = {'subtype': d.get('subtype'), 'is_error': d.get('is_error'), 'turns': d.get('num_turns'),
                             'cost': d.get('total_cost_usd'), 'duration_ms': d.get('duration_ms'),
                             'in_tokens': (u.get('input_tokens') or 0) + (u.get('cache_read_input_tokens') or 0)
                             + (u.get('cache_creation_input_tokens') or 0),
                             'out_tokens': u.get('output_tokens') or 0}
    rec['tools'] = tools


USER_SKILLS = None


def user_skill_names():
    """[사용자 스킬, 명령 이름] 격리가 깨졌는지 볼 때 쓴다(~/.claude/skills, ~/.claude/commands)"""
    global USER_SKILLS
    if USER_SKILLS is None:
        names = set()
        for d in ('skills', 'commands'):
            try:
                for n in os.listdir(os.path.expanduser('~/.claude/' + d)):
                    names.add(os.path.splitext(n)[0])
            except OSError:
                pass
        USER_SKILLS = names
    return USER_SKILLS


def isolation(rec, ws, brain):
    """[격리 검사] 문제 목록(비면 정상)"""
    bad = []
    init = rec.get('init') or {}
    if not init:
        bad.append('시작 이벤트 없음')
    leaked = sorted(set(init.get('skills') or []) & user_skill_names())
    if leaked:
        bad.append('사용자 스킬이 실림: %s' % ', '.join(leaked))
    if init.get('mcp_servers'):
        bad.append('MCP 서버가 실림')
    if any((p or {}).get('path') != 'builtin' for p in init.get('plugins') or []):
        bad.append('기본 제공이 아닌 플러그인이 실림')
    if init.get('memory_paths'):
        bad.append('자동 기억 경로가 잡힘')
    pd = encoded_project_dir(ws)
    if os.path.exists(pd):
        shutil.rmtree(pd, ignore_errors=True)
        bad.append('~/.claude/projects 에 폴더가 생겨 지움')
    log = os.path.join(brain, '.active', 'recall.log') if brain else None
    if brain and not (log and os.path.isfile(log) and '"orient"' in open(log, encoding='utf-8').read()):
        bad.append('brain 훅이 돌지 않음(깨어남 기록 없음)')
    sid = init.get('session_id')
    inst = os.path.expanduser('~/.claude/skills/brain/.active/recall.log')
    if sid and os.path.isfile(inst):
        with open(inst, encoding='utf-8', errors='replace') as f:
            f.seek(max(0, os.path.getsize(inst) - 2000000))
            if sid in f.read():
                bad.append('설치본 brain 훅이 이 세션에 돌았음')
    return bad


def brain_metrics(rec, brain, task):
    """[떠올림 기록] 주입 글자, 떠올린 기억, 연 기억, 핵심 기억을 떠올렸나, 핵심이 아닌 떠올림 수"""
    rec['inject_chars'] = 0
    rec['inject_orient'] = 0
    rec['shown'] = []
    rec['opened'] = []
    if not brain:
        return
    log = os.path.join(brain, '.active', 'recall.log')
    if not os.path.isfile(log):
        return
    for line in open(log, encoding='utf-8'):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get('ev') == 'orient':
            rec['inject_orient'] += d.get('chars', 0)
        else:
            rec['inject_chars'] += d.get('chars', 0) or 0
        for r in d.get('shown') or []:
            rec['shown'].append([d.get('ev'), os.path.splitext(os.path.basename(r))[0]])
        if d.get('ev') == 'open' and d.get('body'):
            rec['opened'].append(os.path.splitext(os.path.basename(d['body']))[0])
    key = set(task['key'])
    rec['key_shown'] = bool(key & set(s for _, s in rec['shown'])) if key else None
    rec['key_opened'] = bool(key & set(rec['opened'])) if key else None
    rec['noise_shown'] = len([s for _, s in rec['shown'] if s not in key])


# ---------------------------------------------------------------- 보고서
def mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return sum(xs) / len(xs) if xs else None


def fmt(x, f='%.2f'):
    return '-' if x is None else f % x


def report(meta, recs, out_dir):
    L = []
    L.append('# brain 벤치 보고서 (%s, 깊이 %s)' % (meta['started'], meta['depth']))
    L.append('')
    L.append('## 요약')
    L.append('')
    L.append('| 과제 | 갈래 | 모델 | 통과 | 평균 비용($) | 평균 턴 | 평균 시간(초) | 평균 주입 글자(도구,요청) | 핵심 기억 떠올림 | 핵심 기억 열람 | 핵심 아닌 떠올림(평균) |')
    L.append('|---|---|---|---|---|---|---|---|---|---|---|')
    valid = [r for r in recs if not r.get('isolation') and not r.get('error')]
    for t in meta['tasks']:
        for arm in meta['arms']:
            for m in meta['models']:
                g = [r for r in valid if r['task'] == t and r['arm'] == arm and r['model'] == m]
                if not g:
                    continue
                res = [r.get('result') or {} for r in g]
                ks = [r.get('key_shown') for r in g if r.get('key_shown') is not None]
                ko = [r.get('key_opened') for r in g if r.get('key_opened') is not None]
                L.append('| %s | %s | %s | %d/%d | %s | %s | %s | %s | %s | %s | %s |' % (
                    t, arm, m, sum(1 for r in g if r['pass']), len(g), fmt(mean([x.get('cost') for x in res]), '%.3f'),
                    fmt(mean([x.get('turns') for x in res]), '%.1f'), fmt(mean([(x.get('duration_ms') or 0) / 1000.0 for x in res]), '%.0f'),
                    '-' if arm == 'off' else fmt(mean([r.get('inject_chars') for r in g]), '%.0f'),
                    '-' if arm == 'off' or not ks else '%d/%d' % (sum(ks), len(ks)),
                    '-' if arm == 'off' or not ko else '%d/%d' % (sum(ko), len(ko)),
                    '-' if arm == 'off' else fmt(mean([r.get('noise_shown') for r in g]), '%.1f')))
    L.append('')
    L.append('갈래별 합계(유효 실행만):')
    L.append('')
    for arm in meta['arms']:
        g = [r for r in valid if r['arm'] == arm]
        if g:
            L.append('- %s: 통과 %d/%d, 비용 합 $%.2f, 평균 턴 %s' % (arm, sum(1 for r in g if r['pass']), len(g),
                     sum((r.get('result') or {}).get('cost') or 0 for r in g), fmt(mean([(r.get('result') or {}).get('turns') for r in g]), '%.1f')))
    inval = [r for r in recs if r.get('isolation') or r.get('error')]
    L.append('- 무효 실행: %d (격리 위반이나 준비 오류 - 아래 전체 표에 이유)' % len(inval))
    L.append('')
    L.append('## 한계')
    L.append('')
    L.append('- 표본이 작다(조합마다 %d회). 차이가 작으면 우연일 수 있다 - 방향을 보는 지표다.' % meta['reps'])
    L.append('- 기억 과제(gen-rates, split-bill)의 정답은 사용자 결정이라 기억에만 있다. brain 끔 갈래는 우연히 맞히지 않는 한 통과하지 못하는 것이 설계다 - 이 과제는 "기억이 필요한 순간에 떠오르고 쓰이는가" 를 잰다.')
    L.append('- 대조 과제(format-cents)는 기억이 필요 없다 - 갈래 사이 통과율, 비용, 턴 차이가 brain 의 부작용(판단 흐림, 군더더기 비용)이다.')
    L.append('- 픽스처는 작은 Python 프로젝트 하나와 기억 17개다. 실제 저장소(기억 1,300개)보다 헷갈리게 하는 기억이 적다.')
    L.append('')
    L.append('## 절차')
    L.append('')
    for line in (__doc__ or '').split('공정성과 투명성 - 보고서에 그대로 싣는다')[1].strip('\n').splitlines():
        L.append(line)
    L.append('')
    L.append('## 환경')
    L.append('')
    L.append('- claude: %s, 모델(시작 이벤트): %s' % (meta.get('claude_version'), ', '.join(sorted(meta.get('resolved_models') or []))))
    L.append('- 갈래: ' + '; '.join('%s = %s (scripts 해시 %s)' % (a['name'], a['commit'], a['hash']) for a in meta['arm_info']))
    L.append('- 픽스처 해시: 프로젝트 %s, 기억 %s, 과제 %s, 채점 %s' % (meta['fix_hash'], meta['cortex_hash'], meta['tasks_hash'], meta['checks_hash']))
    L.append('- 순서 시드 %d, 동시 실행 %d, 실행당 상한: 시간 %d초, 비용 $%.1f, 턴은 과제 파일' % (meta['seed'], meta['jobs'], RUN_TIMEOUT, BUDGET_USD))
    L.append('')
    L.append('## 과제와 채점 기준(미리 정한 것)')
    L.append('')
    for t in meta['task_defs']:
        L.append('- **%s** (%s): "%s"' % (t['id'], t['kind'], t['prompt']))
        if t.get('setup_note'):
            L.append('  - %s' % t['setup_note'])
        for c in t['criteria']:
            L.append('  - %s' % c)
        if t['key']:
            L.append('  - 핵심 기억: %s' % ', '.join('`%s`' % k for k in t['key']))
    L.append('')
    L.append('## 전체 실행')
    L.append('')
    L.append('| # | 과제 | 갈래 | 모델 | 회 | 통과 | 비용($) | 턴 | 시간(초) | 주입 | 떠올린 기억 | 연 기억 | 실패한 기준 / 무효 이유 |')
    L.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for i, r in enumerate(recs, 1):
        res = r.get('result') or {}
        why = '; '.join(c[0] + (' (' + c[2] + ')' if c[2] else '') for c in ((r.get('check') or {}).get('checks') or []) if not c[1])
        if r.get('isolation'):
            why = '무효: ' + '; '.join(r['isolation'])
        if r.get('error'):
            why = '오류: ' + r['error']
        L.append('| %d | %s | %s | %s | %d | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            i, r['task'], r['arm'], r['model'], r['rep'], 'O' if r['pass'] else 'X', fmt(res.get('cost'), '%.3f'),
            res.get('turns', '-'), fmt((res.get('duration_ms') or 0) / 1000.0, '%.0f'), r.get('inject_chars', '-') if r['arm'] != 'off' else '-',
            ', '.join('%s:%s' % (e, s) for e, s in r.get('shown') or []) or '-', ', '.join(r.get('opened') or []) or '-',
            why.replace('|', '/') or '-'))
    path = os.path.join(out_dir, 'report.md')
    open(path, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    return path


# ---------------------------------------------------------------- 진입
def main(argv):
    depth = 'low'
    ref = None
    models = ['haiku', 'sonnet', 'opus']
    reps = 2
    jobs = 4
    out = os.path.expanduser('~/Desktop')
    keep = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in DEPTH_TASKS:
            depth = a
        elif a == '--ref':
            ref = argv[i + 1]
            i += 1
        elif a == '--models':
            models = [x for x in argv[i + 1].split(',') if x]
            i += 1
        elif a == '--reps':
            reps = int(argv[i + 1])
            i += 1
        elif a == '--jobs':
            jobs = int(argv[i + 1])
            i += 1
        elif a == '--out':
            out = os.path.expanduser(argv[i + 1])
            i += 1
        elif a == '--keep':
            keep = True
        else:
            print(__doc__)
            return 2
        i += 1
    if shutil.which('claude') is None:
        print('claude 명령을 찾을 수 없다')
        return 2
    started = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    tmp = tempfile.mkdtemp(prefix='brain-bench-')
    out_dir = os.path.join(out, 'brain-bench-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    try:
        arms = [prepare_arm('cur', tmp)]
        if depth == 'high' or ref:
            if not ref:
                ref = 'HEAD' if '+작업트리' in arms[0]['commit'] else 'HEAD~1'
            arms.append(prepare_arm('ref', tmp, ref))
        arm_names = ['off'] + [a['name'] for a in arms]
        task_defs = [json.load(open(os.path.join(HERE, 'tasks', t + '.json'), encoding='utf-8')) for t in DEPTH_TASKS[depth]]
        runs = []
        for t in task_defs:
            for arm in arm_names:
                for m in models:
                    for rep in range(1, reps + 1):
                        runs.append({'task': t, 'arm': arm, 'model': m, 'rep': rep,
                                     'arm_info': next((a for a in arms if a['name'] == arm), None)})
        random.Random(SEED).shuffle(runs)
        for n, r in enumerate(runs):
            r['id'] = '%03d-%s-%s-%s-%d' % (n, r['task']['id'], r['arm'], r['model'], r['rep'])
        sysline = claude_md_line()
        print('brain 벤치: 깊이 %s, 과제 %d, 갈래 %s, 모델 %s, %d회 -> 실행 %d개 (동시 %d)' % (
            depth, len(task_defs), '/'.join(arm_names), ','.join(models), reps, len(runs), jobs), flush=True)
        recs = []
        with concurrent.futures.ThreadPoolExecutor(jobs) as ex:
            futs = [ex.submit(run_one, r, tmp, sysline) for r in runs]
            for f in concurrent.futures.as_completed(futs):
                rec = f.result()
                recs.append(rec)
                print('  [%d/%d] %s %s' % (len(recs), len(runs), rec['id'],
                      '오류' if rec.get('error') else ('무효' if rec.get('isolation') else ('통과' if rec['pass'] else '실패'))), flush=True)
        order = dict((r['id'], n) for n, r in enumerate(runs))
        recs.sort(key=lambda r: order[r['id']])
        os.makedirs(out_dir)
        meta = {'started': started, 'depth': depth, 'tasks': [t['id'] for t in task_defs], 'task_defs': task_defs, 'arms': arm_names,
                'arm_info': [dict((k, a[k]) for k in ('name', 'commit', 'hash')) for a in arms], 'models': models, 'reps': reps,
                'jobs': jobs, 'seed': SEED, 'fix_hash': tree_hash(FIX_PROJECT), 'cortex_hash': tree_hash(FIX_CORTEX),
                'tasks_hash': tree_hash(os.path.join(HERE, 'tasks')), 'checks_hash': tree_hash(os.path.join(HERE, 'checks')),
                'claude_version': sh(['claude', '--version'], check=False),
                'resolved_models': list(set((r.get('init') or {}).get('model') for r in recs if (r.get('init') or {}).get('model')))}
        json.dump({'meta': meta, 'runs': recs}, open(os.path.join(out_dir, 'runs.json'), 'w'), ensure_ascii=False, indent=1)
        path = report(meta, recs, out_dir)
        print('보고서: %s' % path)
    finally:
        if keep:
            print('임시 폴더를 남김(--keep): %s' % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
