# unittest 는 저장소 루트에서 python3 -m unittest 로 돌린다 - tests/ 안에서 돌리면 ledger 를 못 찾는다

`cd tests && python3 -m unittest` 는 `ModuleNotFoundError: No module named 'ledger'` 로 깨진다. 루트에서 돌리면 된다.
