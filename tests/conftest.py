"""PageFolio テスト用フィクスチャ"""

import json
import os
import sys

import fitz
import pytest

# pagefolio.py をインポートできるようにプロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


@pytest.fixture()
def sample_pdf(tmp_path):
    """テスト用の3ページPDFをメモリ上で生成し、tmp_pathに保存して返す。
    返り値は PDF ファイルパス (str)。
    """
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)  # A4
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    pdf_path = str(tmp_path / "test_sample.pdf")
    doc.save(pdf_path)
    doc.close()
    return pdf_path


@pytest.fixture()
def sample_pdf_doc():
    """テスト用の3ページPDFをメモリ上で生成し、fitz.Document として返す。
    テスト終了後に自動でクローズされる。
    """
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    yield doc
    doc.close()


@pytest.fixture()
def multi_pdf_files(tmp_path):
    """結合・挿入テスト用に複数のPDFファイルを生成する。
    返り値は [path1, path2, path3] のリスト。
    """
    paths = []
    for idx in range(3):
        doc = fitz.open()
        n_pages = idx + 1  # 1ページ, 2ページ, 3ページ
        for p in range(n_pages):
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 72), f"File{idx + 1} Page{p + 1}", fontsize=20)
        path = str(tmp_path / f"file_{idx + 1}.pdf")
        doc.save(path)
        doc.close()
        paths.append(path)
    return paths
