---
last_mapped_commit: fb41c422035fa9d4fac753920909da56e068555c
---

# PageFolio — アーキテクチャ (Architecture)

## 設計スタイル (Architectural Style)

PageFolio は、GUI に Python 標準の **Tkinter**、PDF 処理に **PyMuPDF (fitz)** を使用したデスクトップアプリケーションです。
アプリケーションの複雑化を防ぐため、**多重継承による Mixin パターン**と、GUI や PDF エンジンに依存しない**「純ロジック層」の分離**を基本設計としています。

```mermaid
graph TD
    App[PDFEditorApp (app.py)] --> UIBuilder[UIBuilderMixin (ui_builder.py)]
    App --> FileOps[FileOpsMixin (file_ops.py)]
    App --> PageOps[PageOpsMixin (page_ops.py)]
    App --> RedactOps[RedactOpsMixin (redact_ops.py)]
    App --> Viewer[ViewerMixin (viewer.py)]
    App --> DnD[DnDMixin (dnd.py)]
    App --> OCR[OCRMixin (ocr.py)]
    App --> Print[PrintOpsMixin (print_ops.py)]

    FileOps --> UndoStore[UndoBlobStore (undo_store.py)]
    OCR --> OCRPipeline[PipelineState / consume_one (ocr_pipeline.py)]
    Viewer --> Pagination[Pagination Logic (pagination.py)]
    App --> Plugins[PluginManager (plugins.py)]
```

---

## 核心モジュールと境界 (Core Boundaries)

### 1. アプリ本体と Mixin 構成 (`pagefolio/app.py` & Mixin 群)
`PDFEditorApp` はすべての Mixin を多重継承で統合する「ハブ」です。状態管理のメイン属性 (`self.doc`, `self.current_page`, `self.selected_pages`, `self.settings`) を保持し、各 Mixin がそれらを読み書きします。

### 2. Tkinter / fitz 非依存の「純ロジック層」
UI ライフサイクルや PDF エンジン（PyMuPDF）に依存しないロジックを別モジュールに分離することで、高いテスト容易性を確保しています。

- **`pagination.py`**: サムネイル表示窓（既定 20 ページ）の計算、グローバル ↔ ローカルインデックス変換を行う純関数群。
- **`md_render.py`**: OCR 結果の Markdown テキストを行種別やインライン装飾情報にパースする純粋なテキストパーサ。
- **`undo_store.py`**: メモリを圧迫する PDF 変更履歴 (Undo) 用のページデータを一時ファイルへ退避する Blob 管理ストア。
- **`ocr_pipeline.py`**: スレッドセーフな共有ステータス管理 (`PipelineState`) と、1アイテム処理ロジック。

---

## 核心データフロー (Core Data Flow)

### 1. ディスク退避型 Undo / Redo と Blob ライフサイクル
Undo 履歴を保持するため、ページ削除や編集時の元データを PDF ページ単位でキャプチャしスタックに積みます。
高解像度 PDF などでメモリが圧迫されるのを防ぐため、以下の Blob ライフサイクル制御を導入しています。

```
[操作実行 (例: ページ削除)]
   │
   ├─► bytes が 64KiB 未満 ──► MemBlob (メモリ上保持)
   └─► bytes が 64KiB 以上 ──► FileBlob (一時ファイル page_*.pdf へ退避)
   │
[Undo スタックへ積む (最大20世代)]
   │
   ├─► 世代溢れ (Eviction) ──► Blob.release() (一時ファイルの物理削除)
   └─► Undo/Redo で消費 ──► self._blob_bytes() で復元後、Blob.release()
```

- **安全な解放**: deque の溢れ、Redo スタックのクリア、ファイルのクローズ、アプリ終了 (`atexit` フック) のすべての経路で、一時ファイルが確実に `purge` / `release` されるよう `FileOpsMixin` 内で一元管理されています。

### 2. サムネイルとプレビューの世代制御 (`_preview_gen` / `_thumb_gen`)
プレビュー描画やサムネイルのレンダリングは、重い PDF 読み込み処理が UI スレッドをブロックしないよう `root.after()` で非同期にスケジュールされます。
ユーザーが連続でページを切り替えた際、古いプロセスの処理結果が後から届いて上書きされる「競合状態（Race Condition）」を防ぐため、**「世代カウンタ（Generation Counter）」**を使用しています。

- レンダリング開始時に `_preview_gen` をインクリメント。
- 描画処理が完了した際、登録時の世代番号と現在の `_preview_gen` が一致している場合のみ Tkinter キャンバスに画像を描画し、不一致であれば結果を破棄します。

### 3. OCR 実行パイプライン (スレッド制御)
OCR 処理は `ThreadPoolExecutor` を用いてバックグラウンドで並列実行されます。
- `PipelineState` (内部で `threading.Lock` を保持) が、ワーカー間の進捗・サーキットブレーカー発動条件（連続3回失敗で OCR 停止）・致命的エラー（Connection/Timeout）の状態遷移を一元管理します。
- メイン UI は `ocr_dialog.py` で `PipelineState` を監視し、スレッドセーフに進捗を画面描画します。

---

## デザインパターン (Key Design Patterns)

1. **Mixin パターン**
   大規模な GUI クラス `PDFEditorApp` の責務を、ファイル操作・ページ操作・ビューア等に明確に分解。
2. **Blob パターン (MemBlob / FileBlob)**
   保存先（メモリかディスクか）のポリモーフィズムを統一インターフェース（`load()`, `release()`）で隠蔽。
3. **イベント駆動 (プラグインシステム)**
   `PluginManager` がアプリ内の操作完了（回転・削除・保存等）をフックし、`PDFEditorPlugin` のサブクラスへイベント通知。
4. **サーキットブレーカーパターン**
   `ocr_pipeline.py` において、接続エラーなどの致命的エラーまたは連続した API エラーを検出した際、後続の API 課金が発生する呼び出しを遮断する。
5. **世代ガード (Generation Guard)**
   Tkinter の非同期 `after()` レンダリングで最新の要求状態のみを画面に反映する。
