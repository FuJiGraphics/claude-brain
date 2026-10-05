---
description: {{DESC}}
argument-hint: "{{HINT}}"
disable-model-invocation: true
---
<!-- brain:command - brain 의 install.sh 가 commands/ 템플릿으로 만든 파일이다. 고치려면 저장소의 템플릿을 고치고 install.sh 를 다시 돌린다 -->

현재 폴더에서 `bash "{{BRAIN}}/scripts/recall.sh" $ARGUMENTS` 를 실행한다. 찾은 기억마다 요지 한 줄과 경로를 짧게 알려 준다. 못 찾았으면 그렇다고만 말한다.
