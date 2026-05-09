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

from match.engine import match_competitions
from config import DEEPSEEK_API_KEY
from services.knowledge_base import COMPETITION_FACTS

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
tasks: dict = {}  # task_id -> {"status": "processing"|"done"|"error", "result": ..., "created_at": ..., "error": ...}


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


@app.get("/api/health")
async def health():
    """健康检查端点。"""
    return {
        "status": "ok",
        "deepseek_configured": bool(DEEPSEEK_API_KEY),
    }


@app.get("/api/competitions")
async def list_competitions():
    """返回常识库中收录的竞赛列表。"""
    return {
        "success": True,
        "competitions": [
            {"name": name, "url": info.get("official_url", ""), "form": info.get("参赛形式", "")}
            for name, info in COMPETITION_FACTS.items()
        ]
    }


@app.post("/api/match")
async def start_match(profile: ProfileInput):
    """提交匹配任务 — 立即返回 task_id，后台异步处理。

    前端用 task_id 轮询 GET /api/match/{task_id} 获取结果。
    """
    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {
        "status": "processing",
        "created_at": datetime.now().isoformat(),
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
        "result": task["result"],
        "error": task["error"],
    }


async def _run_match(task_id: str, profile_dict: dict):
    """后台执行匹配任务。"""
    try:
        # 在线程池中运行同步匹配函数，避免阻塞事件循环
        result = await asyncio.to_thread(match_competitions, profile_dict)
        tasks[task_id]["status"] = "done"
        tasks[task_id]["result"] = result
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e) or "匹配服务暂时不可用"


# ── 定期清理过期任务 ──
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
