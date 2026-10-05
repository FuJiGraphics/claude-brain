#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hippocampus 지침에서 이번 모드에 필요한 절만 뽑아 표준 출력으로 낸다 - 데몬이 --append-system-prompt 로 싣는다.
사용법: hippocampus-brief.py <hippocampus.md> <mode>
- 공통 절(머리, §0, 지켜야 하는 것, 큐 실행 형태, 입력, 문체, §6, §7, 돌려줄 것)은 늘 싣고, 모드 절(§1~§5)은 MODE_SECTIONS 대로 고른다.
- 턴마다 컨텍스트 전체를 다시 읽으므로 안 쓰는 절을 빼면 그만큼 매 턴 비용이 준다. 원본은 하나로 두고(사람이 고치는 곳) 여기서 자르기만 한다.
- 모르는 모드거나 절 제목을 못 찾으면 원본 전체를 낸다(빠뜨려서 틀리는 것보다 비싼 쪽이 낫다).
"""
import re
import sys

# 모드 절 제목의 번호 -> 그 절을 싣는 모드. 여기 없는 '## ' 절은 공통이다
MODE_SECTIONS = {
    '1.': ('register',),
    '1b.': ('harness-refresh',),
    '2.': ('record', 'replay', 'targeted', 'sweep'),
    '2b.': ('replay',),
    '3.': ('targeted', 'sweep'),
    '4.': ('sweep',),
    '5.': ('record', 'replay', 'targeted', 'sweep'),
}
MODES = ('register', 'harness-refresh', 'record', 'replay', 'targeted', 'sweep')


def brief(text, mode):
    if mode not in MODES:
        return text
    parts = re.split(r'(?m)^(?=## )', text)
    out, found = [], set()
    for p in parts:
        m = re.match(r'## ([0-9]+b?\.) ', p)
        if m and m.group(1) in MODE_SECTIONS:
            found.add(m.group(1))
            if mode not in MODE_SECTIONS[m.group(1)]:
                continue
        out.append(p)
    if found != set(MODE_SECTIONS):
        return text
    return ''.join(out)


if __name__ == '__main__':
    src, mode = sys.argv[1], sys.argv[2]
    sys.stdout.write(brief(open(src, encoding='utf-8').read(), mode))
    try:   # 기억 언어 절 - 대화 언어로 쓰고, 모를 때만 설정 언어(lang.py)
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import lang
        sys.stdout.write(lang.brief())
    except Exception:
        pass
