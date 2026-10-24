"""実配布EXE受入の外側支援(tests/release_uat_support.py, release_fake_ocr.py)の契約。

これらは支援ツール自体の試験であり、親ゲートや人手受入の実証拠ではない。全fixtureは
tmp_pathだけで完結し、06-04で初めて作る実配布物を前提にしない。
"""

from __future__ import annotations

import ast
import base64
import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import pytest

from tests import release_fake_ocr as fake
from tests import release_uat_support as sup

windows_only = pytest.mark.skipif(os.name != "nt", reason="Windows専用の観測")
VERSION = "v1.10.0"
CANON = {
    "ocr_custom_prompt_sample.md": "distribution/samples/ocr_custom_prompt_sample.md",
    "ocr_summary_prompt_sample.md": "distribution/samples/ocr_summary_prompt_sample.md",
    "はじめに.md": "distribution/はじめに.md",
    "docs/CONFIGURATION.md": "docs/CONFIGURATION.md",
}


# ---------------------------------------------------------------------------
# 共通fixture
# ---------------------------------------------------------------------------
def make_repo(root):
    root = Path(root)
    (root / "pagefolio").mkdir(parents=True)
    (root / "pagefolio/constants.py").write_text(
        f'APP_VERSION = "{VERSION}"\n'
        'SETTINGS_FILE = "pagefolio_settings.json"\n'
        'CUSTOM_PROMPT_FILE = "ocr_custom_prompt.md"\n'
        'SUMMARY_PROMPT_FILE = "ocr_summary_prompt.md"\n',
        encoding="utf-8",
    )
    for name, rel in CANON.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"canon {name}\n", encoding="utf-8")
    return root


def make_dist(root, repo, *, version=VERSION, exe=b"MZ-fake-exe", run_id=None):
    """検証済みbuildと同じ形(report manifest付き)の配布tree。"""
    root = Path(root)
    root.mkdir(parents=True)
    (root / "PageFolio.exe").write_bytes(exe)
    (root / "_internal").mkdir()
    (root / "_internal/lib.bin").write_bytes(b"lib" + exe[:8])
    for name, rel in CANON.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(repo) / rel, target)
    files, dirs = sup.walk_tree(root)
    report = {
        "run_id": run_id or uuid.uuid4().hex,
        "success": True,
        "status": "VERIFIED_BUILD",
        "version": version,
        "python": "3.13 (embedded)",
        "dependencies": {"PyInstaller": "6"},
        "distribution_manifest": files,
        "distribution_directories": dirs,
    }
    (root / "release-report.json").write_text(json.dumps(report), encoding="utf-8")
    return root


def cmd_bytes():
    return Path(os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")).read_bytes()


@pytest.fixture
def repo(tmp_path):
    return make_repo(tmp_path / "repo")


@pytest.fixture
def children():
    items = []
    yield items
    for child in items:
        try:
            if child.stdin:
                child.stdin.close()
            child.kill()
            child.wait(timeout=5)
        except Exception as error:  # noqa: BLE001 - 後始末の失敗は握りつぶす
            _ = error


def piped_popen(children):
    def popen(argv, **kwargs):
        kwargs["stdin"] = subprocess.PIPE
        child = subprocess.Popen(argv, **kwargs)  # noqa: S603
        children.append(child)
        return child

    return popen


def prep(tmp_path, repo, *, exe=b"MZ-fake-exe", case="W01", name="dist", **kw):
    dist = make_dist(tmp_path / name, repo, exe=exe)
    return sup.prepare(
        dist, case, base=tmp_path / "runs", repo=repo, run_id=uuid.uuid4().hex, **kw
    )


# ---------------------------------------------------------------------------
class TestIsolation:
    def test_support_never_imports_the_product(self):
        for name in ("release_uat_support.py", "release_fake_ocr.py"):
            tree = ast.parse((Path(__file__).parent / name).read_text("utf-8"))
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [node.module or ""]
                assert not any(m.split(".")[0] == "pagefolio" for m in modules)

    def test_prepare_copies_whole_tree_and_pins_hashes(self, tmp_path, repo):
        dist = make_dist(tmp_path / "dist", repo)
        before = sup.walk_tree(dist)
        manifest = sup.prepare(dist, "W01", base=tmp_path / "runs", repo=repo)
        copied = Path(manifest["copy"])
        assert sup.walk_tree(copied) == before
        assert manifest["status"] == "prepared"
        assert manifest["source"]["exe_sha256"] == sup.sha_file(
            copied / "PageFolio.exe"
        )
        assert manifest["evidence_kind"] == "production-exe"
        assert sup.walk_tree(dist) == before  # 配布元は不変
        assert Path(manifest["run"]).parent == tmp_path / "runs"

    @pytest.mark.parametrize("damage", ["extra", "modified", "missing"])
    def test_prepare_rejects_tree_not_matching_report(self, tmp_path, repo, damage):
        dist = make_dist(tmp_path / "dist", repo)
        if damage == "extra":
            (dist / "stray.txt").write_text("x")
        elif damage == "modified":
            (dist / "PageFolio.exe").write_bytes(b"tampered")
        else:
            (dist / "_internal/lib.bin").unlink()
        with pytest.raises(sup.IsolationError):
            sup.prepare(dist, "W01", base=tmp_path / "runs", repo=repo)
        assert not list((tmp_path / "runs").glob("release-uat-*"))

    def test_prepare_rejects_unverified_report_and_bad_arguments(self, tmp_path, repo):
        dist = make_dist(tmp_path / "dist", repo)
        report = json.loads((dist / "release-report.json").read_text("utf-8"))
        report["status"] = "INCOMPLETE"
        (dist / "release-report.json").write_text(json.dumps(report), encoding="utf-8")
        with pytest.raises(sup.IsolationError):
            sup.prepare(dist, "W01", base=tmp_path / "runs", repo=repo)
        good = make_dist(tmp_path / "good", repo)
        with pytest.raises(sup.SupportError):
            sup.prepare(good, "../W01", base=tmp_path / "runs", repo=repo)
        with pytest.raises(sup.SupportError):
            sup.prepare(
                good, "W01", evidence_kind="oral", base=tmp_path / "runs", repo=repo
            )

    def test_prepare_rejects_links(self, tmp_path, repo):
        dist = make_dist(tmp_path / "dist", repo)
        try:
            os.symlink(dist / "PageFolio.exe", dist / "link.exe")
        except OSError:  # 権限が無ければjunction(reparse point)で代替する
            cmd = os.environ.get("COMSPEC", "cmd.exe")
            made = subprocess.run(  # noqa: S603
                [cmd, "/c", "mklink", "/J", str(dist / "jct"), str(dist / "_internal")],
                capture_output=True,
                check=False,
            )
            if made.returncode != 0:
                pytest.skip("symlink/junctionを作れません")
        with pytest.raises(sup.IsolationError):
            sup.prepare(dist, "W01", base=tmp_path / "runs", repo=repo)

    def test_cli_prepare_builds_run_and_fixture_pdf(self, tmp_path, repo, capsys):
        dist = make_dist(tmp_path / "dist", repo)
        code = sup.main(
            [
                "prepare",
                "--distribution",
                str(dist),
                "--case",
                "W04",
                "--base",
                str(tmp_path / "runs"),
                "--pdf",
                "ocr-one-page",
            ]
        )
        out = json.loads(capsys.readouterr().out)
        assert code == 0 and out["status"] == "prepared"
        assert out["fixtures"]["ocr-one-page"]["pages"] == 1
        assert (
            sup.main(
                [
                    "prepare",
                    "--distribution",
                    str(tmp_path / "none"),
                    "--case",
                    "W04",
                    "--base",
                    str(tmp_path / "runs"),
                ]
            )
            == 2
        )

    def test_overlay_is_separate_from_distribution_manifest(self, tmp_path, repo):
        manifest = prep(tmp_path, repo)
        run = manifest["run"]
        sup.declare_overlay(run, {"pagefolio_settings.json": b"{}"}, "合成設定")
        manifest = sup.load_run(run)
        assert (
            manifest["overlay"]["pagefolio_settings.json"]
            == hashlib.sha256(b"{}").hexdigest()
        )
        assert "pagefolio_settings.json" not in manifest["distribution_manifest"]
        check = sup.verify_copy(manifest)
        assert check["ok"] and not check["overlay_changed"]
        Path(manifest["copy"], "pagefolio_settings.json").write_bytes(b'{"a":1}')
        check = sup.verify_copy(manifest)  # 明示保存相当はoverlay差分として別に見える
        assert check["ok"] and check["overlay_changed"] == ["pagefolio_settings.json"]

    def test_undeclared_overlay_and_distribution_diffs_are_rejected(
        self, tmp_path, repo
    ):
        manifest = prep(tmp_path, repo)
        run = manifest["run"]
        with pytest.raises(sup.IsolationError):
            sup.declare_overlay(run, {"evil.dll": b"x"}, "未宣言名")
        with pytest.raises(sup.IsolationError):
            sup.declare_overlay(run, {"PageFolio.exe": b"x"}, "配布項目")
        copy_dir = Path(manifest["copy"])
        (copy_dir / "undeclared.txt").write_text("x")
        check = sup.verify_copy(manifest)
        assert not check["ok"] and check["undeclared"] == ["undeclared.txt"]
        (copy_dir / "undeclared.txt").unlink()
        (copy_dir / "PageFolio.exe").write_bytes(b"changed")
        check = sup.verify_copy(manifest)
        assert not check["ok"] and check["distribution_changed"] == ["PageFolio.exe"]

    @windows_only
    def test_start_refuses_dirty_copy_before_launching(self, tmp_path, repo):
        manifest = prep(tmp_path, repo)
        Path(manifest["copy"], "PageFolio.exe").write_bytes(b"changed")

        def forbidden(*args, **kwargs):
            raise AssertionError("差分があるのに起動された")

        with pytest.raises(sup.IsolationError):
            sup.start(manifest["run"], popen=forbidden, settle=0)

    def test_reset_for_case_restores_overlay_or_demands_fresh_copy(
        self, tmp_path, repo
    ):
        manifest = prep(tmp_path, repo)
        run = manifest["run"]
        sup.declare_overlay(run, {"pagefolio_settings.json": b"{}"}, "初期")
        copy_dir = Path(manifest["copy"])
        (copy_dir / "pagefolio_settings.json").write_bytes(b'{"saved": 1}')
        (copy_dir / "ocr_custom_prompt.md").write_text("app-created")  # 無断生成
        with pytest.raises(sup.IsolationError):
            sup.reset_for_case(run, "W02")  # 未宣言ファイル=同一性不明→新copy
        (copy_dir / "ocr_custom_prompt.md").unlink()
        again = sup.reset_for_case(run, "W02")
        assert (copy_dir / "pagefolio_settings.json").read_bytes() == b"{}"
        assert again["case"] == "W02" and again["generation"] == 2
        assert again["case_history"][0]["case"] == "W01"
        (copy_dir / "_internal/lib.bin").write_bytes(b"changed")
        with pytest.raises(sup.IsolationError):
            sup.reset_for_case(run, "W03")

    def test_snapshots_keep_original_user_files_unchanged(self, tmp_path, repo):
        (repo / "pagefolio_settings.json").write_text('{"user": true}', "utf-8")
        before = sup.snapshot_originals(repo)
        manifest = prep(tmp_path, repo)
        item = sup.snapshot(manifest["run"], "during")
        assert item["originals"] == before
        assert item["source_unchanged"] is True
        assert before["pagefolio_settings.json"]["exists"] is True
        assert before["ocr_custom_prompt.md"]["exists"] is False

    def test_fixture_pdfs_are_separate_and_match_card_contract(self, tmp_path, repo):
        manifest = prep(tmp_path, repo)
        one = sup.add_fixture_pdf(manifest["run"], "ocr-one-page")
        three = sup.add_fixture_pdf(manifest["run"], "edit-three-page")
        assert one["pages"] == 1 and one["has_embedded_text"] is False
        assert one["images_on_first_page"] == 1
        assert three["pages"] == 3 and three["sha256"] != one["sha256"]
        # PDFは配布copyの外(run/fixtures)にあり、配布treeを汚さない
        assert Path(one["path"]).parent == Path(manifest["run"]) / "fixtures"
        assert sup.verify_copy(sup.load_run(manifest["run"]))["ok"]


# ---------------------------------------------------------------------------
def hold_mutex(prefix):
    api = sup._api()
    handle = api.k.CreateMutexW(None, False, f"Local\\{prefix}.Owner")
    assert handle
    return handle


@windows_only
class TestOwnership:
    def exe_run(self, tmp_path, repo, name="dist", **kw):
        return prep(tmp_path, repo, exe=cmd_bytes(), name=name, **kw)

    def test_probe_owner_is_read_only_and_detects_existing(self):
        prefix = f"PageFolio.UatTest.{uuid.uuid4().hex}"
        assert sup.probe_owner(prefix) == []
        handle = hold_mutex(prefix)
        try:
            found = sup.probe_owner(prefix)
            assert [f["kind"] for f in found] == ["mutex"]
        finally:
            sup._api().k.CloseHandle(handle)
        assert sup.probe_owner(prefix) == []

    def test_start_refuses_when_production_owner_exists(self, tmp_path, repo):
        prefix = f"PageFolio.UatTest.{uuid.uuid4().hex}"
        manifest = self.exe_run(tmp_path, repo)
        handle = hold_mutex(prefix)

        def forbidden(*args, **kwargs):
            raise AssertionError("既存ownerがあるのに起動された")

        try:
            with pytest.raises(sup.OwnershipError):
                sup.start(
                    manifest["run"], popen=forbidden, owner_prefix=prefix, settle=0
                )
        finally:
            sup._api().k.CloseHandle(handle)
        assert sup.load_run(manifest["run"])["last_refusal"]["reason"] == (
            "existing-owner"
        )
        assert sup.load_run(manifest["run"])["processes"] == []

    def test_start_records_pid_creation_time_and_unmodified_launch(
        self, tmp_path, repo, children
    ):
        prefix = f"PageFolio.UatTest.{uuid.uuid4().hex}"
        manifest = self.exe_run(tmp_path, repo)
        seen = {}

        def spying(argv, **kwargs):
            seen["argv"] = list(argv)
            return piped_popen(children)(argv, **kwargs)

        record = sup.start(manifest["run"], popen=spying, owner_prefix=prefix, settle=0)
        exe = Path(manifest["copy"]) / "PageFolio.exe"
        assert seen["argv"] == [str(exe)]  # 引数・nonceなしで起動
        identity = sup.process_identity(record["pid"])
        assert sup.same_process(record, identity) and identity["alive"]
        assert sup._norm_path(record["image"]) == sup._norm_path(exe)
        assert record["exe_sha256"] == manifest["source"]["exe_sha256"]
        saved = sup.load_run(manifest["run"])
        assert saved["status"] == "running"
        observation = saved["observations"][-1]
        assert observation["processes"][0]["identity"] == "same"
        assert "python" in observation["observer"]  # 観測者の版は別欄
        assert observation["exe_embedded"]["python"] == "3.13 (embedded)"
        assert "foreground" in observation and "pid" in observation["foreground"]
        assert (Path(manifest["run"]) / "evidence" / "inspect-001.json").is_file()
        # 稼働中の再startは拒否される
        with pytest.raises(sup.OwnershipError):
            sup.start(manifest["run"], popen=spying, owner_prefix=prefix, settle=0)
        sup.stop(manifest["run"], timeout=0.3)

    def test_stop_reclaims_only_the_owned_process_after_diagnostics(
        self, tmp_path, repo, children
    ):
        prefix = f"PageFolio.UatTest.{uuid.uuid4().hex}"
        manifest = self.exe_run(tmp_path, repo)
        bystander = subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdin=subprocess.DEVNULL,
        )
        children.append(bystander)
        record = sup.start(
            manifest["run"], popen=piped_popen(children), owner_prefix=prefix, settle=0
        )
        results = sup.stop(manifest["run"], timeout=0.3)
        assert results == [{"pid": record["pid"], "result": "terminated"}]
        assert (
            sup.process_identity(record["pid"]) is None
            or not (sup.process_identity(record["pid"])["alive"])
        )
        diagnostics = Path(manifest["run"]) / "evidence"
        assert (diagnostics / f"stop-diagnostics-{record['pid']}.json").is_file()
        assert bystander.poll() is None  # 無関係processは無傷
        assert sup.load_run(manifest["run"])["status"] == "stopped"

    def test_stop_refuses_to_touch_mismatched_identity(self, tmp_path, repo, children):
        prefix = f"PageFolio.UatTest.{uuid.uuid4().hex}"
        manifest = self.exe_run(tmp_path, repo)
        record = sup.start(
            manifest["run"], popen=piped_popen(children), owner_prefix=prefix, settle=0
        )
        saved = sup.load_run(manifest["run"])
        saved["processes"][0]["created"] += 1  # PID再利用を模す
        sup.save_run(saved)
        results = sup.stop(manifest["run"], timeout=0.3)
        assert results[0]["result"] == "identity-mismatch"
        assert children[0].poll() is None  # 触れていない
        assert sup.process_identity(record["pid"])["alive"]

    def test_stop_records_already_exited_process(self, tmp_path, repo, children):
        prefix = f"PageFolio.UatTest.{uuid.uuid4().hex}"
        manifest = self.exe_run(tmp_path, repo)
        sup.start(
            manifest["run"], popen=piped_popen(children), owner_prefix=prefix, settle=0
        )
        children[0].kill()
        children[0].wait(timeout=5)
        assert sup.stop(manifest["run"], timeout=0.3)[0]["result"] == "already-exited"

    def test_start_kills_own_child_when_image_does_not_match(
        self, tmp_path, repo, children
    ):
        prefix = f"PageFolio.UatTest.{uuid.uuid4().hex}"
        manifest = self.exe_run(tmp_path, repo)

        def other_image(argv, **kwargs):
            child = subprocess.Popen(  # noqa: S603
                [sys.executable, "-c", "import time; time.sleep(60)"],
                stdin=subprocess.DEVNULL,
            )
            children.append(child)
            return child

        with pytest.raises(sup.OwnershipError):
            sup.start(manifest["run"], popen=other_image, owner_prefix=prefix, settle=0)
        children[0].wait(timeout=5)  # 自分の子だけ回収される

    def test_peer_requires_live_verified_primary_and_established_owner(
        self, tmp_path, repo, children
    ):
        prefix = f"PageFolio.UatTest.{uuid.uuid4().hex}"
        manifest = self.exe_run(tmp_path, repo)
        tracer = self.exe_run(
            tmp_path,
            repo,
            name="tracer",
            role="technical-tracer-real-exe",
        )

        def forbidden(*args, **kwargs):
            raise AssertionError("送信すべきでないのに起動された")

        with pytest.raises(sup.OwnershipError):  # 一次なし
            sup.peer(manifest["run"], popen=forbidden, owner_prefix=prefix)
        sup.start(
            manifest["run"], popen=piped_popen(children), owner_prefix=prefix, settle=0
        )
        with pytest.raises(sup.OwnershipError):  # owner未確立
            sup.peer(manifest["run"], popen=forbidden, owner_prefix=prefix)
        handle = hold_mutex(prefix)
        try:
            record = sup.peer(
                manifest["run"],
                with_run=tracer["run"],
                popen=piped_popen(children),
                owner_prefix=prefix,
            )
        finally:
            sup._api().k.CloseHandle(handle)
        saved = sup.load_run(manifest["run"])
        assert record["role"] == "peer"
        assert saved["subject"]["role"] == "final-release-candidate"
        assert saved["peer"]["role"] == "technical-tracer-real-exe"
        assert saved["peer"]["run_id"] == tracer["run_id"]
        assert len(sup.stop(manifest["run"], timeout=0.3)) == 2

    def test_reset_for_case_refuses_while_owned_process_lives(
        self, tmp_path, repo, children
    ):
        prefix = f"PageFolio.UatTest.{uuid.uuid4().hex}"
        manifest = self.exe_run(tmp_path, repo)
        sup.start(
            manifest["run"], popen=piped_popen(children), owner_prefix=prefix, settle=0
        )
        with pytest.raises(sup.OwnershipError):
            sup.reset_for_case(manifest["run"], "W02")
        sup.stop(manifest["run"], timeout=0.3)
        assert sup.reset_for_case(manifest["run"], "W02")["generation"] == 2

    def test_window_and_foreground_observation_shapes(self):
        assert isinstance(sup.windows_of(os.getpid()), list)
        info = sup.foreground_info()
        assert {"hwnd", "pid", "title"} <= set(info)
        env = sup.collect_environment()
        assert env["session_id"] is not None and "observer_python" in env


# ---------------------------------------------------------------------------
def png_b64(color="white"):
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (12, 12), color).save(buffer, "PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def provider(server, timeout=10):
    from pagefolio.ocr_providers import OllamaProvider

    return OllamaProvider(server.url, fake.MODEL, timeout=timeout)


@pytest.fixture
def server(tmp_path):
    items = []

    def make(**kwargs):
        item = fake.FakeOcrServer(run_id="r" * 8, **kwargs).start()
        items.append(item)
        return item

    yield make
    for item in items:
        item.stop()


class TestFakeOcr:
    def test_listens_on_loopback_only_and_never_forwards(self, server):
        with pytest.raises(ValueError):
            fake.FakeOcrServer(host="0.0.0.0")  # noqa: S104
        item = server()
        assert item._httpd.server_address[0] == "127.0.0.1"
        assert item.url.startswith("http://127.0.0.1:")
        tree = ast.parse(
            (Path(__file__).parent / "release_fake_ocr.py").read_text("utf-8")
        )
        imported = {
            (n.module or "") if isinstance(n, ast.ImportFrom) else a.name
            for n in ast.walk(tree)
            if isinstance(n, (ast.Import, ast.ImportFrom))
            for a in (n.names if isinstance(n, ast.Import) else [None])
        }
        assert not {"urllib.request", "http.client", "requests", "socket"} & imported

    def test_models_and_chat_shapes_work_with_existing_ollama_provider(self, server):
        item = server()
        client = provider(item)
        assert client.list_models() == [fake.MODEL]
        assert client.ocr_image(png_b64(), "p") == fake.RESULT_TEXT
        ok, reasons = item.single_attempt_ok(1)
        assert ok, reasons

    def test_settings_match_what_build_provider_consumes(self, server, tmp_path, repo):
        from pagefolio.ocr import build_provider
        from pagefolio.ocr_providers import OllamaProvider

        item = server()
        settings = sup.ocr_settings(item.url)
        built = build_provider(settings)
        assert isinstance(built, OllamaProvider)
        assert built.url == item.url and built.model == fake.MODEL
        assert settings["ocr_concurrency"] == 1
        assert settings["ocr_fallback_enabled"] is False
        manifest = prep(tmp_path, repo, case="W04")
        info = sup.prepare_ocr_connection(manifest["run"], item)
        saved = json.loads(
            (Path(manifest["copy"]) / "pagefolio_settings.json").read_text("utf-8")
        )
        assert saved == settings
        assert info["pdf"]["pages"] == 1 and info["pdf"]["has_embedded_text"] is False
        assert info["expected_posts"] == 1 and info["summary_executed"] is False
        assert sup.verify_copy(sup.load_run(manifest["run"]))["ok"]

    def test_hold_then_release_records_the_same_attempt(self, server, tmp_path):
        item = server(mode="hold", log_path=tmp_path / "events.jsonl")
        outcome = {}
        worker = threading.Thread(
            target=lambda: outcome.update(text=provider(item).ocr_image(png_b64(), "p"))
        )
        worker.start()
        assert item.wait_received(1)
        assert item.summary()["completed"] == []  # 待機中は完了していない
        item.release()
        worker.join(timeout=10)
        data = item.summary()
        assert outcome["text"] == fake.RESULT_TEXT
        received = [e for e in data["events"] if e["event"] == "received"][0]
        assert data["released"] == data["completed"] == [received["attempt_id"]]
        assert received["page_id"] == "p1" and len(received["image_sha256"]) == 64
        assert item.single_attempt_ok(1)[0]
        lines = (tmp_path / "events.jsonl").read_text("utf-8").splitlines()
        assert [json.loads(x)["event"] for x in lines] == [
            "received",
            "released",
            "completed",
        ]

    def test_release_flag_file_releases_a_held_request(self, server, tmp_path):
        flag = tmp_path / "release.flag"
        item = server(mode="hold", release_flag=flag)
        worker = threading.Thread(
            target=lambda: provider(item).ocr_image(png_b64(), "p")
        )
        worker.start()
        assert item.wait_received(1)
        flag.write_text("go")
        worker.join(timeout=10)
        assert not worker.is_alive() and item.single_attempt_ok(1)[0]

    def test_retransmission_keeps_original_attempt_and_fails_single_expectation(
        self, server
    ):
        item = server()
        image = png_b64()
        provider(item).ocr_image(image, "p")
        provider(item).ocr_image(image, "p")
        data = item.summary()
        assert data["posts"] == 2 and len(data["retransmissions"]) == 1
        ids = data["retransmissions"][0]["attempt_ids"]
        assert ids[0].endswith("-1") and ids[1].endswith("-2")
        ok, reasons = item.single_attempt_ok(1)
        assert not ok and any("再送" in r for r in reasons)

    def test_page_count_is_not_projected_into_request_count(self, server):
        item = server(expected_pages=1)
        provider(item).ocr_image(png_b64("white"), "p")
        with pytest.raises(RuntimeError):  # 409: 対象外の別画像は拒否される
            provider(item).ocr_image(png_b64("black"), "p")
        data = item.summary()
        assert data["posts"] == 1 and len(data["rejected"]) == 1
        assert not item.single_attempt_ok(1)[0]
        wide = server(expected_pages=3)
        for color in ("white", "black", "red"):
            provider(wide).ocr_image(png_b64(color), "p")
        assert wide.summary()["posts"] == 3 and wide.single_attempt_ok(3)[0]

    def test_strict_registration_rejects_unregistered_images(self, server):
        item = server()
        item.allow_image(hashlib.sha256(base64.b64decode(png_b64("white"))).hexdigest())
        provider(item).ocr_image(png_b64("white"), "p")
        with pytest.raises(RuntimeError):
            provider(item).ocr_image(png_b64("black"), "p")

    def test_non_synthetic_or_malformed_input_is_rejected(self, server):
        item = server()
        import urllib.error
        import urllib.request

        def post(body):
            request = urllib.request.Request(  # noqa: S310
                item.url + "/v1/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            return urllib.request.urlopen(request, timeout=5)  # noqa: S310

        for body in (
            {"messages": [{"role": "user", "content": "text only"}]},
            {
                "messages": [
                    {
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": "data:image/png;base64,AAAA"},
                            }
                        ]
                    }
                ]
            },
            {
                "messages": [
                    {
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": "https://example.com/x.png"},
                            }
                        ]
                    }
                ]
            },
        ):
            with pytest.raises(urllib.error.HTTPError) as caught:
                post(body)
            assert caught.value.code == 400
        assert item.summary()["posts"] == 0 and len(item.summary()["rejected"]) == 3

    def test_error_mode_never_uses_retry_inducing_status(self, server):
        for status in (429, 500, 503):
            with pytest.raises(ValueError):
                fake.FakeOcrServer(mode="error", error_status=status)
        item = server(mode="error", error_status=400)
        with pytest.raises(RuntimeError):
            provider(item).ocr_image(png_b64(), "p")
        assert item.summary()["completed"]

    def test_hold_limit_is_shorter_than_provider_timeout_and_expiry_is_visible(
        self, server
    ):
        with pytest.raises(ValueError):
            fake.FakeOcrServer(mode="hold", provider_timeout=10, hold_limit=10)
        item = server(mode="hold", provider_timeout=5, hold_limit=0.3)
        started = time.monotonic()
        assert provider(item, timeout=5).ocr_image(png_b64(), "p") == fake.RESULT_TEXT
        assert time.monotonic() - started < 5
        ok, reasons = item.single_attempt_ok(1)
        assert not ok and any("待機上限" in r for r in reasons)

    def test_models_endpoint_and_unknown_paths(self, server):
        import urllib.error
        import urllib.request

        item = server()
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(item.url + "/api/tags", timeout=5)  # noqa: S310
        assert caught.value.code == 404

    def test_connection_entry_is_labeled_preparation_not_acceptance(
        self, server, tmp_path, repo
    ):
        item = server()
        provider(item).ocr_image(png_b64(), "p")
        manifest = prep(tmp_path, repo, case="W04")
        entry = sup.build_connection_entry(
            manifest["run"], item.summary(), user_answer="W04準備：結果表示を確認"
        )
        assert entry["purpose"] == "connection-preparation"
        assert entry["binary_sha256"] == manifest["source"]["exe_sha256"]
        assert entry["server"]["posts"] == 1 and len(entry["server"]["attempts"]) == 1
        assert [e["event"] for e in entry["server"]["events"]] == [
            "received",
            "completed",
        ]


# ---------------------------------------------------------------------------
@windows_only
class TestLockedOverlayVerification:
    """X03の排他lock中でも、宣言済みoverlayだけは起動/観測の照合を止めない(06-04で判明)。"""

    def test_held_overlay_is_reported_not_fatal_and_verified_after_release(
        self, tmp_path, repo
    ):
        data = b'{"theme": "dark"}'
        manifest = prep(tmp_path, repo, overlays={sup.SETTINGS_NAME: data})
        settings = Path(manifest["copy"]) / sup.SETTINGS_NAME
        with sup.prepare_settings_fault(manifest["copy"], "unreadable"):
            with pytest.raises(PermissionError):
                sup.sha_file(settings)  # 実際に読めない状態である
            check = sup.verify_copy(manifest)
            assert check["ok"] is True
            assert check["overlay_changed"] == []
            assert check["locked_unverified"] == [sup.SETTINGS_NAME]
        released = sup.verify_copy(manifest)
        assert released["locked_unverified"] == []
        assert released["overlay_changed"] == []
        assert sup.sha_file(settings) == hashlib.sha256(data).hexdigest()

    def test_held_distribution_file_still_fails_closed(self, tmp_path, repo):
        manifest = prep(tmp_path, repo)
        target = Path(manifest["copy"]) / "_internal/lib.bin"
        handle = sup._hold(target, sup.GENERIC_READ, 0)
        try:
            with pytest.raises(PermissionError):
                sup.verify_copy(manifest)
        finally:
            sup._api().k.CloseHandle(handle)

    def test_held_overlay_declared_absent_is_flagged_as_changed(self, tmp_path, repo):
        manifest = prep(tmp_path, repo, overlays={sup.SETTINGS_NAME: None})
        settings = Path(manifest["copy"]) / sup.SETTINGS_NAME
        settings.write_bytes(b"{}")  # 不存在宣言なのに存在する(無断作成相当)
        handle = sup._hold(settings, sup.GENERIC_READ, 0)
        try:
            check = sup.verify_copy(manifest)
            assert check["overlay_changed"] == [sup.SETTINGS_NAME]
        finally:
            sup._api().k.CloseHandle(handle)


# ---------------------------------------------------------------------------
@windows_only
class TestSettingsFaultPreparation:
    @pytest.fixture
    def area(self, tmp_path, monkeypatch):
        import pagefolio.settings as settings_mod

        directory = tmp_path / "copy"
        directory.mkdir()
        path = directory / "pagefolio_settings.json"
        monkeypatch.setattr(settings_mod, "_get_settings_path", lambda: str(path))
        return directory, path, settings_mod

    def test_missing_is_absent_and_product_classifies_it(self, area):
        directory, path, mod = area
        with sup.prepare_settings_fault(directory, "missing") as fault:
            assert fault.record["established"] is True
            assert mod._load_settings_result().status == "missing"
        path.write_text("{}")
        with pytest.raises(sup.NotEstablished):
            sup.prepare_settings_fault(directory, "missing")

    def test_corrupt_bytes_are_classified_corrupt_by_the_product(self, area):
        directory, path, mod = area
        with sup.prepare_settings_fault(directory, "corrupt") as fault:
            assert fault.record["json_parseable"] is False
            assert mod._load_settings_result().status == "corrupt"

    def test_unreadable_uses_external_share_restriction(self, area):
        directory, path, mod = area
        path.write_text('{"theme": "dark"}', "utf-8")
        before = hashlib.sha256(path.read_bytes())
        with sup.prepare_settings_fault(directory, "unreadable") as fault:
            record = fault.record
            assert record["probe_read"]["win32_error"] == sup.ERROR_SHARING_VIOLATION
            assert record["handle"]["share"] == hex(0)
            assert record["observer"]["pid"] == os.getpid()
            assert record["observer"]["created"] > 0
            assert mod._load_settings_result().status == "unreadable"
        assert mod._load_settings_result().status == "ok"  # 解放後は読める
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before.hexdigest()

    def test_save_write_is_tmp_collision_before_any_write(self, area):
        directory, path, mod = area
        path.write_text('{"theme": "dark"}', "utf-8")
        original = hashlib.sha256(path.read_bytes()).hexdigest()
        with sup.prepare_settings_fault(directory, "save-write") as fault:
            tmp = Path(str(path) + ".tmp")
            assert fault.record["tmp"]["exclusive_create_collision"] is True
            assert "書込途中失敗ではない" in fault.record["note"]
            assert mod._save_settings({"theme": "light"}) is False
            assert tmp.exists() and tmp.read_bytes() == b"uat-owned-tmp"  # 削除されない
            assert hashlib.sha256(path.read_bytes()).hexdigest() == original

    def test_save_replace_blocks_delete_share_and_keeps_original(self, area):
        directory, path, mod = area
        path.write_text('{"theme": "dark"}', "utf-8")
        original = hashlib.sha256(path.read_bytes()).hexdigest()
        with sup.prepare_settings_fault(directory, "save-replace") as fault:
            record = fault.record
            assert record["probe_delete"]["win32_error"] == sup.ERROR_SHARING_VIOLATION
            assert record["probe_read"]["ok"] is True
            assert mod._save_settings({"theme": "light"}) is False
            assert not Path(str(path) + ".tmp").exists()  # 所有tmpは消去される
            assert hashlib.sha256(path.read_bytes()).hexdigest() == original
        assert mod._save_settings({"theme": "light"}) is True  # 解放後は保存できる

    def test_unestablished_fault_is_not_run_and_releases_handles(self, area):
        directory, path, mod = area
        with pytest.raises(sup.NotEstablished):  # 合成設定が無い
            sup.prepare_settings_fault(directory, "unreadable")
        with pytest.raises(sup.SupportError):
            sup.prepare_settings_fault(directory, "unknown-kind")

    @pytest.mark.parametrize(
        "kind", ["missing", "corrupt", "unreadable", "save-write", "save-replace"]
    )
    def test_fault_cli_keeps_copy_consistent_with_overlay_manifest(
        self, tmp_path, repo, capsys, kind
    ):
        manifest = prep(tmp_path, repo, case="X03")
        run = manifest["run"]
        code = sup.main(
            ["fault", "--run", str(run), "--kind", kind, "--hold-seconds", "0.2"]
        )
        record = json.loads(capsys.readouterr().out)
        assert code == 0 and record["established"] is True
        check = sup.verify_copy(sup.load_run(run))
        assert check["ok"] and check["overlay_changed"] == []  # 起動前の拒否理由が無い

    def test_fault_overlay_names_stay_inside_declared_set(self, tmp_path, repo):
        manifest = prep(tmp_path, repo, case="X03")
        run = manifest["run"]
        sup.declare_overlay(run, {"pagefolio_settings.json": b"{}"}, "障害準備")
        sup.declare_overlay(run, {"pagefolio_settings.json.tmp": b"t"}, "tmp衝突")
        assert sup.verify_copy(sup.load_run(run))["ok"]


# ---------------------------------------------------------------------------
# 証拠audit
# ---------------------------------------------------------------------------
def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Phase:
    """tmp_path内だけで完結する一貫した証拠一式(本番台帳にはコピーしない)。"""

    def __init__(self, tmp_path):
        self.root = make_repo(tmp_path / "repo")
        self.phase = self.root / ".planning/phases/06-release-validation"
        self.phase.mkdir(parents=True)
        self.out = tmp_path / "output-root"
        self.tmp = tmp_path
        self.run_ids = {k: uuid.uuid4().hex for k in ("initial", "rebuild")}
        self.make_build()
        self.manual = self.make_manual()
        self.protection, self.prep_text = self.make_protection()
        self.quality = self.make_quality()
        self.gate = self.make_gate()
        self.write_all()

    # -- build -----------------------------------------------------------
    def make_build(self):
        history = self.out / ".release-history" / self.run_ids["rebuild"]
        final = self.out / f"PageFolio-{VERSION}"
        trees = {}
        for order, directory in (("initial", history), ("rebuild", final)):
            make_dist(
                directory,
                self.root,
                exe=f"MZ-{order}".encode(),
                run_id=self.run_ids[order],
            )
            files, dirs = sup.walk_tree(directory)
            trees[order] = (directory, files, dirs)
        input_manifest = {"pagefolio.py": "abc"}
        runs = []
        for order in ("initial", "rebuild"):
            directory, files, dirs = trees[order]
            run_id = self.run_ids[order]
            report = json.loads((directory / "release-report.json").read_text("utf-8"))
            report.update(
                argv=[sys.executable, "-m", "PyInstaller", "--clean", "--onedir"],
                builder={"exit": 0},
                input_manifest=input_manifest,
                embedded_report_sha256=files["release-report.json"],
            )
            report_path = self.out / ".release-work" / run_id / "report.json"
            report_path.parent.mkdir(parents=True)
            report_path.write_text(json.dumps(report), encoding="utf-8")
            runs.append(
                {
                    "role": "final-release",
                    "order": order,
                    "run_id": run_id,
                    "cli_argv": [
                        "tools/build_release.py",
                        "--output-root",
                        str(self.out),
                    ],
                    "pyinstaller_exit": 0,
                    "pyinstaller_executed": True,
                    "report_path": str(report_path),
                    "report_sha256": sup.sha_file(report_path),
                    "input_manifest_sha256": sup.canonical_sha(input_manifest),
                    "tree_sha256": sup.tree_sha(files, dirs),
                }
            )
        directory, files, dirs = trees["rebuild"]
        self.target = {
            "exe_sha256": files["PageFolio.exe"],
            "tree_sha256": sup.tree_sha(files, dirs),
            "version": VERSION,
            "input_manifest_sha256": sup.canonical_sha(input_manifest),
        }
        self.build = {
            "schema_version": 1,
            "version": VERSION,
            "release_allowed": False,
            "uat_status": "not-run",
            "final_release": {
                "output_root": str(self.out),
                "final_dir": str(final),
                "exe_sha256": self.target["exe_sha256"],
                "tree_sha256": self.target["tree_sha256"],
                "input_manifest_sha256": self.target["input_manifest_sha256"],
                "bundled_sha256": {n: files[n] for n in CANON},
                "runs": runs,
            },
        }

    # -- 人手 ------------------------------------------------------------
    def row(self, case, name, *, entry="production-exe", kind=None, **extra):
        kind = kind or (
            "production-exe" if entry == "production-exe" else "python-real"
        )
        item = {
            "subrow": name,
            "entry": entry,
            "condition": extra.pop("condition", "main"),
            "evidence_kind": kind,
            "status": "pass",
            "required_observations": ["state"],
            "observations": {"state": "観測値"},
            "answer": f"{case}：期待どおり",
            "run_id": uuid.uuid4().hex,
            "observed_at": "2026-10-25T00:00:00+00:00",
            "environment": {"os": "Windows 11", "elevated": False, "session_id": 1},
            "binary_sha256": self.target["exe_sha256"]
            if kind == "production-exe"
            else "",
            "input_manifest_sha256": self.target["input_manifest_sha256"],
        }
        item.update(extra)
        return item

    def make_manual(self):
        cases = []
        for case in sup.ALL_IDS:
            if case == "W01":
                rows = [self.row(case, c, condition=c) for c in ("normal", "zoomed")]
            elif case == "W02":
                rows = [
                    self.row(case, c, condition=c)
                    for c in ("settings", "thumb", "preview")
                ]
            elif case == "W12a":
                rows = [
                    self.row(case, f"{a}-{b}", entry="script", condition=f"{a}-{b}")
                    for a in ("script", "module", "relocated")
                    for b in ("script", "module", "relocated")
                ]
            elif case == "W12b":
                rows = [
                    self.row(
                        case,
                        "tracer",
                        subject=self.subject(),
                        peer={
                            "role": "technical-tracer-real-exe",
                            "binary_sha256": sha("tracer"),
                            "version": "v1.9.1",
                            "provenance": {
                                "run_id": uuid.uuid4().hex,
                                "source_manifest_sha256": sha("src"),
                            },
                        },
                    ),
                    self.row(
                        case,
                        "copy",
                        subject=self.subject(),
                        peer={
                            "role": "same-version-copy",
                            "binary_sha256": self.target["exe_sha256"],
                            "version": VERSION,
                        },
                    ),
                ]
            else:
                rows = [self.row(case, "main")]
            cases.append({"id": case, "subrows": rows})
        return {"schema_version": 1, "cases": cases}

    def subject(self):
        return {
            "role": "final-release-candidate",
            "binary_sha256": self.target["exe_sha256"],
            "version": VERSION,
        }

    # -- 保護/接続/障害 --------------------------------------------------
    def make_protection(self):
        exe = self.target["exe_sha256"]
        rid = lambda: uuid.uuid4().hex  # noqa: E731
        same = {"exists": True, "sha256": sha("x")}
        protection = {
            "schema_version": 1,
            "build_ref": {"final_run_id": self.run_ids["rebuild"], "exe_sha256": exe},
            "protection_stop": [
                {
                    "name": name,
                    "run_id": rid(),
                    "builder_started": False,
                    "exit_code": 1,
                    "before": {name: same},
                    "after": {name: same},
                }
                for name in sup.read_constants(self.root)[1]
            ],
            "launch": {
                "cases": [
                    {
                        "name": name,
                        "run_id": rid(),
                        "binary_sha256": exe,
                        "hash_before": sha(name),
                        "hash_stable": sha(name),
                        "hash_after_exit": sha(name),
                    }
                    for name in ("normal", "corrupt", "unreadable")
                ]
            },
            "update": {
                "collision": {
                    "stopped_before_choice": True,
                    "old_before": sha("o"),
                    "old_after": sha("o"),
                    "new_before": sha("n"),
                    "new_after": sha("n"),
                },
                "no_collision": {"copied_hash_match": True, "old_preserved": True},
            },
            "connection": [
                self.connection("ocr-single"),
                self.connection("w05b-modal"),
            ],
            "faults": {
                fid: {
                    "established": True,
                    "method": "外部probe",
                    "run_id": rid(),
                    "binary_sha256": exe,
                    "observed_at": "2026-10-25T00:00:00+00:00",
                    "observation": {
                        "settings_absent_until_stable": True,
                        "original_before": sha("a"),
                        "original_after": sha("a"),
                        "holder": {"pid": 10, "created": 20},
                        "probe_denied": True,
                    },
                }
                for fid in sup.FAULT_IDS
            },
        }
        runs = set(sup._walk_values(protection, "run_id"))
        text = "# 準備\n" + "".join(f"run-ref: {r}\n" for r in sorted(runs))
        return protection, text

    def connection(self, kind):
        item = {
            "purpose": "connection-preparation",
            "kind": kind,
            "run_id": uuid.uuid4().hex,
            "binary_sha256": self.target["exe_sha256"],
            "observed_at": "2026-10-25T00:00:00+00:00",
            "user_answer": "接続を確認",
            "server": {
                "posts": 1,
                "attempts": [
                    {"attempt_id": "a-1", "image_sha256": sha("i"), "page_id": "p1"}
                ],
                "retransmissions": [],
                "expired": [],
                "rejected": 0,
                "events": [{"event": "received"}, {"event": "completed"}],
            },
        }
        if kind == "w05b-modal":
            item["server"]["events"] = [
                {"event": "received"},
                {"event": "released"},
                {"event": "completed"},
            ]
            item.update(
                modal_shown=True,
                peer_returned_to_modal=True,
                answered_no=True,
                same_request_completed=True,
            )
        return item

    # -- 品質/ゲート -----------------------------------------------------
    def make_quality(self):
        return {
            "schema_version": 1,
            "inputs": dict(self.target),
            "quality": {
                "ruff_check": {"exit": 0},
                "ruff_format": {"exit": 0},
                "ast": {"exit": 0},
                "pytest": {
                    "exit": 0,
                    "passed": 1900,
                    "failed": 0,
                    "errors": 0,
                    "crashed": False,
                    "excluded": False,
                    "single_process": True,
                    "log_sha256": sha("log"),
                },
            },
            "phase4": {"fresh": True, "covered_digest": "d1", "current_digest": "d1"},
            "unresolved": [
                {
                    "id": uid,
                    "status": "open",
                    "evaluation": "実測で再発なし(原因は未確定)",
                }
                for uid in sup.REQUIRED_UNRESOLVED
            ],
        }

    def make_gate(self):
        return {
            "schema_version": 1,
            "parent_gates": [
                {
                    "id": gid,
                    "owner": "親orchestrator",
                    "command": f"${gid}",
                    "expected_report": "判定とpath/hash",
                    "status": "pending",
                }
                for gid in sup.PARENT_GATES
            ],
            "release_conditions": [
                {"id": "RC-1", "status": "pass", "evidence": "06-EVIDENCE.json"}
            ],
            "threats": [
                {
                    "id": tid,
                    "severity": "high" if i < 8 else "medium",
                    "status": "unevaluated" if i in (5, 6) else "mitigated",
                }
                for i, tid in enumerate(sup.REQUIRED_THREATS)
            ],
            "nyquist": {"ran": False, "passed": False},
        }

    def finalize(self):
        digest = sup.canonical_sha(self.quality["inputs"])
        for gate in self.gate["parent_gates"]:
            gate["status"] = "pass"
            gate["report"] = {
                "path": f"reports/{gate['id']}.md",
                "sha256": sha(gate["id"]),
                "exit": 0,
                "at": "2026-10-26T00:00:00+00:00",
                "verdict": "pass",
                "target_inputs_sha256": digest,
            }
        for threat in self.gate["threats"]:
            threat["status"] = "mitigated"
        self.gate["nyquist"] = {"ran": True, "passed": True}
        for item in self.quality["unresolved"]:
            item["status"] = "resolved"
            item["evidence"] = {"path": "debug/x.md", "sha256": sha("x")}
        self.write_all()

    # -- 書込 ------------------------------------------------------------
    def write_all(self):
        def dump(name, value):
            sup.write_json(self.phase / name, value)

        dump(sup.BUILD, self.build)
        dump(sup.MANUAL, self.manual)
        dump(sup.PROTECTION, self.protection)
        (self.phase / sup.PREPARATION).write_text(self.prep_text, encoding="utf-8")
        dump(sup.QUALITY, self.quality)
        (self.phase / sup.GATE).write_text(
            "# gate\n\n```json release-gate\n"
            + json.dumps(self.gate, ensure_ascii=False, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )

    def case(self, case_id):
        return next(c for c in self.manual["cases"] if c["id"] == case_id)

    def audit(self, mode, **kw):
        return sup.run_audit(self.phase, mode=mode, repo=self.root, **kw)


@pytest.fixture
def phase(tmp_path):
    return Phase(tmp_path)


def assert_fails(audit, needle):
    assert not audit.ok, "不合格のはずが合格した"
    assert any(needle in reason for reason in audit.reasons), audit.reasons


class TestEvidenceAudit:
    # -- モードと出力 ----------------------------------------------------
    def test_modes_are_mutually_exclusive(self, phase, capsys):
        for pair in (
            ["--allow-pending", "--build-only"],
            ["--require-pass", "W01", "--allow-pending"],
            ["--for-handoff", "--preparation-only"],
            ["--build-only", "--for-handoff"],
        ):
            with pytest.raises(SystemExit) as caught:
                sup.main(["audit", "--phase-dir", str(phase.phase), *pair])
            assert caught.value.code == 2

    def test_cli_prints_mode_exit_and_reasons_and_never_completes(self, phase, capsys):
        code = sup.main(
            [
                "audit",
                "--phase-dir",
                str(phase.phase),
                "--repo",
                str(phase.root),
                "--require-pass",
                "W01",
            ]
        )
        out = json.loads(capsys.readouterr().out)
        assert code == 0 and out["mode"] == "require-pass" and out["exit_code"] == 0
        assert out["phase_complete"] is False and out["release_allowed"] is False
        assert out["task_ready"] is True
        phase.case("W01")["subrows"][0]["status"] = "not-run"
        phase.write_all()
        code = sup.main(
            [
                "audit",
                "--phase-dir",
                str(phase.phase),
                "--repo",
                str(phase.root),
                "--require-pass",
                "W01",
            ]
        )
        out = json.loads(capsys.readouterr().out)
        assert code == 1 and out["reasons"]

    def test_audit_is_read_only_for_every_evidence_file(self, phase):
        before = {p.name: p.read_bytes() for p in phase.phase.iterdir()}
        for mode, kw in (
            ("allow-pending", {}),
            ("require-pass", {"require": "W01,W06"}),
            ("build-only", {}),
            ("preparation-only", {}),
            ("for-handoff", {}),
            ("final", {}),
        ):
            phase.audit(mode, **kw)
        assert {p.name: p.read_bytes() for p in phase.phase.iterdir()} == before

    # -- allow-pending -----------------------------------------------------
    def test_allow_pending_is_structural_only_and_tolerates_not_run(self, phase):
        for case in phase.manual["cases"]:
            for sub in case["subrows"]:
                sub.update(status="not-run", answer="", observations={})
        phase.write_all()
        audit = phase.audit("allow-pending")
        assert audit.ok and audit.extra["structural_only"] is True
        assert audit.extra["task_ready"] is False
        assert phase.audit("require-pass", require="W01").ok is False

    def test_allow_pending_still_rejects_filled_in_false_pass(self, phase):
        sub = phase.case("W03")["subrows"][0]
        sub["answer"] = ""
        phase.write_all()
        assert_fails(phase.audit("allow-pending"), "回答")
        sub["answer"] = "W03：ok"
        sub["binary_sha256"] = sha("other")
        phase.write_all()
        assert_fails(phase.audit("allow-pending"), "binary hash")

    # -- require-pass ------------------------------------------------------
    def test_require_pass_expands_every_subrow_of_the_ids(self, phase):
        assert phase.audit("require-pass", require="W01,W02,W12a,W12b").ok
        phase.case("W01")["subrows"][1]["status"] = "not-run"  # 1行だけnot-run
        phase.write_all()
        audit = phase.audit("require-pass", require="W01")
        assert_fails(audit, "W01/zoomed")

    def test_require_pass_rejects_empty_unknown_and_missing(self, phase):
        for spec in ("", "  ", ",", "W01,,W02", "W99"):
            assert not phase.audit("require-pass", require=spec).ok, spec
        assert_fails(phase.audit("require-pass", require="W01,NOPE"), "未知")
        phase.manual["cases"] = [c for c in phase.manual["cases"] if c["id"] != "W04"]
        phase.write_all()
        assert_fails(phase.audit("require-pass", require="W04"), "宣言されていません")

    def test_require_pass_rejects_short_declarations(self, phase):
        phase.case("W12a")["subrows"].pop()  # 3x3のうち1つ欠落
        phase.case("W02")["subrows"].pop()
        phase.write_all()
        audit = phase.audit("require-pass", require="W12a,W02")
        assert_fails(audit, "宣言が不足")

    def test_other_tasks_not_run_is_tolerated_but_mixed_flag_is_not(self, phase):
        phase.case("W06")["subrows"][0]["status"] = "not-run"
        phase.write_all()
        assert phase.audit("require-pass", require="W01").ok  # 他task分は許容
        assert not phase.audit("require-pass", require="W01,W06").ok  # 混在は不可

    def test_false_pass_variants_are_rejected(self, phase):
        row = phase.case("W03")["subrows"][0]
        for change, needle in (
            ({"evidence_kind": "fault-injection"}, "昇格"),
            ({"evidence_kind": "unit"}, "単体試験"),
            ({"answer": "観察しました"}, "ケースID付き"),
            ({"observations": {"state": ""}}, "必須観測"),
            ({"binary_sha256": sha("tracer")}, "binary hash"),
            ({"run_id": ""}, "run_id"),
            ({"environment": {"os": "x"}}, "環境"),
            ({"status": "fail"}, "failでありpassではありません"),
        ):
            original = copy.deepcopy(row)
            row.update(change)
            phase.write_all()
            assert_fails(phase.audit("require-pass", require="W03"), needle)
            row.clear()
            row.update(original)

    def test_python_rows_must_match_the_current_input_manifest(self, phase):
        phase.case("W12a")["subrows"][0]["input_manifest_sha256"] = sha("old")
        phase.write_all()
        assert_fails(phase.audit("require-pass", require="W12a"), "入力manifest")

    def test_superseded_rows_are_kept_but_need_reason_and_replacement(self, phase):
        manual = sup.supersede_rows(
            phase.manual, generation=2, reason="製品コード変更", ids={"W03"}
        )
        case = next(c for c in manual["cases"] if c["id"] == "W03")
        assert [s["status"] for s in case["subrows"]] == ["pass", "not-run"]
        assert case["subrows"][0]["superseded_by"] == 2  # 元passは消えない
        phase.manual = manual
        phase.write_all()
        assert_fails(phase.audit("require-pass", require="W03"), "not-run")
        case["subrows"][1].update(
            status="pass",
            answer="W03：再実施",
            observations={"state": "ok"},
            binary_sha256=phase.target["exe_sha256"],
            run_id=uuid.uuid4().hex,
            observed_at="2026-10-26",
        )
        phase.write_all()
        assert phase.audit("require-pass", require="W03").ok
        del case["subrows"][0]["supersede_reason"]
        phase.write_all()
        assert_fails(phase.audit("require-pass", require="W03"), "理由")

    # -- W12b --------------------------------------------------------------
    def test_w12b_accepts_final_subject_with_provenanced_peer(self, phase):
        assert phase.audit("require-pass", require="W12b").ok

    def test_w12b_rejects_missing_tracer_or_disguised_subjects_and_peers(self, phase):
        rows = phase.case("W12b")["subrows"]
        cases = (
            (lambda r: r.pop("subject"), "主対象"),
            (
                lambda r: r["subject"].update(role="technical-tracer-real-exe"),
                "final-release",
            ),
            (lambda r: r["subject"].update(binary_sha256=sha("tracer")), "最終hash"),
            (lambda r: r["peer"]["provenance"].clear(), "来歴"),
            (lambda r: r["peer"].update(version=VERSION), "来歴"),
            (
                lambda r: r["peer"].update(binary_sha256=phase.target["exe_sha256"]),
                "来歴",
            ),
        )
        for mutate, needle in cases:
            saved = copy.deepcopy(rows[0])
            mutate(rows[0])
            phase.write_all()
            assert_fails(phase.audit("require-pass", require="W12b"), needle)
            rows[0].clear()
            rows[0].update(saved)
        rows[1]["peer"]["claims_other_version"] = True  # 同版copyを別版と主張
        phase.write_all()
        assert_fails(phase.audit("require-pass", require="W12b"), "同版copy")

    # -- build-only --------------------------------------------------------
    def test_build_only_accepts_two_real_runs_and_reads_only(self, phase, monkeypatch):
        final = Path(phase.build["final_release"]["final_dir"])
        before = sup.stat_tree(phase.out)

        def forbidden(*args, **kwargs):
            raise AssertionError("auditがbuild/processを起動した")

        monkeypatch.setattr(subprocess, "Popen", forbidden)
        monkeypatch.setattr(subprocess, "run", forbidden)
        audit = phase.audit("build-only")
        assert audit.ok, audit.reasons
        assert sup.stat_tree(phase.out) == before  # tree/hash/mtime不変
        assert final.is_dir()

    def test_build_only_uses_the_recorded_output_root_not_dist(self, phase):
        assert not (phase.root / "dist").exists()
        assert phase.audit("build-only").ok

    def test_build_only_rejects_missing_second_third_or_tracer_runs(self, phase):
        runs = phase.build["final_release"]["runs"]
        phase.build["final_release"]["runs"] = runs[:1]
        phase.write_all()
        assert_fails(phase.audit("build-only"), "2run")
        extra = copy.deepcopy(runs[0])
        extra.update(run_id=uuid.uuid4().hex, order="third")
        phase.build["final_release"]["runs"] = [*runs, extra]
        phase.write_all()
        assert_fails(phase.audit("build-only"), "3つ以上")
        tracer = copy.deepcopy(runs[1])
        tracer.update(tracer=True)  # tracerは2回に数えない
        phase.build["final_release"]["runs"] = [runs[0], tracer]
        phase.write_all()
        assert_fails(phase.audit("build-only"), "2run")
        runs[1]["run_id"] = runs[0]["run_id"]  # 同一run IDは異なる2runではない
        phase.build["final_release"]["runs"] = runs
        phase.write_all()
        assert_fails(phase.audit("build-only"), "2run")

    def test_build_only_rejects_inconsistent_runs_and_trees(self, phase):
        final = Path(phase.build["final_release"]["final_dir"])
        runs = phase.build["final_release"]["runs"]
        runs[0]["pyinstaller_exit"] = 1
        phase.write_all()
        assert_fails(phase.audit("build-only"), "PyInstaller")
        runs[0]["pyinstaller_exit"] = 0
        runs[1]["cli_argv"] = ["different"]
        phase.write_all()
        assert_fails(phase.audit("build-only"), "CLI引数")
        runs[1]["cli_argv"] = runs[0]["cli_argv"]
        runs[1]["report_sha256"] = sha("wrong")
        phase.write_all()
        assert_fails(phase.audit("build-only"), "hash不一致")
        runs[1]["report_sha256"] = sup.sha_file(runs[1]["report_path"])
        phase.write_all()
        assert phase.audit("build-only").ok
        (final / "PageFolio.exe").write_bytes(b"tampered")
        assert_fails(phase.audit("build-only"), "tree/EXE hash")

    def test_build_only_rejects_protected_names_samples_and_history(self, phase):
        final = Path(phase.build["final_release"]["final_dir"])
        history = phase.out / ".release-history" / phase.run_ids["rebuild"]
        (final / "ocr_custom_prompt.md").write_text("user")
        assert_fails(phase.audit("build-only"), "保護名")
        (final / "ocr_custom_prompt.md").unlink()
        (final / "ocr_custom_prompt_sample.md").write_text("changed")
        assert_fails(phase.audit("build-only"), "SHA-256")
        shutil.copyfile(
            phase.root / CANON["ocr_custom_prompt_sample.md"],
            final / "ocr_custom_prompt_sample.md",
        )
        assert phase.audit("build-only").ok
        shutil.move(history, phase.tmp / "moved")
        assert_fails(phase.audit("build-only"), "history")

    def test_build_only_requires_not_run_uat_and_release_blocked(self, phase):
        phase.build["release_allowed"] = True
        phase.write_all()
        assert_fails(phase.audit("build-only"), "release_allowed")

    # -- preparation-only --------------------------------------------------
    def test_preparation_only_accepts_complete_evidence(self, phase):
        audit = phase.audit("preparation-only")
        assert audit.ok, audit.reasons

    def test_preparation_only_rejects_missing_or_wrong_evidence(self, phase):
        prot = phase.protection
        cases = (
            (lambda: prot["protection_stop"][0].update(builder_started=True), "停止"),
            (lambda: prot["protection_stop"].pop(), "停止"),
            (lambda: prot["launch"]["cases"][0].update(hash_stable=sha("z")), "変化"),
            (
                lambda: prot["launch"]["cases"][1].update(hash_after_exit=sha("z")),
                "終了後",
            ),
            (
                lambda: prot["update"]["collision"].update(new_after=sha("z")),
                "同名衝突",
            ),
            (lambda: prot["connection"].pop(), "native modal"),
            (lambda: prot["connection"][0]["server"].update(posts=2), "接続"),
            (lambda: prot["connection"][0].update(user_answer=""), "接続"),
            (
                lambda: prot["connection"][0]["server"].update(
                    retransmissions=[{"x": 1}]
                ),
                "接続",
            ),
            (lambda: prot["connection"][1].update(answered_no=False), "modal"),
            (lambda: prot["connection"][0].update(purpose="acceptance"), "接続"),
            (lambda: prot["faults"].pop("X03"), "X03"),
            (
                lambda: prot["faults"]["X02"]["observation"].update(
                    original_after=sha("z")
                ),
                "原本",
            ),
            (lambda: prot["faults"]["X04"].update(established=False), "X04"),
            (lambda: prot["faults"]["X01"].update(binary_sha256=sha("z")), "X01"),
            (lambda: prot["build_ref"].update(exe_sha256=sha("z")), "最終build"),
        )
        for mutate, needle in cases:
            saved = copy.deepcopy(phase.protection)
            mutate()
            phase.write_all()
            assert_fails(phase.audit("preparation-only"), needle)
            phase.protection.clear()
            phase.protection.update(saved)
        phase.write_all()
        assert phase.audit("preparation-only").ok

    def test_preparation_only_checks_run_references_both_ways(self, phase):
        runs = sorted(sup._walk_values(phase.protection, "run_id"))
        phase.prep_text = phase.prep_text.replace(f"run-ref: {runs[0]}\n", "")
        phase.write_all()
        assert_fails(phase.audit("preparation-only"), "run参照")
        phase.prep_text += f"run-ref: {uuid.uuid4().hex}\n"
        phase.write_all()
        assert_fails(phase.audit("preparation-only"), "run参照")

    def test_connection_run_cannot_be_copied_into_w04_acceptance(self, phase):
        connection_run = phase.protection["connection"][0]["run_id"]
        phase.case("W04")["subrows"][0]["run_id"] = connection_run
        phase.write_all()
        assert_fails(phase.audit("preparation-only"), "転記")

    # -- for-handoff と最終監査 -------------------------------------------
    def test_handoff_succeeds_with_only_parent_gates_pending_but_final_fails(
        self, phase
    ):
        handoff = phase.audit("for-handoff")
        assert handoff.ok, handoff.reasons
        report = handoff.report()
        assert report["handoff_ready"] is True
        assert report["phase_complete"] is False and report["release_allowed"] is False
        final = phase.audit("final")
        assert_fails(final, "pending")
        assert final.report()["final_audit_passed"] is False

    def test_final_succeeds_only_after_parent_results_are_recorded(self, phase):
        phase.finalize()
        final = phase.audit("final")
        assert final.ok, final.reasons
        report = final.report()
        assert report["final_audit_passed"] is True
        assert report["phase_complete"] is False and report["release_allowed"] is False
        assert phase.audit("for-handoff").ok  # 実走済みでも引渡し監査は通る

    def test_handoff_rejects_manual_not_run_and_stale_phase4_and_quality_failure(
        self, phase
    ):
        phase.case("W11")["subrows"][0].update(status="not-run")
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "W11")
        phase.case("W11")["subrows"][0].update(status="pass")
        phase.quality["phase4"]["current_digest"] = "changed"
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "Phase4")
        phase.quality["phase4"]["current_digest"] = "d1"
        phase.quality["quality"]["pytest"]["failed"] = 1
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "pytest")
        phase.quality["quality"]["pytest"]["failed"] = 0
        phase.quality["quality"]["pytest"]["excluded"] = True
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "pytest")

    def test_handoff_rejects_unknown_failed_and_incomplete_parent_gates(self, phase):
        gates = phase.gate["parent_gates"]
        gates.append(
            {
                "id": "extra",
                "status": "pending",
                "owner": "x",
                "command": "x",
                "expected_report": "x",
            }
        )
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "4件")
        gates.pop()
        gates[0]["status"] = "needs-fix"
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "needs-fix")
        gates[0]["status"] = "pending"
        del gates[1]["command"]
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "実行手段")

    def test_handoff_rejects_known_high_threat_and_other_unmet_conditions(self, phase):
        phase.gate["threats"][0]["status"] = "open"
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "T-06-01")
        phase.gate["threats"][0]["status"] = "mitigated"
        phase.gate["release_conditions"][0]["status"] = "open"
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "RC-1")
        phase.gate["release_conditions"][0]["status"] = "pass"
        phase.quality["unresolved"].pop()
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "欠落")

    def test_fake_gate_pass_and_target_mismatch_are_rejected(self, phase):
        phase.finalize()
        gate = phase.gate["parent_gates"][0]
        gate["report"]["sha256"] = ""
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "偽pass")
        gate["report"]["sha256"] = sha("ok")
        gate["report"]["target_inputs_sha256"] = sha("old target")
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "対象入力")
        assert_fails(phase.audit("final"), "対象入力")
        phase.quality["inputs"]["exe_sha256"] = sha("other exe")
        phase.write_all()
        assert_fails(phase.audit("for-handoff"), "現行build")

    def test_final_requires_evaluated_threats_nyquist_and_unresolved_grounds(
        self, phase
    ):
        phase.finalize()
        phase.gate["threats"][5]["status"] = "unevaluated"
        phase.write_all()
        assert_fails(phase.audit("final"), "ASVS1")
        assert phase.audit("for-handoff").ok  # 引渡しでは未評価を許容
        phase.gate["threats"][5]["status"] = "mitigated"
        phase.gate["nyquist"]["ran"] = False
        phase.write_all()
        assert_fails(phase.audit("final"), "Nyquist")
        phase.gate["nyquist"]["ran"] = True
        phase.quality["unresolved"][0] = {
            "id": "DEP-05-REGRESSION",
            "status": "open",
            "evaluation": "未解除",
        }
        phase.write_all()
        assert_fails(phase.audit("final"), "DEP-05-REGRESSION")
        phase.quality["unresolved"][0].update(
            status="accepted-by-user", approval={"quote": "承認します"}
        )
        phase.write_all()
        assert phase.audit("final").ok
        phase.quality["unresolved"][0]["status"] = "resolved"
        phase.write_all()
        assert_fails(phase.audit("final"), "根拠")

    def test_missing_evidence_files_fail_closed_in_every_mode(self, phase):
        for name in (sup.GATE, sup.QUALITY, sup.PROTECTION, sup.MANUAL, sup.BUILD):
            (phase.phase / name).unlink()
        for mode, kw in (
            ("allow-pending", {}),
            ("require-pass", {"require": "W01"}),
            ("build-only", {}),
            ("preparation-only", {}),
            ("for-handoff", {}),
            ("final", {}),
        ):
            assert not phase.audit(mode, **kw).ok, mode

    def test_unparsable_evidence_fails_instead_of_crashing(self, phase):
        (phase.phase / sup.MANUAL).write_text("{not json", encoding="utf-8")
        (phase.phase / sup.BUILD).write_text("[]", encoding="utf-8")
        for mode in ("allow-pending", "build-only", "for-handoff", "final"):
            assert not phase.audit(mode).ok

    # -- 中断・再開 --------------------------------------------------------
    def test_resume_state_requires_identical_inputs_before_continuing(
        self, tmp_path, repo
    ):
        manifest = prep(tmp_path, repo)
        phase_dir = tmp_path / "phase"
        phase_dir.mkdir()
        state = sup.save_resume_state(
            phase_dir,
            run=manifest["run"],
            completed=["W01"],
            pending=["W02", "W03"],
            last_answer="W01：最大化に戻った",
        )
        assert state["pending"] == ["W02", "W03"] and state["exe_sha256"]
        current = {
            "run_id": manifest["run_id"],
            "exe_sha256": manifest["source"]["exe_sha256"],
            "tree_sha256": manifest["source"]["tree_sha256"],
            "environment": manifest["environment"],
        }
        same = sup.check_resume(phase_dir, current)
        assert same["same"] and same["action"] == "continue-pending"
        assert same["pending"] == ["W02", "W03"]
        changed = sup.check_resume(phase_dir, {**current, "exe_sha256": sha("new")})
        assert not changed["same"] and changed["action"] == "new-generation"
        assert sup.check_resume(tmp_path / "none", current)["action"] == "no-state"


class TestCatalog:
    def test_task_assignment_covers_all_cases_without_overlap(self):
        ids = sup.ALL_IDS
        assert len(ids) == len(set(ids)) == 31
        assert (
            len(sup.TASK_IDS["06-05-02"]) == 16 and len(sup.TASK_IDS["06-06-01"]) == 15
        )
        expected = {
            "W01", "W02", "W03", "W04", "W05a", "W05b", "W05c", "W06", "W07a", "W07b",
            "W08a", "W08b", "W08c", "W08d", "W09a", "W09b", "W09c", "W09d", "W10a",
            "W10b", "W11", "W12a", "W12b", "W12c", "WR-01",
            "X01", "X02", "X03", "X04", "X05", "X06",
        }  # fmt: skip
        assert set(ids) == expected
