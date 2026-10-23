# Phase 06: サンプル配布とリリース検証 - Pattern Map

**Mapped:** 2026-10-24 JST
**Files analyzed:** 13（ソース・文書の提案新規/変更先。生成ディレクトリと受入証跡は別記）
**Analogs found:** 13 / 13（部分一致を含む。完成済みビルド/実EXE adapterは存在を確認できない）

## File Classification

新規パスは06-RESEARCH.mdの提案であり、確定はplannerが行う。settings.py等は参照接点で、変更を必要条件にしない。

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `distribution/samples/ocr_custom_prompt_sample.md` | config | file-I/O | `dist/PageFolio/ocr_custom_prompt_sample.md` | exact（保存対象そのもの） |
| `distribution/samples/ocr_summary_prompt_sample.md` | config | file-I/O | `dist/PageFolio/ocr_summary_prompt_sample.md` | exact（保存対象そのもの） |
| `distribution/はじめに.md` | utility（文書） | transform | `docs/CONFIGURATION.md` | role-match |
| `tools/build_release.py` | utility | batch / file-I/O | `pagefolio/settings.py` | partial（所有一時ファイルと失敗処理のみ） |
| `tests/test_release_build.py` | test | file-I/O | `tests/conftest.py` | role-match |
| `tests/test_release_contract.py` | test | transform | `tests/test_gsd_dod.py` | exact（静的文書契約） |
| `tests/release_uat_support.py` | utility | event-driven / file-I/O | `tests/test_startup_windows.py` | partial（Python harnessのみ） |
| `pagefolio/constants.py` | config | transform | 同ファイル | exact |
| `README.md` | utility（文書） | transform | `docs/CONFIGURATION.md` | role-match |
| `開発履歴.md` | utility（文書） | transform | 同ファイル | role-match（構成は実装時に確認） |
| `docs/DEVELOPMENT.md` | utility（文書） | transform | 同ファイル | exact |
| `docs/CONFIGURATION.md` | utility（文書） | transform | 同ファイル | exact |
| `.gitignore` | config | file-I/O | 同ファイル | exact |

主要コードanalogは5本に限定：settings.py、conftest.py、test_gsd_dod.py、test_startup_windows.py、config_notice_support.py。上表の文書・定数・サンプルも含め、列挙した既存パスはすべて `git ls-files -- <path>` の出力で追跡を確認した。ignoreされたruntime mirrorは参照しない。

## Pattern Assignments

### サンプル正本2ファイル（config, file-I/O）

**Analog:** 同名の `dist/PageFolio/` 追跡ファイル。内容編集・移動ではなくバイトコピーする。

- OCR原本1行目: `画像から読み取れるすべてのテキストを、欠落させることなく正確に文字起こししてください。`
- サマリ原本1行目: `# OCRテキスト解析・清書プロンプト（PageFolio）`

抜粋から再構築しない。元→新正本→初回配布→再配布で全文のbytes/SHA-256を照合し、元を保持する。コピーAPIのコード例は `tests/test_startup_windows.py:76-82`：

```python
        shutil.copytree(
            _ROOT / "pagefolio",
            fixture / "alternate" / "pagefolio",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        shutil.copyfile(_ROOT / "pagefolio.py", fixture / "alternate" / "pagefolio.py")
```

ignore条件はPythonコピー用であり、配布正本へ盲目的にコピーしない。既存先衝突時に停止する検査は新設する。

### tools/build_release.py（utility, batch / file-I/O）

**Analog:** `pagefolio/settings.py:366-388`。所有権を取得できた一時ファイルだけを操作し、例外種別・errnoを記録するパターンを部分再利用する。

```python
        tmp_path = path + ".tmp"
        with open(tmp_path, "x", encoding="utf-8") as f:
            owned_tmp = True
            json.dump(to_save, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return True
    except Exception as e:
        logger.debug(
            "設定ファイル保存失敗: %s errno=%s",
            type(e).__name__,
            getattr(e, "errno", None),
        )
```

**差分:** 配布CLIでは失敗生成物の削除をコピーしない。単一ファイルのreplaceを複数directory renameのatomic性根拠にしない。preflight、link/junction拒否、所有出力lock、公開前再確認、history保持、rollback、非zero終了、レポート失敗時の扱いはRESEARCH Pattern 2/4に基づき新規設計する。

**imports/実行:** 標準ライブラリを先頭、プロジェクト依存を後に置く。既存 `tests/config_notice_support.py:3-12` は `hashlib/json/Path` → `pagefolio.*` の順。buildは製品Appをimport/起動せず、ASTで定数を読む案を具体化する。

**固定argv:** `tests/test_startup_windows.py:84-103` の引数列＋stdout/stderrファイル＋`CREATE_NO_WINDOW` を参考にする。既存コードにPyInstaller runnerはない。検証済みPythonに `-m PyInstaller` と私有work/spec/distを渡す設計・fake builder境界が必要。

### tests/test_release_build.py（test, file-I/O）

**Analog:** `tests/conftest.py:14-25`。実ディスクに隔離ファイルを作る。

```python
@pytest.fixture()
def tmp_settings(tmp_path):
    """一時ディレクトリに設定ファイルを作成・管理するフィクスチャ。
    返り値は (settings_path, write_fn) のタプル。
    write_fn(data) で設定を書き込む。
    """
    settings_path = tmp_path / "pagefolio_settings.json"

    def write_fn(data):
        settings_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    return settings_path, write_fn
```

fake builderを注入し、保護対象がある場合の「builder未呼出し」＋前後bytes不変を検査する。初回/再ビルド、未知ファイル、同名directory/broken link、同梱欠落/hash不一致、builder失敗、report失敗、公開途中失敗、同時実行を対象にする。fixtureの成功が実EXE受入成功になることはない。

**故障注入analog:** `tests/config_notice_support.py:114-117`：

```python
    def _replace(self, source, target, *args, **kwargs):
        if self.fault_enabled and Path(target).resolve() == self.settings_path:
            raise PermissionError(13, "isolated replace fault")
        return self._original_replace(source, target, *args, **kwargs)
```

対象パスに限定する。製品の設定保存や実利用directory全体のACLを変更しない。

### tests/test_release_contract.py（test, transform）

**Analog:** `tests/test_gsd_dod.py:42-47,61-62,100-104`。

```python
from __future__ import annotations

import re
from pathlib import Path

import pytest
```

```python
def _repo_root() -> Path:
    return Path(__file__).parent.parent
```

```python
def _read_validation_status(path: Path) -> str | None:
    frontmatter = _extract_frontmatter(path.read_text(encoding="utf-8"))
    if frontmatter is None:
        return None
    return _read_status(frontmatter)
```

既存文書をread-onlyで検査し、欠落と未完了を成功扱いしない。版のAST読取、README/履歴との一致、ガイド参照の到達性、正本とコピーの一致、W全枝番とWR-01の割当を対象にする。DoDを通すために未完了Phaseのfrontmatterをvalidatedへ変更しない。新たな一般YAML依存は不要。

### tests/release_uat_support.py（utility, event-driven / file-I/O）

**Analog:** `tests/test_startup_windows.py` の明示CLIと記録、`tests/config_notice_support.py` の原本保護。

**CLI範囲**（2752-2758,2778-2783）：

```python
    parser.add_argument(
        "--entry", choices=["script", "module", "relocated"], default="module"
    )
```

現状に `--entry exe` はない。通常pytestから人手待ちを分離する原則は継承する。実EXEは配布ツリー完全コピー＋hash固定＋外部PID/window/foreground/時刻観測で作る。Python monkeypatch、製品App継承、fixtureのstopファイルがfrozen製品へ届くとは仮定しない。専用製品CLI追加も要求しない。

**runと記録**（2801-2804,2842-2855）：

```python
            run = Path(
                tempfile.mkdtemp(
                    prefix="pagefolio-uat-", dir=_ROOT / ".planning" / "tmp"
                )
            )
```

```python
            manifest = {
                "run": str(run),
                "namespace": namespace,
                "case": args.case,
                "role": role,
                "fixture": str(fixture),
                "launcher_pid": child.pid,
                "environment": environment,
                "originals_before": before,
                "source_commit": subprocess.check_output(  # noqa: S603
                    [git_executable, "rev-parse", "HEAD"], cwd=_ROOT, text=True
                ).strip(),
            }
            save(run / "manifest.json", manifest)
```

environmentの収集例は2815-2833：OS、Python、pointer_bits、session_id、sid、authentication_luid、foreground、is_admin、Tcl/Tk。新adapterではEXE hash・入口・dirty差分hash・観測時刻・判定種別を追加し、ケースIDと結ぶ。observerのPython/Tk版をEXE内蔵版として記録しない。

**失敗診断**（172-179）：

```python
def _finish(child, timeout=_FINISH_TIMEOUT):
    try:
        out, err = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # killより前に証拠を採る。killすると生存/保持の区別が消える。
        exited = child.poll() is not None
        report = _stall_report(child)
        child.kill()
```

この例は所有Popenのみ。実EXEの回収は所有PIDと生成時刻等を照合し、無関係processを名前だけで停止しない。再発時に期限延長や除外を追加せず、初回失敗を保持して親workflowを止める。

### 文書・定数・ignoreの変更先

- `pagefolio/constants.py:12,15,21-22`：`APP_VERSION = "v1.9.1"`、`SETTINGS_FILE = "pagefolio_settings.json"`、`CUSTOM_PROMPT_FILE = "ocr_custom_prompt.md"`、`SUMMARY_PROMPT_FILE = "ocr_summary_prompt.md"`。版のみ承認済みv1.10.0へ同期、名前は保護対象定義として利用する。
- `distribution/はじめに.md` / `README.md` / `docs/CONFIGURATION.md`：現存 `docs/CONFIGURATION.md:116-121` の表形式を参考に、OCR/サマリを別々に説明する。117行の「PyInstaller ビルド後は .exe と同じ場所」、120行の「ファイルが存在する場合のみ、入力欄の内容をファイルへ書き戻す」を保持。新ガイドはサンプルからコピー、衝突時停止、旧版保持、外部編集、Apply連動を短く記し、配布物から到達する詳細リンクを用意する。
- `docs/DEVELOPMENT.md:65-103`：現行ビルド節を専用CLIへ更新。70行の `pyinstaller --onedir --noconsole --icon=pagefolio.ico --name=PageFolio pagefolio.py` が維持する基本構成。85-103行の退避→破壊的再生成→復元は解消対象であり安全パターンとしてコピーしない。
- `開発履歴.md`：既存追跡文書。最新節の構成・位置は今回未抽出のため、実装担当が読んでv1.10.0の変更と保証制約を追記する。未完了実機項目を成功と書かない。
- `.gitignore:68-74`：`PageFolio-*.zip.sha256`、`PageFolio-*.zip`、`dist/` が存在。既追跡distはignoreだけでは追跡解除されない。新規生成先の方針を限定して決め、旧配布物削除や全dist stageをしない。

## Shared Patterns

### 原本保護と機密を含めないhash記録

**Source:** `tests/config_notice_support.py:31-38`
**Apply to:** buildの非破壊性試験、EXE adapter、ケース証跡

```python
    for name, path in files.items():
        result[name] = {
            "exists": path.exists(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
            if path.is_file()
            else None,
        }
    return result
```

同ファイル163-164行の原本不変判定：

```python
        if self.originals_before != self.originals_after:
            raise AssertionError("隔離前後で利用者ファイルが変化した")
```

existence/hashは観測用。broken linkの衝突検知をこのexists式だけに任せない。アプリの明示Apply/正常終了の正当な保存と、起動/配布による無断上書きは別の時点で評価する。

### JSONレポート

**Source:** `tests/test_startup_windows.py:2790-2793`
**Apply to:** build report / EXE UAT manifest

```python
    def save(path, value):
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )
```

UTF-8・日本語可読性を再利用。production用レポートでは書込エラーを成功にしない追加制御が必要。設定本文・APIキー・環境全dumpを記録しない。ビルド成功/自動検査/故障注入/実機pass/not-runを別フィールドにする。

### guardとエラー

Web認証は該当なし。ビルドの出力所有権・保護ファイル検査、UATの所有PIDがguardとなる。既存 `settings.py:316-320,383-388` の例外種別/errnoによる記録を参考にする。失敗物を保持し、元の例外を診断失敗で隠さない。

## No Analog Found

| File / 領域 | Role | Data Flow | Reason |
|---|---|---|---|
| tools/build_release.pyのpreflight→staging→publish全体 | utility | batch / file-I/O | 既存の安全な配布pipelineなし。部分I/Oのみ再利用可能 |
| tests/release_uat_support.pyのfrozen adapter | utility | event-driven | 現harnessはPython入口のみ。製品外の観測と障害準備を設計する必要あり |
| tests/test_release_build.pyのfake builder | test | batch | 既存fixtureはあるがPyInstaller runnerの注入契約は新規 |
| tests/test_release_contract.pyのAST版読取 | test | transform | 今回選んだanalogにAST版番号読取はない。RESEARCHの案を具体化 |
| case別の実EXE fake OCR/障害fixture | utility | request-response / event-driven | loopback等は研究上の案。実接続方法の完成は未確認 |

## 生成物・受入証跡の割当

- `dist/.release-work/<run-id>/`、`dist/PageFolio-<APP_VERSION>/`、`dist/.release-history/<run-id>/` は生成物（file-I/O）。コードanalogではない。private run保持は上記mkdtempを参考にし、成功前の公開・失敗cleanupを避ける。
- Phase06 UAT/VALIDATION/EVIDENCE等はconfig相当の証跡（transform）。具体名は計画で確定。06-UAT-CARRYOVER.mdの全ID/枝番を入力として割り当てる。今回この証跡群を新規作成・変更していない。
- Phase4 stale再検証は親workflowの依存。既存H01〜H14/意味評価2件の無理由再実施は組まない。未準備W11、WR-01時間超過履歴、未解除回帰を残す。

## Metadata

**Analog search scope:** tracked tests/、pagefolio/settings.py・constants.py、docs/、distの既存2サンプル、.gitignore
**主要コードanalog:** 5
**Pattern extraction date:** 2026-10-24 JST
**実施範囲:** 読取・git追跡確認と本書作成のみ。実装・ビルド・pytest・実機UAT・commitは未実施。
