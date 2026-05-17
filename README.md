# papers/notebooklm/ — NotebookLM 処理パイプライン

このフォルダは、論文 PDF を NotebookLM にかけて 4 種生成物を作るための処理系をまとめる。

NotebookLM は研究側(`papers/`)のサブツールであり、生成物そのものは各論文フォルダに保存する。

## ファイル

- `pipeline.md` — 4 種生成の仕様、プロンプト、標準フロー、保存命名規則
- `process_paper.py` — PDF 1 本を NotebookLM に投入し、音声・動画・スライド・インフォグラフィックを生成/取得する自動化スクリプト

## 使い方

## 前提条件

- `nlm` (notebooklm-mcp-cli) が PATH に存在し、`nlm login` 済みであること

## 実行例

```bash
nohup python3 papers/notebooklm/process_paper.py <PDF パス> > /tmp/process.log 2>&1 &
```

`DEST_DIR` を省略すると、PDF と同じディレクトリに以下の命名規約で保存する。フォルダ名から arxiv ID を抽出して prefix にする(同名ファイル衝突回避、2026-05-12 改訂):

```text
{arxiv_id}.pdf                 # 元論文(処理後にリネーム)
{arxiv_id}_audio.m4a
{arxiv_id}_video.mp4
{arxiv_id}_slides.pdf
{arxiv_id}_infographic.png
```

例: フォルダ `MultiAgentGraphRAG_2511.08274/` の場合 → `2511.08274_audio.m4a` 等。

詳細なプロンプト・生成仕様・命名規約の背景は `pipeline.md` を参照。
