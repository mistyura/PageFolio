---
quick_id: 260722-rel
slug: v181-merge-release
date: 2026-07-22
status: complete
---

# Summary: v1.8.1 マージ・リリース

GSD-AUDIT-DIRECTIVE（260722-gae）項目 5 のリリース作業を完了。

| ステップ | 結果 |
|----------|------|
| PR #34 マージ | ユーザー実施（merge commit `8741bad`・2026-07-22） |
| main ツリー検証 | ブランチ先端 `3f1c00a` と diff ゼロを確認 — pytest 1109 件グリーン・ruff クリーンの検証を流用 |
| PyInstaller ビルド | onedir 再ビルド（`--onedir --noconsole --icon=pagefolio.ico --name=PageFolio --noconfirm`）→ `v1.8.1 ビルド` コミット `d7aa217`。ビルド後 exe を実起動しプロセス生成を確認（WS 100MB） |
| サンプルプロンプト保全 | `--noconfirm` により dist/PageFolio が再作成され 2 ファイルが消失 → 事前退避分を復元し、git 追跡内容（v1.8.1 架空化済み）と完全一致を確認 |
| 注釈付きタグ | `v1.8.1` をマージコミット `8741bad` に付与し push |
| GitHub Release | [v1.8.1](https://github.com/mistyura/PageFolio/releases/tag/v1.8.1) を Latest・非 draft で公開。`PageFolio-v1.8.1-win64.zip`（48.9MB）+ `.sha256` 添付 |

## 次セッションへの申し送り

- **サンプルプロンプトのビルド消失リスク（恒久課題）**: `ocr_custom_prompt_sample.md` /
  `ocr_summary_prompt_sample.md` は dist/PageFolio 直下にのみ git 管理されており、
  PyInstaller `--noconfirm` ビルドで毎回消える。今回は手動退避→復元で対応したが、
  ソースツリー側へ原本を移して `--add-data` またはビルド後コピーのスクリプト化が
  望ましい（次マイルストーン候補）。
- 260722-gae の先送り課題②③（LLM 設定ダイアログの temperature 無視注記・新世代
  thinking 実測）は STATE.md Operator Next Steps 参照。
