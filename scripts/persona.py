#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 성격 - 프로젝트마다 사용자가 정한 작업 방식(성향 노드 그래프)을 세션에 싣는 문장과 훅 관문으로 컴파일한다.

저장: <brain>/persona/<슬러그>.json (기기 로컬, 저장소에 안 올라간다). 쓰는 곳은 에디터(editor/server.py)뿐이고,
thalamus 가 훅마다 읽어 컴파일한다. 컴파일은 표 기반이라 같은 그래프는 언제나 같은 결과가 된다(미리보기 = 실제 주입).

그래프:
  nodes: [{id, kind: 'trait', trait: <TRAITS 키>, level: 1|2|3}, {id, kind: 'situation', situation: <SITUATIONS 키>}]
  edges: [{from: <trait 노드 id>, to: <situation 노드 id>}]   성향이 어느 상황에서 쓰이는가. normal(평소)이 허브다
  verify_re: 검증 명령으로 볼 정규식(비우면 VERIFY_DEFAULT), big_files: 큰 변경으로 볼 파일 수(기본 5), enabled
강도와 수단(성격이 행동을 바꾸는 길):
  1 = 세션 시작 문장(약한 표현)  2 = 문장 + 요청마다 한 줄 상기  3 = 2 + 훅 관문(PreToolUse ask/deny, Stop block)
  관문이 없는 성향,상황 조합의 3 은 2 로 내리고 경고한다.
문장은 사실형이다 - 명령형 훅 문구는 모델이 프롬프트 주입으로 의심한다(thalamus.py 머리 주석, 2026-09-29 실측).

명령행: persona.py compile <json 경로>   컴파일 결과 JSON
        persona.py show <슬러그>          저장된 성격의 컴파일 결과(세션 문장, 상기 줄, 관문, 경고)
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
PERSONA_DIR = os.environ.get('BRAIN_PERSONA_DIR') or os.path.join(BRAIN, 'persona')   # 시험용으로 바꿔 끼울 수 있다

SESSION_BUDGET = 600      # 세션 시작 문장 글자 상한 - 넘으면 경고(자르지 않는다)
TURN_BUDGET = 90          # 요청마다 상기 줄 글자 상한
TRAIT_SOFT_MAX = 7        # 활성 성향 노드가 이보다 많으면 문장이 묽어진다는 경고

# 축 - 같은 축의 양 끝은 같은 상황에서 섞인다(오른쪽 강도 - 왼쪽 강도)
AXES = [
    ('speed', '속도', 'drive', 'careful'),
    ('ask', '질문', 'autonomy', 'curious'),
    ('verify', '검증', 'quick', 'thorough'),
    ('scope', '범위', 'minimal', 'proactive'),
    ('report', '보고', 'concise', 'friendly'),
]

# 성향: 이름, 아이콘, 축, 상기용 짧은 말, 문장(약, 강). 문장은 관찰 가능한 행동과 숫자로 쓴다
TRAITS = {
    'drive': dict(name='추진', icon='🚀', axis='speed', short='확인 없이 진행',
                  soft='충분히 알면 확인을 구하지 않고 진행하는 편이다',
                  firm='충분히 알면 확인을 구하지 않고 바로 고치고, 끝난 뒤 한 일을 보고한다'),
    'careful': dict(name='신중', icon='🧘', axis='speed', short='계획 먼저',
                    soft='고치기 전에 무엇을 바꿀지 한두 줄로 먼저 밝힌다',
                    firm='고치기 전에 계획(바꿀 파일, 방법, 되돌리는 법)을 먼저 보이고 나서 진행한다'),
    'autonomy': dict(name='자율', icon='🧭', axis='ask', short='묻지 말고 기본값',
                     soft='모호한 점은 합리적 기본값으로 정하는 편이다',
                     firm='모호한 점은 묻지 않고 합리적 기본값으로 진행하고, 가정한 것을 결과 끝에 적는다'),
    'curious': dict(name='호기심', icon='🔍', axis='ask', short='모호하면 질문',
                    soft='해석이 갈리는 점은 물어본다',
                    firm='고치기 전에 해석이 갈리는 점을 질문으로 확인한다(한 번에 3개 이하)'),
    'quick': dict(name='빠름', icon='⚡', axis='verify', short='검증 가볍게',
                  soft='검증은 가볍게 한다',
                  firm='검증은 바꾼 부분에 직접 닿는 확인 하나로 끝낸다'),
    'thorough': dict(name='꼼꼼', icon='🔬', axis='verify', short='고친 뒤 검증',
                     soft='고친 뒤 빌드나 테스트로 확인한다',
                     firm='고친 뒤 빌드, 테스트, 실제 실행 중 가능한 것으로 확인하고 그 결과를 보고에 적는다'),
    'minimal': dict(name='최소', icon='✂️', axis='scope', short='요청 범위만',
                    soft='요청 범위 안에서만 고친다',
                    firm='요청한 것만 고친다. 주변 개선은 고치지 않고 보고 끝에 한 줄로 제안만 한다'),
    'proactive': dict(name='적극', icon='🌱', axis='scope', short='관련 개선 같이',
                      soft='관련된 개선점이 보이면 제안한다',
                      firm='요청과 직접 관련된 결함이나 개선은 같이 고치고 보고에 따로 적는다'),
    'concise': dict(name='간결', icon='📏', axis='report', short='보고 짧게',
                    soft='보고는 짧게 한다',
                    firm='결과 보고는 5줄 안으로, 바뀐 것과 확인한 것만 적는다'),
    'friendly': dict(name='친절', icon='💬', axis='report', short='이유 설명',
                     soft='결정의 이유를 함께 설명한다',
                     firm='결과 보고에 무엇을 왜 그렇게 했는지와 고려한 대안을 설명한다'),
}

# 상황: 이름, 아이콘, 문장 머리, 감지 수단(None 이면 모델 판단 - 강제 불가)
SITUATIONS = {
    'normal': dict(name='평소', icon='🏠', prefix='', detect='always'),
    'risky': dict(name='되돌리기 어려운 작업', icon='💣',
                  prefix='되돌리기 어려운 작업(파일 삭제, 강제 푸시, 이력 재작성, DB 변경, 배포)에서는', detect='bash'),
    'after_edit': dict(name='코드를 고친 뒤', icon='🛠️', prefix='코드를 고친 뒤에는', detect='stop'),
    'big_change': dict(name='큰 변경', icon='🏗️', prefix='한 요청에서 파일 {n}개 넘게 바꾸게 되면', detect='edit'),
    'ambiguous': dict(name='요청이 모호할 때', icon='🌫️', prefix='요청 해석이 둘 이상이면', detect=None),
    'new_area': dict(name='처음 보는 영역', icon='🗺️', prefix='처음 보는 코드 영역을 다룰 때는', detect=None),
}

# 상황별 고유 문장 - 일반 문장보다 그 자리에 맞는 행동이 있을 때
SPECIAL = {
    ('careful', 'risky'): '실행 전에 멈추고 무엇이 사라지거나 바뀌는지 밝힌다',
    ('careful', 'big_change'): '더 진행하기 전에 지금까지 바꾼 것과 남은 계획을 정리해 보인다',
    ('thorough', 'after_edit'): '끝내기 전에 빌드나 테스트로 확인하고 결과를 보고에 적는다',
    ('curious', 'ambiguous'): '고치기 전에 갈리는 점을 질문으로 확인한다(한 번에 3개 이하)',
    ('curious', 'new_area'): '구조를 먼저 읽고, 이해가 안 되는 점은 고치기 전에 묻는다',
    ('careful', 'new_area'): '구조를 먼저 읽고 영향 범위를 밝힌 뒤 고친다',
}

# 상기 줄의 짧은 말 - 상황 이름과 그 자리의 행동
SIT_SHORT = {'risky': '위험 작업', 'after_edit': '고친 뒤', 'big_change': '큰 변경', 'ambiguous': '모호할 때', 'new_area': '처음 보는 곳'}
SPECIAL_SHORT = {('careful', 'risky'): '멈추고 확인', ('careful', 'big_change'): '멈추고 정리', ('thorough', 'after_edit'): '반드시 검증',
                 ('curious', 'ambiguous'): '질문', ('curious', 'new_area'): '읽고 질문', ('careful', 'new_area'): '읽고 영향 밝히기'}

# 관문 - (성향, 상황) 이 강도 3 일 때 거는 훅. 여기 없는 조합의 3 은 2 로 내린다
GATES = {
    ('careful', 'risky'): ('risky_ask', '되돌리기 어려운 명령 앞에서 사용자 확인'),
    ('careful', 'big_change'): ('big_change_ask', '파일을 기준 수보다 많이 바꾸면 사용자 확인'),
    ('careful', 'normal'): ('first_edit_ask', '요청마다 첫 파일 수정 앞에서 사용자 확인'),
    ('thorough', 'after_edit'): ('verify_stop', '고치고 검증 없이 끝내려 하면 한 번 되돌려 보냄'),
    ('thorough', 'normal'): ('verify_stop', '고치고 검증 없이 끝내려 하면 한 번 되돌려 보냄'),
    ('autonomy', 'normal'): ('deny_ask', '선택지 질문 도구를 막고 기본값으로 진행시킴'),
    ('autonomy', 'ambiguous'): ('deny_ask', '선택지 질문 도구를 막고 기본값으로 진행시킴'),
}

# 조합 문장 - 같은 상황에 둘 다 있으면 붙는다(축이 다른 성향끼리)
COMBOS = [
    (('drive', 'curious'), '궁금한 점은 묻되 답을 기다리며 멈추지 않는다 - 기본값으로 진행하고 질문과 가정을 결과 끝에 적는다'),
    (('careful', 'concise'), '계획은 3줄 안으로 보인다'),
    (('proactive', 'thorough'), '요청 밖에서 고친 것도 확인 대상에 넣는다'),
    (('drive', 'thorough'), '빠르게 진행하되 끝내기 전 확인은 거르지 않는다'),
    (('curious', 'concise'), '질문은 짧게, 고를 수 있는 선택지로 묻는다'),
    (('minimal', 'friendly'), '고치지 않은 주변 문제는 이유와 함께 목록으로만 남긴다'),
]

# 검증 명령 기본 패턴 - 빌드, 테스트, 타입 검사, 린트, 문법 검사
VERIFY_DEFAULT = (r'\b(test|tests|pytest|jest|vitest|mocha|unittest|tsc|eslint|ruff|mypy|pyright|py_compile|'
                  r'cargo (test|build|check|clippy)|go (test|build|vet)|dotnet (build|test)|gradle|mvn|make\b|'
                  r'npm (run )?(test|build|lint|check|compile)|pnpm (run )?(test|build|lint)|yarn (test|build|lint)|'
                  r'xcodebuild|swift (build|test)|-batchmode|-runTests|bash -n|node --check|shellcheck)\b')

# 되돌리기 어려운 명령
RISKY_RE = re.compile(
    r'(\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)|\bgit\s+push\b[^\n]*(--force|-f\b|--delete|\s:)|\bgit\s+reset\s+--hard|'
    r'\bgit\s+clean\s+-[a-zA-Z]*f|\bgit\s+(checkout|restore)\s+(--\s+)?\.(\s|$)|\bgit\s+branch\s+-D|\bgit\s+rebase\b|'
    r'\bgit\s+filter-(branch|repo)|\bgit\s+stash\s+(drop|clear)|\bdrop\s+(table|database|schema)\b|\btruncate\s+table\b|'
    r'\bdelete\s+from\b|\bnpm\s+publish|\bvsce\s+publish|\bdocker\s+(system\s+prune|rm|rmi)\b|\bkubectl\s+delete|'
    r'\bterraform\s+(apply|destroy)|\bmkfs|\bdd\s+if=|>\s*/dev/sd|\bchmod\s+-R|\bchown\s+-R|\bfind\b[^\n]*-delete)',
    re.I)

# 품종(프리셋) - 다마고치처럼 고르는 시작점. 그래프는 이것으로 만든다
BREEDS = {
    'squirrel': dict(name='다람쥐', icon='🐿️', desc='재빠르게 해치우는 타입. 위험한 것만 멈춘다',
                     fit='프로토타입, 개인 도구',
                     traits=[('drive', 2, 'normal'), ('autonomy', 2, 'normal'), ('concise', 2, 'normal'),
                             ('careful', 3, 'risky')]),
    'owl': dict(name='부엉이', icon='🦉', desc='계획하고 확인하는 타입. 고친 건 반드시 검증한다',
                fit='배포되는 확장, 유료 패키지',
                traits=[('careful', 2, 'normal'), ('thorough', 3, 'after_edit'), ('concise', 1, 'normal'),
                        ('careful', 3, 'risky')]),
    'cat': dict(name='고양이', icon='🐱', desc='궁금한 게 많은 탐험가. 묻고 제안한다',
                fit='낯선 코드 탐색, 설계 단계',
                traits=[('curious', 2, 'ambiguous'), ('proactive', 2, 'normal'), ('friendly', 2, 'normal'),
                        ('curious', 2, 'new_area')]),
    'turtle': dict(name='거북이', icon='🐢', desc='느리지만 정확하다. 범위를 지키고 크게 바꿀 땐 멈춘다',
                   fit='원본 충실 이식, 큰 코드베이스',
                   traits=[('careful', 3, 'big_change'), ('thorough', 3, 'after_edit'), ('minimal', 2, 'normal'),
                           ('careful', 3, 'risky')]),
}


# ---------------------------------------------------------------- 저장
def _safe(slug):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', slug or '')[:80]


def path_of(slug):
    return os.path.join(PERSONA_DIR, _safe(slug) + '.json')


def load(slug):
    """[저장된 성격] 없거나 깨졌으면 None"""
    try:
        with open(path_of(slug), encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (IOError, OSError, ValueError):
        return None


def save(slug, graph):
    """[성격 저장] 검증한 그래프를 원자적으로 쓴다. 저장한 그래프를 돌려준다"""
    g = normalize(graph)
    g['slug'] = slug
    g['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    os.makedirs(PERSONA_DIR, exist_ok=True)
    p = path_of(slug)
    tmp = '%s.%d.tmp' % (p, os.getpid())
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(g, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    return g


def from_breed(key):
    """[품종 → 그래프] 상황 노드는 쓰인 것만, 성향 노드는 왼쪽 열, 상황 노드는 오른쪽 열에 놓는다"""
    b = BREEDS[key]
    nodes, edges, sit_ids = [], [], {}
    for i, (t, lv, s) in enumerate(b['traits']):
        if s not in sit_ids:
            sit_ids[s] = 's-' + s
            nodes.append({'id': sit_ids[s], 'kind': 'situation', 'situation': s,
                          'x': 560, 'y': 60 + 110 * len(sit_ids) - 110})
        nid = 't%d' % (i + 1)
        nodes.append({'id': nid, 'kind': 'trait', 'trait': t, 'level': lv, 'x': 80, 'y': 40 + 100 * i})
        edges.append({'from': nid, 'to': sit_ids[s]})
    return {'version': 1, 'breed': key, 'name': b['name'], 'enabled': True, 'nodes': nodes, 'edges': edges,
            'verify_re': '', 'big_files': 5}


def normalize(graph):
    """[그래프 정리] 모르는 성향,상황, 끊긴 연결, 잘못된 강도를 걷어 낸다"""
    g = graph if isinstance(graph, dict) else {}
    nodes, ids = [], {}
    for n in g.get('nodes') or []:
        if not isinstance(n, dict) or not n.get('id'):
            continue
        nid = str(n['id'])[:40]
        x, y = n.get('x', 0), n.get('y', 0)
        pos = {'x': float(x) if isinstance(x, (int, float)) else 0, 'y': float(y) if isinstance(y, (int, float)) else 0}
        if n.get('kind') == 'trait' and n.get('trait') in TRAITS:
            lv = n.get('level')
            lv = lv if lv in (1, 2, 3) else 2
            nodes.append(dict(pos, id=nid, kind='trait', trait=n['trait'], level=lv))
        elif n.get('kind') == 'situation' and n.get('situation') in SITUATIONS:
            nodes.append(dict(pos, id=nid, kind='situation', situation=n['situation']))
        else:
            continue
        ids[nid] = nodes[-1]
    edges, seen = [], set()
    for e in g.get('edges') or []:
        if not isinstance(e, dict):
            continue
        a, b = str(e.get('from')), str(e.get('to'))
        if a in ids and b in ids and ids[a]['kind'] == 'trait' and ids[b]['kind'] == 'situation' and (a, b) not in seen:
            seen.add((a, b))
            edges.append({'from': a, 'to': b})
    bf = g.get('big_files')
    vr = g.get('verify_re') if isinstance(g.get('verify_re'), str) else ''
    try:
        re.compile(vr or VERIFY_DEFAULT)
    except re.error:
        vr = ''
    return {'version': 1, 'breed': g.get('breed') if g.get('breed') in BREEDS else '',
            'name': str(g.get('name') or '')[:40], 'enabled': g.get('enabled') is not False,
            'nodes': nodes, 'edges': edges, 'verify_re': vr[:400],
            'big_files': bf if isinstance(bf, int) and 2 <= bf <= 50 else 5}


# ---------------------------------------------------------------- 컴파일
def compile_graph(graph):
    """[그래프 → 주입물]
    - session: 세션 시작에 싣는 여러 줄(사실형), turn: 요청마다 한 줄, gates: 훅 관문 설정, warnings: 사용자에게 보일 경고
    - 같은 상황, 같은 축의 양 끝은 강도 차로 섞인다(0 이면 상쇄). 관문 없는 3 은 2 로 내린다
    """
    g = normalize(graph)
    nodes = {n['id']: n for n in g['nodes']}
    warnings = []
    # 상황별 성향 강도 - 같은 성향이 같은 상황에 여러 번이면 센 쪽
    by_sit = {}
    linked = set()
    for e in g['edges']:
        t, s = nodes[e['from']], nodes[e['to']]
        linked.add(t['id'])
        cur = by_sit.setdefault(s['situation'], {})
        cur[t['trait']] = max(cur.get(t['trait'], 0), t['level'])
    loose = [n for n in g['nodes'] if n['kind'] == 'trait' and n['id'] not in linked]
    if loose:
        warnings.append('연결 안 된 성향 %d개는 쓰이지 않아요: %s' % (
            len(loose), ', '.join(TRAITS[n['trait']]['name'] for n in loose)))
    active = sum(len(v) for v in by_sit.values())
    if active > TRAIT_SOFT_MAX:
        warnings.append('성향이 %d개라 문장이 묽어져요. %d개 이하가 효과적이에요' % (active, TRAIT_SOFT_MAX))
    # 축 섞기
    for s, tr in by_sit.items():
        for key, label, left, right in AXES:
            if left in tr and right in tr:
                tr_l, tr_r = tr[left], tr[right]
                d = tr_r - tr_l
                ln, rn = TRAITS[left]['name'], TRAITS[right]['name']
                sn = SITUATIONS[s]['name']
                del tr[left], tr[right]
                if d == 0:
                    warnings.append('%s: %s %d, %s %d이 같은 세기라 서로 상쇄돼요' % (sn, ln, tr_l, rn, tr_r))
                else:
                    win = right if d > 0 else left
                    tr[win] = abs(d)
                    warnings.append('%s: %s %d, %s %d이 섞여 %s %d만 남아요' % (sn, ln, tr_l, rn, tr_r, TRAITS[win]['name'], abs(d)))
    # 관문과 강도 3 내리기
    gates = {}
    for s, tr in by_sit.items():
        for t, lv in list(tr.items()):
            if lv < 3:
                continue
            gk = GATES.get((t, s))
            if gk is None:
                tr[t] = 2
                why = '감지할 수 없는 상황이라' if SITUATIONS[s]['detect'] is None else '이 조합은 강제 수단이 없어'
                warnings.append('%s의 %s 3은 %s 2로 내렸어요' % (SITUATIONS[s]['name'], TRAITS[t]['name'], why))
            else:
                gates[gk[0]] = gk[1]
    if 'first_edit_ask' in gates and 'big_change_ask' in gates:
        del gates['big_change_ask']   # 첫 수정마다 묻는다면 큰 변경 확인은 겹친다
    # 문장
    lines = []
    order = ['normal', 'ambiguous', 'new_area', 'big_change', 'after_edit', 'risky']
    for s in order:
        tr = by_sit.get(s)
        if not tr:
            continue
        ts = sorted(tr, key=lambda t: ([a[0] for a in AXES].index(TRAITS[t]['axis']), t))
        clauses = []
        used_combo = set()
        for pair, text in COMBOS:
            if pair[0] in tr and pair[1] in tr:
                clauses.append(text)
                if pair == ('drive', 'curious'):
                    used_combo.add('curious')   # 조합 문장이 호기심의 행동을 대신한다
        base = []
        for t in ts:
            if t in used_combo:
                continue
            txt = SPECIAL.get((t, s)) or (TRAITS[t]['firm'] if tr[t] >= 2 else TRAITS[t]['soft'])
            if tr[t] >= 3 and (t, s) in GATES:
                txt += '(설정으로 강제됨)'
            base.append(txt)
        body = '. '.join(base + clauses)
        prefix = SITUATIONS[s]['prefix'].format(n=g['big_files'])
        if s == 'normal':
            lines.append('- 평소: %s.' % body)
        else:
            lines.append('- %s %s.' % (prefix, body))
    session = ''
    if lines:
        head = '[기억] 사용자가 이 프로젝트에서 원하는 작업 방식(brain 성격 설정%s). 학습된 선호와 어긋나면 이 설정이 우선이다:' % (
            ', ' + g['name'] if g['name'] else '')
        session = '\n'.join([head] + lines + ['- 이번 요청에서 사용자가 다르게 말하면 그 말이 우선이다.'])
        if len(session) > SESSION_BUDGET:
            warnings.append('세션 문장이 %d자로 예산(%d자)을 넘어요. 성향을 줄이면 각 문장이 더 잘 지켜져요' % (len(session), SESSION_BUDGET))
    # 요청마다 한 줄 - 강도 2 이상 중 센 것부터 셋
    picks = []
    for s in order:
        for t, lv in (by_sit.get(s) or {}).items():
            if lv >= 2:
                lab = TRAITS[t]['short'] if s == 'normal' else '%s엔 %s' % (SIT_SHORT[s], SPECIAL_SHORT.get((t, s)) or TRAITS[t]['short'])
                picks.append((-lv, order.index(s), lab))
    picks.sort()
    turn = ''
    if picks:
        turn = '[기억] 이 프로젝트의 작업 방식: ' + ', '.join(p[2] for p in picks[:3])
        if len(turn) > TURN_BUDGET:
            turn = '[기억] 이 프로젝트의 작업 방식: ' + ', '.join(p[2] for p in picks[:2])
    gate_cfg = {k: True for k in gates}
    if 'big_change_ask' in gates:
        gate_cfg['big_change_ask'] = g['big_files']
    if 'verify_stop' in gates:
        gate_cfg['verify_re'] = g['verify_re'] or VERIFY_DEFAULT
    effective = {s: dict(tr) for s, tr in by_sit.items() if tr}
    return {'session': session, 'turn': turn, 'gates': gate_cfg, 'gate_notes': gates, 'warnings': warnings,
            'effective': effective, 'enabled': g['enabled']}


def compiled(slug):
    """[thalamus 용] 저장된 성격이 있고 켜져 있으면 컴파일 결과, 아니면 None"""
    g = load(slug)
    if not g or g.get('enabled') is False:
        return None
    c = compile_graph(g)
    return c if (c['session'] or c['gates']) else None


def catalog():
    """[에디터 용] 성향, 상황, 축, 품종 목록"""
    return {
        'traits': {k: {x: v[x] for x in ('name', 'icon', 'axis', 'short', 'soft', 'firm')} for k, v in TRAITS.items()},
        'situations': {k: {'name': v['name'], 'icon': v['icon'], 'detect': v['detect'], 'short': SIT_SHORT.get(k, '평소'),
                           'forceable': any(gk[1] == k for gk in GATES)} for k, v in SITUATIONS.items()},
        'axes': [{'key': a[0], 'name': a[1], 'left': a[2], 'right': a[3]} for a in AXES],
        'breeds': {k: {x: v[x] for x in ('name', 'icon', 'desc', 'fit')} for k, v in BREEDS.items()},
        'gates': ['%s+%s' % k for k in GATES],
        'special_short': {'%s+%s' % k: v for k, v in SPECIAL_SHORT.items()},
        'verify_default': VERIFY_DEFAULT,
    }


# ---------------------------------------------------------------- 관문 판정 (thalamus 가 부른다)
def is_risky(cmd):
    return bool(cmd and RISKY_RE.search(cmd))


def is_verify(cmd, pattern):
    try:
        return bool(cmd and re.search(pattern or VERIFY_DEFAULT, cmd, re.I))
    except re.error:
        return False


CODE_EXT = re.compile(r'\.(md|txt|json|ya?ml|toml|ini|cfg|lock|csv|svg|png|jpe?g|gif)$', re.I)


def is_code(path):
    """[코드 파일인가] 문서, 설정, 자산은 검증 관문의 대상이 아니다"""
    return bool(path) and not CODE_EXT.search(path)


def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == 'compile':
        with open(a[1], encoding='utf-8') as f:
            print(json.dumps(compile_graph(json.load(f)), ensure_ascii=False, indent=1))
        return 0
    if len(a) >= 2 and a[0] == 'show':
        g = load(a[1])
        if not g:
            print('성격 없음: %s' % a[1])
            return 1
        c = compile_graph(g)
        print(c['session'] or '(세션 문장 없음)')
        print(c['turn'] or '(상기 줄 없음)')
        for k, v in c['gate_notes'].items():
            print('관문 %s: %s' % (k, v))
        for w in c['warnings']:
            print('경고: ' + w)
        return 0
    if len(a) >= 2 and a[0] == 'breed':
        print(json.dumps(compile_graph(from_breed(a[1])), ensure_ascii=False, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
