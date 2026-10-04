#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""홍보 영상용 가상의 데모 뇌를 만든다 - 실제 기억(cortex)과 완전히 분리된 폴더에.
사용법: make_demo.py <출력 폴더> [--lang ko|en|ja|zh]   → <출력>/cortex, <출력>/active, <출력>/persona
한국어가 원본이고, 다른 언어는 promo/demo/<언어>.json(translate_demo.py 가 만든 번역)으로 제목, 키워드, 본문, 설명, 일지를 바꾼다.
서버를 BRAIN_CORTEX=<출력>/cortex BRAIN_ACTIVE=<출력>/active BRAIN_PERSONA_DIR=<출력>/persona 로 띄우면 이 데모를 보여 준다."""
import json
import os
import shutil
import sys
import time

NOW = time.time()
DAY = 86400

# (슬러그, 스택, 설명, {색인 이름: [(파일, 제목, 키워드, 본문, 며칠 전)]})
PROJECTS = [
    ('pixel-quest', 'unity', '2D 픽셀 RPG. 턴제 전투, 인벤토리, 세이브가 핵심이다.', {
        'lessons-index-combat.md': [
            ('combat-turn-order-speed-stat', '턴 순서는 speed 스탯 내림차순, 같으면 파티원이 먼저다', '`TurnQueue.Build`, 동률 처리, 선공',
             '- `TurnQueue.Build` 가 speed 내림차순으로 줄을 세운다. 동률이면 파티원이 적보다 먼저다(사용자 결정 2026-09-12).\n- 동률 규칙을 바꾸면 보스전 밸런스 표가 전부 어긋난다.', 2),
            ('combat-crit-roll-uses-seeded-rng', '치명타 판정은 전투마다 시드 고정 난수를 쓴다 - UnityEngine.Random 금지', '`BattleRng`, 리플레이, 재현',
             '- `BattleRng(seed)` 하나로 치명타, 회피를 굴린다. `UnityEngine.Random` 을 섞으면 리플레이가 어긋난다(함정).\n- 시드는 `BattleContext.Seed` 에 있다.', 1),
            ('combat-status-effect-stack-cap', '상태이상 중첩은 최대 3이고 지속시간은 가장 긴 것으로 갱신한다', '`StatusEffect.Apply`, 독, 화상',
             '- 독, 화상은 3중첩까지. 넘치면 지속시간만 가장 긴 값으로 갱신한다.\n- 중첩 상한은 `StatusConfig.asset` 이 소유한다.', 4),
            ('combat-damage-formula-armor', '피해 공식은 공격력 x 배율 - 방어력 x 0.5, 최소 1', '`DamageCalc`, 방어력, 최소 피해',
             '- `DamageCalc.Compute` 가 소유한다. 최소 피해 1 은 기획 요구다.\n- 방어 관통 스킬은 0.5 계수만 0.2 로 바꾼다.', 9),
            ('combat-skill-cooldown-in-turns', '스킬 쿨다운은 초가 아니라 턴 단위다', '`SkillSlot.Cooldown`, 턴 종료',
             '- 쿨다운은 자기 턴이 끝날 때 1 줄어든다. 적 턴에는 줄지 않는다.', 12),
        ],
        'lessons-index-ui.md': [
            ('ui-dialogue-box-pixel-perfect', '대화창은 Pixel Perfect Camera 배율에 맞춰 9-slice 를 정수 배로만 늘린다', '`DialogueBox`, 9-slice, 번짐',
             '- 배율이 정수가 아니면 테두리 픽셀이 번진다(함정). `PixelPerfectCamera.assetsPPU` 는 16 이다.', 3),
            ('ui-inventory-grid-drag', '인벤토리 드래그는 슬롯 위 0.15초 머물러야 교환한다', '`InventoryGrid`, 드래그 앤 드롭, 오작동',
             '- 바로 교환하면 스크롤 중 오작동이 잦았다. 0.15초 지연은 사용자 요청이다.', 5),
            ('ui-font-korean-bitmap', '한글은 비트맵 폰트 Galmuri11 하나만 쓴다', '폰트, TextMeshPro, Galmuri',
             '- TMP 폰트 에셋 `Galmuri11 SDF` 를 쓴다. 다른 한글 폰트를 섞으면 줄 높이가 흔들린다.', 20),
            ('ui-hp-bar-tween', 'HP 바는 깎일 때 흰 잔상이 0.4초 뒤 따라간다', '`HpBar`, DOTween, 잔상',
             '- `HpBar.Damage` 가 앞 막대를 즉시, 흰 잔상을 0.4초 뒤에 줄인다.', 6),
        ],
        'lessons-index-save.md': [
            ('save-json-version-migration', '세이브는 JSON 이고 version 필드로 옛 세이브를 올린다', '`SaveSystem`, 마이그레이션, version',
             '- `SaveSystem.Load` 가 version 을 보고 `Migrations` 를 차례로 적용한다.\n- 필드를 지우지 말고 이름만 옮긴다 - 옛 세이브가 깨진다(사고 2026-09-20).', 1),
            ('save-autosave-on-scene-change', '자동 저장은 씬 전환 직전에만 한다 - 전투 중 저장 금지', '자동 저장, 씬 전환, 전투',
             '- 전투 중 저장하면 턴 큐가 반쯤 직렬화돼 불러올 때 터진다(함정).', 7),
            ('save-path-persistent-data', '세이브 위치는 persistentDataPath/saves/slot{n}.json', '저장 경로, 슬롯',
             '- 슬롯은 3개. 클라우드 동기화는 아직 없다.', 15),
        ],
        'lessons-index-build.md': [
            ('build-addressables-before-player', '플레이어 빌드 전에 Addressables 를 먼저 빌드해야 한다', 'Addressables, 빌드 순서, 리소스 누락',
             '- 순서를 바꾸면 실행은 되는데 몬스터 스프라이트가 비어 있다(함정).\n- `Tools/Build/All` 메뉴가 순서를 지킨다.', 2),
            ('build-steam-depot-upload', '스팀 업로드는 depot 2개 - 윈도우, 맥', 'Steamworks, depot, 배포',
             '- `steam_build/app_build.vdf` 를 쓴다. 맥 빌드는 공증 후 올린다.', 10),
            ('build-il2cpp-stripping', 'IL2CPP 코드 스트리핑이 리플렉션 쓰는 세이브 클래스를 지운다 - link.xml 필요', 'IL2CPP, link.xml, 스트리핑',
             '- `Assets/link.xml` 에 `SaveData` 네임스페이스를 남긴다. 빠지면 릴리스 빌드에서만 로드가 실패한다.', 3),
        ],
    }),
    ('cafe-order-api', 'node', '카페 주문 API 서버. Express + PostgreSQL, 결제는 토스페이먼츠.', {
        'lessons-index-db.md': [
            ('db-migration-knex-order', '마이그레이션은 knex 로만 하고 파일 이름 시각 순서로 돈다', 'knex, 마이그레이션, 순서',
             '- 수동 SQL 로 스키마를 바꾸면 다음 배포에서 마이그레이션이 충돌한다(사고 2026-09-02).', 3),
            ('db-order-status-enum', '주문 상태는 pending, paid, brewing, done, canceled 다섯 개', '주문 상태, enum, 취소',
             '- 상태 전이는 `OrderStateMachine` 하나가 소유한다. 직접 UPDATE 하지 않는다.', 6),
            ('db-connection-pool-size', '커넥션 풀은 10 - 서버리스로 옮기면 1 로 줄인다', 'pg pool, 커넥션',
             '- 풀이 크면 DB 최대 연결 수를 넘는다.', 11),
        ],
        'lessons-index-auth.md': [
            ('auth-jwt-refresh-rotation', '리프레시 토큰은 쓸 때마다 새로 발급하고 옛 것은 즉시 폐기한다', 'JWT, 리프레시 토큰, 회전',
             '- 재사용이 감지되면 그 사용자의 토큰을 전부 폐기한다(보안 결정).', 2),
            ('auth-staff-role', '직원 권한은 staff, owner 둘이고 환불은 owner 만 한다', '권한, 환불, owner',
             '- `requireRole("owner")` 미들웨어를 환불 라우트에 건다.', 8),
        ],
        'lessons-index-deploy.md': [
            ('deploy-fly-io-secrets', '배포는 fly.io, 비밀값은 fly secrets 로만 넣는다', 'fly.io, 배포, secrets, 환경변수',
             '- `.env` 를 이미지에 넣지 않는다. `fly secrets set` 을 쓴다.', 1),
            ('deploy-healthcheck-db', '헬스체크는 DB 핑까지 본다 - 안 그러면 죽은 인스턴스로 트래픽이 간다', '헬스체크, /health',
             '- `/health` 가 `SELECT 1` 을 돈다. 타임아웃 2초.', 4),
            ('deploy-payment-webhook-idempotent', '결제 웹훅은 paymentKey 로 멱등 처리한다', '토스페이먼츠, 웹훅, 중복 결제',
             '- 같은 웹훅이 두세 번 온다. `payments.payment_key` 유니크 제약으로 막는다(함정).', 2),
        ],
    }),
    ('habit-tracker', 'ios', '습관 기록 iOS 앱. SwiftUI + SwiftData.', {
        'lessons-index.md': [
            ('swiftdata-migration-plan', 'SwiftData 스키마를 바꿀 땐 VersionedSchema 와 마이그레이션 플랜을 같이 올린다', 'SwiftData, 마이그레이션',
             '- 빠뜨리면 업데이트한 사용자 앱이 시작하자마자 꺼진다(사고).', 5),
            ('widget-timeline-refresh', '위젯은 자정에 타임라인을 새로 만든다', 'WidgetKit, 타임라인, 자정',
             '- `.after(nextMidnight)` 정책을 쓴다.', 9),
            ('streak-timezone', '연속 기록은 사용자 시간대 기준 날짜로 센다', '연속 기록, 시간대',
             '- UTC 로 세면 해외 사용자의 연속 기록이 끊긴다(사용자 제보).', 3),
            ('haptics-on-check', '습관을 체크하면 가벼운 햅틱 하나 - 성공 햅틱은 쓰지 않는다', '햅틱, 피드백',
             '- 사용자 선호: 너무 요란하다는 피드백이 있었다.', 13),
        ],
    }),
    ('my-blog', '-', '개인 블로그. Astro 정적 사이트.', {}),
]
STACKS = {
    'unity': [
        ('unity-serializefield-rename', '직렬화 필드 이름을 바꿀 땐 FormerlySerializedAs 를 붙인다', 'FormerlySerializedAs, 인스펙터 값 유실',
         '- 안 붙이면 프리팹에 넣어 둔 값이 조용히 사라진다(함정).', 6),
        ('unity-coroutine-disabled-object', '비활성 오브젝트에서는 코루틴이 시작되지 않는다', 'StartCoroutine, 비활성',
         '- 꺼진 오브젝트에서 부르면 에러 없이 아무 일도 안 일어난다.', 14),
        ('unity-meta-files-commit', '.meta 파일은 반드시 같이 커밋한다', '.meta, GUID, 깨진 참조',
         '- 빠지면 다른 PC 에서 프리팹 참조가 전부 Missing 이 된다.', 20),
    ],
    'node': [
        ('node-esm-dirname', 'ESM 에는 __dirname 이 없다 - import.meta.url 로 만든다', 'ESM, __dirname',
         '- `fileURLToPath(new URL(".", import.meta.url))`', 10),
    ],
}
COMMON = [
    ('commit-message-korean', '커밋 메시지는 한국어로, 접두사는 feat, fix, refactor, chore', '커밋, 컨벤션',
     '- 사용자 결정. 한 커밋에는 한 가지 일만.', 9),
    ('ask-before-delete', '파일을 지우기 전에는 무엇이 사라지는지 먼저 말한다', '삭제, 확인',
     '- 사용자 선호.', 18),
]


def w(path, text, days=0):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    t = NOW - days * DAY - 600
    os.utime(path, (t, t))


def lesson(root, rel_dir, item):
    fn, title, kw, body, days = item
    w(os.path.join(root, rel_dir, 'lessons', fn + '.md'), '# %s\n\n%s\n' % (title, body), days)
    return '- [%s](lessons/%s.md) - %s' % (title, fn, kw), 'lessons/%s.md' % fn, days


JOURNAL = [
    ('replay', 'pixel-quest', '대화를 되짚어 새 기억 2개: 세이브 마이그레이션 사고, 치명타 난수 시드', 30),
    ('record', 'cafe-order-api', '먹이로 받은 기억 1개 새김: 결제 웹훅은 paymentKey 로 멱등 처리', 26),
    ('sweep', 'pixel-quest', '정리: 겹친 전투 교훈 2개를 하나로 합치고 색인을 줄였다', 20),
    ('replay', 'habit-tracker', '대화를 되짚어 새 기억 1개: 연속 기록은 사용자 시간대 기준', 12),
    ('replay', 'pixel-quest', '대화를 되짚어 새 기억 1개: 빌드 전에 Addressables 먼저', 5),
]


def localize(lang):
    """[번역 적용] promo/demo/<언어>.json 의 memories{파일: [제목, 키워드, 본문]}, notes{슬러그: 설명}, journal[요약] 로 바꾼다"""
    global PROJECTS, STACKS, COMMON, JOURNAL
    if lang == 'ko':
        return
    tr = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo', lang + '.json'), encoding='utf-8'))
    M = tr['memories']
    fix = lambda it: (it[0],) + tuple(M[it[0]]) + (it[4],) if it[0] in M else it
    PROJECTS = [(slug, stack, tr['notes'].get(slug, note), {k: [fix(x) for x in v] for k, v in idx.items()}) for slug, stack, note, idx in PROJECTS]
    STACKS = {k: [fix(x) for x in v] for k, v in STACKS.items()}
    COMMON = [fix(x) for x in COMMON]
    JOURNAL = [(m, sl, tr['journal'][i] if i < len(tr['journal']) else su, h) for i, (m, sl, su, h) in enumerate(JOURNAL)]


def main():
    a = sys.argv[1:]
    lang = a[a.index('--lang') + 1] if '--lang' in a else 'ko'
    localize(lang)
    out = os.path.abspath(a[0])
    shutil.rmtree(out, ignore_errors=True)
    cx, act, per = os.path.join(out, 'cortex'), os.path.join(out, 'active'), os.path.join(out, 'persona')
    rows, strength = [], {}
    for slug, stack, note, idx in PROJECTS:
        rows.append('| /Users/demo/dev/%s | %s | %s | - | %s |' % (slug, slug, stack, note))
        pdir = 'projects/' + slug
        index_lines = ['# %s - 기억 지도' % slug, '', '> %s' % note, '']
        for name, items in idx.items():
            lines = ['# %s - %s' % (slug, name.replace('.md', '')), '']
            for it in items:
                line, rel, days = lesson(cx, pdir, it)
                lines.append(line)
                if days < 10:
                    strength['%s/%s' % (pdir, rel)] = {'shown': 6 - days // 2, 'opened': 2, 'grepped': 1,
                                                      'last': time.strftime('%Y-%m-%d', time.localtime(NOW - days * DAY))}
            w(os.path.join(cx, pdir, name), '\n'.join(lines) + '\n', 1)
            index_lines.append('- [%s](%s) - %s 관련 교훈' % (name.replace('.md', ''), name, name.split('-')[-1].replace('.md', '')))
        if slug == 'cafe-order-api':   # 머리가 꽉 찬 뇌 - 지도가 2,500자를 넘는다
            index_lines += ['', '## 작업 메모'] + ['- 주문 %d 단계: 메뉴 선택, 옵션, 결제, 제조 알림, 픽업 알림, 영수증, 리뷰 요청까지 이어지는 흐름의 화면과 API 를 나눠 둔다. 각 단계의 실패 처리와 재시도 규칙은 해당 색인에 있다.' % i for i in range(1, 22)]
        w(os.path.join(cx, pdir, 'INDEX.md'), '\n'.join(index_lines) + '\n', 1)
    w(os.path.join(cx, 'registry.md'), '# registry\n\n| 경로 프리픽스 | 프로젝트 슬러그 | 스택 | 스택 버전 | 비고 |\n|---|---|---|---|---|\n' + '\n'.join(rows) + '\n')
    for stack, items in STACKS.items():
        lines = ['# %s - lessons index' % stack, '']
        for it in items:
            lines.append(lesson(cx, 'stacks/' + stack, it)[0])
        w(os.path.join(cx, 'stacks', stack, 'lessons-index.md'), '\n'.join(lines) + '\n', 2)
    lines = ['# common - lessons index', '']
    for it in COMMON:
        lines.append(lesson(cx, 'common', it)[0])
    w(os.path.join(cx, 'common', 'lessons-index.md'), '\n'.join(lines) + '\n', 2)
    # 해마 상태: 강도, 잠, 일지
    hc = os.path.join(cx, '.hippocampus')
    w(os.path.join(hc, 'strength.json'), json.dumps({'generated': time.strftime('%Y-%m-%d'), 'memories': strength}, ensure_ascii=False))
    w(os.path.join(hc, 'sleep', 'last'), str(int(NOW - 7 * 3600)))
    w(os.path.join(hc, 'sleep', 'last-summary.txt'), '이상 없음')
    for i, (mode, slug, summ, hrs) in enumerate(JOURNAL):
        rid = '2026100%d-demo-%02d' % (i % 9, i)
        t = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(NOW - hrs * 3600))
        w(os.path.join(hc, 'done', rid + '.json'), json.dumps({'id': rid, 'status': 'done', 'summary': summ, 'finished_at': t}, ensure_ascii=False))
        w(os.path.join(hc, 'done', rid + '.request.json'), json.dumps({'mode': mode, 'slug': slug, 'caller': 'demo'}, ensure_ascii=False))
    os.makedirs(os.path.join(hc, 'queue'), exist_ok=True)
    # 앱 상태: 설치일(옮겨 온 기억이 없게 오래전), 설정
    w(os.path.join(act, 'brain-born'), time.strftime('%Y-%m-%d', time.localtime(NOW - 23 * DAY)) + '\n', 23)
    w(os.path.join(act, 'config'), 'enabled=1\nhippocampus_model=claude-sonnet-5-5\nhippocampus_effort=medium\nlang=%s\n' % lang)
    # 성격: 습관 앱은 부엉이
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
    os.environ['BRAIN_PERSONA_DIR'] = per
    import persona
    persona.PERSONA_DIR = per
    persona.save('habit-tracker', persona.from_breed('owl', lang))
    print(out)


if __name__ == '__main__':
    main()
