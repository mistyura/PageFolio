# M004-nh4gku: v1.7.5 — GSD-PI 同期・課題洗い出し・小粒修正

**Gathered:** 2026-07-13
**Status:** Ready for planning

## Project Description

GSD-Core（`.planning/quick`）のクイックタスクで出荷した v1.7.2〜v1.7.4 の内容を GSD-PI（`.gsd/`）の記録へ反映して履歴を一元化し、そのうえで課題の洗い出し（既知残課題の棚卸し・コード監査・ドキュメント整合監査）を行う。洗い出した課題のうち小粒なものは M004 内で修正し、3 回見送られてきた人手 UAT（実機目視）を正式実施したうえで v1.7.5 として出荷する。

## Why This Milestone

実装は v1.7.4（テスト 880 件グリーン）まで進んでいるが、GSD 側の記録（PROJECT.md・CONTEXT.md 等）は v1.7.1 止まりで 3 リリース分先行している。記録と実態のズレを解消しないと、次マイルストーンの計画が誤った前提（テスト 859 件・v1.7.1 のモジュール構成）に立ってしまう。あわせて、v1.7.1 出荷時から積み残している既知課題（ShortcutsDialog WR-01/02・開発履歴.md v1.7.0 表記整合・人手 UAT 未実施）を放置せず、監査で新規課題も洗い出して品質の現在地を確定させる。

## User-Visible Outcome

### When this milestone is complete, the user can:

- `.gsd/PROJECT.md` 等を読むだけで v1.7.4 までの全履歴（quick 出荷分含む）を正確に把握できる
- 優先度付きの課題リスト（既知＋監査で新規発見）を見て次マイルストーンのスコープを判断できる
- 小粒修正と UAT 実機目視確認を経た v1.7.5 リリース（zip + sha256）を利用できる

### Entry point / environment

- Entry point: `python pagefolio.py`（開発）/ PyInstaller onedir ビルド（配布）
- Environment: Windows 11 ローカル・Tkinter デスクトップアプリ
- Live dependencies involved: なし（OCR クラウド API は UAT の目視確認項目に含まれうるが、新規統合はない）

## Completion Class

- Contract complete means: `.gsd/` 記録が v1.7.4 実態と一致（grep/目視で検証可能）・課題リストが成果物として存在・小粒修正が pytest/ruff で担保
- Integration complete means: 修正後のフルテストスイートがグリーン・ドキュメント（README/CLAUDE.md/docs/）と実コードの乖離ゼロを監査で確認
- Operational complete means: 人手 UAT チェックリストの実機目視を実施し pass/fail を記録・v1.7.5 リリース成果物（zip + sha256）を作成

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- `.gsd/PROJECT.md` を含む GSD-PI 記録に v1.7.2〜v1.7.4 のポイントリリースが反映され、`.planning/quick` の計画書・サマリが `.gsd/` 側構造へ移植されている
- 課題リスト（棚卸し＋監査新規発見＋ドキュメント乖離）が優先度・粒度（M004 修正 / 繰り越し）付きで存在する
- 小粒修正込みで `pytest` 全件グリーン・`ruff check` クリーン・`APP_VERSION = v1.7.5` に同期（README バッジ・開発履歴.md も同期）
- 人手 UAT はユーザー本人の実機目視が必要であり、シミュレーション不可（Xvfb スモークでは代替しない）

## Architectural Decisions

### quick 記録の移植も含めた GSD-PI 同期

**Decision:** `.gsd/` の状態記録更新に加え、`.planning/quick` の v1.7.2〜v1.7.4 計画書・サマリを GSD-PI 側の構造へ取り込み直す。

**Rationale:** 履歴を GSD-PI に一元化し、今後の計画・監査が単一の記録系を参照できるようにする（ユーザー明示選択）。

**Alternatives Considered:**
- 記録の更新のみ（PROJECT.md 等の状態同期に留める） — 作業は軽いが履歴が `.planning` と `.gsd` に分散したまま残るため不採用

### 課題の洗い出しは 3 軸すべて実施

**Decision:** (1) 既知残課題の棚卸し、(2) コード監査による新規発見（コードレビュー/最適化監査・PERF-01 サムネイル仮想化の要否判断含む）、(3) ドキュメント整合監査（README/CLAUDE.md/docs/ と実コードの乖離）をすべて行う。

**Rationale:** 品質の現在地を一度に確定させ、次マイルストーンの計画精度を上げる（ユーザー明示選択）。

**Alternatives Considered:**
- 既知残課題のみ — 新規の潜在課題を見落とすため不採用

### 小粒修正は M004 内で実施・出荷、大粒は繰り越し

**Decision:** 洗い出した課題のうち小粒なもの（ShortcutsDialog WR-01/02・開発履歴.md v1.7.0 表記整合・監査で見つかる軽微バグ/乖離）は M004 内で修正し v1.7.5 として出荷。大粒（PERF-01 サムネイル仮想化等の設計を伴うもの）は優先度を付けて次マイルストーンへ繰り越す。

**Rationale:** 小粒を溜め込まず出荷サイクルを回しつつ、監査結果に引きずられてマイルストーンが肥大化するのを防ぐ。

**Alternatives Considered:**
- 洗い出しのみ（修正は全て次へ） — 既知の小粒課題を 3 マイルストーン連続で持ち越すことになるため不採用

### 出荷バージョンは v1.7.5（パッチ）

**Decision:** `APP_VERSION = v1.7.5` でパッチバンプ。

**Rationale:** 小粒修正・ドキュメント整合中心のためパッチが自然（ユーザー確認済み）。

**Alternatives Considered:**
- v1.8.0 — UAT 正式実施を区切りとするマイナーバンプ案。機能追加がないため不採用

### 人手 UAT は M004 内で正式実施

**Decision:** v1.4.0 / v1.6.0 / v1.7.1 で計 3 回「一旦 pass」としてきた実機目視 UAT を、チェックリスト整備のうえユーザー参加セッションとして M004 内で実施する。

**Rationale:** コード/自動ゲートは全通過済みだが、実描画（透かしの半透明・Markdown 整形・実 API 出力品質など）は目視でしか検証できず、3 回の先送りで deferred リスクが累積している。

**Alternatives Considered:**
- チェックリスト作成のみ（実施は別途） — 4 回目の先送りになるため不採用

## Error Handling Strategy

既存方針を踏襲する。修正はユーザー可視の失敗を `messagebox.showerror` へ、裸の `except:` 禁止（`except Exception as e:`）、例外の握りつぶしには最低限 logger 呼び出し。監査・同期作業自体はドキュメント/記録操作が中心のため、検証は grep・pytest・ruff・実機目視で行い、失敗時はその場で修正して再検証する。UAT で fail が出た項目は課題リストへ記録し、小粒なら M004 内で修正、大粒なら繰り越し判断を行う。

## Risks and Unknowns

- 監査で見つかる課題の量・粒度が未知 — 小粒/大粒の線引きを誤ると M004 が肥大化する。スライス計画時に「修正はタイムボックス内・設計を伴うものは即繰り越し」の規律を明文化する
- quick 記録の移植先の具体形（`.gsd/` 内のどの構造に収めるか）が未確定 — GSD-PI のアーティファクト規約（phases/ 構造・summary frontmatter）に合わせる必要があり、計画フェーズで移植形式を確定する
- 人手 UAT はユーザーの実機・時間を要する — セッションが取れない場合に M004 完了がブロックされる。チェックリスト整備を先行スライスにし、実施を終盤スライスに置く
- `.gsd/` 直下に未整理の作業ツリー変更（STATE.md/gsd.db 削除・CONTEXT.md/PREFERENCES.md 新規）が存在 — 移行途中の状態を壊さないよう、同期作業前に現状を確認してから着手する

## Existing Codebase / Prior Art

- `.gsd/PROJECT.md` — v1.7.1 止まりの現況記録。同期の主対象（Current State・Next Milestone Goals・テスト件数 859→880 等）
- `.planning/quick/` — v1.7.2〜v1.7.4 のクイックタスク計画書・サマリ。移植元
- `.planning/MILESTONES.md` — ポイントリリースの記録慣行の参照元
- `開発履歴.md` — v1.7.2/v1.7.3/v1.7.4 エントリが実装内容の一次情報。v1.7.0 表記整合（V16-D-04 残課題）の修正対象でもある
- `pagefolio/constants.py` — `APP_VERSION = "v1.7.4"`（真の情報源）。出荷時に v1.7.5 へバンプ
- `.planning/phases/`（v1.7.1）の `04-REVIEW.md` — ShortcutsDialog WR-01/02 の詳細（キャプチャ対象切替時の前行表示残留・修飾キーなし単キー登録の入力衝突）
- `pagefolio/dialogs/shortcuts.py` — WR-01/02 の修正対象
- `CLAUDE.md` / `README.md` / `docs/` — v1.7.4 quick で一部同期済みだが全面整合監査の対象

## Relevant Requirements

- PERF-01（サムネイル仮想化・Future Requirements 継続） — 本マイルストーンでは実装せず、コード監査で要否・優先度を判断して繰り越し先を確定する
- V16-D-04 残課題（開発履歴.md の v1.7.0 表記整合） — 本マイルストーンで解消
- V171 残課題（ShortcutsDialog WR-01/02・人手 UAT 未実施） — 本マイルストーンで解消

## Scope

### In Scope

- `.gsd/` 記録の v1.7.4 実態への同期（PROJECT.md・CONTEXT.md・CODEBASE.md 等）
- `.planning/quick` の v1.7.2〜v1.7.4 記録の GSD-PI 構造への移植
- 既知残課題の棚卸し（WR-01/02・版番整合・UAT 未実施ほか）
- コード監査（バグ・負債・性能。PERF-01 要否判断含む）
- ドキュメント整合監査（README/CLAUDE.md/docs/ と実コードの乖離）
- 優先度・粒度付き課題リストの作成
- 小粒課題の修正（WR-01/02・開発履歴.md v1.7.0 表記整合・監査発見の軽微修正）
- 人手 UAT チェックリスト整備と実機目視セッションの実施
- v1.7.5 出荷（APP_VERSION/README/開発履歴.md 同期・onedir ビルド・zip + sha256）

### Out of Scope / Non-Goals

- PERF-01 サムネイル仮想化の実装（要否判断のみ・実装は次マイルストーン）
- 設計変更を伴う大粒修正（監査で発見しても繰り越し）
- 新機能の追加
- OS キーストア連携・OAuth・検索可能 PDF 化・プラグイン API バージョン管理（従来から Out of Scope 継続）

## Technical Constraints

- Python 3.8+ 互換・Tkinter・pymupdf・依存追加なし（V14-D-01 踏襲）
- API キーの settings.json 非永続（`_SENSITIVE_KEYS` ガード）維持
- LANG キーは ja/en 同一キーでパリティ維持
- 修正はすべて `ruff check . && ruff format .` と `pytest` 全件グリーンを通す
- `.gsd/` の checkbox 操作は gsd_* ツール経由（手動トグル禁止）
- リリース成果物は `PageFolio-<tag>-win64.zip` + `.sha256`・dist/PageFolio はリビルド毎にコミット（既存リリース流儀）

## Integration Points

- GitHub Releases — v1.7.5 タグ・リリース作成（immutable releases 有効・アセットは作成時同梱・タグ衝突時は -N サフィックス）
- GSD-PI（`.gsd/` + gsd.db） — 記録同期・quick 移植の書き込み先
- なし（外部 API への新規統合はない。UAT 目視で既存クラウド OCR を触る可能性はある）

## Testing Requirements

- 既存フルスイート（880 件）を修正後も全件グリーンに維持
- WR-01/02 修正には可能な範囲で回帰テストを追加（Tk ヘッドレスで検証可能なロジック部分）
- ドキュメント整合監査は「ドキュメント記載のコマンド・パス・モジュール構成が実在する」ことを実地確認
- 人手 UAT はチェックリスト項目ごとに pass/fail を記録（自動化しない・実機目視が本質）

## Acceptance Criteria

- 同期スライス: `.gsd/PROJECT.md` に v1.7.2〜v1.7.4 が反映され「テスト 880 件・APP_VERSION v1.7.4（作業時点）」等の実態値と一致・quick 記録が `.gsd/` 側へ移植済み
- 棚卸し/監査スライス: 優先度・粒度（M004 修正 / 繰り越し）付き課題リストが成果物として存在
- 修正スライス: WR-01/02 解消・開発履歴.md v1.7.0 表記整合完了・監査発見の小粒修正完了・pytest/ruff グリーン
- UAT スライス: チェックリストを実機目視で消化し結果を記録
- 出荷スライス: `APP_VERSION = v1.7.5`・README バッジ・開発履歴.md 同期・リリース成果物作成

## Open Questions

- quick 記録の移植形式（`.gsd/phases/` 配下の遡及フェーズとするか、独立の履歴アーティファクトとするか） — 計画フェーズで GSD-PI の規約に合わせて確定する
- 監査で PERF-01 相当の性能問題が「小粒修正で緩和可能」と判明した場合の扱い — 緩和のみ M004・本対応は繰り越し、が現時点の想定
