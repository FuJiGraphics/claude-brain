#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""README 스크린샷 - 데모 서버에 뜬 앱을 헤드리스 Chrome 으로 장면마다 찍고, 네 장을 한 장으로 묶는다.
사용: shoot.py <앱 주소(?t=토큰)> <출력 폴더> <언어>
  → <출력>/<언어>-home.png, -brain.png, -explain.png, -ask.png, -persona.png (폰 화면 450x900, 2배 해상도)
  → <출력>/brain-shots-<언어>.png (뇌, 쉬운 말, 물어보기, 성격 네 장과 설명 글을 가로로 묶은 것 - README 맨 위에 쓴다)
make_shots.sh 가 데모 뇌, 서버, Haiku 미리 만들기를 마친 뒤 부른다. 표준 라이브러리만 쓴다(record.py 의 웹소켓을 쓴다)."""
import base64
import html
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from record import CHROME, WS, evaluate  # noqa: E402

PORT = 9335
CAPTIONS = {
    'ko': [('프로젝트마다 자라는 뇌', '말풍선은 이 뇌가 아끼는 것이에요'), ('AI 메모를 쉬운 말로', '왜 기억하는지, 언제 떠올리는지'),
           ('뇌에게 바로 물어보기', '기억 안에서만, 근거와 함께 답해요'), ('일하는 성격 정하기', '꼭! 규칙은 훅이 지켜요')],
    'en': [('A brain for every project', 'Bubbles show what it cares about'), ('AI notes in plain words', 'Why it remembers, when it recalls'),
           ('Ask your project\'s brain', 'Answers only from its memories, with sources'), ('Choose how Claude works', '"must!" rules are enforced by hooks')],
    'ja': [('プロジェクトごとに育つ脳', '吹き出しはこの脳が大事にしていること'), ('AI のメモをやさしい言葉で', 'なぜ覚えているか、いつ思い出すか'),
           ('脳にそのまま聞ける', '記憶の中だけで、根拠つきで答えます'), ('働き方の性格を決める', '「必ず!」のルールはフックが守ります')],
    'zh': [('每个项目都长出一个大脑', '气泡是这个大脑珍视的东西'), ('把 AI 笔记讲成大白话', '为什么记住、什么时候想起'),
           ('直接问问大脑', '只根据记忆回答,并附上依据'), ('决定 Claude 的工作方式', '“一定!”规则由钩子强制执行')],
}
ASK = {'ko': '세이브 구조 바꿀 때 조심할 거 있어?', 'en': 'Anything to watch out for when changing the save format?',
       'ja': 'セーブ形式を変えるとき、気をつけることある?', 'zh': '改存档格式时要注意什么?'}

# 장면: (이름, 준비 JS - 끝나면 true 를 돌려주는 식을 기다린다)
WAIT = 'await new Promise(r => setTimeout(r, %d));'


def until(ws, expr, sec=90):
    end = time.time() + sec
    while time.time() < end:
        if evaluate(ws, expr):
            return True
        time.sleep(0.3)
    return False


def run(ws, js):
    ws.call('Runtime.evaluate', {'expression': '(async () => {%s})()' % js, 'awaitPromise': True, 'returnByValue': True})


def shot(ws, path):
    data = ws.call('Page.captureScreenshot', {'format': 'png'})['result']['data']
    with open(path, 'wb') as f:
        f.write(base64.b64decode(data))


def main():
    url, out, lang = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3]
    os.makedirs(out, exist_ok=True)
    prof = os.path.join(out, '.chrome-prof')
    shutil.rmtree(prof, ignore_errors=True)
    ch = subprocess.Popen([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--force-color-profile=srgb',
                           '--remote-debugging-port=%d' % PORT, '--user-data-dir=' + prof, '--window-size=450,900', 'about:blank'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                page = next(t for t in json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % PORT)) if t['type'] == 'page')
                break
            except Exception:
                time.sleep(0.2)
        ws = WS(page['webSocketDebuggerUrl'])
        ws.call('Page.enable')
        ws.call('Emulation.setDeviceMetricsOverride', {'width': 450, 'height': 900, 'deviceScaleFactor': 2, 'mobile': False})
        ws.call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': 'light'}]})
        ws.call('Page.navigate', {'url': url})
        until(ws, "!!document.querySelector('#tabbar')", 20)
        run(ws, "localStorage.setItem('brainWelcomed','1'); localStorage.setItem('brainCoach','1'); localStorage.setItem('brainTheme','light');")
        ws.call('Page.navigate', {'url': url})
        names = []

        # 1. 홈
        until(ws, "document.querySelectorAll('.pet-tile').length >= 3", 30)
        time.sleep(1.6)
        shot(ws, os.path.join(out, '%s-home.png' % lang)); names.append('home')

        # 2. 뇌 (말풍선)
        run(ws, "location.hash = '#/p/projects/pixel-quest';")
        until(ws, "document.querySelectorAll('.bubble.on').length >= 3 && !document.querySelector('.bubble.ghost')", 120)
        time.sleep(2.2)
        shot(ws, os.path.join(out, '%s-brain.png' % lang)); names.append('brain')

        # 3. 쉬운 말 풀이 (최근 배운 것 첫 줄)
        run(ws, "document.querySelector('#recent .mem').click();")
        until(ws, "!!document.querySelector('.plain .pr') && document.querySelector('.fb .fq').textContent.length > 5", 120)
        time.sleep(1.4)
        shot(ws, os.path.join(out, '%s-explain.png' % lang)); names.append('explain')
        run(ws, "document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));" + WAIT % 500)

        # 4. 물어보기 (Haiku 가 실제로 답한다)
        run(ws, "document.querySelector('#aAsk').click();" + WAIT % 700)
        until(ws, "!!document.querySelector('#chatIn')", 10)
        run(ws, "const i = document.querySelector('#chatIn'); i.value = %s; document.querySelector('#chatGo').click();" % json.dumps(ASK[lang], ensure_ascii=False))
        until(ws, "document.querySelectorAll('.chat .msg:not(.me) .bb').length >= 2 && !document.querySelector('.typing')", 120)
        time.sleep(1.4)
        shot(ws, os.path.join(out, '%s-ask.png' % lang)); names.append('ask')
        run(ws, "document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));" + WAIT % 500)

        # 5. 성격 (부엉이)
        run(ws, "document.querySelector('#aPersona').click();" + WAIT % 900)
        until(ws, "!!document.querySelector('.breed')", 15)
        run(ws, "const b = [...document.querySelectorAll('.breed')].find(x => x.dataset.b === 'owl'); if (b) b.click();" + WAIT % 1200)
        until(ws, "!!document.querySelector('#canvas .node')", 15)
        time.sleep(1.2)
        run(ws, "document.querySelector('#toast').classList.remove('on');" + WAIT % 900)   # 품종 안내 토스트가 제목을 가리지 않게
        shot(ws, os.path.join(out, '%s-persona.png' % lang)); names.append('persona')

        # 묶음: 뇌, 쉬운 말, 물어보기, 성격
        cap = CAPTIONS[lang]
        cells = ''.join('<figure><img src="file://%s"><figcaption><b>%s</b><span>%s</span></figcaption></figure>' % (
            os.path.join(out, '%s-%s.png' % (lang, n)), html.escape(c[0]), html.escape(c[1]))
            for n, c in zip(['brain', 'explain', 'ask', 'persona'], cap))
        font = {'ko': "'Pretendard Variable', 'Apple SD Gothic Neo'", 'ja': "'Hiragino Sans'", 'zh': "'PingFang SC'", 'en': "'Helvetica Neue'"}[lang]
        page_html = ('<!doctype html><meta charset="utf-8"><style>'
                     'html,body{margin:0;background:#fff4ef}'
                     'body{display:flex;gap:28px;padding:36px 40px 30px;font-family:%s,system-ui,sans-serif;width:max-content}'
                     'figure{margin:0;width:330px;display:flex;flex-direction:column;align-items:center}'
                     'img{width:330px;height:660px;border-radius:30px;box-shadow:0 10px 30px rgba(120,60,40,.18),0 0 0 6px #fff;object-fit:cover;object-position:top}'
                     'figcaption{margin-top:18px;text-align:center;color:#3a2a30}'
                     'figcaption b{display:block;font-size:21px;letter-spacing:-.2px}'
                     'figcaption span{display:block;margin-top:5px;font-size:14.5px;color:#8a7178}'
                     '</style>%s' % (font, cells))
        gal = os.path.join(out, '.gallery-%s.html' % lang)
        with open(gal, 'w', encoding='utf-8') as f:
            f.write(page_html)
        ws.call('Emulation.setDeviceMetricsOverride', {'width': 1484, 'height': 800, 'deviceScaleFactor': 1.5, 'mobile': False})
        ws.call('Page.navigate', {'url': 'file://' + gal})
        until(ws, "[...document.images].every(i => i.complete)", 15)
        time.sleep(0.8)
        shot(ws, os.path.join(out, 'brain-shots-%s.png' % lang))
        os.remove(gal)
        print('  %s: %s, brain-shots-%s.png' % (lang, ', '.join(names), lang))
    finally:
        ch.terminate()
        shutil.rmtree(prof, ignore_errors=True)


if __name__ == '__main__':
    main()
