# Phase 6: 品質保証仕上げ（通知UX・UI一貫性監査・ドキュメント整合） - Context

**Gathered:** 2026-07-16
**Status:** Ready for planning

<domain>
## Phase Boundary

v1.8.0 の最終仕上げフェーズ。①軽微エラー向けの再試行アクション付き非モーダルトースト通知（自動消滅なし・重大エラーの `messagebox` モーダルは維持）、②ダイアログ間のスクロールパターン・フォントスケーリングの監査と是正、③開発履歴.md の v1.7.0 表記整合（V16-D-04 残課題の解消）を行い、マイルストーンを締められる状態にする。

対象要件: V180-QA-02（再試行付き非モーダルトースト）・V180-QA-03（スクロールパターン統一・フォントスケーリング監査）・V180-QA-04（開発履歴.md 表記整合）。

追加折り込み（ユーザー確定・要件外だが Core Value 直撃バグのため本フェーズで解消）: `pagefolio/file_ops.py` の insert→undo→redo→undo ページ重複バグ修正（Phase 5 の deferred item・D-16 参照）。

**スコープ外:** 全エラーの非モーダル化（アンチフィーチャー確定・`.planning/research/FEATURES.md`）・成功通知/情報通知へのトースト転用・スクロール共通ヘルパーの新設・フォントの `_font` ヘルパーへの全面一本化・旧 PDF Editor 時代エントリの改変・OS ネイティブ通知（Windows トースト API）連携。

</domain>

<decisions>
## Implementation Decisions

### トースト対象エラーの線引き（QA-02）
- **D-01:** トースト化の選定基準は「**再試行ボタンが意味を持つ操作**」（一時要因で失敗しうる操作）に限定する。全 messagebox（約80箇所）の網羅置換はしない。入力バリデーション系エラー（トリミング範囲過小・テンプレート名重複等）と致命的エラーは従来どおり `messagebox` モーダルを維持する。
- **D-02:** 初回対象セットは**保存系＋印刷の 4 操作**: 上書き保存（`_save_file`）・別名保存（`_save_as`）・縮小保存（`_save_compressed`）・印刷（`_print_pdf`/`_send_to_printer`）の失敗。すべてメインウィンドウ発の操作であり、AV ロック・共有違反等の一時要因で再試行が最も有効な領域。モデル一覧取得失敗は既にダイアログ内ラベル通知（非モーダル）があるため対象外。
- **D-03:** 再試行ボタンは**同一操作の単純再実行のみ**（ボタンは「再試行」1つ。保存失敗→同じパスへ再保存、印刷失敗→再送信）。「別名で保存」等の代替アクション併設はしない（FEATURES.md 最小実装ライン「アクションボタン1つ」と整合）。
- **D-04:** 再試行が再び失敗した場合は**同じトーストを最新エラー文言で更新して残す**（回数制限なし・モーダル昇格なし）。要件どおり自動消滅もしない。

### トーストの表示形態・挙動（QA-02）
- **D-05:** 実装方式は**メインウィンドウ内オーバーレイ**（`place()` でメインウィンドウ上に重ねる常駐 Frame）。`Toplevel + overrideredirect` は不採用（フォーカス・タスクバー・マルチモニタ・最小化追従の癖を回避）。テーマ `C` 辞書・`_font` ヘルパーをそのまま適用し、ウィンドウ移動/最小化に自然追従させる。
- **D-06:** 表示位置は**右下**（トーストの業界標準位置。左ペインサムネイル・右ツールパネルの操作導線と重ならない）。
- **D-07:** 同時表示は**1件のみ**（新しいエラーが出たら置換）。スタック管理・レイアウト再計算は実装しない。対象操作（保存/印刷）はユーザーの能動操作であり同時多発は実質起きない。
- **D-08:** トーストが消える条件は ①✕ボタン ②トースト経由の再試行成功 ③**別経路で同一操作が成功した場合**（例: トースト表示中にメニューから再保存して成功→トーストも消す）の3つ。古い失敗通知の残留による誤解を防ぐため、対象操作の成功パスに dismiss 呼び出しを追加する。
- **D-09:** トースト文言は既存規約どおり `LANG` 辞書（ja/en 両方・`test_lang_parity.py` の parity 対象）経由とし、色は `C` 辞書・フォントは `_font(delta)` を使う（CLAUDE.md 規約の踏襲・ハードコード禁止）。

### スクロールパターン/フォントスケーリング監査（QA-03）
- **D-10:** スクロールの統一基準は **v1.7.2 の llm_config パターン**（Canvas + Scrollbar + 高さクランプ + 下部ボタン固定 + マウスホイール対応）を正とする。監査対象はスクロール実装を持つ 8 ファイル（batch_ocr / llm_config dialog・sections / merge / plugin / ocr_dialog / ui_builder / viewer）で、不一致（ホイール未対応・クランプなし等）をこの基準に寄せる。
- **D-11:** 是正は**不一致箇所の個別是正のみ**。`make_scrollable_frame()` 等の共通ヘルパー新設・既存動作箇所の一斉移行はしない（回帰面を狭く保つ。「仕上げフェーズを軽く保つ」Phase 3〜5 の一貫方針）。
- **D-12:** フォント監査の是正範囲は**サイズ数値ハードコードのみ**（例: `about.py` の 16pt 固定）。`font_size` 設定（8〜16）に追従しない箇所だけを `_font(delta)` ベースへ修正する。`ui_builder.py` の `("Segoe UI", fs±n)` は fs 連動済みのため対象外、`settings.py` のフォントプレビューラベルは意図的固定のため対象外。
- **D-13:** 再発防止は**フォントのみ回帰テスト化**（フォントサイズ数値ハードコードを検出するソーススキャン型テスト。`test_source_keyguard.py`/`test_lang_parity.py` の grep 型前例踏襲・意図的固定箇所は allowlist 管理）。スクロールパターンは構造的にテスト化困難なため監査記録のみ。

### 開発履歴.md 整合（QA-04）
- **D-14:** 突合先は **git タグ履歴＋APP_VERSION 変更履歴＋`.planning/MILESTONES.md`**。PageFolio 時代の全エントリ（v1.3.0〜v1.7.4）について日付・版番・内容の不一致を検出して修正する。V16-D-04 の痕跡（v1.6.0 期の一時 v1.7.0 バンプ由来の表記）もこの過程で確実に特定する。事前調査では v1.6.0 見出し・実 v1.7.0（2026-07-03 ポイントリリース）エントリとも現在は正しい可能性が高く、「残不整合の特定」自体が作業の第一歩。
- **D-15:** 旧 PDF Editor 時代の同名バージョン見出し（v1.7.0/v1.6.0 が新旧 2 回出現）は**現状維持**。「PDF Editor 時代（リブランディング前）」セクションで区別済み・アンカー衝突なし・歴史的記録は改変しない。監査記録に「意図的な共存」と明記するのみ。
- **D-16:** 突合の結果、既に整合済みで修正不要だった場合は**監査記録（確認範囲・判定根拠）をフェーズ成果物に残して V180-QA-04 を完了扱い**とする。あわせて `PROJECT.md` Key Decisions の V16-D-04「⚠️ Revisit」ステータスを解消済みへ更新する。

### 折り込みバグ修正（Phase 5 持ち越し）
- **D-17:** `pagefolio/file_ops.py` の `_restore_state()` 内 `insert_redo` restore ブロックが原因の **insert→undo→redo→undo（2回目）でページが重複するバグ**を本フェーズで修正し、undo/redo 往復の回帰テストを追加する。再現コード・原因推定は `.planning/phases/05-blob-shortcutsdialog/deferred-items.md` に記録済み。delete/delete_redo の対称パターンに倣った修正が起点。

### Claude's Discretion
- トーストウィジェットの内部設計（クラス構成・配置モジュール。新規 `pagefolio/toast.py` か `ui_builder.py` 内かは計画時判断。既存の純ロジック層系譜に沿えるならテスト容易性を優先）
- トーストの視覚デザイン詳細（枠線・アイコン・✕ボタンの形状・幅の上限・長文エラーの折り返し/省略）
- 再試行コールバックの受け渡し方式（`functools.partial` / ラムダ / メソッド参照）と dismiss カテゴリのキー設計
- スクロール監査の具体的な不一致判定手順と是正の適用順序
- フォントハードコード検出テストの正規表現・allowlist の管理形式
- 開発履歴.md 突合の実施手順（git タグ一覧取得方法・監査記録の記載場所＝SUMMARY か独立ファイルか）
- insert_redo バグ修正の具体的なコード変更（deferred-items.md の原因推定を検証したうえで確定）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・フェーズ定義
- `.planning/REQUIREMENTS.md` — V180-QA-02/03/04 の要件文言（本フェーズの対象3要件）
- `.planning/ROADMAP.md` — Phase 6 の Goal・Success Criteria（成功基準3項目）・依存関係（Phase 5 完了後の最終仕上げ）

### リサーチ成果物
- `.planning/research/FEATURES.md` §エラー時リカバリー通知 — トーストの Table Stakes（非モーダル・アクション付きは自動消滅なし）と Anti-Features（全エラーの通知化は不採用）・最小実装ライン（軽微エラー向け1種・アクションボタン1つ）。D-01〜D-05 の直接の根拠

### 既知課題・持ち越し項目の出典
- `.planning/codebase/CONCERNS.md` — messagebox 全モーダルの現状（§Security 他）・スクロール/フォント関連の既知の目安
- `.planning/phases/05-blob-shortcutsdialog/deferred-items.md` — insert→undo→redo→undo ページ重複バグの再現コード・原因推定（D-17 の直接の出典。**必読**）
- `.planning/STATE.md` §Blockers/Concerns — 同バグの記録（05-03 発見・未修正）

### QA-04 の突合対象
- `開発履歴.md` — 監査・是正の対象ファイル（PageFolio 時代エントリ v1.3.0〜v1.7.4。旧 PDF Editor 時代セクションは現状維持）
- `.planning/MILESTONES.md` — 突合先（マイルストーン・ポイントリリースの正史）
- `.planning/PROJECT.md` §Key Decisions — V16-D-04「⚠️ Revisit」ステータス（D-16 で解消へ更新する対象）

### 規約
- `.planning/codebase/CONVENTIONS.md` — テーマ `C` 辞書・`_font(delta)` ヘルパー・`LANG` 辞書 i18n・messagebox エラーパターンの既存規約（トースト実装が従う規約面）

### 前例パターン（コード内）
- `pagefolio/dialogs/llm_config/dialog.py` — v1.7.2 の Canvas+Scrollbar+高さクランプ+下部ボタン固定パターン（D-10 の統一基準の実体）
- `pagefolio/app.py:473` — `_set_status`（既存の非モーダル表示前例・トーストと役割分担する）
- `pagefolio/file_ops.py` — `_save_file`/`_save_as`/`_save_compressed`（D-02 のトースト化対象）・`_restore_state` の `insert_redo` ブロック（D-17 の修正対象）
- `pagefolio/print_ops.py` — `_print_pdf`/`_send_to_printer`（D-02 のトースト化対象）
- `tests/test_source_keyguard.py`・`tests/test_lang_parity.py` — ソーススキャン型回帰テストの前例（D-13 のフォント検出テストが踏襲する形式）
- `pagefolio/dialogs/about.py:42` — フォント 16pt ハードコードの代表例（D-12 の是正対象）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_set_status`（`app.py:473`）: ヘッダーの非モーダルステータス表示。トーストとは別役割（操作完了の軽い通知）としてそのまま残す
- テーマ `C` 辞書・`_font(delta)`・`LANG` 辞書: トーストの色・フォント・文言にそのまま適用できる既存基盤
- `test_source_keyguard.py` の grep 型ソーススキャンパターン: フォントハードコード検出テスト（D-13）にそのまま流用できる
- v1.7.2 llm_config のスクロール実装: 統一基準（D-10）の参照実装として全是正箇所が倣う
- `deferred-items.md` の再現コード: insert_redo バグ（D-17）の回帰テストの土台にそのまま使える

### Established Patterns
- エラー表示は `messagebox.showerror(self._t("err_title"), ...)` + `LANG` キー: トースト化対象以外はこのパターンを維持。トースト文言も `LANG` 経由（D-09）
- 依存追加なし方針（V14-D-01）: トーストは Tkinter 自前実装（標準トーストは存在しない）
- 「過剰実装を避け小さく保つ」（Phase 3〜5 で一貫）: 1件表示・単一ボタン・個別是正の選択はすべてこの方針に沿う
- 純ロジック層集約の系譜（`pagination.py` 等）: トーストの状態管理を Tk 非依存にできる場合はテスト容易性を優先（Claude 判断）

### Integration Points
- `file_ops.py` の保存系 3 メソッドと `print_ops.py` の印刷系: showerror をトースト表示＋再試行コールバックへ置換し、成功パスに dismiss を追加（D-02/D-08）
- メインウィンドウ（`app.py`/`ui_builder.py`）: トーストオーバーレイの親。`_rebuild_ui()`（テーマ切替時の全ウィジェット破棄）でトーストが消えても再表示不要（エラー状態は破棄されて自然）だが、place の親子関係は再構築に耐える設計にする
- `_restore_state()`（`file_ops.py`）: insert_redo ブロックの修正点（D-17）。既存の undo 往復テスト群（`tests/test_pdf_ops.py`・`test_undo_stress.py`）と連動

</code_context>

<specifics>
## Specific Ideas

- 全領域で「推奨＝最小・低リスク」の選択肢が一貫して採用された: 少数精選のトースト対象（D-01/D-02）・単一ボタン（D-03）・1件表示（D-07）・個別是正（D-11）・現状維持（D-15）。仕上げフェーズを軽く保つ方針が明確
- 唯一のスコープ拡張はユーザーの明示判断による insert_redo バグの折り込み（D-17）。「Undo/Redo が正しく動作する」という Core Value 直撃のバグを抱えたまま v1.8.0 を出荷しないことを優先した
- トーストの消滅条件（D-08）は「古い失敗通知が残って誤解を招く」ことへの明確な問題意識から「同一操作の成功でも消す」を採用

</specifics>

<deferred>
## Deferred Ideas

- **成功/情報通知へのトースト転用** — 本フェーズはエラー通知のみ。将来トースト対象を広げる場合はスタック表示（D-07 で不採用）の再検討とセット
- **スクロールの共通ヘルパー化**（`make_scrollable_frame()` 等） — D-11 で不採用。将来スクロールダイアログがさらに増えた時点で再検討

</deferred>

---

*Phase: 6-品質保証仕上げ（通知UX・UI一貫性監査・ドキュメント整合）*
*Context gathered: 2026-07-16*
