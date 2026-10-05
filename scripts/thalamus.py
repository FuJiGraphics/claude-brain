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
  (성격)                                              persona/<슬러그>.json 이 있으면 SessionStart 에 작업 방식 문장, UserPromptSubmit 에
                                                      상기 한 줄, PreToolUse(AskUserQuestion 포함) 관문, Stop 검증 검사를 더한다(persona.py)
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
# 지도 범례 문구는 lang.T[언어]['legend'] 에 있다
ORIENT_CARDS = 8          # 깨어남: 절차 기억(단계 카드) 줄 수 상한
AWAKE_GAP = 20 * 60       # 같은 대화록의 깨어 있는 중 재생 사이 최소 간격(초) - replay.py 와 같은 값
AWAKE_MIN_BYTES = 4000    # 지난 처리 위치 뒤 새로 쌓인 대화록이 이보다 작으면 재생을 띄우지 않는다

TMP_PREFIX = ('/tmp/', '/private/tmp/', '/var/folders/', '/private/var/folders/')
GENERIC_IDS = frozenset('fileID guid PrefabInstance MonoBehaviour RectTransform GameObject Transform SerializeField propertyPath '
                        'spriteMode Assets A_Prefab A_Prefabs A_Scripts A_Res A_Data Editor.log TextMeshProUGUI ScriptableObject '
                        'Debug.Log Debug.LogError Debug.LogWarning UnityEngine UnityEditor System.IO NullReferenceException '
                        'MissingReferenceException ArgumentException InvalidOperationException'.split())
# 명령이 다루는 파일 - Unity 자산과 흔한 언어의 소스, 설정 파일. 문서(.md)는 너무 흔해 뺀다
CODE_EXT = (r'(?:cs|prefab|asset|unity|mat|shader|anim|controller|uss|uxml|asmdef|json|ojn|ojm|py|sh|mjs|cjs|js|ts|tsx|jsx'
            r'|vue|svelte|go|rs|java|kt|kts|swift|c|cc|cpp|h|hpp|m|mm|rb|php|dart|scala|lua|sql|gradle|toml|ya?ml)')
FILE_TOKEN_RE = re.compile(r'[\w@+.-]+\.' + CODE_EXT + r'\b')
CODE_FILE_RE = re.compile(r'\.' + CODE_EXT + r'$', re.I)
HEREDOC_RE = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?[^\n]*\n.*?\n\s*\1\s*(?:\n|$)", re.S)
API_RE = re.compile(r'\b([A-Z][A-Za-z0-9_]*(?:\.[A-Z][A-Za-z0-9_]*)+)\s*[(<]')
# 소문자로 시작하는 받는 쪽의 호출(stripe.paymentIntents.create(, self.charge_card() - JS, TS, Python 의 흔한 꼴. 쓰는 것은 낱말이 둘 이상인 부분뿐
# 받는 쪽 없이 부르는 소문자 시작 함수(chargeCard(, charge_card() 도 같다. C# 의 대문자 시작 호출은 API_RE 만 본다(전과 같다)
CALL_RE = re.compile(r'(?<![\w.$])([a-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\(')
# 어느 코드에나 나오는 내장 호출 - 단서가 못 된다
COMMON_CALLS = frozenset('setTimeout setInterval clearTimeout clearInterval requestAnimationFrame parseInt parseFloat toString '
                         'toFixed forEach indexOf lastIndexOf startsWith endsWith toLowerCase toUpperCase addEventListener '
                         'removeEventListener querySelector querySelectorAll getElementById getAttribute setAttribute '
                         'preventDefault stopPropagation appendChild removeChild createElement useState useEffect useMemo '
                         'useCallback useRef useContext hasOwnProperty isArray fromEntries getItem setItem removeItem '
                         'readFileSync writeFileSync existsSync mkdirSync join_path __init__ __name__ __main__'.split())
# 너무 흔한 파일 이름 - 소문자 한 낱말 이름 가운데 어느 프로젝트에나 있는 것. 이 밖의 한 낱말(charge, billing)은 기억 파일 이름이나 제목에 있을 때만 쓴다
GENERIC_STEMS = frozenset('index main app utils util helpers helper types type config configs constants const common models model '
                          'routes route router server client test tests spec setup init base core lib api views view controller '
                          'controllers service services store schema schemas styles style layout page component components hooks '
                          'context provider handler handlers middleware database settings urls admin apps forms serializers tasks '
                          'signals manage wsgi asgi conftest package readme license makefile dockerfile global globals logger errors '
                          'error mock mocks fixtures data default loading template templates script scripts module modules plugin '
                          'plugins options props state actions reducer reducers selectors slice slices entry bootstrap vite webpack '
                          'babel eslint jest tsconfig next nuxt'.split())
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
import lang as L  # noqa: E402  세션 문구의 언어(.active/config 의 lang=, 없으면 ko)
import plat  # noqa: E402  경로 비교, bash, 프로세스 분리(macOS, Linux, Windows)


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
                if len(c) >= 3 and plat.is_abs(c[0]):
                    c += [''] * (5 - len(c))
                    rows.append((plat.norm(c[0]), c[1], c[2], c[3], '|'.join(c[4:]).strip()))
    except (IOError, OSError):
        pass
    return rows


def _wintmp():
    import tempfile
    return tempfile.gettempdir()


def under(root, p):
    return plat.under(root, p)   # Windows 는 C:\, C:/, /c/ 표기와 대소문자를 맞춰 비교한다


def scope(cwd, full=False):
    """[세션 범위]
    - (루트, 슬러그, 스택) 또는 None(등록 안 된 곳, brain 폴더 아래 = hippocampus 자신). full 이면 registry 행 전체
    """
    if not cwd:
        return None
    cwd = plat.norm(cwd)
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
    """[파일 경로의 단서] [(단서, 세기)]
    - 파일 이름 줄기 하나. 대문자 문서 이름(README, CLAUDE)과 짧은 이름은 뺀다
    - 소문자 한 낱말(charge.ts, billing.py)은 'plain' - JS, TS, Python 은 파일 이름이 대개 이 꼴이라 빼 버리면 파일로 떠올리는 길이 막힌다.
      영어 낱말이라 우연히 겹치기 쉬워(render.ts 와 frame-render) 소스, 설정 파일만, index, utils 같은 흔한 이름은 빼고, Mem.by_id 에서 더 좁힌다
    - 그때 확장자까지 붙은 이름(charge.ts)도 'file' 로 - 인덱스 줄 머리에 파일 이름을 그대로 적은 기억은 그 파일에 관한 것이다.
      제목이 한국어, 일본어, 중국어인 뇌에서는 제목에 영어 낱말이 없어 'plain' 만으로는 거의 안 걸린다
    """
    if not path:
        return []
    name = os.path.basename(path.rstrip('/'))
    if name.endswith('.meta'):
        name = name[:-5]
    stem = os.path.splitext(name)[0]
    if len(stem) < 4 or stem.isupper():
        return []
    if plain_word(stem):
        ok = CODE_FILE_RE.search(name) and stem not in GENERIC_STEMS and stem not in GENERIC_IDS
        return [(stem, 'plain'), (name, 'file')] if ok else []
    return [(stem, 'head')]


def bash_cues(cmd, exclude=()):
    """[명령의 단서]
    - 명령이 읽거나 쓰는 파일의 줄기(head - 파일을 연 것과 같다)
    - CLI 이름, grep 패턴, heredoc 코드 같은 명령문 속 낱말은 쓰지 않는다(판정 방해 64%)
    """
    out = []
    for m in FILE_TOKEN_RE.finditer(HEREDOC_RE.sub('\n', cmd)):
        stem = os.path.splitext(os.path.basename(m.group(0)))[0]
        # 소문자 한 낱말(check.sh, capture.py)은 쓰지 않는다 - 조사, 검증 스크립트 이름이라 실제 세션 재생에서 엉뚱한 기억을 끌어오고 맞던 것을 밀어냈다
        if len(stem) >= 4 and not plain_word(stem) and stem not in exclude and all(stem != x for x, _ in out):
            out.append((stem, 'head'))
    return out[:10]


def api_cues(new, old='', exclude=(), calls=True):
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
    # 소문자로 시작하는 호출(JS, TS, Python): 낱말이 둘 이상인 이름(paymentIntents, chargeCard, charge_card)만 - create, get, log 같은 한 낱말은 어디에나 있다.
    # 편집에만 쓴다 - 명령의 heredoc 속 조사 코드는 의도가 아니다(명령문 속 낱말은 판정 방해 64%)
    had2 = set(CALL_RE.findall(old or '')) if calls else ()
    for m in (CALL_RE.finditer(new or '') if calls else ()):
        if len(out) >= 8:
            break
        if m.group(1) in had2:
            continue
        parts = m.group(1).split('.')
        if any(x[:1].isupper() for x in parts):
            continue   # 대문자 부분이 낀 사슬(button.onClick.AddListener)은 C# 꼴 - API_RE 만 본다
        for part in parts[1:] if len(parts) > 1 else parts:
            p = part.strip('_$')
            if len(p) >= 6 and p[0].islower() and p not in COMMON_CALLS and (any(ch.isupper() for ch in p[1:]) or '_' in p):
                add(p)
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

    def by_id(self, cue, strong_only=False, top1=False, plain=False):
        """[단서 하나]
        - [(기억 경로, 순위, 점수, 줄)] 순위 0 그대로, 1 별칭, 2 정규화
        - strong_only 면 기억 파일 이름이나 첫 링크 글에 단서가 있을 때만. 흔한 단서는 파일 이름 일치만
        - plain(소문자 한 낱말 파일 이름과 그 확장자 붙은 이름): 낱말 단위 일치만, 공용 층 기억은 빼고 프로젝트, 스택 기억만.
          진짜 사용자 뇌 5개 프로젝트에서 공용 층 일치는 거의 우연이었다(protocol.ts -> collaboration-protocol 같은 것)
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
            if plain and (not (wb or slug_hit) or self.ctx.rel(h.body).startswith('common/')):
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
        cues = [(c, st) for c, st in path_cues(path) if c not in exclude]
        if kind == 'edit' and new:
            cues += api_cues(new, old, exclude)
    elif kind == 'bash':
        cues = bash_cues(text, exclude) + api_cues(text, '', exclude, calls=False)
    elif kind == 'error':
        cues = error_cues(text, exclude)
    else:
        return [], []
    if not cues and not synapses():
        return [], []
    mem = Mem(slug, stack)
    cand = {}
    for c, st in cues:
        for body, tier, sc, line in mem.by_id(c, st in ('strong', 'plain'), st == 'api', st in ('plain', 'file')):
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
    head = L.t('recall') % (', '.join('`%s`' % c for c in cues[:4]), CX)
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
        body = body[:cut if cut > limit // 2 else limit] + '\n' + L.t('full') % rel
    return body


def orient(row):
    """[깨어남 - 그 자리의 기억 지도]
    - 프로젝트 요지(registry 비고), 프로젝트,스택,공용 지도(INDEX, 레이어별 상한), 절차 기억(단계 카드) 줄
    - 링크는 각 지도 파일이 있는 폴더 기준이다
    """
    root, slug, stack, ver, note = row
    head = L.t('orient') % (slug, stack + ((' ' + ver.split(' ')[0]) if ver else ''), CX)
    out = [head]
    if note:
        out.append(L.t('note') % clip(re.sub(r'\s+', ' ', note.replace('**', '')), ORIENT_NOTE))
    full = ORIENT_MODE == 'full'
    out.append('- ' + L.t('legend'))
    pm = _map('projects/%s/INDEX.md' % slug, 10 ** 6 if full else ORIENT_INDEX, True)
    if pm:
        out += [L.t('map_project') % ('projects/%s/INDEX.md' % slug), pm]
    if stack and stack not in ('-', '?'):
        sm = _map('stacks/%s/INDEX.md' % stack, 10 ** 6 if full else ORIENT_STACK, True)
        if sm:
            out += [L.t('map_stack') % ('stacks/%s/INDEX.md' % stack), sm]
    cm_ = _map('common/INDEX.md', 10 ** 6 if full else ORIENT_COMMON)
    if cm_:
        out += [L.t('map_common') % 'common/INDEX.md', cm_]
    cards = []
    for lay in (('stacks', stack), ('projects', slug)):
        if not lay[1] or lay[1] in ('-', '?'):
            continue
        for line in _read(os.path.join(CX, lay[0], lay[1], 'INDEX.md')).splitlines():
            if '](phases/' in line and line.lstrip().startswith(('-', '*')):
                cards.append('%s/%s: %s' % (lay[0], lay[1], gist(line, 200)))
    if cards:
        out.append(L.t('cards'))
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
# 문구는 lang.T[언어]['habit'] 에 있다(언어별)


CONTROL_RE = re.compile(r'^/(?:brain(?::brain)?(?:\s+(?P<a>.*))?|claude-brain-(?P<b>[a-z]+)(?:\s+(?P<c>.*))?)$', re.I | re.S)
PRESETS = ('default', 'eco', 'quality')
MODELS = ('sonnet', 'opus', 'haiku')
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max', 'auto')


def _run(args, timeout=4):
    args = plat.argv(args)
    # 자식 출력은 UTF-8 이다 - Windows 의 시스템 코드 페이지로 풀면 한글, 일본어가 깨진다
    p = subprocess.run(args, capture_output=True, timeout=timeout, env=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8'))
    return (p.stdout or p.stderr).decode('utf-8', 'replace').strip()


def control(prompt, cwd=''):
    """[/claude-brain-<명령> 또는 /brain <명령>] - 스크립트만 돌리면 되는 명령을 훅이 바로 처리하고 결과 글을 돌려준다. 그 밖이면 None
    - 바로 처리: status(인자 없는 /brain 포함), on, off, on here, off here, register, config [프리셋 | lang <언어>], model <이름>, effort <값>,
      stop, sleep, results, app(옛 이름 editor). cwd 는 훅 입력의 작업 폴더(here, register 가 쓴다)
    - None(모델이 처리): recall, remember, 모르는 명령 - 명령 파일이나 SKILL.md 가 받는다
    """
    mt = CONTROL_RE.match(prompt.strip())
    if not mt:
        return None
    if mt.group('b') is not None:
        w = [mt.group('b').lower()] + (mt.group('c') or '').lower().split()
    else:
        w = (mt.group('a') or '').lower().split() or ['status']
    cmd, args = w[0], w[1:]
    from cli_i18n import m   # 사람이 읽는 결과 글 - brain 언어로
    sh = 'bash'   # _run 과 plat.argv 가 Git Bash 와 / 경로로 바꾼다
    cfg = [sh, os.path.join(HERE, 'config.sh')]
    ctl = [sh, os.path.join(HERE, 'hippocampus-ctl.sh')]
    try:
        if cmd == 'status' and not args:
            return _run([sh, os.path.join(HERE, 'status.sh')])
        if cmd in ('on', 'off') and not args:
            return _run(cfg + [cmd]) or m('ctl.changed')
        if cmd in ('on', 'off') and args == ['here']:
            # 이 프로젝트만 쉬기/깨우기 - 전체 켜짐과 따로 .active/config 의 mute= 에 슬러그를 넣고 뺀다
            sc = scope(cwd)
            if not sc:
                return m('mu.none')
            _run(cfg + ['mute' if cmd == 'off' else 'unmute', sc[1]])
            return m('mu.off' if cmd == 'off' else 'mu.on', sc[1])
        if cmd == 'register' and not args:
            # 지금 등록 - 위로 가장 가까운 git 루트를 해마에게 맡긴다(밤의 자동 등록 조건을 기다리지 않는다)
            out = _run([sys.executable, os.path.join(HERE, 'register.py'), cwd or os.getcwd()], timeout=4)
            return out or m('rg.fail', '-')
        if cmd == 'config':
            if not args:
                return _run(cfg + ['show']) + '\n' + m('ctl.change')
            if len(args) == 1 and args[0] in PRESETS:
                return _run(cfg + ['preset', args[0]]) or m('ctl.changed')
            if len(args) == 2 and args[0] == 'lang' and args[1] in L.LANGS:
                return _run(cfg + ['lang', args[1]]) or m('ctl.changed')
            return m('ctl.usage', '/claude-brain-config [default | eco | quality | lang <ko|en|ja|zh>]')
        if cmd == 'model':
            if len(args) == 1 and args[0] in MODELS:
                return _run(cfg + ['model', args[0]]) or m('ctl.changed')
            return m('ctl.usage', '/claude-brain-model sonnet | opus | haiku')
        if cmd == 'effort':
            if len(args) == 1 and args[0] in EFFORTS:
                return _run(cfg + ['effort', args[0]]) or m('ctl.changed')
            return m('ctl.usage', '/claude-brain-effort low | medium | high | xhigh | max | auto')
        if cmd == 'stop' and not args:
            return _run(ctl + ['stop']) or m('hc.stop')
        if cmd in ('app', 'editor') and not args:
            # 서버는 세션과 무관한 프로세스로 뜨고 editor.sh 는 주소만 알리고 바로 끝난다(훅 제한 5초)
            return _run([sh, os.path.join(HERE, 'editor.sh')], timeout=4) or m('ctl.app_fail', plat.norm(os.path.join(HERE, 'editor.sh')))
        if cmd == 'results' and not args:
            return _run(ctl + ['results', '--brief'])
        if cmd == 'sleep' and not args:
            # 잠 주기는 몇 초를 넘길 수 있어 훅 제한 시간(5초) 안에 기다리지 않는다 - 세션과 무관한 프로세스로 띄우고 바로 돌아온다
            lg = os.path.join(CX, '.hippocampus', 'logs')
            os.makedirs(lg, exist_ok=True)
            with open(os.path.join(lg, 'sleep-manual.out'), 'a') as out:
                subprocess.Popen(plat.argv([sh, os.path.join(HERE, 'sleep.sh')]), stdin=subprocess.DEVNULL, stdout=out,
                                 stderr=subprocess.STDOUT, cwd=BRAIN, **plat.detach_kw())
            return m('ctl.sleep')
    except Exception as e:
        return m('ctl.error', e.__class__.__name__)
    return None


def enabled():
    """[brain 이 켜져 있나] - /brain off 가 .active/config 에 enabled=0 을 남긴다. 파일이 없으면 켜짐"""
    try:
        with open(os.path.join(BRAIN, '.active', 'config'), encoding='utf-8', errors='replace') as f:
            return not any(l.strip() == 'enabled=0' for l in f)
    except (OSError, ValueError):   # 깨진 설정 파일이면 켜진 것으로 본다(말없이 꺼지지 않게)
        return True


def muted():
    """[쉬는 프로젝트 슬러그] .active/config 의 mute=a,b - /claude-brain-off here 가 남긴다. 그 프로젝트에선 떠올림, 성격, 습관 줄이 모두 쉰다"""
    try:
        with open(os.path.join(BRAIN, '.active', 'config'), encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.startswith('mute='):
                    return {x for x in line.strip()[5:].split(',') if x}
    except (OSError, ValueError):
        pass
    return set()


_GATE = {}   # PreToolUse 관문 결정(성격) - emit 이 떠올림과 함께 싣고, 떠올림이 없으면 main 이 따로 낸다


def emit(ev, text):
    o = {'hookEventName': ev, 'additionalContext': text}
    if _GATE:
        o.update(_GATE)
        _GATE.clear()
    print(json.dumps({'hookSpecificOutput': o}, ensure_ascii=False))


# ---------------------------------------------------------------- 성격 (persona.py)
def persona_of(slug):
    """[그 프로젝트의 성격 컴파일 결과] 없거나 꺼졌거나 읽기 오류면 None - 성격은 떠올림을 막지 않는다"""
    try:
        import persona
        return persona.compiled(slug)
    except Exception:
        return None


def gate(d, sid, agent):
    """[성격 관문 - PreToolUse]
    - 위험 명령(risky_ask), 요청의 첫 수정(first_edit_ask), 큰 변경(big_change_ask)은 사용자 확인(ask), 자율 3(deny_ask)은 질문 도구를 막는다
    - 신중 2(plan_first)는 요청의 첫 코드 수정을 한 번 막고(deny) 계획을 먼저 보이게 한다 - 사용자에게는 묻지 않는다
    - 코드 수정과 검증 명령을 세션 상태(pt)에 적는다 - Stop 검증 검사(verify_block)가 읽는다. 서브에이전트의 수정,검증도 메인 상태에 센다
    """
    sc = scope(d.get('cwd') or '')
    if sc is None:
        return
    pc = persona_of(sc[1])
    if not pc or not pc['gates']:
        return
    import persona
    g = pc['gates']
    tool = d.get('tool_name') or ''
    ti = d.get('tool_input') or {}
    if tool == 'AskUserQuestion':
        if g.get('deny_ask') and not agent:
            _GATE.update(permissionDecision='deny', permissionDecisionReason=L.t('gate_ask_deny'))
        return
    mp = state_file(sid, '')
    if tool == 'Bash':
        cmd = ti.get('command') or ''
        if g.get('verify_stop') and persona.is_verify(cmd, g.get('verify_re')):
            st = load_state(mp)
            st.setdefault('pt', {})['dirty'] = False
            save_state(mp, st)
        if g.get('risky_ask') and persona.is_risky(cmd):
            _GATE.update(permissionDecision='ask', permissionDecisionReason=L.t('gate_risky'))
        return
    p = ti.get('file_path') or ti.get('notebook_path') or ''
    if not persona.is_code(p) or p.startswith(TMP_PREFIX) or under(BRAIN, p):
        return
    st = load_state(mp)
    pt = st.setdefault('pt', {})
    if g.get('plan_first') and not agent and not pt.get('planned'):
        # 신중 2: 요청의 첫 코드 수정을 한 번 되돌려 계획을 먼저 보이게 한다. 수정은 일어나지 않았으니 파일, 검증 상태에는 세지 않는다
        pt['planned'] = True
        save_state(mp, st)
        _GATE.update(permissionDecision='deny', permissionDecisionReason=L.t('gate_plan'))
        return
    files = pt.setdefault('files', [])
    if p not in files:
        files.append(p)
    pt['dirty'] = True
    if not agent:
        if g.get('first_edit_ask') and not pt.get('asked_first'):
            pt['asked_first'] = True
            _GATE.update(permissionDecision='ask', permissionDecisionReason=L.t('gate_first'))
        elif g.get('big_change_ask') and len(files) > g['big_change_ask'] and not pt.get('asked_big'):
            pt['asked_big'] = True
            _GATE.update(permissionDecision='ask', permissionDecisionReason=L.t('gate_big') % g['big_change_ask'])
    save_state(mp, st)


def verify_block(d, sid):
    """[성격 검증 검사 - Stop] 꼼꼼 3: 이번 요청에서 코드를 고친 뒤 검증 명령이 없으면 한 번 되돌려 보낸다. 되돌릴 이유 글 또는 None"""
    sc = scope(d.get('cwd') or '')
    if sc is None:
        return None
    pc = persona_of(sc[1])
    if not pc or not pc['gates'].get('verify_stop'):
        return None
    mp = state_file(sid, '')
    st = load_state(mp)
    pt = st.get('pt') or {}
    if not pt.get('dirty') or pt.get('stop_blocked'):
        return None
    pt['stop_blocked'] = True
    st['pt'] = pt
    save_state(mp, st)
    return L.t('gate_verify') % len(pt.get('files') or [])


def hook():
    t0 = time.time()
    raw = sys.stdin.buffer.read().decode('utf-8', 'replace')   # Windows 의 시스템 코드 페이지로 읽으면 한글 요청이 깨진다
    if not raw.strip():
        return 0
    d = json.loads(raw)
    ev = d.get('hook_event_name') or ''
    if ev == 'UserPromptSubmit':
        r = control(d.get('prompt') or '', d.get('cwd') or '')
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
    cwd0 = plat.norm(d.get('cwd') or '')
    if under(BRAIN, cwd0) or under(os.path.realpath(BRAIN), cwd0):
        return 0   # hippocampus 자신의 세션 - 떠올리지도, 열람으로 세지도 않는다(망각 판정이 흐려진다)
    q = muted()
    if q:
        sc0 = scope(cwd0)
        if sc0 and sc0[1] in q:
            return 0   # 이 프로젝트는 쉬는 중(/claude-brain-off here)
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
            pc = persona_of(row[1])
            if pc and pc['session']:
                text += '\n' + pc['session']
            log({'t': int(t0), 'sid': sid, 'ev': 'orient', 'slug': row[1], 'chars': len(text), 'ms': int((time.time() - t0) * 1000)})
            emit(ev, text)
        return 0
    if ev == 'UserPromptSubmit':
        if agent:
            return 0
        sc = scope(d.get('cwd') or '')
        if sc is not None:
            text = L.t('habit')
            pc = persona_of(sc[1])
            if pc:
                st = load_state(sp)
                st['pt'] = {}   # 요청마다 관문 상태(수정한 파일, 검증 여부, 이미 물었는지)를 새로 센다
                save_state(sp, st)
                if pc['turn']:
                    text += '\n' + pc['turn']
            log({'t': int(t0), 'sid': sid, 'ev': 'habit', 'chars': len(text), 'ms': int((time.time() - t0) * 1000)})
            emit(ev, text)
        return 0
    if ev == 'SubagentStart':
        row = scope(d.get('cwd') or '', full=True)
        if row is not None:
            emit(ev, L.t('sub') % (row[1], row[2], CX))
        return 0
    if ev in ('Stop', 'PreCompact', 'SessionEnd'):
        if not d.get('stop_hook_active'):
            blk = verify_block(d, sid) if ev == 'Stop' else None
            rest(d, ev != 'Stop')
            if blk:
                print(json.dumps({'decision': 'block', 'reason': blk}, ensure_ascii=False))
        return 0
    if ev == 'PreToolUse':
        gate(d, sid, agent)
        if (d.get('tool_name') or '') == 'AskUserQuestion':
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
        if ((path.startswith(TMP_PREFIX) or (plat.WIN and under(_wintmp(), path))) and scope(path) is None) or under(BRAIN, path):
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
        subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err, **plat.detach_kw())


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


def _utf8_out():
    """[표준 출력을 UTF-8 로] Windows 는 파이프 출력이 시스템 코드 페이지(cp1252, cp949 등)라 한글, 일본어를 쓰다 오류가 나거나 깨진다"""
    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            pass


def main():
    _utf8_out()
    if len(sys.argv) > 1 and sys.argv[1] == 'probe':
        return probe(sys.argv[2:])
    if len(sys.argv) > 2 and sys.argv[1] == 'scope':
        sc = scope(os.path.abspath(sys.argv[2]))
        if sc:
            print('\t'.join(sc))
        return 0
    try:
        r = hook()
    except Exception:
        r = 0
    if _GATE:
        print(json.dumps({'hookSpecificOutput': dict(_GATE, hookEventName='PreToolUse')}, ensure_ascii=False))
    return r


if __name__ == '__main__':
    sys.exit(main())
