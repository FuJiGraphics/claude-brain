#!/bin/bash
# README 스크린샷 만들기 - 홍보 영상과 같은 가상의 데모 뇌로 앱을 띄워 장면마다 찍는다. 실제 기억(cortex)은 건드리지 않는다.
# 사용법: bash promo/make_shots.sh [언어 ko|en|ja|zh] [출력 폴더]   (기본 ko, ~/Desktop/brain-promo)
#   만드는 것: <언어>-home.png, -brain.png, -explain.png, -ask.png, -persona.png, brain-shots-<언어>.png(네 장 묶음)
# 필요: macOS 또는 Linux 의 Google Chrome, python3, claude CLI(말풍선, 쉬운 말, 물어보기를 Haiku 로 만든다 - 몇 센트)
set -eu
BRAIN="$(cd "$(dirname "$0")/.." && pwd)"
LANGX="${1:-ko}"
case "$LANGX" in ko|en|ja|zh) ;; *) echo "언어는 ko, en, ja, zh 중 하나"; exit 2 ;; esac
OUTDIR="${2:-$HOME/Desktop/brain-promo}"; mkdir -p "$OUTDIR"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/brain-shots.XXXXXX")"
PORT=7463
SRV=''
trap 'kill ${SRV:-} 2>/dev/null || true; rm -rf "$WORK"' EXIT

echo "1/3 데모 뇌, 데모 서버"
python3 "$BRAIN/promo/make_demo.py" "$WORK/demo" --lang "$LANGX" >/dev/null
export BRAIN_CORTEX="$WORK/demo/cortex" BRAIN_ACTIVE="$WORK/demo/active" BRAIN_PERSONA_DIR="$WORK/demo/persona"
export BRAIN_EDITOR_DRYRUN=1 BRAIN_EDITOR_FAKEAI=0   # 동작은 흉내만, AI 는 진짜
rm -f "$WORK/demo/persona/pixel-quest.json"          # 성격 장면은 빈 캔버스에서 부엉이를 고르는 모습으로
python3 "$BRAIN/editor/server.py" --port $PORT --no-state > "$WORK/server.log" 2>&1 &
SRV=$!
for _ in $(seq 50); do grep -q 't=' "$WORK/server.log" 2>/dev/null && break; sleep 0.1; done
T="$(grep -o 't=[A-Za-z0-9_-]*' "$WORK/server.log" | head -1 | cut -c3-)"

echo "2/3 말풍선, 쉬운 말 미리 만들기 (Haiku)"
python3 - "$PORT" "$T" "$LANGX" <<'PY'
import json, sys, time, urllib.request, concurrent.futures as cf
port, tok, lang = sys.argv[1], sys.argv[2], sys.argv[3]
get = lambda p: json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%s%s' % (port, p), headers={'X-Brain-Token': tok}), timeout=200))
get('/api/topics?l=projects/pixel-quest&force=1&lang=%s' % lang)
for _ in range(90):
    if get('/api/topics?l=projects/pixel-quest&lang=%s' % lang)['status'] != 'running':
        break
    time.sleep(2)
mems = get('/api/layer?l=projects/pixel-quest')['recent'][:3]
with cf.ThreadPoolExecutor(3) as ex:
    list(ex.map(lambda m: get('/api/explain?lang=%s&p=%s' % (lang, urllib.request.quote(m['path']))), mems))
PY

echo "3/3 찍기"
python3 "$BRAIN/promo/shoot.py" "http://127.0.0.1:$PORT/?t=$T" "$OUTDIR" "$LANGX"
echo "완성: $OUTDIR"
