# NotebookLM 論文処理パイプライン

論文 PDF を 1 本投入するだけで、**音声解説・動画解説・スライド資料・インフォグラフィック** の 4 種類の生成物を NotebookLM で自動生成し、論文フォルダに保存するための処理系です。

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

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> 仮想環境を有効化したターミナルで以降の作業を行ってください。

### 2. NotebookLM MCP サーバー(`nlm` CLI)のインストール

このパイプラインは [`notebooklm-mcp`](https://github.com/yutkat/notebooklm-mcp) が提供する `nlm` コマンドを内部で呼び出します。クローンした直後は入っていないので、以下のいずれかの方法でインストールしてください。

```bash
# Homebrew(macOS 推奨)
brew install nlm

# もしくは go install
go install github.com/yutkat/notebooklm-mcp/cmd/nlm@latest
```

インストール後、`nlm --version` でパスが通っていることを確認してください。

### 3. Google アカウントの認証(Chrome 認証)

`nlm` は内部で **Chrome を起動して Google アカウントにログイン** することで NotebookLM を操作します。リポジトリをクローンしただけでは認証情報が含まれていないため、**初回は必ず以下を実行して自分の Google アカウントでログイン** してください。

```bash
nlm login
```

- 実行すると Chrome が起動し、Google ログイン画面が開きます
- 普段 NotebookLM を使っている Google アカウントでログインしてください
- 認証トークンはローカルに保存され、以降は自動で再利用されます
- トークンが切れた場合や別アカウントに切り替えたい場合も `nlm login` を再実行します

> ⚠️ **重要**: NotebookLM が利用可能なプラン(個人/Workspace 等)の Google アカウントが必要です。認証は各ユーザーのローカル環境で完結し、リポジトリには含まれません。

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

```bash
python3 notebooklm/process_paper.py <PDF のパス>
```

### 実行例

```bash
python3 notebooklm/process_paper.py papers/MultiAgentGraphRAG_2511.08274/MultiAgentGraphRAG.pdf
```

### バックグラウンド実行(推奨)

4 種の生成には合計で 30 分〜1 時間かかります。バックグラウンドで実行し、ログをファイルに残しておくと安心です。

```bash
nohup python3 notebooklm/process_paper.py <PDF のパス> > /tmp/process.log 2>&1 &
```

完了すると macOS の通知センターに通知が届きます。

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

## ⚙️ 仕様の詳細

- プロンプト・生成オプション・命名規則の背景 → [`notebooklm/pipeline.md`](notebooklm/pipeline.md)
- スクリプト内部の実装(ポーリング、リトライ、リネーム処理など) → [`notebooklm/process_paper.py`](notebooklm/process_paper.py)
