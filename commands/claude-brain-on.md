---
description: {{DESC}}
argument-hint: "{{HINT}}"
disable-model-invocation: true
---
<!-- brain:command - brain 의 install.sh 가 commands/ 템플릿으로 만든 파일이다. 고치려면 저장소의 템플릿을 고치고 install.sh 를 다시 돌린다 -->

보통은 brain 훅이 이 입력을 먼저 받아 바로 처리하므로 여기까지 오지 않는다. 여기까지 왔으면 훅이 꺼진 것이다 - 인자가 `here` 면 현재 폴더에서 `python3 "{{BRAIN}}/scripts/thalamus.py" scope .` 의 둘째 칸(슬러그)을 얻어 `bash "{{BRAIN}}/scripts/config.sh" unmute <슬러그>` 를 실행하고 한 줄로 알린다(빈 출력이면 등록된 프로젝트가 아니라고 알린다). 인자가 없으면 `bash "{{BRAIN}}/scripts/config.sh" on` 를 실행하고 결과를 보여 준다.
