"""
赛赋(SaiFu) 个性化竞赛调研服务 — 基于用户画像 + 知识库生成调研报告。
"""
from services.ai_client import call_deepseek
from services.knowledge_base import (
    get_kb_competition_list, COMPETITION_FACTS,
    local_match_from_kb, enrich_with_facts,
    get_benefit_text, get_pitfall_text, classify_competition,
    TIPS, MYTHS,
)


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


def _kb_result_to_recommendation(kb_item: dict) -> dict:
    """将知识库匹配结果转为 research 格式的推荐条目（含模板化 benefits/pitfalls/cat/desc）。"""
    # 截止日期：优先用 deadline_reference（如"每年5-8月"），其次用 registration_deadline
    deadline = (
        kb_item.get("deadline_reference") or
        kb_item.get("registration_deadline") or
        "待公布"
    )
    # 参赛形式：用 registration_form（已修复为真实数据如"团队(3人)"）
    form = kb_item.get("registration_form") or kb_item.get("participation_type", "团队赛")
    # 费用
    fee = kb_item.get("fee_amount", "免费")
    if not fee or fee == "未知":
        fee = "免费"
    # 描述：用 desc（现已扩到 300 字，含赛制流程+作品类型）
    desc = kb_item.get("desc", "")[:300]
    if not desc:
        desc = "A类学科竞赛，请查看官网了解备赛要求"
    # 评分
    score = int(kb_item.get("match_score", 75))
    # 类别
    cat = kb_item.get("cat", "🏫 学校/教育部类")
    # 推荐指数
    rec_idx = kb_item.get("recommend_index", 4)
    # benefits/pitfalls（从 KB 带过来，后面会补充）
    benefits = kb_item.get("benefits", "")
    pitfalls = kb_item.get("pitfalls", "")

    return {
        "name": kb_item.get("name", ""),
        "cat": cat,
        "level": "国家级",  # 84项A类竞赛均为国家级
        "recommend_index": rec_idx,
        "deadline": deadline,
        "form": form,
        "fee": fee,
        "desc": desc,
        "reason": kb_item.get("match_reason", "A类赛事，与你的专业和技能匹配"),
        "benefits": benefits,
        "pitfalls": pitfalls,
        "preparation": desc,
        "match_score": score,
        "focus": kb_item.get("focus", "保研加分,拿奖率高"),
        "official_url": kb_item.get("official_url") or kb_item.get("registration_url", "待查"),
        "_from_kb": True,
    }


def run_research(user_data: dict) -> dict:
    """执行个性化竞赛调研 — LLM分析 + 知识库强制匹配。

    Args:
        user_data: 从报告解析出的用户画像 dict

    Returns:
        dict: 调研结果，含 recommendations / advice / risks / summary
    """
    import json
    import re

    # ── 第1步：本地知识库强制匹配（保证A类竞赛不会漏）──
    # 构建 profile dict 用于 KB 匹配
    profile = {
        "school": user_data.get("school", ""),
        "major": user_data.get("major", ""),
        "grade": user_data.get("grade", ""),
        "interests": user_data.get("interests", ""),
        "skills": user_data.get("core_skills") or user_data.get("skills", ""),
        "tech_directions": user_data.get("skill_domains", []),
        "goals": [user_data.get("goals", "")] if isinstance(user_data.get("goals"), str) else user_data.get("goals", []),
        "time_commitment": user_data.get("weekly_hours") or user_data.get("time_commitment", ""),
        "avoid_types": user_data.get("avoid_types", ""),
    }
    kb_matches = local_match_from_kb(profile, top_n=10)
    kb_matches = [enrich_with_facts(m) for m in kb_matches]

    kb_recommendations = []
    seen_kb_names = set()
    for m in kb_matches:
        name = m.get("name", "")
        if name and name not in seen_kb_names:
            seen_kb_names.add(name)
            kb_recommendations.append(_kb_result_to_recommendation(m))

    # ── 第2步：LLM 深度分析（知识库作为参考）──
    prompt = _build_research_prompt(user_data)

    messages = [
        {"role": "system", "content": "你是一位资深的大学生竞赛规划顾问，擅长根据学生画像推荐最适合的竞赛并给出备赛建议。你只返回 JSON，不输出其他内容。"},
        {"role": "user", "content": prompt},
    ]

    # 用 call_deepseek 获取原始文本，手动解析 JSON（更稳健）
    raw_text = call_deepseek(messages, temperature=0.4, max_tokens=4096)

    # 解析 JSON
    text = raw_text
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    result = None
    for s in [text, text.strip()]:
        try:
            parsed = json.loads(s)
            if isinstance(parsed, dict) and "recommendations" in parsed:
                result = parsed
                break
        except json.JSONDecodeError:
            pass

    if result is None:
        try:
            match = re.search(r'\{[\s\S]*"recommendations"[\s\S]*\}', text)
            if match:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    result = parsed
        except (json.JSONDecodeError, AttributeError):
            pass

    if result is None:
        result = {
            "recommendations": [],
            "advice": {
                "time_plan": "AI 暂未生成建议，请重试。",
                "skill_improvement": "",
                "team_strategy": "",
            },
            "risks": [],
            "summary": "调研结果解析失败，请重试。",
        }

    # ── 第3步：智能合并 — LLM 富文本优先，KB 填补事实空缺 ──
    llm_recs = result.get("recommendations", [])

    # 简易名称归一化（用于跨 KB/LLM 去重匹配）
    def _norm_name(n):
        import re as _re
        n = n.lower().strip()
        n = _re.sub(r'[（(][^）)]*[）)]', '', n)
        n = _re.sub(r'[]「」『』""''""（）()[【】《》、，。；：！？·|/@#$%^&*+=~` _-]+', '', n)
        return n

    # 构建 KB 归一化名称 → KB 条目的映射
    kb_norm_map = {}
    for r in kb_recommendations:
        n = _norm_name(r.get("name", ""))
        if n:
            kb_norm_map[n] = r

    merged_recs = []
    seen_norm_names = set()

    # Pass 1: LLM 结果优先（富文本字段更个性化）
    for r in llm_recs:
        n = _norm_name(r.get("name", ""))
        if not n or n in seen_norm_names:
            continue
        seen_norm_names.add(n)

        # 如果 KB 中有同名竞赛，用 KB 事实数据补全 LLM 缺失字段
        if n in kb_norm_map:
            kb_item = kb_norm_map[n]
            for field in ["level", "deadline", "form", "fee", "official_url", "desc", "cat", "recommend_index"]:
                llm_val = str(r.get(field, "")).strip()
                kb_val = str(kb_item.get(field, "")).strip()
                if not llm_val or llm_val in ("未知", "待公布", "待查", "", "None"):
                    if kb_val and kb_val not in ("未知", "待公布", "待查", "", "None"):
                        r[field] = kb_val
            # 保留 LLM 的 reason 和 preparation（更个性化），不覆盖

        merged_recs.append(r)

    # Pass 2: KB 独有的竞赛（LLM 没推荐的），追加到末尾
    for r in kb_recommendations:
        n = _norm_name(r.get("name", ""))
        if n and n not in seen_norm_names:
            seen_norm_names.add(n)
            merged_recs.append(r)

    # ── 步骤 4：用知识库 JSON 补齐所有结果的缺失字段 ──
    merged_recs = [enrich_with_facts(m) for m in merged_recs]

    # ── 步骤 5：为所有结果填充模板字段（benefits/pitfalls/cat/recommend_index）──
    for r in merged_recs:
        r_name = r.get("name", "")
        form_str = str(r.get("form", ""))
        is_team = "团队" in form_str
        fee_str = str(r.get("fee", ""))
        is_free = (fee_str == "免费" or fee_str == "0")
        # 类别标签
        if not r.get("cat"):
            r["cat"] = classify_competition(r_name)
        # 推荐指数（从 match_score 推算）
        if not r.get("recommend_index"):
            score_val = r.get("match_score", 70)
            if score_val >= 90:
                r["recommend_index"] = 5
            elif score_val >= 80:
                r["recommend_index"] = 4
            elif score_val >= 70:
                r["recommend_index"] = 3
            else:
                r["recommend_index"] = 2
        # 为什么参加（只需要竞赛名称）
        if not r.get("benefits"):
            r["benefits"] = get_benefit_text(r_name)
        # 注意事项（需要 form/fee 信息）
        if not r.get("pitfalls"):
            r["pitfalls"] = get_pitfall_text(r_name, is_team, is_free, fee_str)
        # 竞赛内容描述（desc）
        if not r.get("desc"):
            r["desc"] = r.get("preparation", "")

    result["recommendations"] = merged_recs
    result["kb_matched_count"] = len(kb_recommendations)
    result["tips"] = TIPS
    result["myths"] = MYTHS

    return result
