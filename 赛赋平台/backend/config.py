"""
赛赋(SaiFu) 配置模块 — 统一管理所有配置，API Key 从环境变量读取。
"""
import os

# ── DeepSeek API 配置 ──
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("请在环境变量中设置 DEEPSEEK_API_KEY")

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"  # 必须带 /v1
DEEPSEEK_MODEL = "deepseek-chat"

# LLM 参数
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 16384

# ── 搜索配置 ──
MAX_SEARCH_RESULTS_PER_QUERY = 8
SLEEP_BETWEEN_QUERIES = 0.8  # 搜索间隔（防 DuckDuckGo 限速）

# ── 匹配配置 ──
MIN_MATCH_SCORE = 50  # 低于此分数的竞赛不展示
MAX_CLOSED_COMPETITIONS = 1  # 已截止竞赛最多保留几条
