---
estimated_steps: 14
estimated_files: 4
skills_used: []
---

# T06: ruff + pytest で全件確認（リグレッションなし・108件以上 PASSED）

T01〜T05 のすべての変更後、リント・フォーマット・テストの全チェックを実行して S03 の完成を確認する。エラーがあれば修正する。

**実行するコマンド:**
```bash
ruff check . && ruff format --check .
pytest --tb=short -q
```

**よくある修正パターン:**
- `ruff` が `E501`（行長超過）を検出した場合: 長い行を分割する
- `ruff` が `F841`（未使用変数）を検出した場合: 変数名を `_` に変更するか削除
- `pytest` でテストが失敗した場合: エラーメッセージを確認し、T01〜T05 の実装と照合して修正

**制約:**
- `pyproject.toml` / `ruff.toml` は編集禁止
- 裸の `except:` 句は禁止（`except Exception as e:` の形で）
- テスト件数は 108 件以上であること（S02 完了時点で 108 件）

## Inputs

- `pagefolio/file_ops.py`
- `pagefolio/page_ops.py`
- `pagefolio/dnd.py`
- `tests/test_pdf_ops.py`

## Expected Output

- `pagefolio/file_ops.py`
- `pagefolio/page_ops.py`
- `pagefolio/dnd.py`
- `tests/test_pdf_ops.py`

## Verification

ruff check . && ruff format --check . && pytest --tb=short -q
