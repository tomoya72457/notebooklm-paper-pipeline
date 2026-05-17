# NotebookLM 論文処理パイプライン

論文 PDF を 1 本投入するだけで、**音声解説・動画解説・スライド資料・インフォグラフィック** の 4 種類の生成物を NotebookLM で自動生成し、論文フォルダに保存するための処理系です。

**対応 OS**: macOS / Windows / Linux

---

## 📁 リポジトリ構成

```
notebooklm-paper-pipeline/
├── README.md              # 本ファイル
├── notebooklm/
│   ├── process_paper.py   # PDF 1 本を投入して 4 種生成・取得する自動化スクリプト
│   └── pipeline.md        # 4 種生成の仕様・プロンプト・命名規則の詳細
└── papers/                # 論文をここに格納する(論文ごとにサブフォルダを作る)
```

---

## 🚀 セットアップ

### 1. Python 仮想環境の作成

リポジトリのルートディレクトリで以下を実行します。

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows(PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows(コマンドプロンプト)**

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

> 仮想環境を有効化したターミナルで以降の作業を行ってください。本スクリプトは Python 標準ライブラリのみで動作するため、`pip install` で追加のパッケージを入れる必要はありません。

### 2. Google Chrome のインストール

`nlm` の認証は **Google Chrome を起動して Google アカウントにログイン** することで行われます。Chrome が入っていない環境では認証ができないため、まず Chrome をインストールしてください。

- ダウンロード: https://www.google.com/chrome/

### 3. NotebookLM MCP サーバー(`nlm` CLI)のインストール

このパイプラインは [`notebooklm-mcp`](https://github.com/yutkat/notebooklm-mcp) が提供する `nlm` コマンドを内部で呼び出します。クローンした直後は入っていないので、お使いの OS に合わせてインストールしてください。

**macOS(Homebrew)**

```bash
brew install nlm
```

**Windows / Linux / macOS 共通(Go を使う方法)**

事前に [Go](https://go.dev/dl/) をインストールしたうえで:

```bash
go install github.com/yutkat/notebooklm-mcp/cmd/nlm@latest
```

> Windows の場合、`%USERPROFILE%\go\bin` を `PATH` 環境変数に追加してください。

インストール後、ターミナルを開き直して以下で確認します。

```bash
nlm --version
```

### 4. NotebookLM への Chrome 認証(初回必須)

リポジトリには認証情報は含まれていません。**クローンした各自が、自分の Google アカウントで NotebookLM にログインする必要があります**。

以下のコマンドを実行すると Chrome が起動して Google ログイン画面が開きます。

```bash
nlm login
```

手順:

1. コマンドを実行すると **Google Chrome が自動で起動** します
2. ブラウザに **Google アカウントのログイン画面** が表示されます
3. 普段 **NotebookLM (https://notebooklm.google.com)** を使っている Google アカウントでログインします
4. ログインに成功すると、認証トークンがローカルに保存されます
5. 以降のコマンドはトークンを自動で再利用するので、`nlm login` を毎回実行する必要はありません
6. トークンが切れた場合や別アカウントに切り替えたい場合は、再度 `nlm login` を実行してください

> ⚠️ **重要**
> - NotebookLM が利用可能な Google アカウント(個人 / Workspace 等)が必要です
> - 認証は各ユーザーのローカル環境で完結し、リポジトリには **一切含まれません**
> - 他人がクローンしても、認証は最初から自分でやり直す必要があります

---

## 📥 論文の配置

生成 AI 等で壁打ちして見つけてきた論文を、`papers/` フォルダの中に **論文ごとに専用のサブフォルダ** を作って格納します。

フォルダ名は `<論文の略称>_<arxivID>` の形式を推奨します(スクリプトが arxiv ID を自動抽出してファイル名のプレフィックスに使うため)。

### 例

```
papers/
└── MultiAgentGraphRAG_2511.08274/
    └── MultiAgentGraphRAG.pdf      # 取得してきた論文 PDF
```

---

## ▶️ スクリプトの実行

論文 PDF のパスを引数に指定して `process_paper.py` を実行します。

### 基本形

**macOS / Linux**

```bash
python3 notebooklm/process_paper.py <PDF のパス>
```

**Windows**

```powershell
python notebooklm\process_paper.py <PDF のパス>
```

### 実行例

**macOS / Linux**

```bash
python3 notebooklm/process_paper.py papers/MultiAgentGraphRAG_2511.08274/MultiAgentGraphRAG.pdf
```

**Windows**

```powershell
python notebooklm\process_paper.py papers\MultiAgentGraphRAG_2511.08274\MultiAgentGraphRAG.pdf
```

### バックグラウンド実行(推奨)

4 種の生成には合計で 30 分〜1 時間かかります。バックグラウンドで実行し、ログをファイルに残しておくと安心です。

**macOS / Linux**

```bash
nohup python3 notebooklm/process_paper.py <PDF のパス> > process.log 2>&1 &
```

**Windows(PowerShell)**

```powershell
Start-Process python `
  -ArgumentList "notebooklm\process_paper.py","<PDF のパス>" `
  -RedirectStandardOutput process.log `
  -RedirectStandardError process.err `
  -NoNewWindow
```

完了するとデスクトップに通知が届きます(macOS 通知センター / Windows トースト通知 / Linux libnotify)。通知が表示されない環境でも、ログファイル末尾の `[NOTIFY]` 行で完了を確認できます。

---

## 📦 生成される成果物

スクリプト実行後、論文フォルダに以下のファイルが自動で保存されます(arxiv ID をプレフィックスとして付与)。

```
papers/MultiAgentGraphRAG_2511.08274/
├── 2511.08274.pdf              # 元論文(自動でリネーム)
├── 2511.08274_audio.m4a        # 🎧 音声解説
├── 2511.08274_video.mp4        # 🎬 動画解説
├── 2511.08274_slides.pdf       # 📊 スライド資料
└── 2511.08274_infographic.png  # 🖼️ インフォグラフィック
```

> **なぜ arxiv ID をプレフィックスにするのか?**
> 固定名(`audio.m4a` 等)だと、Apple Music / QuickTime / Spotlight 等がファイル名+メタデータだけで識別するため、別の論文の音声を再生してしまう混線が起きるためです。詳細は `notebooklm/pipeline.md` を参照。

---

## 🔍 生成内容のスタイル

すべての生成物は **落合フォーマット**(以下の 6 項目)で日本語で生成されます。

- どんなもの?
- 先行研究と比べてどこがすごい?
- 技術や手法のキモはどこ?
- どうやって有効だと検証した?
- 議論はある?
- 次に読むべき論文は?

詳細なプロンプトや生成オプションは `notebooklm/pipeline.md` を参照してください。

---

## 🧰 トラブルシューティング

| 症状 | 原因と対処 |
|------|-----------|
| `nlm: command not found` / `'nlm' は内部コマンドではない` | `nlm` がインストールされていない、または PATH に通っていない。インストール手順を再確認 |
| `nlm login` で Chrome が起動しない | Chrome 未インストール、もしくは既定ブラウザの設定で Chrome が見つからない |
| 認証エラーで API 呼び出しが失敗する | `nlm login` を再実行してトークンを更新 |
| 通知が表示されない | OS の通知設定で許可されていない、または Linux で `libnotify` 未導入。標準出力 / ログの `[NOTIFY]` 行で完了確認可 |

---

## ⚙️ 仕様の詳細

- プロンプト・生成オプション・命名規則の背景 → [`notebooklm/pipeline.md`](notebooklm/pipeline.md)
- スクリプト内部の実装(ポーリング、リトライ、リネーム処理など) → [`notebooklm/process_paper.py`](notebooklm/process_paper.py)
