# Feature Research — OCR プロバイダ化 + クラウドAPI対応

**ドメイン:** デスクトップ PDF エディタへのマルチプロバイダ OCR 機能追加（Python/Tkinter）
**調査日:** 2026-06-06
**信頼度:** HIGH（確定済み設計仕様書 `docs/OCRプロバイダ化_見積もり仕様.md` を正典とする）

---

## Feature Landscape

### Table Stakes（ユーザーが当然と思う機能）

Missing these = 機能が壊れていると感じる。

| 機能 | なぜ期待されるか | 複雑度 | 実装メモ |
|------|----------------|--------|---------|
| プロバイダ選択 UI（off / gemini / claude / lmstudio / tesseract） | 複数バックエンドを選択できなければ抽象化の意義がない | MEDIUM | `ocr_provider` 設定値を SettingsDialog のドロップダウンに追加。既定 `"off"` で外部送信を防ぐ。`ocr_dialog.py` のサーバ行は選択プロバイダに応じて条件表示 |
| 既定プロバイダ `"off"` — OCR ボタン非表示/disabled | クラウド課金・外部送信を望まないユーザー向けの安全な初期状態 | LOW | `ocr_provider == "off"` のときは `ui_builder.py` でボタンを disabled にする（`_doc_buttons` 管理外の独立フラグ） |
| APIキー未設定時の明示エラー | キーが無い状態でクラウドOCRを実行しようとしたとき、黙って失敗するのは許容されない | LOW | `os.environ.get("ANTHROPIC_API_KEY")` が `None` なら実行前に `messagebox.showerror`。入力欄は設けない（平文保存禁止） |
| APIキーは環境変数のみ・`settings.json` への書き込み禁止 | セキュリティ上の最低基準。キーが JSON に残ると認証情報漏洩リスク | LOW | `settings.py` のデフォルト値定義にキー項目を追加しない。`_save_settings()` でキー値が混入しないことをコードレビューで保証 |
| テキスト埋め込み判定による OCR スキップ (`page.get_text()`) | スキャン PDF でない場合に API/GPU コストをゼロにする。低スペック PC でも一瞬で完了 | LOW | `ocr_dialog.py` の `_worker` フェーズ1で `page.get_text().strip()` が非空ならその結果を即採用。API 呼び出しをスキップ。空のときのみ Vision API へ |
| ページ単位の逐次レンダリング→送信→破棄 | 現行の「全ページ画像を一括 `images` 辞書に保持」は低RAM PC で OOM を起こしうる | MEDIUM | `_worker` を2フェーズ（全画像一括生成→並列送信）から1フェーズ（render→send→discard を逐次ループ）に変更。fitz 同一 Document 並行アクセス回避はそのまま維持 |
| クラウド向け並列度抑制（デフォルト 1〜2）| 現行 `MAX_OCR_CONCURRENCY=8` のままだと 429 Rate Limit を頻発させる | LOW | `ocr_providers.py` 各 Provider クラスに `default_concurrency` 属性を持たせる。Gemini/Claude は `2`、LM Studio は既存の `DEFAULT_OCR_CONCURRENCY=2` を引き継ぎ `MAX_OCR_CONCURRENCY=8` まで許容 |
| 429/5xx リトライ（指数バックオフ） | クラウドAPIはレート制限が発生する。リトライなしだと途中ページが欠落する | MEDIUM | `call_provider` 内部で HTTP 429 / 500-503 を受けたらスリープ後リトライ（最大3回、1s/2s/4s）。429 の `Retry-After` ヘッダがあれば優先採用 |
| プロバイダ切替に伴うモデル一覧取得 | プロバイダを変えたときに前のモデルIDが残っていると混乱する | LOW | `_fetch_models` を Provider ごとに実装。Gemini は `/v1beta/models`、Claude は `/v1/models`、LM Studio は既存 `/v1/models` 実装を流用 |

### Differentiators（競合優位性になる機能）

| 機能 | 価値提案 | 複雑度 | 実装メモ |
|------|---------|--------|---------|
| コスト/プライバシー確認ダイアログ（ページ数 × 概算コスト表示） | 「送るとどのくらいかかるか」を実行前に提示することで課金トラブルを未然に防ぐ。GPU 非搭載 PC ユーザーはクラウド課金初心者が多い | MEDIUM | 実行ボタン押下後、クラウドプロバイダ選択時のみ `messagebox.askyesno` でページ数・概算トークン費用（定数ベース概算）・プライバシー注記を表示。LM Studio/Tesseract には表示しない |
| `ocr_scale` デフォルト見直し（2.0 → 1.5）+ UI へのコスト/精度ヒント表示 | 低スペック PC での CPU レンダリング負荷を削減しつつ、ユーザーがトレードオフを理解できる | LOW | `DEFAULT_OCR_SCALE = 1.5` に変更。Spinbox 横に「低 ←速度/コスト↔精度→ 高」ラベルを追加 |
| Tesseract Provider（GPU 不要・完全無料・オフライン） | ネット接続なし・課金なしのフォールバック。精度は低いが存在するだけでオフライン環境を救う | MEDIUM | `pytesseract` wrapper として実装。`jpn` / `jpn_vert` 言語データ要求を UI に明示。`ocr_scale` は 3.0 以上を推奨とヒント表示。`TesseractProvider` 選択時は「精度がクラウドより劣ります」の警告を SettingsDialog に表示 |
| プラグインによるカスタムプロバイダ登録（`PluginManager` 拡張） | サードパーティが独自 OCR バックエンドを追加できる。エコシステムの拡張可能性 | HIGH | `PluginManager` に `register_ocr_provider(name, provider_class)` フックを追加。Phase 4（任意）。フェーズ 1〜3 には影響しない |
| セッション中のみのインメモリAPIキー保持（ダイアログ入力→JSON非書込み） | 環境変数を設定できないユーザーへの逃げ道を、セキュリティを妥協せずに提供 | LOW | `OCRDialog` に「環境変数が未設定の場合、ここに入力してください（保存されません）」フォームを追加。入力値は `os.environ` に `setenv` せず、ダイアログインスタンスのメモリのみに保持 |

### Anti-Features（よく要求されるが問題を起こす機能）

| 機能 | 要求される理由 | なぜ問題か | 代替案 |
|------|-------------|-----------|-------|
| APIキーを `settings.json` に保存 | 毎回環境変数を設定するのが面倒 | キーが平文 JSON に残ると認証情報漏洩リスク。`pagefolio_settings.json` は `dist/` 以下に置かれるためバイナリ配布時にも漏洩の可能性 | セッション中メモリ保持のみ（differentiator として提供）。長期的には OS キーストア（Windows Credential Manager）連携を別マイルストーンで検討 |
| クラウド OCR のフルページ並列化（8並列固定） | 速くなる | Gemini/Claude の Rate Limit（429）を頻発させ、かえって遅くなるか全ページ失敗になる | プロバイダ別 `default_concurrency` で制御（クラウドは 1〜2、ローカルは最大8） |
| 公式 SDK（`anthropic` / `google-genai`）の採用 | コード記述が楽になる | PyInstaller ビルドが肥大化し、隠れ依存の取り込みが難しくなる。現行の `.exe` 単体配布方針と相容れない | `urllib` 直叩きで実装（確定済み方針） |
| LM Studio を GPU 非搭載ユーザーの主推奨として前面に出す | ローカル推論なので無料・プライベート | GPU 非搭載 PC では低速/VRAM 不足で実用にならない。初回起動でユーザーを失望させる | SettingsDialog でプロバイダを選ぶ際に「GPU が無い場合は Gemini / Claude を推奨」のツールチップまたはラベルを表示 |
| Tesseract を主役 OCR エンジンとして据える | 無料・オフライン・Python から使いやすい | 日本語学習データ未導入・低解像度・複雑レイアウトで精度が大幅に落ちる。ユーザーの期待値に応えられない | オプション扱い（`tesseract` プロバイダとして実装し「精度劣後」を明記） |
| 温度パラメータを Claude Opus 4.8 で有効化 | 全プロバイダで設定を統一したい | Anthropic API 仕様上、Opus 4.8 系は `temperature` パラメータを受け付けず API エラーになる（`output_config.effort` で代替） | モデル名に `opus` が含まれる場合は temperature Spinbox を disabled にし `effort` ドロップダウンを代わりに表示 |

---

## Feature Dependencies

```
[プロバイダ抽象化 (OCRProvider 基底クラス)]
    └──requires──> [LM Studio を Provider 実装へリファクタ]
    └──requires──> [run_parallel() 一般化]
                       └──enables──> [Gemini Provider]
                       └──enables──> [Claude Provider]
                       └──enables──> [Tesseract Provider]

[プロバイダ選択 UI (ocr_provider 設定)]
    └──requires──> [プロバイダ抽象化]
    └──enables──> [APIキー未設定エラー表示]
    └──enables──> [コスト/プライバシー確認ダイアログ]
    └──enables──> [プロバイダ別デフォルト並列度]

[テキスト埋め込み判定 OCR スキップ]
    └──requires──> [なし (fitz.page.get_text() は既存機能)]
    └──独立して最優先で実装可能]

[逐次レンダリング化]
    └──requires──> [run_parallel() 一般化]
    └──enhances──> [Gemini Provider / Claude Provider]（メモリ削減効果が大きい）

[PluginManager プロバイダ登録フック]
    └──requires──> [プロバイダ抽象化]
    └──独立 (Phase 4・任意)]
```

### 依存関係メモ

- **プロバイダ抽象化がすべての前提:** `OCRProvider` 基底クラスと `run_parallel()` の一般化なしに、Gemini/Claude の実装もダイアログ改修も着手できない。
- **テキスト埋め込み判定は独立:** `page.get_text()` は既存 fitz 機能のみで完結するため、プロバイダ抽象化の前でも後でも実装可能。低コスト・高効果のため Phase 1 で先行実施が最適。
- **逐次レンダリング化はクラウド Provider と相性が良い:** フェーズ2以降（クラウドProvider 追加後）に適用することでメモリ削減と429対策を同時に達成できる。

---

## MVP 定義（v1.4.0 スコープ）

### フェーズ1 で出荷（既存挙動を変えずに内部刷新）

- [x] `OCRProvider` 基底クラス定義 — すべてのクラウド Provider 実装の前提
- [x] LM Studio を Provider 実装へリファクタ — 後方互換維持で既存 OCR が壊れないことをテスト担保
- [x] `run_parallel()` 一般化 — プロバイダ非依存の並列実行基盤
- [x] テキスト埋め込み判定による OCR スキップ — 独立実装・低コスト・高効果

### フェーズ2で追加（Claude Provider + 最小UI改修）

- [ ] Claude Provider（`ANTHROPIC_API_KEY`・messages API・effort 対応・モデル一覧）
- [ ] `ocr_provider` 設定値 + SettingsDialog のプロバイダ選択 UI
- [ ] APIキー未設定エラー表示
- [ ] 多言語文言追加（`lang.py`）

### フェーズ3で追加（Gemini + 低スペック対策）

- [ ] Gemini Provider（`GEMINI_API_KEY` / `GOOGLE_API_KEY`・inline_data・モデル一覧）
- [ ] 逐次レンダリング化（メモリ最適化）
- [ ] コスト/プライバシー確認ダイアログ（クラウドプロバイダ選択時のみ）
- [ ] `ocr_scale` デフォルト見直し + UI ヒント表示
- [ ] 429/5xx リトライ（指数バックオフ）

### フェーズ4 — 任意

- [ ] Tesseract Provider（精度劣後注記つき）
- [ ] PluginManager プロバイダ登録フック新設

---

## Feature Prioritization Matrix

| 機能 | ユーザー価値 | 実装コスト | 優先度 |
|------|------------|----------|-------|
| `OCRProvider` 抽象化 + LM Studio リファクタ | HIGH（全体の土台） | MEDIUM | P1 |
| テキスト埋め込み判定 OCR スキップ | HIGH（コスト/速度）| LOW | P1 |
| Claude Provider | HIGH（GPU 非搭載の主役） | MEDIUM | P1 |
| プロバイダ選択 UI + 既定 `off` | HIGH（安全な初期状態） | MEDIUM | P1 |
| APIキー未設定エラー | HIGH（セキュリティ/UX） | LOW | P1 |
| Gemini Provider | HIGH（コスト競争力） | MEDIUM | P1 |
| 逐次レンダリング化 | HIGH（低RAM PC） | MEDIUM | P2 |
| 429/5xx リトライ | MEDIUM（安定性） | MEDIUM | P2 |
| コスト/プライバシー確認ダイアログ | MEDIUM（課金トラブル防止） | LOW | P2 |
| `ocr_scale` 見直し + ヒント | MEDIUM（低スペック体験） | LOW | P2 |
| Tesseract Provider | LOW（オプション） | MEDIUM | P3 |
| PluginManager プロバイダ登録フック | LOW（拡張性） | HIGH | P3 |
| セッション中メモリ保持 APIキー入力欄 | LOW（利便性） | LOW | P3 |

---

## 既存 OCR 実装との依存関係（改修コスト把握）

現行コードで変更が必要なファイルと影響範囲を整理する。

| ファイル | 現状 | v1.4.0 での変更 | 影響度 |
|---------|------|----------------|-------|
| `pagefolio/ocr.py` | LM Studio 専用関数群 + `OCRMixin` | `OCRProvider` 基底クラス新設・LM Studio を Provider 実装へ・`run_parallel()` 一般化 | HIGH（主要リファクタ対象） |
| `pagefolio/ocr_dialog.py` | `call_lm_studio_parallel` / `fetch_lm_studio_models` を直 import・`url_var`/`model_var` 前提 | プロバイダ選択 UI 追加・APIキーエラー表示・逐次レンダリング化・温度 disabled（Opus）など | HIGH（L サイズ、最大作業量） |
| `pagefolio/settings.py` | `lm_studio_url` / `lm_studio_model` / `ocr_*` のデフォルト値 | `ocr_provider: "off"` 追加・キー項目は追加しない | LOW |
| `pagefolio/lang.py` | `ocr_server_label` 等の文言 | プロバイダ名・APIキー未設定・精度注記・コスト警告の文言追加 | LOW |
| `pagefolio/ui_builder.py` | OCR ボタン（現在ページ/選択ページ） | `ocr_provider == "off"` 時にボタン disabled | LOW |
| 新規 `pagefolio/ocr_providers.py` | なし | Gemini / Claude / Tesseract Provider 実装を収容 | HIGH（新規作成） |
| 新規 `tests/test_ocr.py` | なし | 各 Provider の payload 構築・レスポンス解析・スキップ判定をモックテスト | MEDIUM |

---

## Sources

- `docs/OCRプロバイダ化_見積もり仕様.md` — 確定済み設計仕様（最高信頼度）
- `.planning/PROJECT.md` — マイルストーン目標・Key Decisions
- `pagefolio/ocr.py` — 現行実装の結合点分析
- `pagefolio/ocr_dialog.py` — 現行 UI の改修対象の把握
- Anthropic API 仕様（`docs/` spec より）— `temperature` 非対応（Opus 4.8）・`effort` 代替
- Google AI Studio API 仕様（`docs/` spec より）— `inline_data`・`GEMINI_API_KEY`/`GOOGLE_API_KEY` フォールバック

---

*Feature research for: OCR プロバイダ化 + クラウドAPI対応（PageFolio v1.4.0）*
*調査日: 2026-06-06*
