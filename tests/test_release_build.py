"""配布CLIの実ディスク境界。pytestから実PyInstallerは起動しない。"""

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git") or "git"
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
    def __init__(self, payload=b"fake fixture executable"):
        self.calls = []
        self.payload = payload

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
        (stage / "PageFolio.exe").write_bytes(self.payload)
        (stage / "_internal").mkdir()
        (stage / "_internal/runtime.dll").write_bytes(b"fixture runtime")
        log.write_text("fake builder only", encoding="utf-8")


def make_link(link, target):
    """実際のリンクを作る。Windowsはjunction、それ以外はsymlink。"""
    if os.name == "nt":
        shell = os.environ["ComSpec"]
        subprocess.run(  # noqa: S603
            [shell, "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
        )
    else:
        os.symlink(target, link, target_is_directory=True)


def drop_link(link):
    if os.path.lexists(link):
        os.rmdir(link) if os.name == "nt" else os.unlink(link)


def tree(path):
    """リンクを辿らず通常ファイルのbytesを相対名で控える。"""
    return {
        p.relative_to(path).as_posix(): p.read_bytes()
        for p in sorted(path.rglob("*"))
        if p.is_file()
    }


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


def build_managed(repo, out, payload=b"first executable"):
    """前回の管理済み配布を実際に作り、(結果, 配布tree) を返す。"""
    result, _ = invoke(repo, out, FakeBuilder(payload))
    assert result["success"] is True
    return result, tree(Path(result["output"]))


def assert_no_side_effects(out):
    """拒否はlock・作業領域・履歴を作る前に起きる。"""
    assert not list(out.glob(".PageFolio-*.lock"))
    assert not (out / ".release-work").exists()
    assert not (out / ".release-history").exists()


class TestPreflight:
    @pytest.mark.parametrize("kind", ["file", "directory", "broken-link"])
    @pytest.mark.parametrize("name", PROTECTED)
    def test_protected_name_kinds_stop_before_any_change(
        self, repo, tmp_path, name, kind
    ):
        out = tmp_path / "output"
        final = out / "PageFolio-v9.8.7"
        final.mkdir(parents=True)
        (final / "keep.txt").write_bytes(b"keep")
        target = final / name
        if kind == "file":
            target.write_bytes(b"private user content")
        elif kind == "directory":
            target.mkdir()
            (target / "inner.txt").write_bytes(b"private inner")
        else:
            gone = tmp_path / "gone"
            gone.mkdir()
            make_link(target, gone)
            gone.rmdir()
        before = tree(final)
        try:
            result, builder = invoke(repo, out)
            assert result["success"] is False
            assert builder.calls == []
            assert tree(final) == before
            assert os.path.lexists(target)
            assert_no_side_effects(out)
            shown = json.dumps(result, ensure_ascii=False)
            assert "private user content" not in shown
            assert "private inner" not in shown
        finally:
            if kind == "broken-link":
                drop_link(target)

    def test_protected_name_is_case_insensitive(self, repo, tmp_path):
        out = tmp_path / "output"
        final = out / "PageFolio-v9.8.7" / "nested"
        final.mkdir(parents=True)
        (final / "OCR_Custom_Prompt.MD").write_bytes(b"private")
        result, builder = invoke(repo, out)
        assert result["success"] is False
        assert builder.calls == []
        assert (final / "OCR_Custom_Prompt.MD").read_bytes() == b"private"

    def test_unknown_existing_file_rejected(self, repo, tmp_path):
        out = tmp_path / "output"
        final = out / "PageFolio-v9.8.7"
        final.mkdir(parents=True)
        (final / "notes.txt").write_bytes(b"not managed")
        result, builder = invoke(repo, out)
        assert result["success"] is False
        assert builder.calls == []
        assert (final / "notes.txt").read_bytes() == b"not managed"
        assert_no_side_effects(out)

    def test_real_junction_destination_rejected(self, repo, tmp_path):
        out = tmp_path / "output"
        out.mkdir()
        real = tmp_path / "real"
        real.mkdir()
        (real / "user.txt").write_bytes(b"outside")
        link = out / "PageFolio-v9.8.7"
        make_link(link, real)
        try:
            result, builder = invoke(repo, out)
            assert result["success"] is False
            assert builder.calls == []
            assert tree(real) == {"user.txt": b"outside"}
        finally:
            drop_link(link)

    def test_real_junction_ancestor_rejected(self, repo, tmp_path):
        real = tmp_path / "real"
        real.mkdir()
        link = tmp_path / "linked"
        make_link(link, real)
        try:
            result, builder = invoke(repo, link / "child")
            assert result["success"] is False
            assert builder.calls == []
            assert list(real.iterdir()) == []
        finally:
            drop_link(link)

    @pytest.mark.parametrize("name", [".release-work", ".release-history"])
    def test_work_or_history_name_taken_by_file(self, repo, tmp_path, name):
        out = tmp_path / "output"
        out.mkdir()
        (out / name).write_bytes(b"not a directory")
        result, builder = invoke(repo, out)
        assert result["success"] is False
        assert builder.calls == []
        assert (out / name).read_bytes() == b"not a directory"

    def test_tracked_source_file_collision_rejected(self, repo):
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        for args in (
            ["init", "-q"],
            ["add", "-A"],
            ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
            + ["commit", "-q", "-m", "fixture"],
        ):
            subprocess.run(  # noqa: S603
                [GIT, "-C", str(repo), *args],
                check=True,
                env=env,
                capture_output=True,
                stdin=subprocess.DEVNULL,
            )
        result, builder = invoke(repo, repo / "pagefolio.py")
        assert result["success"] is False
        assert builder.calls == []
        assert (repo / "pagefolio.py").read_bytes() == b"print('fixture')\n"

    def test_stale_or_foreign_lock_is_never_taken(self, repo, tmp_path):
        out = tmp_path / "output"
        out.mkdir()
        lock = out / ".PageFolio-v9.8.7.lock"
        lock.write_bytes(b'{"created": 1, "pid": 1, "run_id": "dead"}')
        before = lock.read_bytes()
        result, builder = invoke(repo, out)
        assert result["success"] is False
        assert builder.calls == []
        assert lock.read_bytes() == before
        assert not (out / ".release-work").exists()

    @pytest.mark.parametrize(
        "leaf", ["a b", "a&b", "a'b", "a$b;(c)", "a%b^c", "日本語 出力"]
    )
    def test_shell_characters_are_literal(self, repo, tmp_path, leaf):
        result, builder = invoke(repo, tmp_path / leaf)
        assert result["success"] is True
        assert len(builder.calls) == 1
        assert Path(result["output"]).parent.name == leaf

    def test_secrets_are_not_collected(self, repo, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "super-secret-key-value")
        (repo / "pagefolio_settings.json").write_text(
            '{"api_key": "settings-secret"}', encoding="utf-8"
        )
        result, _ = invoke(repo, tmp_path / "output")
        assert result["success"] is True
        for path in Path(result["output"]).parent.rglob("*"):
            if path.is_file() and path.suffix in {".json", ".log"}:
                text = path.read_text("utf-8", errors="replace")
                assert "super-secret-key-value" not in text
                assert "settings-secret" not in text


class TestRebuild:
    def test_managed_rebuild_keeps_previous_tree(self, repo, tmp_path):
        out = tmp_path / "output"
        first, old_tree = build_managed(repo, out)
        second_builder = FakeBuilder(b"second executable")
        second, _ = invoke(repo, out, second_builder)
        assert second["success"] is True
        assert len(second_builder.calls) == 1
        history = Path(second["old_output"])
        assert history.parent == out / ".release-history"
        assert tree(history) == old_tree
        final = Path(second["output"])
        assert (final / "PageFolio.exe").read_bytes() == b"second executable"
        embedded = json.loads((final / "release-report.json").read_text("utf-8"))
        assert embedded["old_output"] == str(history)
        assert Path(first["run"]).is_dir()
        assert not list(out.glob(".PageFolio-*.lock"))

    @pytest.mark.parametrize(
        "mutate",
        [
            lambda f: (f / "_internal/runtime.dll").write_bytes(b"changed"),
            lambda f: (f / "added.txt").write_bytes(b"unknown"),
            lambda f: (f / "_internal/runtime.dll").unlink(),
            lambda f: (f / "release-report.json").write_bytes(b"{}"),
            lambda f: (f / "extra-dir").mkdir(),
            lambda f: (f / "docs/CONFIGURATION.md").write_bytes(b"edited"),
        ],
        ids=["modified", "unknown", "missing", "report", "directory", "docs"],
    )
    def test_changed_managed_tree_rejected_before_builder(self, repo, tmp_path, mutate):
        out = tmp_path / "output"
        first, _ = build_managed(repo, out)
        final = Path(first["output"])
        mutate(final)
        before = tree(final)
        dirs = sorted(p.name for p in final.rglob("*") if p.is_dir())
        builder = FakeBuilder(b"second executable")
        result, _ = invoke(repo, out, builder)
        assert result["success"] is False
        assert builder.calls == []
        assert tree(final) == before
        assert sorted(p.name for p in final.rglob("*") if p.is_dir()) == dirs
        assert not (out / ".release-history").exists()

    def test_missing_external_report_rejected(self, repo, tmp_path):
        out = tmp_path / "output"
        first, old_tree = build_managed(repo, out)
        (Path(first["run"]) / "report.json").unlink()
        builder = FakeBuilder()
        result, _ = invoke(repo, out, builder)
        assert result["success"] is False
        assert builder.calls == []
        assert tree(Path(first["output"])) == old_tree

    def test_user_prompt_copy_in_managed_tree_stops(self, repo, tmp_path):
        out = tmp_path / "output"
        first, _ = build_managed(repo, out)
        final = Path(first["output"])
        (final / "ocr_custom_prompt.md").write_bytes(b"my private prompt")
        builder = FakeBuilder()
        result, _ = invoke(repo, out, builder)
        assert result["success"] is False
        assert builder.calls == []
        assert (final / "ocr_custom_prompt.md").read_bytes() == b"my private prompt"

    def test_concurrent_run_cannot_share_output(self, repo, tmp_path):
        out = tmp_path / "output"
        cli = load_cli()
        inner_builder = FakeBuilder(b"inner")
        seen = {}

        def outer(argv, *, cwd, log, report):
            seen["inner"] = cli.run_build(out, repo=repo, builder=inner_builder)
            seen["lock_alive"] = bool(list(out.glob(".PageFolio-*.lock")))
            FakeBuilder(b"outer")(argv, cwd=cwd, log=log, report=report)

        result = cli.run_build(out, repo=repo, builder=outer)
        assert result["success"] is True
        assert seen["inner"]["success"] is False
        assert seen["lock_alive"] is True
        assert inner_builder.calls == []
        assert (Path(result["output"]) / "PageFolio.exe").read_bytes() == b"outer"
        assert not list(out.glob(".PageFolio-*.lock"))

    def test_output_change_during_build_blocks_publish(self, repo, tmp_path):
        out = tmp_path / "output"
        first, _ = build_managed(repo, out)
        final = Path(first["output"])

        def racing(argv, *, cwd, log, report):
            FakeBuilder(b"second")(argv, cwd=cwd, log=log, report=report)
            (final / "late.txt").write_bytes(b"someone else")

        result = load_cli().run_build(out, repo=repo, builder=racing)
        assert result["success"] is False
        assert (final / "late.txt").read_bytes() == b"someone else"
        assert (final / "PageFolio.exe").read_bytes() == b"first executable"
        assert (Path(result["run"]) / "dist/PageFolio/PageFolio.exe").is_file()

    def test_lock_replaced_during_build_blocks_publish(self, repo, tmp_path):
        out = tmp_path / "output"

        def racing(argv, *, cwd, log, report):
            FakeBuilder()(argv, cwd=cwd, log=log, report=report)
            next(out.glob(".PageFolio-*.lock")).write_bytes(b"foreign owner")

        result = load_cli().run_build(out, repo=repo, builder=racing)
        assert result["success"] is False
        assert not (out / "PageFolio-v9.8.7").exists()
        assert next(out.glob(".PageFolio-*.lock")).read_bytes() == b"foreign owner"

    def test_input_change_during_build_blocks_publish(self, repo, tmp_path):
        out = tmp_path / "output"

        def racing(argv, *, cwd, log, report):
            FakeBuilder()(argv, cwd=cwd, log=log, report=report)
            (repo / "pagefolio.py").write_bytes(b"print('changed')\n")

        result = load_cli().run_build(out, repo=repo, builder=racing)
        assert result["success"] is False
        assert not (out / "PageFolio-v9.8.7").exists()
        assert (Path(result["run"]) / "INCOMPLETE").is_file()


class TestFailureRetention:
    def failed_run(self, result):
        run = Path(result["run"])
        report = json.loads((run / "report.json").read_text("utf-8"))
        assert result["success"] is False
        assert report["success"] is False
        assert report["status"] == "INCOMPLETE"
        assert (run / "INCOMPLETE").is_file()
        assert (run / "build.log").is_file()
        return run, report

    def managed(self, repo, tmp_path):
        out = tmp_path / "output"
        first, old_tree = build_managed(repo, out)
        return out, Path(first["output"]), old_tree

    def test_builder_failure_keeps_log_and_old_output(self, repo, tmp_path):
        out, final, old_tree = self.managed(repo, tmp_path)
        cli = load_cli()

        def failing(argv, *, cwd, log, report):
            log.write_text("partial pyinstaller output", encoding="utf-8")
            raise cli.BuildError("injected build failure")

        result = cli.run_build(out, repo=repo, builder=failing)
        run, report = self.failed_run(result)
        assert "injected build failure" in report["error"]
        assert report["stage"] == "build"
        assert (run / "build.log").read_text("utf-8") == "partial pyinstaller output"
        assert tree(final) == old_tree
        assert not list(out.glob(".PageFolio-*.lock"))

    def test_interrupt_is_reported_not_success(self, repo, tmp_path):
        out = tmp_path / "output"

        def interrupted(argv, *, cwd, log, report):
            raise KeyboardInterrupt

        result = load_cli().run_build(out, repo=repo, builder=interrupted)
        self.failed_run(result)
        assert not (out / "PageFolio-v9.8.7").exists()
        assert not list(out.glob(".PageFolio-*.lock"))

    def test_missing_executable_fails(self, repo, tmp_path):
        out, final, old_tree = self.managed(repo, tmp_path)

        def empty(argv, *, cwd, log, report):
            Path(argv[argv.index("--distpath") + 1], "PageFolio").mkdir(parents=True)

        result = load_cli().run_build(out, repo=repo, builder=empty)
        self.failed_run(result)
        assert tree(final) == old_tree

    def test_copy_hash_mismatch_fails_before_publish(self, repo, tmp_path, monkeypatch):
        out, final, old_tree = self.managed(repo, tmp_path)
        cli = load_cli()
        real_copy = shutil.copyfile

        def corrupt(source, target, *args, **kwargs):
            real_copy(source, target, *args, **kwargs)
            if Path(target).name == "ocr_custom_prompt_sample.md":
                Path(target).write_bytes(b"corrupt")
            return target

        monkeypatch.setattr(cli.shutil, "copyfile", corrupt)
        result = cli.run_build(out, repo=repo, builder=FakeBuilder())
        run, report = self.failed_run(result)
        assert "SHA-256" in report["error"]
        assert tree(final) == old_tree
        assert (run / "dist/PageFolio/PageFolio.exe").is_file()

    def test_report_write_failure_is_not_success_and_rolls_back(
        self, repo, tmp_path, monkeypatch
    ):
        out, final, old_tree = self.managed(repo, tmp_path)
        cli = load_cli()
        real_write = cli._write_json

        def failing_write(path, value):
            if path.name == "report.json" and value.get("status") == "VERIFIED_BUILD":
                raise OSError("injected disk full")
            return real_write(path, value)

        monkeypatch.setattr(cli, "_write_json", failing_write)
        result = cli.run_build(out, repo=repo, builder=FakeBuilder(b"second"))
        run, report = self.failed_run(result)
        assert "injected disk full" in report["error"]
        assert report["stage"] != "complete"
        assert tree(final) == old_tree
        assert (run / "dist/PageFolio/PageFolio.exe").read_bytes() == b"second"

    def test_promote_failure_restores_previous_output(
        self, repo, tmp_path, monkeypatch
    ):
        out, final, old_tree = self.managed(repo, tmp_path)
        cli = load_cli()
        real_rename = Path.rename

        def failing(self, target):
            if self.name == "PageFolio":
                raise OSError("injected promote failure")
            return real_rename(self, target)

        monkeypatch.setattr(Path, "rename", failing)
        result = cli.run_build(out, repo=repo, builder=FakeBuilder(b"second"))
        run, report = self.failed_run(result)
        assert "injected promote failure" in report["error"]
        assert "rollback_error" not in report
        assert tree(final) == old_tree
        assert (run / "dist/PageFolio/PageFolio.exe").read_bytes() == b"second"

    def test_history_move_failure_leaves_old_output(self, repo, tmp_path, monkeypatch):
        out, final, old_tree = self.managed(repo, tmp_path)
        cli = load_cli()
        real_rename = Path.rename

        def failing(self, target):
            if self.name == "PageFolio-v9.8.7":
                raise OSError("injected history failure")
            return real_rename(self, target)

        monkeypatch.setattr(Path, "rename", failing)
        result = cli.run_build(out, repo=repo, builder=FakeBuilder(b"second"))
        run, _ = self.failed_run(result)
        assert tree(final) == old_tree
        assert (run / "dist/PageFolio/PageFolio.exe").read_bytes() == b"second"

    def test_rollback_failure_is_reported_and_history_kept(
        self, repo, tmp_path, monkeypatch
    ):
        out, final, old_tree = self.managed(repo, tmp_path)
        cli = load_cli()
        real_rename = Path.rename

        def failing(self, target):
            if self.name == "PageFolio" or self.parent.name == ".release-history":
                raise OSError(f"injected failure for {self.name}")
            return real_rename(self, target)

        monkeypatch.setattr(Path, "rename", failing)
        result = cli.run_build(out, repo=repo, builder=FakeBuilder(b"second"))
        run, report = self.failed_run(result)
        assert "injected failure" in report["error"]
        assert "injected failure" in report["rollback_error"]
        assert tree(Path(result["old_output"])) == old_tree
        assert (run / "dist/PageFolio/PageFolio.exe").read_bytes() == b"second"

    def test_post_publish_mismatch_restores_previous_output(
        self, repo, tmp_path, monkeypatch
    ):
        out, final, old_tree = self.managed(repo, tmp_path)
        cli = load_cli()
        real_rename = Path.rename

        def tamper(self, target):
            moved = real_rename(self, target)
            if self.name == "PageFolio":
                (Path(target) / "PageFolio.exe").write_bytes(b"tampered after copy")
            return moved

        monkeypatch.setattr(Path, "rename", tamper)
        result = cli.run_build(out, repo=repo, builder=FakeBuilder(b"second"))
        run, report = self.failed_run(result)
        assert "照合" in report["error"]
        assert tree(final) == old_tree
        assert (run / "dist/PageFolio/PageFolio.exe").read_bytes() == (
            b"tampered after copy"
        )

    def test_kept_lock_survives_unreclaimed_builder(self, repo, tmp_path):
        out = tmp_path / "output"

        def stuck(argv, *, cwd, log, report):
            report["keep_lock"] = True
            raise RuntimeError("child could not be reclaimed")

        result = load_cli().run_build(out, repo=repo, builder=stuck)
        self.failed_run(result)
        assert len(list(out.glob(".PageFolio-*.lock"))) == 1


class TestCommandLine:
    def test_success_exit_and_guidance(self, repo, tmp_path, capsys):
        code = load_cli().main(
            ["--output-root", str(tmp_path / "out")], builder=FakeBuilder(), repo=repo
        )
        shown = capsys.readouterr()
        assert code == 0
        assert "完全copy" in shown.out
        assert "未実施" in shown.out
        assert "承認済み" not in shown.out

    def test_failure_exit_is_nonzero_and_keeps_user_file(self, repo, tmp_path, capsys):
        out = tmp_path / "out"
        (out / "PageFolio-v9.8.7").mkdir(parents=True)
        (out / "PageFolio-v9.8.7/ocr_custom_prompt.md").write_bytes(b"mine")
        code = load_cli().main(
            ["--output-root", str(out)], builder=FakeBuilder(), repo=repo
        )
        shown = capsys.readouterr()
        assert code == 1
        assert "ビルド失敗" in shown.err
        assert (out / "PageFolio-v9.8.7/ocr_custom_prompt.md").read_bytes() == b"mine"


class TestGitAttributes:
    PATHS = (
        "dist/PageFolio/ocr_custom_prompt_sample.md",
        "dist/PageFolio/ocr_summary_prompt_sample.md",
        "distribution/samples/ocr_custom_prompt_sample.md",
        "distribution/samples/ocr_summary_prompt_sample.md",
    )

    @staticmethod
    def git(cwd, *args):
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        return subprocess.run(  # noqa: S603
            [GIT, "-C", str(cwd), *args],
            check=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            env=env,
        ).stdout

    def test_only_four_paths_are_unset(self):
        lines = [
            line.strip()
            for line in (ROOT / ".gitattributes").read_text("utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        assert sorted(lines) == sorted(f"{p} -text" for p in self.PATHS)

    def test_check_attr_reports_unset_only_for_the_four(self):
        out = self.git(ROOT, "check-attr", "text", "--", *self.PATHS, "README.md")
        states = {}
        for line in out.decode("utf-8").splitlines():
            name, _, state = line.partition(": text: ")
            states[name] = state
        assert {states[p] for p in self.PATHS} == {"unset"}
        assert states["README.md"] == "unspecified"

    def test_originals_and_canonical_copies_are_byte_identical(self):
        for old, new in (self.PATHS[0::2], self.PATHS[1::2]):
            assert (ROOT / old).read_bytes() == (ROOT / new).read_bytes()
        assert b"\r\n" in (ROOT / self.PATHS[0]).read_bytes()

    def test_index_blobs_match_worktree_bytes(self):
        for path in self.PATHS:
            blob = self.git(ROOT, "show", f":{path}")
            assert blob == (ROOT / path).read_bytes()

    def test_autocrlf_true_isolated_fixture_keeps_bytes(self, tmp_path):
        work = tmp_path / "fixture"
        for path in (*self.PATHS, ".gitattributes"):
            (work / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, work / path)
        self.git(work, "init", "-q")
        self.git(work, "config", "core.autocrlf", "true")
        self.git(work, "add", "-A")
        self.git(
            work,
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "commit",
            "-q",
            "-m",
            "fixture",
        )
        for path in self.PATHS:
            original = (ROOT / path).read_bytes()
            assert self.git(work, "cat-file", "blob", f"HEAD:{path}") == original
            (work / path).unlink()
            self.git(work, "checkout", "--", path)
            assert (work / path).read_bytes() == original
