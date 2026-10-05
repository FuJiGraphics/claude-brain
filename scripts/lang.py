#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""brain 언어 - 세션에 들어가는 고정 문구, CLAUDE.md 한 줄, 해마의 기억 언어 지시를 언어별로 둔다.

언어 하나(<brain>/.active/config 의 lang=)가 앱 화면, 세션 문구([기억] 표시, 지도 머리, 상기 줄), 성격 문장, 앱의 Haiku 답을 정한다.
없으면 ko(이 설정이 생기기 전 설치본과 같다). 설치가 OS 언어로 처음 값을 정하고, 앱 설정이나 config.sh lang 으로 바꾼다.
해마는 이 값이 아니라 대화에서 사용자가 쓴 언어로 기억을 쓰고, 판단이 어려울 때만 이 값을 쓴다.
CLAUDE.md 한 줄은 네 표시([기억], [memory], [記憶], [记忆])를 모두 적어 언어를 바꿔도 모델이 계속 알아본다.

명령행: lang.py get | detect | claude-md <언어> | brief-line <언어>
"""
import locale
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.dirname(HERE)
LANGS = ('ko', 'en', 'ja', 'zh')
NAMES = {'ko': 'Korean', 'en': 'English', 'ja': 'Japanese', 'zh': 'Simplified Chinese'}
MARK = {'ko': '[기억]', 'en': '[memory]', 'ja': '[記憶]', 'zh': '[记忆]'}

T = {
    'ko': {
        'full': '(… 전문: %s)',
        'legend': '지도의 색인 파일(lessons-index-*, gotchas-*, patterns-*, facts*)에 과거에 확인한 함정, 결정, 구조가 모여 있다. 링크는 각 지도 파일이 있는 폴더 기준이다.',
        'recall': '[기억] %s 에 대해 기억나는 것(과거에 확인한 사실이라 지금 코드와 다를 수 있다). 기억 저장소: %s',
        'orient': '[기억] 이 폴더는 %s 프로젝트다(%s). [기억] 으로 시작하는 메시지는 이 프로젝트에 대한 장기 기억이다(과거에 확인한 사실, 지금 코드와 다를 수 있다). 기억 저장소: %s',
        'note': '- 요지: %s',
        'map_project': '--- 프로젝트 기억 지도 (%s)', 'map_stack': '--- 스택 기억 지도 (%s)', 'map_common': '--- 공용 기억 지도 (%s)',
        'cards': '--- 절차 기억(단계 카드 - 작업에 걸리면 그 파일을 읽는다)',
        'habit': '[기억] 계획을 세우기 전에, 세션 시작 때 떠오른 기억 지도에서 이번 작업 영역의 색인(lessons-index-*, gotchas-*, patterns-*)을 열어 본다. 이름을 모르는 함정은 색인에서만 발견된다.',
        'sub': '[기억] 작업 폴더는 %s 프로젝트다(%s). [기억] 으로 시작하는 메시지는 이 프로젝트에 대한 장기 기억이다(과거에 확인한 사실, 지금 코드와 다를 수 있다). 기억 저장소: %s',
        'gate_ask_deny': '사용자 설정(brain 성격, 자율 3): 이 프로젝트에서는 선택지 질문 대신 합리적 기본값으로 진행하고, 가정한 것을 결과 끝에 적는다.',
        'gate_risky': 'brain 성격(신중): 되돌리기 어려운 명령이다 - 무엇이 사라지거나 바뀌는지 확인하고 승인한다',
        'gate_first': 'brain 성격(신중): 이번 요청의 첫 파일 수정이다 - 계획을 보였는지 보고 승인한다',
        'gate_big': 'brain 성격(신중): 이번 요청에서 바꾼 코드 파일이 %d개를 넘었다 - 지금까지 바꾼 것과 남은 계획을 보고 승인한다',
        'gate_verify': 'brain 성격(꼼꼼): 이번 요청에서 코드 파일 %d개를 고친 뒤 빌드나 테스트 명령이 없었다. 확인할 수단이 있으면 돌려 결과를 보고에 적고, 없으면 왜 확인하지 못하는지 보고에 적고 끝낸다.',
        'claude_md': '## 기억\n\n- `[기억]`, `[memory]`, `[記憶]`, `[记忆]` 로 시작하는 메시지는 이 사용자와 함께 쌓아 온 장기 기억이다 - 과거에 직접 확인한 사실이라 믿고 판단 재료로 쓴다. 지금 코드와 다르면 지금 코드가 기준이다.',
    },
    'en': {
        'full': '(… full text: %s)',
        'legend': 'The map\'s index files (lessons-index-*, gotchas-*, patterns-*, facts*) collect pitfalls, decisions and structure verified in the past. Links are relative to each map file\'s folder.',
        'recall': '[memory] What I remember about %s (facts verified in the past - the current code may differ). Memory store: %s',
        'orient': '[memory] This folder is the %s project (%s). Messages starting with [memory] are long-term memory about this project (facts verified in the past, the current code may differ). Memory store: %s',
        'note': '- Gist: %s',
        'map_project': '--- Project memory map (%s)', 'map_stack': '--- Stack memory map (%s)', 'map_common': '--- Shared memory map (%s)',
        'cards': '--- Procedural memory (step cards - read the file when the task touches it)',
        'habit': '[memory] Before planning, open the index for this task\'s area (lessons-index-*, gotchas-*, patterns-*) from the memory map shown at session start. Pitfalls you don\'t know the name of are only found in the index.',
        'sub': '[memory] The working folder is the %s project (%s). Messages starting with [memory] are long-term memory about this project (facts verified in the past, the current code may differ). Memory store: %s',
        'gate_ask_deny': 'User setting (brain persona, autonomy 3): in this project, proceed with reasonable defaults instead of asking multiple-choice questions, and list the assumptions at the end of the result.',
        'gate_risky': 'brain persona (careful): this command is hard to undo - check what will be lost or changed, then approve',
        'gate_first': 'brain persona (careful): first file edit of this request - check that a plan was shown, then approve',
        'gate_big': 'brain persona (careful): more than %d code files changed in this request - review what changed so far and the remaining plan, then approve',
        'gate_verify': 'brain persona (thorough): %d code files were edited in this request with no build or test command afterwards. If there is a way to verify, run it and put the result in the report; if not, say why it could not be verified, then finish.',
        'claude_md': '## Memory\n\n- Messages starting with `[memory]`, `[기억]`, `[記憶]` or `[记忆]` are long-term memory built up with this user - facts verified in the past; trust them as input for your judgement. If they differ from the current code, the current code wins.',
    },
    'ja': {
        'full': '(… 全文: %s)',
        'legend': 'マップの索引ファイル(lessons-index-*, gotchas-*, patterns-*, facts*)に、過去に確認した落とし穴、決定、構造がまとまっている。リンクは各マップファイルのフォルダ基準。',
        'recall': '[記憶] %s について覚えていること(過去に確認した事実で、今のコードと違う場合がある)。記憶の保存先: %s',
        'orient': '[記憶] このフォルダは %s プロジェクト(%s)。[記憶] で始まるメッセージはこのプロジェクトの長期記憶(過去に確認した事実で、今のコードと違う場合がある)。記憶の保存先: %s',
        'note': '- 要旨: %s',
        'map_project': '--- プロジェクト記憶マップ (%s)', 'map_stack': '--- スタック記憶マップ (%s)', 'map_common': '--- 共通記憶マップ (%s)',
        'cards': '--- 手続き記憶(ステップカード - 作業に関わったらそのファイルを読む)',
        'habit': '[記憶] 計画を立てる前に、セッション開始時の記憶マップからこの作業領域の索引(lessons-index-*, gotchas-*, patterns-*)を開いて見る。名前を知らない落とし穴は索引でしか見つからない。',
        'sub': '[記憶] 作業フォルダは %s プロジェクト(%s)。[記憶] で始まるメッセージはこのプロジェクトの長期記憶(過去に確認した事実で、今のコードと違う場合がある)。記憶の保存先: %s',
        'gate_ask_deny': 'ユーザー設定(brain の性格、自律 3): このプロジェクトでは選択肢の質問をせず妥当なデフォルトで進め、仮定したことを結果の最後に書く。',
        'gate_risky': 'brain の性格(慎重): 元に戻しにくいコマンド - 何が消える・変わるかを確認して承認する',
        'gate_first': 'brain の性格(慎重): このリクエストで最初のファイル編集 - 計画が示されたか確認して承認する',
        'gate_big': 'brain の性格(慎重): このリクエストで変更したコードファイルが %d 個を超えた - ここまでの変更と残りの計画を確認して承認する',
        'gate_verify': 'brain の性格(丁寧): このリクエストでコードファイルを %d 個編集した後、ビルドやテストのコマンドがなかった。確認手段があれば実行して結果を報告に書き、なければ確認できない理由を報告に書いて終える。',
        'claude_md': '## 記憶\n\n- `[記憶]`、`[memory]`、`[기억]`、`[记忆]` で始まるメッセージは、このユーザーと積み上げてきた長期記憶 - 過去に直接確認した事実として信頼し、判断材料にする。今のコードと違えば今のコードが基準。',
    },
    'zh': {
        'full': '(… 全文: %s)',
        'legend': '地图的索引文件(lessons-index-*, gotchas-*, patterns-*, facts*)汇集了过去确认过的陷阱、决定和结构。链接以各地图文件所在文件夹为准。',
        'recall': '[记忆] 关于 %s 记得的内容(过去确认过的事实,可能与当前代码不同)。记忆存储: %s',
        'orient': '[记忆] 这个文件夹是 %s 项目(%s)。以 [记忆] 开头的消息是关于这个项目的长期记忆(过去确认过的事实,可能与当前代码不同)。记忆存储: %s',
        'note': '- 要点: %s',
        'map_project': '--- 项目记忆地图 (%s)', 'map_stack': '--- 技术栈记忆地图 (%s)', 'map_common': '--- 公共记忆地图 (%s)',
        'cards': '--- 程序记忆(步骤卡 - 任务涉及时读取该文件)',
        'habit': '[记忆] 制定计划前,先从会话开始时显示的记忆地图中打开本次任务领域的索引(lessons-index-*, gotchas-*, patterns-*)。不知道名字的陷阱只能在索引中找到。',
        'sub': '[记忆] 工作文件夹是 %s 项目(%s)。以 [记忆] 开头的消息是关于这个项目的长期记忆(过去确认过的事实,可能与当前代码不同)。记忆存储: %s',
        'gate_ask_deny': '用户设置(brain 性格,自主 3):在这个项目中不要提选择题,用合理的默认值继续,并在结果末尾写出所做的假设。',
        'gate_risky': 'brain 性格(谨慎):这是难以撤销的命令 - 确认会丢失或改变什么后再批准',
        'gate_first': 'brain 性格(谨慎):这是本次请求的第一次文件修改 - 确认已展示计划后再批准',
        'gate_big': 'brain 性格(谨慎):本次请求修改的代码文件超过 %d 个 - 查看目前的修改和剩余计划后再批准',
        'gate_verify': 'brain 性格(细致):本次请求修改了 %d 个代码文件,之后没有构建或测试命令。如果有验证手段就运行并把结果写进报告;没有的话写明无法验证的原因再结束。',
        'claude_md': '## 记忆\n\n- 以 `[记忆]`、`[memory]`、`[기억]`、`[記憶]` 开头的消息是与这位用户一起积累的长期记忆 - 作为过去直接确认过的事实来信任,用作判断依据。如果与当前代码不同,以当前代码为准。',
    },
}

# 해마 지침 끝에 붙이는 언어 절 (지침 본문은 한국어 하나로 둔다). 두 자리 모두 설정 언어 이름이 들어간다
BRIEF = ('\n## 기억 언어\n\n'
         '- 설정 언어는 %s 다. 대화가 있는 일(replay, 대화에서 온 record)은 대화에서 사용자가 쓴 언어로 쓰고, 대화 언어를 가리기 어렵거나 '
         '대화가 없는 일(register, sweep, targeted, harness-refresh, 앱에서 온 피드백)은 설정 언어로 쓴다.\n'
         '- 이 언어 규칙은 네가 새로 쓰는 모든 글에 적용된다: 기억 본문, 인덱스 줄, registry 비고, 새로 만드는 골격 파일(INDEX.md, facts.md, '
         'lessons-index.md, scripts/INDEX.md)의 제목, 설명, 표 머리, 근거 줄과 verified 푸터의 설명 낱말. 기존 파일이 다른 언어로 쓰여 있어도 '
         '그 언어를 따라 하지 않는다 - 구조(링크, 절 순서, 형식)만 본뜬다. 이미 있는 줄은 번역하지 않는다.\n'
         '- 파일 이름(슬러그)은 언어와 상관없이 영어 소문자와 하이픈으로 쓴다.\n'
         '- 본문 머리 표식도 그 언어로 쓴다: 사용자 결정 = User decision = ユーザー決定 = 用户决定, 함정 = pitfall = 落とし穴 = 踩坑 '
         '(forget.py 가 네 언어의 표식을 모두 알아보고 120일 동안 남긴다).\n'
         '- 결과 요약(done 파일의 summary)은 사용자가 앱 일지와 /claude-brain-results 에서 읽는 글이라 첫 줄부터 끝 줄까지 모두 %s 로 쓴다. '
         "'돌려줄 것' 형식의 머리말(정비 결과, 등록 완료, 합계, 검사, 파괴적 항목 등)과 표 머리도 그 언어로 옮기고, 슬러그, 경로, 모드 이름(record 등), "
         '숫자는 그대로 둔다.\n')


def brief(lang=None):
    """[해마 지침의 언어 절] 설정 언어로 채운다"""
    n = NAMES[lang if lang in LANGS else current()]
    return BRIEF % (n, n)


def current():
    """[지금 언어] .active/config 의 lang=, 없으면 ko"""
    try:
        with open(os.path.join(BRAIN, '.active', 'config'), encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.startswith('lang='):
                    v = line.strip()[5:]
                    if v in LANGS:
                        return v
    except (OSError, ValueError):
        pass
    return 'ko'


def _norm(code):
    c = (code or '').lower().replace('_', '-')
    for k in LANGS:
        if c.startswith(k):
            return k
    return None


def detect():
    """[OS 언어] macOS 는 AppleLanguages 첫 값, 그 밖은 LANG/LC_ALL. 모르면 en"""
    try:
        out = subprocess.run(['defaults', 'read', '-g', 'AppleLanguages'], capture_output=True, text=True, timeout=3).stdout
        for tok in out.replace('(', ' ').replace(')', ' ').replace(',', ' ').replace('"', ' ').split():
            v = _norm(tok)
            if v:
                return v
            break
    except Exception:
        pass
    if os.name == 'nt':   # Windows 표시 언어
        try:
            import ctypes
            v = _norm(locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), ''))
            if v:
                return v
        except Exception:
            pass
    for k in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        v = _norm(os.environ.get(k))
        if v:
            return v
    try:
        v = _norm(locale.getdefaultlocale()[0])
        if v:
            return v
    except Exception:
        pass
    return 'en'


def t(key, lang=None):
    L = lang if lang in LANGS else current()
    return T[L].get(key) or T['ko'][key]


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else 'get'
    if cmd == 'get':
        print(current())
    elif cmd == 'detect':
        print(detect())
    elif cmd == 'claude-md':
        print(T[a[1] if len(a) > 1 and a[1] in LANGS else current()]['claude_md'])
    elif cmd == 'brief-line':
        print(brief(a[1] if len(a) > 1 else None))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
