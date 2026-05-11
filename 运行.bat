@echo off
title 竞赛选赛助手 V1.6
cd /d "%~dp0"

echo.
echo ================================================
echo       竞赛选赛助手 V1.6 - 一键运行
echo ================================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未检测到 Python
    echo 正在打开 Python 下载页面...
    start https://www.python.org/downloads/
    echo.
    echo 请安装 Python 后重新运行此脚本。
    echo 安装时务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
echo [OK] Python 已就绪

:: 检查依赖
python -c "from ddgs import DDGS" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INSTALL] 正在安装搜索库 ddgs...
    pip install ddgs -q
)
python -c "from openai import OpenAI" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INSTALL] 正在安装 openai...
    pip install openai -q
)
echo [OK] 依赖库已就绪

:: 检查 API Key
python -c "import os; exit(0 if os.environ.get('DEEPSEEK_API_KEY','') else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [WARN] 未检测到 DeepSeek API Key
    echo.
    echo 获取方式：
    echo   1. 打开 https://platform.deepseek.com
    echo   2. 手机号注册/登录
    echo   3. 左侧菜单 -> API Keys -> 创建新 Key
    echo   4. 复制 sk- 开头的密钥
    echo.
    set /p APIKEY="请输入你的 API Key: "
    set DEEPSEEK_API_KEY=%APIKEY%
    echo.
    echo 提示：运行以下命令可永久保存密钥（下次不用再输）：
    echo   setx DEEPSEEK_API_KEY "%APIKEY%"
    echo.
) else (
    echo [OK] API Key 已配置
)

echo.
echo [RUN] 正在搜索竞赛信息，请稍候...
echo       全程约 30-60 秒，取决于网络速度
echo.

:: 运行主脚本
python "02-方案\0503-match_competitions.py" --profile "03-素材\用户画像模板.md"

echo.
echo ================================================
echo   运行完成！结果已显示在上方。
echo   如需重新搜索，请再次双击此文件。
echo ================================================
pause
