# projects/ledger - lessons index

- [ledger/gen/rates.py 는 커밋하지 않는 생성 파일 - tools/build_rates.py --rounding half-even 으로 만든다(기본 half-up 이면 정산이 1센트 어긋남), 사용자 결정 2026-09-02](lessons/gen-rates-built-with-half-even-rounding-2026-09-02.md) - ModuleNotFoundError ledger.gen.rates, 환율 표, 반올림, build_rates
- [split_bill 의 나머지 센트는 마지막 사람에게 몰아 준다 - 앞사람부터 1센트씩 나누면 영수증 대조가 어긋났다, 사용자 결정 2026-09-10](lessons/split-bill-remainder-goes-to-last-payer-2026-09-10.md) - 나눠 내기, 더치페이, 나머지, money.py
- [data/rates.csv 는 UTF-8 BOM 없이 저장한다 - 엑셀에서 내보내면 BOM 이 붙어 첫 열 이름이 깨졌다(2026-08-21)](lessons/rates-csv-utf8-without-bom-2026-08-21.md) - csv, 인코딩, currency 열
- [보고서 날짜는 ISO 8601(YYYY-MM-DD)로 쓴다 - 사용자 결정 2026-08-30](lessons/report-dates-iso-8601-2026-08-30.md) - format, 날짜 형식, report
- [to_cents 는 값을 문자열로 바꾼 뒤 Decimal 로 계산한다 - float 를 바로 곱하면 0.1+0.2 오차로 1센트 틀렸다](lessons/to-cents-via-decimal-string.md) - money.py, float 오차
- [unittest 는 저장소 루트에서 python3 -m unittest 로 돌린다 - tests/ 안에서 돌리면 ledger 를 못 찾는다](lessons/run-unittest-from-repo-root.md) - ModuleNotFoundError ledger, 테스트 실행 위치
- [동기화 잠금 파일 data/.sync.lock 은 동기화가 끝나면 지운다](lessons/sync-lock-file-cleanup.md) - database is locked, sqlite
- [환율 API 는 하루 100회 제한 - 응답을 data/cache 에 하루 동안 둔다(2026-08-15)](lessons/exchange-rate-api-daily-limit-2026-08-15.md) - rates, 환율, 호출 제한
- [원 단위로만 보여 주던 옛 금액 화면은 지웠다(2026-07-01)](lessons/old-won-display-removed-2026-07-01.md) - format, 표시, 화면
- [CLI 옵션 이름은 kebab-case(--dry-run)로 쓴다 - 사용자 결정](lessons/cli-options-kebab-case.md) - argparse, 옵션 이름
