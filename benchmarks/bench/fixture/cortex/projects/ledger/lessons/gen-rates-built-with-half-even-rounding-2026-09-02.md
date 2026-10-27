# ledger/gen/rates.py 는 커밋하지 않는 생성 파일 - tools/build_rates.py --rounding half-even 으로 만든다(기본 half-up 이면 정산이 1센트 어긋남), 사용자 결정 2026-09-02

회계팀 정산 기준이 은행가 반올림(half-even)이라 환율 표도 그 방식으로 만든다. 기본값 half-up 으로 만든 표로 정산했더니 USD 와 JPY 에서 1센트씩 어긋났다(2026-09-02, 사용자 결정).

- 만드는 법: 저장소 루트에서 `python3 tools/build_rates.py --rounding half-even`
- 생성 파일을 손으로 쓰거나 고치지 않는다 - 다음 생성에서 덮인다
