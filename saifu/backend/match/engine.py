"""
赛赋(SaiFu) 匹配引擎 — 组织完整的匹配流程：搜索 → LLM匹配 → 常识库校验 → 交叉验证 → 自审查。
"""
from datetime import date
from services.search import generate_search_queries, search_competitions
from services.ai_client import call_deepseek_json
from services.knowledge_base import (
    enrich_with_facts, classify_competition,
    get_benefit_text, get_pitfall_text, find_related_case,
    local_match_from_kb, get_kb_competition_list,
    MYTHS, TIPS,
)
from services.validation import cross_source_verify, self_review_results
from config import MIN_MATCH_SCORE, MAX_CLOSED_COMPETITIONS


def _build_knowledge_text():
    """构建嵌入 LLM prompt 的竞赛知识文本（含84项A类竞赛列表）。"""
    kb_list = get_kb_competition_list()
    return f"""## 竞赛分类（两类，简单分清）
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
- 大一标注门槛是否适合

## ⭐ 优先知识库：教育部认可的A类学科竞赛（优先从以下竞赛中匹配）
以下竞赛为国家教育部认定的全国大学生学科竞赛，含金量高、综测加分认可度广。匹配时必须优先从其中选择：
{kb_list}

规则：上述A类竞赛中与学生画像匹配的，match_score 应+5~10分，且在 match_reason 中标注"[A类赛事]"。非A类竞赛的 match_score 正常计算不额外加分。"""


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
- 空闲月份: {profile.get('available_months', '未填写')}
- 寒暑假可备赛: {profile.get('summer_winter', '未填写')}
- 常用工具: {profile.get('tools', '未填写')}
- 其他技能说明: {profile.get('other_skills', '无')}
- 赛事偏好: {profile.get('preference', '不限')}
- 团队/个人偏好: {profile.get('team_preference', '不限')}
- 是否有指导老师: {profile.get('has_advisor', '未知')}
- 是否可跨校: {profile.get('can_cross_school', '未知')}
- 想避免的竞赛类型: {profile.get('avoid_types', '无')}
- 过往最高获奖: {profile.get('past_highest_award', '未填写')}
- 代表性项目: {profile.get('representative_projects', '未填写')}
- 作品集链接: {profile.get('portfolio_link', '无')}
- 比赛周期偏好: {profile.get('preferred_duration', '不限')}
- 比赛形式偏好: {profile.get('preferred_format', '不限')}
- 报名费预算: {profile.get('fee_budget', '不限')}
- 语言偏好: {profile.get('language_pref', '不限')}
- 最低接受获奖: {profile.get('min_award', '不限')}
- 理想目标: {profile.get('ideal_goal', '未填写')}
- 策略偏好: {profile.get('strategy', '未填写')}"""


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
4. match_reason: 三段式"专业匹配度:XX;年级/时间合适度:XX;兴趣/目标契合度:XX"，每段15-25字。禁止使用"待确认""未知""不明确"等模糊词——必须根据学生画像和竞赛常识给出具体评价，不确定时做合理推断即可
4a. 年级/时间合适度评估框架(必须据此做出具体判断，不准说"待确认"):
   - 学生年级来自画像(大一~研三)，竞赛通常面向本科/研究生两个层次
   - 大一/大二: 适合大多数本科竞赛→写"大二可参加，门槛适中"或"适合低年级积累经验"
   - 大三/大四: 有专业知识积累→写"大三有基础，正是黄金期"或"大四备赛经验足"
   - 研一~研三: 适合研究生组别→写"研究生组别匹配"或"科研能力匹配"
   - 时间投入评估：少于5h/周→适合短期冲刺型；5-15h/周→适合大多数竞赛；15h+/周→适合长期备赛
   - 结合学生画像中的"每周时间投入"和"空闲月份"，与竞赛周期做匹配判断
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
    """归一化竞赛名，用于去重比较 — 激进模式，宁可多去不少去。"""
    import re
    n = name.lower().strip()
    # 删除括号及其中内容：(NECCS)、（全国赛）、[简称] 等
    n = re.sub(r'[（(][^）)]*[）)]', '', n)
    n = re.sub(r'[【\[]([^】\]])*[】\]]', '', n)
    # 删除届数
    n = re.sub(r'第[一二三四五六七八九十\d]+届', '', n)
    # 删除年份+年：2026年、2025-2026年度
    n = re.sub(r'\d{4}[-\s]*\d{0,4}\s*[年年度]', '', n)
    # 删除所有标点、括号、特殊符号
    n = re.sub(r'[]「」『』""''""（）()[【】《》、，。；：！？·|/@#$%^&*+=~` _-]+', '', n)
    # 删除常见后缀
    n = re.sub(r'(中国赛|全球赛|全国赛|省赛|国赛|校赛|区域赛|选拔赛|初赛|复赛|决赛|总赛)$', '', n)
    # 删除常见前缀
    n = re.sub(r'^(中国|全国|全球|国际)', '', n)
    # 如果归一化后太短（<2字符），保留原名（避免不同竞赛被错误合并）
    if len(n.strip()) < 2:
        return name.lower().strip()
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

    # ── 步骤 0: 本地知识库优先匹配（A类竞赛，不联网不用LLM）──
    kb_matches = local_match_from_kb(profile)
    kb_matches = [enrich_with_facts(m) for m in kb_matches]

    # ── 步骤 1: 生成搜索词 ──
    queries = generate_search_queries(profile)

    # ── 步骤 2: 执行搜索 ──
    results = search_competitions(queries)

    if not results:
        # 联网搜索失败但有本地知识库结果，返回知识库结果
        if kb_matches:
            for m in kb_matches:
                name = m.get("name", "")
                if not m.get("benefits"):
                    m["benefits"] = get_benefit_text(name)
                if not m.get("pitfalls"):
                    is_team = "团队" in str(m.get("participation_type", ""))
                    m["pitfalls"] = get_pitfall_text(name, is_team, m.get("is_free", True), m.get("fee_amount", ""))
            return {
                "success": True,
                "open": kb_matches,
                "closed": [],
                "resources": [],
                "search_queries_used": queries,
                "kb_matches_count": len(kb_matches),
                "note": "联网搜索暂时不可用，以下为本地A类竞赛知识库匹配结果",
                "tips": TIPS, "myths": MYTHS,
            }
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

    # ── 去重：open 列表内部去重 ──
    def _dedup(items: list[dict]) -> list[dict]:
        """双重去重：先按归一化名称，再按 URL（registration_url + official_url）。"""
        seen_names = set()
        seen_urls = set()
        result = []
        for m in items:
            norm = _normalize_name(_val(m, "name", "n") or "")
            # 按名称去重
            if norm and norm in seen_names:
                continue
            # 按 URL 去重（非"未知"的 URL 才参与比较）
            urls = [
                (m.get("registration_url") or "").strip().rstrip("/"),
                (m.get("official_url") or "").strip().rstrip("/"),
                (m.get("source_url") or "").strip().rstrip("/"),
            ]
            has_url_overlap = False
            for u in urls:
                if u and u not in ("未知", "无", "", "未找到", "暂无"):
                    if u in seen_urls:
                        has_url_overlap = True
                        break
            if has_url_overlap:
                continue
            # 记录
            if norm:
                seen_names.add(norm)
            for u in urls:
                if u and u not in ("未知", "无", "", "未找到", "暂无"):
                    seen_urls.add(u)
            result.append(m)
        return result

    competitions = _dedup(competitions)

    # 去重：已截止列表中排除与报名中同名的
    open_norm = set()
    open_urls = set()
    for m in competitions:
        open_norm.add(_normalize_name(_val(m, "name", "n") or ""))
        for key in ("registration_url", "official_url", "source_url"):
            u = (m.get(key) or "").strip().rstrip("/")
            if u and u not in ("未知", "无", "", "未找到", "暂无"):
                open_urls.add(u)
    def _in_open(m):
        if _normalize_name(_val(m, "name", "n") or "") in open_norm:
            return True
        for key in ("registration_url", "official_url", "source_url"):
            u = (m.get(key) or "").strip().rstrip("/")
            if u and u in open_urls:
                return True
        return False
    closed_list = [m for m in closed_list if not _in_open(m)]
    closed_list = sorted(closed_list, key=lambda m: int(_val(m, "match_score", "s") or 0), reverse=True)[:MAX_CLOSED_COMPETITIONS]

    # 去重：resources 列表内部去重
    resources = _dedup(resources)

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

    # ── 步骤 9: 合并本地知识库结果（优先）+ LLM 结果 ──
    if kb_matches:
        # 收集已有结果的归一化名称和 URL
        existing_norms = set()
        existing_urls = set()
        for m in competitions:
            existing_norms.add(_normalize_name(_val(m, "name", "n") or ""))
            for key in ("registration_url", "official_url", "source_url"):
                u = (m.get(key) or "").strip().rstrip("/")
                if u and u not in ("未知", "无", "", "未找到", "暂无"):
                    existing_urls.add(u)

        # 去重：KB 结果中排除与 LLM 结果重复的
        unique_kb = []
        for m in kb_matches:
            norm = _normalize_name(_val(m, "name", "n") or "")
            kb_url = (m.get("official_url") or "").strip().rstrip("/")
            if norm and norm in existing_norms:
                continue
            if kb_url and kb_url in existing_urls:
                continue
            # 补充 benefits/pitfalls（KB 结果这些字段为空）
            name = m.get("name", "")
            if not m.get("benefits"):
                m["benefits"] = get_benefit_text(name)
            if not m.get("pitfalls"):
                is_team = "团队" in str(m.get("participation_type", ""))
                is_free = m.get("is_free", True)
                fee = m.get("fee_amount", "")
                m["pitfalls"] = get_pitfall_text(name, is_team, is_free, fee)
            unique_kb.append(m)

        # KB 结果追加到前面
        competitions = unique_kb + competitions

        # 整体重新按 match_score 排序（KB 结果分数通常 50-95，LLM 结果分数通常也在这个范围）
        competitions = sorted(
            competitions,
            key=lambda m: int(_val(m, "match_score", "s") or 0),
            reverse=True
        )

    return {
        "success": True,
        "open": competitions,
        "closed": closed_list,
        "resources": resources,
        "search_queries_used": queries,
        "kb_matches_count": len(kb_matches) if kb_matches else 0,
        "tips": TIPS,
        "myths": MYTHS,
    }


def generate_personal_summary(profile: dict, top_matches: list) -> dict:
    """基于用户画像和匹配结果，生成个性化总结（备赛建议、风险提示、总体评估）。

    Args:
        profile: 用户画像 dict
        top_matches: 前 N 个匹配竞赛列表

    Returns:
        {"advice": {...}, "risks": [...], "summary": "..."}
    """
    profile_text = _build_profile_text(profile)

    # 构建前5个匹配竞赛摘要
    match_text = ""
    for i, m in enumerate(top_matches[:5]):
        m_name = m.get("name", "未知竞赛")
        m_score = m.get("match_score", "?")
        m_reason = m.get("match_reason", "")
        match_text += f"{i+1}. {m_name} (匹配度:{m_score}%)\n"
        match_text += f"   理由: {m_reason}\n\n"
    if not match_text:
        match_text = "暂未匹配到高适配竞赛"

    prompt = f"""基于以下用户画像和竞赛匹配结果，生成一份个性化的备赛总结。

{profile_text}

## 匹配到的竞赛
{match_text}

请返回严格的 JSON（不要其他文字）：
{{
  "advice": {{
    "time_plan": "基于用户空闲月份和年级，给出具体的时间规划建议（100-150字）",
    "skill_improvement": "基于用户当前技能，指出需要补强的方向（100-150字）",
    "team_strategy": "基于用户情况和匹配竞赛特点，给出组队建议（100-150字）"
  }},
  "risks": [
    {{"type": "风险类型（如：时间冲突、技能缺口、报名门槛）", "detail": "具体描述", "solution": "应对方案"}}
  ],
  "summary": "一段话总结该用户的竞赛适配方向和整体建议（150字内）"
}}

要求：
- risks 至少1条，最多3条，要结合用户实际画像
- 建议要具体实用，不能泛泛而谈
- summary 要结合用户的专业和匹配到的竞赛来写
- 如果用户某方面信息缺失（如未填学校），不要编造，用"建议补充XX信息"代替"""

    try:
        result = call_deepseek_json(
            messages=[{"role": "user", "content": prompt}]
        )
        return result
    except Exception:
        # LLM 调用失败时返回默认值
        return {
            "advice": {
                "time_plan": "建议根据竞赛报名时间提前3-6个月规划，合理分配每周学习时间。",
                "skill_improvement": "建议针对目标竞赛的要求，针对性地提升相关技能。",
                "team_strategy": "建议寻找优势互补的队友，根据竞赛要求提前组建团队。",
            },
            "risks": [
                {"type": "信息缺失", "detail": "部分画像信息不完整，可能影响匹配精度", "solution": "建议补充完整的个人信息以获得更精准的推荐"}
            ],
            "summary": "基于您的画像，系统已为您匹配到合适的竞赛。建议结合个人时间安排和兴趣方向，优先选择匹配度高的竞赛参与。",
        }
