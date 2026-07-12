# M001: M001: M001: M001: v1.4.0 Migration

**Vision:** PageFolio の既存コードベースに対する最適化プロジェクト。

## Slices

- [x] **S01: Provider Abstraction** `risk:medium` `depends:[]`
  > After this: OCR バックエンドを差し替え可能にするための抽象基底 `OCRProvider` と、その最初の実装 `LMStudioProvider` を新規ファイル `pagefolio/ocr_providers.

- [x] **S02: Claude Provider Ui** `risk:medium` `depends:[S01]`
  > After this: Anthropic Claude messages API を urllib 直叩きで呼び出す `ClaudeProvider` と、429/5xx リトライ可能を示す `OCRRetryableError` 例外を `pagefolio/ocr_providers.

- [x] **S03: Gemini Provider** `risk:medium` `depends:[S02]`
  > After this: Gemini を OCR プロバイダとして使えるようにする中核実装。`ocr_providers.

- [x] **S04: Tesseract Pluginmanager Qa** `risk:medium` `depends:[S03]`
  > After this: unit tests prove tesseract-pluginmanager-qa works
