# CLAUDE.md — PageFolio AI 開発指示書

このファイルは Claude (AI) がこのプロジェクトを編集・拡張する際に参照する指示書です。
エンドユーザー向けの情報は [README.md](README.md)、変更履歴は [開発履歴.md](開発履歴.md) を参照してください。

---

## プロジェクト概要

| 項目 | 内容 |
|------|------|
| アプリ名 | PageFolio |
| 対象 OS | Windows 11 |
| 現在バージョン | `pagefolio/constants.py` の `APP_VERSION` を参照 |

> バージョン番号は `pagefolio/constants.py` の `APP_VERSION` を真の情報源とする。
> README.md のバッジ・開発履歴.md の最新エントリと同期させること。

---

> ファイル構成は `ls` / `git ls-files` で、モジュールごとの責務は `pagefolio/CLAUDE.md` を参照。

---

## コーディング規約

### 構造・命名

- **パッケージ構成を維持する**: `pagefolio/` パッケージにモジュール分割済み。Mixin パターンで PDFEditorApp を構成。
- **メソッド名**: `_` プレフィックスで内部メソッドを示す。
- **テーマ色の参照**: グローバル定数ではなく `C["BG_DARK"]` 等のテーマ辞書を使う。
- **フォントサイズ**: ハードコードせず `self._font(delta)` ヘルパーを使う（ベース + delta）。

### ボタンスタイル

- 通常操作 → `"TButton"`
- 主要アクション → `"Accent.TButton"`
- 破壊的操作（削除・終了） → `"Danger.TButton"`
- トリミングモード ON → `"CropOn.TButton"`

### 操作後の作法

- **再描画**: ページ変更後は必ず `self._refresh_all()` を呼ぶ。
- **ステータス表示**: 操作完了後は `self._set_status(msg)` でヘッダーに表示。
- **ファイル操作前の確認**: `self._check_doc()` で `self.doc` の存在を確認する。
- **トリミング安全処理**: CropBox は必ず MediaBox 内にクランプしてから `set_cropbox` を呼ぶ。
- **設定保存**: `pagefolio_settings.json` に JSON で永続化（`_save_settings()`）。

### 作業フロー

- **1タスクずつ完了させてから次のタスクへ進むこと**
- **リント必須**: py ファイルを編集したら必ず `ruff check . && ruff format .` が通ることを確認すること
- **テスト必須**: コミット前に `pytest` を通すこと

### 禁止事項

- `pyproject.toml` の編集
- 裸の `except:` 句（必ず `except Exception as e:` の形で）
- `# type: ignore` の無断使用

---

## 言語ルール

タスクリスト（TodoWrite）の内容を含め、**すべての返答を日本語で行うこと**。

以下の出力も**原則日本語**で記述する。

| 対象 | 例 |
|------|-----|
| コミットメッセージ | `ページ回転機能のバグを修正` |
| ブランチ説明・PR タイトル / 本文 | `サムネイルD&Dの末尾ドロップ対応` |
| GitHub Issue のタイトル / コメント | `トリミング後にプレビューが更新されない` |
| コードレビューのフィードバック | `この条件分岐は不要では？` |
| `開発履歴.md` の記載 | 既存ルール通り |
| セッション終了時の申し送り | `session-handoff` スキルのフォーマット |
| ユーザーへの応答・説明 | 会話はすべて日本語 |

**例外（英語のまま）**:

- ソースコード中の変数名・関数名・クラス名
- ライブラリ名・コマンド名（`pymupdf`, `git push` など）
- エラーメッセージの引用（原文ママ）

---

## 既知の制限・注意事項

- トリミングは **選択中のページ全体** に一括適用（複数選択時は相対座標変換で各ページに適用）
- D&D による複数ページ一括移動は **選択ページをまとめて移動**（単一ページ D&D も引き続き動作）
- パスワード保護 PDF は開く際にパスワード入力を求める（`_authenticate_doc`）。パスワードの付与（AES-256）/解除は「🔒 パスワード」セクションから別名保存で行う
- 印刷は OS の既定 PDF ハンドラへ送る方式（Windows: `os.startfile(path, "print")`）。Windows 以外は未対応で情報通知に留める
- `set_cropbox` によるトリミングはメタデータ上の cropbox 変更であり、PDF の物理的なページサイズは変わらない
- 黒塗り・モザイク（`redact_ops.py`）は **破壊的操作**: `apply_redactions()` は矩形下のテキスト・画像を実削除し、矩形に交差する注釈も削除される（PyMuPDF 仕様）。undo は `page_edit` op（適用前ページ bytes）で可能。回転表示中のページでも `page_ops.py` の共通ヘルパー `_derotate_rect`（`page.derotation_matrix` 使用）により表示座標→未回転座標へ変換されるため、トリミング・黒塗り・モザイクの3操作すべてで「見たままの位置」に適用される（v1.7.1 Phase 3・D-08 で解消）
- 黒塗り/モザイクは連続適用（明示トグルで OFF にするまでモード維持）に対応し、複数矩形を追加してから一括適用できる。1回の Undo で全矩形がまとめて戻る（v1.7.1 Phase 3・D-05/D-07）。モザイクの粒度は右ペインのスライダーで調整でき `pagefolio_settings.json` に永続化される（D-06）
- サムネイルは `fitz.Matrix(0.22 * z, 0.22 * z)`（`z` は `thumb_zoom_var`、既定 1.0）のスケールで生成（変更時はパフォーマンスに注意）
- プレビューは `self.zoom * 1.5` のスケールで生成
- 右ペインはスクロール可能な Canvas 構成（`_build_tools_scrollable` で実装）
- OCR・クラウド LLM 固有の注意事項（API キーの扱い、リトライ制御、スレッド制約、外部プロンプトファイル連動、Gemini のパラメータ制限、モデル一覧取得）は [pagefolio/CLAUDE.md](pagefolio/CLAUDE.md) の「OCR・LLM の注意事項」を参照
- **`pagefolio/ocr_providers/registry.py` の独立性制約**（v1.8.0 Phase 1 新設のプロバイダ→環境変数 中央レジストリ）: Python 標準ライブラリ（`os`）のみに依存し、pagefolio 内部の他モジュール（特に `settings.py`・UI 関連）を import しない。settings.py 等から参照される際の循環 import を構造的に防ぐための制約であり、将来も内部モジュールへの import 依存を追加しないこと。新プロバイダの機密キー定義追加はこの1ファイルに閉じる（V180-ROBUST-02）

---

## 変更時のチェックリスト

- [ ] `ruff check . && ruff format .` でリント・フォーマット確認
- [ ] `python -c "import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"` で構文確認
- [ ] `pytest` でテスト確認（合格条件の詳細は下記「リリースゲート」節を参照）
- [ ] `開発履歴.md` に変更内容を追記
- [ ] バージョン番号を更新（`pagefolio/constants.py` の `APP_VERSION`、開発履歴.md、README.md のバッジ）

---

## リリースゲート（全テスト完走条件）

**合格条件:** 以下のコマンドが失敗 0 件・ERROR 0 件・プロセスクラッシュなしで完走すること。

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"
```

単一プロセスでのフルスイート実行（現在 1398 件収集）が合格条件。分割実行は不要。
過去に観測されていた `TclError` によるセットアップ ERROR・`STATUS_BREAKPOINT` プロセス
クラッシュの2症状は、v1.9.0 Phase 3 の切り分け調査（10回連続実行）で現行環境では
再現しないことを確認済み（リサーチセッションの7回と合算し累計17回連続グリーン）。

**`--basetemp` について:** `%TEMP%\pytest-of-shdwf` のロック競合回避専用であり、テストを
1 件も除外しない。実行環境でロック競合が起きないなら省略してよい。

**やってはいけないこと:** テストの削除・skip マーク付与・`-k` / `--ignore` による静かな
除外でゲートを通すこと。除外を伴う運用を採る場合は対象と件数と根拠を必ず明示し、合計が
全件と一致することを示すこと。

**根拠:** [.planning/phases/03-qa-release-gate/03-TEST-ENV-INVESTIGATION.md](.planning/phases/03-qa-release-gate/03-TEST-ENV-INVESTIGATION.md)

---

## セッション終了時のルール

作業が完了したら、依頼されなくても必ず日本語で申し送りを出力すること。
この出力は claude.ai に貼り付けて Notion を更新するために使用する。
**書式は `session-handoff` スキル（`.claude/skills/session-handoff/SKILL.md`）を参照すること。**

<!-- GSD:project-start source:PROJECT.md -->

## Project

**PageFolio — コード最適化プロジェクト**

PageFolio の既存コードベースに対する最適化プロジェクト。
バグ修正・リファクタリング・テスト充実の 3 軸で品質を底上げする。

**Core Value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする。
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architectural Constraints

- **Threading:** UI runs on the Tkinter main thread. Preview and thumbnail renders are processed on the main thread via `root.after()` chained calls; generation counters (`_preview_gen`, `_thumb_gen`) prevent stale results from overwriting newer ones. OCR uses `ThreadPoolExecutor`.
- **Global state:** `C` (theme dict) and `_current_font_size` in `pagefolio/settings.py` are module-level mutable singletons updated at runtime.
- **Undo limit:** Hard-coded to `MAX_UNDO = 20` in `pagefolio/app.py`. 各エントリは操作固有のデルタ dict（rotate: 回転値リスト、crop: cropbox タプル、delete/page_edit: ページ単位 Blob 等）であり、full PDF シリアライズではない。
- **Undo Blob ライフサイクル（v1.7.0）:** ページ単位のキャプチャは必ず `_capture_page_blob(page_i)` 経由で行う（64KiB 以上は `UndoBlobStore` が tempfile へ退避・未満は MemBlob）。復元側は `self._blob_bytes(data)` で bytes を取り出す（生 bytes 後方互換）。解放は deque 溢れ（`_push_evicting`）・redo クリア（`_clear_redo_stack`）・消費時（`_undo`/`_redo` 内の identity 比較付き dispose）・ファイルクローズ/終了時（`_clear_undo_stacks` → purge）＋ atexit。スタックへの直接 `append`/`clear` は禁止（Blob がリークする）。
- **CropBox safety:** All crop operations must clamp the `CropBox` inside the page's `MediaBox` before calling `set_cropbox()` (`pagefolio/page_ops.py`).

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
