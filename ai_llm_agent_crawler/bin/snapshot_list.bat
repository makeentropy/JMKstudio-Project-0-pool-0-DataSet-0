@echo off
REM ============================================================
REM  Snapshot 列表批处理 (Windows)
REM  用法: snapshot_list.bat [entity]
REM ============================================================
setlocal

set ENTITY=%1
if "%ENTITY%"=="" (
    set /p ENTITY=请输入实体 ID:
)

set BIN_DIR=%~dp0

where ai-crawler >nul 2>nul
if %errorlevel%==0 (
    ai-crawler snapshot list --entity "%ENTITY%"
) else (
    python "%BIN_DIR%snapshot_cli.py" list --entity "%ENTITY%"
)

endlocal
