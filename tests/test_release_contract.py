"""版・正本・文書の契約。文書はUTF-8でread-onlyに検査し、書き換えて通さない。"""

import ast
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from tests import release_uat_support as sup

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ("ocr_custom_prompt_sample.md", "ocr_summary_prompt_sample.md")
# 元の dist/PageFolio にあった2サンプルの全文SHA-256（内容改稿はこのphaseの範囲外）。
SAMPLE_SHA256 = {
    "ocr_custom_prompt_sample.md": (
        "03ec2d06b184282974d32be00f228bc37126c79b58aa9ec6e5fc38633e648e5d"
    ),
    "ocr_summary_prompt_sample.md": (
        "6960cb29b8b65b9823a2c48011316ae83dbec32331d2ab63260f910ce2c08b55"
    ),
}
LINK = re.compile(r"\]\(([^)\s]+)\)")
# 未実施の確認を成功のように書く表現（「未」が直前にある場合は除く）。
FALSE_PASS = re.compile(
    r"(?<!未)(実機受入|人手受入|出荷承認|リリース承認)(は|を)?(済み?|合格|完了|承認済)"
)


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def app_version():
    """APP_VERSION を import せず AST のリテラルから読む（版の真の情報源）。"""
    tree = ast.parse(read("pagefolio/constants.py"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "APP_VERSION" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("APP_VERSION が見つからない")


def section(text, heading):
    """見出し行から次の同レベル以上の見出しまでを返す。"""
    lines = text.splitlines()
    level = len(heading) - len(heading.lstrip("#"))
    start = next(i for i, line in enumerate(lines) if line.startswith(heading))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        match = re.match(r"(#+)\s", lines[i])
        if match and len(match.group(1)) <= level:
            end = i
            break
    return "\n".join(lines[start:end])


def relative_links(text):
    return [
        link.split("#")[0]
        for link in LINK.findall(text)
        if not re.match(r"[a-z]+:", link) and link.split("#")[0]
    ]


class TestVersionAndDocs:
    def test_app_version_is_v1_10_0(self):
        assert app_version() == "v1.10.0"

    def test_readme_badge_matches_app_version(self):
        assert f"badge/version-{app_version()}-blue" in read("README.md")

    def test_history_latest_section_is_current_version(self):
        text = read("開発履歴.md")
        headings = [x for x in text.splitlines() if x.startswith("## ")]
        assert headings[0].startswith(f"## {app_version()}")
        latest = section(text, headings[0])
        for word in ("Phase 4", "Phase 5", "Phase 6"):
            assert word in latest
        assert "未承認" in latest
        assert "未実施" in latest
        assert not FALSE_PASS.search(latest)
        assert re.search(rf"最終更新\*\*: {re.escape(app_version())}", text)

    def test_history_keeps_phase5_record_with_reference(self):
        text = read("開発履歴.md")
        phase5 = section(text, "## 未リリース — Phase 5")
        assert "05-UAT.md" in phase5
        assert "H01" in phase5

    def test_readme_distribution_section_states_use_and_limits(self):
        body = section(read("README.md"), "## 配布版（EXE）の使い方")
        version = app_version()
        for needle in (
            f"PageFolio-{version}",
            "ocr_custom_prompt_sample.md",
            "ocr_custom_prompt.md",
            "ocr_summary_prompt_sample.md",
            "ocr_summary_prompt.md",
            "旧フォルダー",
            "上書きしない",
            "同じ session",
            "排他未対応の旧版",
            "前面化",
            "保証外",
            "未実施",
        ):
            assert needle in body, needle
        assert not FALSE_PASS.search(body)

    def test_readme_relative_links_resolve(self):
        text = read("README.md")
        for link in relative_links(text):
            assert (ROOT / link).exists(), link

    def test_no_second_version_constant_in_release_cli(self):
        source = read("tools/build_release.py")
        assert not re.search(r"""["']v\d+\.\d+\.\d+["']""", source)


class TestSampleSources:
    def test_sources_match_original_sha256(self):
        for name in SAMPLES:
            data = (ROOT / "distribution/samples" / name).read_bytes()
            assert hashlib.sha256(data).hexdigest() == SAMPLE_SHA256[name], name

    def test_sources_are_byte_identical_to_legacy_dist(self):
        for name in SAMPLES:
            assert (ROOT / "distribution/samples" / name).read_bytes() == (
                ROOT / "dist/PageFolio" / name
            ).read_bytes()

    def test_gitattributes_keeps_sample_bytes(self):
        text = read(".gitattributes")
        for name in SAMPLES:
            assert f"distribution/samples/{name} -text" in text

    def test_sources_are_tracked_by_git(self):
        git = shutil.which("git") or "git"
        out = subprocess.run(  # noqa: S603
            [git, "ls-files", "--", "distribution/samples"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            stdin=subprocess.DEVNULL,
        ).stdout.split()
        assert sorted(out) == sorted(f"distribution/samples/{n}" for n in SAMPLES)


def load_cli():
    path = ROOT / "tools/build_release.py"
    spec = importlib.util.spec_from_file_location("release_contract_cli", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fake_builder(argv, *, cwd, log, report):
    """実PyInstallerは起動せず、onedirの最小形だけを置く。"""
    dist = Path(argv[argv.index("--distpath") + 1]) / "PageFolio"
    (dist / "_internal").mkdir(parents=True)
    (dist / "PageFolio.exe").write_bytes(b"fixture executable")
    (dist / "_internal/runtime.dll").write_bytes(b"fixture runtime")
    log.write_text("contract fixture", encoding="utf-8")


def help_options():
    out = subprocess.run(  # noqa: S603
        [sys.executable, str(ROOT / "tools/build_release.py"), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        stdin=subprocess.DEVNULL,
        check=True,
    ).stdout
    return out, sorted(set(re.findall(r"--[a-z][a-z-]+", out)) - {"--help"})


class TestGuideAndWorkflow:
    def test_guide_is_short_markdown_for_both_prompts(self):
        raw = (ROOT / "distribution/はじめに.md").read_bytes()
        assert b"\r" not in raw
        text = raw.decode("utf-8")
        assert len(text.splitlines()) <= 70
        for needle in (
            f"PageFolio-{app_version()}",
            "ocr_custom_prompt_sample.md",
            "ocr_custom_prompt.md",
            "ocr_summary_prompt_sample.md",
            "ocr_summary_prompt.md",
            "旧フォルダー",
            "上書きしない",
            "両方",
            "選",
            "プラグイン",
            "自動では移行されません",
            "旧フォルダーの `PageFolio.exe`",
            "排他未対応の旧版",
            "前面化",
            "保証外",
        ):
            assert needle in text, needle
        assert not FALSE_PASS.search(text)

    def test_guide_links_resolve_inside_the_bundle(self, tmp_path):
        result = load_cli().run_build(tmp_path / "out", repo=ROOT, builder=fake_builder)
        assert result["success"] is True, result
        final = Path(result["output"])
        guide = (final / "はじめに.md").read_text(encoding="utf-8")
        links = relative_links(guide)
        assert "docs/CONFIGURATION.md" in links
        for link in links:
            assert (final / link).is_file(), link
        assert (final / "docs/CONFIGURATION.md").read_bytes() == (
            ROOT / "docs/CONFIGURATION.md"
        ).read_bytes()
        assert (final / "はじめに.md").read_bytes() == (
            ROOT / "distribution/はじめに.md"
        ).read_bytes()
        report = json.loads((final / "release-report.json").read_text("utf-8"))
        digest = hashlib.sha256((ROOT / "docs/CONFIGURATION.md").read_bytes())
        assert report["distribution_manifest"]["docs/CONFIGURATION.md"] == (
            digest.hexdigest()
        )
        assert report["release_allowed"] is False

    def test_development_describes_one_cli_for_first_and_rebuild(self):
        text = read("docs/DEVELOPMENT.md")
        out, options = help_options()
        assert options, out
        for option in options:
            assert option in text, option
        for needle in (
            "tools/build_release.py",
            "初回",
            "再ビルド",
            "同じ",
            "INCOMPLETE",
            "release-report.json",
            ".release-history",
            ".release-work",
            "preflight",
            "完全な複製",
            "自動起動しない",
            "実機受入",
            "PageFolio-<APP_VERSION>",
            "旧追跡",
            "plugins",
            "自動では移行しない",
        ):
            assert needle in text, needle

    def test_development_gives_safe_recovery_and_retention_rules(self):
        text = read("docs/DEVELOPMENT.md")
        for needle in (
            "PID",
            "生成時刻",
            "終了済み",
            "解除しない",
            "使用容量",
            "run一覧",
            "SHA-256",
            "別保存",
            "明示",
            "旧dist",
        ):
            assert needle in text, needle

    def test_development_has_no_destructive_or_duplicated_instructions(self):
        text = read("docs/DEVELOPMENT.md")
        for forbidden in (
            "/tmp/ocr_",  # noqa: S108
            "git add -A",
            "git add .",
            "git add dist",
            "rm -rf dist",
            "pyinstaller PageFolio.spec --noconfirm",
        ):
            assert forbidden not in text, forbidden
        assert not re.search(r"PageFolio-v\d+\.\d+\.\d+", text)

    def test_legacy_tracked_dist_and_ignore_rules_are_kept(self):
        git = shutil.which("git") or "git"
        tracked = subprocess.run(  # noqa: S603
            [git, "ls-files", "--", "dist/PageFolio/PageFolio.exe"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            stdin=subprocess.DEVNULL,
        ).stdout.split()
        assert tracked == ["dist/PageFolio/PageFolio.exe"]
        assert "dist/*" in read(".gitignore").splitlines()

    def test_configuration_documents_sample_copy_without_changing_contract(self):
        text = read("docs/CONFIGURATION.md")
        for needle in (
            "ocr_custom_prompt_sample.md",
            "ocr_summary_prompt_sample.md",
            "コピー",
            "上書きしない",
            "UTF-8",
            "書き戻す",
            "毎回再読込",
        ):
            assert needle in text, needle


# ---------------------------------------------------------------------------
# 06-05-01: 全ケースの入口別カードと証拠台帳（TestCaseCoverage）
# ---------------------------------------------------------------------------
PHASE_DIR = ROOT / ".planning/phases/06-release-validation"
CARRYOVER_CASES = (
    "W01 W02 W03 W04 W05a W05b W05c W06 W07a W07b W08a W08b W08c W08d "
    "W09a W09b W09c W09d W10a W10b W11 W12a W12b W12c WR-01"
).split()
FAULT_CASES = tuple(f"X0{n}" for n in range(1, 7))
GROUPS = {
    **dict.fromkeys(("W01", "W02"), "G1"),
    **dict.fromkeys(("W03", "W04"), "G2"),
    **dict.fromkeys(("W05a", "W05b", "W05c"), "G3"),
    **dict.fromkeys(("W12a", "W12b", "W12c"), "G4"),
    **dict.fromkeys(("X01", "X02", "X03"), "G5"),
    **dict.fromkeys(("X04", "X05", "X06"), "G6"),
    **dict.fromkeys(("W06", "W07a"), "G7"),
    **dict.fromkeys(("W07b", "WR-01"), "G8"),
    **dict.fromkeys(("W08a", "W08b"), "G9"),
    **dict.fromkeys(("W08c", "W08d"), "G10"),
    **dict.fromkeys(("W09a", "W09b"), "G11"),
    **dict.fromkeys(("W09c", "W09d"), "G12"),
    **dict.fromkeys(("W10a", "W10b"), "G13"),
    "W11": "G14",
}
ENTRIES3 = ("script", "module", "production-exe")
CARD_LABELS = (
    "準備コマンド",
    "利用者操作",
    "期待",
    "必須観測",
    "失敗時の回収",
    "出典",
)
CARD_HEAD = re.compile(r"^### ((?:W\d{2}[a-d]?|WR-01|X\d{2}))/(\S+)\s*$", re.MULTILINE)


def pairs(conds, entries):
    return {(c, e) for c in conds for e in entries}


# 台帳のsubrowが満たすべき (条件, 入口) の宣言。台帳側の宣言を写すのではなく、
# 計画(D-13〜D-16・移管条件)から独立に書いた期待値。
EXPECTED_PAIRS = {
    "W01": pairs(("normal", "zoomed"), ENTRIES3),
    "W02": pairs(("settings", "thumb", "preview"), ENTRIES3),
    "W03": pairs(("pdf-3page",), ENTRIES3),
    "W04": pairs(("ocr-1page",), ENTRIES3),
    "W05a": pairs(("nested-settings",), ENTRIES3),
    "W05b": pairs(("ocr-close-confirm",), ENTRIES3),
    "W05c": pairs(("quit-no",), ENTRIES3),
    "W12a": {
        (f"{a}-{b}", a)
        for a in ("script", "module", "relocated")
        for b in ("script", "module", "relocated")
    },
}
W12B_CONDITIONS = {
    "exe-exe-samecopy",
    "exe-script",
    "script-exe",
    "exe-module",
    "module-exe",
    "exe-tracer",
    "tracer-exe",
    "exe-relocated-copy",
    "relocated-copy-exe",
}
W12C_CONDITIONS = {
    "explorer-python",
    "terminal-python",
    "explorer-exe",
    "terminal-exe",
}
X04_CONDITIONS = {
    "general-settings",
    "llm-or-external-prompt",
    "shortcut",
    "plugin-change",
    "ocr-conditions",
    "tool-settings",
    "window-exit",
    "replace-notification",
}
PHASE5_H = tuple(f"H{n:02d}" for n in range(1, 15))
# 実機passになった行が属してよいstatus。passの妥当性はauditが検査する。
STATUSES = ("not-run", "pass", "fail", "blocked")


def ledger():
    return json.loads((PHASE_DIR / "06-MANUAL-EVIDENCE.json").read_text("utf-8"))


def cards():
    text = (PHASE_DIR / "06-UAT.md").read_text("utf-8")
    heads = list(CARD_HEAD.finditer(text))
    found = {}
    for i, head in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        found[f"{head.group(1)}/{head.group(2)}"] = text[head.end() : end]
    return found


def rows():
    for case in ledger()["cases"]:
        for sub in case["subrows"]:
            yield case, sub


def carryover_ids():
    ids = []
    for line in (PHASE_DIR / "06-UAT-CARRYOVER.md").read_text("utf-8").splitlines():
        if not line.startswith("| W"):
            continue
        cell = line.split("|")[1].strip()
        match = re.match(r"(W\d{2})([a-d](?:/[a-d])*)?", cell)
        base, letters = match.group(1), match.group(2)
        if letters:
            ids += [base + letter for letter in letters.split("/")]
        else:
            ids.append(base)
    return ids


class TestCaseCoverage:
    def test_all_carryover_cases_and_fault_cases_are_declared_once(self):
        ids = [case["id"] for case in ledger()["cases"]]
        assert len(ids) == len(set(ids)), "ケースIDが重複しています"
        assert set(ids) == set(CARRYOVER_CASES) | set(FAULT_CASES)
        assert len(CARRYOVER_CASES) == 25  # 24枝番 + WR-01
        # 移管正本(06-UAT-CARRYOVER)の表の全IDが台帳で追跡されている
        assert set(carryover_ids()) <= set(ids)
        assert set(CARRYOVER_CASES) - {"WR-01"} == set(carryover_ids())

    def test_groups_and_tasks_follow_the_validation_table(self):
        for case in ledger()["cases"]:
            assert case["group"] == GROUPS[case["id"]], case["id"]
            task = "06-05-02" if case["id"] in sup.TASK_IDS["06-05-02"] else None
            task = task or (
                "06-06-01" if case["id"] in sup.TASK_IDS["06-06-01"] else ""
            )
            assert case["task"] == task, case["id"]
        assigned = set(sup.TASK_IDS["06-05-02"]) | set(sup.TASK_IDS["06-06-01"])
        assert assigned == set(CARRYOVER_CASES) | set(FAULT_CASES)

    def test_subrows_expand_by_entry_and_condition(self):
        by_case = {c["id"]: c["subrows"] for c in ledger()["cases"]}
        for case_id, expected in EXPECTED_PAIRS.items():
            got = [(s["condition"], s["entry"]) for s in by_case[case_id]]
            assert len(got) == len(set(got)), case_id
            assert set(got) == expected, case_id
        assert {s["condition"] for s in by_case["W12b"]} == W12B_CONDITIONS
        assert {s["condition"] for s in by_case["W12c"]} == W12C_CONDITIONS
        assert {s["condition"] for s in by_case["X04"]} == X04_CONDITIONS
        for case_id in FAULT_CASES:
            assert {s["entry"] for s in by_case[case_id]} == {"production-exe"}

    def test_python_injection_and_exe_common_behavior_are_separate_rows(self):
        by_case = {c["id"]: c["subrows"] for c in ledger()["cases"]}
        for case_id in ("W07a", "W07b", "W08a", "W08b", "W08d"):
            kinds = {(s["entry"], s["evidence_kind"]) for s in by_case[case_id]}
            assert any(k == "fault-injection" for _, k in kinds), case_id
            assert ("production-exe", "production-exe") in kinds, case_id
            for entry, kind in kinds:
                # 注入はPython入口だけ。実EXEへfrozen hookを仮定した行を作らない
                assert (kind == "fault-injection") == (entry != "production-exe"), (
                    case_id,
                    entry,
                    kind,
                )

    def test_every_subrow_is_fully_declared_and_not_prematurely_passed(self):
        target = json.loads((PHASE_DIR / "06-BUILD-EVIDENCE.json").read_text("utf-8"))
        exe = target["final_release"]["exe_sha256"]
        seen = set()
        for case, sub in rows():
            where = f"{case['id']}/{sub['subrow']}"
            assert where not in seen, where
            seen.add(where)
            assert sub["status"] in STATUSES, where
            assert sub["evidence_kind"] in sup.EVIDENCE_KINDS, where
            assert sub["required_observations"], where
            assert len(set(sub["required_observations"])) == len(
                sub["required_observations"]
            ), where
            assert sub["card"] == where, where
            # 準備(担当が用意した)と実機passは別フィールド
            assert sub["preparation"]["status"] in (
                "not-prepared",
                "driver-ready",
                "prepared",
            ), where
            if sub["entry"] == "production-exe":
                assert sub["evidence_kind"] == "production-exe", where
                assert sub["expected_binary_sha256"] == exe, where
            if sub["status"] == "not-run":
                # 空欄補完・準備済みを回答/pass根拠に変えない
                assert sub["answer"] == "", where
                assert sub["observations"] == {}, where
                assert sub["observed_at"] == "", where
                assert sub["binary_sha256"] == "", where

    def test_cards_cover_every_subrow_with_all_required_labels(self):
        found = cards()
        expected = {f"{case['id']}/{sub['subrow']}" for case, sub in rows()}
        assert set(found) == expected
        for key, body in found.items():
            for label in CARD_LABELS:
                assert label in body, (key, label)
        for case, sub in rows():
            body = found[f"{case['id']}/{sub['subrow']}"]
            for name in sub["required_observations"]:
                assert name in body, (case["id"], sub["subrow"], name)

    def test_phase5_results_are_referenced_not_repeated(self):
        data = ledger()
        reuse = data["phase5_reuse"]
        assert [item["id"] for item in reuse["human_checks"]] == list(PHASE5_H)
        assert len(reuse["semantic_evaluations"]) == 2
        source = (ROOT / ".planning/phases/05-config-notification/05-UAT.md").read_text(
            "utf-8"
        )
        for item in reuse["human_checks"]:
            assert re.search(rf"\| {item['id']}\b.*\| pass \|", source), item["id"]
            assert item["reuse"] == "reference-only-not-repeated"
        assert reuse["source"].endswith("05-UAT.md")
        # H01〜H14を06-05の枝番として再実施する行は作らない
        assert not any(re.fullmatch(r"H\d\d", c["id"]) for c in data["cases"])
        assert {c["id"] for c in data["cases"]}.isdisjoint(PHASE5_H)

    def test_w12b_roles_hashes_and_both_directions(self):
        build = json.loads((PHASE_DIR / "06-BUILD-EVIDENCE.json").read_text("utf-8"))
        final = build["final_release"]["exe_sha256"]
        w12b = next(c for c in ledger()["cases"] if c["id"] == "W12b")
        by = {s["condition"]: s for s in w12b["subrows"]}
        for pair in (
            ("exe-script", "script-exe"),
            ("exe-module", "module-exe"),
            ("exe-tracer", "tracer-exe"),
            ("exe-relocated-copy", "relocated-copy-exe"),
        ):
            assert all(name in by for name in pair), pair  # 両方向
        for sub in w12b["subrows"]:
            assert sub["subject"]["role"] == "final-release-candidate"
            assert sub["subject"]["binary_sha256"] == final
            assert sub["evidence_kind"] == "production-exe"
            assert sub["binary_sha256"] in ("", final)
        for name in ("exe-tracer", "tracer-exe"):
            peer = by[name]["peer"]
            assert peer["role"] == "technical-tracer-real-exe"
            assert peer["binary_sha256"] != final
            assert peer["version"] != build["version"]
            assert peer["provenance"]["run_id"]
            assert peer["provenance"]["source_manifest_sha256"]
            # tracerを公式旧版/最終EXE受入済みとして扱わない
            assert peer.get("official_release") is False
        for name in ("exe-exe-samecopy", "exe-relocated-copy", "relocated-copy-exe"):
            peer = by[name]["peer"]
            assert peer["role"] == "same-version-copy"
            assert peer["binary_sha256"] == final
            assert peer["version"] == build["version"]
        for name in ("exe-script", "script-exe"):
            assert by[name]["peer"] == {"role": "python-entry", "entry": "script"}
        for name in ("exe-module", "module-exe"):
            assert by[name]["peer"] == {"role": "python-entry", "entry": "module"}

    def test_structure_audit_accepts_ledger_and_rejects_false_pass(self, tmp_path):
        for name in ("06-BUILD-EVIDENCE.json", "06-MANUAL-EVIDENCE.json"):
            shutil.copyfile(PHASE_DIR / name, tmp_path / name)
        audit = sup.run_audit(tmp_path, mode="allow-pending")
        assert audit.ok, audit.reasons
        # 全subrow未実施のままrequire-passは通らない(構造専用allow-pendingとは別)
        if any(sub["status"] != "pass" for _, sub in rows()):
            assert not sup.run_audit(
                tmp_path, mode="require-pass", require="W01,W02"
            ).ok

        def mutate(change):
            data = ledger()
            change(data)
            (tmp_path / "06-MANUAL-EVIDENCE.json").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
            return sup.run_audit(tmp_path, mode="allow-pending")

        def passed_without_answer(data):
            sub = next(c for c in data["cases"] if c["id"] == "W03")["subrows"][0]
            sub["status"] = "pass"

        def unit_as_pass(data):
            sub = next(c for c in data["cases"] if c["id"] == "W04")["subrows"][0]
            sub.update(status="pass", evidence_kind="unit", answer="W04：期待どおり")

        def exe_without_binary_hash(data):
            sub = next(
                s
                for c in data["cases"]
                if c["id"] == "W03"
                for s in c["subrows"]
                if s["entry"] == "production-exe"
            )
            sub.update(
                status="pass",
                answer="W03：期待どおり",
                observations={n: "x" for n in sub["required_observations"]},
                run_id="r",
                observed_at="2026-10-25T00:00:00+00:00",
                environment={"os": "Windows 11", "elevated": False, "session_id": 1},
                binary_sha256="",
            )

        def dropped_case(data):
            data["cases"] = [c for c in data["cases"] if c["id"] != "W06"]

        def missing_condition(data):
            case = next(c for c in data["cases"] if c["id"] == "W01")
            case["subrows"] = [s for s in case["subrows"] if s["condition"] != "zoomed"]

        assert not mutate(passed_without_answer).ok
        assert not mutate(unit_as_pass).ok
        assert not mutate(exe_without_binary_hash).ok
        # 台帳の漏れ(ケース/条件)はrequire-passの宣言検査で拒否される
        dropped = ledger()
        dropped_case(dropped)
        (tmp_path / "06-MANUAL-EVIDENCE.json").write_text(
            json.dumps(dropped, ensure_ascii=False), encoding="utf-8"
        )
        assert not sup.run_audit(tmp_path, mode="require-pass", require="W06").ok
        missing = ledger()
        missing_condition(missing)
        (tmp_path / "06-MANUAL-EVIDENCE.json").write_text(
            json.dumps(missing, ensure_ascii=False), encoding="utf-8"
        )
        assert not sup.run_audit(tmp_path, mode="require-pass", require="W01").ok

    def test_uat_document_keeps_states_separate_and_never_claims_pass(self):
        text = (PHASE_DIR / "06-UAT.md").read_text("utf-8")
        assert not FALSE_PASS.search(text)
        for needle in (
            "準備完了・build成功・人手pass・Phase完了は別の状態",
            "ケースID",
            "貼り付け",
            "LLM",
            "06-UAT-CARRYOVER.md",
            "04-WINDOWS-UAT.md",
            "05-UAT.md",
            "technical-tracer-real-exe",
            "final-release-candidate",
        ):
            assert needle in text, needle
