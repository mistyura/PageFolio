---
phase: 2
reviewers: [antigravity]
reviewed_at: 2026-07-14T10:50:07Z
plans_reviewed: [02-01-PLAN.md, 02-02-PLAN.md, 02-03-PLAN.md, 02-04-PLAN.md]
---

# Cross-AI Plan Review — Phase 2

## Antigravity Review

# Plan Review: Phase 2 — AI強化（プロンプト・テンプレート管理 + プロバイダーフォールバック）

## 1. Summary (要約)
本計画（Plan 02-01 〜 02-04）は、PageFolio のプロンプト・テンプレート管理とプロバイダーフォールバック機能を、既存の設計思想に則って極めて論理的かつ安全に実装するためのロードマップを提示しています。`settings.py` における永続化データ構造の定義、純ロジック層（`ocr_fallback.py`）の完全な分離によるテスト容易性の確保、既存の `MergeOrderDialog` や `ShortcutsDialog` の UI パターンの再利用は、開発効率と堅牢性を両立させる優れたアプローチです。
しかし、本フェーズの最大難所であるフォールバック実行時（`OCRDialog` 内のオーケストレーション）において、ダイアログローカルな設定スナップショット（`self._active_ocr_settings`）を導入しているにもかかわらず、`_on_run` や `_on_summary` の内部で依然としてグローバルな `self.app.settings` からプロバイダ設定やモデル等を再構築しようとしてしまう設計不整合が存在します。この参照漏れを解消するための完全な引数一般化が必要です。

---

## 2. Strengths (強み)
* **グローバル設定汚染の構造的防止 (Pitfall 4 回避)**
  フォールバック中の一時的なプロバイダ切替が次回起動時に永続化されないよう、`self.app.settings` は汚染させず、コピーされたローカル辞書 `self._active_ocr_settings` 上でのみ処理を進める設計方針（`pagefolio/ocr_dialog.py` 拡張）が非常に堅牢です。
* **既存アセットの賢明な再利用**
  `pagefolio/dialogs/shortcuts.py` の重複拒否による保存エラー検証（D-04）や、`pagefolio/dialogs/merge.py` の `tk.Listbox` + 上下ボタンによる並び替え UI（D-13）など、既に動作検証済みのコンポーネント構成をそのまま流用することで、車輪の再発明とバグ混入リスクを低減しています。
* **純粋な優先順位解決メカニズムの維持**
  `pagefolio/ocr.py` の `resolve_ocr_prompt`/`resolve_summary_prompt` の既存の 3 段解決（custom > provider別 > 汎用）のシグネチャを改変せず、`load_custom_prompt`/`load_summary_prompt` の戻り値である `custom_prompt` 自体の解決ロジックをテンプレート層を含む 3 段に細分化するアプローチ（Pattern 4）は、下流テストの破損を防ぎます。
* **テストファーストな依存関係管理 (Wave 0 Gaps 解消)**
  UI に依存しない純ロジック部分（テンプレート CRUD や次候補選択関数）を `tests/test_prompt_templates.py` や `tests/test_ocr_fallback.py` で先に検証するスケジュールを組んでおり、確実な段階的ビルドが期待できます。

---

## 3. Concerns (懸念事項)

### 【HIGH】`_on_run` 再開時における `self.app.settings` の参照残りによるフォールバック先のリセット
`pagefolio/ocr_dialog.py` の `_on_run` メソッド（ocr_dialog.py:1362-1473）では、実行開始時にプロバイダを再構築するために以下のように `self.app.settings` を直接参照しています。
```python
name = self.app.settings.get("ocr_provider", "")
...
self.provider = build_provider(self.app.settings, api_key=api_key, ...)
```
フォールバック提案が承認され、`_switch_to_fallback_provider` 内で `_active_ocr_settings` にフォールバック先を反映したスナップショット `fb` を作成し、`_on_run(resume=True, settings=fb)` を呼び出したとしても、`_on_run` 内の上記ブロックで `self.app.settings` から元のエラーを起こしたプロバイダを読み込み直して `self.provider` を上書きしてしまいます。これではフォールバックが機能せず元のプロバイダで再実行されてしまいます。

### 【MEDIUM】`_on_summary_error` からのサマリ再開オーケストレーションの記述不足
[D-12] により、サマリ生成の失敗時にも同じフォールバック順を適用するとされています。しかし、OCR 実行時とは異なり、サマリ生成は `_on_summary`（ocr_dialog.py:1947）によってトリガーされます。`_on_summary` は現在引数を受け取らないシグネチャであり、フォールバック切替後に `settings=fb` スナップショットを引き継いで再試行する際のオーケストレーションフロー（サマリ専用の `_on_summary` の一般化など）について、計画内での設計言及が不十分です。

### 【LOW】Tesseract 未インストール環境におけるフォールバック順の例外処理漏れ
[D-14] にて、フォールバック順には API キー未設定のプロバイダも含めるため `tesseract` も候補になりますが、ユーザー環境に Tesseract 自体がインストールされていないケースが想定されます。`llm_config/dialog.py:63` などで `_tesseract_available` が判定されていますが、フォールバックチェーンで `tesseract` が選択された際、`build_provider` 呼び出しや実行時に発生する `RuntimeError` が静かに握りつぶされず、適切に次のフォールバック候補に遷移できるかどうかの検証経路の確認が必要です。

---

## 4. Suggestions (提案事項)
* **`_on_run` 内部の `self.app.settings` 参照の完全な引数（`s`）置き換え**
  `_on_run` 内のプロバイダ選択や `build_provider` の引数解決において、以下のようにローカル変数 `s` を介してパラメータを取得するように Plan 02-04 に明示的なタスク指示を追加してください。
  ```python
  s = settings if settings is not None else self.app.settings
  name = s.get("ocr_provider", "")
  # build_provider 等の呼び出しも s を渡す
  self.provider = build_provider(s, api_key=api_key, ...)
  ```
* **サマリ実行関数 `_on_summary` のシグネチャ拡張**
  `_on_summary` メソッドも `_on_run` と同様に `_on_summary(self, settings=None)` のように拡張し、フォールバックからの再開時には `fb` スナップショットを受け取ってサマリワーカー（`_summary_worker`）に渡せるように計画を更新してください。
* **`_check_cloud_api_key` の API キー解決以外の検証拡張**
  ローカルプロバイダ（特に Tesseract）へのフォールバック時にも、インストール状態の事前チェックが行えるよう、必要に応じて `_check_cloud_api_key` の役割を `_validate_provider_readiness` 等に一般化して例外発生を防ぐことを推奨します。

---

## 5. Risk Assessment (リスク評価)
* **リスクレベル: MEDIUM**
* **理由:**
  UI や純関数の分離、設定スキーマの設計自体は非常に低リスクですが、`self.app.settings` のグローバル参照が `ocr_dialog.py` 内に散見されるため、計画通りの「設定汚染のないローカルスナップショットによるフォールバック」を完遂するには、`_on_run` や `_on_summary` の引数解決の徹底が欠かせません。この参照修正漏れがある場合、フォールバックが全く機能しなくなるバグとなるため、中程度のリスクと判定します。Suggestions に従い `_on_run` の内部参照の置き換えを明文化すれば、リスクは **LOW** に低減されます。

---

## Consensus Summary

単一レビュアー（Antigravity）のため、複数レビュアー間の合意形成は該当なし。Antigravity の所見を要約する。

### Agreed Strengths
- Pitfall 4（settings 汚染）のローカルスナップショット方式による構造的回避
- 既存 UI パターン（MergeOrderDialog / ShortcutsDialog）の再利用によるリスク低減
- `resolve_ocr_prompt`/`resolve_summary_prompt` のシグネチャ不変を保ったテンプレート層挿入
- Wave 0 テスト先行作成による段階的ビルド

### Agreed Concerns
- 【HIGH】`_on_run` 内の `self.app.settings` 直接参照が残ると、フォールバック承認後も元プロバイダで再実行されてしまい機能自体が無効化される（Plan 02-04 に `settings` 引数一般化の明示的タスク指示が必要）
- 【MEDIUM】サマリ経路（`_on_summary`/`_summary_worker`）のフォールバック再開時の設定スナップショット引き継ぎ設計が計画内で不十分
- 【LOW】Tesseract 未インストール環境でフォールバック候補に tesseract が選ばれた場合の例外遷移経路が未検証

### Divergent Views
該当なし（単一レビュアー）。
