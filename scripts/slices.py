#!/usr/bin/env python3
"""노트북 정비 조각 계산 - hippocampus 한 번의 실행이 담을 수 있는 크기로 노트북을 나눈다(agents/hippocampus.md §3).

사용법:
  python3 slices.py --nb <노트북> [--max-tok 40000] [--json]      조각 목록
  python3 slices.py --nb <노트북> --due <N> [--done-dir <.hippocampus/done>]   가장 오래 정비 안 된 조각 N개(JSON)
  python3 slices.py --make-requests <due.json> --registry <registry.md> --out <폴더> [--caller <이름>]
      --due 출력(due.json)의 조각마다 sweep 요청 JSON 을 <폴더>/req-NN.json 으로 쓴다(hippocampus-enqueue.sh 에 그대로 넣는다).
      키: mode(sweep), project_root(projects 레이어면 registry 에서 슬러그로 찾은 경로, 아니면 빈 문자열), slug(projects 레이어면 슬러그, 아니면 -),
          stack(stacks 레이어면 그 스택, projects 레이어면 registry 의 스택, common 이면 -), caller(기본 hippocampus-ctl-sweep), payload.slice({id, files, tok}).
      출력: 요청 파일마다 한 줄 - 경로, 조각 id, 토큰(탭으로 구분).

조각 = 검색 대상 인덱스 파일 하나(레이어 루트 INDEX.md, *index*.md, 카테고리 파일)와 그 줄의 첫 링크가 가리키는 본문들.
추정 토큰(1.40*한글 + 0.58*기타 + 4*줄)이 상한을 넘으면 같은 인덱스를 #2, #3 으로 나눈다. 어느 인덱스에도 안 걸린 본문은
레이어별 '(미등록)' 조각이 된다. 조각 id 는 '<레이어>:<인덱스 파일명>[#n]' 이라 노트북이 조금 바뀌어도 대체로 유지된다.
정비 이력은 큐 결과(done/*.request.json 의 payload.slice.id 와 done/*.json 의 status)에서 읽는다 - 별도 상태 파일 없음.
"""
import glob, json, os, re, sys, collections

FIRST_MD = re.compile(r'\]\([^() ]+\.md\)')
CATEGORY_RE = re.compile(r'^(gotchas|patterns|decisions|api-facts|infra)(-[a-z0-9-]+)?\.md$')


def arg(a, name, default=None):
    if name in a and a.index(name) + 1 < len(a):
        return a[a.index(name) + 1]
    return default


def tok(t):
    hg = sum(1 for ch in t if '가' <= ch <= '힣')
    return int(1.40 * hg + 0.58 * (len(t) - hg) + 4 * t.count('\n'))


def layers(nb):
    out = ['common'] if os.path.isdir(os.path.join(nb, 'common')) else []
    for top in ('stacks', 'projects'):
        for d in sorted(glob.glob(os.path.join(nb, top, '*'))):
            if os.path.isdir(d):
                out.append(top + '/' + os.path.basename(d))
    return out


def compute(nb, max_tok):
    slices = []
    for lay in layers(nb):
        root = os.path.join(nb, lay)
        idx_files = []
        for f in sorted(os.listdir(root)):
            if f.endswith('.md') and (f == 'INDEX.md' or 'index' in f or 'router' in f or f == 'dormant.md' or CATEGORY_RE.match(f)):
                idx_files.append(f)
        owned = set()
        bodies_all = set()
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in ('_archive', 'scripts', '__pycache__')]
            for f in fn:
                if f.endswith('.md'):
                    rel = os.path.relpath(os.path.join(dp, f), nb)
                    if os.path.dirname(rel) != lay or f not in idx_files:
                        bodies_all.add(rel)
        for f in idx_files:
            irel = lay + '/' + f
            t = open(os.path.join(nb, irel), encoding='utf-8', errors='replace').read()
            targets = []
            for line in t.splitlines():
                m = FIRST_MD.search(line)
                if not m:
                    continue
                r = os.path.normpath(os.path.join(lay, m.group(0)[2:-1]))
                if r in bodies_all and r not in owned and r not in targets:
                    targets.append(r)
            owned.update(targets)
            part, size, n = [irel], tok(t), 1
            for r in targets:
                c = tok(open(os.path.join(nb, r), encoding='utf-8', errors='replace').read())
                if len(part) > 1 and size + c > max_tok:
                    slices.append({'id': '%s:%s%s' % (lay, f, '' if n == 1 else '#%d' % n), 'layer': lay, 'files': part, 'tok': size})
                    n += 1
                    part, size = [irel], tok(t)
                part.append(r)
                size += c
            slices.append({'id': '%s:%s%s' % (lay, f, '' if n == 1 else '#%d' % n), 'layer': lay, 'files': part, 'tok': size})
        rest = sorted(bodies_all - owned)
        part, size, n = [], 0, 1
        for r in rest:
            c = tok(open(os.path.join(nb, r), encoding='utf-8', errors='replace').read())
            if part and size + c > max_tok:
                slices.append({'id': '%s:(미등록)#%d' % (lay, n), 'layer': lay, 'files': part, 'tok': size})
                n += 1
                part, size = [], 0
            part.append(r)
            size += c
        if part:
            slices.append({'id': '%s:(미등록)#%d' % (lay, n), 'layer': lay, 'files': part, 'tok': size})
    return slices


def last_swept(done_dir):
    last = {}
    for rq in glob.glob(os.path.join(done_dir, '*.request.json')):
        try:
            d = json.load(open(rq, encoding='utf-8'))
            sid = ((d.get('payload') or {}).get('slice') or {}).get('id')
            if d.get('mode') != 'sweep' or not sid:
                continue
            res = json.load(open(rq.replace('.request.json', '.json'), encoding='utf-8'))
            if res.get('status') in ('done', 'partial'):
                last[sid] = max(last.get(sid, ''), res.get('finished_at', ''))
        except Exception:
            continue
    return last


def read_registry(path):
    """[registry 표 읽기]
    - 슬러그 -> (프로젝트 경로, 스택) 사전. 표의 칸은 `| 경로 | 슬러그 | 스택 | 스택 버전 | 비고 |` 순이다
    - 첫 `|` 두 줄(머리, 구분선)은 건너뛴다. 스택 칸이 비었으면 -
    """
    rows = {}
    with open(path, encoding='utf-8') as f:
        lines = [l for l in f.read().splitlines() if l.startswith('|')]
    for l in lines[2:]:
        c = l.split('|')
        if len(c) < 5:
            continue
        root, slug, stack = (x.strip().strip('`') for x in c[1:4])
        if slug:
            rows[slug] = (root, stack or '-')
    return rows


def make_requests(due_path, registry_path, out_dir, caller):
    """[sweep 요청 JSON 쓰기]
    - due.json 의 조각마다 <out_dir>/req-NN.json 을 쓰고 경로, 조각 id, 토큰을 한 줄씩 출력한다
    """
    with open(due_path, encoding='utf-8') as f:
        due = json.load(f)
    reg = read_registry(registry_path)
    os.makedirs(out_dir, exist_ok=True)
    for i, s in enumerate(due, 1):
        layer = s.get('layer') or s['id'].split(':', 1)[0]
        root, slug, stack = '', '-', '-'
        if layer.startswith('projects/'):
            slug = layer.split('/', 1)[1]
            if slug in reg:
                root, stack = reg[slug]
            else:
                sys.stderr.write('경고: registry 에 없는 슬러그 %s - project_root 를 비운다\n' % slug)
        elif layer.startswith('stacks/'):
            stack = layer.split('/', 1)[1]
        req = {
            'mode': 'sweep', 'project_root': root, 'slug': slug, 'stack': stack, 'caller': caller,
            'payload': {'slice': {'id': s['id'], 'files': s['files'], 'tok': s['tok']}},
        }
        path = os.path.join(out_dir, 'req-%02d.json' % i)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(req, f, ensure_ascii=False, indent=1)
        print('%s\t%s\t%d' % (path, s['id'], s['tok']))
    return 0


def main():
    a = sys.argv[1:]
    if '--make-requests' in a:
        due, reg, out = arg(a, '--make-requests'), arg(a, '--registry'), arg(a, '--out')
        if not (due and reg and out):
            print(__doc__)
            return 2
        return make_requests(due, reg, out, arg(a, '--caller', 'hippocampus-ctl-sweep'))
    nb = arg(a, '--nb')
    if not nb:
        print(__doc__)
        return 2
    nb = os.path.abspath(os.path.expanduser(nb))
    sl = compute(nb, int(arg(a, '--max-tok', '40000')))
    if '--due' in a:
        last = last_swept(arg(a, '--done-dir', os.path.join(nb, '.hippocampus', 'done')))
        sl.sort(key=lambda s: (last.get(s['id'], ''), s['id']))
        print(json.dumps(sl[:int(arg(a, '--due'))], ensure_ascii=False))
        return 0
    if '--json' in a:
        print(json.dumps(sl, ensure_ascii=False))
        return 0
    by = collections.Counter(s['layer'] for s in sl)
    print('조각 %d개, 최대 %d 토큰' % (len(sl), max(s['tok'] for s in sl)))
    for k, v in by.items():
        print('  %s %d' % (k, v))
    return 0


if __name__ == '__main__':
    sys.exit(main())
