# API Coverage — Phase 01（safety-rollback）

No external API integration: 本フェーズが触るのはローカルの `fitz`（PyMuPDF）ドキュメント操作・Tkinter UI・`pagefolio_settings.json` / 外部プロンプト md のローカル I/O のみで、フェーズ内のどのプランも外部 API / SDK / サービスへの新規統合を行わない。

## 検出シグナルの評価

決定的ディテクタ（`bin/lib/api-coverage.cjs`）は `detected: true` を返したが、そのシグナルは既存プラン（01-02）の `<threat_model>` に記載された **既存**のクラウド OCR 境界の説明文（「ローカルの PDF ページ画像 → クラウド OCR API（Claude / Gemini / RunPod）」）に一致したものである。当該記述は V190-SAFE-03（OCR OFF の一貫化＝**この境界を閉じる**要件）の脅威モデルとして書かれた説明であり、新しい API 統合ではない。クラウド OCR プロバイダ自体は v1.4.0〜v1.8.1 で既に出荷済みの既存機能であり、本フェーズはその呼び出し面を一切変更していない。

新規プロバイダ（OpenAI / ChatGPT）の追加は **Phase 2（V190-CAT-01/02・V190-OAI-01〜13）** のスコープであり、そのフェーズの計画時に本チェックポイントが改めて発火する。

## 本フェーズ（01-07 を含む）が実際に触る面

| 面 | 種別 | 備考 |
|---|---|---|
| `fitz`（PyMuPDF）Document API | ローカルライブラリ | 既存依存。バージョン変更なし |
| Tkinter / `tkinter.messagebox` | ローカル GUI | 既存依存 |
| `pagefolio/undo_store.py`（tempfile） | ローカルファイルシステム | 既存依存 |
| `pagefolio_settings.json` / `ocr_*_prompt.md` | ローカルファイル I/O | 既存依存 |

---

*Recorded: 2026-08-11 — gsd-planner（01-07 計画時）*
