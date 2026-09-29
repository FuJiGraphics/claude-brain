#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 검색 엔진 - thalamus(자동 떠올림)와 recall.sh(의식적 떠올리기)가 함께 쓴다.

recall.sh 가 범위(슬러그, 스택)를 정한 뒤 이 파일을 한 번 실행해 모든 이름을 한꺼번에 처리한다.
  nbsearch.py --nb <노트북> --slug <슬러그> --stack <스택> --log <checks.log> --bodies <.bodies>
              [--cache-dir <폴더>] [--commit-flag <파일>] -- <이름>...
종료 코드: 0 성공, 2 인자 오류, 3 기록 전에 실패(nb-grep.sh 가 현행 bash 루프로 대신한다).
--commit-flag: 대조 기록을 쓰기 직전에 만들고 성공하면 지운다. 실패했을 때 이 파일이 없으면 아무것도 기록하지 않은 것이라
               nb-grep.sh 가 안전하게 다른 python 이나 bash 루프로 넘어간다(인터프리터가 아예 안 뜬 경우도 같다).
벤치마크용 함수: run(nb_root, slug, stack, names, bodies_seen) -> (출력 문자열, per)
python 3.7 호환을 지킨다(_lib.sh 의 nw_find_python 하한). 조정값의 근거는 REPORT.md.

이름마다 검색 순서
  1. 인덱스 줄(레이어 루트의 INDEX.md, *index*.md): 1순위 그대로(대소문자 무시) > 별칭 > 정규화 > 다단어
  2. 1순위나 별칭 히트가 있으면 링크 밖 본문 언급을 한 줄로 덧붙인다
  3. 1순위나 별칭 히트가 없으면 본문 대체 검색(이름 그대로), 그것도 없으면 여러 단어 이름에 한해 단어 일부 일치
속도: 거르기는 UTF-8 바이트(소문자,정규화 사본)로 하고 맞은 줄만 문자열로 푼다. re,glob 는 기동 비용 때문에 쓰지 않는다.
"""
import math
import os
import sys
import time
from bisect import bisect_right

# ---- 조정값 (근거는 REPORT.md 의 조정 절) ----
LINE_MAX = 300          # 히트 줄이 이보다 길면 첫 링크 + 일치 앞뒤 창으로 줄인다
HEAD_LINK_MAX = 160     # 첫 링크가 이 위치 안에서 끝나면 줄 머리부터 링크까지 보여 준다
WIN = 70                # 일치 앞뒤 창
SNAP = 12               # 창 끝을 이 글자 수 안의 단어 경계로 맞춘다
TOP_HITS = 6            # '히트:' 형식으로 자세히 보여 줄 히트 수
EXTRA_HITS = 15         # 그 뒤 '추가 히트:' 한 줄 형식 수, 나머지는 건수만
DEDUP_BODY = True       # 이미 '히트:' 로 보인 본문을 다시 가리키는 히트는 '추가 히트' 로 내린다
BODY_TOP = 1            # 본문을 여는 상위 본문 수
BODY_FULL_LINES = 25    # 이 줄 수 이하이고
BODY_FULL_CHARS = 2000  # 이 글자 수 이하면 전문
BODY_MODE = 'title'     # 길면 'title' = 제목 줄 + 이름이 나온 줄(없으면 머리), 'head' = 머리 몇 줄(명세 원안)
BODY_HEAD_LINES = 8     # 머리 줄 수 상한
BODY_HEAD_CHARS = 1000  # 머리 합계 글자 상한
BODY_MATCH_LINES = 2    # 이름이 나온 줄을 몇 개 보여 주나
MATCH_LINE_MAX = 200    # 그 줄 하나의 글자 상한
BODY_TIER_MAX = 2       # 이 순위(0 그대로, 1 별칭, 2 정규화, 3 다단어) 이하의 히트만 본문을 연다(다단어 일치는 엉뚱한 줄이 많다)
SLUG_BONUS = 3          # 정규화한 이름이 링크 슬러그(파일명)에 들어 있으면 가산
TF_BONUS = 1            # 링크 본문에 이름이 나온 횟수 log2(1+n) (최대 3) 의 배수만큼 가산
CAND_TOP = 5            # 본문 대체 검색 후보 파일 수
CAND_WIN = 70           # 후보 줄의 일치 앞뒤 창
MENTION_TOP = 3         # 1순위나 별칭 히트가 있을 때 링크 밖 본문 언급을 한 줄에 몇 개까지 적나(0 = 끔)
FALLBACK_ON_WEAK = True # 1순위나 별칭 히트가 없으면 정규화,다단어 히트가 있어도 본문 대체 검색을 한다
FUZZY_TOP = 3           # 아무것도 못 찾은 여러 단어 이름에 단어 일부 일치 인덱스 줄을 몇 개 보이나(0 = 끔)
FUZZY_BODY_TOP = 2      # 같은 조건에서 단어 일부가 겹치는 본문(BM25)을 몇 개 보이나(0 = 끔)
FUZZY_MIN_RATIO = 0.5   # 단어 일부 일치로 칠 최소 비율(최소 2단어)
FUZZY_COMPACT = True    # 연관 후보를 한 줄로(링크된 본문 경로 + 일치 앞뒤 창), False 면 히트처럼 두 줄
FUZZY_WIN = 60          # 한 줄 연관 후보의 일치 앞뒤 창
FUZZY_BODY_SCOPE = 'linked'  # 'linked' = 단어가 나온 인덱스 줄이 가리키는 본문만 채점, 'all' = 본문 전부를 단어마다 훑는다
BM25_K1 = 1.2
BM25_B = 0.75
TITLE_BOOST = 1.0       # 제목 줄(첫 줄)에 나온 단어의 추가 가중(idf 배수)
NORM_MIN = 3            # 정규화 일치를 쓸 최소 길이(정규화 뒤)
WORD_MIN = 2            # 여러 단어 이름에서 단어로 치는 최소 길이(한글 외)
WORD_MIN_HANGUL = 1     # 한글 단어의 최소 길이('씬', '탭' 같은 한 글자 명사를 쓰고, 기능어는 STOP_1 로 뺀다)
STOP_1 = frozenset('후 안 못 중 전 때 및 등 것 수 더 잘 또 좀 곧 각 몇 새 첫 한 두 세 네 온 이 그 저 뒤 앞 위 속 밖 간'.split())
HANGUL_END = tuple(sorted(set((
    '으로', '에서', '에게', '까지', '부터', '처럼', '보다', '하고', '하면', '해서', '했다', '한다', '된다', '이다', '였다',
    '됨', '함', '임', '음', '짐', '림', '김', '기', '게', '이', '가', '을', '를', '은', '는', '의', '에', '로', '과', '와',
    '도', '만', '고', '며', '서', '다', '요', '지')), key=lambda e: -len(e)))

SEP_CHARS = frozenset(' \t,;`|()[]')   # 창 끝을 맞출 단어 경계
# 정규화 일치에서 지우는 글자: 공백류(ASCII),_,-,.,/ (줄바꿈은 남겨 줄 번호를 유지한다)
SEP_ASCII = ' \t\r\x0b\x0c_-./'
SEP_SET = frozenset(SEP_ASCII)
NORM_TABLE = str.maketrans('', '', SEP_ASCII)
SEP_ASCII_B = SEP_ASCII.encode('ascii')
CACHE_MAGIC = b'NBSEARCH-BODIES 2\n'
IS_WIN = os.sep != '/'


# ---------------------------------------------------------------- 공용
def nfc(s):
    """[NFC 정규화]
    - ASCII 는 그대로(unicodedata 불러오기 약 0.5ms 를 아낀다)
    """
    if s.isascii():
        return s
    import unicodedata
    f = getattr(unicodedata, 'is_normalized', None)
    if f is not None and f('NFC', s):
        return s
    return unicodedata.normalize('NFC', s)


def norm(s):
    return s.lower().translate(NORM_TABLE)


def uni_cased(s):
    """[비 ASCII 대소문자 글자가 있나]
    - 있으면 바이트 소문자화(ASCII 만)로는 대소문자 무시가 안 되므로 문자열 경로로 찾는다
    """
    for c in s:
        if ord(c) > 127 and c.lower() != c.upper():
            return True
    return False


def disp(p):
    """[표시용 경로]
    - Windows 에서도 슬래시 표기(C:/...)로 낸다(_lib.sh nw_tool_path 규칙)
    """
    if IS_WIN:
        return p.replace('\\', '/')
    return p


def npath(p):
    return os.path.normpath(p)


def is_word(c):
    return c.isalnum() or c == '_'


def is_hangul(ch):
    return '\uac00' <= ch <= '\ud7a3'


def maybe_nfd(b):
    """[NFD 가 섞였을 수 있나]
    - 한글 자모(U+1100-11FF, E1 84-87), 결합 발음 부호(U+0300-036F, CC,CD), 가나 결합 탁점(E3 82 99,9A)
    - 한 바이트 검사(memchr)로 먼저 걸러 보통 파일은 거의 비용이 없다
    """
    if b'\xe1' in b:
        for mk in (b'\xe1\x84', b'\xe1\x85', b'\xe1\x86', b'\xe1\x87'):
            if mk in b:
                return True
    if b'\xcc' in b or b'\xcd' in b:
        return True
    if b'\xe3' in b and (b'\xe3\x82\x99' in b or b'\xe3\x82\x9a' in b):
        return True
    return False


def read_raw(p):
    """[파일을 UTF-8 바이트로]
    - BOM 을 떼고, NFD 가 섞였을 수 있으면 NFC 로 고친다. 읽을 수 없으면 None
    """
    try:
        with open(p, 'rb') as f:
            b = f.read()
    except (IOError, OSError):
        return None
    if b.startswith(b'\xef\xbb\xbf'):
        b = b[3:]
    if maybe_nfd(b):
        b = nfc(b.decode('utf-8', 'replace')).encode('utf-8')
    return b


def read_text(p):
    b = read_raw(p)
    if b is None:
        return None
    return b.decode('utf-8', 'replace')


# ---------------------------------------------------------------- 마크다운 링크 (re 없이)
def iter_links(line):
    """[줄의 마크다운 .md 링크]
    - '](경로.md)' 에서 경로에 '(', ')', 공백이 없는 것만(현행 nb-grep.sh 의 정규식과 같은 기준)
    - 돌려줌: (텍스트 시작, 텍스트 끝, 경로 시작, 경로 끝, 링크 끝). 텍스트가 없으면 텍스트 시작 = -1
    """
    pos = 0
    while True:
        r = line.find('](', pos)
        if r < 0:
            return
        k = line.find(')', r + 2)
        if k < 0:
            return
        path = line[r + 2:k]
        if len(path) < 4 or '(' in path or ' ' in path or not path.endswith('.md'):
            pos = r + 1
            continue
        prev = line.rfind(']', 0, r)
        lb = line.find('[', prev + 1, r)
        yield (lb, r, r + 2, k, k + 1)
        pos = k + 1


def first_link(line):
    for lk in iter_links(line):
        return lk
    return None


def first_full_link(line):
    for lk in iter_links(line):
        if lk[0] >= 0:
            return lk
    return None


class Doc(object):
    """읽은 파일 하나. 거르기는 바이트(소문자,정규화 사본)로 하고, 표시할 때만 문자열로 푼다. 사본은 필요할 때 한 번만"""
    __slots__ = ('path', '_raw', '_lowb', '_lowb_lines', '_normb', '_normb_lines', '_text', '_lines', '_low',
                 '_low_lines', '_normu_lines')

    def __init__(self, path, raw=None, lowb=None):
        self.path = path
        self._raw = raw
        self._lowb = lowb
        self._lowb_lines = None
        self._normb = None
        self._normb_lines = None
        self._text = None
        self._lines = None
        self._low = None
        self._low_lines = None
        self._normu_lines = None

    @property
    def raw(self):
        if self._raw is None:
            b = read_raw(self.path)
            if b is None:
                b = b''
            self._raw = b
        return self._raw

    @property
    def lowb(self):
        if self._lowb is None:
            self._lowb = self.raw.lower()
        return self._lowb

    @property
    def lowb_lines(self):
        if self._lowb_lines is None:
            ls = self.lowb.split(b'\n')
            if self.lowb.endswith(b'\n'):
                ls = ls[:-1]
            self._lowb_lines = ls
        return self._lowb_lines

    @property
    def normb(self):
        if self._normb is None:
            self._normb = self.lowb.translate(None, SEP_ASCII_B)
        return self._normb

    def normb_lines(self):
        if self._normb_lines is None:
            self._normb_lines = self.normb.split(b'\n')[:len(self.lowb_lines)]
        return self._normb_lines

    @property
    def text(self):
        if self._text is None:
            self._text = self.raw.decode('utf-8', 'replace')
        return self._text

    @property
    def lines(self):
        if self._lines is None:
            t = self.text
            lines = t.split('\n')
            if t.endswith('\n'):
                lines = lines[:-1]
            self._lines = [l.rstrip('\r') for l in lines]
        return self._lines

    @property
    def low(self):
        if self._low is None:
            self._low = self.text.lower()
        return self._low

    @property
    def low_lines(self):
        if self._low_lines is None:
            self._low_lines = [l.lower() for l in self.lines]
        return self._low_lines

    def normu_lines(self):
        if self._normu_lines is None:
            self._normu_lines = [l.translate(NORM_TABLE) for l in self.low_lines]
        return self._normu_lines

    def first_lowb(self):
        b = self.lowb
        k = b.find(b'\n')
        if k < 0:
            return b
        return b[:k]


class Q(object):
    """검색어 하나(대소문자 무시). 바이트로 거르고, 비 ASCII 대소문자 글자가 있으면 문자열로 찾는다"""
    __slots__ = ('s', 'b', 'uni')

    def __init__(self, s):
        self.s = s.lower()
        self.uni = uni_cased(s)
        self.b = self.s.encode('utf-8')

    def in_doc(self, doc):
        if self.uni:
            return self.s in doc.low
        return self.b in doc.lowb

    def line_idx(self, doc):
        if self.uni:
            s = self.s
            return [i for i, ll in enumerate(doc.low_lines) if s in ll]
        b = self.b
        return [i for i, lb in enumerate(doc.lowb_lines) if b in lb]

    def count(self, doc):
        if self.uni:
            return doc.low.count(self.s)
        return doc.lowb.count(self.b)


class NQ(object):
    """정규화 검색어 하나(공백류,_,-,.,/ 무시)"""
    __slots__ = ('s', 'b', 'uni')

    def __init__(self, name):
        self.s = norm(name)
        self.uni = uni_cased(name)
        self.b = self.s.encode('utf-8')

    def line_idx(self, doc):
        if self.uni:
            s = self.s
            return [i for i, nl in enumerate(doc.normu_lines()) if s in nl]
        if self.b not in doc.normb:
            return []
        b = self.b
        return [i for i, nl in enumerate(doc.normb_lines()) if b in nl]


_DOC_CACHE = {}


def load_doc(p, st=None):
    """[파일 읽기]
    - 같은 프로세스에서 다시 부르면 수정 시각과 크기가 같을 때 읽은 결과를 재사용한다(벤치마크, 시험)
    - 읽을 수 없으면 None
    """
    if st is None:
        try:
            st = os.stat(p)
        except OSError:
            return None
    key = (st.st_mtime_ns, st.st_size)
    c = _DOC_CACHE.get(p)
    if c is not None and c[0] == key:
        return c[1]
    b = read_raw(p)
    if b is None:
        return None
    d = Doc(p, raw=b)
    _DOC_CACHE[p] = (key, d)
    return d


class Ix(object):
    """레이어 루트의 인덱스 파일 하나"""
    __slots__ = ('path', 'rel', 'lrank', 'order', 'doc')

    def __init__(self, path, rel, lrank, order, doc):
        self.path = path
        self.rel = rel
        self.lrank = lrank
        self.order = order
        self.doc = doc


class Hit(object):
    """인덱스 줄 하나의 일치. tier 0 그대로, 1 별칭, 2 정규화, 3 다단어, 4 단어 일부"""
    __slots__ = ('ix', 'no', 'tier', 'label', 's', 'e', 'score', 'link', 'body', 'slug')

    def __init__(self, ix, no, tier, label, s, e):
        self.ix = ix
        self.no = no
        self.tier = tier
        self.label = label
        self.s = s
        self.e = e
        self.score = 0.0
        self.link = None
        self.body = None
        self.slug = None
        lk = first_link(self.line)
        if lk is not None:
            self.link = self.line[lk[2]:lk[3]]
            self.body = npath(os.path.join(os.path.dirname(ix.path), self.link))
            self.slug = os.path.splitext(os.path.basename(self.link))[0]

    @property
    def line(self):
        return self.ix.doc.lines[self.no - 1]


# ---------------------------------------------------------------- 문맥
class Ctx(object):
    """한 번의 호출(노트북, 슬러그, 스택) 동안 공유하는 읽기 결과"""

    def __init__(self, nb, slug, stack, cache_dir=None):
        self.nb = npath(nb)
        self.slug = slug
        self.stack = stack
        self.cache_dir = cache_dir
        self.layers = []
        if slug and slug != '?':
            self.layers.append((npath(os.path.join(self.nb, 'projects', slug)), 2))
        if stack and stack not in ('?', '-'):
            self.layers.append((npath(os.path.join(self.nb, 'stacks', stack)), 1))
        self.layers.append((npath(os.path.join(self.nb, 'common')), 0))
        self.layer_dirs = set(d for d, _ in self.layers)
        self.ixs = []
        self._bodies = None
        self._aliases = None
        self._memo = {}
        self._term_memo = {}
        self._load_index()

    def _load_index(self):
        seen = set()
        order = 0
        for d, lrank in self.layers:
            try:
                names = os.listdir(d)
            except OSError:
                continue
            globbed = sorted(f for f in names if 'index' in f and f.endswith('.md') and not f.startswith('.'))
            for f in ['INDEX.md'] + globbed:
                p = os.path.join(d, f)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if (st.st_mode & 0o170000) != 0o100000:   # 일반 파일만
                    continue
                key = (st.st_dev, st.st_ino)
                if not st.st_ino:
                    key = os.path.normcase(os.path.realpath(p))
                if key in seen:
                    continue
                seen.add(key)
                p = npath(p)
                doc = load_doc(p, st)
                if doc is None:
                    continue
                self.ixs.append(Ix(p, self.rel(p), lrank, order, doc))
                order += 1

    def term_lines(self, q):
        """[검색어가 나온 인덱스 줄]
        - [(Ix, 줄 번호 목록)]. 같은 호출에서 같은 검색어는 한 번만 훑는다
        """
        key = (q.s, q.uni)
        r = self._term_memo.get(key)
        if r is None:
            r = []
            for ix in self.ixs:
                if q.in_doc(ix.doc):
                    li = q.line_idx(ix.doc)
                    if li:
                        r.append((ix, li))
            self._term_memo[key] = r
        return r

    def rel(self, p):
        """[노트북 기준 상대 경로(표시용 슬래시)]"""
        pre = self.nb + os.sep
        if p.startswith(pre):
            return disp(p[len(pre):])
        return disp(os.path.relpath(p, self.nb))

    def is_index_like(self, p):
        b = os.path.basename(p).lower()
        if b.startswith('index') or 'router' in b or b == 'search-aliases.md':
            return True
        return 'index' in b and os.path.dirname(p) in self.layer_dirs

    def aliases(self):
        """[별칭 그룹]
        - common/search-aliases.md 와 각 레이어 루트의 search-aliases.md 의 '- a = b = c' 줄. 파일이 없으면 빈 목록
        """
        if self._aliases is None:
            groups = []
            files = [npath(os.path.join(self.nb, 'common', 'search-aliases.md'))]
            for d, _ in self.layers:
                p = npath(os.path.join(d, 'search-aliases.md'))
                if p not in files:
                    files.append(p)
            for p in files:
                doc = load_doc(p)
                if doc is None:
                    continue
                for line in doc.lines:
                    s = line.strip()
                    if len(s) < 3 or s[0] not in '-*' or not s[1].isspace() or '=' not in s:
                        continue
                    mem = [x.strip().strip('`').strip() for x in s[1:].split('=')]
                    mem = [x for x in mem if x]
                    if len(mem) >= 2:
                        groups.append(mem)
            self._aliases = groups
        return self._aliases

    def alias_terms(self, name):
        """[이름의 별칭]
        - 이름과 같은(대소문자, 공백,_,-,.,/ 무시) 구성원이 있는 그룹의 다른 구성원들
        """
        key = norm(name)
        if not key:
            return []
        out = []
        for g in self.aliases():
            if any(norm(m) == key for m in g):
                for m in g:
                    if norm(m) != key and m.lower() not in [x.lower() for x in out]:
                        out.append(m)
        return out

    def _list_bodies(self):
        """[본문 파일 목록]
        - [(경로, 레이어 가산, stat)]. os.walk 와 같은 순서(파일 먼저, 하위 폴더는 이름순), 심볼릭 링크 폴더는 따라가지 않는다
        """
        out = []

        def walk(d, lrank, at_root):
            try:
                ents = list(os.scandir(d))
            except OSError:
                return
            files = []
            dirs = []
            for e in ents:
                nm = e.name
                if nm.startswith('.'):
                    continue
                try:
                    if e.is_dir():
                        if nm not in ('_archive', 'scripts') and not e.is_symlink():
                            dirs.append(e)
                    elif nm.endswith('.md'):
                        files.append(e)
                except OSError:
                    continue
            for e in sorted(files, key=lambda x: x.name):
                b = e.name.lower()
                if b.startswith('index') or 'router' in b or b == 'search-aliases.md' or (at_root and 'index' in b):
                    continue   # is_index_like 와 같은 기준(레이어 루트 여부를 깊이로 안다)
                try:
                    st = e.stat()
                except OSError:
                    continue
                out.append((e.path, lrank, st))
            for e in sorted(dirs, key=lambda x: x.name):
                walk(e.path, lrank, False)

        for d, lrank in self.layers:
            walk(d, lrank, True)
        return out

    def body_set(self):
        """[본문 전부를 한 덩어리로]
        - 레이어 아래 .md 중 인덱스,라우터,_archive/,scripts/, 숨김 파일을 뺀 것의 소문자 사본을 \\x00 으로 이어 붙인 바이트
        - cache_dir 가 있으면 캐시에서 읽는다(파일마다 수정 시각과 크기가 같을 때만, 아니면 다시 만든다)
        """
        if self._bodies is None:
            listed = self._list_bodies()
            bs = None
            if self.cache_dir:
                bs = self._cache_load(listed)
            if bs is None:
                paths = []
                lranks = []
                lows = []
                sts = []
                for p, lrank, st in listed:
                    doc = load_doc(p, st)
                    if doc is None:
                        continue
                    paths.append(p)
                    lranks.append(lrank)
                    lows.append(doc.lowb)
                    sts.append(st)
                bs = BodySet(paths, lranks, lows, 0)
                if self.cache_dir and len(paths) == len(listed):
                    self._cache_save(paths, sts, lows)
            self._bodies = bs
        return self._bodies

    # ---- 본문 캐시 ----
    def _cache_file(self):
        import zlib
        key = zlib.crc32(('%s\n%s\n%s' % (self.nb, self.slug, self.stack)).encode('utf-8')) & 0xffffffff
        safe = ''.join(c for c in ('%s-%s' % (self.slug, self.stack)) if c.isalnum() or c in '-_.')[:60]
        return os.path.join(self.cache_dir, 'bodies-%s-%08x.bin' % (safe, key))

    def _cache_load(self, listed):
        try:
            with open(self._cache_file(), 'rb') as f:
                data = f.read()
        except (IOError, OSError):
            return None
        try:
            if not data.startswith(CACHE_MAGIC):
                return None
            pos = len(CACHE_MAGIC)
            e = data.index(b'\n', pos)
            n = int(data[pos:e])
            pos = e + 1
            if n != len(listed):
                return None
            lens = []
            for i in range(n):
                e = data.index(b'\n', pos)
                rel, mt, sz, ln = data[pos:e].split(b'\t')
                pos = e + 1
                p, lrank, st = listed[i]
                if int(mt) != st.st_mtime_ns or int(sz) != st.st_size:
                    return None
                if rel.decode('utf-8') != self.rel(p):
                    return None
                lens.append(int(ln))
            if pos + sum(lens) + max(0, n - 1) != len(data):
                return None
            return BodySet([x[0] for x in listed], [x[1] for x in listed], None, pos, data, lens)
        except (ValueError, UnicodeDecodeError):
            return None

    def _cache_save(self, paths, sts, lows):
        head = [CACHE_MAGIC, ('%d\n' % len(paths)).encode('ascii')]
        for p, st, lb in zip(paths, sts, lows):
            rel = self.rel(p)
            if '\t' in rel or '\n' in rel:
                return
            head.append(('%s\t%d\t%d\t%d\n' % (rel, st.st_mtime_ns, st.st_size, len(lb))).encode('utf-8'))
        path = self._cache_file()
        tmp = '%s.%d.tmp' % (path, os.getpid())
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(tmp, 'wb') as f:
                f.write(b''.join(head))
                f.write(b'\x00'.join(lows))
            os.replace(tmp, path)
        except (IOError, OSError):
            try:
                os.remove(tmp)
            except OSError:
                pass


class BodySet(object):
    """본문 전부의 소문자 사본(한 덩어리 바이트)과 문서별 [시작, 끝) 위치. 문서 사이는 \\x00 이라 이름이 걸쳐 맞지 않는다"""
    __slots__ = ('paths', 'lranks', 'blob', 'starts', 'ends', 'index')

    def __init__(self, paths, lranks, lows, base, data=None, lens=None):
        self.paths = paths
        self.lranks = lranks
        if data is None:
            lens = [len(x) for x in lows]
            data = b'\x00'.join(lows)
        self.blob = data
        self.starts = []
        self.ends = []
        pos = base
        for ln in lens:
            self.starts.append(pos)
            self.ends.append(pos + ln)
            pos += ln + 1
        self.index = dict((p, i) for i, p in enumerate(paths))

    def __len__(self):
        return len(self.paths)

    def counts(self, q):
        """[검색어가 나온 문서와 횟수]
        - {문서 번호: 횟수}. 바이트 한 덩어리에서 find 를 되풀이하고, 맞은 문서는 끝으로 건너뛴다
        """
        out = {}
        if not self.paths:
            return out
        if q.uni:
            for i, p in enumerate(self.paths):
                d = load_doc(p)
                if d is not None:
                    c = d.low.count(q.s)
                    if c:
                        out[i] = c
            return out
        b = q.b
        blob = self.blob
        pos = self.starts[0]
        starts = self.starts
        ends = self.ends
        while True:
            k = blob.find(b, pos)
            if k < 0:
                break
            i = bisect_right(starts, k) - 1
            out[i] = blob.count(b, starts[i], ends[i])
            pos = ends[i]
        return out

    def count_in(self, q, i):
        if q.uni:
            d = load_doc(self.paths[i])
            if d is None:
                return 0
            return d.low.count(q.s)
        return self.blob.count(q.b, self.starts[i], self.ends[i])

    def title_lowb(self, i):
        k = self.blob.find(b'\n', self.starts[i], self.ends[i])
        if k < 0:
            k = self.ends[i]
        return self.blob[self.starts[i]:k]

    def length(self, i):
        return self.ends[i] - self.starts[i]


# ---------------------------------------------------------------- 단어
def query_words(name):
    """[이름을 단어로]
    - 공백으로 나누고 앞뒤 문장부호를 뗀다. 짧은 단어와 한 글자 기능어는 뺀다
    """
    words = []
    for w in name.lower().split():
        w = w.strip('.,;:!?()[]{}"\'`')
        if not w or w in words:
            continue
        if all(is_hangul(c) for c in w):
            if len(w) < WORD_MIN_HANGUL or (len(w) == 1 and w in STOP_1):
                continue
        elif len(w) < WORD_MIN:
            continue
        words.append(w)
    return words


def word_key(w):
    """[단어 비교 키]
    - 한글로 끝나면 흔한 조사,어미를 뗀 줄기(2자 이상 남을 때). 줄기는 원형의 앞부분이라 원형이 있으면 줄기도 있다
    """
    if w and is_hangul(w[-1]):
        for e in HANGUL_END:
            if w.endswith(e) and len(w) - len(e) >= 2:
                return w[:-len(e)]
    return w


# ---------------------------------------------------------------- 인덱스 검색
def _norm_span(line_low, needle):
    keep = []
    buf = []
    for i, ch in enumerate(line_low):
        if ch in SEP_SET:
            continue
        keep.append(i)
        buf.append(ch)
    k = ''.join(buf).find(needle)
    if k < 0:
        return 0, 0
    return keep[k], keep[k + len(needle) - 1] + 1


def find_hits(ctx, name):
    """[이름 하나의 인덱스 히트]
    - 1순위 그대로(대소문자 무시) > 별칭 > 정규화 > 다단어(구절이 어디에도 안 맞을 때만)
    - 같은 순위 안에서는 단어 경계, 링크 텍스트,경로 안 일치, 슬러그 일치, 본문 언급 횟수, 레이어 가산
    """
    lname = name.lower()
    if not lname.strip():
        return []
    hits = {}

    def add(ix, i, tier, label, term):
        key = (ix.order, i)
        if key in hits:
            return
        k = ix.doc.low_lines[i].find(term)
        if k < 0:
            k = 0
        hits[key] = Hit(ix, i + 1, tier, label, k, k + len(term))

    q = Q(lname)
    for ix, li in ctx.term_lines(q):
        for i in li:
            add(ix, i, 0, None, q.s)
    for term in ctx.alias_terms(name):
        aq = Q(term)
        for ix, li in ctx.term_lines(aq):
            for i in li:
                add(ix, i, 1, term, aq.s)
    nq = NQ(lname)
    if len(nq.s) >= NORM_MIN:
        for ix in ctx.ixs:
            for i in nq.line_idx(ix.doc):
                key = (ix.order, i)
                if key not in hits:
                    s, e = _norm_span(ix.doc.low_lines[i], nq.s)
                    hits[key] = Hit(ix, i + 1, 2, None, s, e)
    phrase = any(h.tier in (0, 2) for h in hits.values())
    words = query_words(lname)
    if not phrase and len(words) >= 2:
        wqs = [Q(w) for w in words]
        per_ix = None
        for wq in wqs:
            cur = dict((ix.order, (ix, set(li))) for ix, li in ctx.term_lines(wq))
            if per_ix is None:
                per_ix = cur
            else:
                per_ix = dict((o, (v[0], v[1] & cur[o][1])) for o, v in per_ix.items() if o in cur)
            if not per_ix:
                break
        for o in sorted(per_ix or {}):
            ix, common = per_ix[o]
            for i in sorted(common):
                add(ix, i, 3, words, wqs[0].s)

    out = list(hits.values())
    nn = nq.s
    for h in out:
        line = h.line
        s, e = h.s, h.e
        wb = (s <= 0 or not is_word(line[s - 1])) and (e >= len(line) or not is_word(line[e]))
        inlink = False
        for lk in iter_links(line):
            if (lk[0] >= 0 and lk[0] < s < lk[1]) or lk[2] <= s < lk[3]:
                inlink = True
                break
        has_body = h.body is not None and not ctx.is_index_like(h.body)
        sc = 4 * int(wb) + 2 * int(inlink) + h.ix.lrank + int(has_body)
        if SLUG_BONUS and h.slug and len(nn) >= NORM_MIN and nn in norm(h.slug):
            sc += SLUG_BONUS
        if TF_BONUS and has_body:
            d = load_doc(h.body)
            if d is not None:
                tq = q
                if h.tier == 1:
                    tq = Q(h.label)
                sc += TF_BONUS * min(3.0, math.log(1 + tq.count(d), 2))
        h.score = sc
    out.sort(key=lambda h: (h.tier, -h.score, h.ix.order, h.no))
    return out


def fuzzy_search(ctx, name, want_lines, want_bodies):
    """[단어 일부 일치]
    - 여러 단어 이름에서 단어의 절반 이상(최소 2개)이 같은 인덱스 줄에 있는 줄, 같은 본문에 있는 본문을 찾는다
    - 인덱스는 한 번만 훑고, 본문은 FUZZY_BODY_SCOPE 에 따라 전부 또는 단어가 나온 인덱스 줄이 가리키는 것만 채점한다
    - 줄은 맞은 단어 수, 드문 단어 가중(idf) 순. 본문은 맞은 단어 수, BM25(제목 줄 가산) 순
    - 반환: ([(점수, 맞은 단어 목록, Hit)], [(점수, 맞은 단어 목록, 경로, Doc)])
    """
    words = query_words(name)
    if len(words) < 2 or (want_lines <= 0 and want_bodies <= 0):
        return [], []
    need = max(2, int(math.ceil(len(words) * FUZZY_MIN_RATIO)))
    kqs = [Q(word_key(w)) for w in words]
    total = 0
    df = [0] * len(words)
    cand = []
    linked = set()
    by_ix = {}
    for wi, kq in enumerate(kqs):
        for ix, li in ctx.term_lines(kq):
            per_line = by_ix.setdefault(ix.order, (ix, {}))[1]
            for i in li:
                per_line.setdefault(i, []).append(wi)
            df[wi] += len(li)
    for ix in ctx.ixs:
        total += ix.doc.lowb.count(b'\n')
    for o in sorted(by_ix):
        ix, per_line = by_ix[o]
        for i in sorted(per_line):
            if len(per_line[i]) >= need:
                cand.append((ix, i, per_line[i]))
            if want_bodies > 0 and FUZZY_BODY_SCOPE == 'linked':
                line = ix.doc.lines[i]
                lk = first_link(line)
                if lk is not None:
                    linked.add(npath(os.path.join(os.path.dirname(ix.path), line[lk[2]:lk[3]])))
    line_idf = [math.log((total + 1.0) / (1.0 + d)) for d in df]
    lines_out = []
    for ix, i, got in cand:
        ll = ix.doc.low_lines[i]
        first = None
        for wi in got:
            k = ll.find(kqs[wi].s)
            if k >= 0 and (first is None or k < first[0]):
                first = (k, k + len(kqs[wi].s))
        if first is None:
            first = (0, 0)
        h = Hit(ix, i + 1, 4, [words[wi] for wi in got], first[0], first[1])
        sc = sum(line_idf[wi] for wi in got)
        if h.body is not None and not ctx.is_index_like(h.body):
            sc += 0.5
        lines_out.append((sc, h.label, h))
    lines_out.sort(key=lambda r: (-len(r[1]), -r[0], r[2].ix.order, r[2].no))
    lines_out = lines_out[:max(0, want_lines)]
    if want_bodies <= 0:
        return lines_out, []
    exclude = set(h.body for sc, got, h in lines_out if h.body is not None)
    bs = ctx.body_set()
    n = len(bs)
    if not n:
        return lines_out, []
    avg = (bs.ends[-1] - bs.starts[0] - (n - 1)) / float(n)
    if FUZZY_BODY_SCOPE == 'linked':
        idx = sorted(bs.index[p] for p in linked if p in bs.index)
        idf = line_idf
    else:
        idx = range(n)
    rows = []
    bdf = [0] * len(words)
    for i in idx:
        tf = [bs.count_in(kq, i) for kq in kqs]
        for wi, c in enumerate(tf):
            if c:
                bdf[wi] += 1
        if sum(1 for c in tf if c) >= need and bs.paths[i] not in exclude:
            rows.append((i, tf))
    if FUZZY_BODY_SCOPE != 'linked':
        idf = [math.log((n - d + 0.5) / (d + 0.5) + 1.0) for d in bdf]
    scored = []
    for i, tf in rows:
        dl = bs.length(i)
        title = bs.title_lowb(i)
        sc = 0.0
        got = []
        for wi, c in enumerate(tf):
            if not c:
                continue
            got.append(words[wi])
            sc += idf[wi] * c * (BM25_K1 + 1) / (c + BM25_K1 * (1 - BM25_B + BM25_B * dl / avg))
            if kqs[wi].uni:
                in_title = kqs[wi].s in title.decode('utf-8', 'replace')
            else:
                in_title = kqs[wi].b in title
            if in_title:
                sc += idf[wi] * TITLE_BOOST
        scored.append((sc, got, bs.paths[i]))
    scored.sort(key=lambda r: (-len(r[1]), -r[0], r[2]))
    out = []
    for sc, got, p in scored[:want_bodies]:
        out.append((sc, got, p, load_doc(p)))
    return lines_out, out


# ---------------------------------------------------------------- 본문 검색
def body_candidates(ctx, name, exclude, want=None):
    """[인덱스 밖 본문 후보]
    - 이름(과 별칭)이 그대로 나온 본문을 많이 나온 순서로
    - 반환: [(경로, 횟수, 첫 일치 앞뒤 창)]. 창은 앞 want 개에만 만든다(None 이면 전부)
    """
    qs = [Q(t) for t in [name] + ctx.alias_terms(name) if t.strip()]
    if not qs:
        return []
    bs = ctx.body_set()
    tot = {}
    for q in qs:
        for i, c in bs.counts(q).items():
            tot[i] = tot.get(i, 0) + c
    res = []
    for i, c in tot.items():
        p = bs.paths[i]
        if p not in exclude:
            res.append((p, bs.lranks[i], c))
    res.sort(key=lambda r: (-r[2], -r[1], r[0]))
    out = []
    for n, (p, lrank, cnt) in enumerate(res):
        win = ''
        if want is None or n < want:
            doc = load_doc(p)
            if doc is not None:
                low = doc.low
                first = None
                for q in qs:
                    k = low.find(q.s)
                    if k >= 0 and (first is None or k < first[0]):
                        first = (k, k + len(q.s))
                if first is not None:
                    t = doc.text
                    a = max(0, first[0] - CAND_WIN)
                    b = min(len(t), first[1] + CAND_WIN)
                    win = ' '.join(t[a:b].split())
        out.append((p, cnt, win))
    return out


# ---------------------------------------------------------------- 표시
def _snap(line, a, b, s, e):
    """[창 끝을 단어 경계로]
    - 일치 구간 [s, e) 는 늘 남긴다
    """
    if a > 0:
        for j in range(a, min(s, a + SNAP)):
            if line[j] in SEP_CHARS:
                a = j + 1
                break
    if b < len(line):
        for j in range(b - 1, max(e, b - SNAP) - 1, -1):
            if line[j] in SEP_CHARS:
                b = j
                break
    return a, b


def clip_line(line, s, e):
    """[긴 히트 줄 줄이기]
    - LINE_MAX 이하면 그대로, 넘으면 첫 링크(줄 머리가 짧으면 머리부터) + 일치 앞뒤 창, 잘린 곳은 '…'
    """
    if len(line) <= LINE_MAX:
        return line
    ws, we = _snap(line, max(0, s - WIN), min(len(line), e + WIN), s, e)
    lk = first_full_link(line)
    segs = []
    if lk is not None:
        hs = lk[0]
        he = lk[4]
        if he <= HEAD_LINK_MAX:
            hs = 0
        if ws <= he + 1 and we > hs:
            segs.append((min(hs, ws), max(he, we)))
        elif we <= hs:
            segs.append((ws, we))
            segs.append((hs, he))
        else:
            segs.append((hs, he))
            segs.append((ws, we))
    else:
        segs.append((ws, we))
    out = []
    prev = 0
    for a, b in segs:
        if a > prev:
            out.append('…')
        out.append(line[a:b])
        prev = b
    if prev < len(line):
        out.append('…')
    return ''.join(out)


def _clip_match(l, a, b):
    if len(l) <= MATCH_LINE_MAX:
        return l
    half = max(20, (MATCH_LINE_MAX - (b - a)) // 2)
    x, y = _snap(l, max(0, a - half), min(len(l), b + half), a, b)
    head = ''
    tail = ''
    if x > 0:
        head = '…'
    if y < len(l):
        tail = '…'
    return head + l[x:y] + tail


def body_lines(path, bodies_seen, terms):
    """[본문 블록]
    - 짧으면 전문, 길면 제목 줄 + 이름이 나온 줄(없으면 머리 몇 줄) 뒤 생략 표시
    - 이 세션에 이미 낸 본문은 경로만
    - 반환: (줄 목록, 본문을 냈나)
    """
    doc = load_doc(path)
    if doc is None:
        return ['   (본문 파일 없음: %s)' % disp(path)], False
    if path in bodies_seen:
        return ['   --- 본문: %s (이미 이 세션에 출력됨 - 필요하면 Read)' % disp(path)], False
    bodies_seen.add(path)
    t = doc.text
    n = t.count('\n')
    lines = doc.lines
    out = ['   --- 본문: %s (%d 줄)' % (disp(path), n)]
    if n <= BODY_FULL_LINES and len(t) <= BODY_FULL_CHARS:
        out += ['   | ' + l for l in lines]
        return out, True
    matches = []
    if BODY_MATCH_LINES > 0 and terms:
        for i in range(1, len(lines)):
            ll = doc.low_lines[i]
            for term in terms:
                j = ll.find(term)
                if j >= 0:
                    matches.append((i, j, j + len(term)))
                    break
            if len(matches) >= BODY_MATCH_LINES + BODY_HEAD_LINES:
                break
    head_n = BODY_HEAD_LINES
    if BODY_MODE == 'title' and matches:
        head_n = 1
    total = 0
    k = 0
    for l in lines[:head_n]:
        k += 1
        if total + len(l) > BODY_HEAD_CHARS:
            room = BODY_HEAD_CHARS - total
            if room > 40:
                out.append('   | ' + l[:room] + '…')
            break
        out.append('   | ' + l)
        total += len(l)
    shown = 0
    for i, a, b in matches:
        if shown >= BODY_MATCH_LINES:
            break
        if i < k:
            continue
        out.append('   | %d: %s' % (i + 1, _clip_match(lines[i], a, b)))
        shown += 1
    out.append('   | … (이하 생략 - 전문은 위 경로)')
    return out, True


def _tag(h):
    if h.tier == 1:
        return '(별칭: %s) ' % h.label
    if h.tier == 2:
        return '(정규화 일치) '
    if h.tier == 3:
        return '(단어 일치: %s) ' % ' + '.join(h.label)
    return ''


def search_name(ctx, name):
    """[이름 하나의 검색 결과]
    - 세션 상태(이미 낸 본문)와 무관한 부분. 같은 호출에서 같은 이름은 한 번만 찾는다
    - 반환: (히트 목록, 본문 언급 [(경로, 횟수)], 본문 후보 [(경로, 횟수, 창)], 후보 그 외 수, 연관 후보, 연관 본문)
    """
    if name in ctx._memo:
        return ctx._memo[name]
    hits = find_hits(ctx, name)
    ments = []
    cands = []
    cand_more = 0
    fz = []
    fzb = []
    strong = any(h.tier <= 1 for h in hits)
    if strong and MENTION_TOP > 0:
        linked = set(h.body for h in hits if h.body is not None)
        ments = body_candidates(ctx, name, linked, 0)
    if not hits or (FALLBACK_ON_WEAK and not strong):
        linked = set(h.body for h in hits if h.body is not None)
        allc = body_candidates(ctx, name, linked, CAND_TOP)
        cands = allc[:CAND_TOP]
        cand_more = max(0, len(allc) - CAND_TOP)
        if not hits and not allc:
            fz, fzb = fuzzy_search(ctx, name, FUZZY_TOP, FUZZY_BODY_TOP)
    r = (hits, ments, cands, cand_more, fz, fzb)
    ctx._memo[name] = r
    return r


def render_name(ctx, name, bodies_seen):
    """[이름 하나의 출력]
    - 반환: (대조 줄 앞까지의 출력 줄, 로그 files 목록, per 사전)
    """
    hits, ments, cands, cand_more, fz, fzb = search_name(ctx, name)
    lines = []
    printed = []
    hitfiles = []
    candidates = []
    files = []
    for h in hits:
        if h.link:
            files.append(h.link)
        else:
            files.append('%s:%d' % (os.path.basename(h.ix.path), h.no))

    shown = []
    extra = []
    shown_bodies = set()
    for h in hits:
        dup = DEDUP_BODY and h.body is not None and h.body in shown_bodies
        if len(shown) < TOP_HITS and not dup:
            shown.append(h)
            if h.body is not None:
                shown_bodies.add(h.body)
        else:
            extra.append(h)
    rest = max(0, len(extra) - EXTRA_HITS)
    extra = extra[:EXTRA_HITS]

    slots = BODY_TOP
    opened = set()
    for h in shown:
        lines.append('히트: %s:%d' % (disp(h.ix.path), h.no))
        lines.append('   ' + _tag(h) + clip_line(h.line, h.s, h.e))
        if h.body is None:
            continue
        hitfiles.append(h.body)
        if h.body in opened or ctx.is_index_like(h.body):
            continue
        opened.add(h.body)
        if slots <= 0 or h.tier > BODY_TIER_MAX:
            continue
        slots -= 1
        terms = [name.lower()]
        if h.tier == 1:
            terms = [h.label.lower()] + terms
        elif h.tier == 3:
            terms = list(h.label)
        bl, did = body_lines(h.body, bodies_seen, terms)
        lines.extend(bl)
        if did:
            printed.append(h.body)
    for h in extra:
        if h.body is not None:
            hitfiles.append(h.body)
            lines.append('추가 히트: %s:%d [%s]' % (h.ix.rel, h.no, h.slug))
        else:
            lines.append('추가 히트: %s:%d' % (h.ix.rel, h.no))
    if rest > 0:
        lines.append('그 외 히트 %d건 (표시 생략)' % rest)

    if ments:
        parts = ['%s (%d곳)' % (ctx.rel(p), cnt) for p, cnt, _ in ments[:MENTION_TOP]]
        more = ''
        if len(ments) > MENTION_TOP:
            more = ' 외 %d개' % (len(ments) - MENTION_TOP)
        lines.append('본문 언급(인덱스 밖, 노트북 기준): %s%s' % (', '.join(parts), more))
        candidates.extend(p for p, _, _ in ments[:MENTION_TOP])
    for p, cnt, win in cands:
        lines.append('본문 후보(인덱스 밖): %s (%d곳) - …%s…' % (disp(p), cnt, win))
        candidates.append(p)
    if cand_more:
        lines.append('본문 후보 그 외 %d개 파일' % cand_more)
    for sc, got, h in fz:
        linked_body = h.body is not None and not ctx.is_index_like(h.body)
        if FUZZY_COMPACT:
            line = h.line
            a, b = _snap(line, max(0, h.s - FUZZY_WIN), min(len(line), h.e + FUZZY_WIN), h.s, h.e)
            win = line[a:b].strip()
            where = '%s:%d' % (disp(h.ix.path), h.no)
            if linked_body:
                where = disp(h.body)
            lines.append('연관 후보(단어 일부 %s): %s - …%s…' % (','.join(got), where, win))
        else:
            lines.append('연관 후보(단어 일부 %s): %s:%d' % (','.join(got), disp(h.ix.path), h.no))
            lines.append('   ' + clip_line(h.line, h.s, h.e))
        if linked_body:
            candidates.append(h.body)
    for sc, got, p, doc in fzb:
        title = ''
        if doc is not None and doc.lines:
            title = doc.lines[0]
        if len(title) > 120:
            title = title[:120] + '…'
        lines.append('연관 본문(단어 일부 %s): %s - %s' % (','.join(got), disp(p), title))
        candidates.append(p)

    top = None
    for h in shown:
        if h.body is not None and not ctx.is_index_like(h.body):
            top = h.body
            break
    if top is None and candidates:
        top = candidates[0]
    per = {'name': name, 'hits': len(hits), 'printed': printed, 'hitfiles': sorted(set(hitfiles)),
           'candidates': candidates, 'top': top}
    return lines, files, per


def clean_name(name):
    """[표시,기록용 이름]
    - NFC 로 정규화하고 줄바꿈은 공백으로(로그 한 줄 형식 보호)
    """
    return nfc(name).replace('\r', ' ').replace('\n', ' ')


def build(ctx, names, bodies_seen):
    return [render_name(ctx, clean_name(n), bodies_seen) for n in names]


def assemble(names, res, lognos, log_line):
    out = []
    for name, (lines, files, per), ln in zip(names, res, lognos):
        out.extend(lines)
        out.append('대조: "%s" → 히트 %d (log #%s)' % (clean_name(name), per['hits'], ln))
        out.append('')
    out.append(log_line)
    return '\n'.join(out) + '\n'


# ---------------------------------------------------------------- 벤치마크 진입점
def run(nb_root, slug, stack, names, bodies_seen):
    """[벤치마크 실행]
    - 기록 파일 없이 검색과 출력만 한다. 로그 번호는 0, 기록 줄은 '기록: (bench)'
    - 반환: (출력 문자열, per 목록). per 의 경로는 os.path.normpath 한 절대 경로
    """
    ctx = Ctx(os.path.abspath(nb_root), slug, stack)
    res = build(ctx, names, bodies_seen)
    text = assemble(names, res, [0] * len(names), '기록: (bench)')
    return text, [r[2] for r in res]


# ---------------------------------------------------------------- 명령행
OPTS = ('--nb', '--slug', '--stack', '--log', '--bodies', '--cache-dir', '--commit-flag')


def _parse(argv):
    opts = {}
    names = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--':
            names = argv[i + 1:]
            break
        if a in OPTS and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]
            i += 2
            continue
        raise ValueError('알 수 없는 인자: %s' % a)
    for k in ('nb', 'slug', 'stack', 'log', 'bodies'):
        if k not in opts:
            raise ValueError('인자 없음: --%s' % k)
    if not names:
        raise ValueError('대조할 이름이 없다')
    return opts, names


def _lock(f):
    try:
        import fcntl
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    except (ImportError, OSError):
        pass


def _read_seen(path):
    seen = set()
    t = read_text(path)
    if t:
        for line in t.split('\n'):
            line = line.strip()
            if line:
                seen.add(npath(line))
    return seen


def main(argv):
    if sys.version_info < (3, 7):
        sys.stderr.write('nbsearch: python 3.7 이상이 필요하다\n')
        return 3
    try:
        opts, names = _parse(argv)
    except ValueError as e:
        sys.stderr.write('nbsearch: %s\n' % e)
        return 2
    try:
        if os.environ.get('NBSEARCH_TEST_FAIL') == 'precommit':
            raise RuntimeError('시험용 실패')
        seen = _read_seen(opts['bodies'])
        ctx = Ctx(opts['nb'], opts['slug'], opts['stack'], opts.get('cache-dir') or None)
        res = build(ctx, names, seen)
    except Exception as e:  # 기록 전 실패 - nb-grep.sh 가 현행 bash 루프로 대신한다
        sys.stderr.write('nbsearch: 검색 실패(%s: %s)\n' % (type(e).__name__, e))
        return 3
    flag = opts.get('commit-flag')
    if flag:
        try:
            open(flag, 'w').close()
        except (IOError, OSError) as e:
            sys.stderr.write('nbsearch: 커밋 표지를 만들 수 없다(%s)\n' % e)
            return 3
    # 여기부터 기록. 대조 로그 줄 번호 = 기존 줄 수 + 1 (동시 실행은 잠금으로 줄 세운다)
    lognos = []
    with open(opts['log'], 'a+', encoding='utf-8', newline='\n') as f:
        _lock(f)
        f.seek(0)
        n = f.read().count('\n')
        for name, (lines, files, per) in zip(names, res):
            n += 1
            f.write('#%d %s name="%s" hits=%d files="%s"\n' % (
                n, time.strftime('%Y-%m-%d %H:%M:%S'), clean_name(name), per['hits'], ','.join(files)))
            lognos.append(n)
        f.flush()
    new = []
    for lines, files, per in res:
        for p in per['printed']:
            if p not in new:
                new.append(p)
    if new:
        # 중복 억제 목록은 출력 절약용이다. 못 쓰면(읽기 전용, 디스크 가득) 알리고 계속한다 - 대조 기록은 이미 썼으므로
        # 여기서 죽으면 출력이 통째로 사라진다(현행 bash 루프도 이 경우 오류만 내고 계속한다).
        try:
            with open(opts['bodies'], 'a', encoding='utf-8', newline='\n') as f:
                for p in new:
                    f.write(disp(p) + '\n')
        except (IOError, OSError) as e:
            sys.stderr.write('nbsearch: 본문 중복 억제 목록을 쓸 수 없다(%s) - 대조 기록과 출력은 그대로\n' % e)
    text = assemble(names, res, lognos,
                    '기록: %s' % disp(opts['log']))
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except BrokenPipeError:
        try:
            sys.stdout = open(os.devnull, 'w')
        except OSError:
            pass
    if flag:
        try:
            os.remove(flag)
        except OSError:
            pass
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
