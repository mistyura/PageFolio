"""版・正本・文書の契約。文書はUTF-8でread-onlyに検査し、書き換えて通さない。"""

import ast
import hashlib
import re
import shutil
import subprocess
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
