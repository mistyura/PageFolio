# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""Tesseract OCR プロバイダ（subprocess 直呼び・ネットワーク不要）"""

import base64
import subprocess

from pagefolio.ocr_providers.base import OCRProvider


def _detect_tesseract():
    """Tesseract の存在・インストール済み言語を検出する関数。

    D-05: import 時に一度だけ固定するのではなく、TesseractProvider の生成時
    （build_provider 呼び出しの都度・llm_config.py の UI 構築時）に**都度呼び出し
    可能**な関数として設計する。呼び出しコストは subprocess 起動2回（数十ms）で
    頻度的に無視できる。呼び出しの都度 subprocess を起動しないこと（並列 OCR の
    ocr_image からは呼ばない — Anti-Pattern）。

    戻り値: (available: bool, langs: frozenset[str]) のタプル。
    Tesseract が見つかれば (True, {インストール済み言語...}) を、
    見つからなければ (False, frozenset()) を返す。
    """
    try:
        r = subprocess.run(
            ["tesseract", "--version"],  # noqa: S603 S607
            capture_output=True,
            timeout=5,
        )
        if r.returncode != 0:
            return False, frozenset()
        # --list-langs でインストール済み言語を取得
        # Windows は stdout、Linux 系は stderr に出力する場合があるため両方を確認
        r2 = subprocess.run(
            ["tesseract", "--list-langs"],  # noqa: S603 S607
            capture_output=True,
            timeout=5,
        )
        raw = (r2.stdout or r2.stderr).decode(errors="replace")
        langs = frozenset(
            line.strip()
            for line in raw.splitlines()
            if line.strip() and not line.lower().startswith("list of")
        )
        return True, langs
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False, frozenset()


class TesseractProvider(OCRProvider):
    """Tesseract OCR プロバイダ（subprocess 直呼び・ネットワーク不要）。

    tesseract コマンドを stdin パイプ方式で呼び出して OCR を実行する。
    API キー・ネットワーク接続は不要でオフライン環境でも動作する。

    注意: LLM ベースのプロバイダより精度が劣る場合があります。
    """

    default_concurrency = 1  # CPU バウンド・シングルスレッド前提
    max_concurrency = 2

    RECOMMENDED_LANGS: list = ["jpn+eng", "eng", "jpn"]

    def __init__(self, lang="jpn+eng", psm=3, timeout=60, available_langs=None):
        """初期化。

        引数:
          lang:    Tesseract に渡す要求言語コード（例: "jpn+eng"）。"+" 区切りで
                   複数指定可能。段階的縮退（D-06）により実際に使われる言語は
                   self.effective_lang に確定される。
          psm:     ページセグメンテーションモード（3=全自動、6=単一ブロック）
          timeout: subprocess タイムアウト秒数（既定: 60）
          available_langs: 検出済みの利用可能言語集合（frozenset[str] 等）。
                   None（既定）のときはこの場で _detect_tesseract() を呼び直し
                   再検出する（D-05: プロバイダ生成時に都度再評価・再起動不要で
                   言語パック追加を反映）。呼び出し元（build_provider 等）が
                   再検出済みの結果を明示的に渡すことも可能。
        """
        self.lang = lang
        self.psm = psm
        self.timeout = timeout
        if available_langs is None:
            # D-03 互換: パッケージ再エクスポート面（pagefolio.ocr_providers.
            # _detect_tesseract）経由で呼ぶ。既存テストが同属性を monkeypatch
            # して再検出結果を差し替えるため、tesseract.py 内のモジュール
            # ローカル名を直接呼ぶとその差し替えを拾えない（分割前は同一
            # モジュール内の名前だったため単一の名前空間で解決できていた）。
            from pagefolio.ocr_providers import _detect_tesseract as _redetect

            _, available_langs = _redetect()
        self.available_langs = available_langs or frozenset()
        # D-06: __init__ 時点で段階的縮退を確定し、ocr_image は都度計算しない
        self.effective_lang, self.lang_fallback = self._resolve_lang(
            self.lang, self.available_langs
        )
        # フォールバック発生時の注記表示（D-07・Task 2）が読む要求/実効ペア
        self.requested_lang = self.lang

    @staticmethod
    def _resolve_lang(requested_raw, available_langs):
        """段階的縮退で実効言語を確定する（D-06）。

        まず要求言語（"+" 区切り）のうち利用可能な部分集合を、要求の指定順を
        保ったまま残す。部分集合が非空ならそれを実効言語とする。空（＝全滅、
        または要求自体が空）なら現行の自動決定（jpn 利用可→"jpn+eng" /
        なし→"eng"）へ落とす。常にどちらかの分岐で値を返し、例外は送出しない
        （必ず何かしらの言語で実行できることを保証する）。

        戻り値: (effective_lang: str, fallback_occurred: bool) のタプル。
        fallback_occurred は「要求言語が非空で、かつ実効言語が要求と完全一致
        しない」場合に True になる。
        """
        requested = [t for t in (requested_raw or "").split("+") if t]
        subset = [t for t in requested if t in available_langs]
        if subset:
            return "+".join(subset), subset != requested
        auto = "jpn+eng" if "jpn" in available_langs else "eng"
        return auto, bool(requested)

    def ocr_image(self, b64_png, prompt, **kwargs):
        """Tesseract を stdin パイプ方式で呼び出して OCR テキストを返す。

        引数:
          b64_png: PNG 画像の base64 文字列
          prompt:  OCR 指示テキスト（Tesseract では無視される。インターフェース互換用）
          **kwargs: 未使用（インターフェース互換のため受け取る）

        戻り値: OCR 結果テキスト（str）

        例外:
          RuntimeError:  tesseract コマンドが見つからない、または終了コード != 0
          TimeoutError:  tesseract がタイムアウト（D-T2）
        """
        # -l へ渡すのは __init__ で段階的縮退済みの実効言語のみ（検出済み集合
        # との積を取った結果）。生の self.lang を直接渡さない（T-2-T01 mitigate）。
        lang = self.effective_lang
        png_bytes = base64.b64decode(b64_png)
        try:
            result = subprocess.run(  # noqa: S603
                ["tesseract", "stdin", "stdout", "-l", lang, "--psm", str(self.psm)],  # noqa: S607
                input=png_bytes,
                capture_output=True,
                timeout=self.timeout,
            )
        except FileNotFoundError as e:
            raise RuntimeError("tesseract コマンドが見つかりません") from e
        except subprocess.TimeoutExpired as e:
            raise TimeoutError(
                f"Tesseract がタイムアウトしました ({self.timeout}s)"
            ) from e
        if result.returncode != 0:
            err = result.stderr.decode(errors="replace")
            raise RuntimeError(f"Tesseract エラー (rc={result.returncode}): {err}")
        return result.stdout.decode("utf-8", errors="replace").strip()

    def list_models(self):
        """利用可能な Tesseract 言語コードのリストを返す。

        戻り値: ["tesseract"]（固定の単一エントリ）
        """
        return ["tesseract"]
