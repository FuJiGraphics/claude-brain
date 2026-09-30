---
description: 기억시키기 - 해마 큐에 넣고 바로 끝난다
argument-hint: "<내용>"
disable-model-invocation: true
---
<!-- brain:command - brain 의 install.sh 가 commands/ 템플릿으로 만든 파일이다. 고치려면 저장소의 템플릿을 고치고 install.sh 를 다시 돌린다 -->

`$ARGUMENTS` 를 기억할 내용으로 쓴다. 이 대화에서 그 내용의 근거(file:line 또는 사용자 발화 인용)를 찾아 붙여 현재 폴더에서 `bash "{{BRAIN}}/scripts/remember.sh" "<내용> - 근거: <근거>"` 를 실행한다. 근거를 못 찾으면 "근거: 사용자 요청 <오늘 날짜>" 로 둔다. 사용자에게 되묻지 않는다. 실행 후 한 줄로 알린다.
