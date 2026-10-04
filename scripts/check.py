#!/usr/bin/env python3
"""cortex 검사 - hippocampus 가 쓴 뒤마다 돌린다(agents/hippocampus.md §7).

사용법: python3 check.py --nb <cortex 경로> [--layer <common|stacks/<스택>|projects/<슬러그>|global|all>]...
  종료 코드 0 = 파손,인출 불가 없음, 1 = 있음, 2 = 사용법 오류(--nb 가 cortex 가 아님, --layer 가 없는 레이어이거나 값이 없음).
  참고 항목(줄 길이, 크기, 금지 문자, 단계 카드 세부 형식, 잠재 기억 개수)은 판단 재료라 종료 코드에 넣지 않는다.
  --layer 는 형식,참고 항목을 보여 줄 범위만 좁힌다. 죽은 링크와 주 인덱스 줄(떠오르지 않는 lesson) 검사는
  옮기기,승격,아카이브가 다른 레이어의 링크까지 죽이므로 늘 cortex 전체를 본다.

검사: 죽은 링크(cortex 밖으로 나가는 링크, refs/ 원문, 코드 안 링크는 제외), 검색 대상 인덱스에 주 줄이 없는 lesson(recall.sh 로 열 수 없음.
      단 레이어 루트 dormant.md 의 줄이 첫 링크로 가리키는 lesson 은 forget.py 가 숨긴 잠재 기억이라 세지 않고 정보 줄로만 알린다),
      경로 고정 파일 존재, 400자 넘는 인덱스 줄, 인덱스 임계(항목 = 서로 다른 첫 링크 60, 200줄, 10,000자),
      금지 문자(코드,인용,외부 문서 원문 제외), 스크립트 등록 4요소, 레이어 INDEX 크기(목표 3,000자, projects 는 thalamus 가 세션 시작에 싣는 상한 2,500자 - 정보),
      전역 형식(registry 표와 슬러그,스택 폴더, harness-routing 번호,절, 단계 카드의 INDEX 링크와 세부 형식).
"""
import re
import os, re, sys, collections

LINE_MAX = 400
FIRST_MD = re.compile(r'\]\([^() ]+\.md\)')
LINK_RE = re.compile(r'\]\(([^()\s]+?)\)')
PROTECT_FENCE = re.compile(r'```.*?```|`[^`\n]*`', re.S)
PROTECT_RE = re.compile(r'```.*?```|`[^`\n]*`|"[^"\n]*"', re.S)
FORBID = {'·': '·', 'ㆍ': 'ㆍ', '—': '—', '–': '–'}
EXTS = ('.md', '.py', '.sh', '.cs', '.js', '.ts', '.json', '.html', '.txt', '.gs', '.mjs', '.ps1')
CATEGORY_RE = re.compile(r'^(gotchas|patterns|decisions|api-facts|infra)(-[a-z0-9-]+)?\.md$')
DORMANT_RE = re.compile(r'(common|(projects|stacks)/[^/]+)/dormant[.]md')
NO_PRIMARY = '주 인덱스 줄 없음 - recall.sh 로 열 수 없음(§0)'
# 스크립트가 경로로 여는 파일 - 새로 설치한 시드에도 있어야 한다. 기기에서 자란 lesson 은 넣지 않는다(시드에 없어 새 설치가 늘 '파손'으로 보였다)
FIXED_FILES = (
    'registry.md',
    'common/harness-routing.md', 'common/glossary.md', 'common/search-aliases.md',
)


def layer_of(rel):
    p = rel.split('/')
    if p[0] in ('projects', 'stacks') and len(p) > 1:
        return p[0] + '/' + p[1]
    if p[0] == 'common':
        return 'common'
    return 'global'


def is_index(rel):
    if '/lessons/' in '/' + rel:
        return False
    b = os.path.basename(rel)
    if b == 'dormant.md':
        return False   # forget.py 가 옮겨 둔 인덱스 줄의 보관 파일이다. 인덱스가 아니라서 크기,줄 길이 임계를 재지 않는다
    p = rel.split('/')
    at_root = (len(p) == 3 and p[0] in ('projects', 'stacks')) or (len(p) == 2 and p[0] == 'common')
    if b == 'INDEX.md' or 'index' in b.lower() or 'router' in b.lower():
        return True
    return at_root and bool(CATEGORY_RE.match(b))


def is_grep_target(rel):
    d, b = os.path.split(rel)
    p = d.split('/')
    if b == 'dormant.md':
        return False   # 자동 떠올림에 안 걸리게 하려고 인덱스 이름을 피한 파일이다
    return (d == 'common' or (len(p) == 2 and p[0] in ('projects', 'stacks'))) and (b == 'INDEX.md' or 'index' in b)


def option_values(a, flag):
    """[옵션 값 수집]
    - flag 가 나온 자리마다 바로 뒤의 값을 모은다
    - 값이 없거나 다른 옵션이 바로 오면 None(사용법 오류)
    """
    out = []
    for i, x in enumerate(a):
        if x != flag:
            continue
        if i + 1 >= len(a) or a[i + 1].startswith('--'):
            return None
        out.append(a[i + 1])
    return out


def dirs_in(nb, top):
    """[폴더 이름 목록]
    - 대소문자를 그대로 비교하려고 listdir 결과를 쓴다(macOS 는 isdir 가 대소문자를 무시한다)
    """
    d = os.path.join(nb, top)
    if not os.path.isdir(d):
        return set()
    return {n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n))}


def main():
    a = sys.argv[1:]
    nbs = option_values(a, '--nb')
    if not nbs:
        print(__doc__)
        return 2
    nb = os.path.abspath(os.path.expanduser(nbs[0]))
    lay = option_values(a, '--layer')
    if lay is None:
        print('오류: --layer 뒤에 레이어 이름이 없다(예: common, stacks/unity, projects/<슬러그>, global)')
        return 2
    layers = [x.strip().rstrip('/') for x in lay] or ['all']
    if not (os.path.isfile(os.path.join(nb, 'registry.md')) and os.path.isdir(os.path.join(nb, 'common'))):
        print('오류: --nb 가 cortex 가 아니다(registry.md, common/ 없음): %s' % nb)
        return 2
    valid = ['common', 'global'] + ['stacks/' + n for n in sorted(dirs_in(nb, 'stacks'))] + ['projects/' + n for n in sorted(dirs_in(nb, 'projects'))]
    for l in layers:
        if l != 'all' and l not in valid:
            print('오류: --layer %s 가 cortex 에 없다. 있는 것: all, %s' % (l, ', '.join(valid)))
            return 2
    sel = lambda rel: 'all' in layers or layer_of(rel) in layers
    files, texts = {}, {}
    for dp, dn, fn in os.walk(nb):
        dn[:] = [d for d in dn if d not in ('.hippocampus', '__pycache__', '.git')]
        for f in fn:
            if f == '.DS_Store':
                continue
            rel = os.path.relpath(os.path.join(dp, f), nb).replace(os.sep, '/')
            files[rel] = os.path.join(dp, f)
            if f.endswith('.md'):
                try:
                    texts[rel] = open(os.path.join(dp, f), encoding='utf-8', errors='replace').read()
                except OSError:
                    texts[rel] = ''
    live = lambda rel: '/_archive/' not in '/' + rel
    P = collections.defaultdict(list)
    info = []
    for rel, t in texts.items():
        if not live(rel):
            continue
        # 죽은 링크는 --layer 와 무관하게 전체를 본다. cortex 밖(..), 절대 경로, refs/ 원문, 코드 안 링크는 cortex 가 소유한 링크가 아니라 제외한다.
        if '/refs/' not in '/' + rel:
            for m in LINK_RE.finditer(PROTECT_FENCE.sub('', t)):
                tgt = m.group(1).split('#')[0]
                if not tgt or tgt.startswith(('http:', 'https:', 'mailto:')) or os.path.isabs(tgt) or not tgt.endswith(EXTS):
                    continue
                norm = os.path.normpath(os.path.join(os.path.dirname(rel), tgt)).replace(os.sep, '/')
                if norm.startswith('..') or norm in files:
                    continue
                P['죽은 링크'].append('%s -> %s' % (rel, tgt))
        if sel(rel) and '/refs/' not in '/' + rel:
            scan = PROTECT_RE.sub('', t)
            for ch, name in FORBID.items():
                n = scan.count(ch)
                if n:
                    P['금지 문자'].append('%s %s x%d' % (rel, name, n))
        if sel(rel) and is_index(rel) and rel not in ('registry.md', '.pending.md'):
            ls = t.splitlines()
            entry_lines = [l for l in ls if l.lstrip().startswith('- ')]
            firsts = {FIRST_MD.search(l).group(0) for l in entry_lines if FIRST_MD.search(l)}
            items = len(firsts) or len(entry_lines)
            over = [x for x, c in (('항목 %d' % items, items > 60), ('%d줄' % len(ls), len(ls) > 200), ('%d자' % len(t), len(t) > 10000)) if c]
            if over:
                P['인덱스 임계 초과(§5)'].append('%s (%s)' % (rel, ', '.join(over)))
            if '/scripts/' in '/' + rel:
                miss = [i + 1 for i, l in enumerate(ls) if re.match(r'^\s*-\s*\[', l) and not all(k in l for k in ('왜', '언제', '어떻게', '결과'))]
                if miss:
                    P['스크립트 등록 4요소 누락'].append('%s 줄 %s' % (rel, ','.join(map(str, miss[:12]))))
            else:
                longl = [i + 1 for i, l in enumerate(ls) if len(l) > LINE_MAX]
                if longl:
                    P['인덱스 줄 400자 넘음(§5 참고 수치)'].append('%s 줄 %s' % (rel, ','.join(map(str, longl[:12]))))
        if sel(rel) and re.fullmatch(r'(common|(projects|stacks)/[^/]+)/INDEX[.]md', rel):
            cap = 3000
            if rel.startswith('projects/'):
                cap = 2500   # thalamus 가 세션 시작에 싣는 상한(ORIENT_INDEX) - 넘으면 뒷줄이 안 보인다
            if len(t) > cap:
                info.append('레이어 INDEX %s %d자 (목표 %s)' % (rel, len(t), format(cap, ',')))
    # 떠오르지 않는 lesson: 어느 레이어의 검색 대상 인덱스에도 첫 링크로 안 걸린 lesson. 옮기기가 다른 레이어를 고아로 만들므로 이것도 전체를 본다.
    # 단 레이어 루트 dormant.md 의 줄이 첫 링크로 가리키는 lesson 은 forget.py 가 인덱스 줄만 숨긴 잠재 기억이다(본문이 남아 recall.sh 본문 검색으로 찾히고 다시 쓰이면 되살아난다).
    primary = collections.Counter()
    for rel, t in texts.items():
        if live(rel) and is_grep_target(rel):
            for line in t.splitlines():
                m = FIRST_MD.search(line)
                if m:
                    primary[os.path.normpath(os.path.join(os.path.dirname(rel), m.group(0)[2:-1])).replace(os.sep, '/')] += 1
    dormant = collections.Counter()
    for rel, t in texts.items():
        if live(rel) and DORMANT_RE.fullmatch(rel):
            for line in t.splitlines():
                m = FIRST_MD.search(line)
                if m:
                    dormant[os.path.normpath(os.path.join(os.path.dirname(rel), m.group(0)[2:-1])).replace(os.sep, '/')] += 1
    latent = 0
    for rel in texts:
        if live(rel) and '/lessons/' in '/' + rel and primary.get(rel, 0) == 0:
            if dormant.get(rel, 0) > 0:
                latent += 1
            else:
                P[NO_PRIMARY].append(rel)
    if latent:
        info.append('잠재 기억 %d개' % latent)
    for rel, t in texts.items():
        if sel(rel) and live(rel) and '/phases/' in '/' + rel:
            if not t.startswith('# 단계 카드:') or '- 트리거:' not in t or '채택 시' not in t:
                P['단계 카드 형식'].append(rel)
            if '](phases/%s)' % os.path.basename(rel) not in texts.get(layer_of(rel) + '/INDEX.md', ''):
                P['레이어 INDEX 에 카드 줄 없음'].append(rel)
    if 'all' in layers or 'global' in layers:
        slugs, stacks = dirs_in(nb, 'projects'), dirs_in(nb, 'stacks')
        reg = texts.get('registry.md', '')
        rows = [l for l in reg.splitlines() if l.startswith('|')]
        for l in rows[2:]:
            c = l.split('|')
            if len(c) < 7 or not re.match(r'^(/|[A-Za-z]:[\\/])', c[1].strip().strip('`')):   # /..., C:/..., C:\...
                P['registry 형식'].append(l[:80])
                continue
            slug, stack = c[2].strip().strip('`'), c[3].strip().strip('`')
            note = '|'.join(c[5:-1]).strip()
            if len(note) > 500:
                P['registry 비고 500자 넘음(§5 참고 수치)'].append('%s %d자' % (slug, len(note)))
            if slug not in slugs:
                P['registry 슬러그 폴더 없음'].append(slug or '(빈 칸)')
            if stack not in ('', '-', '?') and stack not in stacks:   # '?' = 자동 등록이 스택을 못 정한 자리
                P['registry 스택 폴더 없음'].append(stack)
        for need in FIXED_FILES:
            if need not in files:
                P['경로 고정 파일 없음'].append(need)
        hr = texts.get('common/harness-routing.md', '')
        m = re.search(r'^checked_version:[ \t]*(\S+)[ \t]*$', hr, re.M)
        if not m or not re.fullmatch(r'claude-code_\S+', m.group(1)):
            P['harness-routing checked_version 형식'].append('common/harness-routing.md')
        nums = set(re.findall(r'^[|] *([0-9]+) *[|]', hr, re.M))
        for need in ('1', '2', '4', '6', '8', '12'):
            if need not in nums:
                P['harness-routing 표 번호 누락'].append('#' + need)
        for sec in ('## 3. [깨짐] 기록', '## 5. 실측 기록'):
            if sec not in hr:
                P['harness-routing 절 누락'].append(sec)
    # 단계 카드의 제목,트리거 줄 형식은 스크립트가 읽지 않고 세션의 모델이 읽으므로 참고로 둔다. 카드 파일 존재(죽은 링크)와 INDEX 링크만 파손이다.
    LEVEL = {
        '파손': ('registry 형식', '경로 고정 파일 없음', 'registry 슬러그 폴더 없음', 'registry 스택 폴더 없음', 'harness-routing checked_version 형식', 'harness-routing 표 번호 누락', 'harness-routing 절 누락', '레이어 INDEX 에 카드 줄 없음'),
        '인출 불가': ('죽은 링크', NO_PRIMARY),
    }
    lv = lambda k: next((n for n, ks in LEVEL.items() if k in ks), '참고')
    hard = sum(len(v) for k, v in P.items() if lv(k) != '참고')
    print('== check %s - 파손,인출 불가 %d건, 참고 %d건' % (' '.join(layers), hard, sum(len(v) for k, v in P.items() if lv(k) == '참고')))
    for level in ('파손', '인출 불가', '참고'):
        for k, v in P.items():
            if lv(k) != level:
                continue
            print('## [%s] %s (%d)' % (level, k, len(v)))
            for x in v[:100]:
                print('  -', x)
            if len(v) > 100:
                print('  ... 외 %d' % (len(v) - 100))
    for x in info:
        print('(참고)', x)
    return 1 if hard else 0


if __name__ == '__main__':
    sys.exit(main())
