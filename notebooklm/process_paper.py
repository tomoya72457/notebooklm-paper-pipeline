#!/usr/bin/env python3
"""論文 PDF を NotebookLM にかけて 4 種(音声/動画/スライド/インフォ)を生成・取得する。

設計の要点:
- AI エージェント(Claude/Codex 等)が完了を polling せず、ローカルプロセス内で待機する
  → 実行中の AI トークン消費はゼロ
- 完了をデスクトップ通知 (macOS / Windows / Linux 対応)
- 落合フォーマットのプロンプトは papers/notebooklm/pipeline.md と整合(変更時は両方更新)

Usage:
    python3 papers/notebooklm/process_paper.py <PDF_PATH> [<DEST_DIR>]
        DEST_DIR を省略すると PDF と同じディレクトリに保存。

Run in background (推奨):
    nohup python3 papers/notebooklm/process_paper.py <pdf> > /tmp/p.log 2>&1 &

Pre-requisites:
- nlm (notebooklm-mcp-cli) が PATH に存在
- nlm login 済み
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
import shutil
from datetime import datetime

# papers/notebooklm/pipeline.md セクション 1 と整合
PROMPT_AUDIO: str = """添付ファイルについて、以下の項目を埋めてください。
・先行研究と比べてどこがすごい？
・技術や手法のキモはどこ？
・どうやって有効だと検証した？
・議論はある？
・次に読むべき論文は？
できる限り関連する図表番号に言及してください。
できる限り引用論文の出典を記載してください。"""

PROMPT_VIDEO_SLIDES: str = """添付ファイルについて、以下の項目を埋めてください。
・どんなもの？
・先行研究と比べてどこがすごい？
・技術や手法のキモはどこ？
・どうやって有効だと検証した？
・議論はある？
・次に読むべき論文は？
できる限り関連する図表番号に言及してください。
できる限り引用論文の出典を記載してください。"""

POLL_INTERVAL_SEC: int = 60
MAX_WAIT_MIN: int = 60
SOURCE_WAIT_TIMEOUT_SEC: int = 1800  # 30min, large PDFs may exceed nlm default 600s
EXPECTED_ARTIFACT_TYPES: set[str] = {"audio", "video", "slide_deck", "infographic"}

# 命名規約: {arxiv_id}_{type}.ext
# 同名ファイルの衝突(Apple Music 等のライブラリ混線)を防ぐため、論文フォルダ
# 名から arxiv ID を抽出して prefix にする。詳細は AGENTS.md Sec.6 / pipeline.md Sec.4
_ARTIFACT_SUFFIX: dict[str, str] = {
    "audio": "audio.m4a",
    "video": "video.mp4",
    "slide_deck": "slides.pdf",
    "infographic": "infographic.png",
}
_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})")


def extract_arxiv_id(folder: Path) -> str:
    """フォルダ名(例: MultiAgentGraphRAG_2511.08274)から arxiv ID を抽出。
    マッチしない場合はフォルダ名そのものを返す(フォールバック)。
    """
    m = _ARXIV_ID_RE.search(folder.name)
    return m.group(1) if m else folder.name


def build_output_files(arxiv_id: str) -> dict[str, str]:
    """{type: filename} の辞書を arxiv_id プレフィックス付きで構築。"""
    return {t: f"{arxiv_id}_{suffix}" for t, suffix in _ARTIFACT_SUFFIX.items()}

# CLI-controlled options (set via main)
GLOBAL_MODEL: str | None = None
GLOBAL_FALLBACK_MODEL: str | None = None
GLOBAL_FORCE: bool = False


def nlm_supports_model() -> bool:
    """nlm が --model オプションをサポートするかを確認。失敗時は False を返す。"""
    try:
        out = subprocess.run(["nlm", "audio", "create", "--help"], capture_output=True, text=True, check=True).stdout
        return "--model" in out
    except Exception:
        return False


SUPPORTS_MODEL = nlm_supports_model()


def run_nlm(args: list[str]) -> str:
    """nlm CLI を実行して stdout を返す。失敗時は CalledProcessError を上げる。
    SUPPORTS_MODEL が False の場合、--model に続く値を自動的に除去して実行する。
    """
    # Filter out --model if not supported
    if not SUPPORTS_MODEL:
        filtered: list[str] = []
        skip_next = False
        for a in args:
            if skip_next:
                skip_next = False
                continue
            if a == "--model":
                skip_next = True
                continue
            filtered.append(a)
        args = filtered
    result = subprocess.run(
        ["nlm", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def create_notebook(title: str) -> str:
    """ノートを作成して UUID を返す。"""
    out = run_nlm(["notebook", "create", title])
    match = re.search(r"ID:\s*([0-9a-f-]{36})", out)
    if match is None:
        raise RuntimeError(f"Notebook ID not found in output: {out!r}")
    return match.group(1)


def add_source_pdf(notebook_id: str, pdf_path: Path) -> None:
    """PDF を追加し、サーバ側の処理完了まで待つ。"""
    run_nlm([
        "source", "add", notebook_id,
        "--file", str(pdf_path),
        "--wait",
        "--wait-timeout", str(SOURCE_WAIT_TIMEOUT_SEC),
    ])


def trigger_all_artifacts(notebook_id: str, model: str | None = None) -> None:
    """4 種の生成を順次トリガー(NotebookLM 側は非同期に走る)。

    model が指定されれば各 nlm call に --model <model> を付与する。
    """
    model_args = ["--model", model] if model else []
    run_nlm([
        "audio", "create", notebook_id,
        "--format", "deep_dive",
        "--language", "ja",
        "--focus", PROMPT_AUDIO,
        *model_args,
        "--confirm",
    ])
    run_nlm([
        "video", "create", notebook_id,
        "--format", "explainer",
        "--language", "ja",
        "--focus", PROMPT_VIDEO_SLIDES,
        *model_args,
        "--confirm",
    ])
    run_nlm([
        "slides", "create", notebook_id,
        "--format", "detailed_deck",
        "--language", "ja",
        "--focus", PROMPT_VIDEO_SLIDES,
        *model_args,
        "--confirm",
    ])
    run_nlm([
        "infographic", "create", notebook_id,
        "--orientation", "portrait",
        "--detail", "detailed",
        "--language", "ja",
        *model_args,
        "--confirm",
    ])


def fetch_statuses(notebook_id: str) -> dict[str, str]:
    """artifact type → status のマップを返す(--json で安定パース)。"""
    raw = run_nlm(["studio", "status", "--json", notebook_id])
    items: list[dict[str, object]] = json.loads(raw)
    statuses: dict[str, str] = {}
    for item in items:
        artifact_type = item.get("type")
        status = item.get("status")
        if not isinstance(artifact_type, str) or not isinstance(status, str):
            raise RuntimeError(f"Unexpected studio status payload: {items!r}")
        statuses[artifact_type] = status
    return statuses


def wait_until_all_completed(notebook_id: str, fallback_model: str | None = None) -> None:
    """全 4 種が completed になるまで polling。失敗が出た場合、fallback_model が指定されていれば一度だけ再試行する。
    それでも失敗なら例外を上げる。
    """
    deadline = time.monotonic() + MAX_WAIT_MIN * 60
    retried_with_fallback = False
    while time.monotonic() < deadline:
        statuses = fetch_statuses(notebook_id)
        present = set(statuses.keys()) & EXPECTED_ARTIFACT_TYPES
        completed = {t for t in present if statuses[t] == "completed"}
        failed = {t for t in present if statuses[t] == "failed"}
        if failed:
            if fallback_model and not retried_with_fallback:
                # 再試行: 失敗したアーティファクトのみ fallback_model で再トリガー
                for art in sorted(failed):
                    trigger_specific_artifact(notebook_id, art, fallback_model)
                retried_with_fallback = True
                # 少し待ってから再チェック
                time.sleep(POLL_INTERVAL_SEC)
                continue
            raise RuntimeError(f"Generation failed for: {sorted(failed)} (statuses={statuses})")
        if completed >= EXPECTED_ARTIFACT_TYPES:
            return
        time.sleep(POLL_INTERVAL_SEC)
    raise TimeoutError(f"Did not complete within {MAX_WAIT_MIN} minutes")


def ensure_outputs_do_not_exist(dest_dir: Path, output_files: dict[str, str], force: bool = False) -> None:
    """既存成果物の上書きを禁止。ただし force=True の場合は既存を backup_<ts> に退避して上書きを許す。"""
    existing: list[Path] = [
        (dest_dir / filename)
        for filename in output_files.values()
        if (dest_dir / filename).exists()
    ]
    if not existing:
        return
    if not force:
        raise FileExistsError(f"Refusing to overwrite existing artifacts: {[str(p) for p in existing]}")
    # backup
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = dest_dir / f"backup_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for p in existing:
        shutil.move(str(p), str(backup_dir / p.name))
    print(f"Backed up existing artifacts to {backup_dir}")


def download_all(notebook_id: str, dest_dir: Path, output_files: dict[str, str]) -> None:
    """4 種を {arxiv_id}_{type}.ext 形式で dest_dir に保存。"""
    dest_dir.mkdir(parents=True, exist_ok=True)
    run_nlm(["download", "audio", notebook_id, "--no-progress", "-o", str(dest_dir / output_files["audio"])])
    run_nlm(["download", "video", notebook_id, "--no-progress", "-o", str(dest_dir / output_files["video"])])
    run_nlm(["download", "slide-deck", notebook_id, "--no-progress", "-o", str(dest_dir / output_files["slide_deck"])])
    run_nlm(["download", "infographic", notebook_id, "--no-progress", "-o", str(dest_dir / output_files["infographic"])])


def trigger_specific_artifact(notebook_id: str, artifact: str, model: str | None = None) -> None:
    """特定のアーティファクトだけ再トリガーする。artifact は audio/video/slide_deck/infographic のいずれか。"""
    model_args = ["--model", model] if model else []
    if artifact == "audio":
        run_nlm([
            "audio", "create", notebook_id,
            "--format", "deep_dive",
            "--language", "ja",
            "--focus", PROMPT_AUDIO,
            *model_args,
            "--confirm",
        ])
    elif artifact == "video":
        run_nlm([
            "video", "create", notebook_id,
            "--format", "explainer",
            "--language", "ja",
            "--focus", PROMPT_VIDEO_SLIDES,
            *model_args,
            "--confirm",
        ])
    elif artifact == "slide_deck":
        run_nlm([
            "slides", "create", notebook_id,
            "--format", "detailed_deck",
            "--language", "ja",
            "--focus", PROMPT_VIDEO_SLIDES,
            *model_args,
            "--confirm",
        ])
    elif artifact == "infographic":
        run_nlm([
            "infographic", "create", notebook_id,
            "--orientation", "portrait",
            "--detail", "detailed",
            "--language", "ja",
            *model_args,
            "--confirm",
        ])
    else:
        raise ValueError(f"Unknown artifact: {artifact}")


def notify_desktop(title: str, message: str) -> None:
    """OS のデスクトップ通知を発火する。失敗しても全体は止めない(副作用扱い)。

    - macOS  : osascript で通知センターに表示
    - Windows: PowerShell + Windows.Forms バルーン通知
    - Linux  : notify-send (libnotify) があれば表示
    どの OS でも標準出力にもメッセージを出すので、通知が出なくても完了は判別可能。
    """
    import platform

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{message}" with title "{title}" sound name "Glass"',
                ],
                check=False,
            )
        elif system == "Windows":
            ps_script = (
                '[reflection.assembly]::loadwithpartialname("System.Windows.Forms") | Out-Null; '
                '[reflection.assembly]::loadwithpartialname("System.Drawing") | Out-Null; '
                '$n = New-Object System.Windows.Forms.NotifyIcon; '
                '$n.Icon = [System.Drawing.SystemIcons]::Information; '
                '$n.Visible = $true; '
                f'$n.ShowBalloonTip(10000, "{title}", "{message}", '
                '[System.Windows.Forms.ToolTipIcon]::Info)'
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                check=False,
            )
        else:  # Linux 等
            if shutil.which("notify-send"):
                subprocess.run(["notify-send", title, message], check=False)
    except Exception:
        pass
    print(f"\n[NOTIFY] {title}: {message}", flush=True)


def process(pdf_path: Path, dest_dir: Path, model: str | None = None, fallback_model: str | None = None, force: bool = False) -> None:
    # 命名規約: dest_dir のフォルダ名から arxiv_id を抽出して全ファイル名の prefix にする
    arxiv_id = extract_arxiv_id(dest_dir)
    output_files = build_output_files(arxiv_id)
    title = pdf_path.stem
    ensure_outputs_do_not_exist(dest_dir, output_files, force=force)
    print(f"[1/6] Creating notebook: {title} (arxiv_id={arxiv_id})", flush=True)
    notebook_id = create_notebook(title)
    print(f"      Notebook ID: {notebook_id}", flush=True)

    print("[2/6] Adding PDF source (waiting for processing)", flush=True)
    add_source_pdf(notebook_id, pdf_path)

    print("[3/6] Triggering 4 generations", flush=True)
    trigger_all_artifacts(notebook_id, model=model)

    print("[4/6] Waiting for all 4 to complete (polling locally)", flush=True)
    wait_until_all_completed(notebook_id, fallback_model=fallback_model)

    print(f"[5/6] Downloading to {dest_dir}", flush=True)
    download_all(notebook_id, dest_dir, output_files)

    # PDF 自体も {arxiv_id}.pdf に揃える(Apple Music 等の同名衝突回避)
    canonical_pdf = dest_dir / f"{arxiv_id}.pdf"
    if pdf_path.resolve() != canonical_pdf.resolve() and not canonical_pdf.exists():
        shutil.move(str(pdf_path), str(canonical_pdf))
        print(f"[6/6] Renamed PDF: {pdf_path.name} -> {canonical_pdf.name}", flush=True)

    notify_desktop(title, "NotebookLM 4 種ダウンロード完了")
    print("Done.", flush=True)


def main(argv: list[str]) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Process a paper with NotebookLM pipeline")
    parser.add_argument("pdf", help="Path to PDF")
    parser.add_argument("dest", nargs="?", help="Destination directory (defaults to PDF parent)")
    parser.add_argument("--force", action="store_true", help="Backup and overwrite existing artifacts")
    parser.add_argument("--model", help="Model to use for nlm calls (e.g., claude-code)")
    parser.add_argument("--fallback-model", help="Fallback model to retry failed artifacts")
    args = parser.parse_args(argv[1:])

    pdf = Path(args.pdf).expanduser().resolve()
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    dest = Path(args.dest).expanduser().resolve() if args.dest else pdf.parent
    process(pdf, dest, model=args.model, fallback_model=args.fallback_model, force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
