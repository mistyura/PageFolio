# W12c pass 2行の環境欄補正（2026-11-09）

## 事象

全件 pytest で `tests/test_release_contract.py::TestCaseCoverage` の2件が失敗した。台帳構造監査（`tests/release_uat_support.py`）は pass 行の `environment` に `os`・`elevated`・`session_id` を要求するが、`06-05-record-w12c.cjs` は run manifest の environment をそのまま転記し、`elevated` を書かない（`is_admin` のみ）。W12a/W12b の recorder は `elevated` を書いており、W12c だけの欠落。

## 補正（利用者承認: 案1、2026-11-09）

`06-MANUAL-EVIDENCE.json` の次の2行の `environment` に `"elevated": false` を追記した。値は各 run の `manifest.json` の `environment.is_admin`（いずれも `false`）から取った。他の欄・他の行は変更していない。

| 行 | run | 根拠 |
|---|---|---|
| W12c/explorer-python@script | pagefolio-uat-44b37ad5f04c4048bdcfcf605cc6976e | manifest.json environment.is_admin=false |
| W12c/terminal-python@script | pagefolio-uat-74bdbdeb60cf415d9edc8c16e4c6f2ce | manifest.json environment.is_admin=false |

## 未対応

- `06-05-record-w12c.cjs` 自体は作業tree凍結中のため未修正。凍結解除時に `elevated` を書くよう修正すること（修正しないと同recorderで新たに記録する行が再び監査で拒否される）。
