"""
赛赋(SaiFu) FastAPI 应用入口 — 提供 Web API。
采用提交+轮询模式处理长时匹配任务，避免 Cloudflare Tunnel 断连。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import asyncio
import uuid
from datetime import datetime

from match.engine import match_competitions, generate_personal_summary
from config import LLM_API_KEY
from services.knowledge_base import COMPETITION_FACTS
from services.research import run_research
from services.ai_client import ServerAPIExhausted

app = FastAPI(title="赛赋 SaiFu - 智能竞赛匹配平台", version="1.0.0")

# ── CORS 中间件 ──
FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 任务存储（内存中）──
tasks: dict = {}  # task_id -> {"status": "queued"|"processing"|"done"|"error", "result": ..., "created_at": ..., "queue_position": N, "error": ...}

# ── 并发控制（最多同时处理 5 个匹配/调研任务）──
match_semaphore = asyncio.Semaphore(5)

def _get_queue_position(task_id: str) -> int:
    """计算某任务前面还有几个排队的。"""
    current = tasks.get(task_id)
    if not current:
        return 0
    # 统计创建时间更早且状态为 queued 的任务
    pos = 0
    for tid, t in tasks.items():
        if t.get("status") == "queued" and t.get("created_at", "") < current.get("created_at", ""):
            pos += 1
    return pos


class ProfileInput(BaseModel):
    """用户画像输入 — 所有字段可选，缺的自动用默认值。"""
    school: Optional[str] = ""
    major: Optional[str] = ""
    grade: Optional[str] = ""
    interests: Optional[str] = ""
    skills: Optional[str] = ""
    tech_directions: Optional[list] = []
    tools: Optional[list] = []
    other_skills: Optional[str] = ""
    goals: Optional[list] = []
    time_commitment: Optional[str] = ""
    available_months: Optional[str] = ""
    summer_winter: Optional[str] = ""
    preference: Optional[str] = ""
    team_preference: Optional[str] = ""
    preferred_duration: Optional[str] = ""
    preferred_format: Optional[str] = ""
    fee_budget: Optional[str] = ""
    language_pref: Optional[str] = ""
    has_advisor: Optional[str] = ""
    can_cross_school: Optional[str] = ""
    avoid_types: Optional[str] = ""
    past_highest_award: Optional[str] = ""
    representative_projects: Optional[list] = []
    has_portfolio: Optional[bool] = False
    portfolio_link: Optional[str] = ""
    has_lab: Optional[bool] = False
    join_school_team: Optional[bool] = False
    need_teammate: Optional[bool] = False
    min_award: Optional[str] = ""
    ideal_goal: Optional[str] = ""
    strategy: Optional[str] = ""
    # 可选：用户自己的 API Key（存在浏览器 localStorage，不落盘）
    user_api_key: Optional[str] = ""
    # 可选：用户指定的 API Base URL 和模型（支持 OpenAI / 豆包 等）
    user_api_base_url: Optional[str] = ""
    user_api_model: Optional[str] = ""


class ImportResearchInput(BaseModel):
    """导入用户报告 + 触发调研的请求体。"""
    user_data: dict  # 从报告文本解析出的所有字段


class TargetResearchInput(BaseModel):
    """定向调研（知道比赛名称）请求体。"""
    school: str = ""
    major: str = ""
    grade: str = ""
    competition_name: str = ""  # 用户指定的比赛名称
    skills: str = ""
    major_category: str = ""
    goals: list = []
    time_commitment: str = ""
    alias: str = ""
    # 可选：用户自己的 API Key
    user_api_key: Optional[str] = ""
    user_api_base_url: Optional[str] = ""
    user_api_model: Optional[str] = ""


@app.get("/api/health")
async def health():
    """健康检查端点。"""
    return {
        "status": "ok",
        "llm_configured": bool(LLM_API_KEY),
    }


@app.get("/api/competitions")
async def list_competitions():
    """返回84项A类竞赛知识库。"""
    # 去重（同一竞赛可能有多个别称）
    seen_ids = set()
    items = []
    for name, info in COMPETITION_FACTS.items():
        cid = info.get("id")
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        items.append({
            "id": cid,
            "name": info.get("name", name),
            "alt_name": info.get("alt_name", ""),
            "url": info.get("url", ""),
            "form": info.get("form", ""),
            "timing": info.get("timing", ""),
            "fee": info.get("fee", ""),
            "format": info.get("format", ""),
            "requirements": info.get("requirements", ""),
        })
    # 按 id 排序
    items.sort(key=lambda x: x.get("id") or 999)
    return {
        "success": True,
        "count": len(items),
        "competitions": items,
    }


@app.post("/api/match")
async def start_match(profile: ProfileInput):
    """提交匹配任务 — 立即返回 task_id，后台异步处理。

    前端用 task_id 轮询 GET /api/match/{task_id} 获取结果。
    """
    task_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    tasks[task_id] = {
        "status": "queued",
        "created_at": now,
        "result": None,
        "error": None,
    }

    profile_dict = profile.model_dump()

    # 启动后台任务
    asyncio.create_task(_run_match(task_id, profile_dict))

    return {
        "success": True,
        "task_id": task_id,
        "message": "匹配任务已提交，请轮询获取结果",
    }


@app.get("/api/match/{task_id}")
async def get_match_result(task_id: str):
    """查询匹配任务状态和结果。

    status="queued": 排队等待中
    status="processing": 还在处理中
    status="done": 已完成，result 字段包含匹配结果
    status="error": 出错，error 字段包含错误信息
    """
    task = tasks.get(task_id)
    if not task:
        return {"success": False, "error": "任务不存在或已过期", "status": "not_found"}

    return {
        "success": True,
        "task_id": task_id,
        "status": task["status"],
        "queue_position": _get_queue_position(task_id) if task["status"] == "queued" else 0,
        "result": task["result"],
        "error": task["error"],
    }


async def _run_match(task_id: str, profile_dict: dict):
    """后台执行匹配任务。"""
    import logging
    # 提取用户 LLM 配置（如有），用后即弃不落盘
    user_api_key = profile_dict.pop("user_api_key", None) or None
    user_api_base = profile_dict.pop("user_api_base_url", None) or None
    user_api_model = profile_dict.pop("user_api_model", None) or None

    # 构建用户 LLM 配置（有 key 才构建，否则传 None 走服务器 Key）
    user_llm = None
    if user_api_key:
        user_llm = {"api_key": user_api_key}
        if user_api_base:
            user_llm["base_url"] = user_api_base
        if user_api_model:
            user_llm["model"] = user_api_model

    try:
        # 排队：获取并发槽位
        async with match_semaphore:
            tasks[task_id]["status"] = "processing"
            # 在线程池中运行同步匹配函数，避免阻塞事件循环
            result = await asyncio.to_thread(match_competitions, profile_dict, api_key=user_llm)
        # 生成个性化总结（备赛建议 + 风险提示 + 总体评估）
        try:
            top_matches = result.get("open", [])[:5]
            summary_data = await asyncio.to_thread(
                generate_personal_summary, profile_dict, top_matches, api_key=user_llm
            )
            result["advice"] = summary_data.get("advice", {})
            result["risks"] = summary_data.get("risks", [])
            result["summary"] = summary_data.get("summary", "")
            # 校验：LLM 可能返回空字段，用模板补全
            if not result["advice"].get("time_plan") and not result["advice"].get("skill_improvement") and not result["advice"].get("team_strategy"):
                top_names = [m.get("name", "目标竞赛") for m in top_matches[:3] if m.get("name")]
                result["advice"] = {
                    "time_plan": f"建议优先关注 {'、'.join(top_names) if top_names else '匹配到的竞赛'}，提前规划备赛节奏。",
                    "skill_improvement": "结合你的专业基础，针对竞赛要求补强相关技能。",
                    "team_strategy": "寻找优势互补的队友，通过学校竞赛群或实验室招募。",
                }
            if not result.get("risks") or len(result.get("risks", [])) == 0:
                result["risks"] = [
                    {"type": "时间管理", "detail": "备赛需持续投入，可能与课业冲突", "solution": "制定周计划，拆解为每日小目标"},
                ]
            if not result.get("summary") or len(str(result.get("summary", "")).strip()) < 10:
                total_open = len(result.get("open", []))
                total_closed = len(result.get("closed", []))
                top_name = top_matches[0].get("name", "匹配到的竞赛") if top_matches else "匹配到的竞赛"
                result["summary"] = f"系统为你匹配到 {total_open} 个报名中的竞赛" + (f"和 {total_closed} 个可提前规划的竞赛" if total_closed else "") + f"。建议优先关注 {top_name}，结合你的专业和时间安排重点准备。"
        except Exception as e:
            logging.warning(f"生成个人总结失败，使用模板兜底: {e}")
            # 模板兜底：即使 LLM 失败，也保证用户能看到总结
            open_list = result.get("open", [])
            closed_list = result.get("closed", [])
            top3 = [m.get("name", "") for m in (open_list[:3]) if m.get("name")]
            names_str = "、".join(top3) if top3 else "匹配到的竞赛"
            result["advice"] = {
                "time_plan": f"建议优先关注 {names_str}，根据报名截止时间倒推备赛节奏，提前 1-3 个月开始准备。",
                "skill_improvement": f"针对 {names_str} 的要求，建议结合你的专业和技能基础，提前补强竞赛所需的特定技能。",
                "team_strategy": "建议寻找 2-3 名优势互补的队友（如技术+设计+答辩），通过学校竞赛群或实验室招募。",
            }
            result["risks"] = [
                {"type": "时间管理", "detail": "备赛需要持续投入时间，与课业可能冲突", "solution": "制定周计划，将备赛任务拆解为每天 1-2 小时的小目标"},
                {"type": "信息不对称", "detail": "竞赛规则和评审标准可能更新", "solution": "定期查看官网通知，加入竞赛交流群获取最新动态"},
            ]
            total_open = len(open_list)
            total_closed = len(closed_list)
            result["summary"] = f"系统为你匹配到 {total_open} 个报名中的竞赛" + (f"和 {total_closed} 个可提前规划的竞赛" if total_closed else "") + f"。建议优先关注 {names_str}，结合你的专业背景和时间安排，选择匹配度最高的 2-3 个竞赛重点准备。"
        tasks[task_id]["status"] = "done"
        tasks[task_id]["result"] = result
    except ServerAPIExhausted as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e) or "匹配服务暂时不可用"


# ── 定期清理过期任务 ──
# ── 导入调研 API ──
@app.post("/api/import-and-research")
async def start_import_research(body: ImportResearchInput):
    """导入用户报告 + 发起调研 — 立即返回 task_id，后台异步处理。

    前端用 task_id 轮询 GET /api/import-and-research/{task_id} 获取调研结果。
    """
    task_id = "research_" + str(uuid.uuid4())[:8]
    tasks[task_id] = {
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "result": None,
        "error": None,
    }

    user_data = body.user_data

    # 启动后台调研任务
    asyncio.create_task(_run_import_research(task_id, user_data))

    return {
        "success": True,
        "task_id": task_id,
        "message": "调研任务已提交，请轮询获取结果",
    }


@app.get("/api/import-and-research/{task_id}")
async def get_research_result(task_id: str):
    """查询调研任务状态和结果。

    status="processing": 还在分析中
    status="done": 已完成，result 字段包含调研结果
    status="error": 出错，error 字段包含错误信息
    """
    task = tasks.get(task_id)
    if not task:
        return {"success": False, "error": "任务不存在或已过期", "status": "not_found"}

    return {
        "success": True,
        "task_id": task_id,
        "status": task["status"],
        "result": task["result"],
        "error": task["error"],
    }


async def _run_import_research(task_id: str, user_data: dict):
    """后台执行导入调研任务：保存用户数据 + 调用 AI 调研。"""
    import json
    import os
    from datetime import date

    # 提取用户 LLM 配置（如有），用后即弃，不落盘
    user_api_key = user_data.pop("user_api_key", None) or None
    user_api_base = user_data.pop("user_api_base_url", None) or None
    user_api_model = user_data.pop("user_api_model", None) or None

    user_llm = None
    if user_api_key:
        user_llm = {"api_key": user_api_key}
        if user_api_base:
            user_llm["base_url"] = user_api_base
        if user_api_model:
            user_llm["model"] = user_api_model

    try:
        # 1. 保存用户数据到本地 JSON（不含 api_key）
        name = user_data.get("name", "未知用户")
        safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
        today_str = date.today().isoformat()
        users_dir = os.path.join(os.path.dirname(__file__), "data", "users")
        os.makedirs(users_dir, exist_ok=True)

        user_filename = f"{safe_name}_{today_str}.json"
        user_path = os.path.join(users_dir, user_filename)
        with open(user_path, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        # 2. 调用 AI 调研（在线程池中运行同步函数）
        research_result = await asyncio.to_thread(run_research, user_data, api_key=user_llm)

        # 3. 保存调研结果到本地 JSON
        research_filename = f"{safe_name}_{today_str}_research.json"
        research_path = os.path.join(users_dir, research_filename)
        with open(research_path, "w", encoding="utf-8") as f:
            json.dump(research_result, f, ensure_ascii=False, indent=2)

        # 4. 构建返回结果
        tasks[task_id]["status"] = "done"
        tasks[task_id]["result"] = {
            "success": True,
            "user_name": name,
            "user_school": user_data.get("school", ""),
            "user_file": user_filename,
            "research_file": research_filename,
            "recommendations": research_result.get("recommendations", []),
            "advice": research_result.get("advice", {}),
            "risks": research_result.get("risks", []),
            "summary": research_result.get("summary", ""),
        }
    except ServerAPIExhausted as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e) or "调研服务暂时不可用"


# ── 定向调研 API（知道比赛名称 → 深度分析）──
@app.post("/api/target-research")
async def start_target_research(body: TargetResearchInput):
    """提交定向调研任务 — 立即返回 task_id，后台异步处理。

    用户知道比赛名称，填写简化画像后，AI 查找该比赛详情并生成个性化备赛规划。
    """
    task_id = "target_" + str(uuid.uuid4())[:8]
    tasks[task_id] = {
        "status": "processing",
        "created_at": datetime.now().isoformat(),
        "result": None,
        "error": None,
    }

    profile_dict = body.model_dump()

    # 启动后台任务
    asyncio.create_task(_run_target_research(task_id, profile_dict))

    return {
        "success": True,
        "task_id": task_id,
        "message": "定向调研任务已提交，请轮询获取结果",
    }


@app.get("/api/target-research/{task_id}")
async def get_target_research_result(task_id: str):
    """查询定向调研任务状态和结果。"""
    task = tasks.get(task_id)
    if not task:
        return {"success": False, "error": "任务不存在或已过期", "status": "not_found"}

    return {
        "success": True,
        "task_id": task_id,
        "status": task["status"],
        "result": task["result"],
        "error": task["error"],
    }


async def _run_target_research(task_id: str, profile_dict: dict):
    """后台执行定向调研任务。"""
    from services.research import run_targeted_research
    import logging

    # 提取用户 LLM 配置（如有）
    user_api_key = profile_dict.pop("user_api_key", None) or None
    user_api_base = profile_dict.pop("user_api_base_url", None) or None
    user_api_model = profile_dict.pop("user_api_model", None) or None

    user_llm = None
    if user_api_key:
        user_llm = {"api_key": user_api_key}
        if user_api_base:
            user_llm["base_url"] = user_api_base
        if user_api_model:
            user_llm["model"] = user_api_model

    try:
        result = await asyncio.to_thread(run_targeted_research, profile_dict, api_key=user_llm)
        tasks[task_id]["status"] = "done"
        tasks[task_id]["result"] = {
            "success": True,
            "user_name": profile_dict.get("alias", "") or profile_dict.get("school", ""),
            "recommendations": result.get("recommendations", []),
            "advice": result.get("advice", {}),
            "risks": result.get("risks", []),
            "summary": result.get("summary", ""),
        }
    except ServerAPIExhausted as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)
    except Exception as e:
        logging.exception("定向调研失败")
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e) or "定向调研服务暂时不可用"


async def _cleanup_old_tasks():
    """每 5 分钟清理超过 30 分钟的任务。"""
    while True:
        await asyncio.sleep(300)
        now = datetime.now()
        to_remove = []
        for tid, task in tasks.items():
            created = datetime.fromisoformat(task["created_at"])
            if (now - created).total_seconds() > 1800:
                to_remove.append(tid)
        for tid in to_remove:
            del tasks[tid]


@app.on_event("startup")
async def startup():
    asyncio.create_task(_cleanup_old_tasks())


# ── 本地开发入口 ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
