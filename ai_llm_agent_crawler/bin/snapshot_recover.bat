@echo off
REM ============================================================
REM  Snapshot 恢复批处理 (Windows)
REM  用法: snapshot_recover.bat [entity] [snapshot_id] [output_path]
REM  示例: snapshot_recover.bat mydata snap_20260711_abc123 D:\restored
REM ============================================================
setlocal

set ENTITY=%1
set SNAP_ID=%2
set OUTPUT=%3

if "%ENTITY%"=="" (
    set /p ENTITY=请输入实体 ID:
)
if "%SNAP_ID%"=="" (
    set /p SNAP_ID=请输入快照 ID:
)
if "%OUTPUT%"=="" (
    set /p OUTPUT=请输入输出路径:
)

set BIN_DIR=%~dp0

where ai-crawler >nul 2>nul
if %errorlevel%==0 (
    ai-crawler snapshot restore --entity "%ENTITY%" --id "%SNAP_ID%" --out "%OUTPUT%"
) else (
    python "%BIN_DIR%snapshot_cli.py" restore --entity "%ENTITY%" --id "%SNAP_ID%" --out "%OUTPUT%"
)

endlocal
