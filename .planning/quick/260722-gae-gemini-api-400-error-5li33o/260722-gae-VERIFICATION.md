---
quick_id: 260722-gae
slug: gemini-api-400-error-5li33o
status: passed
verified: 2026-07-22
---

# 検証レポート: 260722-gae（v1.8.1 Gemini 400 修正）

GSD-AUDIT-DIRECTIVE.md に基づく遡及検証。リモート環境（GSD 不在）で実装された
本タスクの「独立検証」を GSD-Core セッション（ローカル Windows 実機）で完了した。

## 検証結果

| 項目 | 結果 | 実施者 / 環境 |
|------|------|---------------|
| 実機 OCR: gemini-3.6-flash | ✅ 400 解消・問題なし | ユーザー（手動ビルド + 実 API キー・2026-07-22） |
| 実機 OCR: gemini-3.5-flash-lite | ✅ 400 解消・問題なし | 同上 |
| 実機 OCR: gemini-3.5-flash（退行確認） | ✅ 退行なし（パラメータ省略後も正常） | 同上 |
| pytest 全件（独立再実行） | ✅ 1109 件パス（214 秒） | GSD-Core セッション・ローカル Windows |
| pytest（RECOMMENDED_MODELS 追補後） | ✅ test_ocr_providers.py 193 件パス | 同上 |
| ruff check / format | ✅ クリーン（87 ファイル） | 同上 |
| 設計判断レビュー（精査項目 2） | ✅ 世代ゲート方式で確定（ユーザー承認） | 本セッション・2026-07-22 |
| 記録整合性（精査項目 4） | ✅ 整合（詳細は SUMMARY.md 精査結果） | 同上 |
| セキュリティレビュー | ✅ threats_open: 0（260722-gae-SECURITY.md） | 同上 |

## 補足

- リモート環境の pytest は python3.12 + xvfb-run で 1109 件、ローカル Windows でも
  同数グリーン — 環境差による退行なし。
- 世代判定フォールバック（判定不能 → パラメータ省略）は全世代で合法のため
  誤判定時も 400 は再発しない（安全側不変条件を確認）。
