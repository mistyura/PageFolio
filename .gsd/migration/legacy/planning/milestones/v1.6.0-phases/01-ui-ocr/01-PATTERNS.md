# Phase 1: 設定/UI 改善（OCR パラメータ一元化・スライダー配置） - Pattern Map

**Mapped:** 2026-06-18
**Files analyzed:** 5（すべて既存ファイルの修正。新規ファイル作成なし）
**Analogs found:** 5 / 5（うち決定打となる同一リポジトリ内アナログ多数）

> このフェーズは**新規ファイルを作らず既存ファイルを修正する**。各ファイルの「最も近いアナログ」は、原則として**同一モジュール内の隣接コード**である。最大の収穫は、読み取り専用化のアナログが**すでに同じファイル `ocr_dialog.py` の `url_var` Entry（259-269）に存在する**こと。プランナーはこれをそのまま横展開すればよい。

---

## File Classification

| 修正ファイル | 役割 (Role) | データフロー (Data Flow) | 最も近いアナログ | マッチ品質 |
|--------------|-------------|--------------------------|------------------|------------|
| `pagefolio/ocr_dialog.py` | dialog（OCR 実行 UI） | request-response / settings dict → widgets | 同ファイル `url_var` Entry（259-269）＝既存の `state="readonly"` 実装 | exact（同一パターンが同ファイル内に既存） |
| `pagefolio/dialogs/llm_config.py` | dialog（永続設定の唯一の編集面） | widgets → settings dict（`_apply`） | 同ファイル `_apply`（838-908）＝編集・クランプ・保存導線 | exact（変更ほぼ不要・参照元） |
| `pagefolio/ui_builder.py` | UI construction（Mixin） | widget レイアウト（pack 構造） | 同ファイル `hdr` / `sel_frame`（174-198）＝`pack(fill="x")` 独立行 | exact（同パターンの独立行が直上に既存） |
| `pagefolio/viewer.py` | render（Mixin） | settings dict ↔ thumbnail 倍率 | 同ファイル `_on_thumb_zoom_release`（146-154） | exact（**変更不要・挙動維持の確認対象**） |
| `pagefolio/settings.py` | persistence | DEFAULT_SETTINGS / `_save_settings` | 同ファイル defaults（45-65）/ `_SENSITIVE_KEYS`（17-26） | exact（**変更不要・真実の源として参照のみ**） |

---

## Shared Patterns（横断パターン）

### 読み取り専用ウィジェット（最重要・同一ファイル内に既存）
**Source:** `pagefolio/ocr_dialog.py` の `url_var` Entry（259-269）
**Apply to:** OCRDialog の数値パラメータ Spinbox 群（scale / timeout / max_tokens / temperature）＋ `model_combo`

既存の読み取り専用 Entry がそのまま雛形になる。グレーアウト感は `fg=C["TEXT_SUB"]` ＋ `state="readonly"` ＋ `readonlybackground` で表現済み:

```python
tk.Entry(
    sf,
    textvariable=self.url_var,
    font=self._font(-1),
    bg=C["BG_CARD"],
    fg=C["TEXT_SUB"],            # ← グレーアウト（TEXT_MAIN ではなく TEXT_SUB）
    insertbackground=C["TEXT_MAIN"],
    relief="flat",
    state="readonly",           # ← 読み取り専用化の核
    readonlybackground=C["BG_CARD"],
).pack(side="left", fill="x", expand=True, padx=4)
```

**`tk.Spinbox` への適用差分:** `tk.Spinbox` は `state="readonly"` を受け付ける（スピンボタンも無効化される）が、`readonlybackground` 引数は持たない。`fg=C["TEXT_SUB"]` への変更＋`state="readonly"` の付与で「グレーアウトした読める値」を満たす（D-01・Claude's Discretion 範囲）。`tk.Label` への置換も裁量で可だが、最小差分は既存 Spinbox に `state="readonly"` を足し `fg` を `TEXT_SUB` にする方法。

**`model_combo`（285-291）への適用:** `ttk.Combobox` は `state="readonly"`（プルダウン選択のみ可）と `state="disabled"`（完全無効）がある。読み取り専用表示の意図に沿うのは `state="disabled"`（D-01: 編集導線は LLMConfig に一元化）。「モデル取得」ボタン（292-296）も併せて無効化/非表示を検討（裁量）。

### LANG キー追加規約（新規文言が必要な場合のみ）
**Source:** `pagefolio/lang.py`（CLAUDE.md 規約）
**Apply to:** 読み取り専用ラベルや「設定で変更」等の新規文言を足す場合
- ja / en **両辞書に同一キー**で追加（キー数左右一致を維持）。
- 既存キー（`ocr_scale_short` / `ocr_timeout_short` / `ocr_max_tokens_short` / `ocr_temperature_short` / `ocr_params_hint` 等）はそのまま流用可。新規文言は最小限に。

### 設定の単一の真実 & 永続化
**Source:** `pagefolio/settings.py` defaults（45-65）/ `_save_settings`（79〜）
**Apply to:** OCRDialog 表示・LLMConfig 保存の整合
- OCR 画面は `app.settings`（＝LLMConfig 適用結果）を**表示するだけ**。保存ロジックは増やさない。
- 機密キーは `_SENSITIVE_KEYS`（17-26）ガードで非保存。本フェーズで触る数値パラメータは機密ではないため変更不要。

---

## Pattern Assignments（ファイル別）

### `pagefolio/ocr_dialog.py` (dialog, settings dict → widgets)

**Analog:** 同ファイル `url_var` Entry（259-269、上記 Shared 参照）

**読み取り専用化対象（Spinbox 群・現状は編集可）:**

| 変数 | 行 | from/to | 適用 |
|------|----|---------|------|
| `scale_var` | 319-331 | 1.0–4.0 | `state="readonly"` + `fg=C["TEXT_SUB"]` |
| `timeout_var` | 339-351 | 10–600 | 同上 |
| `max_tokens_var` | 359-371 | -1–MAX | 同上 |
| `temperature_var` | 386-398 | 0.0–2.0 | 同上 |
| `url_var`（Entry） | 259-269 | — | **既に readonly**（手本・変更不要） |
| `model_var`（Combobox） | 285-291 | — | `state="disabled"`（編集導線撤去） |

**編集可能のまま残す実行時 UI（変更禁止・D-06）:**
- `preset_var` Radiobutton 群（225-241）
- `force_ocr_var` Checkbutton（416-426）
- `api_key_var` Entry（439-449、`_session_api_keys` 経由・非永続）

**ライブ即時反映（D-03）— 既存経路を活用:**
`_refresh_provider_dependent_ui`（866-896）が `_apply_llm_settings`（794〜）から呼ばれ、LM Studio 欄では既に Tk 変数を settings へ再同期している（844-848）:

```python
# (g) LM Studio 欄の Tk 変数も settings に合わせて更新
self.url_var.set(self.app.settings.get("lm_studio_url", "http://localhost:1234"))
self.model_var.set(self.app.settings.get("lm_studio_model", ""))
```

**プランナーへの指示:** 読み取り専用化した数値パラメータの即時反映は、この (g) ブロックと**同じ要領**で、`_apply_llm_settings` 内（または `_refresh_provider_dependent_ui` 内）に `scale_var` / `timeout_var` / `max_tokens_var` / `temperature_var` を `app.settings` の値で `.set()` し直す行を追加すればよい。`state="readonly"` の Spinbox でも `textvariable` 経由の `.set()` は反映される（readonly はユーザー入力のみ禁止）。LM Studio 欄が `lmstudio`/`""`/`off` 分岐（834-848）でのみ更新されている点に注意 — 数値パラメータは全プロバイダ共通なので、分岐の外（共通箇所）で同期すること。

---

### `pagefolio/dialogs/llm_config.py` (dialog, widgets → settings dict)

**Analog:** 同ファイル `_apply`（838-908）

このファイルは**一元化の「先（編集面）」であり、機能追加はほぼ不要**。`_apply` は既に全数値パラメータをクランプして `llm_settings` に収集し、`on_apply` コールバック（OCRDialog 側 `_apply_llm_settings`）へ渡している:

```python
try:
    llm_settings["ocr_scale"] = max(1.0, min(4.0, float(self.ocr_scale_var.get())))
except (tk.TclError, ValueError):
    llm_settings["ocr_scale"] = 1.5
# timeout / max_tokens / temperature / concurrency も同じ try/except クランプパターン（881-904）
self.destroy()
if self.on_apply:
    self.on_apply(llm_settings)
```

**プランナーへの指示:** 本フェーズでは `llm_config.py` の編集は原則不要（既に唯一の編集導線として完成）。OCRDialog 側を読み取り専用化しても、保存・適用はこの既存 `_apply` → `on_apply` 経路に集約されるため、ここに手を入れる必要はない。確認のみ。

---

### `pagefolio/ui_builder.py` (UI construction, pack レイアウト)

**Analog:** 同ファイル直上の独立行 `hdr`（174-175）/ `sel_frame`（191-192）

両者とも `tk.Frame(parent, bg=C["BG_PANEL"])` を作り `pack(fill="x", ...)` する**全幅独立行**パターン。これを 1 行追加するだけで D-08 を満たす。

**現状（スライダーが `sel_frame` 内 side="right" で幅を奪い合う・問題箇所）:**
```python
sel_frame = tk.Frame(parent, bg=C["BG_PANEL"])
sel_frame.pack(fill="x", padx=6, pady=2)
ttk.Button(sel_frame, text=self._t("select_all"), command=self._select_all).pack(side="left", padx=2)
ttk.Button(sel_frame, text=self._t("deselect"), command=self._deselect_all).pack(side="left", padx=2)

self.thumb_zoom_var = tk.DoubleVar(value=self.settings.get("thumb_zoom", 1.0))
self.thumb_zoom_scale = ttk.Scale(
    sel_frame, from_=0.5, to=2.5, variable=self.thumb_zoom_var, orient="horizontal",
)
self.thumb_zoom_scale.pack(side="right", fill="x", expand=True, padx=(10, 2))  # ← 同一行で幅競合
self.thumb_zoom_scale.bind("<ButtonRelease-1>", self._on_thumb_zoom_release)
```

**目標（独立行へ移設・`hdr`/`sel_frame` と同じ独立行パターンを踏襲）:**
```python
sel_frame = tk.Frame(parent, bg=C["BG_PANEL"])
sel_frame.pack(fill="x", padx=6, pady=2)
ttk.Button(sel_frame, text=self._t("select_all"), command=self._select_all).pack(side="left", padx=2)
ttk.Button(sel_frame, text=self._t("deselect"), command=self._deselect_all).pack(side="left", padx=2)

# 新設: スライダー専用の全幅独立行（ボタン行の直後）
zoom_frame = tk.Frame(parent, bg=C["BG_PANEL"])
zoom_frame.pack(fill="x", padx=6, pady=(0, 4))
self.thumb_zoom_var = tk.DoubleVar(value=self.settings.get("thumb_zoom", 1.0))
self.thumb_zoom_scale = ttk.Scale(
    zoom_frame, from_=0.5, to=2.5, variable=self.thumb_zoom_var, orient="horizontal",
)
self.thumb_zoom_scale.pack(fill="x", expand=True, padx=2)  # ← side 指定なし＝全幅
self.thumb_zoom_scale.bind("<ButtonRelease-1>", self._on_thumb_zoom_release)
```

**不変条件（D-09）:** `from_=0.5` / `to=2.5`、`thumb_zoom_var`、`<ButtonRelease-1>` → `_on_thumb_zoom_release` バインドは一切変えない。変更は親フレームと pack 引数のみ。`zoom_frame` の `pack` は `canvas_frame`（211-212）より前に置くこと（パネル上部に配置）。

---

### `pagefolio/viewer.py` (render, settings ↔ 倍率) — 変更不要・挙動維持の確認対象

**Analog:** 自身 `_on_thumb_zoom_release`（146-154）

```python
def _on_thumb_zoom_release(self, event=None):
    if not hasattr(self, "thumb_zoom_var"):
        return
    self.settings["thumb_zoom"] = self.thumb_zoom_var.get()
    from pagefolio.settings import _save_settings
    _save_settings(self.settings)
    self._invalidate_thumb_cache()
    self._refresh_all()
```

倍率参照は `_get_thumb_photo`（137-139）の `fitz.Matrix(0.22 * z, 0.22 * z)`。**`thumb_zoom_var` という属性名さえ維持されれば、UI 配置変更の影響を一切受けない。** プランナーはこのファイルを変更しない（コールバック／倍率挙動の不変を保証する確認対象）。

---

### `pagefolio/settings.py` (persistence) — 変更不要・真実の源として参照のみ

**Analog:** 自身 defaults（45-65）/ `_SENSITIVE_KEYS`（17-26）

`thumb_zoom` は defaults に明示キーがなく `_on_thumb_zoom_release` 側で `self.settings.get("thumb_zoom", 1.0)` / 直接代入で扱われる（既存挙動）。OCR 数値パラメータ（`ocr_scale` 等 53-57）は既に defaults・LLMConfig 保存経路に存在。**本フェーズで `settings.py` の編集は不要**（単一の真実として参照のみ）。

---

## No Analog Found

なし。全 5 ファイルが既存コードの修正であり、各々に同一リポジトリ内（多くは同一ファイル内）の決定打アナログが存在する。RESEARCH.md フォールバックは不要。

---

## Metadata

**Analog search scope:** `pagefolio/ocr_dialog.py`, `pagefolio/dialogs/llm_config.py`, `pagefolio/ui_builder.py`, `pagefolio/viewer.py`, `pagefolio/settings.py`
**Files scanned:** 5（CONTEXT.md 指定の行範囲を直接 Read）
**Pattern extraction date:** 2026-06-18
