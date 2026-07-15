# Phase 5: 堅牢性強化（サムネイル仮想化 + Blobリーク検出 + ShortcutsDialog修正） - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-16
**Phase:** 05-堅牢性強化（サムネイル仮想化 + Blobリーク検出 + ShortcutsDialog修正）
**Areas discussed:** 仮想化の実体化方式, thumb_cache LRU 設計, WR-02 単キー衝突の解消方針, Blob リーク検出の仕組み

---

## 仮想化の実体化方式

### Q1: 「可視範囲のみ実体化」の実現方式

| Option | Description | Selected |
|--------|-------------|----------|
| 画像遅延レンダリング型（推奨） | ウィジェットは窓内全生成のまま、get_pixmap のみ可視範囲優先・窓外はスクロールで見えた時にレンダリング。構造変更最小・落とし穴2を構造的に回避 | ✓ |
| ウィジェット再利用型 | 可視行のみウィジェット実体化しスクロールでリサイクル。最大限の軽量化だがキー不整合リスク・PERF-F01（v2送り）との境界が曖昧に | |
| Claude に任せる | 計画・リサーチ段階で選択させる | |

**User's choice:** 画像遅延レンダリング型（推奨）

### Q2: スクロール中のレンダリングタイミング

| Option | Description | Selected |
|--------|-------------|----------|
| デバウンス型（推奨） | スクロール停止後（例: 150ms 無操作）に可視範囲をレンダリング。キャッシュヒット分は即時表示 | ✓ |
| 逐次型 | スクロールイベントのたびに即キュー投入。高速スクロールで無駄なレンダリングが発生 | |
| Claude に任せる | 実装時にプロファイリングして選択 | |

**User's choice:** デバウンス型（推奨）

### Q3: アイドル時間の先読みレンダリング

| Option | Description | Selected |
|--------|-------------|----------|
| 先読みあり（推奨） | 可視範囲 → 窓内残りの順で低優先レンダリングを継続。総仕事量は現行と同じで体感改善 | ✓ |
| 可視範囲のみ厳格 | 見えていない分は一切レンダリングしない。CPU最小だがプレースホルダ頻度が上がる | |
| Claude に任せる | 実装時の複雑さを見て判断 | |

**User's choice:** 先読みあり（推奨）

### Q4: PERF-03 回帰テストの水準

| Option | Description | Selected |
|--------|-------------|----------|
| プロパティ風テスト＋ユニット（推奨） | seed 固定 random.Random のランダム操作列で 500+ページ相当の不変条件検証。新規依存なし | ✓ |
| ユニットテストのみ | 純関数と主要シナリオの従来型テストに絞る。検出力は落ちる | |
| Claude に任せる | 計画時にテスト容易性を見て決定 | |

**User's choice:** プロパティ風テスト＋ユニット（推奨）

---

## thumb_cache LRU 設計

### Q1: LRU 上限の単位

| Option | Description | Selected |
|--------|-------------|----------|
| 枚数固定（推奨） | 定数で上限枚数（例: 最大窓100の3倍=300枚）。シンプル・テスト容易 | ✓ |
| メモリ量換算 | 概算バイト合計で上限管理。ズーム率に依らずメモリ一定だが実装が複雑 | |
| Claude に任せる | 計画時に決定 | |

**User's choice:** 枚数固定（推奨）

### Q2: 上限値のユーザー設定公開

| Option | Description | Selected |
|--------|-------------|----------|
| 定数のみ（推奨） | コード内定数。設定画面に出さない（Phase 6 UI監査対象を増やさない） | ✓ |
| 設定公開 | settings.json + SettingsDialog に項目追加 | |

**User's choice:** 定数のみ（推奨）

### Q3: エビクションのタイミング

| Option | Description | Selected |
|--------|-------------|----------|
| 純粋 LRU（推奨） | 容量到達時に最古参照分だけ自然に押し出す。窓の行き来で即表示 | ✓ |
| 窓移動時に積極パージ | 窓移動のたびに窓外を即エビクト。メモリ最小だがキャッシュの意義が薄れる | |
| Claude に任せる | 計画時に決定 | |

**User's choice:** 純粋 LRU（推奨）

### Q4: LRU 実装の配置

| Option | Description | Selected |
|--------|-------------|----------|
| 純ロジック層に新設（推奨） | Tk 非依存の汎用 LRU コンテナを新規モジュールまたは pagination.py に追加。既存呼び出し面は維持 | ✓ |
| viewer.py 内で完結 | ViewerMixin に直接実装。ファイル追加なしだが Tk 依存のまま | |
| Claude に任せる | 計画時に決定 | |

**User's choice:** 純ロジック層に新設（推奨）

---

## WR-02 単キー衝突の解消方針

### Q1: 解消アプローチ

| Option | Description | Selected |
|--------|-------------|----------|
| フォーカスガード（推奨） | 発火時にフォーカス中ウィジェットを判定し、入力系フォーカス中は修飾なし単キーの発火を抑止。既定 <Delete>/<F5> の既存衝突も根治 | ✓ |
| キャプチャ時拒否 | 修飾なし文字キーの登録をエラーに。既定 <Delete> の既存衝突は残る | |
| 両方（多層防御） | ガード＋登録制限。最も堅牢だが実装・テスト面積最大 | |

**User's choice:** フォーカスガード（推奨）

### Q2: ガード対象キーの範囲

| Option | Description | Selected |
|--------|-------------|----------|
| Ctrl/Alt なし全部（推奨） | 修飾なし単キー＋Shift のみの組合せを抑止（Shift+文字は大文字入力そのもの）。Ctrl/Alt 系は入力中も有効 | ✓ |
| 修飾完全なしのみ | 修飾キーゼロの単キーだけ抑止。Shift+文字の衝突リスクが残る | |
| Claude に任せる | 実装時に決定 | |

**User's choice:** Ctrl/Alt なし全部（推奨）

### 補足: WR-01（表示残留）

成功基準で挙動確定済み（切替時に前行表示を元へ復元）のため質問せず、修正実装は Claude の裁量とした。

---

## Blob リーク検出の仕組み

### Q1: 検出機構の水準

| Option | Description | Selected |
|--------|-------------|----------|
| __del__+released フラグ（推奨） | _released フラグ追加で リーク／double-release 両検出。weakref レジストリなしの軽量案。終了時誤検知抑止に配慮 | ✓ |
| weakref 追跡セット併用 | 生存 Blob の集計 API も追加する CONCERNS 推奨フル実装。__slots__ 変更とレジストリ管理が増える | |
| __del__ ロギングのみ | リーク検出のみの最小実装。double-release は検出しない | |

**User's choice:** __del__+released フラグ（推奨）

### Q2: リーク検出時の振る舞い

| Option | Description | Selected |
|--------|-------------|----------|
| 警告ログ＋回収（推奨） | logger.warning で記録しつつ __del__ 内で unlink もベストエフォート試行 | ✓ |
| 警告ログのみ | 回収は purge/atexit に完全に委ねる | |
| Claude に任せる | 実装時に決定 | |

**User's choice:** 警告ログ＋回収（推奨）

### Q3: ロギングの有効化

| Option | Description | Selected |
|--------|-------------|----------|
| 常時有効（推奨） | logger.warning で常時出力。長時間運用での検出という ROBUST-01 の目的に合致 | ✓ |
| デバッグ限定 | 環境変数や DEBUG レベルでのみ有効。実ユーザー環境での発見機会を失う | |

**User's choice:** 常時有効（推奨）

### Q4: AV 衝突回帰テストの範囲

| Option | Description | Selected |
|--------|-------------|----------|
| CONCERNS フルカバー（推奨） | ①unlink PermissionError mock ②insert→undo→redo→undo の double-release スパイ ③test_undo_stress.py 連動の一時ディレクトリ残留監視 | ✓ |
| 最小（unlink 衝突のみ） | 要件文言の最低限のみ検証 | |
| Claude に任せる | 計画時に決定 | |

**User's choice:** CONCERNS フルカバー（推奨）

---

## Claude's Discretion

- WR-01 の具体的な修正実装（`_start_capture` で旧行を `_refresh_row`）
- デバウンス待機時間の具体値（150ms は例示）
- LRU 上限の具体値（300 枚は例示・最大窓サイズ超が必須条件）
- LRU コンテナの配置先（新規モジュール vs pagination.py）と API 設計
- フォーカスガードの入力系ウィジェット判定方法とガード純関数の配置
- `__del__` 終了時誤検知抑止の具体的実装
- 可視範囲判定の実装方法（スクロールオフセット計算は pagination.py の純関数として追加）

## Deferred Ideas

なし — 議論はフェーズスコープ内に収まった（PERF-F01＝連続スクロール型本格仮想化の v2 送りは維持）
