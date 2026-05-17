# NotebookLM パイプライン仕様

論文 PDF 1 本から **音声解説・動画解説・スライド資料・インフォグラフィック** の 4 種を生成して、その論文のフォルダに保存する標準手順。

## 1. ユーザー指定の生成プロンプト(落合フォーマット)

すべての生成で「論文の内容を以下の項目で埋めてください」というスタイルを採用する。

### 共通の質問項目

```
添付ファイルについて、以下の項目を埋めてください。
・どんなもの？
・先行研究と比べてどこがすごい？
・技術や手法のキモはどこ？
・どうやって有効だと検証した？
・議論はある？
・次に読むべき論文は？
できる限り関連する図表番号に言及してください。
できる限り引用論文の出典を記載してください。
```

### 出力種別ごとの違い

| 出力 | 「どんなもの？」 | 追加指定 |
|-----|------|------|
| 音声解説 | **含めない**(時間配分の都合) | — |
| 動画解説 | 含める | — |
| スライド資料 | 含める | **PDF 形式で保存** |
| インフォグラフィック | (専用 UI) | **レイアウト=縦向き、詳細レベル=詳細** |

## 2. CLI コマンドへのマッピング

`nlm` (notebooklm-mcp-cli) を使用。各コマンドの `--focus` に上記プロンプトを渡す。

### 音声解説

```bash
nlm audio create <NOTEBOOK_ID> \
    --format deep_dive \
    --focus "添付ファイルについて、以下の項目を埋めてください。
・先行研究と比べてどこがすごい？
・技術や手法のキモはどこ？
・どうやって有効だと検証した？
・議論はある？
・次に読むべき論文は？
できる限り関連する図表番号に言及してください。
できる限り引用論文の出典を記載してください。" \
    --language ja \
    --confirm
```

### 動画解説

```bash
nlm video create <NOTEBOOK_ID> \
    --format explainer \
    --focus "添付ファイルについて、以下の項目を埋めてください。
・どんなもの？
・先行研究と比べてどこがすごい？
・技術や手法のキモはどこ？
・どうやって有効だと検証した？
・議論はある？
・次に読むべき論文は？
できる限り関連する図表番号に言及してください。
できる限り引用論文の出典を記載してください。" \
    --language ja \
    --confirm
```

### スライド資料

```bash
nlm slides create <NOTEBOOK_ID> \
    --format detailed_deck \
    --focus "<上記と同じ 6 項目プロンプト>" \
    --language ja \
    --confirm
```

→ 生成後、`nlm download` で PDF として取得して論文フォルダに保存。

### インフォグラフィック

```bash
nlm infographic create <NOTEBOOK_ID> \
    --orientation portrait \
    --detail detailed \
    --language ja \
    --confirm
```

(インフォグラフィックは focus テキストではなくレイアウトオプションで指定)

## 3. 1 論文を処理する標準フロー

```
1. ノート作成: nlm notebook create "<論文名>"
2. ソース追加: nlm source add <NOTEBOOK_ID> --file <PDF パス>
3. 4 種を順次生成 (上記コマンド)
4. 完了を待機 (各処理 5-15 分)
5. ダウンロード: nlm download <NOTEBOOK_ID> --type audio/video/slides/infographic
6. 論文フォルダに保存
```

## 4. 保存先の命名規則(2026-05-12 改訂、`{arxiv_id}_{type}.ext` 形式)

論文フォルダ(例: `papers/01_グラフ生成・構造解析/AGENTiGraph_2410.11531/`)に以下を置く:

```
AGENTiGraph_2410.11531/                  # フォルダ名: <ShortName>_<arxiv_id>
├── 2410.11531.pdf                       # 元論文
├── 2410.11531_audio.m4a                 # 音声解説
├── 2410.11531_video.mp4                 # 動画解説
├── 2410.11531_slides.pdf                # スライド資料
└── 2410.11531_infographic.png           # インフォグラフィック
```

### なぜ arxiv_id プレフィックスか

旧規約(`audio.m4a` / `video.mp4` 等の固定名)では、リポジトリ内に同名ファイルが複数並列し、**Apple Music / QuickTime / Spotlight** 等が「ファイル名+メタデータ」だけで識別する場合に **別フォルダのファイルを再生してしまう** 混線が発生した(2026-05-11 発覚)。

arxiv ID を全アーティファクトの prefix に置くことで:
- システム全体で **一意なファイル名** を保証
- ソート時に arXiv ID 順で並ぶ
- アプリ・OS の indexing 挙動に依存しない根本解決

### `process_paper.py` の実装

`extract_arxiv_id()` が `dest_dir` (= 論文フォルダ)の名前から正規表現 `(\d{4}\.\d{4,5})` で arxiv ID を抽出し、`build_output_files()` で `{arxiv_id}_{suffix}` 形式のファイル名辞書を構築する。スクリプト末尾で入力 PDF も `{arxiv_id}.pdf` にリネームする。

## 5. 推奨実行: `papers/notebooklm/process_paper.py`

上記の手順を 1 コマンドにまとめた自動化スクリプト。

```bash
nohup python3 papers/notebooklm/process_paper.py <PDF パス> > /tmp/process.log 2>&1 &
```

- ノート作成 → ソース追加 → 4 種生成トリガー → 完了 polling → ダウンロード(固定名)を内部で完結
- ポーリングがローカルプロセス内なので **AI トークン消費ゼロ**
- 既存成果物がある場合は `FileExistsError` で早期停止
- 完了時に macOS 通知

詳細は `papers/notebooklm/process_paper.py` の docstring を参照。

## 6. AI エージェント運用

Claude Code / Codex に `nlm` MCP を接続済み(`nlm setup add claude-code` / `nlm setup add codex` で導入)。

セッションを再起動すると、MCP 経由で「`papers/04_本命_特許AgenticRAG/AgenticRAG_Survey_2501.09136/` の論文を NotebookLM パイプラインにかけて」のように自然言語で実行できる。

### このプロジェクト固有の取り決め

- 言語は **日本語** (`--language ja`)
- スライドは **PDF 形式で保存**(オリジナルはスライド形式だが PDF 化)
- インフォグラフィックは **縦向き / 詳細レベル**
- 既存の音声/動画/スライド/インフォグラフィックがあるフォルダでは **再生成しない**(明示要求された場合のみ)
