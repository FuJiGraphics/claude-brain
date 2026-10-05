<h1 align="center">brain</h1>
<p align="center"><b>Claude Code が前回わかったことを覚えておけるようにする、長期記憶のスキルです</b></p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.ko.md">한국어</a> · <b>日本語</b> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-CC%20BY--ND%204.0-lightgrey.svg" alt="CC BY-ND 4.0"></a>
  <a href="https://claude.com/claude-code"><img src="https://img.shields.io/badge/Claude%20Code-Skill-d97757?logo=anthropic&logoColor=white" alt="Claude Code skill"></a>
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20(beta)%20%7C%20Linux-lightgrey" alt="platforms">
  <img src="https://img.shields.io/badge/lang-JA%20%7C%20EN%20%7C%20KO%20%7C%20ZH-blue" alt="languages">
</p>

<p align="center">
  <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-ja-720p.mp4">
    <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/brain-promo-ja-preview.gif" alt="brain アプリのプレビュー" width="720">
  </a>
  <br><sub>▶ <a href="https://cdn.jsdelivr.net/gh/FuJiGraphics/claude-brain@media/brain-promo-ja-720p.mp4">1分の動画で見る</a>(画面のプロジェクトと記憶はデモ用に作ったものです)</sub>
</p>

同じプロジェクトで Claude Code と数週間ほど作業していると、先週一緒に突き止めた落とし穴や、2か月前に決めたルールをもう一度説明する場面が出てきます。説明し忘れると、同じミスがそのまま繰り返されることもあります。

brain はそうした内容を会話の中から自動で選んで覚えておきます。そしてあとで、Claude がその記憶に関係するファイルを開いたり、コマンドを実行したり、エラーに出会ったりすると、その記憶を Claude に渡します。わざわざ呼び出す必要はなく、記憶のファイルはすべてお使いのコンピューターに普通の Markdown として保存されます。

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

インストールしたら、いま作業しているプロジェクトのフォルダで Claude Code に `/claude-brain-register` と一度入力してください。そのプロジェクトからすぐに記憶がたまり始めます。あとはいつも通り使うだけで、どんな記憶がたまったか気になったときは `/claude-brain-app` と入力してみてください。

## インストールすると変わること

**同じ説明を繰り返さなくて済みます。** たとえば Claude が決済のコードを直そうとした瞬間、brain は以前に確かめた事実をこのように渡します。

```
[記憶] `PaymentClient` について覚えていること(過去に確認した事実で、今のコードと違う場合がある)。
- 決済のリトライは冪等キーを使い回す - 新しく作ると二重決済になる (projects/shop/lessons/payment-retry-reuses-key.md)
```

セッションの開始時にプロジェクトの記憶の地図(索引)を一度広げておき、作業中はその場面に関係のある記憶だけを1〜2件ずつ渡します。当てはまるものがなければ、それ以上は入れません。毎回のセッションに長い文書を丸ごと読み込ませるやり方とは違います。

**覚えてと頼まなくても記憶がたまります。** セッションの外で別に動くエージェント(brain では*海馬*と呼んでいます)が会話の記録を振り返り、長く残す価値のあるものだけを根拠つきで書き留めます。ユーザーによる訂正、決めたこと、時間をかけて突き止めた原因などです。

**記憶が自分で整理されます。** 毎晩、重なった記憶をまとめ、45日以上使われていない記憶は消さずに奥へしまいます。決めたことや落とし穴のような大事な記憶は120日間残しておきます。

**目で見て直せます。** brain アプリでは、プロジェクトごとに育つ脳を眺めたり、AI が書いたメモをやさしい言葉で読んだり、間違った記憶をボタンひとつで正したりできます。

<p align="center">
  <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/brain-shots-ja.png" alt="brain アプリの画面 - プロジェクトの脳、やさしい言葉の説明、質問、性格" width="100%">
</p>

## 本当に違いは出るのでしょうか

実際のプロジェクトで、同じ機能を2回実装してもらいました。1回は brain をつけて、もう1回はつけずに。モデル、依頼、開始コミットはそろえ、どちらが brain なのかを知らない Opus 5.5 の審査モデル2つが採点しました。

<p align="center">
<picture><source media="(prefers-color-scheme: dark)" srcset="benchmarks/2026-09-30/score-dark.svg"><img src="benchmarks/2026-09-30/score-light.svg" alt="審査の点数" width="720"></picture>
</p>

| | 事例 1: ルーレットのミニゲーム | 事例 2: ピンボールのミニゲーム |
|---|---|---|
| 審査の点数(50点満点、審査2回の平均) | **brain 34** / 素の状態 29 | **brain 30.5** / 素の状態 22 |
| 審査モデルの選択 | brain 2 / 2 | brain 2 / 2 |
| かかった時間 | 9.9分 / 6.9分 | 13.9分 / 4.7分 |
| 費用(API 料金換算) | $2.98 / $1.96 | $3.37 / $1.12 |

差が出たのは、コードやドキュメントに書かれていない知識でした。

- 会話の中だけで決めたルール: このプロジェクトでは、シートのデータを TSV で受け取ると2か月前の会話で決めていて、リポジトリのどこにも書かれていませんでした。brain 側はこのルールを守り、素の状態の側はローカルの JSON を直接書き換えました。
- 苦労して突き止めた落とし穴: こうした落とし穴が2つあり、brain 側は2つとも避け、素の状態の側は2つとも踏みました。「キャッシュされたポップアップを開き直すと初期化が走らない」がその1つです。
- 機能が収まるべき場所: brain 側は既存のイベントの流れにマネージャー、ポップアップ、精算までつなぎ、素の状態の側は独立したミニゲームだけを作りました。

その代わり、時間と費用は多くかかりました(時間は1.4〜3.0倍、費用は1.5〜3.0倍)。増えた分の多くは記憶を読んで確かめるためのもので、事例 2 では brain 側が既存のイベントの流れまでつないだため、作業の範囲も2倍ほど広くなりました。使い捨てのスクリプトよりも、数週間以上続くプロジェクトで効果が大きくなります。

<details><summary>試験の方法と限界</summary>

- モデルはどちらも Sonnet 5.5、effort medium です。
- 素の状態の側は `claude -p --restricted` で CLAUDE.md、自動メモリ、ユーザー設定をすべて切り、リポジトリのファイルだけを読めるようにしました。brain 側は同じ条件に brain のフックと記憶の案内1行だけを加えました。会話の記録を調べ、brain 側にだけ記憶が実際に入ったことを確かめています。
- 審査は Opus 5.5 のモデル2つが担当し、規約、既存の構造の活用、重複、動作の正しさ、完成度を見ました。
- 事例は2件、各条件1回なので、統計的に確定した結果ではなく、初期の兆しとして見ていただければと思います。同じ日に行った「計画を1回立てる」試験(実際の課題18件、モデル3種)では品質の差は出ませんでした。1回きりの計画では、こうした文脈の知識が表に出る場面が少なかったと考えています。
- 元データ: [`benchmarks/2026-09-30/results.json`](benchmarks/2026-09-30/results.json)

</details>

## ほかの方法と何が違うのでしょうか

いちばん大きな違いは、記憶が **いつ、誰の判断で** コンテキストに入るかです。2026年10月時点の各プロジェクトの公式ドキュメントをもとにまとめました。

| | 誰が記憶を書くか | どう思い出されるか | 整理と忘却 | 保存場所 |
|---|---|---|---|---|
| **brain** | バックグラウンドのエージェントが会話の記録から(+ ユーザーのフィードバック) | **ファイル、コマンド、エラーに合わせて自動で**、必要な瞬間に | 毎晩の統合、しまい込み、使用回数の集計、リンク検査 | ローカルの Markdown |
| `CLAUDE.md` / rules | ユーザー(頼めば Claude) | セッション開始時に丸ごと | なし | ローカルのファイル |
| Claude Code の自動メモリ | セッション中に Claude が | 起動時に `MEMORY.md` の先頭、トピックファイルは Claude が読むとき | 上限付近で整理を案内 | ローカル |
| [claude-mem](https://github.com/thedotmack/claude-mem) | フックが集め、ワーカーが要約 | 起動時に最近のセッションを注入、MCP で検索 | ドキュメント上なし | ローカルの SQLite |
| [Mem0 MCP](https://docs.mem0.ai/platform/mem0-mcp) | エージェントが `add_memory` を呼ぶ | エージェントが検索する必要あり | OSS は追加のみ | クラウドまたはセルフホスト |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | エージェントが MCP でノートを書く | エージェントが検索する必要あり | 手動 | ローカルの Markdown |
| [MCP memory サーバー](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | エージェントがエンティティを作る | エージェントが読むか検索する必要あり | なし | ローカルの JSONL |
| [Cline Memory Bank](https://docs.cline.bot/customization/memory-bank) | 「update memory bank」と言えば Cline が | 作業のたびに全ファイルを読む | なし | プロジェクトの Markdown |
| [Cursor rules](https://cursor.com/docs/context/rules) | ユーザー(自動メモリは 2.1 で削除) | 常時、説明ベース、glob | なし | プロジェクト、ダッシュボード |
| [Windsurf memories](https://docs.devin.ai/desktop/cascade/memories) | Cascade が自動で | Cascade が関係あると判断したとき | ドキュメント上なし | ローカル |
| [Copilot Memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory) | Copilot が根拠の引用とともに | 使う前に現在のブランチで検証 | 28日使われないと期限切れ | GitHub のサーバー |

どれを選べばよいでしょうか? すべてのセッションに必要な少数のルールは、`CLAUDE.md` に置くのがいちばんです。brain はその隣で、`CLAUDE.md` に書ききれない何百もの小さな落とし穴や決めたことを受け持ちます。複数のツールや複数の人で記憶を共有したい場合は、Mem0 や Basic Memory のような MCP の記憶のほうが合っています。brain は1台のマシンで、Claude Code とだけ動きます。

## brain アプリ

`/claude-brain-app` と入力すると、スマホの形をした小さなウィンドウが開きます。Chrome や Edge のアプリモードで動き、このコンピューターの外からは接続できません。

<p align="center">
  <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/ja-home.png" alt="brain アプリのホーム" width="300">
  &nbsp;
  <img src="https://raw.githubusercontent.com/FuJiGraphics/claude-brain/media/ja-persona.png" alt="性格を決める" width="300">
</p>

- プロジェクトごとに育つ脳: 記憶が増えるにつれて、たまご、あかちゃん、こども、おとな、賢者へと育ちます。気分は頭の重さ、海馬の失敗、睡眠、学習といった実際の状態を見て変わります。
- 吹き出し: この脳がいちばん大事にしている話題を、短い言葉で見せます。押すとその話題の記憶をまとめて見られます。
- やさしい言葉の説明: AI が書いたメモは短くて硬く、読みにくいものです。記憶を開くと、ひとことの要約、なぜ覚えているのか、いつ思い出すのか、難しい言葉の説明が先に表示されます。
- フィードバック: 記憶ごとに「デプロイは今も release スクリプトで行っていますか?」のような質問がついています。「はい、合ってる」「変わった」「大事」「もういらない」のどれかを押すとポストにたまり、ポストで「海馬にまとめて送る」を押すと海馬に届きます。反映が終わるとアプリがお知らせします。
- 質問: プロジェクトの脳と会話できます。記憶の中だけで答え、根拠にした記憶も一緒に見せます。
- エサやりと脳の整理: 必ず覚えてほしいことを直接伝えたり、頭が重くなったときに海馬へ整理を任せたりできます。
- まだ知らないプロジェクト: 最近 Claude Code で作業したのに、まだ登録されていないフォルダを表示します。「育てる」を押すと、1〜2分でそのプロジェクトの脳が生まれます。
- 眠っている記憶と保管庫: 長く使われずにしまった記憶は記憶帳の「眠っている記憶」に、海馬が整理の中で手放した記憶は「保管庫」にあります。保管庫の記憶は、また必要になったら戻せます。
- お休み: 特定のプロジェクトだけで brain を休ませることができます。
- 使用量とバックアップ: 設定で今週 brain が使った Claude の使用量を確かめたり、記憶を1つの zip にバックアップしたりできます。

アプリが記憶ファイルを直接書き換えることはありません。エサ、フィードバック、整理の依頼はすべて海馬の作業待ちの列(キュー)に入るので、記憶ファイルを直すのはいつも海馬だけです。

### 働き方の性格

プロジェクトごとに、Claude の働き方を決められます。リス(すばやく)、フクロウ(計画して確認)、ネコ(質問して提案)、カメ(遅いけど正確)から選ぶか、性向を状況に直接つないで作ることもできます。

| 強さ | 起きること |
|---|---|
| 軽め | セッションの開始時にひとこと伝えます |
| ふつう | さらに、依頼のたびに1行ずつ思い出させます |
| 必ず! 🔒 | さらに、フックが直接守らせます。`rm -rf`、`push --force`、`reset --hard`、デプロイなどの前にユーザーへ確認し、ビルドやテストなしで終えようとすると一度差し戻します |

プレビューに表示される文が、Claude が実際に受け取る文です。

## コマンド

ほとんどはフックがその場で処理するので、トークンを使いません。結果は設定した言語で表示されます。

| コマンド | すること |
|---|---|
| `/claude-brain-app` | brain アプリを開く |
| `/claude-brain-status` | オン/オフ、海馬の作業と失敗、最後の夜の整理、最近の想起、今週の使用量 |
| `/claude-brain-register` | このプロジェクトを今すぐ登録する |
| `/claude-brain-on`、`/claude-brain-off` | brain のオン/オフ。後ろに `here` をつけると、このプロジェクトだけが対象になります |
| `/claude-brain-config [default\|eco\|quality]` | 海馬のモデルを選ぶ: Sonnet medium / Sonnet low / Opus high。`lang ja` のように言語も変えられます |
| `/claude-brain-model`、`/claude-brain-effort` | 海馬のモデルと effort を個別に決める |
| `/claude-brain-remember <内容>` | 覚えてほしいことを直接伝える |
| `/claude-brain-recall <名前>...` | ファイル、シンボル、API、エラー、症状で記憶を探す |
| `/claude-brain-sleep` | 夜の整理を今すぐ実行する |
| `/claude-brain-results` | 海馬がしたことを見る |
| `/claude-brain-stop` | 今の作業が終わったら海馬を止める |
| `/claude-brain-update` | 新しいバージョンを取得する(記憶はそのまま) |
| `/claude-brain-backup` | 記憶と性格を1つの zip にバックアップする |

## 費用とプライバシー

- 思い出すために別の API を呼ぶことはありません。ただし、セッション開始時のプロジェクトの記憶の地図(最大約6,000文字)、依頼ごとの習慣の1行、作業中に思い出した記憶(セッションあたり平均約2,000文字、上限9,000文字)がコンテキストに加わります。すべて合わせると、作者の環境ではセッションあたり約15,000文字(トークンにして4,000〜5,000ほど)でした。フック1回にかかる時間は約25ms です。
- 海馬は Claude の使用量を使います。作業1件ごとに `claude -p` を1回実行します(既定は Sonnet 5.5、effort medium)。デモの記憶で測った値は、記録1件で0.06〜0.13ドル、整理1件で0.05〜0.11ドルでした(API 料金ベース)。実際のプロジェクトでは記憶が多いほど少し増えます。抑えたい場合は `/claude-brain-config eco` をお試しください。
- アプリの AI 機能(吹き出し、やさしい言葉の説明、質問)は Claude Haiku を呼び出し、1回あたり0.002〜0.004ドルほどです。説明はキャッシュしておきます。
- 使った量は `/claude-brain-status` とアプリ設定の「使用量」でいつでも確認できます。Pro や Max のサブスクリプションでは、この金額は実際の請求額ではなく、使った量の目安です。
- 記憶のファイルはこのコンピューターにだけ保存されます。ただし、Claude のセッション、海馬、アプリが Claude を呼ぶときは、必要な記憶の内容がプロンプトに入って Anthropic API に送られます。海馬は確認が必要なときに Web を検索したり読んだりすることがあります(WebFetch、WebSearch)。そのほかに、1日1回新しいバージョンを確認します(`git fetch`)。不要な場合は `~/.claude/skills/brain/.active/config` に `update_check=0` と書いてください。アプリは `127.0.0.1` でのみ、起動のたびに新しいトークンで開きます。
- 海馬は承認プロンプトなしで実行されます。承認してくれる人のいないバックグラウンドの作業だからです。その代わり、git への書き込み、`rm`、`sudo`、設定ファイルやほかのスキルの編集は拒否ルールで防いでいます。詳しくは下の [海馬の権限](#hippocampus-permissions) にまとめました。

## インストール、更新、バックアップ

```bash
git clone --single-branch https://github.com/FuJiGraphics/claude-brain.git ~/.claude/skills/brain
bash ~/.claude/skills/brain/scripts/install.sh
```

Windows では、同じ2行を Git Bash(Claude Code が使うシェル)で実行してください。インストールは何度実行しても結果が同じで、書き換える設定ファイルは `<ファイル>.brain-bak-<時刻>` としてバックアップします。インストールが行うことは次のとおりです。

1. `~/.claude/settings.json` に brain のフックを登録します。ほかのフックには触れません。brain のフックはどんな場合も正常な終了コードで終わるので、性格を「必ず!」にしていなければ、brain がツールの呼び出しを止めることはありません。
2. Claude Code のステータスラインの末尾に `[BRAIN]` の表示を付けます。もとのステータスラインはそのまま残します。
3. `~/.claude/CLAUDE.md` に、`[記憶]` メッセージが何なのかを伝える1行を加えます。試したところ、この1行がないと Claude は記憶を出どころのわからない文として無視しました。
4. 毎日04:30に夜の整理を予約します(macOS は launchd、Windows はタスク スケジューラ)。Linux では cron に `scripts/sleep.sh` を直接登録してください。
5. `/claude-brain-*` コマンドを作り、OS の言語に合わせて言語を決めます。

### プロジェクトの登録

brain は登録されたプロジェクトの中でだけ動きます。直近7日間にセッション3つ以上、依頼10件以上のやりとりがあった git フォルダは、毎晩1つずつ自動で登録されます。すぐ始めたいときは、そのフォルダで `/claude-brain-register` と入力するか、アプリのホームの「まだ知らないプロジェクト」で「育てる」を押してください。

### 更新

`/claude-brain-update` と入力すると、新しいバージョンを取得してインストールをやり直します。手で編集したファイルがある場合は上書きせずに止まり、お知らせします。新しいバージョンが出ると、アプリのホームと `/claude-brain-status` に案内が表示されます。

<details><summary>2026年10月5日より前にインストールした場合(最初の1回だけ)</summary>

以前のバージョンは記憶フォルダ(`cortex/`)の一部を git で管理していたため、`git pull` が競合で止まります。次のコマンドを1回だけ実行すると、記憶をそのままにして新しい構成へ移れます。

```bash
cd ~/.claude/skills/brain
cp -R cortex .active/cortex-backup          # 先に記憶をコピーしておきます
git checkout -- cortex && git pull          # 新しいバージョンを取得します
cp -R .active/cortex-backup/. cortex/       # 記憶を元の場所に戻します
bash scripts/install.sh
```

それ以降は `/claude-brain-update` で更新できます。
</details>

### バックアップと別のコンピューターへの引っ越し

`/claude-brain-backup`(またはアプリ設定のバックアップ)で、記憶と性格を1つの zip にまとめられます。zip は `~/Downloads` に保存されます。新しいコンピューターに brain をインストールしてから `bash ~/.claude/skills/brain/scripts/backup.sh restore <zip のパス>` を実行してください。そのコンピューターにあった記憶は `.active/before-restore-<時刻>/` に移してから入れ替え、ユーザー名が違ってホームフォルダのパスが変わった場合は、プロジェクトのパスも合わせて直します。海馬が作業中のときは復元しないので、その場合は先に `/claude-brain-stop` で止めてください。

### アンインストール

`bash ~/.claude/skills/brain/scripts/install.sh --uninstall` で、フック、ステータスラインの表示、CLAUDE.md の1行、コマンドファイル、夜の整理の予約を解除し、海馬を止めます。記憶はフォルダを削除するまで残ります。

## よくある質問

**`CLAUDE.md` だけでは足りませんか?** すべてのセッションに必要な少数のルールには、`CLAUDE.md` がいちばん向いています。ただし毎回丸ごと読み込まれ、人が書く必要があり、自分では整理されません。brain は `CLAUDE.md` に書ききれない何百もの小さな落とし穴や決めたことを受け持ち、いま扱っているファイルやエラーに関係するものだけを取り出します。

**Claude Code の自動メモリはオンのままでもいいですか?** `~/.claude/settings.json` に `"autoMemoryEnabled": false` を入れてオフにすることをおすすめします。自動メモリには間違いを直す仕組みがなく、セッションのたびに読み込まれるので、古いメモが brain の新しい記憶とぶつかることがあります。

**記憶が間違っていたら?** アプリでその記憶を開き、「変わった」を押して今の状況を書いてから、ポストから送ってください。海馬が確かめてから直します。記憶には確認した日付がついていて、今のコードと違う場合はいつでも今のコードが優先です。

**記憶がどこまでも増え続けませんか?** 毎晩、重なった記憶をまとめ、長く使われていない記憶はしまい込みます。しまった記憶も検索では見つかります。アプリの「頭の重さ」が整理のタイミングを教えてくれます。

**特定のプロジェクトだけオフにしたいです。** そのフォルダで `/claude-brain-off here` と入力するか、アプリのプロジェクト画面で「このプロジェクトではお休み」をオンにしてください。記憶はそのまま残ります。

**チームで共有できますか?** 今のところは難しいです。記憶はマシンごとにあります。バックアップの zip で移すことはできますが、複数の人が同時に書く使い方は想定していません。

**Cursor や Codex でも使えますか?** 残念ながら使えません。Claude Code のフックの上で動きます。

**どの言語に対応していますか?** アプリ、コマンドの結果、インストールの案内、セッションの文、性格は、日本語、英語、韓国語、中国語に対応しています。記憶は会話した言語でたまり、訂正や決定といったシグナルも4つの言語で読み取ります。言語はアプリの設定か、`/claude-brain-config lang ja` のように変えられます。

**セッションに何が入ったか見られますか?** `/claude-brain-status` で直近24時間の想起の回数と文字数を確認でき、`~/.claude/skills/brain/.active/recall.log` にはすべての記録が残ります。

## 知っておいていただきたいこと

- 測定は1人のプロジェクトで行いました(macOS、主に Unity/C# と VS Code 拡張)。エラーから手がかりを取り出す規則は C# のコンパイルエラーに合わせて調整しています。開いたり直したりするファイルの名前で思い出す部分は、言語に関係なく動きます。コマンドの中のファイルは一般的な言語のソースと設定ファイルの拡張子を、API 名は `PaymentClient.Charge(` のように大文字で始まるドット表記を読み取ります。
- Windows 対応はベータ版です。パス、フック、タスク スケジューラ、アプリを Windows 向けに移して確認しましたが、実際の Windows マシンではまだ十分に使えていません。問題があれば Issue で教えていただけると助かります。
- 文脈が大事な作業では、時間とトークンが多めにかかります(上のベンチマークをご覧ください)。
- 海馬は、このコンピューターで監督なしに動くエージェントです。拒否ルールを設けていますが、気になる場合は `scripts/hippocampus-perm.mode` を `acceptEdits` に変えられます。ただしそうすると海馬が記憶ファイルを書けなくなり、brain は新しく学ばなくなります(思い出すことはそのまま動きます)。

## 仕組み

名前は脳の構造から借りています。

| 部品 | 人の脳では | このスキルでは |
|---|---|---|
| **cortex** | 大脳皮質、定着した長期記憶 | Markdown の記憶の保存先です。`common/`、`stacks/<スタック>/`、`projects/<スラッグ>/` の3層に分かれ、層ごとに薄い索引と記憶本文があります |
| **thalamus** | 視床、感覚をふるいにかけて意識に上げる | フックです。いま扱うファイル、コマンド、エラーに関係する記憶を渡し、セッション開始時にプロジェクトの地図を広げます |
| **hippocampus** | 海馬、新しい記憶を作る | バックグラウンドの `claude -p` ワーカーです。cortex に書く唯一の担い手として、登録、記録、再生、整理を受け持ちます |
| **sleep** | 睡眠、記憶を固めて忘れる | 毎晩、使用回数の集計、忘却、残った会話の再生、検索失敗からの学習、整理、検査を行います |

```
[思い出す - セッションの中]
ツール呼び出し ─ フック ─▶ thalamus ─▶ cortex の中の関係する記憶 ─▶ [記憶] メッセージがセッションに入る

[書き留める - セッションの外]
ターンの終わり、圧縮の直前、セッションの終わり ─▶ thalamus ─▶ 再生(起きているとき) ──┐
毎日04:30 ─▶ sleep ─▶ 再生、検索失敗からの学習、整理 ──────────────────────────┴─▶ キュー ─▶ hippocampus ─▶ cortex
```

Claude Code がもともと残している会話の記録が、短期記憶の役割を果たします。同じ区間は1回だけ処理します。

<details><summary><b>思い出す - thalamus</b></summary>

フックは SessionStart、UserPromptSubmit、PreToolUse(Edit、Write、MultiEdit、NotebookEdit、Bash、AskUserQuestion)、PostToolUse(Read)、PostToolUseFailure(Bash)、SubagentStart、Stop、PreCompact、SessionEnd にかかります。`cortex/registry.md` に登録されたプロジェクトの中でだけ動きます。

| フックのイベント | 手がかり |
|---|---|
| SessionStart | プロジェクトの要旨、プロジェクトの `INDEX.md`(3,000文字まで)、スタックと共通の索引(それぞれ2,000文字、1,200文字)、手順の記憶の行 |
| UserPromptSubmit | 計画の前に今回の作業範囲の索引を開くよう促す習慣の1行 |
| PostToolUse (Read) | 開いたファイルの名前 |
| PreToolUse (Edit、Write、MultiEdit、NotebookEdit) | 直すファイルの名前、編集内容に新しく出てきた API 名 |
| PreToolUse (Bash) | コマンドが読み書きするファイルの名前、コマンド内のコードの API 名 |
| PostToolUseFailure (Bash) | C# のコンパイルエラーのファイルとエラーコード、例外名と最初のプロジェクトのフレームのファイル |
| SubagentStart | 作業フォルダのプロジェクトと、`[記憶]` が何かを伝える1行 |
| Stop、PreCompact、SessionEnd | 想起はなく、新しい会話の区間が目立てば再生を始めます |

- 関係する記憶がなければ何も出力しません。一度に1〜2件(Bash は1件)、1件あたり240文字まで、セッションごとに40件または9,000文字が上限です(セッション開始時の地図は別に数えます)。
- 1つの手がかりが4つ以上の別々の記憶に当てはまる場合は、ありふれた手がかりとみなし、ファイル名にその手がかりを含む記憶だけを残します。
- 過去の会話431セッションを再生し、想起371件を Sonnet で判定しました。「邪魔になった」と判定された割合が低いファイルを開くとき(0〜3%)、編集の直前(8〜20%)、コマンドが扱うファイル(約10%)でだけ思い出し、割合が高かった依頼の文(64%)、「うまくいかない」という結論(75%)、コマンド内の CLI 名(64%)は手がかりに使いません。
</details>

<details><summary><b>記録、睡眠、忘却</b></summary>

| | 起きているとき | 睡眠 |
|---|---|---|
| 開始 | ターンの終わり、圧縮の直前、セッションの終わりにバックグラウンドで | 毎日04:30。逃したら起きたあとに1回。`/claude-brain-sleep` ですぐに |
| 対象 | 前回の処理位置のあとに新しくたまった会話の区間 | 起きているときに処理できなかった区間 |
| 条件 | 4,000バイト以上、目立ち度6以上(圧縮の直前とセッションの終わりは3以上)。同じ会話の記録は20分に1回(圧縮の直前とセッションの終わりは例外)、全体では1時間に4件 | 目立ち度6以上、高い順に4件 |

目立ち度は、ユーザーの訂正3、決定の表現3、記憶の依頼5、権限の拒否2、ツールの失敗1(最大5)、繰り返しの調査1(最大3)、依頼が5件以上なら1で数えます。訂正、決定、記憶の依頼は、日本語、英語、韓国語、中国語の表現をすべて読み取ります。

睡眠は、使用回数と検索失敗の集計、忘却、残った区間の再生(最大4件)と活発な未登録プロジェクト1つの登録、検索失敗からの学習、いちばん長く整理していない断片3つの整理、検査の順で進みます。`scripts/sleep.conf` を作って `FORGET_DAYS=60` のように書くと、既定値を変えられます。

最後に使われた日から45日(決定、落とし穴、事故を含む記憶は120日)たつと、索引の行を `dormant.md` へ移します。本文は残っていて検索で見つかり、また使われれば元の索引に戻ります。海馬が整理の中で手放した記憶は `_archive/` に移り、アプリの保管庫から戻せます。完全に削除することはありません。
</details>

<a name="hippocampus-permissions"></a>
<details><summary><b>海馬の権限</b></summary>

> [!IMPORTANT]
> 海馬は既定で承認プロンプトなしで動きます(`scripts/hippocampus-perm.mode` の `bypassPermissions`)。brain を `~/.claude/skills/` の下に置くと記憶のフォルダもその下に置かれますが、Claude Code は `.claude/` を保護されたパスとして扱い、編集のたびに承認を求めます。海馬は非対話の `claude -p` なので、承認する人がいません。

- この設定は海馬のプロセスにだけ適用され、あなたの会話のセッションの権限はそのままです。
- ツールは Read、Write、Edit、Grep、Glob、Bash、WebFetch、WebSearch に限り、MCP サーバーやほかのスキルはつなぎません。
- git への書き込み(`commit`、`push`、`checkout`、`reset` など)、`rm`、`sudo`、`find -delete`、ほかのスキルの本文と `settings.json`、`CLAUDE.md`、`hooks/` の編集は拒否ルールで防ぎます。拒否ルールはこのモードでも有効です。
- オフにしたい場合は `echo acceptEdits > ~/.claude/skills/brain/scripts/hippocampus-perm.mode` を実行してください。記憶の書き込みはすべて拒否され(`denied`)、判定だけが残り、brain は新しく学ばなくなります。
</details>

<details><summary><b>設計の根拠になった測定</b></summary>

| 事実 | 根拠 |
|---|---|
| 命令口調のフックの文は、プロンプトインジェクションと疑われて守られませんでした | Claude Code 2.1.283 での隔離実行、2026-09-29 |
| `CLAUDE.md` の1行がないと、`[記憶]` は出どころ不明の文として無視されました | 同日 |
| 「直す前にノートを確認する」という強制ルールが、Edit・Write 6,300件の20%、Bash の書き込み893件の32%で守られませんでした | 分離前の構成のゲート記録 |
| セッションが頼まないと動かない整理は、実際には動きませんでした(キュー668件のうち記録322、整理0) | 分離前の構成のキュー記録 |
| アプリの Haiku 呼び出しは、思考をオンにすると38秒で0.024ドル、オフにすると6秒で0.004ドルでした | 2026-10-05 |
</details>

<details><summary><b>フォルダの構成と動作環境</b></summary>

```
brain/
├── SKILL.md, commands/        # 操作パネル、/claude-brain-* コマンドのひな形
├── agents/hippocampus.md      # 海馬の指示書
├── scripts/                   # thalamus.py(フック)、nbsearch.py(検索)、hippocampus-*.sh、sleep.sh、install.sh、
│                              # update.py、backup.py、register.py、persona.py、lang.py、cli_i18n.py、plat.py …
├── editor/                    # brain アプリ (server.py + web/)
├── seed/cortex/               # 初めてのインストールで使う記憶の保存先のひな形
├── promo/                     # 紹介動画、スクリーンショットのツール(架空のデモの脳)
├── cortex/                    # 記憶(このコンピューターで育ちます。git では管理しません)
└── .active/                   # 実行時の状態(git では管理しません)
```

| | |
|---|---|
| Claude Code | 2.1.28x 以降(2.1.283 で検証) |
| Python | 3.7 以降(`python3`、`python`、`py` のいずれか) |
| `claude` CLI | PATH にあること(海馬とアプリが呼び出します) |
| シェル | bash 3.2 以降。Windows は Git Bash |
| アプリのウィンドウ | Chrome(macOS、Linux)または Edge(Windows)のアプリモード、なければ既定のブラウザ |
| OS | macOS(開発と測定をした環境)、Windows(ベータ)、Linux(動作します。夜の整理は cron で) |
</details>

## ライセンス

[CC BY-ND 4.0](LICENSE)(表示 - 改変禁止 4.0 国際)。Copyright (c) 2026 Cheol Jin Choi (FuJiGraphics).

| 項目 | 内容 |
|---|---|
| 商用利用 | できます。会社の業務や有料サービスの中でも使えます |
| 共有、再配布 | 元のままであればできます |
| 改変版の配布 | 手を加えたものや一部を取り出したものは配布できません |
| クレジット表記 | 作者、リポジトリのアドレス(https://github.com/FuJiGraphics/claude-brain)、ライセンスを明記してください |

改変版を配布したい場合は、作者に別途ご連絡ください。インストールしたコンピューターでたまる記憶は利用者ご本人のものであり、このライセンスとは関係ありません。
