#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 명령행 문구 - 사용자가 터미널과 슬래시 명령 결과로 직접 보는 글을 언어별로 둔다.

lang.py 는 세션(모델)에 들어가는 문구, persona_i18n.py 는 성격 문장, 이 파일은 사람이 읽는 출력이다:
슬래시 명령 결과(thalamus control), 설치기, status, config, hippocampus-ctl, editor.sh, 잠 요약, 해마 실패 요약,
명령어 파일의 설명(description, argument-hint), 앱 서버의 오류 글.
모델만 읽는 출력(recall.sh, remember.sh 의 큐 투입 줄, check.py, 데몬 로그)은 한국어 하나로 둔다 - 모델이 사용자 언어로 옮겨 전한다.

문구 규칙: 자리는 %s, %d 만 쓰고 글자 % 는 %% 로 적는다. 역슬래시는 쓰지 않는다(셸 printf 가 형식 문자열로 읽는다).
언어: <brain>/.active/config 의 lang= (lang.current). 없는 키는 한국어로 돌아간다.

명령행:
  cli_i18n.py sh <묶음>...                      셸 변수(M_<키>, 점은 _)로 내보낸다. 예: eval "$(cli_i18n.py sh cfg st)"
  cli_i18n.py say <키> [인자]...                 한 줄 출력
  cli_i18n.py commands <템플릿> <대상> <brain> <install|uninstall|refresh>   명령어 파일을 그 언어로 쓴다
"""
import glob
import os
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lang as L  # noqa: E402

NATIVE = {'ko': '한국어', 'en': 'English', 'ja': '日本語', 'zh': '简体中文'}

TEXT = {
    'ko': {
        # 슬래시 명령 (thalamus control)
        'ctl.changed': 'brain 설정을 바꿨어요',
        'ctl.change': '바꾸려면: /claude-brain-config default | eco | quality',
        'ctl.usage': '사용법: %s',
        'ctl.app_fail': 'brain 앱을 띄우지 못했어요. 직접 실행: bash %s',
        'ctl.sleep': '밤 정리를 시작했어요. 일은 해마가 뒤에서 하고, 결과는 /claude-brain-status 로 볼 수 있어요',
        'ctl.error': 'brain 명령을 처리하지 못했어요 (%s)',
        # config.sh
        'cfg.on': 'brain: 켜짐',
        'cfg.off': 'brain: 꺼짐',
        'cfg.hippo': '해마: %s, effort %s',
        'cfg.lang': '언어: %s',
        'cfg.stop': '해마: 지금 하던 일만 끝내고 멈춰요 (큐는 남아요)',
        'cfg.usage': '사용법: config.sh %s',
        # status.sh
        'st.h_cfg': '== 설정',
        'st.h_hippo': '== 해마',
        'st.fails': '실패하거나 거부, 시간 초과로 끝난 일: %s건 (자세히: /claude-brain-results)',
        'st.sleep': '== 마지막 밤 정리: %s',
        'st.never': '아직 없어요',
        'st.check': '기억 검사: 망가졌거나 못 찾는 것 %s건, 참고 %s건',
        'st.recall': '== 최근 24시간 떠올림: %s, 세션 %d개, %d자',
        'st.recall_none': '== 최근 24시간 떠올림: 없음',
        'st.harness': '== Claude Code 버전이 바뀌었어요 (기록 %s, 지금 %s). 도구가 실제로 이상하게 동작할 때만 /claude-brain-remember 로 알려 주세요',
        # hippocampus-ctl.sh
        'hc.alive': '데몬: 실행 중 pid %s (시작 %s, 지금 하는 일: %s, 마지막 신호 %s)',
        'hc.idle': '대기',
        'hc.none': '데몬: 쉬는 중',
        'hc.stale': '데몬: 쉬는 중 (남은 잠금은 다음 투입 때 정리돼요)',
        'hc.counts': '큐 대기 %s건, 처리 중 %s건, 끝난 일 %s건',
        'hc.wait_item': '  대기: %s',
        'hc.orphan': '  처리 중으로 남은 일은 데몬이 꺼지며 남은 거예요. 다음 투입 때 큐로 되돌아가요',
        'hc.stop': '멈춤 요청을 받았어요. 지금 하던 일이 끝나면 멈춰요',
        'hc.closed': '마감(실패): %s',
        'hc.killed': '강제로 멈췄어요',
        'hc.no_daemon': '실행 중인 데몬이 없어요',
        'hc.kill_sum': 'hippocampus-ctl.sh kill 로 처리 중에 강제로 멈췄어요. 요청은 done/<id>.request.json 에 있어요',
        'hc.r_total': '해마가 한 일 %d건: %s',
        'hc.r_bad': '실패, 거부, 시간 초과:',
        'hc.r_recent': '최근:',
        'hc.r_all': '전체 보기: bash %s results',
        'hc.r_none': '해마가 한 일이 아직 없어요',
        'hc.r_readfail': '읽기 실패',
        'hc.slice_fail': '정비할 조각을 계산하지 못했어요',
        'hc.usage': '사용법: hippocampus-ctl.sh status | stop | kill | results [--ack|--brief] | log [id] | sweep [N]',
        'stat.done': '완료', 'stat.failed': '실패', 'stat.denied': '거부', 'stat.timeout': '시간 초과', 'stat.partial': '일부 완료',
        # editor.sh
        'ed.off': 'brain 앱을 껐어요',
        'ed.none': '실행 중인 앱이 없어요',
        'ed.fail': '앱을 띄우지 못했어요. 직접 실행: python3 %s',
        'ed.slow': '앱이 3초 안에 뜨지 않았어요. 로그: %s',
        'ed.url': 'brain 앱: %s',
        'ed.local': '(이 컴퓨터에서만 열려요. 끄기: bash %s stop)',
        'ed.restart': '새 버전으로 앱을 다시 띄웠어요',
        'ed.front': '열려 있던 앱 창을 앞으로 가져왔어요',
        # install.sh
        'in.loc_stop': '중단: brain 은 %s/skills 에 있는데 설정 폴더는 %s 예요. CLAUDE_CONFIG_DIR=%s 로 다시 실행해 주세요',
        'in.lang': '언어: %s (바꾸기: /claude-brain-config lang <ko|en|ja|zh> 또는 앱 설정)',
        'in.hook_fail': '중단: 훅을 등록하지 못했어요. %s 를 확인한 뒤 다시 실행해 주세요 (CLAUDE.md 와 잠 예약은 건드리지 않았어요)',
        'in.not_json': 'settings.json 이 올바른 JSON 이 아니에요: %s',
        'in.bad_shape': 'settings.json 의 형식이 예상과 달라요 (최상위나 hooks 가 객체가 아니에요)',
        'in.hooks_on': '훅 등록: %s',
        'in.hooks_off': '훅 해제: %s',
        'in.md_fail': '중단: CLAUDE.md 를 고치지 못했어요 (훅은 이미 걸렸어요). %s 를 확인한 뒤 install.sh 를 다시 실행해 주세요',
        'in.md_on': '기억 안내 한 줄 추가: %s',
        'in.md_off': '기억 안내 한 줄 제거: %s',
        'in.seed': '기억 저장소 준비: %s',
        'in.seed_fail': '중단: 기억 저장소 골격(%s)이 없어요. git clone 을 다시 받아 주세요',
        'in.cmd_fail': '경고: 명령어 파일을 만들지 못했어요 (훅과 기억은 정상이에요)',
        'in.cmd_skip': '건너뜀: %s 는 직접 만든 파일이라 그대로 뒀어요',
        'in.cmd_on': '명령어 /claude-brain-* %d개: %s',
        'in.cmd_off': '명령어 /claude-brain-* %d개 제거',
        'in.plist_fail': '경고: 밤 정리 예약 파일을 만들지 못했어요 (훅과 기억은 정상이에요)',
        'in.sleep_on': '밤 정리 예약: 매일 04:30 (%s)',
        'in.sleep_fail': '경고: 밤 정리 예약에 실패했어요 (훅과 기억은 정상이에요). 나중에 install.sh 를 다시 실행하거나: launchctl bootstrap gui/%s %s',
        'in.sleep_off': '밤 정리 예약 해제',
        'in.sleep_win': '밤 정리 예약: 매일 04:30 (작업 스케줄러 %s)',
        'in.sleep_win_fail': '경고: 작업 스케줄러 등록에 실패했어요 (훅과 기억은 정상이에요). 밤 정리는 /claude-brain-sleep 으로 직접 돌릴 수 있어요',
        'in.sleep_other': '밤 정리 예약: 자동 등록은 macOS, Windows 만 해요. cron 에 하루 한 번 bash %s 를 걸어 주세요',
        'in.hippo_stop': '해마: 지금 하던 일이 끝나면 멈춰요 (남은 큐 %s건은 그대로 둬요)',
        'in.hippo_idle': '해마: 쉬는 중 (남은 큐 %s건은 그대로 둬요)',
        'in.done': '설치를 마쳤어요. 일하시는 프로젝트 폴더에서 Claude Code 에 /claude-brain-register 를 한 번 입력하시면 그 프로젝트부터 기억이 쌓이기 시작해요. 앱 열기: /claude-brain-app',
        'in.undone': '제거를 마쳤어요. 기억(cortex)은 지우지 않았어요: %s',
        # 잠 (sleep.sh)
        'sl.off': 'brain 이 꺼져 있어서 밤 정리를 건너뛰어요 (/claude-brain-on)',
        'sl.running': '밤 정리가 이미 돌고 있어서 건너뛰어요',
        'sl.start': '== 밤 정리 %s',
        'sl.forget_skip': '잊기 단계는 건너뛰어요 (해마가 일하는 중)',
        'sl.miss': '검색 실패 짝 %s개 - 학습을 맡겼어요',
        'sl.dry': '(dry-run) 투입하지 않음: %s건',
        'sl.fails': '해마 실패, 거부 %s건',
        'sl.ok': '이상 없음',
        'sl.sum': '요약: %s',
        'sl.end': '== 끝 %s',
        # 해마 데몬이 대신 쓰는 결과 요약
        'dm.twice': '처리 중에 데몬이 두 번 연달아 꺼져서 다시 시도하지 않고 마감했어요. 요청은 done/<id>.request.json 에 있어요',
        'dm.noresult': '해마가 결과 파일을 남기지 않았어요 (exit %s, 판정 %s). 로그 끝부분:',
        # python 이 없을 때 (_lib.sh 는 이 파일을 못 읽으므로 같은 글을 셸에도 둔다)
        # 앱 서버 오류 (토스트로 보인다)
        'srv.no_claude': 'claude 명령을 찾지 못했어요. Claude Code 가 설치돼 있고 터미널에서 claude 가 실행되는지 확인해 주세요',
        'srv.claude_rc': 'claude 가 오류로 끝났어요 (코드 %d). 로그인이나 사용 한도를 확인해 주세요',
        'srv.bad_reply': 'AI 답을 읽지 못했어요. 잠시 뒤 다시 해 주세요',
        'srv.bad_layer': '알 수 없는 뇌예요',
        'srv.outside': '기억 저장소 밖의 파일은 열 수 없어요',
        'srv.bad_feedback': '알 수 없는 피드백이에요',
        'srv.need_text': '지금은 어떻게 됐는지 적어 주세요',
        'srv.bad_project': '등록된 프로젝트가 아니에요',
        'srv.empty': '내용이 비어 있어요',
        'srv.too_long': '글이 너무 길어요 (%d자까지)',
        'srv.queue_fail': '해마 큐에 넣지 못했어요: %s',
    },
    'en': {
        'ctl.changed': 'brain settings updated',
        'ctl.change': 'To change: /claude-brain-config default | eco | quality',
        'ctl.usage': 'Usage: %s',
        'ctl.app_fail': 'Could not start the brain app. Run it directly: bash %s',
        'ctl.sleep': 'Nightly tidy-up started. The hippocampus works in the background; see results with /claude-brain-status',
        'ctl.error': 'Could not run the brain command (%s)',
        'cfg.on': 'brain: on',
        'cfg.off': 'brain: off',
        'cfg.hippo': 'Hippocampus: %s, effort %s',
        'cfg.lang': 'Language: %s',
        'cfg.stop': 'Hippocampus: stops after the current job (the queue is kept)',
        'cfg.usage': 'Usage: config.sh %s',
        'st.h_cfg': '== Settings',
        'st.h_hippo': '== Hippocampus',
        'st.fails': 'Jobs that failed, were denied or timed out: %s (details: /claude-brain-results)',
        'st.sleep': '== Last nightly tidy-up: %s',
        'st.never': 'not yet',
        'st.check': 'Memory check: %s broken or unreachable, %s notes',
        'st.recall': '== Recalls in the last 24 hours: %s (sessions: %d, chars: %d)',
        'st.recall_none': '== Recalls in the last 24 hours: none',
        'st.harness': '== Claude Code version changed (recorded %s, now %s). Only if tools actually misbehave, tell brain with /claude-brain-remember',
        'hc.alive': 'Daemon: running, pid %s (started %s, working on: %s, last heartbeat %s)',
        'hc.idle': 'idle',
        'hc.none': 'Daemon: resting',
        'hc.stale': 'Daemon: resting (a leftover lock will be cleaned up on the next job)',
        'hc.counts': 'Queued %s, in progress %s, finished %s',
        'hc.wait_item': '  queued: %s',
        'hc.orphan': '  The in-progress job was left behind when the daemon stopped. It goes back to the queue on the next job',
        'hc.stop': 'Stop requested. It stops after the current job',
        'hc.closed': 'Closed (failed): %s',
        'hc.killed': 'Force-stopped',
        'hc.no_daemon': 'No daemon is running',
        'hc.kill_sum': 'Force-stopped by hippocampus-ctl.sh kill while working. The request is in done/<id>.request.json',
        'hc.r_total': 'Hippocampus jobs: %d (%s)',
        'hc.r_bad': 'Failed, denied or timed out:',
        'hc.r_recent': 'Recent:',
        'hc.r_all': 'Full list: bash %s results',
        'hc.r_none': 'The hippocampus has not done any jobs yet',
        'hc.r_readfail': 'could not read',
        'hc.slice_fail': 'Could not work out what to tidy',
        'hc.usage': 'Usage: hippocampus-ctl.sh status | stop | kill | results [--ack|--brief] | log [id] | sweep [N]',
        'stat.done': 'done', 'stat.failed': 'failed', 'stat.denied': 'denied', 'stat.timeout': 'timed out', 'stat.partial': 'partly done',
        'ed.off': 'brain app closed',
        'ed.none': 'The app is not running',
        'ed.fail': 'Could not start the app. Run it directly: python3 %s',
        'ed.slow': 'The app did not start within 3 seconds. Log: %s',
        'ed.url': 'brain app: %s',
        'ed.local': '(Only this computer can open it. To close: bash %s stop)',
        'ed.restart': 'Restarted the app on the new version',
        'ed.front': 'Brought the open app window to the front',
        'in.loc_stop': 'Stopped: brain is in %s/skills but the config folder is %s. Run again with CLAUDE_CONFIG_DIR=%s',
        'in.lang': 'Language: %s (change it with /claude-brain-config lang <ko|en|ja|zh> or in the app settings)',
        'in.hook_fail': 'Stopped: could not register the hooks. Check %s and run again (CLAUDE.md and the nightly schedule were not touched)',
        'in.not_json': 'settings.json is not valid JSON: %s',
        'in.bad_shape': 'settings.json has an unexpected shape (the top level or hooks is not an object)',
        'in.hooks_on': 'Hooks registered: %s',
        'in.hooks_off': 'Hooks removed: %s',
        'in.md_fail': 'Stopped: could not update CLAUDE.md (the hooks are already registered). Check %s and run install.sh again',
        'in.md_on': 'Added the memory line to %s',
        'in.md_off': 'Removed the memory line from %s',
        'in.seed': 'Memory store ready: %s',
        'in.seed_fail': 'Stopped: the memory store template (%s) is missing. Please clone the repository again',
        'in.cmd_fail': 'Warning: could not write the command files (hooks and memory are fine)',
        'in.cmd_skip': 'Skipped: %s is your own file, left as is',
        'in.cmd_on': '%d /claude-brain-* commands: %s',
        'in.cmd_off': 'Removed %d /claude-brain-* commands',
        'in.plist_fail': 'Warning: could not write the nightly schedule file (hooks and memory are fine)',
        'in.sleep_on': 'Nightly tidy-up: every day at 04:30 (%s)',
        'in.sleep_fail': 'Warning: could not schedule the nightly tidy-up (hooks and memory are fine). Run install.sh again later, or: launchctl bootstrap gui/%s %s',
        'in.sleep_off': 'Nightly tidy-up unscheduled',
        'in.sleep_win': 'Nightly tidy-up: every day at 04:30 (Task Scheduler %s)',
        'in.sleep_win_fail': 'Warning: could not register with Task Scheduler (hooks and memory are fine). You can run the tidy-up yourself with /claude-brain-sleep',
        'in.sleep_other': 'Nightly tidy-up: automatic scheduling is macOS and Windows only. Add bash %s to cron once a day',
        'in.hippo_stop': 'Hippocampus: stops after the current job (queued jobs kept: %s)',
        'in.hippo_idle': 'Hippocampus: resting (queued jobs kept: %s)',
        'in.done': 'All set. In the project folder you work in, type /claude-brain-register once in Claude Code and brain starts collecting memories for it. Open the app: /claude-brain-app',
        'in.undone': 'Uninstalled. Your memories (cortex) were not deleted: %s',
        'sl.off': 'brain is off, skipping the nightly tidy-up (/claude-brain-on)',
        'sl.running': 'A tidy-up is already running, skipping',
        'sl.start': '== Nightly tidy-up %s',
        'sl.forget_skip': 'Skipping the forgetting step (the hippocampus is busy)',
        'sl.miss': 'Failed-search pairs: %s - sent for learning',
        'sl.dry': '(dry-run) not queued: %s',
        'sl.fails': '%s hippocampus jobs failed or were denied',
        'sl.ok': 'all good',
        'sl.sum': 'Summary: %s',
        'sl.end': '== Done %s',
        'dm.twice': 'The daemon stopped twice while working on this, so it was closed without another try. The request is in done/<id>.request.json',
        'dm.noresult': 'The hippocampus left no result file (exit %s, verdict %s). End of the log:',
        'srv.no_claude': 'Could not find the claude command. Check that Claude Code is installed and claude runs in a terminal',
        'srv.claude_rc': 'claude ended with an error (code %d). Check your login or usage limit',
        'srv.bad_reply': 'Could not read the AI reply. Please try again in a moment',
        'srv.bad_layer': 'Unknown brain',
        'srv.outside': 'Files outside the memory store cannot be opened',
        'srv.bad_feedback': 'Unknown feedback',
        'srv.need_text': 'Write how it is now',
        'srv.bad_project': 'Not a registered project',
        'srv.empty': 'It is empty',
        'srv.too_long': 'Too long (up to %d characters)',
        'srv.queue_fail': 'Could not queue it for the hippocampus: %s',
    },
    'ja': {
        'ctl.changed': 'brain の設定を変更しました',
        'ctl.change': '変更するには: /claude-brain-config default | eco | quality',
        'ctl.usage': '使い方: %s',
        'ctl.app_fail': 'brain アプリを起動できませんでした。直接実行: bash %s',
        'ctl.sleep': '夜の整理を始めました。作業は海馬がバックグラウンドで行います。結果は /claude-brain-status で確認できます',
        'ctl.error': 'brain コマンドを処理できませんでした (%s)',
        'cfg.on': 'brain: オン',
        'cfg.off': 'brain: オフ',
        'cfg.hippo': '海馬: %s, effort %s',
        'cfg.lang': '言語: %s',
        'cfg.stop': '海馬: 今の作業が終わったら止まります(キューは残ります)',
        'cfg.usage': '使い方: config.sh %s',
        'st.h_cfg': '== 設定',
        'st.h_hippo': '== 海馬',
        'st.fails': '失敗、拒否、タイムアウトで終わった作業: %s 件(詳細: /claude-brain-results)',
        'st.sleep': '== 最後の夜の整理: %s',
        'st.never': 'まだありません',
        'st.check': '記憶チェック: 壊れている・見つからないもの %s 件、参考 %s 件',
        'st.recall': '== 直近24時間の想起: %s、セッション %d 個、%d 文字',
        'st.recall_none': '== 直近24時間の想起: なし',
        'st.harness': '== Claude Code のバージョンが変わりました(記録 %s、現在 %s)。ツールが実際におかしな動きをするときだけ /claude-brain-remember で知らせてください',
        'hc.alive': 'デーモン: 実行中 pid %s (開始 %s、作業中: %s、最後の応答 %s)',
        'hc.idle': '待機',
        'hc.none': 'デーモン: 休止中',
        'hc.stale': 'デーモン: 休止中(残ったロックは次の投入時に片付きます)',
        'hc.counts': 'キュー待ち %s 件、処理中 %s 件、完了 %s 件',
        'hc.wait_item': '  待ち: %s',
        'hc.orphan': '  処理中のまま残った作業は、デーモンが止まったときのものです。次の投入時にキューへ戻ります',
        'hc.stop': '停止の要求を受けました。今の作業が終わったら止まります',
        'hc.closed': '締め切り(失敗): %s',
        'hc.killed': '強制停止しました',
        'hc.no_daemon': '実行中のデーモンはありません',
        'hc.kill_sum': 'hippocampus-ctl.sh kill で処理中に強制停止しました。要求は done/<id>.request.json にあります',
        'hc.r_total': '海馬の作業 %d 件: %s',
        'hc.r_bad': '失敗、拒否、タイムアウト:',
        'hc.r_recent': '最近:',
        'hc.r_all': 'すべて表示: bash %s results',
        'hc.r_none': '海馬の作業はまだありません',
        'hc.r_readfail': '読み込み失敗',
        'hc.slice_fail': '整理する範囲を計算できませんでした',
        'hc.usage': '使い方: hippocampus-ctl.sh status | stop | kill | results [--ack|--brief] | log [id] | sweep [N]',
        'stat.done': '完了', 'stat.failed': '失敗', 'stat.denied': '拒否', 'stat.timeout': 'タイムアウト', 'stat.partial': '一部完了',
        'ed.off': 'brain アプリを閉じました',
        'ed.none': '実行中のアプリはありません',
        'ed.fail': 'アプリを起動できませんでした。直接実行: python3 %s',
        'ed.slow': 'アプリが3秒以内に起動しませんでした。ログ: %s',
        'ed.url': 'brain アプリ: %s',
        'ed.local': '(このコンピューターでのみ開けます。閉じる: bash %s stop)',
        'ed.restart': '新しいバージョンでアプリを起動し直しました',
        'ed.front': '開いていたアプリのウィンドウを前に出しました',
        'in.loc_stop': '中断: brain は %s/skills にありますが、設定フォルダは %s です。CLAUDE_CONFIG_DIR=%s で実行し直してください',
        'in.lang': '言語: %s (変更: /claude-brain-config lang <ko|en|ja|zh> またはアプリの設定)',
        'in.hook_fail': '中断: フックを登録できませんでした。%s を確認してからもう一度実行してください(CLAUDE.md と夜の予約は変更していません)',
        'in.not_json': 'settings.json が正しい JSON ではありません: %s',
        'in.bad_shape': 'settings.json の形式が想定と違います(最上位か hooks がオブジェクトではありません)',
        'in.hooks_on': 'フックを登録: %s',
        'in.hooks_off': 'フックを解除: %s',
        'in.md_fail': '中断: CLAUDE.md を更新できませんでした(フックは登録済みです)。%s を確認してから install.sh をもう一度実行してください',
        'in.md_on': '記憶の案内行を追加: %s',
        'in.md_off': '記憶の案内行を削除: %s',
        'in.seed': '記憶の保存先を準備: %s',
        'in.seed_fail': '中断: 記憶の保存先のひな形(%s)がありません。git clone をやり直してください',
        'in.cmd_fail': '警告: コマンドファイルを作れませんでした(フックと記憶は正常です)',
        'in.cmd_skip': 'スキップ: %s はユーザーのファイルなのでそのままにしました',
        'in.cmd_on': '/claude-brain-* コマンド %d 個: %s',
        'in.cmd_off': '/claude-brain-* コマンド %d 個を削除',
        'in.plist_fail': '警告: 夜の整理の予約ファイルを作れませんでした(フックと記憶は正常です)',
        'in.sleep_on': '夜の整理を予約: 毎日 04:30 (%s)',
        'in.sleep_fail': '警告: 夜の整理を予約できませんでした(フックと記憶は正常です)。あとで install.sh を実行し直すか: launchctl bootstrap gui/%s %s',
        'in.sleep_off': '夜の整理の予約を解除',
        'in.sleep_win': '夜の整理を予約: 毎日 04:30 (タスク スケジューラ %s)',
        'in.sleep_win_fail': '警告: タスク スケジューラに登録できませんでした(フックと記憶は正常です)。夜の整理は /claude-brain-sleep で手動実行できます',
        'in.sleep_other': '夜の整理: 自動予約は macOS と Windows のみです。cron で1日1回 bash %s を実行してください',
        'in.hippo_stop': '海馬: 今の作業が終わったら止まります(残りのキュー %s 件はそのままです)',
        'in.hippo_idle': '海馬: 休止中(残りのキュー %s 件はそのままです)',
        'in.done': 'インストールが完了しました。作業しているプロジェクトのフォルダで Claude Code に /claude-brain-register と一度入力すると、そのプロジェクトから記憶がたまり始めます。アプリを開く: /claude-brain-app',
        'in.undone': 'アンインストールしました。記憶(cortex)は削除していません: %s',
        'sl.off': 'brain がオフなので夜の整理をスキップします (/claude-brain-on)',
        'sl.running': '夜の整理がすでに実行中なのでスキップします',
        'sl.start': '== 夜の整理 %s',
        'sl.forget_skip': '忘却の段階はスキップします(海馬が作業中)',
        'sl.miss': '検索失敗のペア %s 個 - 学習を依頼しました',
        'sl.dry': '(dry-run) 投入しません: %s 件',
        'sl.fails': '海馬の失敗、拒否 %s 件',
        'sl.ok': '異常なし',
        'sl.sum': '要約: %s',
        'sl.end': '== 終了 %s',
        'dm.twice': '処理中にデーモンが2回続けて止まったため、再試行せずに締め切りました。要求は done/<id>.request.json にあります',
        'dm.noresult': '海馬が結果ファイルを残しませんでした (exit %s、判定 %s)。ログの末尾:',
        'srv.no_claude': 'claude コマンドが見つかりません。Claude Code がインストールされ、ターミナルで claude が動くか確認してください',
        'srv.claude_rc': 'claude がエラーで終了しました(コード %d)。ログインや使用上限を確認してください',
        'srv.bad_reply': 'AI の返答を読み取れませんでした。少し待ってからもう一度お試しください',
        'srv.bad_layer': '不明な脳です',
        'srv.outside': '記憶の保存先の外にあるファイルは開けません',
        'srv.bad_feedback': '不明なフィードバックです',
        'srv.need_text': '今どうなっているかを書いてください',
        'srv.bad_project': '登録されたプロジェクトではありません',
        'srv.empty': '内容が空です',
        'srv.too_long': '長すぎます(%d 文字まで)',
        'srv.queue_fail': '海馬のキューに入れられませんでした: %s',
    },
    'zh': {
        'ctl.changed': '已更改 brain 设置',
        'ctl.change': '更改: /claude-brain-config default | eco | quality',
        'ctl.usage': '用法: %s',
        'ctl.app_fail': '无法启动 brain 应用。直接运行: bash %s',
        'ctl.sleep': '已开始夜间整理。海马在后台工作,结果可用 /claude-brain-status 查看',
        'ctl.error': '无法处理 brain 命令 (%s)',
        'cfg.on': 'brain: 已开启',
        'cfg.off': 'brain: 已关闭',
        'cfg.hippo': '海马: %s, effort %s',
        'cfg.lang': '语言: %s',
        'cfg.stop': '海马: 完成当前任务后停止(队列会保留)',
        'cfg.usage': '用法: config.sh %s',
        'st.h_cfg': '== 设置',
        'st.h_hippo': '== 海马',
        'st.fails': '失败、被拒绝或超时的任务: %s 个(详情: /claude-brain-results)',
        'st.sleep': '== 上次夜间整理: %s',
        'st.never': '还没有',
        'st.check': '记忆检查: 损坏或找不到的 %s 个,参考 %s 个',
        'st.recall': '== 最近24小时的回忆: %s,会话 %d 个,%d 字',
        'st.recall_none': '== 最近24小时的回忆: 无',
        'st.harness': '== Claude Code 版本已变化(记录 %s,现在 %s)。只有工具确实出现异常时,才用 /claude-brain-remember 告诉 brain',
        'hc.alive': '守护进程: 运行中 pid %s (开始于 %s,正在处理: %s,最后心跳 %s)',
        'hc.idle': '等待',
        'hc.none': '守护进程: 休息中',
        'hc.stale': '守护进程: 休息中(残留的锁会在下次投入时清理)',
        'hc.counts': '队列等待 %s 个,处理中 %s 个,已完成 %s 个',
        'hc.wait_item': '  等待: %s',
        'hc.orphan': '  处理中的任务是守护进程停止时留下的,下次投入时会回到队列',
        'hc.stop': '已收到停止请求,当前任务完成后停止',
        'hc.closed': '已结束(失败): %s',
        'hc.killed': '已强制停止',
        'hc.no_daemon': '没有运行中的守护进程',
        'hc.kill_sum': '处理中被 hippocampus-ctl.sh kill 强制停止。请求在 done/<id>.request.json',
        'hc.r_total': '海马的任务 %d 个: %s',
        'hc.r_bad': '失败、被拒绝、超时:',
        'hc.r_recent': '最近:',
        'hc.r_all': '查看全部: bash %s results',
        'hc.r_none': '海马还没有做过任务',
        'hc.r_readfail': '读取失败',
        'hc.slice_fail': '无法计算要整理的部分',
        'hc.usage': '用法: hippocampus-ctl.sh status | stop | kill | results [--ack|--brief] | log [id] | sweep [N]',
        'stat.done': '完成', 'stat.failed': '失败', 'stat.denied': '被拒绝', 'stat.timeout': '超时', 'stat.partial': '部分完成',
        'ed.off': '已关闭 brain 应用',
        'ed.none': '应用没有在运行',
        'ed.fail': '无法启动应用。直接运行: python3 %s',
        'ed.slow': '应用在3秒内没有启动。日志: %s',
        'ed.url': 'brain 应用: %s',
        'ed.local': '(只能在这台电脑上打开。关闭: bash %s stop)',
        'ed.restart': '已用新版本重新启动应用',
        'ed.front': '已把打开着的应用窗口切到最前面',
        'in.loc_stop': '已中止: brain 在 %s/skills,但配置文件夹是 %s。请用 CLAUDE_CONFIG_DIR=%s 重新运行',
        'in.lang': '语言: %s (更改: /claude-brain-config lang <ko|en|ja|zh> 或应用设置)',
        'in.hook_fail': '已中止: 无法注册钩子。请检查 %s 后重新运行(没有改动 CLAUDE.md 和夜间计划)',
        'in.not_json': 'settings.json 不是有效的 JSON: %s',
        'in.bad_shape': 'settings.json 的格式与预期不同(顶层或 hooks 不是对象)',
        'in.hooks_on': '已注册钩子: %s',
        'in.hooks_off': '已移除钩子: %s',
        'in.md_fail': '已中止: 无法更新 CLAUDE.md(钩子已注册)。请检查 %s 后重新运行 install.sh',
        'in.md_on': '已添加记忆说明行: %s',
        'in.md_off': '已删除记忆说明行: %s',
        'in.seed': '记忆存储已就绪: %s',
        'in.seed_fail': '已中止: 缺少记忆存储模板(%s)。请重新 git clone',
        'in.cmd_fail': '警告: 无法写入命令文件(钩子和记忆正常)',
        'in.cmd_skip': '已跳过: %s 是你自己的文件,保持不变',
        'in.cmd_on': '/claude-brain-* 命令 %d 个: %s',
        'in.cmd_off': '已移除 /claude-brain-* 命令 %d 个',
        'in.plist_fail': '警告: 无法写入夜间整理的计划文件(钩子和记忆正常)',
        'in.sleep_on': '夜间整理: 每天 04:30 (%s)',
        'in.sleep_fail': '警告: 无法安排夜间整理(钩子和记忆正常)。稍后重新运行 install.sh,或: launchctl bootstrap gui/%s %s',
        'in.sleep_off': '已取消夜间整理计划',
        'in.sleep_win': '夜间整理: 每天 04:30 (任务计划程序 %s)',
        'in.sleep_win_fail': '警告: 无法注册到任务计划程序(钩子和记忆正常)。可以用 /claude-brain-sleep 手动运行整理',
        'in.sleep_other': '夜间整理: 自动计划只支持 macOS 和 Windows。请在 cron 中每天运行一次 bash %s',
        'in.hippo_stop': '海马: 完成当前任务后停止(剩余队列 %s 个保持不变)',
        'in.hippo_idle': '海马: 休息中(剩余队列 %s 个保持不变)',
        'in.done': '安装完成。在你工作的项目文件夹里对 Claude Code 输入一次 /claude-brain-register,这个项目就会开始积累记忆。打开应用: /claude-brain-app',
        'in.undone': '已卸载。记忆(cortex)没有删除: %s',
        'sl.off': 'brain 已关闭,跳过夜间整理 (/claude-brain-on)',
        'sl.running': '夜间整理已在运行,跳过',
        'sl.start': '== 夜间整理 %s',
        'sl.forget_skip': '跳过遗忘步骤(海马正在工作)',
        'sl.miss': '搜索失败的配对 %s 个 - 已交给学习',
        'sl.dry': '(dry-run) 未投入: %s 个',
        'sl.fails': '海马失败、被拒绝 %s 个',
        'sl.ok': '一切正常',
        'sl.sum': '摘要: %s',
        'sl.end': '== 结束 %s',
        'dm.twice': '处理中守护进程连续停止两次,因此不再重试并结束。请求在 done/<id>.request.json',
        'dm.noresult': '海马没有留下结果文件 (exit %s,判定 %s)。日志末尾:',
        'srv.no_claude': '找不到 claude 命令。请确认已安装 Claude Code,并且能在终端运行 claude',
        'srv.claude_rc': 'claude 出错退出(代码 %d)。请检查登录状态或使用额度',
        'srv.bad_reply': '无法读取 AI 的回答。请稍后再试',
        'srv.bad_layer': '未知的大脑',
        'srv.outside': '不能打开记忆存储以外的文件',
        'srv.bad_feedback': '未知的反馈',
        'srv.need_text': '请写下现在的情况',
        'srv.bad_project': '不是已登记的项目',
        'srv.empty': '内容是空的',
        'srv.too_long': '太长了(最多 %d 字)',
        'srv.queue_fail': '无法放入海马队列: %s',
    },
}

# 명령어 파일의 설명(description)과 인자 안내(argument-hint) - 슬래시 명령 목록에 그대로 보인다
CMD = {
    'ko': {
        'app': ('brain 앱 열기 - 프로젝트별 뇌 구경, 물어보기, 먹이, 정리, 성격', ''),
        'config': ('해마 설정 - default(Sonnet medium), eco(Sonnet low), quality(Opus high). 값이 없으면 지금 설정', '[default|eco|quality|lang <ko|en|ja|zh>]'),
        'effort': ('해마 effort 바꾸기', '<low|medium|high|xhigh|max|auto>'),
        'model': ('해마 모델 바꾸기', '<sonnet|opus|haiku>'),
        'off': ('brain 끄기 - 떠올림, 학습, 밤 정리를 멈춰요 (기억은 남아요). here 를 붙이면 이 프로젝트만', '[here]'),
        'on': ('brain 켜기 - 떠올림, 학습, 밤 정리를 다시 돌려요. here 를 붙이면 이 프로젝트만', '[here]'),
        'recall': ('기억 찾기 - 파일, 심볼, API, 에러 문자열, 증상으로', '<이름>...'),
        'remember': ('기억시키기 - 해마 큐에 넣고 바로 끝나요', '<내용>'),
        'results': ('해마가 한 일 - 상태별 건수, 실패한 일, 최근 5건', ''),
        'sleep': ('밤 정리를 지금 돌리기 - 맡기기만 하고 바로 끝나요', ''),
        'status': ('brain 상태 - 켜짐, 해마 설정과 큐, 실패, 마지막 밤 정리, 최근 떠올림', ''),
        'stop': ('해마 멈추기 - 지금 하던 일이 끝나면 멈춰요', ''),
    },
    'en': {
        'app': ('Open the brain app - per-project brains, ask, feed, tidy up, persona', ''),
        'config': ('Hippocampus settings - default (Sonnet medium), eco (Sonnet low), quality (Opus high). No value shows the current settings', '[default|eco|quality|lang <ko|en|ja|zh>]'),
        'effort': ('Change the hippocampus effort', '<low|medium|high|xhigh|max|auto>'),
        'model': ('Change the hippocampus model', '<sonnet|opus|haiku>'),
        'off': ('Turn brain off - stops recall, learning and the nightly tidy-up (memories stay). Add here for this project only', '[here]'),
        'on': ('Turn brain on - recall, learning and the nightly tidy-up run again. Add here for this project only', '[here]'),
        'recall': ('Look up memories - by file, symbol, API, error string or symptom', '<name>...'),
        'remember': ('Make brain remember something - queued for the hippocampus, returns right away', '<what>'),
        'results': ('What the hippocampus did - counts by status, failed jobs, last 5', ''),
        'sleep': ('Run the nightly tidy-up now - just hands it off and returns', ''),
        'status': ('brain status - on/off, hippocampus settings and queue, failures, last tidy-up, recent recalls', ''),
        'stop': ('Stop the hippocampus - after the current job', ''),
    },
    'ja': {
        'app': ('brain アプリを開く - プロジェクトごとの脳、質問、エサ、整理、性格', ''),
        'config': ('海馬の設定 - default(Sonnet medium)、eco(Sonnet low)、quality(Opus high)。値がなければ今の設定', '[default|eco|quality|lang <ko|en|ja|zh>]'),
        'effort': ('海馬の effort を変える', '<low|medium|high|xhigh|max|auto>'),
        'model': ('海馬のモデルを変える', '<sonnet|opus|haiku>'),
        'off': ('brain をオフ - 想起、学習、夜の整理を止めます(記憶は残ります)。here を付けるとこのプロジェクトだけ', '[here]'),
        'on': ('brain をオン - 想起、学習、夜の整理を再開します。here を付けるとこのプロジェクトだけ', '[here]'),
        'recall': ('記憶を探す - ファイル、シンボル、API、エラー文字列、症状で', '<名前>...'),
        'remember': ('覚えさせる - 海馬のキューに入れてすぐ終わります', '<内容>'),
        'results': ('海馬の作業結果 - 状態別の件数、失敗した作業、最近5件', ''),
        'sleep': ('夜の整理を今すぐ実行 - 任せるだけですぐ終わります', ''),
        'status': ('brain の状態 - オン/オフ、海馬の設定とキュー、失敗、最後の夜の整理、最近の想起', ''),
        'stop': ('海馬を止める - 今の作業が終わったら止まります', ''),
    },
    'zh': {
        'app': ('打开 brain 应用 - 各项目的大脑、提问、喂食、整理、性格', ''),
        'config': ('海马设置 - default(Sonnet medium)、eco(Sonnet low)、quality(Opus high)。不带参数时显示当前设置', '[default|eco|quality|lang <ko|en|ja|zh>]'),
        'effort': ('更改海马的 effort', '<low|medium|high|xhigh|max|auto>'),
        'model': ('更改海马的模型', '<sonnet|opus|haiku>'),
        'off': ('关闭 brain - 停止回忆、学习和夜间整理(记忆会保留)。加 here 只对当前项目', '[here]'),
        'on': ('开启 brain - 恢复回忆、学习和夜间整理。加 here 只对当前项目', '[here]'),
        'recall': ('查找记忆 - 按文件、符号、API、错误字符串或症状', '<名称>...'),
        'remember': ('让 brain 记住 - 放入海马队列后立即返回', '<内容>'),
        'results': ('海马的工作结果 - 按状态统计、失败的任务、最近5个', ''),
        'sleep': ('立即运行夜间整理 - 只是交给海马,马上返回', ''),
        'status': ('brain 状态 - 开关、海马设置和队列、失败、上次夜间整理、最近的回忆', ''),
        'stop': ('停止海马 - 完成当前任务后停止', ''),
    },
}

# ---------------------------------------------------------------- 지금 등록, 프로젝트별 쉬기, 업데이트, 사용량, 백업
TEXT['ko'].update({
    'rg.queued': '이 프로젝트를 등록해 달라고 해마에게 맡겼어요: %s (%s). 1~2분 뒤부터 새 세션에서 기억이 쌓이기 시작해요',
    'rg.already': '이미 등록된 프로젝트예요: %s (%s)',
    'rg.pending': '이 프로젝트의 등록을 해마가 이미 기다리고 있어요. 잠시 뒤 /claude-brain-status 로 확인해 주세요',
    'rg.home': '홈 폴더나 드라이브 맨 위는 등록하지 않아요. 프로젝트 폴더에서 실행해 주세요',
    'rg.self': 'brain 자신의 폴더나 Claude 설정 폴더는 등록하지 않아요',
    'rg.nodir': '폴더가 없어요: %s',
    'rg.fail': '등록을 맡기지 못했어요: %s',
    'mu.off': '이 프로젝트(%s)에서는 brain 이 쉬어요. 기억은 그대로 남아요. 다시 깨우기: /claude-brain-on here',
    'mu.on': '이 프로젝트(%s)에서 brain 이 다시 일해요',
    'mu.none': '여기는 brain 에 등록된 프로젝트가 아니에요. 등록하려면: /claude-brain-register',
    'st.muted': '쉬는 프로젝트: %s',
    'st.update': '== 새 버전이 있어요 (변경 %s개, 최근: %s). 받기: /claude-brain-update',
    'us.week': '== 이번 주 사용량: 해마 %s번, 앱 %s번, 약 $%s (API 요금 기준이라 구독 요금제의 실제 청구액과는 달라요)',
    'us.none': '== 이번 주 사용량: 아직 없어요',
    'up.nogit': 'git clone 으로 설치한 경우만 업데이트할 수 있어요. README 의 설치 방법으로 다시 받아 주세요',
    'up.noupstream': '이 폴더는 원격 브랜치를 따라가지 않아서 업데이트할 수 없어요 (git branch --set-upstream-to 로 정해 주세요)',
    'up.checking': '새 버전을 확인하고 있어요...',
    'up.fetch_fail': '새 버전을 확인하지 못했어요. 네트워크를 확인해 주세요 (%s)',
    'up.latest': '이미 최신 버전이에요 (%s)',
    'up.diverged': '이 폴더에 따로 만든 커밋이 %s개 있어서 멈췄어요. 개발용 폴더라면 git pull 로 직접 받아 주세요',
    'up.dirty': '직접 고친 파일이 있어서 멈췄어요: %s. 되돌리거나 따로 보관한 뒤 다시 해 주세요',
    'up.backup': '받기 전에 기억을 통째로 복사해 뒀어요: %s',
    'up.merge_fail': '새 버전을 받지 못했어요 (%s). 기억은 그대로예요',
    'up.restored': '기억 파일 %s개를 제자리로 돌려놨어요',
    'up.done': '업데이트했어요: %s → %s',
    'up.more': '... 그 밖에 %s개',
    'up.restart': '새 Claude Code 세션부터 새 버전이 적용돼요. 앱은 /claude-brain-app 으로 다시 열어 주세요',
    'bk.made': '백업을 만들었어요 (기억 %s개): %s',
    'bk.nofile': '파일이 없어요: %s',
    'bk.notbackup': 'brain 백업 파일이 아니에요: %s',
    'bk.busy': '해마가 일하는 중이라 지금은 되살릴 수 없어요. /claude-brain-stop 으로 멈춘 뒤 다시 해 주세요',
    'bk.restored': '기억 %s개를 되살렸어요. 원래 있던 기억은 여기 옮겨 뒀어요: %s',
    'bk.moved': '프로젝트 경로 %s개를 이 컴퓨터의 홈 폴더로 바꿨어요 (%s → %s)',
    'bk.missing': '이 컴퓨터에 없는 프로젝트 폴더가 있어요: %s. 같은 위치에 두거나 그 폴더에서 /claude-brain-register 로 다시 등록해 주세요',
})
TEXT['en'].update({
    'rg.queued': 'Asked the hippocampus to register this project: %s (%s). In a minute or two, new sessions start building memories',
    'rg.already': 'Already registered: %s (%s)',
    'rg.pending': 'The hippocampus is already about to register this project. Check again shortly with /claude-brain-status',
    'rg.home': 'Your home folder or a drive root cannot be registered. Run this inside a project folder',
    'rg.self': 'brain\'s own folder and the Claude config folder are not registered',
    'rg.nodir': 'No such folder: %s',
    'rg.fail': 'Could not queue the registration: %s',
    'mu.off': 'brain is resting in this project (%s). Memories stay. To wake it: /claude-brain-on here',
    'mu.on': 'brain is working in this project (%s) again',
    'mu.none': 'This folder is not a registered project. To register it: /claude-brain-register',
    'st.muted': 'Resting projects: %s',
    'st.update': '== A new version is available (%s changes, latest: %s). Get it: /claude-brain-update',
    'us.week': '== Usage this week (runs): hippocampus %s, app %s, about $%s (API pricing, so it is not what a Pro or Max plan actually bills)',
    'us.none': '== Usage this week: nothing yet',
    'up.nogit': 'Only installs made with git clone can update. Please reinstall following the README',
    'up.noupstream': 'This folder does not track a remote branch, so it cannot update (set one with git branch --set-upstream-to)',
    'up.checking': 'Checking for a new version...',
    'up.fetch_fail': 'Could not check for a new version. Please check your network (%s)',
    'up.latest': 'Already up to date (%s)',
    'up.diverged': 'Stopped: this folder has its own commits (%s). If it is a development clone, run git pull yourself',
    'up.dirty': 'Stopped: some files were edited by hand: %s. Revert or move them, then try again',
    'up.backup': 'Copied all memories to a safe place before updating: %s',
    'up.merge_fail': 'Could not get the new version (%s). Your memories are untouched',
    'up.restored': 'Memory files put back in place: %s',
    'up.done': 'Updated: %s → %s',
    'up.more': '... and %s more',
    'up.restart': 'The new version applies from your next Claude Code session. Reopen the app with /claude-brain-app',
    'bk.made': 'Backup created (memories: %s): %s',
    'bk.nofile': 'No such file: %s',
    'bk.notbackup': 'Not a brain backup file: %s',
    'bk.busy': 'The hippocampus is working, so restoring now is not safe. Stop it with /claude-brain-stop and try again',
    'bk.restored': 'Memories restored: %s. The memories that were here are kept in: %s',
    'bk.moved': 'Project paths moved to this computer\'s home folder: %s (%s → %s)',
    'bk.missing': 'Some project folders do not exist on this computer: %s. Put them in the same place, or run /claude-brain-register inside each folder',
})
TEXT['ja'].update({
    'rg.queued': 'このプロジェクトの登録を海馬に任せました: %s (%s)。1〜2分後から、新しいセッションで記憶がたまり始めます',
    'rg.already': 'すでに登録されています: %s (%s)',
    'rg.pending': 'このプロジェクトの登録はすでに海馬の順番待ちです。少ししてから /claude-brain-status で確認してください',
    'rg.home': 'ホームフォルダやドライブの最上位は登録しません。プロジェクトのフォルダで実行してください',
    'rg.self': 'brain 自身のフォルダと Claude の設定フォルダは登録しません',
    'rg.nodir': 'フォルダがありません: %s',
    'rg.fail': '登録を依頼できませんでした: %s',
    'mu.off': 'このプロジェクト(%s)では brain がお休みします。記憶はそのままです。起こすには: /claude-brain-on here',
    'mu.on': 'このプロジェクト(%s)で brain がまた働きます',
    'mu.none': 'ここは brain に登録されたプロジェクトではありません。登録するには: /claude-brain-register',
    'st.muted': 'お休み中のプロジェクト: %s',
    'st.update': '== 新しいバージョンがあります(変更 %s 件、最新: %s)。取得: /claude-brain-update',
    'us.week': '== 今週の使用量: 海馬 %s 回、アプリ %s 回、約 $%s (API 料金での計算なので、サブスクリプションの実際の請求額とは異なります)',
    'us.none': '== 今週の使用量: まだありません',
    'up.nogit': 'git clone でインストールした場合のみ更新できます。README の手順でインストールし直してください',
    'up.noupstream': 'このフォルダはリモートブランチを追跡していないため更新できません(git branch --set-upstream-to で設定してください)',
    'up.checking': '新しいバージョンを確認しています...',
    'up.fetch_fail': '新しいバージョンを確認できませんでした。ネットワークを確認してください (%s)',
    'up.latest': 'すでに最新です (%s)',
    'up.diverged': 'このフォルダに独自のコミットが %s 個あるため止めました。開発用のフォルダなら git pull で直接取得してください',
    'up.dirty': '手で編集したファイルがあるため止めました: %s。元に戻すか別の場所に移してから、もう一度お試しください',
    'up.backup': '更新の前に記憶をまるごとコピーしました: %s',
    'up.merge_fail': '新しいバージョンを取得できませんでした (%s)。記憶はそのままです',
    'up.restored': '記憶ファイル %s 個を元の場所に戻しました',
    'up.done': '更新しました: %s → %s',
    'up.more': '... ほか %s 件',
    'up.restart': '次の Claude Code セッションから新しいバージョンが使われます。アプリは /claude-brain-app で開き直してください',
    'bk.made': 'バックアップを作りました(記憶 %s 個): %s',
    'bk.nofile': 'ファイルがありません: %s',
    'bk.notbackup': 'brain のバックアップファイルではありません: %s',
    'bk.busy': '海馬が作業中なので、今は復元できません。/claude-brain-stop で止めてから、もう一度お試しください',
    'bk.restored': '記憶 %s 個を復元しました。元の記憶はここに移しました: %s',
    'bk.moved': 'プロジェクトのパス %s 個を、このコンピューターのホームフォルダに合わせました (%s → %s)',
    'bk.missing': 'このコンピューターにないプロジェクトフォルダがあります: %s。同じ場所に置くか、そのフォルダで /claude-brain-register を実行してください',
})
TEXT['zh'].update({
    'rg.queued': '已请海马登记这个项目: %s (%s)。一两分钟后,新会话就会开始积累记忆',
    'rg.already': '已经登记过了: %s (%s)',
    'rg.pending': '海马已经在排队登记这个项目。请稍后用 /claude-brain-status 查看',
    'rg.home': '不会登记主文件夹或磁盘根目录。请在项目文件夹里运行',
    'rg.self': '不会登记 brain 自己的文件夹和 Claude 配置文件夹',
    'rg.nodir': '没有这个文件夹: %s',
    'rg.fail': '无法提交登记: %s',
    'mu.off': '在这个项目(%s)中 brain 先休息。记忆会保留。唤醒: /claude-brain-on here',
    'mu.on': '在这个项目(%s)中 brain 重新开始工作',
    'mu.none': '这里不是已登记的项目。要登记: /claude-brain-register',
    'st.muted': '休息中的项目: %s',
    'st.update': '== 有新版本(变更 %s 个,最新: %s)。获取: /claude-brain-update',
    'us.week': '== 本周用量: 海马 %s 次,应用 %s 次,约 $%s (按 API 价格计算,与订阅套餐的实际收费不同)',
    'us.none': '== 本周用量: 还没有',
    'up.nogit': '只有用 git clone 安装的才能更新。请按照 README 重新安装',
    'up.noupstream': '这个文件夹没有跟踪远程分支,无法更新(请用 git branch --set-upstream-to 设置)',
    'up.checking': '正在检查新版本...',
    'up.fetch_fail': '无法检查新版本。请检查网络 (%s)',
    'up.latest': '已经是最新版本 (%s)',
    'up.diverged': '这个文件夹有 %s 个自己的提交,已停止。如果是开发用的文件夹,请自己运行 git pull',
    'up.dirty': '有手动修改过的文件,已停止: %s。请还原或移走后再试',
    'up.backup': '更新前已把全部记忆复制到安全的位置: %s',
    'up.merge_fail': '无法获取新版本 (%s)。记忆没有变化',
    'up.restored': '已把 %s 个记忆文件放回原处',
    'up.done': '已更新: %s → %s',
    'up.more': '... 另外 %s 个',
    'up.restart': '从下一个 Claude Code 会话开始使用新版本。请用 /claude-brain-app 重新打开应用',
    'bk.made': '已创建备份(记忆 %s 个): %s',
    'bk.nofile': '没有这个文件: %s',
    'bk.notbackup': '不是 brain 的备份文件: %s',
    'bk.busy': '海马正在工作,现在恢复不安全。请用 /claude-brain-stop 停止后再试',
    'bk.restored': '已恢复 %s 个记忆。原来的记忆移到了这里: %s',
    'bk.moved': '已把 %s 个项目路径改为这台电脑的主文件夹 (%s → %s)',
    'bk.missing': '这台电脑上没有这些项目文件夹: %s。请放到相同位置,或在该文件夹中运行 /claude-brain-register',
})
CMD['ko'].update({'register': ('지금 이 프로젝트 등록하기 - 밤의 자동 등록을 기다리지 않아요', ''),
                  'update': ('brain 업데이트 - 새 버전을 받고 다시 설치해요 (기억은 그대로)', ''),
                  'backup': ('기억 백업 - 기억과 성격을 zip 하나로 (다른 컴퓨터로 옮길 때도)', '')})
CMD['en'].update({'register': ('Register this project now - no need to wait for the nightly auto-registration', ''),
                  'update': ('Update brain - get the new version and reinstall (memories stay)', ''),
                  'backup': ('Back up memories - memories and personas in one zip (also for moving computers)', '')})
CMD['ja'].update({'register': ('このプロジェクトを今すぐ登録 - 夜の自動登録を待ちません', ''),
                  'update': ('brain を更新 - 新しいバージョンを取得して入れ直します(記憶はそのまま)', ''),
                  'backup': ('記憶のバックアップ - 記憶と性格を1つの zip に(別のコンピューターへの引っ越しにも)', '')})
CMD['zh'].update({'register': ('立即登记这个项目 - 不用等夜间自动登记', ''),
                  'update': ('更新 brain - 获取新版本并重新安装(记忆保留)', ''),
                  'backup': ('备份记忆 - 把记忆和性格打包成一个 zip(换电脑时也用)', '')})

# ---------------------------------------------------------------- 큐 투입, 기억시키기, 기억 찾기 (도구 출력 - 사용자도 본다)
TEXT['ko'].update({
    'eq.need': '오류: 요청 JSON 경로가 필요해요', 'eq.queued': '큐 투입: %s', 'eq.running': '해마가 일하는 중이라 큐에 쌓아 뒀어요 (pid %s, 지금: %s)',
    'eq.started': '해마를 깨웠어요 (pid %s) - 로그 %s', 'eq.start_fail': '오류: 해마를 띄우지 못했어요. 큐에는 남아 있어요. 직접 실행: bash %s',
    'eq.perm': '알림: 권한 모드가 %s 라서 기억 쓰기가 거부돼요 (결과는 denied). 되돌리려면 %s 에 bypassPermissions 를 적어 주세요',
    'eq.unset': '미설정', 'eq.badjson': '오류: done 파일을 JSON 으로 읽지 못했어요: %s', 'eq.timeout': '%s초를 기다려도 끝나지 않았어요. 나중에 /claude-brain-status 로 확인해 주세요',
    'rm.usage': '사용법: remember.sh "<내용과 근거>" ...', 'rm.evidence': '사용자가 /claude-brain-remember 로 직접 남기라고 한 내용',
    'rc.usage': '사용법: recall.sh [--root <경로>] <이름>...',
})
TEXT['en'].update({
    'eq.need': 'Error: a request JSON path is required', 'eq.queued': 'Queued: %s', 'eq.running': 'The hippocampus is busy, so this was queued (pid %s, working on: %s)',
    'eq.started': 'Woke the hippocampus (pid %s) - log %s', 'eq.start_fail': 'Error: could not start the hippocampus. The job stays in the queue. Run it directly: bash %s',
    'eq.perm': 'Note: the permission mode is %s, so memory writes are denied (the result will be denied). To change it, write bypassPermissions to %s',
    'eq.unset': 'not set', 'eq.badjson': 'Error: could not read the done file as JSON: %s', 'eq.timeout': 'Not finished after %s seconds. Check later with /claude-brain-status',
    'rm.usage': 'Usage: remember.sh "<what and evidence>" ...', 'rm.evidence': 'The user asked brain to remember this directly with /claude-brain-remember',
    'rc.usage': 'Usage: recall.sh [--root <path>] <name>...',
})
TEXT['ja'].update({
    'eq.need': 'エラー: 要求 JSON のパスが必要です', 'eq.queued': 'キューに追加: %s', 'eq.running': '海馬が作業中なのでキューに積みました (pid %s、作業中: %s)',
    'eq.started': '海馬を起こしました (pid %s) - ログ %s', 'eq.start_fail': 'エラー: 海馬を起動できませんでした。キューには残っています。直接実行: bash %s',
    'eq.perm': 'お知らせ: 権限モードが %s なので記憶の書き込みは拒否されます (結果は denied)。戻すには %s に bypassPermissions と書いてください',
    'eq.unset': '未設定', 'eq.badjson': 'エラー: done ファイルを JSON として読めませんでした: %s', 'eq.timeout': '%s 秒待っても終わりませんでした。あとで /claude-brain-status で確認してください',
    'rm.usage': '使い方: remember.sh "<内容と根拠>" ...', 'rm.evidence': 'ユーザーが /claude-brain-remember で直接覚えるよう頼んだ内容',
    'rc.usage': '使い方: recall.sh [--root <パス>] <名前>...',
})
TEXT['zh'].update({
    'eq.need': '错误: 需要请求 JSON 的路径', 'eq.queued': '已加入队列: %s', 'eq.running': '海马正在工作,已加入队列 (pid %s,正在处理: %s)',
    'eq.started': '已唤醒海马 (pid %s) - 日志 %s', 'eq.start_fail': '错误: 无法启动海马。任务仍在队列中。直接运行: bash %s',
    'eq.perm': '提示: 权限模式是 %s,写入记忆会被拒绝 (结果为 denied)。要改回请在 %s 中写入 bypassPermissions',
    'eq.unset': '未设置', 'eq.badjson': '错误: 无法把 done 文件读成 JSON: %s', 'eq.timeout': '等待 %s 秒仍未完成。请稍后用 /claude-brain-status 查看',
    'rm.usage': '用法: remember.sh "<内容和依据>" ...', 'rm.evidence': '用户用 /claude-brain-remember 直接要求记住的内容',
    'rc.usage': '用法: recall.sh [--root <路径>] <名称>...',
})


def lang_now(lang=None):
    return lang if lang in L.LANGS else L.current()


def m(key, *args, lang=None):
    """[문구] 지금 언어(또는 lang)의 key 를 args 로 채운다. 없는 키는 한국어, 그것도 없으면 키 이름"""
    s = TEXT[lang_now(lang)].get(key) or TEXT['ko'].get(key) or key
    if args:
        try:
            return s % args
        except (TypeError, ValueError):
            return s + ' ' + ' '.join(str(a) for a in args)
    return s.replace('%%', '%')


def native(lang=None):
    """[언어 이름] 그 언어로 쓴 이름과 코드 - 예: 한국어 (ko)"""
    k = lang_now(lang)
    return '%s (%s)' % (NATIVE[k], k)


def status_counts(counter, lang=None):
    """[상태별 건수] done 3, failed 1 → 완료 3, 실패 1"""
    sep = '、' if lang_now(lang) == 'ja' else (',' if lang_now(lang) == 'zh' else ', ')
    return sep.join('%s %d' % (m('stat.' + k, lang=lang) if ('stat.' + k) in TEXT['ko'] else k, n) for k, n in counter)


def _out(text):
    """[표준 출력] Windows 콘솔 코드 페이지와 상관없이 UTF-8, 줄 끝은 \\n (셸 eval 이 \\r 을 명령으로 읽지 않게)"""
    sys.stdout.flush()
    sys.stdout.buffer.write(text.encode('utf-8'))
    sys.stdout.buffer.flush()


def render_commands(src, dst, brain, mode, lang=None):
    """[명령어 파일] 템플릿의 {{BRAIN}}, {{DESC}}, {{HINT}} 를 채워 dst 에 쓴다. 표식 줄이 있는 파일만 이 스크립트 것으로 보고 고치거나 지운다
    - mode: install(쓰기와 지우기), uninstall(지우기), refresh(이미 설치된 곳의 설명만 지금 언어로 다시 쓰기)
    - 돌려주는 값: (원하는 개수, 새로 쓴 수, 지운 수, 건너뛴 사용자 파일 목록)
    """
    mark = '<!-- brain:command'
    k = lang_now(lang)
    mine = lambda f: mark in open(f, encoding='utf-8').read()
    want = {}
    if mode in ('install', 'refresh'):
        if mode == 'refresh' and not os.path.isdir(dst):
            return 0, 0, 0, []
        for t in sorted(glob.glob(os.path.join(src, 'claude-brain-*.md'))):
            name = os.path.basename(t)
            cmd = name[len('claude-brain-'):-3]
            desc, hint = CMD[k].get(cmd) or CMD['ko'].get(cmd) or ('', '')
            text = open(t, encoding='utf-8').read().replace('{{BRAIN}}', brain).replace('{{DESC}}', desc).replace('{{HINT}}', hint)
            if not hint:
                text = '\n'.join(l for l in text.split('\n') if l.strip() != 'argument-hint: ""')
            want[name] = text
        os.makedirs(dst, exist_ok=True)
    n_add = n_del = 0
    skipped = []
    for f in glob.glob(os.path.join(dst, 'claude-brain-*.md')):
        if os.path.basename(f) not in want and mine(f) and mode != 'refresh':
            os.remove(f)
            n_del += 1
    for name, text in want.items():
        f = os.path.join(dst, name)
        if os.path.exists(f) and not mine(f):
            skipped.append(f)
            continue
        if not os.path.exists(f) or open(f, encoding='utf-8').read() != text:
            with open(f, 'w', encoding='utf-8', newline='\n') as w:
                w.write(text)
            n_add += 1
    return len(want), n_add, n_del, skipped


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else ''
    if cmd == 'sh':
        groups = tuple(g + '.' for g in a[1:])
        k = lang_now()
        keys = sorted(x for x in TEXT['ko'] if not groups or x.startswith(groups))
        lines = ['M_%s=%s' % (x.replace('.', '_'), shlex.quote(TEXT[k].get(x) or TEXT['ko'][x])) for x in keys]
        lines.append('M_native=%s' % shlex.quote(native()))
        _out('\n'.join(lines) + '\n')
        return 0
    if cmd == 'say' and len(a) > 1:
        _out(m(a[1], *a[2:]) + '\n')
        return 0
    if cmd == 'commands' and len(a) >= 5:
        n, n_add, n_del, skipped = render_commands(a[1], a[2], a[3], a[4])
        for f in skipped:
            _out(m('in.cmd_skip', f) + '\n')
        if a[4] == 'install':
            _out(m('in.cmd_on', n, a[2]) + '\n')
        elif a[4] == 'uninstall':
            _out(m('in.cmd_off', n_del) + '\n')
        return 0
    _out(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
