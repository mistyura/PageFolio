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
