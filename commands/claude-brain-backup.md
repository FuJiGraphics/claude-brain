---
description: {{DESC}}
argument-hint: "{{HINT}}"
disable-model-invocation: true
---
<!-- brain:command - brain 의 install.sh 가 commands/ 템플릿으로 만든 파일이다. 고치려면 저장소의 템플릿을 고치고 install.sh 를 다시 돌린다 -->

`bash "{{BRAIN}}/scripts/backup.sh" make` 를 실행하고 출력 한 줄을 그대로 보여 준다. 다른 컴퓨터로 옮기려면 그 컴퓨터에 brain 을 설치한 뒤 `bash <brain 경로>/scripts/backup.sh restore <zip 경로>` 를 실행하면 된다고 한 줄 덧붙인다(사용자 언어로).
