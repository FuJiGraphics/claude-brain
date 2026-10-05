---
description: {{DESC}}
argument-hint: "{{HINT}}"
disable-model-invocation: true
---
<!-- brain:command - brain 의 install.sh 가 commands/ 템플릿으로 만든 파일이다. 고치려면 저장소의 템플릿을 고치고 install.sh 를 다시 돌린다 -->

`bash "{{BRAIN}}/scripts/update.sh"` 를 실행하고(시간이 걸릴 수 있으니 timeout 을 300000 으로 준다) 출력을 그대로 보여 준다. 출력에 없는 내용을 덧붙이지 않는다. 멈췄다는 출력이면 그 이유와 해결 방법 한 줄만 사용자 언어로 알린다.
