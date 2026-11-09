# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
# https://github.com/mistyura/PageFolio
"""カラーテーマ定義 — THEMES 辞書と実行時可変 C dict"""

# ===================== カラーテーマ =====================
THEMES = {
    "dark": {
        "BG_DARK": "#1a1a2e",
        "BG_PANEL": "#16213e",
        "BG_CARD": "#0f3460",
        "ACCENT": "#e94560",
        "ACCENT2": "#533483",
        "TEXT_MAIN": "#eaeaea",
        "TEXT_SUB": "#a0a0b0",
        "BTN_HOVER": "#ff6b6b",
        "SUCCESS": "#4ecca3",
        "WARNING": "#ffd460",
        "CROP_ON_BG": "#8b0000",
        "PREVIEW_BG": "#111122",
        "DANGER_BG": "#7c1c2e",
        "DANGER_FG": "#ffaaaa",
    },
    "light": {
        "BG_DARK": "#f0f0f5",
        "BG_PANEL": "#e0e0ea",
        "BG_CARD": "#d0d0dd",
        "ACCENT": "#d63050",
        "ACCENT2": "#7b52ab",
        "TEXT_MAIN": "#1a1a2e",
        "TEXT_SUB": "#555566",
        "BTN_HOVER": "#ff6b6b",
        "SUCCESS": "#2a9d6a",
        "WARNING": "#b8860b",
        "CROP_ON_BG": "#cc3333",
        "PREVIEW_BG": "#c8c8d0",
        "DANGER_BG": "#e8c0c0",
        "DANGER_FG": "#7c1c2e",
    },
}

# 現在テーマの色をモジュールレベルで参照するための辞書（実行時に _apply_theme() で更新）
C = dict(THEMES["dark"])
