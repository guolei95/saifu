"""
赛赋(SaiFu) FastAPI 应用入口 — 提供 Web API。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os

from match.engine import match_competitions
from config import DEEPSEEK_API_KEY
from services.knowledge_base import COMPETITION_FACTS

app = FastAPI(title="赛赋 SaiFu - 智能竞赛匹配平台", version="1.0.0")

# ── CORS 中间件 ──
# 开发阶段允许所有来源，部署后限定 Vercel 域名
FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
async def match(profile: ProfileInput):
    """智能匹配端点 — 接收用户画像，返回匹配结果。

    处理时间：约 30-60 秒。
    """
    try:
        # 转为普通 dict
        profile_dict = profile.model_dump()
        result = match_competitions(profile_dict)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e) or "匹配服务暂时不可用，请稍后重试",
        }


# ── 本地开发入口 ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
