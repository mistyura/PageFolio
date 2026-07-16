# Stack Research

**Domain:** PageFolio v1.8.0 新機能スタック調査（Tkinter デスクトップ PDF エディタの拡張・新規 pip 依存ゼロ方針）
**Researched:** 2026-07-13
**Confidence:** MEDIUM（標準ライブラリの機能自体・PyMuPDF スレッド安全性は公式 GitHub Issue/ドキュメント準拠で高い確度。Tkinter 仮想化の具体実装例は一般 Web 情報中心で確度が低め）

> 本ファイルは v1.8.0 マイルストーンで**新規に必要となるスタック追加・変更のみ**を扱う。既存スタック（Python 3.8+ / Tkinter / PyMuPDF 1.27.2.2 / Pillow 12.2.0 / tkinterdnd2 0.4.3・PyInstaller onedir 配布・OCRProvider 抽象化6プロバイダ）は v1.4.0〜v1.7.4 で検証済みのため再調査しない。v1.4.0 時点の OCR プロバイダ API 仕様調査は `.planning/milestones/` 配下のアーカイブ、または git 履歴上の旧 STACK.md を参照。

## 結論サマリー

v1.8.0 の新機能 4 本（プロンプト・テンプレートマネージャー・明示設定型プロバイダーフォールバック・バッチ複数ファイル OCR キュー・サムネイル仮想化）は、**すべて Python 3.8+ 標準ライブラリのみで実現可能**。新規 pip 依存の追加は不要と判断する（V14-D-01「新規 pip 依存ゼロ方針」を継続維持できる）。

唯一「どうしても足りない場合」の候補として `tksheet`（依存ゼロ・MIT・stdlib tkinter のみ）を検討したが、既存の `pagination.py` 窓表示（既定20件・上限100件）と組み合わせれば標準ライブラリのみで十分な効果が見込めるため、**新規導入は不要**と判断する（詳細は後述）。

## Recommended Stack

### Core Technologies（機能別・すべて標準ライブラリ）

| 技術 | バージョン | 用途 | 推奨理由 |
|------|---------|------|----------|
| `queue.Queue` | 3.8+ 同梱 | バッチ OCR のファイル単位ジョブキュー | `put()`/`get()`/`task_done()`/`join()` でスレッドセーフなタスク完了追跡ができる。`ocr_pipeline.py` の `PipelineState`/`send_sentinels` パターンをファイル単位に一段拡張するだけで実装できる（新規学習コストゼロ） |
| `concurrent.futures.ThreadPoolExecutor` | 3.8+ 同梱 | バッチ OCR のページ単位ワーカー並列実行 | `ocr.py` の `run_parallel()` が既にこのパターンを採用済み。ファイル横断バッチでも同一プールを流用できる |
| `threading.Lock` | 3.8+ 同梱 | バッチジョブ間の共有カウンタ保護 | `ocr_pipeline.py` の `PipelineState` が既に採用。バッチ全体の進捗集計にもそのまま拡張可能 |
| `json` | 3.8+ 同梱 | 名前付きテンプレート・フォールバック順の永続化 | `settings.py` の `_load_settings`/`_save_settings` と同型の dict→JSON パターンをそのまま流用できる |
| `os` | 3.8+ 同梱 | テンプレート md ファイルの探索・読み書き | `load_prompt_file`/`save_prompt_file`（v1.7.4）を複数ファイル対応に一般化するだけで済む |
| 標準 `list` + `try/except` | — | 明示設定順プロバイダーフォールバックの逐次試行 | Chain of Responsibility 相当をクラス階層なしで実装可能。`ocr.py` の `build_provider` ファクトリと `resolve_ocr_prompt` 解決ロジックをそのまま再利用できる |
| `tkinter.Canvas` + 既存 `pagination.py` | 標準 | サムネイル仮想化（窓表示 + 遅延 PhotoImage 生成） | Canvas は O(n) 描画でアイテム数に比例して劣化するため、既存の窓表示（既定20・上限100件）を「表示中ウィンドウ内でも可視領域外のサムネイル生成を遅延させる」方向にもう一段絞り込むアプローチが最小変更で効果が出る |

### Supporting Libraries（新規追加なし・検討したが不採用）

| モジュール | バージョン | 用途 | 判断 |
|---------|---------|---------|-------------|
| `dataclasses` | 3.8+ 同梱 | テンプレート/フォールバック設定の構造体 | **非推奨**。既存コードベースは `settings.py`/`pagination.py` 含め dict ベースで統一されており、`dataclasses` を新規導入すると型パターンが二重化する。plain dict + `.setdefault()` 方式（既存 `_load_settings` と同型）を踏襲するほうが一貫性が高い |
| `collections.OrderedDict` | 3.8+ 同梱 | テンプレートの並び順保持 | **不要**。Python 3.7+ の `dict` は挿入順を保持するため、素の `dict`/`list[dict]` で順序管理できる |
| `sqlite3` | 3.8+ 同梱 | バッチジョブの永続化 | **過剰**。バッチジョブ規模（数〜数十ファイル）では `json` スナップショットで十分（後述「Stack Patterns by Variant」） |

### Development Tools

変更なし。既存の `ruff` 0.15.7・`pytest` 9.0.2・`pytest-cov` 7.1.0 をそのまま使用する。新機能のテストも `tests/test_ocr_pipeline.py`（純ロジック層テストパターン）・`tests/test_pagination.py`（窓計算パターン）を踏襲すれば新規ツール導入は不要。

## Installation

```bash
# 新規インストール不要 — 既存 requirements.txt のまま
# (queue / threading / concurrent.futures / json / os はすべて Python 3.8+ 標準ライブラリ)
```

## 機能別インテグレーション設計

### 1. プロンプト・テンプレートマネージャー

**採用パターン:** v1.7.4 の外部 md ファイル連動（`load_prompt_file`/`save_prompt_file`）をディレクトリ化して拡張する。

- 単一の `ocr_custom_prompt.md` を、`prompts/` ディレクトリ配下の複数 `.md` ファイル（テンプレートごとに1ファイル）+ `prompts_index.json`（マニフェスト: `{"templates": [{"name": str, "filename": str, "created_at": str}], "active": str | null, "schema_version": 1}`）へ発展させる。
- 理由: (a) 既存ユーザーがすでに外部エディタでの md 編集に慣れている（v1.7.4 UX の継続）、(b) テンプレート本文を `pagefolio_settings.json` に埋め込むと DEBT-02 相当の「肥大混在」を再発させる、(c) `_get_base_dir()` の配置基準ロジックをそのまま再利用できる。
- 命名保存・切替 UI は既存 `LLMConfigDialog`（`llm_config.py`）のセクション構成に「テンプレート選択ドロップダウン + 保存/名前変更/削除ボタン」を追加する形で完結し、新規ウィジェットライブラリは不要（`ttk.Combobox` は標準）。
- スキーマバージョニング: `prompts_index.json` に `"schema_version": 1` フィールドを持たせ、読込時に `data.get("schema_version", 0)` で分岐する（Web 調査で確認した「version フィールドを持たせ読込時に分岐する」定石パターンに準拠）。

### 2. 明示設定型プロバイダーフォールバック

**採用パターン:** 標準 `list` の順次試行（Chain of Responsibility 相当）。新規クラス階層は不要。

- `settings.py` に `"ocr_fallback_order": []`（プロバイダ ID の順序リスト、既定は空＝フォールバック無効）を追加。
- 実行時は `ocr.py` の `build_provider()` を順序リストの各要素に対して呼び出し、失敗（fatal 判定）時に次の要素へ進む。既存の「送信先確認ダイアログ」（V171-KEY-04 で RunPod 分岐済み）を **各フォールバック遷移のたびに再提示**する設計とする（要件の「送信先確認再提示つき」を満たす）。自動的な別ベンダー送信をしないという既存方針（外部送信の明示同意）とも整合する。
- 新規ライブラリ・新規デザインパターンの実装コストは実質ゼロ（既存 `build_provider`/`resolve_ocr_prompt` の再利用のみ）。

### 3. バッチ複数ファイル OCR キュー管理

**採用パターン:** `ocr_pipeline.py` の producer-consumer 純ロジック層を「ファイル単位のジョブキュー」でラップする 1 段上の層として新設する（例: `batch_ocr_pipeline.py`）。

- **重要な制約（PyMuPDF 公式で再確認）:** MuPDF/PyMuPDF は公式に thread-safe ではないと明言されている（GitHub Issue #107, #1994）。Python の free-threading（PEP 703）モードでも非対応。公式推奨の回避策は `multiprocessing` だが、`fitz.Document` は pickle 不可でワーカー側がファイルパスから再オープンする必要があり、かつ **PyInstaller でフリーズしたバイナリでの `multiprocessing` はブートストラップが複雑化する**（Windows spawn 方式・`freeze_support()` 必須・onedir 配布との相性検証が別途必要）。
- したがって、バッチ複数ファイル OCR でも既存制約（V14-D-05/06: `fitz.get_pixmap()` はメインスレッドのみ）を維持し、**複数 PDF ファイルを 1 本の直列キューでメインスレッドが順番にオープン→レンダリング**し、レンダリング済み画像の **ネットワーク送信のみ** 既存 `ThreadPoolExecutor`/`ocr_pipeline.consume_one` へオフロードする設計とする。`multiprocessing` は導入しない。
- ジョブキューの構造は `queue.Queue` にファイルパスのリストを積み、`root.after()` ポーリングでメインスレッドの `fitz` 処理と UI 進捗更新を連携する（既存 `ocr_dialog.py` の `_render_next_page` パターンと同型）。複数ファイル×複数ページの入れ子進捗は `PipelineState` を拡張し `file_index`/`file_total` を追加する形で対応できる。
- 永続化（アプリ再起動をまたぐジョブ再開）が要件に含まれる場合は、`queue.Queue` はプロセス内限定なので、`json` でジョブ一覧をスナップショット保存し起動時に再構築する方式が必要（下記「Stack Patterns by Variant」参照）。

### 4. サムネイル仮想化（PERF-01）

**採用パターン:** 既存 `pagination.py` の窓表示ロジックをそのまま踏襲し、「窓内でも可視範囲外のサムネイル PhotoImage 生成を遅延させる」形で一段仮想化を強化する。

- Web 調査で確認した通り、Tkinter Canvas は GPU オフロードなしの O(n) 描画で、真の仮想化（可視範囲のみ描画・スクロール時のウィジェット動的生成/破棄）は組み込み機能として提供されない。
- ただし PageFolio は既に `pagination.py`（v1.6.0 Phase 2）で「窓表示（既定20・許容10〜100件）」を実装済みであり、レンダリングされるサムネイル数は既に上限がある。PERF-01 は「大量ページ対応」が主眼なので、対応範囲は (a) 窓サイズ内でのスクロール描画コスト、(b) `thumb_cache` のエビクション戦略の 2 点に絞れる。
- 推奨実装: `thumb_cache` にサイズ上限（例: 窓サイズの2〜3倍）を導入し、範囲外になったキャッシュエントリを破棄する。「アクセス順リスト + サイズ上限チェック」で十分実装できる（`collections.OrderedDict.move_to_end()` を使う手もあるが、既存コードが dict ベースであることを踏まえ必須ではない）。
- `tksheet` は真の仮想スクロール（可視部分のみ Canvas 再描画）を実装した唯一の実用的な軽量代替として調査したが、**採用は推奨しない**（後述「What NOT to Use」）。

## Alternatives Considered

| 推奨 | 代替 | 代替を使うべき条件 |
|------|------|-------------------|
| dict + `json.dump`（テンプレート/設定スキーマ） | `dataclasses` + 型ヒント | 将来的にテンプレート/フォールバック設定の構造がネストして複雑化し、型安全性の欠如がバグを頻発させる場合。現状の 2〜3 フィールドの平坦な構造では dict で十分 |
| `queue.Queue` + `threading`（バッチキュー） | `asyncio.Queue` | プロジェクト全体を async/await ベースに刷新する場合。現状 `ocr_pipeline.py`/`ocr.py`/`ocr_dialog.py` はすべて `threading` ベースで統一されており、`asyncio` を部分導入すると 2 つの並行モデルが混在し保守性が悪化する。**非推奨** |
| 直列メインスレッド `fitz` 処理（バッチ OCR） | `multiprocessing`（ファイル単位で並列処理） | 将来的に「1台のハイスペック PC で複数 PDF を本当に並列レンダリングしたい」という明確な性能要件が出た場合のみ。PyInstaller onedir 配布での `multiprocessing` 動作検証・`fitz.Document` の再オープンコストなど追加検証が必要なため、v1.8.0 スコープでは見送るべき |
| `pagination.py` 窓表示 + キャッシュエビクション（サムネイル仮想化） | `tksheet`（外部ライブラリ・依存ゼロ） | 窓表示を最大件数（100件）に設定した状態でもスクロール時の体感遅延が解消しない、かつ独自実装のエビクション戦略では追いつかないと実測で判明した場合のみ検討。ただし `tksheet` はスプレッドシート/テーブル UI であり、既存のサムネイル「グリッド + D&D 並び替え」UI とは操作モデルが異なるため、採用時は D&D（`dnd.py`）の全面書き換えが必要になる点に注意 |

## What NOT to Use

| 避けるべき技術 | 理由 | 代わりに使うもの |
|-------|-----|-------------|
| `dataclasses-json` / `pydantic` / `marshmallow`（サードパーティ） | 新規 pip 依存が PyInstaller onedir 配布サイズを増やす（V14-D-01 方針に反する）。テンプレート/フォールバック設定は 2〜3 フィールドの平坦な dict で十分表現できる規模 | 標準 `json` + `dict.setdefault()`（`settings.py` と同型） |
| `asyncio` の部分導入 | 既存コードベース全体が `threading`/`queue` ベースで統一されており、`asyncio` を一部機能だけに導入すると 2 つの並行モデルが混在し、`fitz` のメインスレッド制約（V14-D-05）との相互作用も検証コストが増す | 既存 `threading.Lock`/`queue.Queue`/`ThreadPoolExecutor` パターンの拡張 |
| `multiprocessing`（バッチ複数ファイル OCR の並列化） | PyMuPDF が公式に thread-safe でないことの回避策として文書化されているが、`fitz.Document` の pickle 不可・PyInstaller フリーズ環境での spawn ブートストラップの複雑化・ワーカーごとの再オープンコストなど、v1.8.0 の「単独フェーズへ隔離」する程度の規模には見合わないオーバーヘッド | 直列メインスレッド `fitz` 処理 + ネットワーク送信のみ `ThreadPoolExecutor` へオフロード（既存 `ocr_pipeline.py` パターンの拡張） |
| `tksheet`（サムネイル仮想化の第一選択として） | テーブル/シート UI であり、既存のサムネイルグリッド + D&D 並び替え UI とは操作モデルが根本的に異なる。導入すると `dnd.py`/`viewer.py` の全面書き換えが必要になり、PERF-01（パフォーマンス改善）のスコープを大きく超える | `pagination.py` 窓表示 + `thumb_cache` エビクション戦略の強化 |

## Stack Patterns by Variant

**バッチ OCR ジョブの永続化（アプリ再起動をまたぐ再開）が要件に含まれる場合:**
- `queue.Queue` はプロセス内限定のため、`json` でジョブ一覧（ファイルパス・進捗状態・完了ページ数）を定期的にスナップショット保存する
- 理由: `sqlite3`（標準ライブラリ）も選択肢になるが、バッチジョブの規模（数〜数十ファイル）では過剰。`pagefolio_settings.json` と同じ形式の平坦 JSON で十分

**フォールバック順序が将来 4 プロバイダ以上に複雑化する場合:**
- それでも標準 `list` + `try/except` の逐次試行で対応可能（プロバイダ数が増えても計算量は O(n) のまま）
- 理由: Chain of Responsibility の本質は「順序リストの逐次試行」であり、クラス階層化しても可読性は上がらない規模

**サムネイル窓サイズがユーザー設定で 100 件に達し、なお体感遅延がある場合:**
- まず `thumb_page_size` の上限自体を引き下げる方向（例: 上限 100→60）で対応できないか検討する
- それでも不十分な場合のみ `tksheet` 系の真の仮想スクロールライブラリ導入を再検討する（上記「代替を使うべき条件」参照）

## Version Compatibility

| パッケージ | 互換対象 | 備考 |
|-----------|-----------------|-------|
| `queue` / `threading` / `concurrent.futures` / `json` / `dataclasses`（不採用） | Python 3.8+ | すべて標準ライブラリ同梱。プロジェクトの `pyproject.toml` 制約（Python 3.8+ 型ヒント互換）に影響なし |
| PyMuPDF (fitz) 1.27.2.2（現行固定） | 最新 1.28.0（2026-06-29 リリース） | v1.8.0 のバッチ OCR 機能追加にあたり PyMuPDF のバージョンアップは**必須ではない**（1.27.2.2 → 1.28.0 間の変更履歴にバッチ処理・スレッド安全性に関わる破壊的変更は見当たらない）。中間版 1.27.2.3（2026-04-24・`scrub()`/`get_links()` 修正）への追随は次回メンテナンス時の検討事項として残す |
| `ttk.Combobox`（テンプレート切替 UI） | Tkinter 標準（Python 3.8+ 同梱） | 新規ウィジェット導入不要。`LLMConfigDialog` の既存セクション構成パターンに追加するだけで完結 |

## Sources

- [queue — A synchronized queue class (Python 公式ドキュメント)](https://docs.python.org/3/library/queue.html) — MEDIUM（公式ドキュメント + 複数の解説記事で内容一致を確認）
- [Thread Producer-Consumer Pattern in Python – SuperFastPython](https://superfastpython.com/thread-producer-consumer-pattern-in-python/) — MEDIUM
- [Is PyMuPDF re-entrant / thread-safe? · Issue #107 · pymupdf/PyMuPDF](https://github.com/pymupdf/PyMuPDF/issues/107) — MEDIUM（公式リポジトリのメンテナ回答）
- [Clarification about threading · Issue #1994 · pymupdf/PyMuPDF](https://github.com/pymupdf/PyMuPDF/issues/1994) — MEDIUM（公式リポジトリのメンテナ回答、Issue #107 と内容が一致）
- [Multiprocessing - PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html) — MEDIUM（公式ドキュメント）
- [Change Log - PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/changes.html) — LOW（バージョン履歴の一般 Web 検索経由の要約、一次情報は公式だが取得は Web 検索経由）
- [Understanding Tkinter Canvas Performance Limitations — ancisoft.com](https://www.ancisoft.com/blog/understanding-performance-limitations-of-the-tkinter-canvas/) — LOW（単一ブログ記事、一般的な Tkinter 知識と整合するが一次情報ではない）
- [tksheet · PyPI](https://pypi.org/project/tksheet/) — LOW（PyPI ページ直接取得だが webfetch 経由のため確信度は控えめ）
- [GitHub - ragardner/tksheet](https://github.com/ragardner/tksheet) — LOW
- [Serializing Dataclasses | Tom's Blog](https://tomaugspurger.net/posts/serializing-dataclasses/) — LOW
- [dataclasses-json · PyPI](https://pypi.org/project/dataclasses-json/) — LOW（不採用の根拠確認のため参照）
- [Build a Pluggable API Fallback System — Medium](https://medium.com/@gagan.here/building-a-flexible-verification-pipeline-with-factory-strategy-chain-of-responsibility-dffe144d8d97) — LOW
- 社内一次情報: `pagefolio/ocr_pipeline.py`（producer-consumer 純ロジック層の既存実装）・`pagefolio/settings.py`（dict + JSON 永続化パターンの既存実装）・`pagefolio/pagination.py`（窓表示純ロジック層の既存実装） — HIGH（コードベース直接確認）

---
*Stack research for: PageFolio v1.8.0 新機能（テンプレートマネージャー・プロバイダーフォールバック・バッチ OCR キュー・サムネイル仮想化）*
*Researched: 2026-07-13*
