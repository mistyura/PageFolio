# Phase 2: OCR 磨き込み（レビュー残の現行照合と二重実装解消） - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-05
**Phase:** 2-OCR 磨き込み（レビュー残の現行照合と二重実装解消）
**Areas discussed:** L-1 一本化の方向性, L-4 Tesseract 言語フォールバック, L-2/L-3 プラグイン registry ポリシー, L-6 活き残りの確定範囲

---

## L-1 一本化の方向性

### Q1: どちらの実装を正とするか

| Option | Description | Selected |
|--------|-------------|----------|
| 純ロジック層へ集約（推奨） | ocr_dialog.py の実戦済み挙動を仕様として ocr.py 側ヘルパーを書き直し、dialog が消費。pagination.py/md_render.py と同型パターン | ✓ |
| dialog 実装を正・ヘルパー削除 | ocr_dialog.py は触らず run_with_bounded_buffer と関連テストを削除/移植。挙動リスク最小だがメモリ上限保証のテスト担保が弱まる | |
| お任せ（planner 判断） | 両実装の乖離精査後にリスク・工数バランスで決定 | |

### Q2: 純ロジック層の配置先

| Option | Description | Selected |
|--------|-------------|----------|
| 新モジュール ocr_pipeline.py（推奨） | Tk/fitz 非依存の独立ファイル + tests/test_ocr_pipeline.py。CLAUDE.md 構成表へ追記 | ✓ |
| ocr.py 内で改修 | ファイル追加なし・import 変更最小。ocr.py はさらに肥大 | |
| お任せ（planner 判断） | 抽出規模で判断 | |

### Q3: L-6 パイプライン系小物の解消先

| Option | Description | Selected |
|--------|-------------|----------|
| L-1 プランに吸収（推奨） | プログレス 100%・producer fatal 後 render 継続・sentinel 明文化を L-1 独立プラン内で同時仕様化 | ✓ |
| L-6 一括プランで先に解消 | 先に直すとパイプライン書き直しで二度手間リスク | |

### Q4: 一本化の対象範囲（_summary_worker）

| Option | Description | Selected |
|--------|-------------|----------|
| 画像 OCR パイプラインのみ（推奨） | 二重実装の実体は複数ページ画像 OCR 経路のみ。サマリは現行維持 | ✓ |
| サマリ経路も共通基盤に寄せる | スコープ拡大・回帰面増 | |

---

## L-4 Tesseract 言語フォールバック

### Q1: フォールバック時のユーザーへの伝え方

| Option | Description | Selected |
|--------|-------------|----------|
| OCRDialog 内の非モーダル注記（推奨） | 進捗ラベル/結果ヘッダ部へ WARNING 色で 1 回表示・実行は止めない・結果テキストへ混入させない | ✓ |
| モーダル警告（messagebox） | 確実だがフロー中断 | |
| 結果テキストへ注記行挿入 | エクスポートに残り raw 維持方針と衝突 | |

### Q2: 言語パック検出のタイミング

| Option | Description | Selected |
|--------|-------------|----------|
| プロバイダ生成時に再検出（推奨） | build_provider の都度 tesseract --list-langs。言語パック追加が再起動なしで反映 | ✓ |
| import 時固定のまま | 現状維持・L-4 指摘の半分が残る | |
| お任せ（planner 判断） | 実装コストで決定 | |

### Q3: 指定言語が利用不可の場合のフォールバック先

| Option | Description | Selected |
|--------|-------------|----------|
| 現行の自動決定へ落とす（推奨） | 段階的縮退：利用可能な部分集合→全滅なら jpn 有→jpn+eng / なし→eng | ✓ |
| eng 固定に縮退 | jpn 利用可能でも eng に落ちるケースが生じうる | |
| エラーで中止 | 成功基準の「自動フォールバック」と矛盾 | |

---

## L-2/L-3 プラグイン registry ポリシー

### Q1: 重複名登録のポリシー

| Option | Description | Selected |
|--------|-------------|----------|
| 組込名は拒否・プラグイン同士は後勝ち（推奨） | 組み込み名衝突は logger.warning + 拒否、プラグイン同士は logger.warning + 上書き | ✓ |
| すべて警告付き拒否（先勝ち） | リロードで再登録できないケースに注意が必要 | |
| すべて警告付き上書き（後勝ち） | 組み込み機能の上書きリスク | |

### Q2: 選択中プロバイダのプラグイン unload 時の挙動

| Option | Description | Selected |
|--------|-------------|----------|
| 登録解除のみ（推奨） | settings は触らない。次回実行時に既存の未知名エラー経路で明示エラー | ✓ |
| 選択中なら off へ戻して通知 | 丁寧だが unload が settings 書き換えの副作用を持つ | |

### Q3: 公開アクセサの形

| Option | Description | Selected |
|--------|-------------|----------|
| get + list の 2 メソッド（推奨） | get_ocr_provider(name) -> cls \| None と list_ocr_providers() -> list[str]。私有アクセス 2 箇所を置換 | ✓ |
| お任せ（planner 判断） | 「私有アクセス全廃」のみ固定要件 | |

---

## L-6 活き残りの確定範囲

### Q1: 「等」の裁量範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 明記項目のみ・新発見は Phase 4 へ（推奨） | REVIEW.md の L-6 明記項目だけを Phase 2 対象。新発見は V171-TEST-03 棚卸しへ | ✓ |
| 同種軽微事項は裁量追加可 | 二度手間は減るがプラン規模が読みにくい | |

### Q2: 照合結果の記録先

| Option | Description | Selected |
|--------|-------------|----------|
| RESEARCH.md + 元 REVIEW.md へ ✅（推奨） | RESEARCH.md に活き残り表・解消時に 260610-aaa-REVIEW.md へ ✅ + コミットハッシュ追記 | ✓ |
| RESEARCH.md のみ | 元文書の ✅ 追記慣行を終了 | |

### Q3: URL スキーム検証の適用範囲

| Option | Description | Selected |
|--------|-------------|----------|
| URL 入力を持つ全プロバイダに統一適用（推奨） | LM Studio / Ollama / RunPod へ共通ヘルパー。同一項目の適用先拡張 | ✓ |
| LM Studio のみ（指摘どおり最小） | Ollama/RunPod は Phase 4 棚卸しへ | |

---

## Claude's Discretion

- `ocr_pipeline.py` の API 形状（コールバック境界・関数 vs クラス・引数設計）と dialog 側の描画配線詳細
- Tesseract 言語再検出のキャッシュ戦略と `list_models` との整合
- `_fetch_models` / `_test_connection` 重複解消の共通化形
- フォールバック注記の文言詳細と既存 `tesseract_lang_fallback` キーの再利用/新設判断

## Deferred Ideas

- 照合中に見つかる L-6 リスト外の軽微事項 → Phase 4（V171-TEST-03）へ
- サマリ経路（`_summary_worker`）の共通基盤化 → 将来の OCR 基盤再訪時の候補
