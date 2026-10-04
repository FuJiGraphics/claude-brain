<h1 align="center">brain</h1>
<h3 align="center">make Claude Code remember!</h3>

<p align="center">
  <a href="README.md">English</a> · <a href="README.ko.md">한국어</a> · <b>日本語</b> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-CC%20BY--ND%204.0-lightgrey.svg" alt="CC BY-ND 4.0"></a>
  <a href="https://claude.com/claude-code"><img src="https://img.shields.io/badge/Claude%20Code-Skill-d97757?logo=anthropic&logoColor=white" alt="Claude Code skill"></a>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20(beta)%20%7C%20Linux-lightgrey" alt="platforms">
  <img src="https://img.shields.io/badge/lang-EN%20%7C%20KO%20%7C%20JA%20%7C%20ZH-blue" alt="languages">
  <a href="#ベンチマーク"><img src="https://img.shields.io/badge/blind%20review-2%2F2%20wins-2a78d6" alt="benchmark"></a>
</p>

<p align="center">
  <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-ja-720p.mp4">
    <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/brain-promo-ja-preview.gif" alt="brain アプリのプレビュー" width="720">
  </a>
  <br><sub>▶ <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-ja-720p.mp4">60秒の動画を見る</a>(架空のデモデータ)</sub>
</p>

**brain は、Claude Code のための「勝手に動く」長期記憶です。**
Claude が以前なにかを学んだファイルを開いたり、コマンドを実行したり、エラーに出会ったりした瞬間、その記憶がセッションに自然に浮かびます。新しい記憶はセッションの外で会話ログから作られ、毎晩整理されて古いものは忘れられます。Claude が「覚えておくことを覚えておく」必要はありません。

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

インストール後、Claude Code で **`/claude-brain-app`** と入力するとアプリが開きます。

**目次** · [なぜ必要か](#なぜ必要か) · [何が違うか](#何が違うか) · [ベンチマーク](#ベンチマーク) · [他の方式との比較](#他の方式との比較) · [brain アプリ](#brain-アプリ) · [仕組み](#仕組み) · [インストール](#インストール) · [コマンド](#コマンド) · [コストとプライバシー](#コストとプライバシー) · [よくある質問](#よくある質問) · [制限](#制限) · [リファレンス](#リファレンス) · [ライセンス](#ライセンス)

---

## なぜ必要か

同じプロジェクトで何週間も Claude Code を使っていると、同じ教訓に何度も代償を払うことになります。

- **セッションは毎回まっさらから始まる。** 2か月前に決めたチームのルール、午後をまるごと潰した落とし穴、この機能が全体のどこにはまるのか。もう一度説明するか、抜け落ちて何かが壊れます。
- **「まずメモを確認して」は守られない。** 作者のログでは、編集前にメモを照合する強制ルールが **Edit/Write 6,300 回の 20%、Bash の書き込み 893 回の 32%** で守られませんでした。
- **呼ばれるのを待つ記憶ツールは呼ばれない。** 検索するかどうかをエージェント自身が決めるなら、「知らないことを知らない」ときほど検索しません。
- **メモは腐る。** まとめ、直し、引退させる担い手がいなければ、メモは積み重なり、互いに矛盾し、毎回のセッションに丸ごと読み込まれます。

brain はこれをすべてセッションの外に移します。セッションは何もしません。記憶が浮かぶだけです。

```
Claude が src/Payment/PaymentClient.cs を編集しようとした瞬間にセッションへ入るメッセージ(例)

[記憶] `PaymentClient` について覚えていること(過去に確認した事実で、今のコードと違う場合がある)。
- 決済のリトライは冪等キーを再利用する - 新しく作ると二重決済になる (projects/shop/lessons/payment-retry-reuses-key.md)
```

## 何が違うか

| | |
|---|---|
| 🧠 **聞かなくても浮かぶ** | フックが、いま読んだり編集したりしているファイル、新しく呼ぶ API、コマンドが扱うファイル、出たばかりのコンパイルエラーを見て、それに結びつく記憶だけを渡します。何も該当しなければ何も足しません。 |
| 🌙 **セッションの外で学ぶ** | 別に動くエージェント(*海馬*)が会話ログを振り返り、根拠付きで記憶を書きます。セッションは記録に1ターンも使いません。 |
| 🧹 **眠り、固め、忘れる** | 毎晩、各記憶の使われ方を数え、45日(決定や落とし穴は120日)使われない記憶を削除せずに隠し、重複をまとめ、リンク切れを検査します。 |
| 📜 **命令ではなく事実** | 記憶は出典付きの事実として入ります。今のコードと食い違えば今のコードが勝ちます。命令形のフック文はプロンプトインジェクションと疑われて無視されると実測で分かったので、brain は命令しません。 |
| 💸 **予算内で** | フック1回あたり約20ms、セッションあたり平均約2,000文字で、上限があります。 |
| 📱 **読めるアプリ** | `/claude-brain-app` で、プロジェクトごとの脳が何を大事にし、何を覚えたかを見て、質問し、フィードバックし、整理し、働き方を決められます。 |
| 🎭 **本当に守らせる性格** | プロジェクトごとに Claude の働き方を選べます。「必ず!」のルールはフックが強制します - 元に戻しにくいコマンドの前で確認し、変更後に検証せず終わらせません。 |
| 🌐 **多言語** | アプリ、セッションに入る文、性格を英語、韓国語、日本語、中国語で。記憶は会話した言語でたまります。 |
| 📂 **手元のただのファイル** | 記憶は Markdown ファイルです。サーバーもアカウントも収集もありません。 |

## ベンチマーク

**実際のプロジェクトで同じ機能を2回作らせました。1回は brain あり、1回はなし。** モデル、依頼、起点のコミットは同じで、それぞれ別に複製した作業コピーで実際にコードを書きました。どちらが brain か知らないレビュアー2人が評価しました。

<p align="center">
<picture><source media="(prefers-color-scheme: dark)" srcset="benchmarks/2026-09-30/score-dark.svg"><img src="benchmarks/2026-09-30/score-light.svg" alt="ブラインドレビューの点数" width="720"></picture>
</p>

| | ケース1: ルーレットのミニゲーム | ケース2: ピンボールのミニゲーム |
|---|---|---|
| 評価点(50点満点、2人平均) | **brain 34** / 素の Claude 29 | **brain 30.5** / 素の Claude 22 |
| レビュアーの選択 | brain 2 / 2 | brain 2 / 2 |
| 時間 | 9.9分 / 6.9分 | 13.9分 / 4.7分 |
| コスト(定価換算) | $2.98 / $1.96 | $3.37 / $1.12 |

**差はコードにもドキュメントにもない知識から生まれました。** brain は口頭で決めたチームのルール(シートデータは必ず TSV で受け取る)を守り、素の Claude は破りました。高くついた落とし穴を brain は2つとも避け、素の Claude は2つとも踏みました。さらに brain は機能の全体像をつかみ、既存のイベントの流れにつなげましたが、素の Claude は単独のゲームだけを作りました。

**代償:** brain は時間が1.4〜2.9倍、コストが1.5〜3.0倍かかりました。記憶を読んで確認するコストで、ケース2は作業範囲も2倍でした。ケースは2件、各1回なので、傾向ははっきりしていますが統計的に確定した結果ではありません。別の一発計画テスト(実タスク18件、モデル3種)では品質差がありませんでした。一度きりの計画ではこうした文脈知識が表に出にくいためと考えています。生データ: [`benchmarks/2026-09-30/results.json`](benchmarks/2026-09-30/results.json)

## 他の方式との比較

2026年10月時点、各プロジェクトの公式ドキュメントをもとにまとめました。大事なのは「思い出し方」の列です - 記憶をコンテキストに入れるかを、誰が、いつ決めるのか。

| | 誰が書くか | どう思い出すか | 整理と忘却 | 保存先 |
|---|---|---|---|---|
| **brain** | バックグラウンドのエージェントが会話ログから(+ ユーザーのフィードバック) | **ファイル、コマンド、エラーごとに自動で**、必要なその瞬間に | 毎晩のマージ、休眠化、強さの集計、リンク検査 | ローカルの Markdown |
| `CLAUDE.md` / rules | ユーザー(頼めば Claude) | セッション開始時に丸ごと(パスルールはそのファイルを読むとき) | なし | ローカルファイル |
| Claude Code auto memory | セッション中に Claude が | 開始時に `MEMORY.md` の先頭200行または25KB、トピックファイルは Claude が読むとき | 上限付近でまとめるよう促す | ローカル |
| [claude-mem](https://github.com/thedotmack/claude-mem) | フックが収集し、ワーカーが要約 | 開始時に最近のセッションを注入、MCP ツールで検索 | ドキュメント上なし | ローカル SQLite |
| [Mem0 MCP](https://docs.mem0.ai/platform/mem0-mcp) | エージェントが `add_memory` を呼ぶ | エージェントが検索を呼ぶ必要がある | OSS は追加のみ | クラウドまたはセルフホスト |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | エージェントが MCP でノートを書く | エージェントが検索を呼ぶ必要がある | 手動 | ローカルの Markdown |
| [MCP memory サーバー](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | エージェントがエンティティを作る | エージェントが読み取り・検索を呼ぶ必要がある | なし | ローカル JSONL |
| [Cline Memory Bank](https://docs.cline.bot/customization/memory-bank) | 「update memory bank」と言うと Cline が | タスクごとに全ファイルを読む | なし | プロジェクトの Markdown |
| [Cursor rules](https://cursor.com/docs/context/rules) | ユーザー(自動メモリは 2.1 で廃止) | 常時、説明ベース、glob | なし | プロジェクト、ダッシュボード |
| [Windsurf memories](https://docs.devin.ai/desktop/cascade/memories) | Cascade が自動で | Cascade が関係あると判断したとき | ドキュメント上なし | ローカル |
| [Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory) | Copilot が引用付きで | 使う前に現在のブランチで検証 | 28日使われなければ失効 | GitHub のサーバー |

**どれを選ぶか。** すべてのセッションに必要な少数のルールは `CLAUDE.md` に置き、brain はその横で長い尻尾を受け持ちます。複数のツールやチームで一つの記憶を共有したいなら、MCP 型の記憶(Mem0、Basic Memory)のほうが合います - brain は1台のマシン、Claude Code 専用です。長く続くプロジェクトで、高くつく知識が誰も書き残さない種類のもの(口頭の決定、苦労して見つけた落とし穴、「どう組み合わさっているか」)なら brain が向いています。brain と一緒に使うときは Claude Code の auto memory を**オフ**にすることをおすすめします([よくある質問](#よくある質問))。

## brain アプリ

`/claude-brain-app` で、スマホのような小さなウィンドウが開きます(Chrome または Edge のアプリモード、このコンピューターの中だけ)。

- **脳たち**: プロジェクトごとにキャラクターが一つ。記憶が増えると育ち(たまご、あかちゃん、こども、おとな、賢者)、機嫌は実際のシグナル(頭の重さ、海馬の失敗、睡眠、学習)から決まります。
- **吹き出し**: この脳がいちばん大事にしているものを言葉で。記憶のタイトルを見て Claude Haiku が選びます。タップするとその記憶を集めて見られます。
- **わかりやすい言葉で読む記憶**: AI のメモは電報のように短く読みにくいものです。開くと、一行の要約、なぜ覚えているか、いつ思い出すか、難しい言葉の説明が先に出て、原文は折りたたまれています。
- **はい/いいえのフィードバック**: 各記憶に「今もデプロイは release スクリプトですか?」のような質問が付きます。👍 合ってる、✏️ 変わった、⭐ 大事、🗑 いらない を押すと 📮 ポストにたまり、まとめて海馬に届きます。
- **質問する**: プロジェクトの脳と会話できます。記憶の中だけで答え、根拠にした記憶をリンクします。
- **えさをあげる**: 必ず覚えてほしいことを伝えます。
- **脳の整理**: 頭が重くなったら海馬がまとめて縮めます(削除せず保管)。始める前に何回に分けて作業するか表示します。
- **性格**: 品種(リス、フクロウ、ネコ、カメ)を選ぶか、性向を状況に自分でつなぎます。
- **日誌と設定**: 海馬がしたこと、オン/オフ、モデル、言語、テーマ。

アプリは記憶を直接書き換えません。えさ、フィードバック、整理は、海馬がいつも使うキューに渡します。

### 性格

性向は反対どうしのペア(推進/慎重、自律/好奇心、速さ/丁寧、最小/積極、簡潔/親切)で、状況(普段、元に戻しにくい作業、コードを変更した後、大きな変更、あいまいな依頼、初めて見るコード)につなぎます。強さでどれだけ強く働きかけるかが決まります。

| 強さ | 何が起きるか |
|---|---|
| 軽め | セッション開始時に一文 |
| ふつう | さらに、リクエストのたびに一行で念押し |
| 必ず! 🔒 | さらに、フックが強制: `rm -rf`、`push --force`、`reset --hard`、DB 削除、デプロイの前に確認し、N 個を超えるファイルを変える前に確認し、ビルドやテストなしで終えようとしたら一度差し戻します |

性格は決まった表からコンパイルされるので、プレビューがそのまま Claude の受け取る文です。

## 仕組み

| 部品 | 脳では | brain では |
|---|---|---|
| **cortex** | 大脳皮質 - 定着した長期記憶 | Markdown の記憶ストア。`common/`、`stacks/<スタック>/`、`projects/<スラッグ>/` の3層で、層ごとに薄い索引と記憶本文 |
| **thalamus** | 視床 - 感覚をふるい分けて意識に上げる | フック。いまのファイル、コマンド、エラーに結びつく記憶を渡し、セッション開始時にプロジェクトのマップを示し、手が空いた瞬間に振り返りを始めます |
| **hippocampus** | 海馬 - 新しい記憶を作る | バックグラウンドの `claude -p` ワーカー。cortex に書く唯一の主体で、登録、記録、振り返り、整理をします |
| **sleep** | 睡眠 - 固めて忘れる | 毎晩: 強さの集計、忘却、残りの会話の振り返り、検索失敗の学習、整理、検査 |

```
[思い出す - セッションの中]
ツール呼び出し ─ フック ─▶ thalamus ─▶ cortex の該当する記憶 ─▶ [記憶] メッセージがセッションに入る

[記録する - セッションの外]
ターン終了、圧縮の直前、セッション終了 ─▶ thalamus ─▶ 振り返り(awake) ─────────┐
毎晩 04:30 ─▶ sleep ─▶ 振り返り(scan)、検索失敗の学習、整理 ─────────────────────┴─▶ キュー ─▶ hippocampus ─▶ cortex
```

Claude Code がすでに書いている会話ログが短期記憶の役割を果たします。各区間は一度だけ処理されます。

## インストール

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

Windows では同じ2行を **Git Bash**(Claude Code が使うシェル)で実行します。何度実行しても結果は同じで、変更するファイルは `<ファイル>.brain-bak-<時刻>` にバックアップされます。インストールがすること:

1. `~/.claude/settings.json` に thalamus のフックを登録(他のフックには触れず、すべてのフックが終了コード0で終わるので、brain がツール呼び出しを止めることはありません)
2. `~/.claude/CLAUDE.md` に `[記憶]` メッセージが何かを伝える一行を追加(これがないと Claude は無視しました)
3. 毎晩 04:30 の睡眠を予約(macOS は launchd、Windows はタスク スケジューラ、Linux は cron に `scripts/sleep.sh` を自分で登録)
4. `/claude-brain-*` コマンドを作成
5. OS の言語で言語を設定(アプリか `scripts/config.sh lang ja` で変更)

**プロジェクトは自動で登録されます。** 夜のサイクルが、直近1週間に3日以上・依頼10件以上作業した git フォルダを登録します。すぐ行うなら `/claude-brain-sleep`。

**更新:** `git -C ~/.claude/skills/brain pull && bash ~/.claude/skills/brain/scripts/install.sh`。記憶は git の追跡から外れているので残ります。
**アンインストール:** `bash ~/.claude/skills/brain/scripts/install.sh --uninstall` がフック、CLAUDE.md のブロック、予約を外します。記憶はフォルダを消すまで残ります。

## コマンド

コマンドは入力したときだけ動きます。ほとんどはフックがその場で処理するので、トークンを使いません。

| コマンド | すること |
|---|---|
| `/claude-brain-app` | brain アプリを開く |
| `/claude-brain-status` | オン/オフ、海馬のキューと失敗、最後の睡眠、直近24時間の思い出し |
| `/claude-brain-on`, `/claude-brain-off` | オン、オフ(記憶は残る) |
| `/claude-brain-config [default\|eco\|quality]` | 海馬のモデル: Sonnet medium / Sonnet low / Opus high |
| `/claude-brain-model`, `/claude-brain-effort` | 海馬のモデルと effort の細かい設定 |
| `/claude-brain-sleep` | 夜のサイクルを今すぐ |
| `/claude-brain-results` | 海馬の結果の要約 |
| `/claude-brain-stop` | 今の項目が終わったら海馬を止める |
| `/claude-brain-recall <名前>...` | ファイル、シンボル、API、エラー、症状で記憶を探す |
| `/claude-brain-remember <内容>` | 覚えることをキューに入れる |

## コストとプライバシー

- **思い出し**は API 呼び出しなし。フックはローカルの Python で、1回約20ms、セッションあたり平均約2,000文字を足します。
- **海馬**はキューの項目ごとに `claude -p`(既定は Sonnet medium)を1回動かし、Claude のサブスクリプションか API 使用量を使います。作者の実測では記録の項目は中央値48ターン、9分でした。`/claude-brain-config eco` で減らせます。
- **アプリ**は吹き出し、わかりやすい説明、質問への回答に Claude Haiku(思考オフ)を呼びます。1回あたり約0.001〜0.005ドル、4〜6秒で、説明はキャッシュされます。
- **プライバシー**: 記憶、ログ、アプリはこのコンピューターに残ります。ネットワークに出るのは Claude Code がどのみち行う Claude API の呼び出しだけです。アプリは `127.0.0.1` でのみ、起動ごとに新しいトークンで開きます。
- **権限**: 海馬は承認プロンプトなしで動きます(聞く相手がいないため)。代わりに git の書き込み、`rm`、`sudo`、設定や他のスキルの編集を拒否ルールで止めます。[海馬の権限](#海馬の権限)を参照。

## よくある質問

**`CLAUDE.md` で十分では?** すべてのセッションに必要な少数のルールには最適です。ただし丸ごと読み込まれ、手で書き、自分では片付きません。brain は長い尻尾(数百の落とし穴や決定)を受け持ち、いまのファイルやエラーに関わるものだけを出します。

**Claude Code の auto memory は残すべき?** オフをおすすめします(`"autoMemoryEnabled": false`)。どちらも「前回わかったこと」を持ちますが、auto memory には直す担い手がなく毎回読み込まれるので、古い内容が新しい記憶を上書きすることがあります。

**記憶が間違っていたら?** アプリで開いて ✏️ 変わった を押します。海馬が確認して直します。記憶には確認日が付いていて、今のコードが常に記憶より優先されます。

**記憶が際限なく増えない?** 夜の睡眠が重複をまとめ、使われない記憶を隠します(検索では見つかります)。アプリの「頭の重さ」が整理の必要なタイミングを教えてくれます。

**チームで共有できる?** まだできません。記憶はマシンごとです。`cortex/` を自分で同期することはできますが、複数人の同時書き込みは想定していません。

**Cursor や Codex でも使える?** 使えません。Claude Code のフックの上に作られています。

**どの言語に対応?** アプリ、セッションに入る文、性格は英語、韓国語、日本語、中国語。記憶は会話した言語でたまります。日本語・中国語の症状文での検索は、ファイルやシンボルの一致(言語に依存しない)より弱めです。

**何を入れたか見られる?** `/claude-brain-status` が最近の思い出しの回数と文字数を、`.active/recall.log` がすべてのイベントを示します。

## 制限

- **一人のプロジェクトで測った値です**(macOS、主に Unity/C# と VS Code 拡張)。手がかりの抽出は C# のコンパイルエラーに合わせて調整しました。ファイルや API の一致は言語に依存しません。
- **Windows 対応は新しく加わったばかり(beta)です。** パス、フック、タスク スケジューラ、アプリを移植してレビューしましたが、実機の Windows ではまだ動かしていません。問題があれば issue で教えてください。
- **文脈が大事な作業では時間とトークンが余計にかかります**(ベンチマーク参照)。単発のスクリプトではなく、数週間単位で得をします。
- **海馬はこのコンピューターで監督なしに動くエージェントです**(拒否ルールあり)。気になる場合は `scripts/hippocampus-perm.mode` を `acceptEdits` にすると、書き込まずに判定だけを残します。
- **まだチーム向けではなく**、Claude Code 専用です。

## リファレンス

<details><summary><b>思い出しの詳細(thalamus)</b></summary>

フックは SessionStart、UserPromptSubmit、PreToolUse(Edit、Write、MultiEdit、NotebookEdit、Bash、AskUserQuestion)、PostToolUse(Read)、PostToolUseFailure(Bash)、SubagentStart、Stop、PreCompact、SessionEnd に登録され、登録済みのプロジェクトの中だけで動きます。

| フック | 手がかり |
|---|---|
| SessionStart | プロジェクトの要旨、プロジェクトの `INDEX.md`(2,500文字まで)、手順カード |
| PostToolUse (Read) | 開いたファイル名 |
| PreToolUse (Edit, Write) | 編集するファイル、編集で新しく呼ぶ API |
| PreToolUse (Bash) | コマンドが読み書きするファイル、インラインコードの API |
| PostToolUseFailure (Bash) | C# コンパイルエラーのファイルとコード、例外名と最初のプロジェクトのフレーム |
| Stop, PreCompact, SessionEnd | 思い出しはなし。新しい会話が十分たまっていれば振り返りを開始 |

- 一度に1〜2件(Bash は1件)、1件240文字、セッションあたり最大40件または9,000文字。同じ記憶はセッションに一度だけ。
- 4件以上の異なる記憶に当たる手がかりはありふれたものとみなし、ファイル名にそれを含む記憶だけを残します。
- 収まりきらないほど当たったら、最近使われた記憶を優先します(14日以内 +2、45日以内 +1)。

過去の431セッションを再生し、371件の思い出しを Sonnet が判定しました。邪魔と判定された割合はファイルを開くとき0〜3%、編集直前8〜20%、コマンドが扱うファイル約10% なので使い、依頼文(64%)、「動かない」という結論(75%)、CLI 名(64%)はノイズが多いので使いません。
</details>

<details><summary><b>記憶ストア(cortex)</b></summary>

```
cortex/
├── registry.md            # パスのプレフィックス、プロジェクトのスラッグ、スタック、スタックのバージョン、メモ
├── common/                # スタックに依存しない記憶(ツールの落とし穴、一般原則)
├── stacks/<スタック>/     # エンジンやフレームワーク全般
└── projects/<スラッグ>/   # プロジェクト固有(構造、エントリーポイント、規約の場所)
```

層は「この事実がどこまで一般化できるか」で分けます。各層に薄い索引があり、索引の行の最初のリンクが記憶の本文です。調査のコストを払って分かったこと、ユーザーが言わない限り分からないことだけを記録し、コードを開けば数秒で確認できることは記録しません。
</details>

<details><summary><b>記録、睡眠、忘却、強さ</b></summary>

| | awake | sleep |
|---|---|---|
| 開始 | ターン終了、圧縮の直前、セッション終了 | 毎日 04:30(または `/claude-brain-sleep`) |
| 対象 | 前回の位置以降に増えた会話 | 起きている間に処理されなかった区間 |
| 条件 | 4,000バイト以上かつ顕著さ6以上(圧縮直前とセッション終了は3以上)。同じログは20分に1回 | 顕著さ6以上、上位4件 |

顕著さは、ユーザーの訂正(3)、決定(3)、「覚えて」(5)、権限の拒否(2)、ツールの失敗(1、最大5)、繰り返しの検索(1、最大3)、長いセッション(1)を足したものです。

夜のサイクル: 強さの集計 → 忘却 → 残りの振り返り → 検索失敗の学習 → いちばん長く整理していない3つのかけらの整理 → 検査。

忘却: 記憶の最終使用日は、思い出し、閲覧、検索ヒット、編集、インストール日のうち最も遅い日です。45日(ユーザーの決定、落とし穴、事故、損失に触れる記憶は120日)たつと索引の行が `dormant.md` に移ります。本文は残り検索でも見つかり、また使われると元に戻ります。完全な削除はありません。

`cortex/.hippocampus/strength.json` は記憶ごとに `{shown, opened, grepped, last}` を持ち、忘却、順位付け、整理の判断に使います。
</details>

<details><summary><b>海馬の権限</b></summary>

海馬は既定で `bypassPermissions` で動きます(`scripts/hippocampus-perm.mode`)。非対話の `claude -p` プロセスであり、Claude Code は `~/.claude/` を保護パスとして扱うので、これがないとすべての書き込みが、誰も出せない承認を待つことになります。

- 海馬のプロセスにだけ適用されます。あなたのセッションの権限はそのままです。
- ツールは Read、Write、Edit、Grep、Glob、Bash、WebFetch、WebSearch に限られ、MCP サーバーやスキルは付けません。
- 拒否ルールが git の書き込み、`rm`、`sudo`、`find -delete`、そして `settings.json`、`CLAUDE.md`、フック、あらゆるスキルのコード(このスキル自身を含む)の編集を止めます。拒否ルールはこのモードでも有効です。
- オフにするには: `echo acceptEdits > ~/.claude/skills/brain/scripts/hippocampus-perm.mode`。項目は `denied` で終わり、判定は `hippocampus-ctl.sh results` に残ります。
</details>

<details><summary><b>設計の根拠となった実測</b></summary>

| 事実 | 根拠 |
|---|---|
| フックがコンテキストを足せるのは SessionStart、UserPromptSubmit、PreToolUse、PostToolUse、PostToolUseFailure、Stop | Claude Code 2.1.283 での隔離実行、2026-09-29 |
| 命令形のフック文はプロンプトインジェクションと疑われ、従われなかった | 同じ実験 |
| `CLAUDE.md` の一行がないと、`[記憶]` は出所不明の挿入として無視された | 同日 |
| 編集前にメモを照合する強制ルールが、Edit/Write 6,300回中1,264回、Bash の書き込み893回中290回で守られなかった | brain 以前の構造のゲートログ(shadow モード) |
| セッションが起動しなければならない整理は動かなかった: キュー668件、記録322件、整理0件 | brain 以前の構造のキュー履歴 |
| アプリの Haiku 呼び出し: 思考オンで38秒/0.024ドル、オフで6秒/0.004ドル | 2026-10-05 |
</details>

<details><summary><b>フォルダ構成と動作要件</b></summary>

```
brain/
├── SKILL.md, commands/        # /brain コントロールパネルと /claude-brain-* コマンドのテンプレート
├── agents/hippocampus.md      # 海馬への指示
├── scripts/                   # thalamus.py(フック)、nbsearch.py(検索)、hippocampus-*.sh、sleep.sh、
│                              # persona.py(性格)、lang.py(言語)、plat.py(OS の違い)、install.sh …
├── editor/                    # brain アプリ(server.py + web/)
├── promo/                     # 紹介動画のツール(デモの脳、録画)
├── cortex/                    # 記憶(このコンピューターで育つ、git で追跡しない)
└── .active/                   # 実行時の状態(git で追跡しない)
```

| | |
|---|---|
| Claude Code | 2.1.28x 以降(2.1.283 で検証) |
| Python | 3.7 以上(`python3`、`python`、`py` のいずれか) |
| `claude` CLI | PATH 上にあること(海馬とアプリが呼ぶ) |
| シェル | bash 3.2 以上。Windows は Git Bash(Git for Windows) |
| アプリのウィンドウ | Chrome(macOS、Linux)または Edge(Windows)のアプリモード、なければ既定のブラウザ |
| OS | macOS(開発・計測した環境)、Windows(beta)、Linux(動作、睡眠は cron で) |
</details>

<details><summary><b>n-worker との関係</b></summary>

brain は [n-worker](https://github.com/FuJiGraphics/n-worker) から切り出したスキルで、前身はノートブックと curator デーモンでした。どちらも単独で動きます。両方入れると n-worker のセッションにも `[記憶]` が浮かび、判断材料として使われます。
</details>

## ライセンス

[CC BY-ND 4.0](LICENSE)。Copyright (c) 2026 Cheol Jin Choi (FuJiGraphics)。

改変していないものに限り、商用利用と再配布ができます(作者、リポジトリの URL、ライセンスの表示が必要)。改変版の配布は許可なくできません。あなたのマシンで育つ記憶はあなたのものであり、このライセンスの対象外です。
