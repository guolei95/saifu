"""
赛赋(SaiFu) 个性化竞赛调研服务 — 基于用户画像 + 知识库生成调研报告。
"""
from services.ai_client import call_deepseek
from services.knowledge_base import get_kb_competition_list, COMPETITION_FACTS


def _build_research_prompt(user_data: dict) -> str:
    """构造个性化调研 prompt（含 84 项 A 类竞赛知识库）。"""
    kb_list = get_kb_competition_list()

    # 构建用户画像文本
    name = user_data.get("name", "未知")
    school = user_data.get("school", "未知")
    major = user_data.get("major", "未知")
    grade = user_data.get("grade", "未知")
    interests = user_data.get("interests", "未指定")
    goals = user_data.get("goals", "未指定")
    skills = user_data.get("core_skills") or user_data.get("skills", "未指定")
    skill_domains = user_data.get("skill_domains", "未指定")
    tools = user_data.get("tools", "未指定")
    time_commitment = user_data.get("weekly_hours") or user_data.get("time_commitment", "未指定")
    available_months = user_data.get("free_months") or user_data.get("available_months", "未指定")
    summer_winter = user_data.get("summer_winter_available") or user_data.get("summer_winter", "未指定")
    competition_level = user_data.get("competition_level", "不限")
    team_type = user_data.get("team_type", "未指定")
    has_advisor = user_data.get("has_advisor", "未指定")
    can_cross_school = user_data.get("can_cross_school", "未指定")
    preferred_duration = user_data.get("competition_duration") or user_data.get("preferred_duration", "未指定")
    preferred_format = user_data.get("competition_format") or user_data.get("preferred_format", "未指定")
    fee_budget = user_data.get("registration_fee") or user_data.get("fee_budget", "未指定")
    language_pref = user_data.get("language_pref", "未指定")
    avoid_types = user_data.get("avoid_types", "无")
    highest_award = user_data.get("highest_award", "无")
    projects = user_data.get("representative_projects", "无")
    has_portfolio = user_data.get("has_portfolio", "无")
    has_lab = user_data.get("has_lab", "未指定")
    join_school_team = user_data.get("join_school_team", "未指定")
    need_teammate = user_data.get("need_teammate", "未指定")
    min_award = user_data.get("min_award", "未指定")
    ideal_goal = user_data.get("ideal_goal", "未指定")
    strategy = user_data.get("strategy", "未指定")
    major_category = user_data.get("major_category", "未指定")

    # 构建参数化避免文本
    avoid_text = f"\n- 需避免的竞赛类型：{avoid_types}" if avoid_types and avoid_types != "无" else ""

    return f"""你是一位资深的「大学生竞赛规划顾问」。请你根据以下用户画像，为该学生做一份**个性化竞赛调研报告**。

## 用户画像
━━━━━━━━━━━━━━━━
姓名：{name}
学校：{school}
专业：{major}
年级：{grade}
专业大类：{major_category}
兴趣领域：{interests}
参赛目标：{goals}
核心技能：{skills}
技能领域：{skill_domains}
常用工具/软件：{tools}
每周可投入时间：{time_commitment}
空闲月份：{available_months}
寒暑假可集中备赛：{summer_winter}
偏好赛事级别：{competition_level}
个人/团队偏好：{team_type}
有无指导老师：{has_advisor}
是否接受跨校组队：{can_cross_school}
偏好比赛周期：{preferred_duration}
偏好比赛形式：{preferred_format}
报名费预算：{fee_budget}
语言偏好：{language_pref}{avoid_text}
过往最高获奖：{highest_award}
代表性项目/作品：{projects}
是否有作品集/GitHub：{has_portfolio}
学校是否有实验室/战队：{has_lab}
是否愿意加入校内团队：{join_school_team}
是否需要匹配队友：{need_teammate}
最低接受获奖层次：{min_award}
理想获奖目标：{ideal_goal}
竞赛策略：{strategy}
━━━━━━━━━━━━━━━━

## 竞赛知识库（84 项 A 类竞赛，优先从中推荐）
{kb_list}

## 调研任务
请你严格按照以下 JSON 格式返回调研结果（只返回 JSON，不要其他文字）：

```json
{{
  "recommendations": [
    {{
      "name": "竞赛全称",
      "level": "国家级/省级/国际级",
      "deadline": "2026-XX-XX 或 待公布",
      "form": "个人赛/团队赛",
      "fee": "免费 或 金额",
      "reason": "为什么适合该用户（结合专业、技能、兴趣、目标，80字内）",
      "preparation": "需要准备什么（技能、材料、队友等，60字内）",
      "match_score": 85,
      "focus": "保研加分,能力锻炼,拿奖率高,企业直通 中选1-3个",
      "official_url": "官网链接（不确定填'待查'）"
    }}
  ],
  "advice": {{
    "time_plan": "根据用户空闲时间和年级，给出备赛时间规划建议（200字内）",
    "skill_improvement": "根据用户技能短板，给出技能补强建议（150字内）",
    "team_strategy": "针对该用户的组队建议（队友类型、如何找人，150字内）"
  }},
  "risks": [
    {{
      "type": "短板类型（如：指导老师缺失/技能空白/时间紧张/年级劣势/跨校困难）",
      "detail": "具体风险描述（80字内）",
      "solution": "替代方案或应对策略（100字内）"
    }}
  ],
  "summary": "一段话总结该用户的竞赛适配方向和整体建议（150字内）"
}}
```

## 评分规则
- match_score 综合评分 0-100 分，>=80 分表示高度匹配
- 重点关注：专业对口度、技能匹配度、时间适合度、目标契合度
- A 类赛事自动 +5~10 分，在 reason 中标注 [A类赛事]

## 推荐规则
- 必须推荐 5-8 个竞赛
- 优先从 84 项 A 类竞赛知识库中选择
- 如果用户有 avoid_types 中的类型，坚决不推荐
- 每个推荐必须给出具体的 reason 和 preparation
- 综合考虑用户的时间投入、技能水平和参赛目标

## 风险分析规则
- 至少分析 1-3 个潜在风险点
- 如果没有明显短板，标注"暂无明显短板"
- 每个风险必须给出可行的替代方案

请开始分析。"""


def run_research(user_data: dict) -> dict:
    """执行个性化竞赛调研。

    Args:
        user_data: 从报告解析出的用户画像 dict

    Returns:
        dict: 调研结果，含 recommendations / advice / risks / summary
    """
    prompt = _build_research_prompt(user_data)

    messages = [
        {"role": "system", "content": "你是一位资深的大学生竞赛规划顾问，擅长根据学生画像推荐最适合的竞赛并给出备赛建议。你只返回 JSON，不输出其他内容。"},
        {"role": "user", "content": prompt},
    ]

    # 用 call_deepseek 获取原始文本，手动解析 JSON（更稳健）
    raw_text = call_deepseek(messages, temperature=0.4, max_tokens=4096)

    # 解析 JSON
    import json
    import re

    # 清理 markdown 代码块
    text = raw_text
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # 尝试多种解析策略
    strategies = [text, text.strip()]
    for s in strategies:
        try:
            result = json.loads(s)
            if isinstance(result, dict) and "recommendations" in result:
                return result
        except json.JSONDecodeError:
            pass

    # 最后兜底：尝试从文本中提取 JSON
    try:
        match = re.search(r'\{[\s\S]*"recommendations"[\s\S]*\}', text)
        if match:
            result = json.loads(match.group(0))
            if isinstance(result, dict):
                return result
    except (json.JSONDecodeError, AttributeError):
        pass

    # 完全解析失败，返回基础结构
    return {
        "recommendations": [],
        "advice": {
            "time_plan": "AI 暂未生成建议，请重试。",
            "skill_improvement": "",
            "team_strategy": "",
        },
        "risks": [],
        "summary": "调研结果解析失败，原始回复：" + raw_text[:200],
        "_raw": raw_text,
    }
