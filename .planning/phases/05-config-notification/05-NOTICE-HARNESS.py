"""私有一時設定で実PageFolioと実Toastを目視する開発専用入口。"""

import argparse
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import fitz


def repository_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "pagefolio/app.py").is_file():
            return parent
    raise RuntimeError("pagefolio/app.pyを持つ祖先が見つかりません")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        choices=["read-corrupt", "read-unreadable", "save-write", "save-replace"],
    )
    args = parser.parse_args()
    sys.path.insert(0, str(repository_root()))
    from tests.config_notice_support import create_isolated_app

    isolated = create_isolated_app(args.scenario, visible=True)
    with isolated:
        app, root = isolated.app, isolated.root
        app.doc = fitz.open()
        page = app.doc.new_page()
        page.insert_text((72, 72), "Isolated configuration notice acceptance PDF")
        app.edit_mode = True
        app.selected_pages = {0}
        app._refresh_all()
        controls = tk.Toplevel(root)
        controls.title("PageFolio 隔離受入: " + args.scenario)
        controls.geometry("680x460")
        panel = ttk.Frame(controls, padding=12)
        panel.pack(fill="both", expand=True)
        ttk.Label(
            panel,
            text="実利用設定・PDF・プロンプト・pluginsは使用しません。",
            font=app._font(0),
        ).pack(anchor="w")
        ttk.Label(
            panel,
            text="入力中のまま通知を待ち、PDF画面で回転・Undo・Redoを確認してください。",
            wraplength=640,
            font=app._font(0),
        ).pack(anchor="w")
        entry = ttk.Entry(panel, font=app._font(0))
        entry.insert(0, "ここに入力して通知前後の入力先を確認")
        entry.pack(fill="x", pady=8)
        ttk.Label(
            panel, text=str(isolated.base), wraplength=640, font=app._font(-1)
        ).pack(anchor="w")

        def apply_same():
            app._apply_settings(dict(app.settings))

        def toggle_fault():
            isolated.fault_enabled = not isolated.fault_enabled
            fault_label.configure(
                text="I/O障害: " + ("有効" if isolated.fault_enabled else "解除")
            )

        fault_label = ttk.Label(panel, text="I/O障害: 有効", font=app._font(0))
        fault_label.pack(anchor="w", pady=4)
        for label, callback in [
            ("同値の明示Apply（1回の保存操作）", apply_same),
            ("言語切替・画面再構築", app._toggle_lang),
            ("I/O障害の解除/再注入（unreadable保護は残る）", toggle_fault),
            ("実Settingsモーダル（10秒以上開く）", app._open_settings),
            ("実Pluginモーダル（変更せず閉じる）", app._open_plugin_dialog),
            (
                "既存PDF保存Toastを割込み表示（印刷/書込はしない）",
                lambda: app._toast.show(
                    "save_file",
                    "隔離受入: PDF保存通知",
                    retry_cb=lambda: app._toast.dismiss("save_file"),
                ),
            ),
            ("既存操作Toastを成功dismiss", lambda: app._toast.dismiss("save_file")),
        ]:
            ttk.Button(panel, text=label, command=callback, style="TButton").pack(
                fill="x", pady=2
            )
        ttk.Button(
            panel,
            text="製品の終了操作（D-19確認Yes/No）",
            command=app._quit,
            style="Danger.TButton",
        ).pack(fill="x", pady=2)
        controls.protocol("WM_DELETE_WINDOW", controls.withdraw)
        root.mainloop()


if __name__ == "__main__":
    main()
