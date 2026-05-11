@echo off
REM 竞赛选赛助手 V1.4 (CLI本地终端) — 一键启动
REM V1.x 均为命令行阶段，V2 起才进入网页MVP
REM 支持 --profile "用户画像模板.md" 加载详细画像
REM 依赖: pip install ddgs openai

REM === 把你的 API Key 填在这里 ===
set DEEPSEEK_API_KEY=你的DeepSeek密钥填这里
REM ===============================

if "%DEEPSEEK_API_KEY%"=="你的DeepSeek密钥填这里" (
    echo ❌ 请先编辑 run_match.bat，填入 DEEPSEEK_API_KEY！
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════╗
echo ║  竞赛选赛助手 V1.4  CLI本地终端    ║
echo ╚══════════════════════════════════════╝
echo.

set /p SCHOOL="学校全称: "
set /p MAJOR="专业名称: "
set /p GRADE="年级: "
set /p INTERESTS="兴趣技能（逗号分隔，可留空）: "
set /p REQUIREMENTS="特殊要求（可留空）: "

echo.
echo 正在运行（DuckDuckGo 搜索 + DeepSeek 匹配 + 知识库增强）...
echo.

python "D:\我的竞赛项目-AI赋能竞赛系统\02-方案\0503-match_competitions.py" --school "%SCHOOL%" --major "%MAJOR%" --grade "%GRADE%" --interests "%INTERESTS%" --requirements "%REQUIREMENTS%"

pause
