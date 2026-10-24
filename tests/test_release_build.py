"""配布CLIの実ディスク境界。pytestから実PyInstallerは起動しない。"""

import importlib.util
import json
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ("ocr_custom_prompt_sample.md", "ocr_summary_prompt_sample.md")
PROTECTED = ("pagefolio_settings.json", "ocr_custom_prompt.md", "ocr_summary_prompt.md")


def load_cli():
    path = ROOT / "tools/build_release.py"
    assert path.is_file(), "安全な配布CLIが必要"
    spec = importlib.util.spec_from_file_location("release_build_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "pagefolio").mkdir(parents=True)
    (root / "pagefolio/constants.py").write_text(
        'APP_VERSION = "v9.8.7"\n'
        + "\n".join(
            f"{key} = {value!r}"
            for key, value in zip(
                ("SETTINGS_FILE", "CUSTOM_PROMPT_FILE", "SUMMARY_PROMPT_FILE"),
                PROTECTED,
                strict=True,
            )
        ),
        encoding="utf-8",
    )
    (root / "pagefolio.py").write_bytes(b"print('fixture')\n")
    (root / "pagefolio.ico").write_bytes(b"icon")
    (root / "distribution/samples").mkdir(parents=True)
    for name in SAMPLES:
        (root / "distribution/samples" / name).write_bytes(b"sample\r\n")
    (root / "distribution/はじめに.md").write_text("ガイド", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs/CONFIGURATION.md").write_bytes(b"configuration\n")
    (root / "dist/PageFolio").mkdir(parents=True)
    (root / "dist/PageFolio/old.exe").write_bytes(b"legacy")
    return root


class FakeBuilder:
    def __init__(self):
        self.calls = []

    def __call__(self, argv, *, cwd, log, report):
        self.calls.append(argv)
        assert cwd.is_absolute()
        assert log.is_absolute()
        assert argv[:3] == [str(Path(sys.executable).resolve()), "-m", "PyInstaller"]
        assert argv[-1] == str(cwd / "pagefolio.py")
        assert argv[argv.index("--icon") + 1] == str(cwd / "pagefolio.ico")
        assert "--noconfirm" not in argv
        for flag in ("--clean", "--onedir", "--noconsole"):
            assert flag in argv
        paths = [
            Path(argv[argv.index(f) + 1])
            for f in ("--specpath", "--workpath", "--distpath")
        ]
        assert len(set(paths)) == 3
        assert all(p.is_absolute() and p.parent == log.parent for p in paths)
        stage = paths[-1] / "PageFolio"
        stage.mkdir(parents=True)
        (stage / "PageFolio.exe").write_bytes(b"fake fixture executable")
        (stage / "_internal").mkdir()
        (stage / "_internal/runtime.dll").write_bytes(b"fixture runtime")
        log.write_text("fake builder only", encoding="utf-8")


def invoke(repo, output, builder=None):
    builder = builder or FakeBuilder()
    return load_cli().run_build(output, repo=repo, builder=builder), builder


class TestReleaseTracer:
    def test_empty_output_builds_verified_bundle(self, repo, tmp_path):
        result, builder = invoke(repo, tmp_path / "output & legal space")
        assert result["success"] is True
        assert len(builder.calls) == 1
        final = Path(result["output"])
        for name in SAMPLES:
            assert (final / name).read_bytes() == (
                repo / "distribution/samples" / name
            ).read_bytes()
        report = json.loads((final / "release-report.json").read_text("utf-8"))
        assert report["release_allowed"] is False
        assert report["artifact_role"] == "technical-tracer"
        assert "release-report.json" not in report["distribution_manifest"]
        assert (final / "docs/CONFIGURATION.md").is_file()
        assert (Path(result["run"]) / "report.json").is_file()

    def test_default_dist_preserves_legacy(self, repo):
        result, _ = invoke(repo, repo / "dist")
        assert result["success"] is True
        assert (repo / "dist/PageFolio/old.exe").read_bytes() == b"legacy"

    @pytest.mark.parametrize(
        "target",
        [
            ".",
            "pagefolio",
            "distribution",
            "tools",
            "tests",
            "docs",
            ".git",
            "dist/PageFolio",
        ],
    )
    def test_source_overlap_rejected_before_builder(self, repo, target):
        builder = FakeBuilder()
        result, _ = invoke(repo, repo / target, builder)
        assert result["success"] is False
        assert builder.calls == []
        assert (repo / "pagefolio.py").read_bytes() == b"print('fixture')\n"

    @pytest.mark.parametrize("name", PROTECTED)
    def test_user_file_rejected_before_builder(self, repo, tmp_path, name):
        out = tmp_path / "output"
        final = out / "PageFolio-v9.8.7"
        final.mkdir(parents=True)
        original = final / name
        original.write_bytes(b"private user content")
        result, builder = invoke(repo, out)
        assert result["success"] is False
        assert builder.calls == []
        assert original.read_bytes() == b"private user content"
        assert "private user content" not in json.dumps(result)

    def test_reparse_ancestor_rejected(self, repo, tmp_path, monkeypatch):
        cli = load_cli()
        out = tmp_path / "junction"
        out.mkdir()
        original = Path.lstat

        def reparse(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if path == out:

                class Reparse:
                    st_file_attributes = stat.FILE_ATTRIBUTE_REPARSE_POINT
                    st_mode = value.st_mode

                return Reparse()
            return value

        monkeypatch.setattr(Path, "lstat", reparse)
        builder = FakeBuilder()
        result = cli.run_build(out / "child", repo=repo, builder=builder)
        assert result["success"] is False
        assert builder.calls == []

    def test_unreadable_destination_rejected(self, repo, tmp_path, monkeypatch):
        cli = load_cli()
        out = tmp_path / "output"
        final = out / "PageFolio-v9.8.7"
        final.mkdir(parents=True)
        original = Path.iterdir

        def denied(path):
            if path == final:
                raise PermissionError("fixture unreadable directory")
            return original(path)

        monkeypatch.setattr(Path, "iterdir", denied)
        builder = FakeBuilder()
        assert cli.run_build(out, repo=repo, builder=builder)["success"] is False
        assert builder.calls == []

    def test_original_samples_preserved(self):
        for name in SAMPLES:
            assert (ROOT / "distribution/samples" / name).read_bytes() == (
                ROOT / "dist/PageFolio" / name
            ).read_bytes()
