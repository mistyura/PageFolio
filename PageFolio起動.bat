@echo off
chcp 65001 > nul
cd /d "%~dp0"
python pagefolio.py
if %errorlevel% neq 0 (
    echo.
    echo エラーが発生しました。Enterキーで閉じます。
)
pause
