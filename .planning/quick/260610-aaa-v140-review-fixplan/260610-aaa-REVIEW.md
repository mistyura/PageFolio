---
quick_id: 260610-aaa
slug: v140-review-fixplan
description: v1.4.0 リリース内容のコードレビュー結果と修正計画（v1.4.1 ホットフィックス / v1.4.2 / バックログ）
date: 2026-06-10
status: reference
type: review
review_range: cad78a4 (v1.3.0) .. e0e885f (v1.4.0)
usage: >
  v1.4.0 以降の修正作業（v1.4.1 ホットフィックス等）に着手する際は、
  必ず本文書を参照して対象・優先度・該当箇所を確認すること。
  着手時は本文書の該当項目をチェックし、完了後にステータスを更新する。
---

# v1.4.0 リリースレビュー & 修正計画（260610-aaa）

> **本文書の位置づけ**: v1.4.0（マルチプロバイダ OCR）リリース直後の全差分コードレビュー結果。
> **変更着手時はこの文書を参照すること。** v1.4.1 / v1.4.2 の計画立案・実装はここに記載の
> 指摘番号（H-1 など）を引用して進める。

## レビュー実施内容

- 対象差分: `git diff cad78a4..e0e885f`（コード本体 約 6,000 行 / 125 ファイル）
- 品質ゲート: pytest 396 件全パス・ruff check / format 全パス（2026-06-10 確認）
- リリース状態: タグ `v1.4.0`・GitHub Release（win64 zip + SHA256）公開済み・main 到達済み
- バージョン同期: `APP_VERSION` / README バッジ / 開発履歴.md 一致

## 問題なしと確認済みの領域（再調査不要）

- **API キーガード**: `_SENSITIVE_KEYS` により settings.json へ構造的に保存されない。
  セッションキーは `app._session_api_keys` のみ・ログにキー値出力なし・環境変数優先順位も整合
- **Tesseract subprocess**: `shell=True` 不使用・引数リスト渡し・`psm` int キャスト済み・
  `-l` 引数は `_TESSERACT_LANGS` 由来のみ → インジェクション懸念なし
- **HTTPS**: Anthropic / Gemini とも https 固定・urllib 既定の証明書検証有効
- **lang.py ja/en 整合**: 251/251 キー完全一致（未使用キー 3 件は L-5 参照）
- **規約**: 裸 except なし・C[] / `self._font()` 全面使用・logger 使用

---

## 高優先度（H）— v1.4.1 ホットフィックス対象

### H-1: 既定設定で Claude / Gemini OCR が全リクエスト 400 になる見込み

- 該当: `pagefolio/ocr.py:492,505`（build_provider）、`pagefolio/settings.py` `_load_settings()` の `"ocr_max_tokens": -1`
- 内容: `-1` は LM Studio 専用の「モデル最大値に委ねる」値だが、`_load_settings()` が
  setdefault でマージするためキーは常に存在し、`settings.get("ocr_max_tokens", 4096)` の
  フォールバック 4096 は効かない。Anthropic は正の整数必須・Gemini も `-1` を拒否。
  プロバイダ側にクランプなし（コードレベルで裏取り済み・実 API 検証は未実施）。
- 対応: build_provider の claude/gemini 分岐で `mt <= 0` なら 4096 にクランプ。回帰テスト追加。

### H-2: Tesseract / プラグインプロバイダが実行時に LMStudioProvider へ置換される

- 該当: `pagefolio/ocr_dialog.py:879-889`（`_on_run` else 分岐）、`ocr_dialog.py:661-670`（`_apply_llm_settings` else 分岐）
- 内容: 分岐が claude / gemini / それ以外の 3 択のため `tesseract`・プラグイン登録名も
  else に落ち、`self.provider` が LMStudioProvider で上書きされる。
  「オフライン・外部送信なし」のはずの Tesseract 選択時に画像が LM Studio URL へ送信される。
  `_provider_display_name`（ocr_dialog.py:505-520）も tesseract 分岐がなく
  `ocr_provider_name_tesseract` キーが未使用。
- 対応: else を lmstudio/off 限定にし、それ以外は `build_provider(self.app.settings, ...)` で再生成。
  表示名に tesseract 分岐を追加。

### H-3: プロバイダ切替後に concurrency が再クランプされない

- 該当: `pagefolio/ocr_dialog.py:67`（init 時のみ clamp）、`ocr_dialog.py:615-678`（`_apply_llm_settings`）
- 内容: ダイアログ内で lmstudio→gemini に切替えても `self.concurrency` は旧値のまま。
  `GeminiProvider.max_concurrency = 1`（D-07）が無視され最大 8 ワーカー起動 → 429 連発。
- 対応: `_apply_llm_settings` / `_on_run` の provider 再生成後に
  `self.concurrency = max(1, min(provider.max_concurrency, self.concurrency))` を再評価。

### H-4: LLM 設定ダイアログのセクションがボタン行の下に表示される（UI 崩れ）

- 該当: `pagefolio/dialogs/llm_config.py:543-594`（`_on_provider_change`）
- 内容: プロバイダ別セクション（url/claude/gemini/tesseract/effort/temperature）が
  btn_row pack 後に `before=` なしで pack されるため「適用/キャンセル」より下に出る。
  ocr_dialog 側は 139777c で `before=` 修正済みだが llm_config 側が未対応。
- 対応: scale_row を self 属性化し `pack(..., before=self.scale_row)` 等のアンカー指定。

### H-5: プロバイダ切替時にダイアログがリサイズされずボタンが見切れる（ユーザー報告 2026-06-10）

- 該当: `pagefolio/dialogs/llm_config.py:57`（`resizable(False, False)`）、`:72-81`（`__init__` でのみ
  `winfo_reqheight()` ベースの geometry 計算）、`:543-595`（`_on_provider_change` は pack 切替のみ）
- 内容: ダイアログの高さは初期化時に一度だけ計算され固定される。例 Gemini → LM Studio のように
  項目が多いプロバイダへ切替えると内容が固定高さを超え、「適用/キャンセル」ボタンが見切れる
  （再立ち上げで直るのは初期化時に再計算されるため）。`_on_model_change` の effort/temperature
  切替でも同様に高さが変動する。
- 対応: `_on_provider_change` / `_on_model_change` の末尾で `self.update_idletasks()` 後に
  `h = max(480, self.winfo_reqheight() + 20)` を再計算し、現在位置（`winfo_x()/winfo_y()`）を
  維持したまま `self.geometry(f"{w}x{h}+{x}+{y}")` を再適用する（幅 w は初期値を self 属性化して保持）。
  H-4（`before=` アンカー）と同じメソッドを触るため、**H-4 と同時に修正すること**。

---

## 中優先度（M）— v1.4.2 安定化対象

### M-1: producer のブロッキング put による UI フリーズ

- 該当: `pagefolio/ocr_dialog.py:950-964`（`put(timeout=0.1)` busy-loop）、`ocr_dialog.py:921`（`put(None)` 無タイムアウト）
- 内容: キュー満杯時にメインスレッドが busy-loop / ブロックし、最悪 `ocr_timeout`（600 秒）UI 凍結。
- 対応: `queue.Full` 時は `_render_idx` を進めず `self.after(100, self._render_next_page)` で
  再スケジュール。終了シグナルも `put_nowait` + 再スケジュール化。

### M-2: ダイアログ破棄後コールバック・世代ガード欠如

- 該当: `pagefolio/ocr_dialog.py:1202-1215`（`_on_close`）、`:481-501`（`_clear_text`）、`:986-1113`（`_worker`）
- 内容: 実行中に閉じても旧ワーカーが生存し、破棄済みウィジェットへの `after` で TclError。
  キャンセル→再実行で旧ワーカーが新ランの `_done_count` / `results` を破壊し得る。
  viewer.py の `_preview_gen` 相当の世代ガードが OCRDialog にない。
- 対応: `self._run_gen` を導入しワーカー起動時に捕捉。`after` 投函前と finish 系で
  世代一致 + `winfo_exists()` 確認。`_worker` 内 `after` を `try/except tk.TclError` で保護。

### M-3: `_supports_effort` の誤判定で 400

- 該当: `pagefolio/ocr_providers.py:255-268, 297-300`
- 内容: `EFFORT_MODELS` 外でも `"sonnet" in model` で True になり、effort 非対応の
  claude-sonnet-4-5 に `output_config.effort` を送って 400。逆に未知の将来モデルには
  temperature を送って 400 の恐れ。
- 対応: effort は `EFFORT_MODELS` 完全一致時のみ。temperature は haiku 系のみ。
  それ以外は両方省略（最も安全な前方互換）。単体テスト追加。

### M-4: gemini-2.5-pro で `thinkingBudget: 0` が拒否される可能性

- 該当: `pagefolio/ocr_providers.py:481`（payload 固定）、`:445`（RECOMMENDED_MODELS に pro）
- 内容: 2.5 Pro は thinking 無効化不可で 400 INVALID_ARGUMENT の見込み（実 API 未検証）。
- 対応: pro 系モデルでは `thinkingConfig` を省略。実 API で検証。

### M-5: `Retry-After` を無検証で sleep・キャンセル不能

- 該当: `pagefolio/ocr_providers.py:341, 539`、`pagefolio/ocr.py:259-264, 401-406`
- 内容: サーバが `Retry-After: 86400` を返すとワーカーがその秒数スリープ。
  スリープ中は `is_cancelled` を見ないためキャンセルが効かない。
- 対応: 上限クランプ（例 60 秒）+ 0.5 秒刻みスリープでループ内キャンセル確認。

### M-6: Gemini コスト概算が過小（課金警告として危険方向）

- 該当: `pagefolio/ocr_dialog.py:547-555`（`_estimate_cost`)
- 内容: gemini-2.5-flash に旧 1.5-flash 世代単価（$0.075/$0.30 per MTok）を適用。
  実勢（入力 $0.30 / 出力 $2.50 程度）より大幅過小。
- 対応: 単価を現行価格に更新 or 安全側（高め）に倒す。単価を定数辞書化しモデル名併記。

### M-7: プラグインプロバイダ `cls()` 実体化が無防備

- 該当: `pagefolio/ocr.py:517-519`、`ocr.py:575-588`（`_start_ocr` は ValueError のみ捕捉）
- 内容: プラグインのコンストラクタ例外が Tk コールバック内未処理例外になる
  （「プラグイン失敗は他をクラッシュさせない」方針に違反）。`cls()` 引数なし契約も docstring 未記載。
- 対応: build_provider のプラグイン分岐を try/except Exception で RuntimeError に正規化、
  または `_start_ocr` の捕捉を広げてエラー表示。docstring に契約追記。

### M-8: SettingsDialog 経由の LLMConfigDialog で plugin_manager が常に None

- 該当: `pagefolio/dialogs/settings.py:173`、`pagefolio/app.py:358`
- 内容: `getattr(self, "_plugin_manager", None)` を設定するコードが存在せず常に None。
  設定画面経由ではプラグイン登録プロバイダが Combobox に出ない。
- 対応: `SettingsDialog.__init__` に `plugin_manager` 引数を追加し app.py から渡す。

### M-9: ClaudeProvider レスポンスパースの KeyError 漏れ

- 該当: `pagefolio/ocr_providers.py:364-375`
- 内容: `block["text"]` 直接アクセスだが except は `(json.JSONDecodeError, TypeError)` のみ。
  `text` キー欠落ブロックで素の KeyError が例外規約（RuntimeError 正規化）外に伝播。
- 対応: except に KeyError 追加 or `block.get("text")` で None 除外。

### M-10: ハードコード日本語文言（i18n 違反）8 箇所

- 該当: `pagefolio/ocr_dialog.py:573, 678`、`pagefolio/dialogs/llm_config.py:700, 711, 718, 734, 747, 754`
- 内容: lang=en でも日本語表示。llm_config.py:705/741 の except 側文言は
  「通信失敗でも『未設定』と表示する」誤誘導も含む。
- 対応: LANG 辞書へ ja/en キー追加。エラー文言はエラー内容ベースに分離。

### M-11: `except (X, Exception)` という実質全捕捉の列挙

- 該当: `pagefolio/ocr_dialog.py:676`、`pagefolio/dialogs/llm_config.py:705, 741`
- 内容: タプルに Exception が含まれ個別型列挙が無意味。規約趣旨に反する誤解を招く書き方。
- 対応: 意図が全捕捉なら `except Exception as e:` に簡約。

---

## 低優先度（L）— バックログ（v1.5.0 以降）

### L-1: producer-consumer ロジックの二重実装

- 該当: `pagefolio/ocr.py:140-328`（`run_with_bounded_buffer`・本番未使用）と
  `pagefolio/ocr_dialog.py:891-1113`（独自実装）
- 既に挙動乖離あり（waiting 進捗・"skip" status・render 失敗時 on_done）。
  ヘルパーの docstring はスレッドモデルと矛盾（render_fn を producer スレッドから呼ぶ）。
- 対応: どちらかに一本化 or ヘルパーをテスト専用と明記し仕様統一。
  **M-1/M-2 修正時は両実装への影響を必ず確認すること。**

### L-2: `register_ocr_provider` の名前検証・アンロード解除なし

- 該当: `pagefolio/plugins.py`
- 組み込み名と同名登録は黙って無視・プラグイン無効化後も登録残留。
- 対応: 重複名 `logger.warning`・unload 時の登録解除。

### L-3: `plugin_manager._provider_registry` への私有属性直接アクセス

- 該当: `pagefolio/ocr.py:517`、`pagefolio/dialogs/llm_config.py:110`
- 対応: `PluginManager.get_ocr_provider(name)` 等の公開アクセサ追加。

### L-4: TesseractProvider が `tesseract_lang` 設定を無視

- 該当: `pagefolio/ocr_providers.py:669-697`
- `ocr_image` は常に `_TESSERACT_LANGS` から自動決定し `self.lang` 未使用。
  `_TESSERACT_LANGS` は import 時固定（言語パック追加は再起動まで反映されない）。
- 対応: `self.lang` が利用可能なら優先・不可なら自動フォールバック。

### L-5: lang.py 未使用キー 3 件

- `ocr_provider_off_hint` / `tesseract_not_installed` / `ocr_provider_name_tesseract`
  （最後のキーは H-2 の表示名修正で使用すべきもの）

### L-6: その他の軽微事項

- レンダー失敗ページでプログレスバーが 100% に達しない（`ocr_dialog.py:965-967`）
- ClaudeProvider `list_models` のページネーション・`stop_reason`（截断検出）未対応
- Gemini エラーメッセージの body 切り詰めなし（`ocr_providers.py:497` → `str(body)[:500]` に統一）
- LM Studio URL のスキーム未検証（http/https のみ許可ガード推奨）・
  Gemini モデル名の URL 未エスケープ（`urllib.parse.quote` 推奨）
- producer が fatal 発生後も全ページ render 継続（`ocr.py:192-216`）
- sentinel `buf.put(None)` の暗黙容量不変条件（`ocr.py:217-220`）の明文化
- `_fetch_models` / `_test_connection` のほぼ完全重複（`llm_config.py:649-690`）
- OCR ダイアログ内で "off" 切替時に `app._update_ocr_buttons_state()` 未呼出
- **CLAUDE.md「ファイル構成」の更新**: `dialogs.py` → `dialogs/` パッケージ、
  `lang.py` / `themes.py` / `ocr.py` / `ocr_dialog.py` / `ocr_providers.py` が未記載

---

## リリース計画案

| リリース | 対象 | 規模目安 |
|---------|------|---------|
| v1.4.1 ホットフィックス | H-1〜H-5（着手前に H-1/H-2 を実機再現確認。H-4/H-5 は同一メソッドのため同時修正） | 1 セッション |
| v1.4.2 安定化 | M-1〜M-11 | 1〜2 セッション |
| v1.5.0 以降 | L-1〜L-6 | バックログ |

## 着手時の注意

- H-1（max_tokens）と M-4（thinkingBudget）の API 挙動はコードレビューに基づく判断。
  **修正前に実 API キー / 実 tesseract 環境で再現確認すること。**
- M-1/M-2（producer-consumer）の修正は L-1 の二重実装に注意（ocr.py ヘルパーと
  ocr_dialog.py 独自実装の両方を確認）。
- 修正完了時は本文書の該当項目に完了マーク（✅ + コミットハッシュ）を追記すること。

## 実行推奨コマンド

```
pytest tests/test_ocr.py tests/test_ocr_providers.py tests/test_provider_ui.py
ruff check . && ruff format .
```
