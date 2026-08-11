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

単一プロセスでのフルスイート実行（現在 1404 件収集）が合格条件。分割実行は不要。

### 既知の環境症状（2 症状・現況は別々）

| 症状 | 現況 | 直近の観測 |
|------|------|-----------|
| ① `TclError` によるセットアップ ERROR | **再発する。非再現とは言えない** | 2026-08-12 に再現（`tests/test_toast.py` の 8 件が ERROR・1396 passed / 8 errors）。同日の他 3 実行はいずれもグリーン |
| ② `STATUS_BREAKPOINT` プロセスクラッシュ | 現行環境では未再現 | v1.9.0 Phase 3 の切り分け調査（10 回）+ リサーチセッション（7 回）の計 17 回連続でクラッシュ 0 件。以降も再現報告なし |

症状①は v1.9.0 Phase 3 時点で「現行環境では再現しない」と結論づけていたが、**2026-08-12 に再現した**。
当時の調査ログも根本原因はネイティブ層で未解明・非再現の因果は未証明と留保しており、その留保が
現実になった形。**症状①の非再現を前提にした判断はしないこと。**

### ERROR が出たときの切り分け

1. 該当ファイル単体で実行する（例: `pytest -q tests/test_toast.py`）
2. フルスイートを再実行する

2026-08-12 の実測では 1 で 33 passed、2 で 1404 passed だった。**ただしこれは原因を症状①へ切り分ける
ための手順であり、再実行でグリーンになったことをもって合格とする手順ではない。** 合格条件は上記の
とおり単一プロセスのフルスイートが失敗 0 件・ERROR 0 件・クラッシュなしで完走することであり、
「flaky だから通す」は不可。ERROR を観測したら、再実行の結果とあわせて必ず申し送りに記録すること。

**`--basetemp` について:** `%TEMP%\pytest-of-shdwf` のロック競合回避専用であり、テストを
1 件も除外しない。実行環境でロック競合が起きないなら省略してよい。

**やってはいけないこと:** テストの削除・skip マーク付与・`-k` / `--ignore` による静かな
除外でゲートを通すこと。除外を伴う運用を採る場合は対象と件数と根拠を必ず明示し、合計が
全件と一致することを示すこと。

**根拠:**

- v1.9.0 Phase 3 の切り分け調査（2 症状の一次データと当時の結論）: [.planning/milestones/v1.9.0-phases/03-qa-release-gate/03-TEST-ENV-INVESTIGATION.md](.planning/milestones/v1.9.0-phases/03-qa-release-gate/03-TEST-ENV-INVESTIGATION.md)
- 症状①の再現観測（2026-08-12）: [.planning/quick/260812-a43-claude-md/260812-a43-SUMMARY.md](.planning/quick/260812-a43-claude-md/260812-a43-SUMMARY.md)

---

## セッション終了時のルール

作業が完了したら、依頼されなくても必ず日本語で申し送りを出力すること。
この出力は claude.ai に貼り付けて Notion を更新するために使用する。
**書式は `session-handoff` スキル（`.claude/skills/session-handoff/SKILL.md`）を参照すること。**

<!-- GSD:project-start source:PROJECT.md -->

## Project

プロジェクト概要・コアバリュー・制約 (Tech stack / 互換性 / スレッド制約 / CropBox 安全処理 / 品質ゲート / 言語 / 禁止 / Security / ブランチ運用) の正本は [.planning/PROJECT.md](.planning/PROJECT.md) を参照。

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

言語・ランタイム・依存ライブラリ・配布形態（PyInstaller onedir）・プラットフォーム要件の詳細は [.planning/codebase/STACK.md](.planning/codebase/STACK.md) を参照。

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

命名規約・コードスタイル・import 構成・テスト規約・禁止パターンの詳細は [.planning/codebase/CONVENTIONS.md](.planning/codebase/CONVENTIONS.md) を参照。

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Mixin 構成・コンポーネント責務・データフロー・主要抽象・エントリポイント・アーキテクチャ制約（Threading / Global state / Undo 上限と Blob ライフサイクル / CropBox safety / PDF open-close / Pagination window）の詳細は [.planning/codebase/ARCHITECTURE.md](.planning/codebase/ARCHITECTURE.md) を参照。

補足ドキュメント: [STRUCTURE.md](.planning/codebase/STRUCTURE.md) (ディレクトリ詳細) / [CONCERNS.md](.planning/codebase/CONCERNS.md) (技術的負債) / [INTEGRATIONS.md](.planning/codebase/INTEGRATIONS.md) (外部連携) / [TESTING.md](.planning/codebase/TESTING.md) (テスト戦略)。

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
