"""フェーズ完了 DoD の機械ゲート — quick 260812-and

`.planning/` 配下のフェーズディレクトリのうち適用範囲（v1.9.0 以降）に入るものは
すべて、対応する `*-VALIDATION.md` の frontmatter が `status: validated` である
ことを `pytest` で常時検証する。

根拠:
    - .planning/PROJECT.md 「## フェーズ完了 DoD」節
    - 姉妹プロジェクト loto の tests/test_gsd_dod.py（同じ思想の先行実装）
    - 「ドキュメントに書いてあるだけでは実行されない」— loto は v0.17.0 で
      6 フェーズ全てに /gsd-validate-phase が走らないまま milestone close まで
      進み、audit の段階で初めて発覚した。同じ運用ギャップを PageFolio でも
      防ぐため、pytest が自動収集する強制点を置く。

loto 実装との設計差分（PageFolio 固有の事情で走査の入口を変えている）:
    (1) 走査の入口が ROADMAP ではなくフェーズディレクトリの列挙である。
        loto は `.planning/ROADMAP.md` の `## Progress` 進捗表から
        Status=Complete の行を拾うが、PageFolio の `## Progress` は
        マイルストーン単位の表であり `Phase` 列を持たない。
    (2) PageFolio はフェーズ番号をマイルストーンごとに 1 起点へリセットする
        （プロジェクト方針）。`03-*` は v1.6.0 / v1.7.1 / v1.8.0 / v1.9.0 の
        4 箇所に存在するため、番号からディレクトリを一意に解決できない。
        ディレクトリ列挙を入口にすることでこの曖昧性が構造的に消える。
    (3) PyYAML に依存しない。PageFolio の requirements.txt に PyYAML は無く、
        本ゲートが読むのは frontmatter の `status` スカラー 1 個だけなので
        最小パーサを自前で持ち、テストのために実行依存を増やさない。

適用範囲を v1.9.0 以降に限る理由:
    v1.9.0 未満のアーカイブ済みマイルストーンの `*-VALIDATION.md` は
    `/gsd-validate-phase` の出力ではなく別種のドキュメントで、status 語彙も
    `approved` / `ready` / `draft` / `planned` / `complete` と揃っていない
    （欠落しているフェーズもある）。遡及的な生成・修正は行わない方針のため
    （loto の「v0.17.0 以前への遡及生成は見送り確定」と同じ判断）、適用範囲を
    v1.9.0 以降に限定する。ただし「除外すれば通る」抜け穴にしないため、
    除外対象の集合そのものを `test_legacy_exclusions_match_repository` で
    機械固定し、黙って増えないようにしている。

実行特性: リポジトリ内ファイルの読み取りのみで共有可変状態を持たない。
並列実行しても他テストと競合せず、実行時間は秒未満である。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# 本ゲートを適用する最小マイルストーンバージョン。
MIN_APPLICABLE_VERSION = (1, 9, 0)

# 適用範囲外として意図的に除外しているアーカイブ済みマイルストーン。
# この集合は test_legacy_exclusions_match_repository が実ディレクトリと
# 突き合わせるため、黙って増やすことはできない。
LEGACY_EXCLUDED_MILESTONES = frozenset({"v1.4.0", "v1.6.0", "v1.7.1", "v1.8.0"})

_MILESTONE_DIR_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)-phases$")
_STATUS_LINE_RE = re.compile(r"^status:\s*(.*?)\s*$")


def _repo_root() -> Path:
    return Path(__file__).parent.parent


def _extract_frontmatter(text: str) -> str | None:
    """Markdown 本文手前の `---` 区切り frontmatter ブロックのみを切り出す.

    VALIDATION.md の本文は Markdown であり全文を読めないため切り出しを先に行う。
    ブロックが無ければ None を返す。
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return None


def _read_status(frontmatter: str) -> str | None:
    """frontmatter からトップレベルの `status` スカラーを読む.

    PyYAML に依存しないための最小パーサ。トップレベル（インデント 0）の
    `status:` 行のみを対象とし、ネストしたマッピング内の `status:` は
    拾わない。値の前後のクォートは剥がす。キーが無ければ None。
    """
    for line in frontmatter.splitlines():
        if line[:1].isspace():
            continue
        match = _STATUS_LINE_RE.match(line)
        if not match:
            continue
        value = match.group(1)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value or None
    return None


def _read_validation_status(path: Path) -> str | None:
    frontmatter = _extract_frontmatter(path.read_text(encoding="utf-8"))
    if frontmatter is None:
        return None
    return _read_status(frontmatter)


def _milestone_version(dir_name: str) -> tuple[int, int, int] | None:
    """`v1.9.0-phases` → `(1, 9, 0)`. 形式に合わなければ None."""
    match = _MILESTONE_DIR_RE.match(dir_name)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _collect_phase_dirs(repo_root: Path) -> list[Path]:
    """適用範囲に入るフェーズディレクトリを昇順で返す.

    対象は (a) ライブの `.planning/phases/*/` すべてと、
    (b) `.planning/milestones/v{X.Y.Z}-phases/*/` のうちバージョンが
    MIN_APPLICABLE_VERSION 以上のもの。

    `.planning/milestones/` 直下（`v*-phases/` の階層を挟まない配置）は
    走査対象外。GSD のアーカイブ規約に沿わない配置物を拾わないための
    構造的な絞り込みで、self-test がこの境界を固定している。
    """
    planning_dir = repo_root / ".planning"
    dirs: list[Path] = []

    live_root = planning_dir / "phases"
    if live_root.is_dir():
        dirs.extend(p for p in live_root.iterdir() if p.is_dir())

    milestones_root = planning_dir / "milestones"
    if milestones_root.is_dir():
        for milestone_dir in milestones_root.iterdir():
            if not milestone_dir.is_dir():
                continue
            version = _milestone_version(milestone_dir.name)
            if version is None or version < MIN_APPLICABLE_VERSION:
                continue
            dirs.extend(p for p in milestone_dir.iterdir() if p.is_dir())

    return sorted(dirs)


def _read_live_phase_completion(
    repo_root: Path, phase_dir: Path
) -> tuple[bool, str | None]:
    """現行のPhase行・詳細・進捗を照合する。履歴detailsとPlan行は対象外。"""
    roadmap = repo_root / ".planning" / "ROADMAP.md"
    if not roadmap.is_file():
        return False, "判定不能: ROADMAP.md が存在しない"
    text = re.sub(
        r"<details\b[^>]*>.*?</details>",
        "",
        roadmap.read_text(encoding="utf-8"),
        flags=re.DOTALL | re.IGNORECASE,
    )
    number = str(int(phase_dir.name.split("-", 1)[0]))
    sections = {}
    section = ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        sections.setdefault(section, []).append(line)
    phase_re = re.compile(r"^- \[([ xX])\]\s+(?:\*\*)?Phase\s+(\d+):\s*(.*)")
    phases = [
        m
        for line in sections.get("Phases", [])
        if (m := phase_re.match(line)) and str(int(m[2])) == number
    ]
    details = [
        line
        for line in sections.get("Phase Details", [])
        if re.match(rf"^### Phase 0*{number}:\s", line)
    ]
    if len(phases) != 1 or len(details) != 1:
        return False, "判定不能: 現行Phase行またはPhase Detailsが欠落・重複"
    phase_title = phases[0][3].split("**", 1)[0].strip()
    detail_title = details[0].split(":", 1)[1].strip()
    if phase_title != detail_title:
        return False, "判定不能: Phase行とPhase Detailsの名称が不一致"
    rows = []
    in_table = False
    for line in sections.get("Progress", []):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.startswith("|"):
            in_table = False
            continue
        if cells == ["Phase", "Plans Complete", "Status", "Completed"]:
            in_table = True
            continue
        if in_table and len(cells) == 4 and re.match(rf"^0*{number}\.\s", cells[0]):
            rows.append(cells)
    if len(rows) != 1:
        return False, "判定不能: Phase進捗が欠落・重複"
    _, count, status, date = rows[0]
    status = status.removeprefix("✅ ")
    if status not in {"Planned", "Not started", "In Progress", "Complete"}:
        return False, "判定不能: 未解釈の進捗状態"
    checked = phases[0][1].lower() == "x"
    if status == "Complete":
        plans = sorted(phase_dir.glob("*-PLAN.md"))
        summaries = sorted(phase_dir.glob("*-SUMMARY.md"))
        expected = {p.name.replace("-PLAN.md", "-SUMMARY.md") for p in plans}
        if (
            not plans
            or {p.name for p in summaries} != expected
            or count != f"{len(plans)}/{len(plans)}"
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)
        ):
            return False, "判定不能: CompleteのSUMMARY・件数・完了日が不整合"
        return checked, None
    if checked:
        return False, "判定不能: 完了Phase行と未完了Progressが矛盾"
    if not re.fullmatch(r"\d+/(?:\d+|TBD)", count) or date != "—":
        return False, "判定不能: 未完了Progressの件数・完了日が不整合"
    return False, None


def _collect_dod_violations(repo_root: Path) -> list[tuple[str, str]]:
    """適用範囲の各フェーズを走査し、違反を `(識別子, 理由)` のリストで返す.

    最初の 1 件で早期 return せず全件を走査しきる。違反として扱うのは
    (a) `*-VALIDATION.md` がちょうど 1 件でない、(b) frontmatter の `status`
    が `validated` でない、の 2 種。`nyquist_compliant` は一切参照しない
    — 本ゲートが強制するのは「検証を走らせたこと」であり、ギャップをゼロに
    することではない。
    """
    violations: list[tuple[str, str]] = []
    for phase_dir in _collect_phase_dirs(repo_root):
        label = f"{phase_dir.parent.name}/{phase_dir.name}"
        if phase_dir.parent.name == "phases":
            complete, error = _read_live_phase_completion(repo_root, phase_dir)
            if error:
                violations.append((label, error))
                continue
            if not complete:
                continue
        validation_files = sorted(phase_dir.glob("*-VALIDATION.md"))

        if len(validation_files) != 1:
            violations.append(
                (
                    label,
                    f"*-VALIDATION.md が {len(validation_files)} 件 (期待 1 件)。"
                    "/gsd-validate-phase を実走して NN-VALIDATION.md を"
                    "生成すれば解消する",
                )
            )
            continue

        status = _read_validation_status(validation_files[0])
        if status != "validated":
            violations.append(
                (
                    label,
                    f"{validation_files[0].name} の frontmatter status は "
                    f"{status!r} (期待 'validated')。/gsd-validate-phase を"
                    "実走して status: validated へ昇格させれば解消する",
                )
            )

    return sorted(violations)


def test_completed_phases_are_validated() -> None:
    """適用範囲の全フェーズが `status: validated` であることを保証する.

    走査件数が 0 でないことも合わせて assert する。将来ディレクトリ構造が
    変わって走査が 0 件に落ちたとき、ゲートが黙って通ることを防ぐ最後の
    防護である（空虚 PASS 防止）。
    """
    repo_root = _repo_root()
    phase_dirs = _collect_phase_dirs(repo_root)
    assert phase_dirs, (
        "DoD ゲート走査 0 件 (空虚 PASS の疑い): 適用範囲のフェーズ"
        "ディレクトリを 1 件も発見できなかった。.planning/phases/ および "
        ".planning/milestones/v*-phases/ の配置が変わっていないか確認せよ"
    )

    violations = _collect_dod_violations(repo_root)
    assert not violations, "DoD 違反を検出:\n" + "\n".join(
        f"- {label}: {reason}" for label, reason in violations
    )


def test_legacy_exclusions_match_repository() -> None:
    """適用範囲外としているマイルストーンの集合が実リポジトリと一致すること.

    「除外すれば通る」抜け穴を塞ぐためのガード。新しいマイルストーンが
    MIN_APPLICABLE_VERSION 未満の版番で現れた場合や、LEGACY_EXCLUDED_MILESTONES
    が実態と乖離した場合に FAIL する。除外を増やしたいときは必ずこの
    定数を明示的に書き換える必要がある。
    """
    milestones_root = _repo_root() / ".planning" / "milestones"
    actual_excluded = set()
    actual_included = set()
    for milestone_dir in milestones_root.iterdir():
        if not milestone_dir.is_dir():
            continue
        version = _milestone_version(milestone_dir.name)
        if version is None:
            continue
        name = milestone_dir.name.removesuffix("-phases")
        if version < MIN_APPLICABLE_VERSION:
            actual_excluded.add(name)
        else:
            actual_included.add(name)

    assert actual_excluded == set(LEGACY_EXCLUDED_MILESTONES), (
        "適用範囲外のマイルストーン集合が LEGACY_EXCLUDED_MILESTONES と一致しない。"
        f"実際: {sorted(actual_excluded)} / "
        f"定数: {sorted(LEGACY_EXCLUDED_MILESTONES)}。"
        "除外を増やす場合は定数を明示的に更新し、根拠を PROJECT.md "
        "「## フェーズ完了 DoD」節へ記録すること"
    )
    assert actual_included, (
        "適用範囲に入るアーカイブ済みマイルストーンが 0 件 (空虚 PASS の疑い)"
    )


# ---------------------------------------------------------------------------
# 非空虚 self-test — 実リポジトリに依存しない合成ツリーで検知能力を機械証明する
# ---------------------------------------------------------------------------

_VALIDATED = "---\nstatus: validated\nnyquist_compliant: false\n---\n\n# Validation\n"
_DRAFT = "---\nstatus: draft\nnyquist_compliant: true\n---\n\n# Validation\n"


def _build_synthetic_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    """`.planning/` からの相対パス → 内容 の dict から合成ツリーを組み立てる."""
    planning_dir = tmp_path / ".planning"
    for rel_path, content in files.items():
        target = planning_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return tmp_path


def test_dod_gate_detects_unvalidated_phase(tmp_path: Path) -> None:
    """draft を検知し validated を誤検知しないこと、範囲外を走査しないことを固定する."""
    # 検知する側
    repo = _build_synthetic_repo(
        tmp_path / "draft",
        {"milestones/v1.9.0-phases/01-alpha/01-VALIDATION.md": _DRAFT},
    )
    violations = _collect_dod_violations(repo)
    assert [v[0] for v in violations] == ["v1.9.0-phases/01-alpha"]
    assert "'draft'" in violations[0][1]

    # 誤検知しない側
    repo = _build_synthetic_repo(
        tmp_path / "validated",
        {"milestones/v1.9.0-phases/01-alpha/01-VALIDATION.md": _VALIDATED},
    )
    assert _collect_dod_violations(repo) == []

    # 適用範囲外 (v1.9.0 未満) は draft でも走査されない
    repo = _build_synthetic_repo(
        tmp_path / "legacy",
        {"milestones/v1.8.0-phases/01-alpha/01-VALIDATION.md": _DRAFT},
    )
    assert _collect_phase_dirs(repo) == []
    assert _collect_dod_violations(repo) == []

    # v1.10.0 は v1.9.0 より新しい (文字列比較なら v1.10.0 < v1.9.0 で誤判定する)
    repo = _build_synthetic_repo(
        tmp_path / "double_digit",
        {"milestones/v1.10.0-phases/01-alpha/01-VALIDATION.md": _DRAFT},
    )
    assert [v[0] for v in _collect_dod_violations(repo)] == ["v1.10.0-phases/01-alpha"]

    # ライブの .planning/phases/ も走査対象
    repo = _build_synthetic_repo(
        tmp_path / "live", {"phases/01-alpha/01-VALIDATION.md": _DRAFT}
    )
    violations = _collect_dod_violations(repo)
    assert [v[0] for v in violations] == ["phases/01-alpha"]
    assert "判定不能" in violations[0][1]

    # milestones/ 直下 (v*-phases/ を挟まない配置) は走査対象外
    repo = _build_synthetic_repo(
        tmp_path / "milestone_flat",
        {"milestones/01-alpha/01-VALIDATION.md": _DRAFT},
    )
    assert _collect_phase_dirs(repo) == []

    # 番号リセットの併存: 同じ 03 が複数マイルストーンにあっても曖昧にならず、
    # 適用範囲内のものだけが個別に評価される
    repo = _build_synthetic_repo(
        tmp_path / "reset",
        {
            "milestones/v1.8.0-phases/03-x/03-VALIDATION.md": _DRAFT,
            "milestones/v1.9.0-phases/03-y/03-VALIDATION.md": _DRAFT,
            "milestones/v1.10.0-phases/03-z/03-VALIDATION.md": _VALIDATED,
        },
    )
    assert [v[0] for v in _collect_dod_violations(repo)] == ["v1.9.0-phases/03-y"]

    # 違反リストの順序が安定する
    repo = _build_synthetic_repo(
        tmp_path / "ordering",
        {
            "milestones/v1.9.0-phases/03-c/03-VALIDATION.md": _DRAFT,
            "milestones/v1.9.0-phases/01-a/01-VALIDATION.md": _DRAFT,
            "milestones/v1.9.0-phases/02-b/02-VALIDATION.md": _DRAFT,
        },
    )
    assert [v[0] for v in _collect_dod_violations(repo)] == [
        "v1.9.0-phases/01-a",
        "v1.9.0-phases/02-b",
        "v1.9.0-phases/03-c",
    ]


def test_dod_gate_rejects_empty_and_malformed(tmp_path: Path) -> None:
    """走査 0 件・VALIDATION.md 欠落・frontmatter 異常を skip ではなく違反として扱う."""
    # 走査 0 件は空虚 PASS ではなく FAIL
    repo = _build_synthetic_repo(tmp_path / "empty", {"STATE.md": "# state\n"})
    with pytest.raises(AssertionError):
        assert _collect_phase_dirs(repo), "空虚 PASS の疑い"

    # VALIDATION.md が無いフェーズは違反
    repo = _build_synthetic_repo(
        tmp_path / "missing",
        {"milestones/v1.9.0-phases/01-alpha/01-PLAN.md": "# plan\n"},
    )
    violations = _collect_dod_violations(repo)
    assert [v[0] for v in violations] == ["v1.9.0-phases/01-alpha"]
    assert "0 件" in violations[0][1]

    # VALIDATION.md が 2 件ある場合も違反（どちらを正とするか決められない）
    repo = _build_synthetic_repo(
        tmp_path / "duplicate",
        {
            "milestones/v1.9.0-phases/01-alpha/01-VALIDATION.md": _VALIDATED,
            "milestones/v1.9.0-phases/01-alpha/01b-VALIDATION.md": _VALIDATED,
        },
    )
    assert [v[0] for v in _collect_dod_violations(repo)] == ["v1.9.0-phases/01-alpha"]

    # frontmatter ブロックが無い場合は違反（本文に status: と書いても通らない）
    repo = _build_synthetic_repo(
        tmp_path / "no_frontmatter",
        {
            "milestones/v1.9.0-phases/01-alpha/01-VALIDATION.md": (
                "# no frontmatter\nstatus: validated\n"
            )
        },
    )
    assert [v[0] for v in _collect_dod_violations(repo)] == ["v1.9.0-phases/01-alpha"]

    # status キーを欠く frontmatter を validated と同一視しない
    repo = _build_synthetic_repo(
        tmp_path / "no_status",
        {
            "milestones/v1.9.0-phases/01-alpha/01-VALIDATION.md": (
                "---\nphase: 1\n---\n\nbody\n"
            )
        },
    )
    assert [v[0] for v in _collect_dod_violations(repo)] == ["v1.9.0-phases/01-alpha"]


def test_status_parser_handles_quotes_and_nesting() -> None:
    """PyYAML 非依存の最小パーサが引用符とネストを正しく扱うことを固定する."""
    assert _read_status("status: validated") == "validated"
    assert _read_status('status: "validated"') == "validated"
    assert _read_status("status: 'validated'") == "validated"
    assert _read_status("phase: 1\nstatus:   validated  \n") == "validated"
    assert _read_status("phase: 1\n") is None
    assert _read_status("status:\n") is None
    # ネストしたマッピング内の status は拾わない（トップレベルのみが正）
    assert _read_status("coverage:\n  status: validated\n") is None
    # トップレベルが先に現れれば、後続のネストに影響されない
    assert _read_status("status: draft\ncoverage:\n  status: validated\n") == "draft"


def _live_roadmap(
    checked: bool, status: str, count: str = "0/1", date: str = "—"
) -> str:
    return (
        "## Phases\n<details>\n- [x] Phase 1: 過去\n</details>\n"
        f"- [{'x' if checked else ' '}] **Phase 1: 現行** - 説明\n"
        "- [x] 01-01-PLAN.md\n## Phase Details\n### Phase 1: 現行\n"
        "## Progress\n| Milestone | Status |\n|---|---|\n| v1 | Complete |\n"
        "| Phase | Plans Complete | Status | Completed |\n|---|---|---|---|\n"
        f"| 1. 現行 | {count} | {status} | {date} |\n"
    )


@pytest.mark.parametrize("validation", [_DRAFT, None])
def test_live_incomplete_does_not_require_validation(
    tmp_path: Path, validation
) -> None:
    files = {
        "ROADMAP.md": _live_roadmap(False, "Planned"),
        "phases/01-alpha/01-01-PLAN.md": "# plan\n",
    }
    if validation is not None:
        files["phases/01-alpha/01-VALIDATION.md"] = validation
    assert _collect_dod_violations(_build_synthetic_repo(tmp_path, files)) == []


@pytest.mark.parametrize(
    ("checked", "status", "count", "date", "summary", "requires_validation"),
    [
        (True, "Complete", "1/1", "2026-10-21", True, True),
        (False, "Complete", "1/1", "2026-10-21", True, False),
        (False, "Complete", "1/1", "2026-10-21", False, True),
        (False, "Complete", "0/1", "2026-10-21", True, True),
        (False, "Complete", "1/1", "—", True, True),
        (True, "Planned", "0/1", "—", False, True),
    ],
)
def test_live_completion_requires_consistent_evidence(
    tmp_path, checked, status, count, date, summary, requires_validation
) -> None:
    files = {
        "ROADMAP.md": _live_roadmap(checked, status, count, date),
        "phases/01-alpha/01-01-PLAN.md": "# plan\n",
        "phases/01-alpha/01-VALIDATION.md": _DRAFT,
    }
    if summary:
        files["phases/01-alpha/01-01-SUMMARY.md"] = "# summary\n"
    violations = _collect_dod_violations(_build_synthetic_repo(tmp_path, files))
    assert bool(violations) is requires_validation


@pytest.mark.parametrize(
    "mutate", ["duplicate_phase", "duplicate_progress", "missing", "unknown"]
)
def test_live_roadmap_ambiguity_fails_closed(tmp_path, mutate) -> None:
    roadmap = _live_roadmap(False, "Planned")
    if mutate == "duplicate_phase":
        roadmap = roadmap.replace(
            "## Phase Details", "- [ ] Phase 1: 重複\n## Phase Details"
        )
    elif mutate == "duplicate_progress":
        roadmap += "| 1. 現行 | 0/1 | Planned | — |\n"
    elif mutate == "missing":
        roadmap = roadmap.replace("- [ ] **Phase 1: 現行** - 説明", "")
    else:
        roadmap = roadmap.replace("Planned", "Unknown")
    repo = _build_synthetic_repo(
        tmp_path,
        {
            "ROADMAP.md": roadmap,
            "phases/01-alpha/01-VALIDATION.md": _VALIDATED,
        },
    )
    assert _collect_dod_violations(repo)


def test_milestone_version_parsing() -> None:
    """マイルストーンディレクトリ名のバージョン解釈を固定する."""
    assert _milestone_version("v1.9.0-phases") == (1, 9, 0)
    assert _milestone_version("v1.10.0-phases") == (1, 10, 0)
    assert _milestone_version("v1.9.0-ROADMAP.md") is None
    assert _milestone_version("phases") is None
    # 数値タプル比較なので v1.10.0 > v1.9.0（文字列比較なら逆になる）
    assert _milestone_version("v1.10.0-phases") > _milestone_version("v1.9.0-phases")
