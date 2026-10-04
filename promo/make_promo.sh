#!/bin/bash
# 홍보 영상 만들기 - 가상의 데모 뇌로 앱을 띄워 자동 시연을 녹화하고 1080p MP4 로 묶는다. 실제 기억(cortex)은 건드리지 않는다.
# 사용법: bash promo/make_promo.sh [언어 ko|en|ja|zh] [출력 폴더]   (기본 ko, ~/Desktop/brain-promo)
#   만드는 것: brain-promo-<언어>.mp4 (1080p), brain-promo-<언어>-720p.mp4 (README 링크용, 10MB 아래),
#             brain-promo-<언어>-preview.gif (README 에 바로 보이는 움직이는 미리보기), brain-promo-<언어>-poster.jpg
# 필요: macOS, Google Chrome, python3, swift(Xcode 명령행 도구), claude CLI(데모 뇌의 말풍선, 쉬운 말 풀이, 물어보기를 Haiku 로 만든다 - 몇 센트)
set -eu
BRAIN="$(cd "$(dirname "$0")/.." && pwd)"
LANGX="${1:-ko}"
case "$LANGX" in ko|en|ja|zh) ;; *) echo "언어는 ko, en, ja, zh 중 하나"; exit 2 ;; esac
OUTDIR="${2:-$HOME/Desktop/brain-promo}"; mkdir -p "$OUTDIR"
OUT="$OUTDIR/brain-promo-$LANGX.mp4"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/brain-promo.XXXXXX")"
PORT=7459
SRV=''
trap 'kill ${SRV:-} 2>/dev/null || true; rm -rf "$WORK"' EXIT

echo "1/5 데모 뇌 만들기"
python3 "$BRAIN/promo/make_demo.py" "$WORK/demo" --lang "$LANGX" >/dev/null
export BRAIN_CORTEX="$WORK/demo/cortex" BRAIN_ACTIVE="$WORK/demo/active" BRAIN_PERSONA_DIR="$WORK/demo/persona"
export BRAIN_EDITOR_DRYRUN=1 BRAIN_EDITOR_FAKEAI=0 BRAIN_EDITOR_PROMO=1   # 동작은 흉내만, AI 는 진짜

echo "2/5 데모 서버 띄우기"
python3 "$BRAIN/editor/server.py" --port $PORT --no-state > "$WORK/server.log" 2>&1 &
SRV=$!
for _ in $(seq 50); do grep -q 't=' "$WORK/server.log" 2>/dev/null && break; sleep 0.1; done
T="$(grep -o 't=[A-Za-z0-9_-]*' "$WORK/server.log" | head -1 | cut -c3-)"

echo "3/5 말풍선, 쉬운 말 미리 만들기 (Haiku)"
python3 - "$PORT" "$T" "$LANGX" <<'PY'
import json, sys, time, urllib.request, concurrent.futures as cf
port, tok, lang = sys.argv[1], sys.argv[2], sys.argv[3]
get = lambda p: json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%s%s' % (port, p), headers={'X-Brain-Token': tok}), timeout=200))
for slug in ('pixel-quest', 'cafe-order-api', 'habit-tracker'):
    get('/api/topics?l=projects/%s&force=1&lang=%s' % (slug, lang))
for slug in ('pixel-quest', 'cafe-order-api', 'habit-tracker'):
    for _ in range(90):
        if get('/api/topics?l=projects/%s&lang=%s' % (slug, lang))['status'] != 'running':
            break
        time.sleep(2)
mems = get('/api/layer?l=projects/pixel-quest')['memories']
with cf.ThreadPoolExecutor(4) as ex:
    list(ex.map(lambda m: get('/api/explain?lang=%s&p=%s' % (lang, urllib.request.quote(m['path']))), mems))
print('   주제:', [t['label'] for t in get('/api/topics?l=projects/pixel-quest&lang=%s' % lang)['topics']])
PY

echo "4/5 녹화"
python3 "$BRAIN/promo/record.py" "http://127.0.0.1:$PORT/promo/index.html?t=$T&lang=$LANGX" "$WORK/rec"

echo "5/5 MP4 로 묶기"
swift "$BRAIN/promo/encode.swift" "$WORK/rec/frames.txt" "$OUT" 1920 1080 30 6000000
SMALL="${OUT%.mp4}-720p.mp4"   # README 링크용 - GitHub 무료 계정 동영상 첨부 상한 10MB 아래
swift "$BRAIN/promo/encode.swift" "$WORK/rec/frames.txt" "$SMALL" 1280 720 30 1100000
# README 에 바로 보이는 미리보기(GIF) - 말풍선, 쉬운 말, 피드백, 물어보기 장면. GitHub README 는 저장소의 동영상을 재생하지 않는다
swift "$BRAIN/promo/preview.swift" "$SMALL" "${OUT%.mp4}-preview.gif" "${PREVIEW_W:-640}" "${PREVIEW_FPS:-6}" 9.5 41
swift "$BRAIN/promo/preview.swift" "$OUT" "$WORK/poster.png" 1280 1 11.8 12.5 >/dev/null
sips -s format jpeg -s formatOptions 85 "$WORK/poster.png" --out "${OUT%.mp4}-poster.jpg" >/dev/null
echo "완성: $OUTDIR (언어 $LANGX)"; ls -la "$OUTDIR" | grep "promo-$LANGX" | awk '{print "  " $5 "  " $9}'
