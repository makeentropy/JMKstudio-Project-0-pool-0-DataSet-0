@echo off
chcp 65001 >nul
echo ==========================================
echo   超弦奇点量子系统 - Superstring Singularity
echo ==========================================
echo.

REM 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python
    pause
    exit /b 1
)

REM 创建必要的目录
if not exist "data\pool-0" mkdir "data\pool-0"
if not exist "data\certificates" mkdir "data\certificates"
if not exist "data\visualizations" mkdir "data\visualizations"
if not exist "data\gnupg" mkdir "data\gnupg"

REM 检查依赖
echo 检查依赖...
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo 安装依赖...
    pip install -r requirements.txt
)

echo.
echo 可用的启动选项:
echo   1^) 启动Web终端
echo   2^) 启动Jupyter Notebook
echo   3^) 同时启动Web终端和Jupyter
echo   4^) 仅安装依赖
echo.
set /p choice=请选择 (1-4): 

if "%choice%"=="1" goto start_web
if "%choice%"=="2" goto start_jupyter
if "%choice%"=="3" goto start_both
if "%choice%"=="4" goto install_deps
goto end

:start_web
echo 启动Web终端...
python -m src.web_terminal.app
goto end

:start_jupyter
echo 启动Jupyter Notebook...
jupyter notebook superstring_singularity_quantum.ipynb
goto end

:start_both
echo 同时启动Web终端和Jupyter...
start "Web终端" python -m src.web_terminal.app
timeout /t 2 /nobreak >nul
start "Jupyter" jupyter notebook superstring_singularity_quantum.ipynb
echo.
echo Web终端: http://localhost:5000
echo Jupyter: http://localhost:8888
echo.
goto end

:install_deps
echo 安装依赖...
pip install -r requirements.txt
echo 依赖安装完成
goto end

:end
pause
