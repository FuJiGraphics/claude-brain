#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""데모 뇌(make_demo.py 의 한국어 원본)를 다른 언어로 옮겨 promo/demo/<언어>.json 에 둔다 - 영상마다 다시 번역하지 않게 저장소에 넣는다.
사용법: translate_demo.py en ja zh   (claude CLI 로 Haiku 를 부른다, 언어당 1회)"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'editor'))
import make_demo  # noqa: E402
import server  # noqa: E402

NAMES = {'en': 'English', 'ja': 'Japanese', 'zh': 'Simplified Chinese'}


def source():
    mem = {}
    for _, _, _, idx in make_demo.PROJECTS:
        for items in idx.values():
            for fn, title, kw, body, _ in items:
                mem[fn] = [title, kw, body]
    for items in list(make_demo.STACKS.values()) + [make_demo.COMMON]:
        for fn, title, kw, body, _ in items:
            mem[fn] = [title, kw, body]
    return {'memories': mem, 'notes': {slug: note for slug, _, note, _ in make_demo.PROJECTS},
            'journal': [j[2] for j in make_demo.JOURNAL]}


def main():
    src = source()
    for lang in sys.argv[1:]:
        prompt = ('Translate every Korean string in this JSON into natural %s that a developer would write in their own notes. '
                  'Keep the exact same JSON structure and keys. Keep code identifiers, file names, commands, product names and '
                  'anything inside backticks unchanged. Keep markdown bullets ("- ") and line breaks. Output only the JSON.\n\n%s') % (
            NAMES[lang], json.dumps(src, ensure_ascii=False, indent=0))
        out = server.json_in(server.haiku(prompt, 'You are a precise technical translator. Output JSON only.', timeout=300))
        missing = set(src['memories']) - set(out.get('memories', {}))
        if missing or len(out.get('journal', [])) != len(src['journal']):
            raise SystemExit('%s: 번역이 빠졌다 %s' % (lang, sorted(missing)[:5]))
        os.makedirs(os.path.join(HERE, 'demo'), exist_ok=True)
        with open(os.path.join(HERE, 'demo', lang + '.json'), 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(lang, len(out['memories']), '기억')


if __name__ == '__main__':
    main()
