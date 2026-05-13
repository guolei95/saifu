"""
赛赋(SaiFu) API 消费预算追踪 — 限制服务端 DeepSeek API 总消费不超过 5 元。
超过上限后所有用户需自备密钥，前端显示「小雷已破产」。
"""
import os
import json
import threading
from datetime import datetime, timezone

# ── DeepSeek 官方定价（CNY / 1M tokens）──
# deepseek-chat: 输入 ¥1/M, 输出 ¥2/M
PRICE_INPUT_PER_1M = 1.0   # 每百万输入 token 的 CNY 价格
PRICE_OUTPUT_PER_1M = 2.0  # 每百万输出 token 的 CNY 价格

# ── 预算上限 ──
BUDGET_CAP = float(os.environ.get("SAIFU_BUDGET_CAP", "5.0"))

# ── 预算文件路径 ──
BUDGET_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "budget.json")

_lock = threading.Lock()


def _load_budget() -> dict:
    """加载预算文件，不存在则初始化。"""
    if os.path.exists(BUDGET_FILE):
        try:
            with open(BUDGET_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 兼容旧格式：确保 cap 字段存在
            if "cap" not in data:
                data["cap"] = BUDGET_CAP
            return data
        except (json.JSONDecodeError, IOError):
            pass
    # 初始化
    return {
        "total_cost": 0.0,
        "cap": BUDGET_CAP,
        "currency": "CNY",
        "call_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _save_budget(data: dict):
    """保存预算文件（原子写入）。"""
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    os.makedirs(os.path.dirname(BUDGET_FILE), exist_ok=True)
    tmp = BUDGET_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, BUDGET_FILE)


def get_budget_status() -> dict:
    """查询当前预算状态（供 API 返回前端展示）。"""
    with _lock:
        data = _load_budget()
        remaining = max(0, data["cap"] - data["total_cost"])
        return {
            "total_cost": round(data["total_cost"], 6),
            "cap": data["cap"],
            "remaining": round(remaining, 6),
            "currency": data["currency"],
            "call_count": data["call_count"],
            "is_bankrupt": data["total_cost"] >= data["cap"],
            "usage_percent": round(data["total_cost"] / data["cap"] * 100, 2) if data["cap"] > 0 else 0,
        }


def check_budget() -> bool:
    """检查预算是否还有余额。返回 True 表示可以继续调用。"""
    with _lock:
        data = _load_budget()
        return data["total_cost"] < data["cap"]


def is_bankrupt() -> bool:
    """是否已破产（预算耗尽）。"""
    return not check_budget()


def record_usage(prompt_tokens: int, completion_tokens: int):
    """记录一次 API 调用的 token 消耗并更新累计费用。

    Args:
        prompt_tokens: 输入 token 数
        completion_tokens: 输出 token 数
    """
    cost = (prompt_tokens / 1_000_000) * PRICE_INPUT_PER_1M + \
           (completion_tokens / 1_000_000) * PRICE_OUTPUT_PER_1M

    with _lock:
        data = _load_budget()
        data["total_cost"] += cost
        data["call_count"] = data.get("call_count", 0) + 1
        _save_budget(data)

    return cost


def get_bankrupt_message() -> str:
    """破产提示消息，前端直接展示或弹窗。"""
    return (
        "[BANKRUPT] 小雷已破产 😭\n"
        "服务端 DeepSeek API 的 5 元预算已耗尽，请使用自己的 API 密钥继续使用赛赋。\n"
        "点击下方按钮设置你的密钥（支持 DeepSeek / 豆包 / OpenAI 兼容平台）"
    )
