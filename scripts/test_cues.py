#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""thalamus 에러 단서 시험 - 언어별 에러 출력 표본마다 기대하는 단서가 나오는지 본다(기억 저장소 없이 단서 추출만)

사용: python3 scripts/test_cues.py
- 표본은 각 도구의 실제 출력 꼴이다. 기대 단서는 '반드시 있어야 할 것', 금지 단서는 '나오면 안 되는 것'
- is_error_output: 종료 코드 0 으로 끝난 명령의 출력을 에러로 볼지(성공 출력은 에러로 보면 안 된다)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thalamus as T  # noqa: E402

ROOT = '/work/proj'
CASES = [
    ('TS tsc --pretty false (놓친 실제 사례)',
     "src/type-check.ts(12,27): error TS2307: Cannot find module '../gen/ts-lib.ts' or its corresponding type declarations.",
     ['TS2307', 'type-check', 'ts-lib'], []),
    ('TS tsc pretty',
     "src/scene/loader.ts:40:5 - error TS2339: Property 'spawnEntity' does not exist on type 'World'.",
     ['TS2339', 'spawnEntity'], ['loader']),
    ('C# (기존)',
     "Assets/Scripts/PlayerMover.cs(23,9): error CS0246: The type or namespace name 'InputReader' could not be found",
     ['CS0246', 'PlayerMover', 'InputReader'], []),
    ('Unity 예외 프레임',
     "MissingComponentException: There is no 'Rigidbody2D' attached\nPlayerMover.Update () (at Assets/Scripts/PlayerMover.cs:31)",
     ['MissingComponentException', 'PlayerMover'], []),
    ('MSVC(Windows 루트)',
     "C:\\proj\\src\\RenderGraph.cpp(88,14): error C2065: 'passCount': undeclared identifier",
     ['C2065', 'RenderGraph', 'passCount'], [], 'C:/proj'),
    ('MSVC 링커', "main.obj : error LNK2019: unresolved external symbol \"void __cdecl InitAudio(void)\"", ['LNK2019'], []),
    ('gcc',
     "src/net/socket_pool.c:120:9: error: 'max_conns' undeclared (first use in this function)",
     ['socket_pool', 'max_conns'], []),
    ('clang fatal',
     "lib/AudioMixer.cpp:5:10: fatal error: 'portaudio.h' file not found",
     ['AudioMixer'], []),
    ('swift',
     "Sources/App/SessionStore.swift:44:17: error: cannot find 'tokenCache' in scope",
     ['SessionStore', 'tokenCache'], []),
    ('javac',
     "src/main/java/com/acme/OrderService.java:57: error: cannot find symbol\n    symbol:   method applyCoupon(Order)",
     ['OrderService'], []),
    ('Rust',
     "error[E0308]: mismatched types\n  --> crates/vega-core/src/world_query.rs:88:21\n   |\n88 |     let n: u32 = count_entities(&w);\n   |                  ^^^^^^^^^^^^^^^^^ expected `u32`, found `usize`",
     ['E0308', 'world_query'], []),
    ('Rust clippy',
     "warning: indexing into a string may panic\n  --> src/text_layout.rs:12:5\n   |\n   = help: for further information visit https://rust-lang.github.io/rust-clippy/master/index.html#string_slice",
     ['text_layout'], []),
    ('Rust panic',
     "thread 'main' panicked at src/asset_cache.rs:42:9:\ncalled `Option::unwrap()` on a `None` value",
     ['asset_cache'], []),
    ('Go 컴파일',
     "# example.com/svc/billing\n./invoice_builder.go:31:2: undefined: taxTable",
     ['invoice_builder'], []),
    ('Go panic',
     "panic: runtime error: index out of range [3] with length 3\n\ngoroutine 1 [running]:\nmain.pickShard(...)\n\t/work/proj/shard_router.go:22 +0x1d\nruntime.main()\n\t/usr/local/go/src/runtime/proc.go:271",
     ['shard_router'], ['proc']),
    ('Python 트레이스백(프로젝트 마지막 프레임)',
     "Traceback (most recent call last):\n  File \"/work/proj/app/cli.py\", line 9, in <module>\n    main()\n  File \"/work/proj/app/settlement_job.py\", line 40, in main\n    run()\n  File \"/usr/lib/python3.11/json/__init__.py\", line 293, in load\n    return loads(fp.read())\nKeyError: 'merchant_id'",
     ['settlement_job', 'merchant_id'], ['__init__', 'KeyError']),
    ('Python 모듈 없음',
     "Traceback (most recent call last):\n  File \"/work/proj/ledger/rates.py\", line 2, in <module>\nModuleNotFoundError: No module named 'ledger.gen.rates'",
     ['ledger.gen.rates'], ['ledger.gen', 'rates']),
    ('Python 가상 프레임(<string>)은 파일 단서가 아니다',
     "Traceback (most recent call last):\n  File \"<string>\", line 1, in <module>\nModuleNotFoundError: No module named 'ledger_core'",
     ['ledger_core'], ['<string>']),
    ('pytest',
     "FAILED tests/test_refund_flow.py::test_partial_refund_rounds_down - AssertionError: assert 333 == 334",
     ['test_refund_flow', 'test_partial_refund_rounds_down'], ['AssertionError']),
    ('ruff', "app/payment_gateway.py:3:8: F401 [*] `os` imported but unused\nFound 1 error.\n[*] 1 fixable with the `--fix` option.",
     ['F401', 'payment_gateway'], []),
    ('Node 오류 코드',
     "node:internal/modules/esm/resolve:257\nError [ERR_MODULE_NOT_FOUND]: Cannot find module '/work/proj/dist/worker-pool.js' imported from /work/proj/src/main.mjs",
     ['ERR_MODULE_NOT_FOUND', 'worker-pool'], []),
    ('Node 스택',
     "TypeError: Cannot read properties of undefined (reading 'width')\n    at layoutGlyphs (/work/proj/src/text/glyph_layout.js:77:19)\n    at Object.<anonymous> (/work/proj/node_modules/somelib/index.js:3:1)",
     ['glyph_layout'], ['somelib']),
    ('vitest',
     " FAIL  src/physics/collide.test.ts > broadphase > keeps sleeping bodies\nAssertionError: expected 2 to be 3\n ❯ src/physics/collide.test.ts:41:23",
     ['collide.test'], []),
    ('node:test',
     "✖ splits remainder to last payer (1.2ms)\n  AssertionError [ERR_ASSERTION]: Expected values to be strictly deep-equal\n      at TestContext.<anonymous> (file:///work/proj/test/split_bill.test.mjs:5:10)",
     ['split_bill.test'], []),
    ('Java 예외',
     "Exception in thread \"main\" com.acme.ledger.LedgerClosedException: period 2026-09 closed\n\tat com.acme.ledger.PostingService.post(PostingService.java:88)\n\tat java.base/java.lang.Thread.run(Thread.java:840)",
     ['LedgerClosedException', 'PostingService'], ['Thread']),
    ('Kotlin', "e: file:///work/proj/app/src/main/kotlin/SyncWorker.kt:41:9 Unresolved reference: retryPolicy", ['SyncWorker'], []),
    ('Ruby', "app/models/invoice_mailer.rb:12:in 'deliver_now': undefined method 'recipients' for nil (NoMethodError)",
     ['invoice_mailer', 'deliver_now'], ['NoMethodError']),
    ('PHP', "PHP Fatal error:  Uncaught Error: Call to undefined function render_invoice() in /work/proj/src/InvoiceView.php:23",
     ['InvoiceView'], []),
    ('하네스 차단은 단서 없음', "Permission for this command was denied", [], None),
]
OK_OUTPUTS = [   # 성공한 명령의 흔한 출력 - 에러로 보면 안 된다
    ("grep -n 출력", "src/x.ts:12:  throw new Error('bad input')\nsrc/y.ts:3:// error handling"),
    ("테스트 통과", "Ran 12 tests in 0.020s\n\nOK"),
    ("git log", "abc123 fix: error message wording\ndef456 feat: retry on failure"),
    ("ls", "error_cues.py\nfail_fast.md"),
]


def main():
    bad = 0
    for case in CASES:
        name, text, want, deny = case[:4]
        got = [c for c, _ in T.error_cues(text, set(), case[4] if len(case) > 4 else ROOT)]
        miss = [w for w in want if w not in got]
        extra = [d for d in (deny or []) if d in got]
        gate = T.is_error_output(text)
        if deny is None:
            ok = not got
        else:
            ok = not miss and not extra and gate
        bad += not ok
        print('%s %-28s 단서=%s%s%s%s' % ('ok ' if ok else 'BAD', name, got, ' 빠짐=%s' % miss if miss else '',
                                        ' 금지=%s' % extra if extra else '', '' if gate or deny is None else ' (에러로 안 봄)'))
    for name, text in OK_OUTPUTS:
        e = T.is_error_output(text)
        bad += e
        print('%s %-28s 에러로 봄=%s' % ('BAD' if e else 'ok ', name, e))
    print('실패 %d' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
