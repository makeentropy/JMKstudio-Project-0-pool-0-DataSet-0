@echo off
REM ============================================================
REM  Snapshot 交互式 UI (Windows)
REM  用法: snapshot_ui.bat [storage_path]
REM ============================================================
setlocal
set BIN_DIR=%~dp0
python "%BIN_DIR%snapshot_ui.py" %*
endlocal
