---
description: 해마 처리 결과 - 상태별 건수, 실패 항목, 최근 5건
disable-model-invocation: true
---
<!-- brain:command - brain 의 install.sh 가 commands/ 템플릿으로 만든 파일이다. 고치려면 저장소의 템플릿을 고치고 install.sh 를 다시 돌린다 -->

보통은 brain 훅이 이 입력을 먼저 받아 바로 처리하므로 여기까지 오지 않는다. 여기까지 왔으면 훅이 꺼진 것이다 - `bash "{{BRAIN}}/scripts/hippocampus-ctl.sh" results --brief` 를 실행하고 출력을 보여 준다.
