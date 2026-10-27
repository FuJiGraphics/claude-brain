# data/rates.csv 는 UTF-8 BOM 없이 저장한다 - 엑셀에서 내보내면 BOM 이 붙어 첫 열 이름이 깨졌다(2026-08-21)

엑셀 "CSV UTF-8" 로 내보내면 BOM 이 붙어 csv.DictReader 의 첫 열 이름이 "\ufeffcurrency" 가 되었다. 편집기로 BOM 없이 다시 저장해 고쳤다.
