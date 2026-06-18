# Phase 07 — Discussion Log

**Date:** 2026-06-09
**Phase:** 07-tesseract-pluginmanager-qa
**Facilitator:** Claude (gsd-discuss-phase)

---

## Areas Discussed

### 1. Tesseract の検出・UI

| 質問 | 選択肢 | 決定 |
|------|--------|------|
| 未インストール時の選択肢の扱い | 起動時チェックで disabled / 常に表示し実行時エラー / 設定時チェック | **起動時チェックで disabled** |
| 精度劣後注記の表示場所 | llm_config 常設 / Combobox 選択時のトースト / コスト確認ダイアログ内 | **llm_config 常設** |

**備考:** Phase 6 の `ocr_scale` ヒントと同じ「常設ラベル」パターンで実装。

---

### 2. 言語設定（OCR lang）

| 質問 | 選択肢 | 決定 |
|------|--------|------|
| OCR lang の扱い | jpn+eng 固定 / 入力欄を追加 / Combobox で有効ラング一覧 | **jpn+eng 固定（jpn 未インストール時は eng フォールバック）** |

**備考:** V14-D-01「pip 依存ゼロ」方針から、`subprocess tesseract --list-langs` で言語確認。UI 追加によるユーザー設定は将来フェーズへ defer。

---

### 3. register_ocr_provider API

| 質問 | 選択肢 | 決定 |
|------|--------|------|
| 渡す型 | クラス / インスタンス / factory 関数 | **クラスを渡す（register_ocr_provider(name, cls)）** |
| 登録先 | PluginManager に追加 / ocr.py のグローバル辞書 / OCRProviderRegistry クラス | **PluginManager に追加** |
| Combobox への追加タイミング | 展開時に取得 / 登録時に即時更新 / 手動（プラグイン右考） | **展開時に取得** |

**備考:** 既存 `fire_event` パターンとの一貫性を重視。`on_load` 内で呼び出す設計。

---

### 4. ドキュメント整備の範囲

| 質問 | 選択肢 | 決定 |
|------|--------|------|
| README.md の内容 | OCR セクション更新 / 最小限（バッジ・Changelog のみ） | **OCR セクションを更新（プロバイダ一覧・環境変数・Tesseract インストール案内）** |
| lang.py の範囲 | Tesseract 専用のみ / 全プロバイダの未整備文言もまとめて整備 | **全プロバイダの未整備文言もまとめて整備（ocr_progress_skip 等の整理を含む）** |

---

## Deferred Ideas

- Tesseract の言語パック選択 UI → 将来フェーズ
- TesseractProvider の psm/oem 公開設定 → 将来フェーズ

---

*Log generated: 2026-06-09*
