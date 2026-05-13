"""
赛赋(SaiFu) 配置模块 — 统一管理所有配置，API Key 从环境变量读取。
"""
import os
from dotenv import load_dotenv

load_dotenv()  # 从 .env 文件加载环境变量（本地开发用）

# ── LLM API 配置（通用，支持 DeepSeek / 豆包 / 通义千问 等 OpenAI 兼容平台）──
LLM_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
if not LLM_API_KEY:
    raise RuntimeError(
        "请在环境变量中设置 LLM_API_KEY 或 DEEPSEEK_API_KEY。\n"
        "支持平台：DeepSeek (api.deepseek.com)、豆包 (ark.cn-beijing.volces.com) 等"
    )

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

# LLM 参数
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 8192

# ── 搜索配置 ──
MAX_SEARCH_RESULTS_PER_QUERY = 8
SLEEP_BETWEEN_QUERIES = 0.5  # 搜索间隔（防 DuckDuckGo 限速）

# ── 匹配配置 ──
MIN_MATCH_SCORE = 50  # 低于此分数的竞赛不展示
MAX_CLOSED_COMPETITIONS = 1  # 已截止竞赛最多保留几条

# ── 公开访问开关 ──
# 设为 "false" 关闭公开访问，仅管理员可用（管理员通过 x-saifu-admin 请求头识别）
SAIFU_ENABLED = os.environ.get("SAIFU_ENABLED", "true").lower() != "false"
ADMIN_HASH = "fea2b9dcfc927a0c9d6fad5781f64b60754dce0ea76bbeca9eac202c553b049f"  # SHA256(xiaolei0207)
