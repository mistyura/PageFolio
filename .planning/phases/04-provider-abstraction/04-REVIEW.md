---
phase: 04-provider-abstraction
reviewed: 2026-06-06T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - pagefolio/ocr_dialog.py
  - pagefolio/ocr.py
  - pagefolio/lang.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 4: コードレビュー報告（ギャップ修正 04-04 再レビュー）

**レビュー日時:** 2026-06-06
**深度:** standard
**レビュー対象ファイル数:** 3
**ステータス:** issues_found

## サマリー

Phase 4 ギャップ修正プラン 04-04（commits aea0e9c / 4fe9f45 / ce4c9b4）の差分を中心に standard 深度でレビューした。対象は 2 つの検証ギャップ修正:

- **CR-02:** `_on_run`（`ocr_dialog.py`）がダイアログ UI の live 値で `self.provider` を `LMStudioProvider` として再生成し、v1.3.0 の後方互換を復元。
- **CR-01:** `_start_ocr`（`ocr.py`）が `build_provider` を `try/except ValueError` でガードし、未対応プロバイダ設定時に `messagebox.showerror` + `return`。

検証した良好な点:

- **lang.py のキー parity は完全**: ja / en ともに 233 キーで一致（実測確認）。`ocr_provider_unsupported` も両言語に追加済み。
- **裸の except 不使用**: 追加された `except` 句はすべて `except ValueError as e:` / `except (tk.TclError, ValueError):` の明示形でプロジェクト規約に準拠。
- **スレッド境界の保全**: CR-02 の再生成は `_on_run`（メインスレッド）内で完結し、`fitz` / `get_pixmap` / `self.doc[...]` の参照を含まない。`_worker` への漏洩はない。
- **Python 3.8 互換**: 非互換構文（walrus・`match` 等）は未使用。
- **入力クランプ**: `max_tokens`（-1〜MAX_OCR_MAX_TOKENS）・`temperature`（0.0〜2.0）はクランプ済み。timeout は `_effective_timeout`（10〜600 クランプ済み）が再生成プロバイダに正しく伝播。

BLOCKER は検出されなかったが、Phase 4 のテーマ「プロバイダ抽象化」と整合しない設計上の潜在欠陥を 3 件検出した。いずれも Phase 4（LMStudio 単独）では顕在化しないが、Phase 5/6/7 でプロバイダが増えた瞬間にバグ化する。

## Warnings

### WR-01: `_on_run` がプロバイダ種別を無視して常に LMStudioProvider に上書きする

**File:** `pagefolio/ocr_dialog.py:481-489`
**Issue:**
CR-02 の再生成は `self.provider` を無条件に `LMStudioProvider` で置き換える。`_start_ocr`（`ocr.py:242`）は `build_provider(self.settings)` でプロバイダ種別を解決して `OCRDialog` に渡しているが、`_on_run` がその結果を破棄して LMStudio を固定で再構築する。そのため Phase 5/6/7 で `claude` / `gemini` / `tesseract` プロバイダが追加された瞬間に、ダイアログで「読み取り実行」を押すと選択プロバイダが LMStudio にすり替わる。Phase 4 のコアバリュー（プロバイダ抽象化）を `_on_run` が境界を貫通する形で直接破っている。Phase 4 では LMStudio 単独のため現時点では誤動作しないが、抽象化の境界をハードコードで無効化している点は明確な設計欠陥。

**Fix:**
プロバイダ種別を保持したまま live 値だけを反映する。LMStudio のときだけ属性更新（または再構築）に留める。

```python
from pagefolio.ocr_providers import LMStudioProvider

if self.provider is None or isinstance(self.provider, LMStudioProvider):
    self.provider = LMStudioProvider(
        url=url, model=model, timeout=self._effective_timeout,
        max_tokens=max_tokens, temperature=temperature,
    )
else:
    # 非 LMStudio プロバイダの live 値反映方針を別途定義する
    ...
```

### WR-02: `url` / `model` の TclError フォールバックが到達不能なデッドコードで誤った安心感を与える

**File:** `pagefolio/ocr_dialog.py:461-468`
**Issue:**
`url_var` / `model_var` は `tk.StringVar` であり、`StringVar.get()` は `tk.TclError` も `ValueError` も送出しない（常に str を返す）。したがって `except (tk.TclError, ValueError)` のフォールバック分岐（`getattr(self.provider, "url", "")` 等）は到達不能なデッドコードであり、「壊れた入力に対して安全」という誤った印象を与える。さらに URL Entry は `state="readonly"`（`ocr_dialog.py:165`）でダイアログ上の `url_var` は編集不可なので、`url` の live 取得は常に初期 URL と同値。実質 live なのは `model` のみで、設計意図（live 値反映）とコードの実態が乖離している。

**Fix:**
StringVar 由来の `url` / `model` は例外フォールバックを削除して意図を明確化する。URL を本当に live 編集させたい意図なら Entry の `readonly` を見直す。少なくともデッドな except 分岐は除去する。

```python
url = self.url_var.get().strip()
model = self.model_var.get().strip()
```

### WR-03: `OCRAPIKeyError` がページ単位エラー（`err`）として全ページ分繰り返され、致命的として扱われない

**File:** `pagefolio/ocr.py:140-141`（`run_parallel._call`）
**Issue:**
`ocr_providers.py` の `OCRAPIKeyError` は `RuntimeError` のサブクラス。`run_parallel._call` は `except RuntimeError` を `"err"`（ページ単位エラー）に分類するため、API キー未設定のクラウドプロバイダでは全ページが個別に同じ「キー未設定」エラーで失敗し、致命的エラー（`fatal`）として早期中断されない。Phase 4 は LMStudio（キー不要）のみのため未顕在だが、Phase 5（claude/gemini）でプロバイダ抽象が活きた瞬間に、無駄な並列リクエストとノイジーなページ別エラーを生む。CR-01/CR-02 が触れた OCR 実行経路の直近にある潜在欠陥。

**Fix:**
`run_parallel._call` で `OCRAPIKeyError` を `RuntimeError` より前に捕捉し、専用の fatal 種別として 1 回で中断する分岐を追加する。

```python
from pagefolio.ocr_providers import OCRAPIKeyError
...
except OCRAPIKeyError as e:
    return ("fatal_apikey", page_idx, str(e))
except RuntimeError as e:
    return ("err", page_idx, str(e))
```

## Info

### IN-01: CR-01 のエラーメッセージが空文字 `name` を可読化していない

**File:** `pagefolio/ocr.py:244`
**Issue:**
`name = self.settings.get("ocr_provider", "")` は未設定時に空文字を返す。`build_provider`（`ocr.py:195`）は `name in ("lmstudio", "", "off")` を正常系として扱うため空文字で `ValueError` に到達することはなく実害はないが、将来 `ocr_provider` キー自体が欠落した不正設定で例外経路に入った場合、`ocr_provider_unsupported` が「...設定されています: （空欄）」と表示されユーザーに状況が伝わりにくい。

**Fix:**
`name = self.settings.get("ocr_provider") or "(未設定)"` のように空文字を可読化する。現状の正常系扱いを維持するなら情報として記録に留める。

### IN-02: `LMStudioProvider` の関数内 import が 2 箇所に分散している

**File:** `pagefolio/ocr_dialog.py:481`, `pagefolio/ocr.py:191`
**Issue:**
`LMStudioProvider` の import が `build_provider`（`ocr.py:191`）と `_on_run`（`ocr_dialog.py:481`）の 2 箇所で関数内 import されている。循環 import 回避の理由はコメントで説明されているが、WR-01 の修正（`build_provider` への一本化）と合わせれば `_on_run` 側の直接 import を解消でき、プロバイダ生成ロジックの単一責務化につながる。

**Fix:**
WR-01 を `build_provider` 経由の再構築に統一すれば、`_on_run` からの直接 `LMStudioProvider` import は不要になる。

---

_レビュー日時: 2026-06-06_
_レビュアー: Claude (gsd-code-reviewer)_
_深度: standard_
