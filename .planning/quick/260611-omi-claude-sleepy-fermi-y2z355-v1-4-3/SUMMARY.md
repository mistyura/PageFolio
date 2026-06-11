---
quick_id: 260611-omi
slug: claude-sleepy-fermi-y2z355-v1-4-3
date: 2026-06-11
status: complete
---

# Summary: v1.4.3 確定（マージ・リビルド・ドキュメント更新）

## 実施内容

1. **マージ**: `origin/claude/sleepy-fermi-y2z355` を `main` へ fast-forward マージ
   （`8f996cf..197fbb7`、コンフリクトなし）。`APP_VERSION = "v1.4.3"` 確定。
2. **品質確認**: `ruff check .` クリーン / `pytest` 445 件パス。
3. **リビルド**: PyInstaller（`PageFolio.spec`, onedir）で `dist/PageFolio/` を再ビルドし
   `PageFolio.exe` / `base_library.zip` を「v1.4.3ビルド」コミット（`abfe97c`）。
4. **ドキュメント更新**: `.planning/STATE.md`（Quick Tasks Completed 行追加・Session Continuity・
   Operator Next Steps）。README バッジ・推奨モデル一覧・開発履歴.md v1.4.3 エントリは
   マージ済みブランチに既に含まれていたため追加変更なし。

## v1.4.3 に含まれる変更（マージ由来）

- H-6: OCR ダイアログ クリア後の再実行が前回の致命的エラー残留で即終了する問題を修正
- H-7: Gemini API 経由で gemma モデル選択時に 400 エラーになる問題を修正
- 埋め込みテキストを無視して OCR を実行するオプション追加
- 429 と 5xx のエラーメッセージを分離（500 をレート制限と誤認しない）
- OCR テキスト抽出画面に現在選択中のモデル名を表示・プロバイダ行レイアウト調整
- テスト追加: `tests/test_ocr.py` +283 / `tests/test_ocr_providers.py` +62

## コミット

| Commit | 内容 |
|--------|------|
| `197fbb7`（マージ先端） | ブランチの全 v1.4.3 変更（ff マージで取り込み） |
| `abfe97c` | v1.4.3ビルド（`dist/` 再ビルド成果物） |

## 未実施（申し送り）

- `git push origin main`（未プッシュ）
- GitHub Release 作成（v1.4.0 の 260609-aaa 手順を踏襲）
- H-7 修正の実 API キー環境での動作確認
