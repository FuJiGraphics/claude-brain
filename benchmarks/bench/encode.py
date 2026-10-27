# -*- coding: utf-8 -*-
"""brain 저장 벤치(encode) - 배우는 세션 → 해마 재생 → 기계 채점 → 시험 세션. 시나리오와 채점은 encode/ 에 사전 등록돼 있다(encode/README.md)

bench.py 가 부른다(`bench.py [low|medium|high] encode`). 공정성
- 배우는 세션은 시나리오와 회차마다 한 번만 돌리고(sonnet, 지금 brain 의 훅과 범례, 시작 기억 저장소), 그 대화록 하나를 모든 갈래에 넣는다 -
  갈래 차이는 재생 요약(replay.digest)과 해마 지침(agents/hippocampus.md)뿐이다
- 해마는 지금 데몬(scripts/hippocampus-daemon.sh)을 격리 스위치(BRAIN_HC_ISOLATE=1)로 그대로 돌린다 - 해마 호출의 원본은 데몬 하나다
- 요청 JSON 은 replay.write_request 와 같은 꼴로 만든다(그 함수는 자기 저장소 안에 파일을 써서 벤치가 직접 쓸 수 없다)
- 떠올림 코드는 모든 갈래가 지금 것으로 같다(시험 세션과 닿음 확인)
"""
import concurrent.futures
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

import bench as B

HERE = B.HERE
ENC = os.path.join(HERE, 'encode')
OLD_REF = '234a390'   # 옛 저장 기준 - 사전 등록(encode/README.md)에 적은 값
ORDER = ['incident', 'noise', 'chat-decision', 'silent-wrong']
HC_TIMEOUT = 1800


def scenarios(depth):
    out = []
    for p in glob.glob(os.path.join(ENC, 'scenarios', '*.json')):
        d = json.load(open(p, encoding='utf-8'))
        if depth in d['depth']:
            out.append(d)
    out.sort(key=lambda d: ORDER.index(d['id']) if d['id'] in ORDER else 99)
    return out


def cortex_template(tmp, kind):
    """[기억 저장소 원본] start = 픽스처에서 핵심 기억을 뺀 것(encode/start-cortex.json), ideal = 픽스처 그대로. registry 의 {{ROWS}} 는 남긴다"""
    dst = os.path.join(tmp, 'encode', kind + '-cortex')
    if not os.path.isdir(dst):
        shutil.copytree(B.FIX_CORTEX, dst)
        if kind == 'start':
            spec = json.load(open(os.path.join(ENC, 'start-cortex.json'), encoding='utf-8'))
            B.patch_cortex(dst, {'remove': spec['remove']})
    return dst


def memory_files(cortex):
    """[기억 파일들] {상대 경로: 내용} - .hippocampus 와 registry 는 빼고"""
    out = {}
    for dp, dn, fn in os.walk(cortex):
        dn[:] = [d for d in dn if not d.startswith('.')]
        for f in fn:
            if f.endswith('.md') and f != 'registry.md':
                p = os.path.join(dp, f)
                out[os.path.relpath(p, cortex)] = open(p, encoding='utf-8', errors='replace').read()
    return out


def keyword(rel):
    return re.sub(r'-\d{4}-\d{2}-\d{2}$', '', os.path.splitext(os.path.basename(rel))[0])


_MODS = {}


def replay_module(arm):
    """[갈래의 재생 코드] 그 갈래 사본의 scripts/replay.py 를 이름을 달리해 불러온다"""
    if arm['name'] not in _MODS:
        d = os.path.join(arm['dir'], 'scripts')
        sys.path.insert(0, d)
        try:
            for m in ('replay', 'thalamus', 'plat', 'lang', 'nbsearch'):
                sys.modules.pop(m, None)   # 갈래마다 자기 사본의 모듈을 쓰게
            spec = importlib.util.spec_from_file_location('replay_' + arm['name'], os.path.join(d, 'replay.py'))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        finally:
            sys.path.remove(d)
        _MODS[arm['name']] = mod
    return _MODS[arm['name']]


# ---------------------------------------------------------------- 배우는 세션
def learn(sc, rep, tmp, cur, sysline, start_cx):
    task = dict(sc['learn'], id='learn-' + sc['id'], key=[])
    run = {'id': 'learn-%s-%d' % (sc['id'], rep), 'task': task, 'arm': 'cur', 'arm_info': cur, 'model': sc['learn']['model'],
           'rep': rep, 'cortex': start_cx, 'persist': True, 'no_check': True}
    rec = B.run_one(run, tmp, sysline)
    rec['scenario'] = sc['id']
    rec['marks'] = 0
    if rec.get('transcript'):   # 세션이 remember.sh --mark 를 부른 횟수
        for line in open(rec['transcript'], encoding='utf-8', errors='replace'):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            for x in (d.get('message') or {}).get('content') or [] if d.get('type') == 'assistant' else []:
                cmd = ((x or {}).get('input') or {}).get('command') or '' if isinstance(x, dict) and x.get('type') == 'tool_use' else ''
                if 'remember.sh' in cmd and '--mark' in cmd:
                    rec['marks'] += 1
    return rec


# ---------------------------------------------------------------- 해마
def hippocampus(lr, sc, arm_name, arm, model, tmp, cur, start_cx):
    """[해마 한 번] 그 갈래의 재생 요약과 지침으로 해마가 시작 기억 저장소에 기억을 쓴다. 결과와 기계 채점"""
    rid = '%s-%s-%s' % (lr['id'], arm_name, model)
    base = os.path.join(tmp, 'hc', rid)
    brain = os.path.join(base, 'brain')
    res = {'id': rid, 'scenario': sc['id'], 'learn': lr['id'], 'rep': lr['rep'], 'arm': arm_name, 'model': model}
    try:
        shutil.copytree(os.path.join(cur['dir'], 'scripts'), os.path.join(brain, 'scripts'))
        shutil.copytree(os.path.join(arm['dir'], 'agents'), os.path.join(brain, 'agents'))
        cx = os.path.join(brain, 'cortex')
        shutil.copytree(start_cx, cx)
        probe_ws = os.path.realpath(os.path.join(base, 'probe')) + '/ledger'
        B.fill_registry(cx, [lr['ws'], probe_ws])
        os.makedirs(os.path.join(brain, '.active'))
        before = memory_files(cx)
        mod = replay_module(arm)
        try:
            r = mod.digest(lr['transcript'], B.SLUG, 0, lr['ws'])
        except TypeError:   # 옛 재생 코드는 root 인자가 없다
            r = mod.digest(lr['transcript'], B.SLUG, 0)
        if r is None:
            res['status'] = '요약 없음'
            return res
        text, score, n, end = r
        if arm_name == 'nomark':
            text = '\n'.join(l for l in text.splitlines() if ' M] ' not in l)
        res['digest'] = {'E': text.count(' E] '), 'M': text.count(' M] '), 'cues': text.count(' 단서: '), 'chars': len(text), 'score': score}
        hdir = os.path.join(cx, '.hippocampus')
        for d in ('replay', 'queue'):
            os.makedirs(os.path.join(hdir, d), exist_ok=True)
        sid = os.path.splitext(os.path.basename(lr['transcript']))[0]
        dp = os.path.join(hdir, 'replay', '%s-0.md' % sid)
        open(dp, 'w', encoding='utf-8').write(text + '\n')
        req = {'mode': 'replay', 'project_root': lr['ws'], 'slug': B.SLUG, 'stack': 'python', 'caller': 'brain-awake',
               'payload': {'kind': 'awake', 'digest': dp, 'session': sid, 'transcript': lr['transcript'], 'score': score, 'bytes': [0, end]}}
        qid = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-bench'
        json.dump(req, open(os.path.join(hdir, 'queue', qid + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        env = dict(os.environ, HIPPOCAMPUS_MODEL=model, BRAIN_HC_ISOLATE='1', N_WORKER_IDLE_SLEEP='1', N_WORKER_POLL_SEC='3')
        t0 = time.time()
        try:
            subprocess.run(['bash', os.path.join(brain, 'scripts', 'hippocampus-daemon.sh')], cwd=brain, env=env,
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=HC_TIMEOUT)
        except subprocess.TimeoutExpired:
            res['status'] = 'timeout'
        res['wall_s'] = round(time.time() - t0, 1)
        done = os.path.join(hdir, 'done', qid + '.json')
        if os.path.isfile(done):
            res['status'] = res.get('status') or (json.load(open(done, encoding='utf-8')).get('status') or '?')
        raw = os.path.join(hdir, 'logs', qid + '.json')
        hsid = None
        try:
            d = json.load(open(raw, encoding='utf-8'))
            res['cost'] = d.get('total_cost_usd')
            res['turns'] = d.get('num_turns')
            hsid = d.get('session_id')
        except (IOError, OSError, ValueError):
            pass
        res['isolation'] = []
        if os.path.exists(B.encoded_project_dir(os.path.realpath(cx))):
            shutil.rmtree(B.encoded_project_dir(os.path.realpath(cx)), ignore_errors=True)
            res['isolation'].append('~/.claude/projects 에 해마 세션 폴더가 생겨 지움')
        inst = os.path.expanduser('~/.claude/skills/brain/.active/recall.log')
        if hsid and os.path.isfile(inst) and hsid in open(inst, encoding='utf-8', errors='replace').read()[-2000000:]:
            res['isolation'].append('설치본 brain 훅이 해마 세션에 돌았음')
        after = memory_files(cx)
        changed = sorted(k for k in after if before.get(k) != after[k])
        res['new'] = [k for k in changed if k not in before and '/lessons/' in '/' + k]
        res['changed'] = changed
        res['key'] = key_memories(after, changed, sc['key'])
        res['stored'] = bool(res['key']) if sc['key'] else None
        res['cortex'] = cx
        if sc.get('probe') and res['key']:
            res['probe_shown'] = probe(sc, brain, probe_ws, res['key'])
    except Exception as e:
        res['error'] = '%s: %s' % (e.__class__.__name__, e)
    return res


def key_memories(files, changed, regs):
    """[핵심 사실을 담은 기억] 바뀐 기억 본문(그 본문을 가리키는 색인 줄 포함)에 key 정규식이 모두 맞는 것"""
    if not regs:
        return []
    out = []
    index_text = '\n'.join(v for k, v in files.items() if 'index' in os.path.basename(k).lower())
    for k in changed:
        if '/lessons/' not in '/' + k:
            continue
        base = os.path.basename(k)
        text = files[k] + '\n' + '\n'.join(l for l in index_text.splitlines() if base in l)
        if all(re.search(r, text, re.I) for r in regs):
            out.append(os.path.splitext(base)[0])
    return out


def probe(sc, brain, ws, keys):
    """[닿음 2차] 시험 세션이 겪을 상황(명령 출력 또는 편집)을 그 기억 저장소의 훅에 넣어 핵심 기억 키워드가 떠오르나"""
    shutil.copytree(B.FIX_PROJECT, ws)   # 시험 상황은 시험 과제의 시작 상태(픽스처 그대로)다 - 배우는 세션의 덮어쓰기는 쓰지 않는다
    pr = sc['probe']
    if 'run' in pr:
        p = subprocess.run([sys.executable if a == 'python3' else a for a in pr['run']], cwd=ws, capture_output=True, text=True, timeout=120)
        out = (p.stdout or '') + (p.stderr or '')
        if p.returncode:
            ev = {'hook_event_name': 'PostToolUseFailure', 'tool_name': 'Bash', 'tool_input': {'command': ' '.join(pr['run'])},
                  'error': 'Exit code %d\n%s' % (p.returncode, out)}
        else:
            ev = {'hook_event_name': 'PostToolUse', 'tool_name': 'Bash', 'tool_input': {'command': ' '.join(pr['run'])},
                  'tool_response': {'stdout': p.stdout, 'stderr': p.stderr, 'interrupted': False}}
    else:
        e = pr['edit']
        ev = {'hook_event_name': 'PreToolUse', 'tool_name': 'Edit',
              'tool_input': {'file_path': os.path.join(ws, e['path']), 'old_string': '', 'new_string': e['new']}}
    ev.update(session_id='probe', cwd=ws)
    p = subprocess.run([sys.executable, os.path.join(brain, 'scripts', 'thalamus.py'), 'hook'], input=json.dumps(ev),
                       capture_output=True, text=True, cwd=ws, timeout=60)
    return any('`%s`' % keyword(k) in p.stdout for k in keys)


# ---------------------------------------------------------------- 시험 세션
def test_session(tag, sc, cortex, key, arm_name, model, rep, tmp, cur, sysline):
    task = json.load(open(os.path.join(HERE, 'tasks', sc['test_task'] + '.json'), encoding='utf-8'))
    run = {'id': 'test-%s' % tag, 'task': task, 'arm': 'off' if arm_name == 'off' else 'cur', 'arm_info': cur, 'model': model,
           'rep': rep, 'key': key}
    if cortex:
        clean = os.path.join(tmp, 'tcx', tag)
        shutil.copytree(cortex, clean, ignore=shutil.ignore_patterns('.hippocampus'))
        reg = os.path.join(clean, 'registry.md')
        text = open(reg, encoding='utf-8').read()
        if '{{ROWS}}' not in text:   # 해마가 쓴 저장소는 registry 행이 채워져 있다 - 시험 작업 폴더로 다시 채우게 비운다
            head = text.split('|---|')[0] + '|---|---|---|---|---|\n{{ROWS}}\n'
            open(reg, 'w', encoding='utf-8').write(head)
        run['cortex'] = clean
    rec = B.run_one(run, tmp, sysline)
    rec.update(scenario=sc['id'], enc_arm=arm_name)
    return rec


# ---------------------------------------------------------------- 진입
def run_encode(depth, models, reps, jobs, tmp, sysline, cur):
    scs = scenarios(depth)
    start_cx = cortex_template(tmp, 'start')
    ideal_cx = cortex_template(tmp, 'ideal')
    old = B.prepare_arm('enc-old', tmp, OLD_REF)
    arms = [('old', old), ('new', cur)] + ([('nomark', dict(cur, name='nomark'))] if depth != 'low' else [])
    test_models = ['sonnet'] if depth == 'low' else models
    for a, arm in arms:   # 갈래마다 자기 재생 코드를 미리 불러 둔다(쓰레드에서 sys.modules 를 동시에 고치지 않게)
        replay_module(arm)
    print('저장 벤치: 시나리오 %s, 갈래 %s, 해마 모델 %s, 회차 %d, 시험 모델 %s' % (
        '/'.join(s['id'] for s in scs), '/'.join(a for a, _ in arms), ','.join(models), reps, ','.join(test_models)), flush=True)
    with concurrent.futures.ThreadPoolExecutor(jobs) as ex:
        learns = list(ex.map(lambda x: learn(x[0], x[1], tmp, cur, sysline, start_cx), [(s, r) for s in scs for r in range(1, reps + 1)]))
    print('  배우는 세션 %d개 끝 (표시 %d개)' % (len(learns), sum(l.get('marks', 0) for l in learns)), flush=True)
    byid = dict((s['id'], s) for s in scs)
    jobs_hc = [(lr, byid[lr['scenario']], a, arm, m) for lr in learns if lr.get('transcript') for a, arm in arms for m in models]
    with concurrent.futures.ThreadPoolExecutor(jobs) as ex:
        hcs = list(ex.map(lambda x: hippocampus(x[0], x[1], x[2], x[3], x[4], tmp, cur, start_cx), jobs_hc))
    print('  해마 %d회 끝' % len(hcs), flush=True)
    tests = []
    for h in hcs:
        sc = byid[h['scenario']]
        if sc.get('test_task') and h.get('cortex'):
            for m in test_models:
                tests.append(('%s-%s' % (h['id'], m), sc, h['cortex'], h.get('key') or [], h['arm'], m, h['rep']))
    for sc in scs:
        if not sc.get('test_task'):
            continue
        tkey = json.load(open(os.path.join(HERE, 'tasks', sc['test_task'] + '.json'), encoding='utf-8'))['key']
        for m in test_models:
            for r in range(1, reps + 1):
                tests.append(('%s-off-%s-%d' % (sc['id'], m, r), sc, None, [], 'off', m, r))
                tests.append(('%s-ideal-%s-%d' % (sc['id'], m, r), sc, ideal_cx, tkey, 'ideal', m, r))
    with concurrent.futures.ThreadPoolExecutor(jobs) as ex:
        trs = list(ex.map(lambda x: test_session(x[0], x[1], x[2], x[3], x[4], x[5], x[6], tmp, cur, sysline), tests))
    print('  시험 세션 %d개 끝' % len(trs), flush=True)
    for h in hcs:   # 결과에는 경로 대신 이름만
        h.pop('cortex', None)
    for l in learns:
        l.pop('transcript', None)
    return {'scenarios': [s['id'] for s in scs], 'arms': [a for a, _ in arms], 'models': models, 'test_models': test_models,
            'old_ref': old['commit'], 'start_hash': B.tree_hash(start_cx), 'enc_hash': B.tree_hash(ENC),
            'learn': learns, 'hippo': hcs, 'test': trs}


def frac(xs):
    xs = [x for x in xs if x is not None]
    return '-' if not xs else '%d/%d' % (sum(1 for x in xs if x), len(xs))


def report(E):
    L = ['## 저장 벤치 (encode)', '',
         '배우는 세션 → 해마 → 시험 세션. 저장됨 = 핵심 사실이 기억에 들어감(사전 등록 정규식), 닿음 = 시험 상황을 훅에 넣었을 때 그 기억 키워드가 뜸, '
         '시험 떠올림 = 시험 세션에서 그 기억이 떠오르거나 열림, 통과 = 시험 세션 채점 통과. 갈래 차이는 재생 요약과 해마 지침뿐이다.', '',
         '| 갈래 | 해마 모델 | 저장됨 | 닿음 | 시험 떠올림 | 시험 통과 | 새 기억 수(평균) | 잡음 시나리오 새 기억 | 해마 비용 평균($) | 무효 |',
         '|---|---|---|---|---|---|---|---|---|---|']
    hcs, trs = E['hippo'], E['test']
    for arm in E['arms']:
        for m in E['models'] + ['전체']:
            g = [h for h in hcs if h['arm'] == arm and (m == '전체' or h['model'] == m)]
            gk = [h for h in g if h['scenario'] != 'noise']
            gn = [h for h in g if h['scenario'] == 'noise']
            t = [r for r in trs if r.get('enc_arm') == arm and any(r['id'].startswith('test-' + h['id']) for h in g)]
            L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %d |' % (
                arm, m, frac([h.get('stored') for h in gk]), frac([h.get('probe_shown') for h in gk if h.get('stored')]),
                frac([(r.get('key_shown') or r.get('key_opened')) if r.get('key_shown') is not None else False for r in t]),
                frac([r.get('pass') for r in t]),
                B.fmt(B.mean([len(h.get('new') or []) for h in gk]), '%.1f'), B.fmt(B.mean([len(h.get('new') or []) for h in gn]), '%.1f'),
                B.fmt(B.mean([h.get('cost') for h in g]), '%.3f'), sum(1 for h in g if h.get('error') or h.get('isolation'))))
    for arm in ('off', 'ideal'):
        t = [r for r in trs if r.get('enc_arm') == arm]
        if t:
            L.append('| %s | - | - | - | %s | %s | - | - | - | %d |' % (arm, frac([r.get('key_shown') or r.get('key_opened') for r in t]) if arm == 'ideal' else '-',
                                                                     frac([r.get('pass') for r in t]), sum(1 for r in t if r.get('error') or r.get('isolation'))))
    L += ['', '해마 실행 상태(done 정상, partial 부분, failed/denied/timeout 실패): ' + ', '.join('%s %d' % kv for kv in sorted(_count(h.get('status') or h.get('error') or '?' for h in hcs).items())),
          '배우는 세션: %d개, 세션 표시(remember.sh --mark) 사용 %d번, 무효 %d' % (len(E['learn']), sum(l.get('marks', 0) for l in E['learn']),
                                                                         sum(1 for l in E['learn'] if l.get('isolation') or l.get('error'))),
          '기준: 옛 저장 %s, 시작 기억 저장소 해시 %s, 사전 등록 해시 %s' % (E['old_ref'], E['start_hash'], E['enc_hash']), '',
          '### 해마 실행 전체', '', '| 실행 | 상태 | 요약 E/M/단서 | 새 기억 | 핵심 기억 | 닿음 | 비용 | 무효 이유 |', '|---|---|---|---|---|---|---|---|']
    for h in hcs:
        dg = h.get('digest') or {}
        L.append('| %s | %s | %s/%s/%s | %s | %s | %s | %s | %s |' % (
            h['id'], h.get('status') or h.get('error') or '?', dg.get('E', '-'), dg.get('M', '-'), dg.get('cues', '-'),
            ', '.join(keyword(x) for x in h.get('new') or []) or '-', ', '.join(h.get('key') or []) or '-',
            {True: 'O', False: 'X', None: '-'}[h.get('probe_shown')], B.fmt(h.get('cost'), '%.3f'),
            '; '.join(h.get('isolation') or []) or (h.get('error') or '-')))
    return L


def _count(xs):
    out = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return out
