@echo off
chcp 65001 > nul
cd /d "%~dp0"
python pdf_editor.py
if %errorlevel% neq 0 (
    echo.
    echo エラーが発生しました。Enterキーで閉じます。
)
pause
