# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""LLM 設定ダイアログ（OCR と設定で共有）— Mixin パッケージ統合。

pagefolio/app.py の PDFEditorApp（8 Mixin 構成）と同じパターンで、
責務別3層の Mixin（DialogMixin/SectionsMixin/ModelFetchMixin）を
tk.Toplevel と多重継承して LLMConfigDialog を再構成する。
"""

import tkinter as tk

from pagefolio.dialogs.llm_config.dialog import DialogMixin  # noqa: F401
from pagefolio.dialogs.llm_config.model_fetch import ModelFetchMixin  # noqa: F401
from pagefolio.dialogs.llm_config.sections import SectionsMixin  # noqa: F401
from pagefolio.settings import prompt_file_exists, save_prompt_file  # noqa: F401


# ══════════════════════════════════════════
#  LLM 設定ダイアログ（OCR と設定で共有）
# ══════════════════════════════════════════
class LLMConfigDialog(DialogMixin, SectionsMixin, ModelFetchMixin, tk.Toplevel):
    """プロバイダ選択・欄切替・モデル更新・effort 切替を行う共通ダイアログ。

    対応プロバイダ（off/lmstudio/claude/gemini）:
    プロバイダ選択:
      - off: OCR を無効化（OCR ボタンは disabled になる）
      - lmstudio: LM Studio URL・モデル欄を表示
      - claude: claude モデル欄・effort/temperature 欄を表示
      - gemini: gemini モデル欄・temperature 欄を表示（D-09・effort 非対応）

    # Phase 7: tesseract を追加予定

    Mixin 構成（D-04/D-05・機械的分割）:
      - DialogMixin: __init__/_apply/_on_provider_change/_on_model_change/
        _model_supports_effort/_resize_to_fit/_add_prompt_file_notice/
        _set_lm_status とスクロール域構築の共通部
      - SectionsMixin: _build の UI セクション構築
      - ModelFetchMixin: _fetch_models_async + プロバイダ別 probe/refresh 群

    tk.Toplevel は継承リスト末尾（Pitfall 3・MRO 破壊防止）。__init__ は
    DialogMixin に集約し、他の Mixin は __init__ を持たない。
    """
