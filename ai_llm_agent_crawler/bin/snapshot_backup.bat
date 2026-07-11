@echo off
REM ============================================================
REM  Snapshot 备份批处理 (Windows)
REM  用法: snapshot_backup.bat [entity] [source_path] [compression]
REM  示例: snapshot_backup.bat mydata D:\data tar.gz
REM ============================================================
setlocal

set ENTITY=%1
set SOURCE=%2
set COMPRESSION=%3

if "%ENTITY%"=="" (
    set /p ENTITY=请输入实体 ID:
)
if "%SOURCE%"=="" (
    set /p SOURCE=请输入源路径:
)
if "%COMPRESSION%"=="" set COMPRESSION=none

REM 脚本所在目录
set BIN_DIR=%~dp0
set SRC_DIR=%BIN_DIR%..\src

REM 优先使用已安装的 ai-crawler 命令，回退到 python 直跑
where ai-crawler >nul 2>nul
if %errorlevel%==0 (
    ai-crawler snapshot create-full --entity "%ENTITY%" --source "%SOURCE%" --compression %COMPRESSION%
) else (
    python "%BIN_DIR%snapshot_cli.py" create-full --entity "%ENTITY%" --source "%SOURCE%" --compression %COMPRESSION%
)

endlocal
