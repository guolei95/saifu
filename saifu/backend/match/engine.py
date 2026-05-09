"""
赛赋(SaiFu) 匹配引擎 — 组织完整的匹配流程：搜索 → LLM匹配 → 常识库校验 → 交叉验证 → 自审查。
"""
from datetime import date
from services.search import generate_search_queries, search_competitions
from services.ai_client import call_deepseek_json
from services.knowledge_base import (
    enrich_with_facts, classify_competition,
    get_benefit_text, get_pitfall_text, find_related_case,
    MYTHS, TIPS,
)
from services.validation import cross_source_verify, self_review_results
from config import MIN_MATCH_SCORE, MAX_CLOSED_COMPETITIONS


def _build_knowledge_text():
    """构建嵌入 LLM prompt 的竞赛知识文本。"""
    return """## 竞赛分类（两类，简单分清）
- 🏫 学校/教育部类(蓝桥杯/数学建模/大创/互联网+/挑战杯/计算机设计大赛/信息安全/电子设计等): 由教育部、学校或学会主办,综测✅通常计入,适合保研加分
- 💼 企业类(华为ICT/百度之星/欧莱雅/宝洁/工行杯等): 由企业主办,综测⚠️可能不计入,但企业认可度高,常含offer/面试直通

## 六大好处
1.实践能力: 把课堂变真本事,证明学习能力
2.综测保研: 高层次可获保研名额,复试核心考察
3.考研复试: 协和331逆袭390凭SCI论文
4.求职简历: 仅次于实习的高含金量内容
5.企业直通: 企业赛终极大奖=预录用offer/直通终面卡
6.跨专业跳板: 用比赛证明跨界能力

## 避坑要点
- 企业类必须标注⚠️可能不计综测
- 团队赛标注👥需组队
- 收费赛标注💰金额+确认学校报销
- 大一标注门槛是否适合"""


def _build_json_template():
    """构建 LLM 输出的 JSON 模板。"""
    return {
        "type": "competition或resource",
        "name": "竞赛全称",
        "match_score": 85,
        "match_reason": "专业匹配度:XX;年级/时间合适度:XX;兴趣/目标契合度:XX",
        "cat": "🏫 学校/教育部类或💼 企业类",
        "benefits": "参加好处(结合六大好处，40字)",
        "pitfalls": "避坑提醒",
        "recommend_index": 4,
        "registration_form": "个人/团队",
        "registration_url": "信息页链接",
        "registration_deadline": "YYYY-MM-DD或未知",
        "suitable_majors": "适合专业",
        "cross_school_allowed": True,
        "participation_type": "个人/团队/均可",
        "is_free": True,
        "fee_amount": "免费或金额",
        "notes": "备注（含金量/难度）",
        "source_url": "来源URL",
        "source_type": "官方/非官方",
        "desc": "100-150字描述竞赛内容和考核形式",
        "official_url": "竞赛组委会官网地址(找不到填'未知')",
        "deadline_reference": "往年时间规律参考",
        "focus": "从[保研加分,企业直通,能力锻炼,拿奖率高]中选1-3个逗号分隔"
    }


def _build_profile_text(profile: dict) -> str:
    """将用户画像 dict 转为 LLM 可读的文本。"""
    goals_str = ", ".join(profile.get("goals", [])) if profile.get("goals") else "未指定"
    return f"""- 学校: {profile.get('school', '未知')}
- 专业: {profile.get('major', '未知')}
- 年级: {profile.get('grade', '未知')}
- 兴趣/技能: {profile.get('interests', '不限')}
- 具体技能: {profile.get('skills', profile.get('interests', '未填写'))}
- 技术方向: {profile.get('tech_directions', '未填写')}
- 参赛目标: {goals_str}
- 每周时间投入: {profile.get('time_commitment', '未填写')}
- 赛事偏好: {profile.get('preference', '不限')}
- 团队/个人偏好: {profile.get('team_preference', '不限')}
- 是否有指导老师: {profile.get('has_advisor', '未知')}
- 是否可跨校: {profile.get('can_cross_school', '未知')}
- 想避免的竞赛类型: {profile.get('avoid_types', '无')}
- 过往最高获奖: {profile.get('past_highest_award', '未填写')}
- 代表性项目: {profile.get('representative_projects', '未填写')}
- 比赛周期偏好: {profile.get('preferred_duration', '不限')}
- 比赛形式偏好: {profile.get('preferred_format', '不限')}
- 报名费预算: {profile.get('fee_budget', '不限')}
- 语言偏好: {profile.get('language_pref', '不限')}"""


def _build_results_text(results: list[dict]) -> str:
    """将搜索结果 list 转为 LLM 可读的文本。"""
    text = ""
    for i, r in enumerate(results[:25]):
        text += f"[{i+1}] {r['title']}\n    URL: {r['url']}\n    {r['content'][:250]}\n\n"
    return text


def _build_rules(today: str) -> str:
    """构建 LLM 匹配规则文本。"""
    import json
    json_tpl = json.dumps(_build_json_template(), ensure_ascii=False, indent=2)
    knowledge_text = _build_knowledge_text()

    return f"""当前日期: {today}
{knowledge_text}

JSON格式(必须严格，每条包含全部字段):
{json_tpl}

规则(必须严格遵守):
1. type: 具体竞赛填"competition"，竞赛目录/汇总清单/排行榜填"resource"
2. match_score=专业匹配(30)+年级合适(20)+兴趣匹配(30)+可操作(20)
3. recommend_index(1-5): 1=不推荐 2=勉强 3=可以报 4=推荐 5=强烈推荐
4. match_reason: 三段式"专业匹配度:XX;年级/时间合适度:XX;兴趣/目标契合度:XX"，每段15-25字
5. benefits: 结合六大好处写出具体好处
6. pitfalls: 企业类必须写⚠️可能不计综测，团队赛必须提组队
7. cat: 只填"🏫 学校/教育部类"或"💼 企业类"
8. 竞赛名中如有引号必须用「」
9. type="resource"时，notes写明这个页面列出了哪些竞赛
10. desc: 100-150字描述竞赛内容+考核形式+赛制流程
11. official_url: 组委会官网(与source_url区分)，找不到填"未知"
12. deadline_reference: 仅registration_deadline未知时填写往年规律
13. focus: 学校/教育部类→"保研加分"；企业类→"企业直通"；门槛低获奖率高→"拿奖率高"；其余→"能力锻炼"
14. 必须只输出JSON数组"""


def _normalize_name(name: str) -> str:
    """归一化竞赛名，用于去重比较。"""
    import re
    n = name.lower().strip()
    n = re.sub(r'第[一二三四五六七八九十\d]+届', '', n)
    n = re.sub(r'[「」『』""（）()" "]', '', n)
    n = re.sub(r'[\d]{4}[\s\-_]*(?:[\d]{4})?', '', n)
    n = re.sub(r'(中国赛|全球赛|省赛|国赛|校赛|区域赛|选拔赛|决赛)$', '', n)
    n = re.sub(r'[\s\-_]+', '', n)
    return n.strip()


def _val(m, *keys):
    """取字段值，支持多个备选 key。"""
    for k in keys:
        v = m.get(k)
        if v is not None and v != "":
            return v
    return None


def match_competitions(profile: dict) -> dict:
    """竞赛匹配主流程。

    Args:
        profile: 用户画像 dict（25 字段，不全的字段自动用默认值）

    Returns:
        dict: 匹配结果，包含 open/closed/resources/tips/myths
    """
    today = date.today().isoformat()

    # ── 步骤 1: 生成搜索词 ──
    queries = generate_search_queries(profile)

    # ── 步骤 2: 执行搜索 ──
    results = search_competitions(queries)

    if not results:
        return {
            "success": False,
            "error": "搜索未获取到结果，请检查网络或稍后重试",
            "open": [], "closed": [], "resources": [],
            "search_queries_used": queries,
            "tips": TIPS, "myths": MYTHS,
        }

    # ── 步骤 3: LLM 匹配（分两轮：报名中 + 已截止） ──
    profile_text = _build_profile_text(profile)
    results_text = _build_results_text(results)
    rules = _build_rules(today)
    json_tpl = _build_json_template()
    import json

    # 匹配报名中的竞赛
    open_prompt = f"""找出报名截止日期>={today}或未知、适合此学生的竞赛。

{profile_text}

## 搜索结果
{results_text}

{rules}

⚠️ 关键要求:
- type="competition"的具体竞赛：至少输出6条
- type="resource"的竞赛目录/汇总清单：有多少输出多少
- match_score < 50 不要输出
- match_reason 三段式:"专业匹配度:XX;年级/时间合适度:XX;兴趣/目标契合度:XX"
- desc 必须100-150字描述竞赛内容
- official_url 必须填组委会官网，找不到填"未知"
- focus 必须标注
- 去重：同一竞赛不重复"""

    open_list = call_deepseek_json(
        messages=[{"role": "user", "content": open_prompt}]
    )

    # 匹配已截止的竞赛
    closed_prompt = f"""找出报名已截止但非常值得关注的竞赛（供明年规划参考）。

{profile_text}

## 搜索结果
{results_text}

{rules}

⚠️ 关键要求:
- 最多输出1条已截止的竞赛（挑含金量最高的那条）
- dl末尾标注"(已截止，建议明年X月关注)"
- 必须与专业高度相关，不相关的不输出
- 没有值得关注的就不输出"""

    closed_list = call_deepseek_json(
        messages=[{"role": "user", "content": closed_prompt}]
    )

    # ── 步骤 4: 常识库修正 ──
    open_list = [enrich_with_facts(m) for m in open_list]
    closed_list = [enrich_with_facts(m) for m in closed_list]

    # ── 步骤 5: L1 交叉验证 ──
    if results:
        open_list = cross_source_verify(open_list, results)
        closed_list = cross_source_verify(closed_list, results)

    # ── 步骤 6: L2 LLM 自审查 ──
    open_list = self_review_results(open_list, results, profile)
    closed_list = self_review_results(closed_list, results, profile)

    # ── 步骤 7: 分离 resource 类型 + 过滤 + 排序 ──
    competitions = [m for m in open_list if m.get("type", "competition") != "resource"]
    resources = [m for m in open_list if m.get("type", "competition") == "resource"]

    # 过滤低分
    competitions = [m for m in competitions if int(_val(m, "match_score", "s") or 0) >= MIN_MATCH_SCORE]
    # 按匹配度排序
    competitions = sorted(competitions, key=lambda m: int(_val(m, "match_score", "s") or 0), reverse=True)

    # 去重：已截止列表中排除与报名中同名的
    open_norm = set()
    for m in competitions:
        open_norm.add(_normalize_name(_val(m, "name", "n") or ""))
    closed_list = [m for m in closed_list if _normalize_name(_val(m, "name", "n") or "") not in open_norm]
    closed_list = sorted(closed_list, key=lambda m: int(_val(m, "match_score", "s") or 0), reverse=True)[:MAX_CLOSED_COMPETITIONS]

    # ── 步骤 8: 补充分类、好处、避坑、案例 ──
    for m in competitions + closed_list:
        name = m.get("name", "")
        if not m.get("cat") or m.get("cat") not in ["🏫 学校/教育部类", "💼 企业类"]:
            m["cat"] = classify_competition(name)
        if not m.get("benefits"):
            m["benefits"] = get_benefit_text(name)
        if not m.get("pitfalls"):
            is_team = "团队" in str(m.get("participation_type", ""))
            is_free = m.get("is_free", True)
            fee = m.get("fee_amount", "")
            m["pitfalls"] = get_pitfall_text(name, is_team, is_free, fee)

    # 为 resources 补充 cat
    for m in resources:
        if not m.get("cat"):
            m["cat"] = "📋 竞赛目录"

    return {
        "success": True,
        "open": competitions,
        "closed": closed_list,
        "resources": resources,
        "search_queries_used": queries,
        "tips": TIPS,
        "myths": MYTHS,
    }
