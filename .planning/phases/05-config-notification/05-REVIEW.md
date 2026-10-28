---
phase: 05-config-notification
reviewed: 2026-10-28T06:01:09Z
depth: standard
files_reviewed: 34
files_reviewed_list:
  - .gitattributes
  - README.md
  - distribution/samples/ocr_custom_prompt_sample.md
  - distribution/samples/ocr_summary_prompt_sample.md
  - distribution/はじめに.md
  - docs/CONFIGURATION.md
  - docs/DEVELOPMENT.md
  - pagefolio/constants.py
  - pagefolio/lang.py
  - pagefolio/ocr.py
  - pagefolio/ocr_dialog.py
  - requirements.txt
  - tests/config_notice_support.py
  - tests/conftest.py
  - tests/release_fake_ocr.py
  - tests/release_uat_support.py
  - tests/test_config_notification.py
  - tests/test_gc_barrier_guard.py
  - tests/test_ocr.py
  - tests/test_ocr_dialog_provider_refresh.py
  - tests/test_ocr_local_endpoint.py
  - tests/test_release_build.py
  - tests/test_release_contract.py
  - tests/test_release_uat_support.py
  - tests/test_startup_windows.py
  - tools/build_release.py
  - 開発履歴.md
  - pagefolio/__main__.py
  - pagefolio/startup_win32.py
  - pagefolio/startup_wake.py
  - tests/startup_foreground_audit.py
  - tests/startup_wake_child.py
  - tests/test_startup_foreground_audit.py
  - tests/test_startup_wake.py
findings:
  critical: 1
  warning: 0
  info: 0
  total: 1
status: issues_found
---

# Phase 05: コードレビュー報告

**レビュー日時:** 2026-10-28T06:01:09Z
**深度:** standard
**対象ファイル:** 34
**状態:** issues_found

## Summary

前回レビューの CR-01・CR-02・WR-01 は修正済みの記録と現行の該当経路を照合し、fixed を維持した。追加の設定切替経路に、OCR を `off` にした後もサマリ作成が有効表示になる欠陥を1件検出した。今回の未解決指摘は BLOCKER 1件、WARNING 0件、INFO 0件。

`check evaluation-scope --phase 05 --since 172e993ea61a3b31ffb5a533964481a4dfdb6240 --raw` は `status: degraded`、`reason: no-task-commits-since`、`source: phase-range` を返した。そのため Phase 6 の配布・試験関連まで広がった27ファイルを対象に含め、未コミットで Phase 5 の通知や版記録へ影響する起動経路と試験補助の7ファイルも追加した。前回の21ファイルに関する判定は既存レビューを継承し、現行差分・関連呼出先を重点的に確認した。構造プリパスと外部レビューレーンの指定はない。

## Narrative Findings (AI reviewer)

### CR-03 — BLOCKER: OCR を無効にしても旧プロバイダでサマリを送信できる

**File:** `C:\Users\shdwf\work\project\PageFolio\pagefolio\ocr_dialog.py:1193-1201`、`C:\Users\shdwf\work\project\PageFolio\pagefolio\ocr_dialog.py:813-825`、`C:\Users\shdwf\work\project\PageFolio\pagefolio\ocr_dialog.py:2218-2253`、`C:\Users\shdwf\work\project\PageFolio\pagefolio\ocr_dialog.py:2375-2379`
**Issue:** OCR 完了後、開いたままのダイアログで LLM 設定を `off` にすると、`_apply_llm_settings` は旧 `provider` を保持する。一方、`_update_summary_btn_state` は設定値を確認せず、既存結果と旧 `provider.supports_text_prompt` でサマリボタンを有効にする。`_on_summary` にも `off` の入口ガードがない。旧 LM Studio provider の headless 実メソッド確認では `ocr_provider='off'` でもボタンが `['!disabled']`、cloud 判定が `False` となる。この場合キー確認を通過し、`_summary_worker` が旧 provider の `complete_text_ex(full_text, prompt)` を呼ぶため、無効設定後も OCR 本文を旧接続先へ送信できる。旧 Claude provider ではボタンが有効で表示名も旧 Claude のまま残り、クリック後に `off` の API キー欠落という誤通知を出す。
**Fix:** ボタン状態とサマリ入口の両方で有効設定の `ocr_provider == 'off'` を拒否し、無効時の表示名も設定値を優先する。旧 provider を保持する設計を続ける場合は、無効時にその能力・型を実行可否判定へ使わない。ローカル/クラウド両方で OCR 結果を得てから `off` に切り替える回帰を追加する。

```python
if self.app.settings.get("ocr_provider") == "off":
    self.summary_btn.state(["disabled"])
    return  # _update_summary_btn_state の冒頭

# _on_summary の状態変更・キー確認より前にも同じ off ガードを置く。
```

## 前回指摘の対応継承

| ID | 判定 | 根拠 |
|---|---|---|
| CR-01（BLOCKER） | fixed | `7bbb06c` の内側 Shortcuts 終了時の grab 復元、実 Tk の save/cancel/wm 回帰、利用者 H13 pass。 |
| CR-02（BLOCKER） | fixed | `7bbb06c` の可視時間・FIFO・最小化復帰、利用者 H14 pass。 |
| WR-01（WARNING） | fixed | `2654882` の入力先同一性判定。Entry 以外と None を verified と記録しない。 |

## 検証と限界

- 今回はコード・既存証拠の照合と上記 headless 実メソッド確認を行った。GUI と `pytest` は新規実行していない。
- 親の入力ハッシュ照合で再利用可能と確認された既存の全件試験は `2071 passed / 2 warnings / 480.86s / exit 0`（`.planning/debug/quality-gate-unblock-20261028/full.json`、`full.xml`、`environment.json`）。CR-03 の条件は既存試験で検出されていないため、全件成功を本指摘の解消根拠にはしない。
- 前回の H13/H14 は既存 CR-01/CR-02 の解消根拠であり、新規 CR-03 の確認ではない。Phase 6 の W05b 自動復帰、DEP-05/owner_missing などの未解決条件と出荷停止は本レビューでは解除しない。
- 製品・試験・版・共有状態は変更していない。レビュー記録だけを更新し、commit は行っていない。

---

_Reviewed: 2026-10-28T06:01:09Z_
_Reviewer: gsd-code-reviewer_
_Depth: standard_
