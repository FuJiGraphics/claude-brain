#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""홍보 영상 녹화 - 헤드리스 Chrome 의 화면 전송(Page.startScreencast)을 받아 프레임으로 저장하고 30fps 목록을 만든다.
사용: record.py <promo 주소> <출력 폴더>   → <출력>/f/*.jpg, <출력>/frames.txt
표준 라이브러리만 쓴다(DevTools 웹소켓을 직접 다룬다). 인코딩은 encode.swift 가 한다."""
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.request

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
PORT = 9334
FPS = 30


class WS:
    def __init__(self, url):
        hostport, path = url[5:].split('/', 1)
        host, port = hostport.split(':')
        self.s = socket.create_connection((host, int(port)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(('GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                        'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n' % (path, hostport, key)).encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            buf += self.s.recv(4096)
        self.buf = buf.split(b'\r\n\r\n', 1)[1]
        self.id = 0

    def _recv(self, n):
        while len(self.buf) < n:
            d = self.s.recv(1 << 20)
            if not d:
                raise EOFError
            self.buf += d
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self):
        msg = b''
        while True:
            h = self._recv(2)
            fin, ln = h[0] & 0x80, h[1] & 0x7f
            if ln == 126:
                ln = struct.unpack('>H', self._recv(2))[0]
            elif ln == 127:
                ln = struct.unpack('>Q', self._recv(8))[0]
            msg += self._recv(ln)
            if fin:
                return json.loads(msg.decode('utf-8'))

    def post(self, method, params=None):
        self.id += 1
        data = json.dumps({'id': self.id, 'method': method, 'params': params or {}}).encode()
        n = len(data)
        hdr = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack('>H', n) if n < 65536
                               else bytes([0x80 | 127]) + struct.pack('>Q', n))
        mask = os.urandom(4)
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))
        return self.id

    def call(self, method, params=None):
        i = self.post(method, params)
        while True:
            m = self.recv()
            if m.get('id') == i:
                return m


def evaluate(ws, expr):
    r = ws.call('Runtime.evaluate', {'expression': expr, 'returnByValue': True})
    return r.get('result', {}).get('result', {}).get('value')


def main():
    url, out = sys.argv[1], os.path.abspath(sys.argv[2])
    fdir = os.path.join(out, 'f')
    shutil.rmtree(fdir, ignore_errors=True)
    os.makedirs(fdir)
    prof = os.path.join(out, 'chrome-prof')
    shutil.rmtree(prof, ignore_errors=True)
    ch = subprocess.Popen([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--force-color-profile=srgb',
                           '--remote-debugging-port=%d' % PORT, '--user-data-dir=' + prof, '--window-size=1280,720', 'about:blank'],
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
        ws.call('Emulation.setDeviceMetricsOverride', {'width': 1280, 'height': 720, 'deviceScaleFactor': 1.5, 'mobile': False})
        ws.call('Page.navigate', {'url': url})
        end = time.time() + 120
        while not evaluate(ws, 'window.__ready === true'):
            if time.time() > end:
                raise SystemExit('준비 시간 초과: ' + str(evaluate(ws, 'window.__error')))
            time.sleep(0.3)
        time.sleep(1.0)   # 글꼴, 첫 애니메이션이 자리 잡게
        ws.call('Page.startScreencast', {'format': 'jpeg', 'quality': 88, 'maxWidth': 1920, 'maxHeight': 1080, 'everyNthFrame': 1})
        go_id = ws.post('Runtime.evaluate', {'expression': 'window.__go = true'})
        frames, check_id, last_check, done = [], None, time.time(), False
        while not done:
            m = ws.recv()
            if m.get('method') == 'Page.screencastFrame':
                p = m['params']
                fn = os.path.join(fdir, '%06d.jpg' % len(frames))
                with open(fn, 'wb') as f:
                    f.write(base64.b64decode(p['data']))
                frames.append((p['metadata']['timestamp'], fn))
                ws.post('Page.screencastFrameAck', {'sessionId': p['sessionId']})
            elif check_id is not None and m.get('id') == check_id:
                v = m.get('result', {}).get('result', {}).get('value')
                check_id = None
                if v:
                    done = True
            if check_id is None and time.time() - last_check > 0.8:
                check_id = ws.post('Runtime.evaluate', {'expression': 'window.__done === true', 'returnByValue': True})
                last_check = time.time()
        ws.call('Page.stopScreencast')
        err = evaluate(ws, 'window.__error || ""')
        if err:
            print('연출 오류:', err)
        # 일정한 30fps 로 펴기 - 각 출력 시각에 그 시각까지 온 마지막 프레임
        t0, t1 = frames[0][0], frames[-1][0]
        seq, k = [], 0
        n = int((t1 - t0) * FPS) + 1
        for i in range(n):
            t = t0 + i / FPS
            while k + 1 < len(frames) and frames[k + 1][0] <= t:
                k += 1
            seq.append(frames[k][1])
        with open(os.path.join(out, 'frames.txt'), 'w') as f:
            f.write('\n'.join(seq))
        print('프레임 %d장 받음, %.1f초, 출력 %d프레임' % (len(frames), t1 - t0, n))
    finally:
        ch.terminate()
        shutil.rmtree(prof, ignore_errors=True)


if __name__ == '__main__':
    main()
