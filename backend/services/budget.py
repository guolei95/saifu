"""
赛赋(SaiFu) API 消费预算追踪 + 使用分析 — 限制服务端 DeepSeek 总消费不超过 5 元。
超过上限后所有用户需自备密钥，前端显示「小雷已破产」。

同时记录每笔调用的详细信息（类型、token、费用、是否管理员），
支持按类型/用户/日期等维度查询分析数据。
"""
import os
import json
import threading
from datetime import datetime, timezone, date
from contextvars import ContextVar

# ── DeepSeek 官方定价（CNY / 1M tokens）──
# deepseek-chat: 输入 ¥1/M, 输出 ¥2/M
PRICE_INPUT_PER_1M = 1.0
PRICE_OUTPUT_PER_1M = 2.0

# ── 预算上限 ──
BUDGET_CAP = float(os.environ.get("SAIFU_BUDGET_CAP", "5.0"))

# ── 文件路径 ──
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
BUDGET_FILE = os.path.join(DATA_DIR, "budget.json")
USAGE_LOG_FILE = os.path.join(DATA_DIR, "usage_log.jsonl")

# ── 调用上下文（调用方在发起 LLM 请求前设置）──
call_ctx_type: ContextVar[str] = ContextVar("call_type", default="unknown")
call_ctx_admin: ContextVar[bool] = ContextVar("is_admin", default=False)

_lock = threading.Lock()


# ═══════════════════════════════════════════
# 预算文件读写
# ═══════════════════════════════════════════

def _load_budget() -> dict:
    """加载预算文件，不存在则初始化。"""
    if os.path.exists(BUDGET_FILE):
        try:
            with open(BUDGET_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "cap" not in data:
                data["cap"] = BUDGET_CAP
            return data
        except (json.JSONDecodeError, IOError):
            pass
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


# ═══════════════════════════════════════════
# 预算检查（快速路径，给 ai_client 用）
# ═══════════════════════════════════════════

def get_budget_status() -> dict:
    """查询当前预算状态。"""
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
    """检查预算是否还有余额。"""
    with _lock:
        data = _load_budget()
        return data["total_cost"] < data["cap"]


def is_bankrupt() -> bool:
    """是否已破产。"""
    return not check_budget()


# ═══════════════════════════════════════════
# 详细使用记录（每笔调用记一条 JSONL）
# ═══════════════════════════════════════════

def record_usage(prompt_tokens: int, completion_tokens: int):
    """记录一次 API 调用 — 同时更新余额 & 追加详细日志。

    从 contextvars 自动获取 call_type 和 is_admin。
    """
    cost = (prompt_tokens / 1_000_000) * PRICE_INPUT_PER_1M + \
           (completion_tokens / 1_000_000) * PRICE_OUTPUT_PER_1M

    call_type = call_ctx_type.get()
    is_admin = call_ctx_admin.get()

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": call_type,
        "in": prompt_tokens,
        "out": completion_tokens,
        "cost": round(cost, 8),
        "admin": is_admin,
    }

    with _lock:
        # 1. 更新预算余额
        data = _load_budget()
        data["total_cost"] += cost
        data["call_count"] = data.get("call_count", 0) + 1
        _save_budget(data)

        # 2. 追加详细日志
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(USAGE_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return cost


def get_bankrupt_message() -> str:
    """破产提示消息。"""
    return (
        "[BANKRUPT] 小雷已破产 😭\n"
        "服务端 DeepSeek API 的 5 元预算已耗尽，请使用自己的 API 密钥继续使用赛赋。\n"
        "点击下方按钮设置你的密钥（支持 DeepSeek / 豆包 / OpenAI 兼容平台）"
    )


# ═══════════════════════════════════════════
# 使用分析（读取日志，聚合统计）
# ═══════════════════════════════════════════

def _read_all_logs() -> list[dict]:
    """读取全部使用日志。"""
    entries = []
    if not os.path.exists(USAGE_LOG_FILE):
        return entries
    with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def get_analytics() -> dict:
    """获取完整使用分析数据。

    返回字段：
    - total: 总调用次数 / 总费用
    - by_type: 按调用类型（match / import_research / target_research / personal_summary）
    - by_role: 管理员 vs 普通用户（各自次数 + 费用）
    - daily: 按天汇总
    - recent: 最近 20 条调用记录
    - budget: 当前预算状态
    - estimated_remaining: 按历史均价估算还能用多少次
    """
    entries = _read_all_logs()
    budget = get_budget_status()

    # ── 按类型 ──
    by_type: dict[str, dict] = {}
    # ── 按角色 ──
    admin_calls = 0
    admin_cost = 0.0
    user_calls = 0
    user_cost = 0.0
    # ── 按天 ──
    daily: dict[str, dict] = {}

    for e in entries:
        ct = e.get("type", "unknown")
        c = e.get("cost", 0)
        is_admin = e.get("admin", False)
        ts = e.get("ts", "")[:10]  # YYYY-MM-DD

        # 按类型
        if ct not in by_type:
            by_type[ct] = {"calls": 0, "cost": 0.0, "tokens_in": 0, "tokens_out": 0}
        by_type[ct]["calls"] += 1
        by_type[ct]["cost"] += c
        by_type[ct]["tokens_in"] += e.get("in", 0)
        by_type[ct]["tokens_out"] += e.get("out", 0)

        # 按角色
        if is_admin:
            admin_calls += 1
            admin_cost += c
        else:
            user_calls += 1
            user_cost += c

        # 按天
        if ts not in daily:
            daily[ts] = {"calls": 0, "cost": 0.0}
        daily[ts]["calls"] += 1
        daily[ts]["cost"] += c

    # ── 格式化 ──
    for k, v in by_type.items():
        v["cost"] = round(v["cost"], 6)
        v["avg_cost"] = round(v["cost"] / v["calls"], 6) if v["calls"] else 0

    daily_sorted = [{"date": k, **{sk: round(sv, 6) if isinstance(sv, float) else sv for sk, sv in v.items()}}
                    for k, v in sorted(daily.items())]

    # 估算还能用多少次（按历史均价）
    avg_cost_per_call = budget["total_cost"] / max(budget["call_count"], 1)
    estimated_remaining = int(budget["remaining"] / avg_cost_per_call) if avg_cost_per_call > 0 else 0

    # 最近 20 条
    recent = list(reversed(entries[-20:]))

    return {
        "total": {
            "calls": budget["call_count"],
            "cost": round(budget["total_cost"], 6),
        },
        "by_type": by_type,
        "by_role": {
            "admin": {"calls": admin_calls, "cost": round(admin_cost, 6)},
            "user": {"calls": user_calls, "cost": round(user_cost, 6)},
        },
        "daily": daily_sorted,
        "recent": recent,
        "budget": budget,
        "estimated_remaining_calls": estimated_remaining,
    }
