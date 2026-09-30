#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain thalamus(시상) - 감각(세션이 지금 다루는 파일, 명령, 에러)을 걸러 관련 장기 기억을 의식(세션)으로 올려 보내고,
깨어날 때(세션 시작) 그 자리에 맞는 기억 지도를 켠다. 세션은 이 장치를 모른다 - 기억이 떠오를 뿐이다.

훅 등록(~/.claude/settings.json, 명령은 `python3 <brain>/scripts/thalamus.py hook`):
  SessionStart                                        깨어남: 프로젝트 요지, 기억 지도(프로젝트 INDEX), 절차 기억(단계 카드) 줄
                                                      compact 면 이미 떠올린 목록도 비운다(압축으로 컨텍스트에서 빠졌다)
  PreToolUse  Edit|Write|MultiEdit|NotebookEdit|Bash  고칠 파일, 새로 부르는 API, 명령이 다루는 파일
  PostToolUse Read                                    연 파일(기억 저장소 파일이면 열람 기록만 - 기억 강도)
  PostToolUseFailure Bash                             C# 컴파일 에러, 예외(첫 프로젝트 프레임)
  UserPromptSubmit                                    요청마다: 계획 전에 이번 작업 영역의 색인을 열어 보는 습관 한 줄(HABIT)
  SubagentStart                                       새 에이전트: 작업 폴더의 프로젝트와 '[기억] 은 장기 기억' 한 줄
  Stop, PreCompact, SessionEnd                        쉬는 순간: 새로 쌓인 대화록 구간이 두드러지면 깨어 있는 중 재생(replay.py awake)을
                                                      백그라운드로 띄운다 - 해마가 몇 분 안에 새기고, 그 뒤 모든 세션에서 떠오른다
명령행: thalamus.py probe --cwd <경로> --event <read|edit|bash|error|orient> -- <경로 또는 글>
        thalamus.py scope <경로>   → '루트<TAB>슬러그<TAB>스택' (등록 안 된 곳이면 빈 출력)
원칙: 걸린 게 없으면 출력 없음. 같은 기억은 세션에 한 번. 명령하지 않고 사실과 출처만(명령형 훅 문구는 모델이
      프롬프트 주입으로 의심한다). 어떤 오류도 조용히 통과(exit 0).
근거(2026-09-29, 과거 대화록 431세션 재생 + Sonnet 판정 371건): 파일 열람 방해 0~3%, 편집 8~20%, 명령이 다루는 파일 10%.
      요청 글(방해 64%), '안 된다' 결론(75%), CLI 이름(64%)은 글자 일치로 의도를 못 알아봐 떠올리지 않는다.
      세션당 주입 평균 약 2,000자(상한 SESSION_CHARS). 모델은 CLAUDE.md 의 한 줄('[기억] 은 너의 장기 기억')이 있어야
      이 문구를 믿고 쓴다 - 없으면 출처 불명 삽입으로 보고 무시했다(같은 날 실측).
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
CX = os.path.join(BRAIN, 'cortex')
ACTIVE = os.path.join(BRAIN, '.active')
STATE_DIR = os.path.join(ACTIVE, 'recall')
LOG = os.path.join(ACTIVE, 'recall.log')

# ---- 조정값 ----
MAX_ITEMS = {'read': 2, 'edit': 2, 'bash': 1, 'error': 2}
ITEM_CHARS = 240          # 항목 하나의 글자 상한
DF_MAX = 3                # 단서가 가리키는 서로 다른 기억이 이보다 많으면 흔한 단서 - 파일 이름에 그 단서가 든 기억만 남긴다
SHORT_ID = 6              # 이보다 짧은 단서는 낱말 경계 일치나 파일 이름 일치만 인정
HEAD_CHARS = 160          # 단서가 인덱스 줄의 이 앞부분이나 첫 링크 글에 있어야 그 기억의 주제로 본다(뒤쪽 키워드 나열은 곁가지)
SESSION_CAP = 40          # 세션에 떠올릴 기억 수 상한
SESSION_CHARS = 9000      # 세션에 주입할 글자 상한(약 3천 토큰, 깨어남 지도 제외)
BASH_ITEMS = 8            # 명령 떠올림이 세션에 쓸 수 있는 항목 수 - 조사 명령이 많아 상한이 없으면 예산을 다 먹는다
SUB_CHARS = 3000          # 서브에이전트 하나에 주입할 글자 상한 - 서브는 좁은 일을 짧게 한다(과거 서브 352개 재생: 서브당 평균 899자)
SUB_BASH = 3              # 서브에이전트 하나의 명령 떠올림 항목 상한
TREE_SUB_CHARS = 12000    # 한 세션의 서브에이전트 전부를 합친 글자 상한 - Workflow 가 에이전트를 많이 띄워도 비용이 묶인다
SUB_OFF = frozenset(('Explore', 'claude-code-guide', 'statusline-setup'))   # 위치 찾기,안내 전용 에이전트 - 기억이 결과를 바꾸지 않는다
ORIENT_NOTE = 500         # 깨어남: 프로젝트 요지 글자 상한
ORIENT_INDEX = 3000       # 깨어남: 프로젝트 INDEX 글자 상한(넘으면 줄 경계에서 자르고 전문 경로를 적는다)
ORIENT_STACK = 2000       # 깨어남: 스택 INDEX 글자 상한 - 옛 세션이 연 기억의 38% 는 색인을 타고, 55% 는 지도를 보고 찾아갔다(2026-09-29 실측)
ORIENT_COMMON = 1200      # 깨어남: 공용 INDEX 글자 상한
ORIENT_MODE = os.environ.get('BRAIN_ORIENT', 'legend')   # legend = 상한 + 지도 범례 한 줄, full = 세 지도 전문(상한 없음) - 2차 A/B 로 고른다
LEGEND = ('지도의 색인 파일(lessons-index-*, gotchas-*, patterns-*, facts*)에 과거에 확인한 함정, 결정, 구조가 모여 있다. '
          '링크는 각 지도 파일이 있는 폴더 기준이다.')
ORIENT_CARDS = 8          # 깨어남: 절차 기억(단계 카드) 줄 수 상한
AWAKE_GAP = 20 * 60       # 같은 대화록의 깨어 있는 중 재생 사이 최소 간격(초) - replay.py 와 같은 값
AWAKE_MIN_BYTES = 4000    # 지난 처리 위치 뒤 새로 쌓인 대화록이 이보다 작으면 재생을 띄우지 않는다

TMP_PREFIX = ('/tmp/', '/private/tmp/', '/var/folders/', '/private/var/folders/')
GENERIC_IDS = frozenset('fileID guid PrefabInstance MonoBehaviour RectTransform GameObject Transform SerializeField propertyPath '
                        'spriteMode Assets A_Prefab A_Prefabs A_Scripts A_Res A_Data Editor.log TextMeshProUGUI ScriptableObject '
                        'Debug.Log Debug.LogError Debug.LogWarning UnityEngine UnityEditor System.IO NullReferenceException '
                        'MissingReferenceException ArgumentException InvalidOperationException'.split())
FILE_TOKEN_RE = re.compile(r'[\w@+.-]+\.(?:cs|prefab|asset|unity|mat|shader|anim|controller|uss|uxml|asmdef|json|ojn|ojm|py|sh|mjs|js|ts)\b')
HEREDOC_RE = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?[^\n]*\n.*?\n\s*\1\s*(?:\n|$)", re.S)
API_RE = re.compile(r'\b([A-Z][A-Za-z0-9_]*(?:\.[A-Z][A-Za-z0-9_]*)+)\s*[(<]')
CS_ERR_RE = re.compile(r'([\w.-]+)\.cs\(\d+,\d+\): *(?:error|warning) (CS\d{4}): *([^\n]*)')
FRAME_RE = re.compile(r'\(at (?:[\w./-]*/)?([\w-]+)\.cs:\d+\)|in [^\n]*?/([\w-]+)\.cs:\d+')
EXC_RE = re.compile(r'\b([A-Z][A-Za-z0-9_]*(?:Exception|Error))\b')
QUOTE_ID_RE = re.compile(r"'([A-Za-z_][\w.<>]*)'")
HARNESS_ERR = ("The user doesn't want to proceed", 'The tool use was rejected', '<tool_use_error>', 'Blocked:',
               'Permission for this command was denied', 'Permission to use')
LINK_RE = re.compile(r'\[([^\]]*)\]\(([^()\s]+)\)')
# 옛 n-worker 절차 문구 - 지금은 없는 도구,단계를 가리켜 모델을 헛걸음시킨다. 지도를 보일 때 이런 설명 줄은 뺀다(저장소 원문은 hippocampus 가 정리)
PROC_RE = re.compile(r'(nb-grep|nb-load|nb-gate|curator|AskUserQuestion|model-refresh|대조\(|대조 전용|\bP[0-5]\b)')

sys.path.insert(0, HERE)


# ---------------------------------------------------------------- 범위
def registry():
    """[registry 행]
    - [(루트, 슬러그, 스택, 스택 버전, 비고)]
    """
    rows = []
    try:
        with open(os.path.join(CX, 'registry.md'), encoding='utf-8') as f:
            for line in f:
                if not line.startswith('|'):
                    continue
                c = [x.strip().strip('`') for x in line.strip().strip('|').split('|')]
                if len(c) >= 3 and c[0].startswith('/'):
                    c += [''] * (5 - len(c))
                    rows.append((c[0].rstrip('/'), c[1], c[2], c[3], '|'.join(c[4:]).strip()))
    except (IOError, OSError):
        pass
    return rows


def under(root, p):
    return p == root or p.startswith(root + '/')


def scope(cwd, full=False):
    """[세션 범위]
    - (루트, 슬러그, 스택) 또는 None(등록 안 된 곳, brain 폴더 아래 = hippocampus 자신). full 이면 registry 행 전체
    """
    if not cwd:
        return None
    cwd = cwd.rstrip('/')
    if under(BRAIN, cwd) or under(os.path.realpath(BRAIN), cwd):
        return None
    best = None
    for row in registry():
        if under(row[0], cwd) and (best is None or len(row[0]) > len(best[0])):
            best = row
    if best is None:
        return None
    return best if full else best[:3]


# ---------------------------------------------------------------- 단서
def plain_word(x):
    """[흔한 낱말인가]
    - 소문자 알파벳만으로 된 한 낱말(common, manifest, plan), 엔진 공통 타입,필드(fileID, RectTransform, m_Name)는 어느 기억에나 걸려 단서가 못 된다
    """
    return (x.isalpha() and x.islower()) or x in GENERIC_IDS or (x.startswith('m_') and x[2:3].isupper())


def path_cues(path):
    """[파일 경로의 단서]
    - 파일 이름 줄기 하나. 흔한 낱말, 대문자 문서 이름(README, CLAUDE)은 뺀다
    """
    if not path:
        return []
    stem = os.path.basename(path.rstrip('/'))
    if stem.endswith('.meta'):
        stem = stem[:-5]
    stem = os.path.splitext(stem)[0]
    if len(stem) < 4 or plain_word(stem) or stem.isupper():
        return []
    return [stem]


def bash_cues(cmd, exclude=()):
    """[명령의 단서]
    - 명령이 읽거나 쓰는 파일의 줄기(head - 파일을 연 것과 같다)
    - CLI 이름, grep 패턴, heredoc 코드 같은 명령문 속 낱말은 쓰지 않는다(판정 방해 64%)
    """
    out = []
    for m in FILE_TOKEN_RE.finditer(HEREDOC_RE.sub('\n', cmd)):
        stem = os.path.splitext(os.path.basename(m.group(0)))[0]
        if len(stem) >= 4 and not plain_word(stem) and stem not in exclude and all(stem != x for x, _ in out):
            out.append((stem, 'head'))
    return out[:10]


def api_cues(new, old='', exclude=()):
    """[편집 내용, 명령문 속 코드의 단서]
    - 새로 부르는 점 표기 API(AssetDatabase.SaveAssets, UniTask.Yield)와 그 메서드 이름(SaveAssets). 원래 있던 호출은 뺀다
    - 세기 'api': 줄 머리 일치까지 인정하고, 여러 기억이 그 API 를 말하면 가장 들어맞는 하나만 고른다(부르려는 API 는 의도가 분명한 단서다)
    """
    had = set(API_RE.findall(old or ''))
    out = []

    def add(c):
        if c and c not in exclude and c not in GENERIC_IDS and all(c != x for x, _ in out):
            out.append((c, 'api'))

    for m in API_RE.finditer(new or ''):
        a = m.group(1)
        if a in had:
            continue
        add(a)
        meth = a.rsplit('.', 1)[-1]
        if len(meth) >= 6 and any(ch.isupper() for ch in meth[1:]):
            add(meth)
        if len(out) >= 8:
            break
    return out


def error_cues(text, exclude=()):
    """[에러의 단서]
    - C# 컴파일 에러: 파일 줄기(head) + 에러 코드, 인용된 식별자(strong)
    - 예외: 첫 프로젝트 프레임의 파일 줄기(head) + 예외 이름(strong, 흔한 예외 제외)
    - 하네스 차단,권한 거부, 일반 셸 실패는 단서 없음
    """
    t = text.lstrip()
    if t.startswith(HARNESS_ERR) or 'Blocked:' in t[:80]:
        return []
    out = []

    def add(c, st):
        if c and len(c) >= 4 and c not in exclude and not plain_word(c) and all(c != x for x, _ in out):
            out.append((c, st))

    for m in CS_ERR_RE.finditer(text[:6000]):
        add(m.group(1), 'head')
        add(m.group(2), 'strong')
        for q in QUOTE_ID_RE.findall(m.group(3)):
            add(q, 'strong')
    if EXC_RE.search(text[:3000]):
        for m in EXC_RE.finditer(text[:3000]):
            add(m.group(1), 'strong')
        fm = FRAME_RE.search(text[:6000])
        if fm:
            add(fm.group(1) or fm.group(2), 'head')
    return out[:8]


# ---------------------------------------------------------------- 검색
def camel_words(cue):
    """[API 이름의 낱말] AssetDatabase.SaveAssets -> [save, assets] (마지막 부분만, 3자 이상)"""
    last = cue.rsplit('.', 1)[-1]
    return [w.lower() for w in re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])', last) if len(w) >= 3]


def slug_has(slug, ncue):
    """[파일 이름이 단서를 낱말 단위로 품는가]
    - eval-file-newtonsoft 는 eval_file 을 품고, headless-browser 는 head 를 품지 않는다
    """
    toks = [t for t in slug.lower().replace('_', '-').split('-') if t]
    for i in range(len(toks)):
        acc = ''
        for j in range(i, len(toks)):
            acc += toks[j]
            if acc == ncue:
                return True
            if len(acc) >= len(ncue):
                break
    return False


class Mem(object):
    """한 번의 훅 호출 동안의 기억 저장소 읽기(검색 엔진 nbsearch 를 쓴다)"""

    def __init__(self, slug, stack):
        import nbsearch
        self.ns = nbsearch
        self.ctx = nbsearch.Ctx(CX, slug, stack)

    def by_id(self, cue, strong_only=False, top1=False):
        """[단서 하나]
        - [(기억 경로, 순위, 점수, 줄)] 순위 0 그대로, 1 별칭, 2 정규화
        - strong_only 면 기억 파일 이름이나 첫 링크 글에 단서가 있을 때만. 흔한 단서는 파일 이름 일치만
        """
        hits = [h for h in self.ns.find_hits(self.ctx, cue) if h.tier <= 2 and h.body is not None
                and not self.ctx.is_index_like(h.body) and os.path.isfile(h.body)]
        if not hits:
            return []
        ncue = self.ns.norm(cue)
        out = []
        for h in hits:
            line = h.line
            s, e = h.s, h.e
            wb = (s <= 0 or not self.ns.is_word(line[s - 1])) and (e >= len(line) or not self.ns.is_word(line[e]))
            slug_hit = bool(h.slug) and len(ncue) >= 3 and slug_has(h.slug, ncue)
            lk = self.ns.first_link(line)
            in_title = lk is not None and ((lk[0] >= 0 and lk[0] <= s < lk[1]) or lk[2] <= s < lk[3])
            if not (slug_hit or in_title or (s < HEAD_CHARS and not strong_only)):
                continue
            if len(cue) < SHORT_ID and not (wb or slug_hit):
                continue
            if h.tier == 2 and not (wb or slug_hit) and len(ncue) < 10:
                continue
            bonus = 3 if slug_hit else 0
            if top1 and h.slug:
                # API 이름의 낱말(SaveAssets -> save, assets)이 기억 파일 이름에 있으면 그 API 에 관한 기억일 가능성이 높다
                stoks = set(h.slug.lower().replace('_', '-').split('-'))
                bonus += sum(1 for w in camel_words(cue) if w in stoks)
            out.append((h.body, h.tier, h.score + bonus, line, slug_hit))
        if len(set(x[0] for x in out)) > DF_MAX:
            slugs = [x for x in out if x[4]]
            if slugs and len(set(x[0] for x in slugs)) <= DF_MAX:
                out = slugs
            elif top1 and out:
                out = [min(out, key=lambda x: (x[1], -x[2]))]
            else:
                return []
        return [(b, t, sc, ln) for b, t, sc, ln, _ in out]


def title_of(body):
    """[기억 본문의 제목 줄]
    - 첫 줄이 '# ' 로 시작하면 그 문장(기억의 요지 - 788개 중 787개가 이 형식, 중앙 62자). 아니면 None
    """
    try:
        with open(body, encoding='utf-8') as f:
            first = f.readline().strip()
    except (IOError, OSError, UnicodeDecodeError):
        return None
    if first.startswith('# ') and len(first) > 4:
        return first[2:].strip()
    return None


def clip(s, limit):
    if len(s) <= limit:
        return s
    cut = s.rfind(' ', 0, limit)
    if cut < limit * 0.6:
        cut = limit
    return s[:cut].rstrip(' ,;-') + '…'


def gist(line, limit=ITEM_CHARS):
    s = line.strip()
    if s[:2] in ('- ', '* '):
        s = s[2:]
    s = LINK_RE.sub(lambda m: m.group(1), s)
    s = s.replace('**', '').replace('`', '')
    return clip(s, limit)


def recall(slug, stack, kind, text, seen, path=None, root=None, new=None, old=None):
    """[떠올림 한 번]
    - 반환: (항목 [(기억 상대 경로, 요지, 단서)], 쓴 단서)
    """
    exclude = set(x for x in (root or '').split('/') if x)
    if kind in ('read', 'edit'):
        cues = [(c, 'head') for c in path_cues(path) if c not in exclude]
        if kind == 'edit' and new:
            cues += api_cues(new, old, exclude)
    elif kind == 'bash':
        cues = bash_cues(text, exclude) + api_cues(text, '', exclude)
    elif kind == 'error':
        cues = error_cues(text, exclude)
    else:
        return [], []
    if not cues and not synapses():
        return [], []
    mem = Mem(slug, stack)
    cand = {}
    for c, st in cues:
        for body, tier, sc, line in mem.by_id(c, st == 'strong', st == 'api'):
            key = (tier, -sc)
            if body not in cand or key < cand[body][0]:
                cand[body] = (key, line, c)
    if len(cand) > MAX_ITEMS.get(kind, 2):
        st = strength()
        today = time.strftime('%Y-%m-%d')
        for body in list(cand):
            last = (st.get(mem.ctx.rel(body)) or {}).get('last', '')
            if last:
                age = days_between(last, today)
                bonus = 2 if age <= 14 else (1 if age <= 45 else 0)
                key, line, cue = cand[body]
                cand[body] = ((key[0], key[1] - bonus), line, cue)
    items = []
    for body, (key, line, cue) in sorted(cand.items(), key=lambda kv: kv[1][0]):
        rel = mem.ctx.rel(body)
        if rel in seen:
            continue
        items.append((rel, gist(title_of(body) or line), cue))
        if len(items) >= MAX_ITEMS.get(kind, 2):
            break
    # 경험으로 배운 연결: 인덱스 줄 일치로는 못 찾는 개념 수준 기억을 하나까지 더한다
    syn = synapses()
    if syn:
        got = set(r for r, _, _ in items) | set(seen)
        for c in synapse_cues(kind, path, text, new):
            for rel, sup, conf in syn.get(c, []):
                bp = os.path.join(CX, rel)
                if rel in got or not os.path.isfile(bp):
                    continue
                items.append((rel, gist(title_of(bp) or rel), c.split(':', 1)[-1]))
                got.add(rel)
                break
            if len(items) > MAX_ITEMS.get(kind, 2):
                break
    return items, [c for c, _ in cues]


def strength():
    """[기억 강도] sleep 이 밤마다 집계한 {상대 경로: {shown, opened, grepped, last}}"""
    try:
        with open(os.path.join(CX, '.hippocampus', 'strength.json'), encoding='utf-8') as f:
            return json.load(f).get('memories') or {}
    except (IOError, OSError, ValueError):
        return {}


def days_between(a, b):
    try:
        import datetime
        return (datetime.date.fromisoformat(b[:10]) - datetime.date.fromisoformat(a[:10])).days
    except ValueError:
        return 9999


_SYN = None


def synapses():
    """[연결 표] synapse.py 가 밤마다 배운 {단서: [[기억, 지지도, 확신도]]}. 없으면 빈 표"""
    global _SYN
    if _SYN is None:
        try:
            with open(os.path.join(CX, '.hippocampus', 'synapses.json'), encoding='utf-8') as f:
                _SYN = json.load(f).get('cues') or {}
        except (IOError, OSError, ValueError):
            _SYN = {}
    return _SYN


def synapse_cues(kind, path, text, new):
    """[연결 표를 찾을 단서] synapse.py 의 단서 형식과 같다"""
    import synapse
    out = []
    if path:
        out += synapse.file_cues(path)
    if kind == 'bash':
        for m in FILE_TOKEN_RE.finditer(HEREDOC_RE.sub('\n', text or '')):
            out += synapse.file_cues(m.group(0))
        out += synapse.api_cues(text)
    if kind == 'edit' and new:
        out += synapse.api_cues(new)
    if kind == 'error':
        out += synapse.err_cues(text)
    return out


def render(items):
    cues = []
    for _, _, c in items:
        if c not in cues:
            cues.append(c)
    head = '[기억] %s 에 대해 기억나는 것(과거에 확인한 사실이라 지금 코드와 다를 수 있다). 기억 저장소: %s' % (
        ', '.join('`%s`' % c for c in cues[:4]), CX)
    return '\n'.join([head] + ['- %s (%s)' % (g, rel) for rel, g, _ in items])


# ---------------------------------------------------------------- 깨어남
def _read(p):
    try:
        with open(p, encoding='utf-8') as f:
            return f.read()
    except (IOError, OSError, UnicodeDecodeError):
        return ''


def _map(rel, limit, drop_cards=False):
    """[레이어 지도 하나]
    - INDEX 본문에서 제목 줄(#)과 빈 줄을 빼고, 단계 카드 절은 따로 보이므로 뺄 수 있다. 상한을 넘으면 줄 경계에서 자르고 전문 경로를 적는다
    """
    text = _read(os.path.join(CX, rel))
    out = []
    skip = False
    for line in text.splitlines():
        t = line.rstrip()
        if not t.strip() or t.startswith('# '):
            continue
        if t.startswith('## '):
            skip = drop_cards and 'phases/' in t or (drop_cards and '단계 카드' in t)
        if skip:
            continue
        if drop_cards and '](phases/' in t:
            continue
        if PROC_RE.search(t):
            if t.lstrip().startswith('>') or not LINK_RE.search(t):
                continue   # 절차 설명 줄
            t = re.sub(r'\s*-\s*P[0-5]\b[^\n]*$', '', t)   # 제목 줄 끝의 절차 설명만 자른다
        out.append(t)
    body = '\n'.join(out)
    if len(body) > limit:
        cut = body.rfind('\n', 0, limit)
        body = body[:cut if cut > limit // 2 else limit] + '\n(… 전문: %s)' % rel
    return body


def orient(row):
    """[깨어남 - 그 자리의 기억 지도]
    - 프로젝트 요지(registry 비고), 프로젝트,스택,공용 지도(INDEX, 레이어별 상한), 절차 기억(단계 카드) 줄
    - 링크는 각 지도 파일이 있는 폴더 기준이다
    """
    root, slug, stack, ver, note = row
    head = ('[기억] 이 폴더는 %s 프로젝트다(%s%s). [기억] 으로 시작하는 메시지는 이 프로젝트에 대한 장기 기억이다'
            '(과거에 확인한 사실, 지금 코드와 다를 수 있다). 기억 저장소: %s') % (slug, stack, (' ' + ver.split(' ')[0]) if ver else '', CX)
    out = [head]
    if note:
        out.append('- 요지: %s' % clip(re.sub(r'\s+', ' ', note.replace('**', '')), ORIENT_NOTE))
    full = ORIENT_MODE == 'full'
    out.append('- ' + LEGEND)
    pm = _map('projects/%s/INDEX.md' % slug, 10 ** 6 if full else ORIENT_INDEX, True)
    if pm:
        out += ['--- 프로젝트 기억 지도 (projects/%s/INDEX.md)' % slug, pm]
    if stack and stack not in ('-', '?'):
        sm = _map('stacks/%s/INDEX.md' % stack, 10 ** 6 if full else ORIENT_STACK, True)
        if sm:
            out += ['--- 스택 기억 지도 (stacks/%s/INDEX.md)' % stack, sm]
    cm_ = _map('common/INDEX.md', 10 ** 6 if full else ORIENT_COMMON)
    if cm_:
        out += ['--- 공용 기억 지도 (common/INDEX.md)', cm_]
    cards = []
    for lay in (('stacks', stack), ('projects', slug)):
        if not lay[1] or lay[1] in ('-', '?'):
            continue
        for line in _read(os.path.join(CX, lay[0], lay[1], 'INDEX.md')).splitlines():
            if '](phases/' in line and line.lstrip().startswith(('-', '*')):
                cards.append('%s/%s: %s' % (lay[0], lay[1], gist(line, 200)))
    if cards:
        out.append('--- 절차 기억(단계 카드 - 작업에 걸리면 그 파일을 읽는다)')
        out += ['- ' + c for c in cards[:ORIENT_CARDS]]
    return '\n'.join(out)


# ---------------------------------------------------------------- 상태, 기록
def _safe(s):
    return ''.join(c for c in s if c.isalnum() or c in '-_.')[:120] or 'x'


def state_file(sid, agent):
    return os.path.join(STATE_DIR, _safe(sid + ('.' + agent if agent else '')) + '.json')


def load_state(p):
    try:
        with open(p, encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get('seen'), list):
            return d
    except (IOError, OSError, ValueError):
        pass
    return {'seen': []}


def save_state(p, d):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = '%s.%d.tmp' % (p, os.getpid())
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, p)
    except (IOError, OSError):
        pass


def log(rec):
    try:
        os.makedirs(ACTIVE, exist_ok=True)
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    except (IOError, OSError):
        pass


def sweep_old_states():
    try:
        now = time.time()
        for n in os.listdir(STATE_DIR):
            p = os.path.join(STATE_DIR, n)
            if now - os.path.getmtime(p) > 3 * 86400:
                os.remove(p)
    except OSError:
        pass


# ---------------------------------------------------------------- 훅
def classify(d):
    """[훅 입력 → (사건 종류, 글, 경로, 새 내용, 옛 내용)]
    - 해당 없으면 사건 종류가 None
    """
    ev = d.get('hook_event_name') or ''
    tool = d.get('tool_name') or ''
    ti = d.get('tool_input') or {}
    if ev == 'PreToolUse':
        if tool == 'Bash':
            return 'bash', ti.get('command') or '', None, None, None
        p = ti.get('file_path') or ti.get('notebook_path') or ''
        new = ti.get('new_string') or ti.get('content') or ti.get('new_source') or ''
        old = ti.get('old_string') or ''
        for x in ti.get('edits') or []:
            if isinstance(x, dict):
                new += '\n' + (x.get('new_string') or '')
                old += '\n' + (x.get('old_string') or '')
        return 'edit', p, p, new[:8000], old[:8000]
    if ev == 'PostToolUse' and tool == 'Read':
        p = ti.get('file_path') or ''
        return 'read', p, p, None, None
    if ev == 'PostToolUseFailure' and tool == 'Bash' and not d.get('is_interrupt'):
        return 'error', (d.get('error') or '')[:6000], None, None, None
    return None, None, None, None, None


# 조사 습관 - 지도는 세션 시작 때 한 번이라 계획할 즈음엔 멀어지고, 모델은 필요가 안 보이면 색인을 열지 않는다(정보만으로는 부족했다).
# 그래서 요청마다 짧게 싣는다. 근거(2026-09-29 A/B 3차, 20과제 x 판정관 3): 이 문장이 있으면 계획에 반영한 정답 기억 1.42 -> 1.82
# (옛 구조 1.90 과 차이 없음, t=-0.36), 틀린 주장 0.28 -> 0.13. 그때는 시스템 프롬프트로 넣었다 - 훅 전달은 4차에서 잰다.
HABIT = ('[기억] 계획을 세우기 전에, 세션 시작 때 떠오른 기억 지도에서 이번 작업 영역의 색인(lessons-index-*, gotchas-*, patterns-*)을 열어 본다. '
         '이름을 모르는 함정은 색인에서만 발견된다.')


CONTROL_RE = re.compile(r'^/(?:brain(?::brain)?(?:\s+(?P<a>.*))?|claude-brain-(?P<b>[a-z]+)(?:\s+(?P<c>.*))?)$', re.I | re.S)
PRESETS = ('default', 'eco', 'quality')
MODELS = ('sonnet', 'opus', 'haiku')
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max', 'auto')


def _run(args, timeout=4):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return (p.stdout or p.stderr).strip()


def control(prompt):
    """[/claude-brain-<명령> 또는 /brain <명령>] - 스크립트만 돌리면 되는 명령을 훅이 바로 처리하고 결과 글을 돌려준다. 그 밖이면 None
    - 바로 처리: status(인자 없는 /brain 포함), on, off, config [프리셋], model <이름>, effort <값>, stop, sleep, results
    - None(모델이 처리): recall, remember, 모르는 명령 - 명령 파일이나 SKILL.md 가 받는다
    """
    m = CONTROL_RE.match(prompt.strip())
    if not m:
        return None
    if m.group('b') is not None:
        w = [m.group('b').lower()] + (m.group('c') or '').lower().split()
    else:
        w = (m.group('a') or '').lower().split() or ['status']
    cmd, args = w[0], w[1:]
    cfg = ['bash', os.path.join(HERE, 'config.sh')]
    ctl = ['bash', os.path.join(HERE, 'hippocampus-ctl.sh')]
    try:
        if cmd == 'status' and not args:
            return _run(['bash', os.path.join(HERE, 'status.sh')])
        if cmd in ('on', 'off') and not args:
            return _run(cfg + [cmd]) or 'brain 설정을 바꿨다'
        if cmd == 'config':
            if not args:
                return _run(cfg + ['show']) + '\n바꾸기: /claude-brain-config default | eco | quality'
            if len(args) == 1 and args[0] in PRESETS:
                return _run(cfg + ['preset', args[0]]) or 'brain 설정을 바꿨다'
            return '사용법: /claude-brain-config [default | eco | quality]'
        if cmd == 'model':
            if len(args) == 1 and args[0] in MODELS:
                return _run(cfg + ['model', args[0]]) or 'brain 설정을 바꿨다'
            return '사용법: /claude-brain-model sonnet | opus | haiku'
        if cmd == 'effort':
            if len(args) == 1 and args[0] in EFFORTS:
                return _run(cfg + ['effort', args[0]]) or 'brain 설정을 바꿨다'
            return '사용법: /claude-brain-effort low | medium | high | xhigh | max | auto'
        if cmd == 'stop' and not args:
            return _run(ctl + ['stop']) or '해마: 지금 항목이 끝나면 멈춘다'
        if cmd == 'results' and not args:
            return _run(ctl + ['results', '--brief'])
        if cmd == 'sleep' and not args:
            # 잠 주기는 몇 초를 넘길 수 있어 훅 제한 시간(5초) 안에 기다리지 않는다 - 세션과 무관한 프로세스로 띄우고 바로 돌아온다
            lg = os.path.join(CX, '.hippocampus', 'logs')
            os.makedirs(lg, exist_ok=True)
            with open(os.path.join(lg, 'sleep-manual.out'), 'a') as out:
                subprocess.Popen(['bash', os.path.join(HERE, 'sleep.sh')], stdin=subprocess.DEVNULL, stdout=out,
                                 stderr=subprocess.STDOUT, cwd=BRAIN, start_new_session=True)
            return '잠 주기를 시작했다 - 투입만 하고 곧 끝나며 처리는 해마가 뒤에서 한다. 결과: /claude-brain-status'
    except Exception as e:
        return 'brain 명령을 처리하지 못했다: %s' % e.__class__.__name__
    return None


def enabled():
    """[brain 이 켜져 있나] - /brain off 가 .active/config 에 enabled=0 을 남긴다. 파일이 없으면 켜짐"""
    try:
        with open(os.path.join(BRAIN, '.active', 'config'), encoding='utf-8') as f:
            return not any(l.strip() == 'enabled=0' for l in f)
    except OSError:
        return True


def emit(ev, text):
    print(json.dumps({'hookSpecificOutput': {'hookEventName': ev, 'additionalContext': text}}, ensure_ascii=False))


def hook():
    t0 = time.time()
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    d = json.loads(raw)
    ev = d.get('hook_event_name') or ''
    if ev == 'UserPromptSubmit':
        r = control(d.get('prompt') or '')
        if r:
            # caveman 처럼 제어 명령은 훅이 바로 처리하고 모델에는 넘기지 않는다(토큰 0). reason 은 사용자에게만 보인다
            print(json.dumps({'decision': 'block', 'reason': r}, ensure_ascii=False))
            return 0
    if not enabled():
        return 0
    sid = d.get('session_id') or ''
    agent = d.get('agent_id') or ''
    if not sid:
        return 0
    cwd0 = (d.get('cwd') or '').rstrip('/')
    if under(BRAIN, cwd0) or under(os.path.realpath(BRAIN), cwd0):
        return 0   # hippocampus 자신의 세션 - 떠올리지도, 열람으로 세지도 않는다(망각 판정이 흐려진다)
    if agent and (d.get('agent_type') or '') in SUB_OFF:
        return 0   # 위치 찾기,안내 전용 서브에이전트 - 서브 안 도구 훅에도 agent_id, agent_type 이 온다(2026-09-29 실측)
    sp = state_file(sid, agent)
    if ev == 'SessionStart':
        if (d.get('source') or '') == 'compact':
            st = load_state(sp)
            st['seen'] = []
            st['chars'] = 0
            st['bash'] = 0
            save_state(sp, st)
        sweep_old_states()
        row = scope(d.get('cwd') or '', full=True)
        if row is not None:
            text = orient(row)
            log({'t': int(t0), 'sid': sid, 'ev': 'orient', 'slug': row[1], 'chars': len(text), 'ms': int((time.time() - t0) * 1000)})
            emit(ev, text)
        return 0
    if ev == 'UserPromptSubmit':
        if agent:
            return 0
        if scope(d.get('cwd') or '') is not None:
            log({'t': int(t0), 'sid': sid, 'ev': 'habit', 'chars': len(HABIT), 'ms': int((time.time() - t0) * 1000)})
            emit(ev, HABIT)
        return 0
    if ev == 'SubagentStart':
        row = scope(d.get('cwd') or '', full=True)
        if row is not None:
            emit(ev, '[기억] 작업 폴더는 %s 프로젝트다(%s). [기억] 으로 시작하는 메시지는 이 프로젝트에 대한 장기 기억이다'
                     '(과거에 확인한 사실, 지금 코드와 다를 수 있다). 기억 저장소: %s' % (row[1], row[2], CX))
        return 0
    if ev in ('Stop', 'PreCompact', 'SessionEnd'):
        if not d.get('stop_hook_active'):
            rest(d, ev != 'Stop')
        return 0
    kind, text, path, new, old = classify(d)
    if kind is None:
        return 0
    if kind in ('read', 'edit') and path:
        rp = os.path.realpath(path)
        if under(os.path.realpath(CX), rp) or under(CX, path):
            if kind == 'read':
                log({'t': int(t0), 'sid': sid, 'ev': 'open', 'body': os.path.relpath(rp, os.path.realpath(CX))})
            return 0
        # 임시 폴더라도 등록된 프로젝트 안의 파일이면 단서로 쓴다(프로젝트를 /tmp 아래에 둔 경우 - 2026-09-30 구현 시험에서 떠올림이 0 이 된 원인)
        if (path.startswith(TMP_PREFIX) and scope(path) is None) or under(BRAIN, path):
            if kind == 'read' or not new:
                return 0
            path = None   # 작업 폴더의 eval 코드 같은 임시 파일: 파일 이름은 단서가 아니고 새로 부르는 API 만 본다
    sc = scope(d.get('cwd') or '')
    if sc is None:
        return 0
    root, slug, stack = sc
    st = load_state(sp)
    seen = st.get('seen') or []
    cap_chars, cap_bash = (SUB_CHARS, SUB_BASH) if agent else (SESSION_CHARS, BASH_ITEMS)
    if len(seen) >= SESSION_CAP or st.get('chars', 0) >= cap_chars:
        return 0
    if kind == 'bash' and st.get('bash', 0) >= cap_bash:
        return 0
    if agent:
        tree = load_state(state_file(sid, ''))
        if tree.get('sub_chars', 0) >= TREE_SUB_CHARS:
            return 0
    items, cues = recall(slug, stack, kind, text, set(seen), path, root, new, old)
    if not items:
        return 0
    out = render(items)
    st['seen'] = seen + [rel for rel, _, _ in items]
    st['chars'] = st.get('chars', 0) + len(out)
    if kind == 'bash':
        st['bash'] = st.get('bash', 0) + len(items)
    save_state(sp, st)
    if agent:
        tree = load_state(state_file(sid, ''))
        tree['sub_chars'] = tree.get('sub_chars', 0) + len(out)
        save_state(state_file(sid, ''), tree)
    log({'t': int(t0), 'sid': sid, 'ev': kind, 'cues': cues[:8], 'shown': [rel for rel, _, _ in items], 'chars': len(out),
         'ms': int((time.time() - t0) * 1000)})
    emit(ev, out)
    return 0


def rest(d, force):
    """[쉬는 순간 - 깨어 있는 중 재생 띄우기]
    - 새로 쌓인 대화록이 작거나 간격 안이면 아무것도 안 한다(턴마다 부르므로 판정만 싸게). 재생은 분리된 프로세스라 세션을 기다리게 하지 않는다
    """
    tp = d.get('transcript_path') or ''
    cwd = d.get('cwd') or ''
    if not tp or not os.path.isfile(tp) or scope(cwd) is None:
        return
    try:
        with open(os.path.join(ACTIVE, 'replay-marks.json'), encoding='utf-8') as f:
            mk = json.load(f).get(tp) or {}
    except (IOError, OSError, ValueError):
        mk = {}
    if os.path.getsize(tp) - mk.get('pos', 0) < AWAKE_MIN_BYTES:
        return
    if not force and time.time() - mk.get('t', 0) < AWAKE_GAP:
        return
    args = [sys.executable, os.path.join(HERE, 'replay.py'), 'awake', '--transcript', tp, '--cwd', cwd, '--sid', d.get('session_id') or '']
    if force:
        args.append('--force')
    os.makedirs(ACTIVE, exist_ok=True)
    with open(os.path.join(ACTIVE, 'awake.err'), 'ab') as err:
        subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err, start_new_session=True, close_fds=True)


def probe(argv):
    a = argv
    cwd = a[a.index('--cwd') + 1]
    kind = a[a.index('--event') + 1]
    text = ' '.join(a[a.index('--') + 1:]) if '--' in a else ''
    row = scope(cwd, full=True)
    if row is None:
        print('범위 밖:', cwd)
        return 0
    t0 = time.time()
    if kind == 'orient':
        o = orient(row)
        print(o)
        print('(%d자)' % len(o))
    else:
        items, cues = recall(row[1], row[2], kind, text, set(), text if kind in ('read', 'edit') else None, row[0],
                             text if kind == 'edit' else None)
        print('단서:', cues)
        print(render(items) if items else '(떠오른 기억 없음)')
    print('%.0f ms' % ((time.time() - t0) * 1000))
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'probe':
        return probe(sys.argv[2:])
    if len(sys.argv) > 2 and sys.argv[1] == 'scope':
        sc = scope(os.path.abspath(sys.argv[2]))
        if sc:
            print('\t'.join(sc))
        return 0
    try:
        return hook()
    except Exception:
        return 0


if __name__ == '__main__':
    sys.exit(main())
