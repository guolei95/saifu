#!/usr/bin/env python3
"""竞赛选赛助手 — 技能入口脚本

由 SKILL.md 中的 /competition-match 命令调用。
自动读取用户画像模板，运行主匹配脚本。
"""

import os
import sys
import subprocess
from pathlib import Path

# 项目根目录（.claude/skills/competition-match/scripts/ → 项目根）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

MAIN_SCRIPT = PROJECT_ROOT / "02-方案" / "0503-match_competitions.py"
PROFILE_FILE = PROJECT_ROOT / "03-素材" / "用户画像模板.md"


def main():
    # 解析参数
    analyze_target = None
    args = sys.argv[1:]
    if "--analyze" in args:
        idx = args.index("--analyze")
        if idx + 1 < len(args):
            analyze_target = args[idx + 1]

    if not MAIN_SCRIPT.exists():
        print(f"❌ 找不到主脚本: {MAIN_SCRIPT}")
        sys.exit(1)

    cmd = ["python", str(MAIN_SCRIPT), "--profile", str(PROFILE_FILE)]
    if analyze_target:
        cmd.extend(["--analyze", analyze_target])

    print(f"🚀 竞赛选赛助手启动中...")
    print(f"   画像: {PROFILE_FILE}")
    if analyze_target:
        print(f"   分析: {analyze_target}")
    print()

    # 检查 API Key
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("⚠️ 未检测到 DEEPSEEK_API_KEY 环境变量")
        print("   请先设置: set DEEPSEEK_API_KEY=sk-你的密钥")
        print("   或直接双击 运行.bat（会自动提示输入）")
        sys.exit(1)

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
