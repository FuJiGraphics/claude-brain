#!/bin/bash
# 홍보 영상 만들기 - 가상의 데모 뇌로 앱을 띄워 자동 시연을 녹화하고 1080p MP4 로 묶는다. 실제 기억(cortex)은 건드리지 않는다.
# 사용법: bash promo/make_promo.sh [출력 mp4 경로]   (기본 ~/Desktop/brain-promo.mp4)
# 필요: macOS, Google Chrome, python3, swift(Xcode 명령행 도구), claude CLI(데모 뇌의 말풍선, 쉬운 말 풀이, 물어보기를 Haiku 로 만든다 - 몇 센트)
set -eu
BRAIN="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$HOME/Desktop/brain-promo.mp4}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/brain-promo.XXXXXX")"
PORT=7459
SRV=''
trap 'kill ${SRV:-} 2>/dev/null || true; rm -rf "$WORK"' EXIT

echo "1/5 데모 뇌 만들기"
python3 "$BRAIN/promo/make_demo.py" "$WORK/demo" >/dev/null
export BRAIN_CORTEX="$WORK/demo/cortex" BRAIN_ACTIVE="$WORK/demo/active" BRAIN_PERSONA_DIR="$WORK/demo/persona"
export BRAIN_EDITOR_DRYRUN=1 BRAIN_EDITOR_FAKEAI=0 BRAIN_EDITOR_PROMO=1   # 동작은 흉내만, AI 는 진짜

echo "2/5 데모 서버 띄우기"
python3 "$BRAIN/editor/server.py" --port $PORT --no-state > "$WORK/server.log" 2>&1 &
SRV=$!
for _ in $(seq 50); do grep -q 't=' "$WORK/server.log" 2>/dev/null && break; sleep 0.1; done
T="$(grep -o 't=[A-Za-z0-9_-]*' "$WORK/server.log" | head -1 | cut -c3-)"

echo "3/5 말풍선, 쉬운 말 미리 만들기 (Haiku)"
python3 - "$PORT" "$T" <<'PY'
import json, sys, time, urllib.request, concurrent.futures as cf
port, tok = sys.argv[1], sys.argv[2]
get = lambda p: json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%s%s' % (port, p), headers={'X-Brain-Token': tok}), timeout=200))
for slug in ('pixel-quest', 'cafe-order-api', 'habit-tracker'):
    get('/api/topics?l=projects/%s&force=1' % slug)
for slug in ('pixel-quest', 'cafe-order-api', 'habit-tracker'):
    for _ in range(90):
        if get('/api/topics?l=projects/%s' % slug)['status'] != 'running':
            break
        time.sleep(2)
mems = get('/api/layer?l=projects/pixel-quest')['memories']
with cf.ThreadPoolExecutor(4) as ex:
    list(ex.map(lambda m: get('/api/explain?p=' + urllib.request.quote(m['path'])), mems))
print('   주제:', [t['label'] for t in get('/api/topics?l=projects/pixel-quest')['topics']])
PY

echo "4/5 녹화"
python3 "$BRAIN/promo/record.py" "http://127.0.0.1:$PORT/promo/index.html?t=$T" "$WORK/rec"

echo "5/5 MP4 로 묶기"
swift "$BRAIN/promo/encode.swift" "$WORK/rec/frames.txt" "$OUT" 1920 1080 30 6000000
SMALL="${OUT%.mp4}-small.mp4"   # README 첨부용 - GitHub 무료 계정 동영상 첨부 상한 10MB 아래
swift "$BRAIN/promo/encode.swift" "$WORK/rec/frames.txt" "$SMALL" 1280 720 30 1100000
echo "완성: $OUT ($(du -h "$OUT" | cut -f1)), $SMALL ($(du -h "$SMALL" | cut -f1))"
