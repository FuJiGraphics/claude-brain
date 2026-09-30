---
description: brain 상태 - 켜짐, 해마 설정과 큐, 실패, 마지막 잠, 최근 떠올림
disable-model-invocation: true
---
<!-- brain:command - brain 의 install.sh 가 commands/ 템플릿으로 만든 파일이다. 고치려면 저장소의 템플릿을 고치고 install.sh 를 다시 돌린다 -->

보통은 brain 훅이 이 입력을 먼저 받아 바로 처리하므로 여기까지 오지 않는다. 여기까지 왔으면 훅이 꺼진 것이다 - `bash "{{BRAIN}}/scripts/status.sh"` 를 실행하고 출력을 표로 짧게 요약한다.
