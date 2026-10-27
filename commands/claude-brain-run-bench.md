---
description: {{DESC}}
argument-hint: "{{HINT}}"
disable-model-invocation: true
---
<!-- brain:command - brain 의 install.sh 가 commands/ 템플릿으로 만든 파일이다. 고치려면 저장소의 템플릿을 고치고 install.sh 를 다시 돌린다 -->

`python3 "{{BRAIN}}/benchmarks/bench/bench.py" $ARGUMENTS` 를 백그라운드로 실행한다. 인자가 없으면 깊이 low 로 떠올림(recall)과 저장(encode) 두 묶음을 돌린다(low 는 30분 안팎, 묶음 하나만 주면 그것만, high 는 몇 시간까지). 끝나면 출력 마지막 줄의 보고서 경로를 알리고, 보고서의 "먼저 읽을 것", 과제 종류별 합계, 저장 벤치 표를 그대로 보여 준다. 해석을 덧붙일 때는 보고서의 "한계" 절도 함께 적는다. 벤치는 끝나면 임시 폴더를 지우고 결과 폴더 하나만 바탕화면에 남긴다.
