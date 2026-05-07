"""
竞赛常识库 — 硬编码的竞赛数据和校验函数。
数据来源：0503-match_competitions.py，经整理后直接复用。
"""

# ═══════════════════════════════════════════════════════════
# 1. 竞赛分类速查（两类：学校/教育部类 vs 企业类）
# ═══════════════════════════════════════════════════════════
COMPETITION_CATEGORIES = {
    "🏫 学校/教育部类": {
        "keywords": [
            "大创", "互联网+", "挑战杯", "创新创业", "创新大赛", "三创赛",
            "数学建模", "蓝桥杯", "计算机设计", "电子设计", "机械创新", "化工设计",
            "英语竞赛", "力学竞赛", "结构设计", "数字建筑",
            "信息安全", "网络安全", "软件创新", "物联网",
            "服创", "服务外包", "统计建模", "人工智能",
            "三下乡", "志愿服务", "社会实践", "数据要素",
        ],
        "主办方": "政府/教育部/学校/学会",
        "综测": "✅ 通常计入综测",
        "说明": "由教育部门、学校或学会主办，综测加分通常认可",
    },
    "💼 企业类": {
        "keywords": [
            "华为", "欧莱雅", "宝洁", "联合利华", "工行杯",
            "百度之星", "腾讯", "阿里", "京东", "商赛",
            "营销大赛", "商业精英", "企业赛", "金融科技",
            "品牌大赛", "创新挑战赛",
        ],
        "主办方": "企业",
        "综测": "⚠️ 部分学校不计入，先确认本校政策",
        "说明": "企业主办，综测不一定认可但企业认可度高，常含offer/面试直通",
    },
}

# ═══════════════════════════════════════════════════════════
# 2. 六大好处模板
# ═══════════════════════════════════════════════════════════
BENEFIT_TEMPLATES = {
    "实践能力": "把课堂知识变成真本事，赛中遇到的问题逼你自学解决——这是企业最看重的「学习能力」",
    "综测保研": "高层次竞赛（如互联网+国奖）可直接获保研名额。保外校面试核心考察科研和比赛经历",
    "考研复试": "科研和比赛经历在复试中权重极高——协和医院331分考生凭SCI逆袭390分对手",
    "求职简历": "比赛经历是仅次于实习的高含金量简历内容，既能证明硬实力又能证明软实力",
    "企业直通": "很多企业赛的终极大奖是预录用offer或直通终面卡——不用投简历直接进终面",
    "跨专业跳板": "想转行？用比赛证明你有跨界能力——比「我感兴趣」有说服力100倍",
}

# ═══════════════════════════════════════════════════════════
# 3. 六大避坑规则
# ═══════════════════════════════════════════════════════════
PITFALL_RULES = {
    "企业赛": "⚠️ 部分企业赛不计入综测加分！选赛前务必确认你学校的综测规则",
    "需要导师": "⚠️ 此竞赛需要指导老师，大一的同学建议提前联系专业课老师或辅导员",
    "团队赛": "👥 需要组队参赛，建议找专业互补的队友（技术+文案+表达各一人）",
    "高难度": "⚠️ 难度较高，建议有一定基础后再报，或者先跟学长学姐打下手积累经验",
    "时间冲突": "⚠️ 注意比赛时间是否与期末考试冲突，合理安排",
    "费用": "⚠️ 此竞赛有报名费，确认学校是否报销",
}

# ═══════════════════════════════════════════════════════════
# 4. 四大焦点标签
# ═══════════════════════════════════════════════════════════
FOCUS_LABELS = {
    "保研加分": "🎓 该竞赛在多数高校计入综测加分，高层次获奖可直接获保研名额或面试加分",
    "企业直通": "💼 企业主办或冠名，终极大奖常含实习/预录用offer/直通终面卡，企业认可度高",
    "能力锻炼": "💪 侧重实践能力成长，适合积累项目经验，丰富简历，提升综合竞争力",
    "拿奖率高": "🏆 门槛相对较低、获奖比例较高，适合首次参赛建立信心和履历",
}

# ═══════════════════════════════════════════════════════════
# 5. 竞赛常识库（9个热门竞赛的权威信息）
# ═══════════════════════════════════════════════════════════
COMPETITION_FACTS = {
    "蓝桥杯": {
        "official_url": "https://dasai.lanqiao.cn",
        "报名窗口": "前一年10月—12月（学校统一报名）；补报至当年3月",
        "省赛时间": "当年4月（通常中旬）",
        "国赛时间": "当年5月底—6月初",
        "报名费": "300元/人",
        "组别": "研究生组/大学A组(985/211)/B组(普通本科)/C组(专科)",
        "参赛形式": "个人",
        "备注": "⚠️ 主要报名期是10-12月！3月仅是个人补报最终截止日",
    },
    "华为ICT大赛": {
        "official_url": "https://e.huawei.com/cn/talent/ict-academy",
        "报名窗口": "每年9月左右启动",
        "赛制": "实践赛(网络/云/基础软件/AI四赛道)+创新赛+编程赛+挑战赛",
        "报名费": "免费",
        "参赛形式": "团队(3人+1指导老师)",
    },
    "数学建模": {
        "official_url": "https://www.mcm.edu.cn",
        "全称": "高教社杯全国大学生数学建模竞赛(CUMCM)",
        "比赛时间": "每年9月上旬（连续72小时）",
        "报名时间": "赛前2-4周（通常8月）",
        "报名费": "约200-300元/队",
        "参赛形式": "团队(3人)",
    },
    "计算机设计大赛": {
        "official_url": "https://jsjds.blcu.edu.cn",
        "全称": "中国大学生计算机设计大赛(4C大赛)",
        "时间线": "校赛3-4月 → 省赛5月 → 国赛7-8月",
        "报名费": "免费",
        "参赛形式": "团队(2-5人)",
        "大类": "软件应用与开发/物联网/AI应用/大数据/数媒等11类",
    },
    "服务外包": {
        "official_url": "https://www.fwwb.org.cn",
        "全称": "中国大学生服务外包创新创业大赛",
        "报名窗口": "每年2-3月",
        "参赛形式": "团队",
        "报名费": "免费",
        "赛道": "A类企业命题+B类创业实践+C类OPC创客+D类腾讯开悟AI",
    },
    "挑战杯": {
        "official_url": "https://www.tiaozhanbei.net",
        "全称": "挑战杯全国大学生课外学术科技作品竞赛/创业计划竞赛",
        "时间线": "校赛秋季→省赛次年春→国赛次年夏（两年一届）",
        "参赛形式": "团队(需要指导老师)",
        "报名费": "免费",
        "备注": "⚠️ 需指导老师，大一建议先跟学长学姐项目积累经验",
    },
    "互联网+": {
        "official_url": "https://cy.ncss.cn",
        "全称": "中国国际大学生创新大赛(原互联网+)",
        "时间线": "校赛4-5月 → 省赛6-8月 → 国赛10月",
        "参赛形式": "团队(需要指导老师)",
        "报名费": "免费",
    },
    "大创": {
        "official_url": "各校教务处官网",
        "全称": "大学生创新创业训练计划项目",
        "时间线": "各校自行安排（通常每年3-5月申报）",
        "参赛形式": "团队(需要指导老师)",
    },
    "信息安全竞赛": {
        "official_url": "https://www.ciscn.cn",
        "全称": "全国大学生信息安全竞赛(CISCN)",
        "时间线": "线上初赛5月 → 分区赛6月 → 全国总决赛7-8月",
        "赛道": "作品赛+创新实践能力赛(CTF)",
        "参赛形式": "团队",
        "报名费": "免费",
    },
}

# ═══════════════════════════════════════════════════════════
# 6. 10个真实案例
# ═══════════════════════════════════════════════════════════
REAL_CASES = [
    {"id": 1, "title": "双非大一进前9%决赛",
     "match": ["挑战杯", "互联网+", "创新创业"],
     "story": "三个双非大一学生，在各种名校队伍中进入前9%决赛",
     "lesson": "学校牌子不是决定因素，关键是你愿不愿意做"},
    {"id": 2, "title": "没得奖也能写进简历",
     "match": ["欧莱雅", "宝洁", "联合利华", "商赛", "企业赛"],
     "story": "参加联合利华商赛没得奖，但完整走完全流程，简历写了调研和策划过程",
     "lesson": "面试官看的是你做了什么、怎么做的，不只是奖项本身"},
    {"id": 3, "title": "企业赛直通offer",
     "match": ["华为", "民生银行", "金融科技", "企业赛"],
     "story": "参加民生银行金融科技挑战赛，特等奖直接获预录用offer",
     "lesson": "企业赛的最大价值不是奖金，而是绕过了简历筛选直接见面试官"},
    {"id": 4, "title": "跨专业入职华为",
     "match": ["编程", "Python", "数学建模", "蓝桥杯", "软件"],
     "story": "机械专业同学参加编程比赛，凭借比赛项目经历跨专业入职华为做程序员",
     "lesson": "比赛是跨专业求职的第一步——用比赛证明你有这个能力"},
    {"id": 5, "title": "成绩不好靠比赛逆袭",
     "match": ["华为", "企业赛", "销售", "营销"],
     "story": "大三之前成绩一般还挂过科，靠华为销售挑战赛拿东北区金奖直通终面入职华为",
     "lesson": "成绩不好不代表没路，用比赛证明自己"},
    {"id": 6, "title": "大创一鱼多吃",
     "match": ["大创", "挑战杯", "互联网+"],
     "story": "一个大创项目改题目参加挑战杯，两个比赛都得奖",
     "lesson": "同一份努力，换个包装可以收获两份"},
    {"id": 7, "title": "数学建模找外援",
     "match": ["数学建模", "数模", "美赛"],
     "story": "拿到题目先找博士生聊3小时请教经验，比自己摸索3天还有用",
     "lesson": "大学竞赛不是闭卷考试，找到有经验的人请教比埋头苦干高效得多"},
    {"id": 8, "title": "商赛进全国前200",
     "match": ["欧莱雅", "商赛", "营销", "品牌"],
     "story": "欧莱雅Brandstorm每年2万+队伍，进前200本身就是简历亮点，凭此找到大厂实习",
     "lesson": "商赛即使没拿大奖，进到一定轮次就是简历亮点"},
    {"id": 9, "title": "指导老师层级决定奖项",
     "match": ["大创", "挑战杯", "互联网+"],
     "story": "唯一做出实物并成功飞行的项目只拿校一等奖，室友没做出来拿国二——指导老师是院长",
     "lesson": "选指导老师尽量找职称高的"},
    {"id": 10, "title": "考研复试331逆袭390",
     "match": ["学术", "科研", "论文"],
     "story": "北京协和医院复试，331分考生凭SCI论文经历逆袭390分对手",
     "lesson": "科研和比赛经历在复试中权重极高，能弥补初试差距"},
]

# ═══════════════════════════════════════════════════════════
# 7. 三大误区 + 小贴士
# ═══════════════════════════════════════════════════════════
MYTHS = [
    "❌ 「只有大佬才能参赛」→ ✅ 大佬都是从小白成长的，双非大一也能进前9%决赛",
    "❌ 「等学了专业课再参加」→ ✅ 不是学会了再比，是在比赛中学会",
    "❌ 「不得奖就白参加了」→ ✅ 认真做了就能写进简历，面试官看过程不看奖状",
]

TIPS = [
    "💡 报名前务必去官网核实截止日期和参赛要求，网络信息可能有误",
    "💡 同类型比赛建议只报 2-3 个，精力分散反而难出成绩",
    "💡 大一优先报低门槛的积累经验 → 大二大三再冲高含金量赛事",
]


# ═══════════════════════════════════════════════════════════
# 函数部分
# ═══════════════════════════════════════════════════════════

def classify_competition(name: str) -> str:
    """根据竞赛名称判断分类（两类：学校/教育部类 vs 企业类）。"""
    name_lower = name.lower()
    for cat, info in COMPETITION_CATEGORIES.items():
        for kw in info["keywords"]:
            if kw.lower() in name_lower:
                return cat
    if "大赛" in name or "竞赛" in name or "杯" in name:
        return "🏫 学校/教育部类"
    return "🏫 学校/教育部类"


def get_benefit_text(name: str, benefits_text: str = "") -> str:
    """根据竞赛类型生成好处说明。"""
    cat = classify_competition(name)
    parts = []

    if "企业类" in cat:
        parts.append("💼 求职直通：" + BENEFIT_TEMPLATES["企业直通"])
    else:
        parts.append("🎓 综测保研：" + BENEFIT_TEMPLATES["综测保研"][:50] +
                     "。" + BENEFIT_TEMPLATES["考研复试"][:40])
    parts.append("📋 专业技能：" + BENEFIT_TEMPLATES["实践能力"])

    if benefits_text:
        parts.append(benefits_text)
    return "\n│ ".join(parts)


def get_pitfall_text(name: str, is_team: bool, is_free: bool, fee: str) -> str:
    """生成避坑提醒。"""
    cat = classify_competition(name)
    warnings = []

    if "企业类" in cat:
        warnings.append(PITFALL_RULES["企业赛"])
    if is_team:
        warnings.append(PITFALL_RULES["团队赛"])
    if not is_free or (fee and fee not in ["免费", "未知"]):
        warnings.append(PITFALL_RULES["费用"])
    if "挑战杯" in name or "大创" in name or "互联网" in name:
        warnings.append(PITFALL_RULES["需要导师"])

    return "\n│ ⚠️ ".join(warnings) if warnings else "暂无明显坑点，放心报名"


def find_fact_match(name: str) -> dict | None:
    """在 COMPETITION_FACTS 中模糊匹配竞赛名。"""
    name_lower = name.lower()
    best_key = None
    best_len = 0
    for key in COMPETITION_FACTS:
        if key.lower() in name_lower:
            if len(key) > best_len:
                best_len = len(key)
                best_key = key
    if best_key:
        return COMPETITION_FACTS[best_key]
    return None


def enrich_with_facts(competition: dict) -> dict:
    """用内置常识库修正/补充竞赛信息。

    对于 COMPETITION_FACTS 中存在的竞赛：
    - official_url: 用已知正确值覆盖
    - deadline_reference: 补全时间规律
    - notes: 追加备注
    - fee_amount / participation_type: 常识库补充
    """
    facts = find_fact_match(competition.get("name", ""))
    if not facts:
        return competition

    competition["_verified_by_facts"] = True

    # 官网修正
    known_url = facts.get("official_url", "").rstrip("/")
    comp_url = competition.get("official_url", "").rstrip("/")
    if known_url and known_url != comp_url:
        old_url = competition.get("official_url", "")
        if old_url and old_url not in ("未知", "无", ""):
            competition["_url_was"] = old_url
            competition["_url_fixed"] = True
        competition["official_url"] = known_url
    elif known_url and known_url == comp_url:
        competition["_url_verified"] = True

    # 时间规律补充
    dl_ref_parts = []
    if "报名窗口" in facts:
        dl_ref_parts.append(f"报名: {facts['报名窗口']}")
    if "比赛时间" in facts:
        dl_ref_parts.append(f"比赛: {facts['比赛时间']}")
    if "省赛时间" in facts:
        dl_ref_parts.append(f"省赛: {facts['省赛时间']}")
    if "时间线" in facts:
        dl_ref_parts.append(facts['时间线'])
    if dl_ref_parts:
        existing = competition.get("deadline_reference", "")
        if existing and existing not in ("未知", "无", ""):
            competition["deadline_reference"] = f"{existing} | 📌 {', '.join(dl_ref_parts)}"
        else:
            competition["deadline_reference"] = ", ".join(dl_ref_parts)

    # 备注追加
    if "备注" in facts:
        existing_notes = competition.get("notes", "")
        fact_note = facts["备注"]
        if fact_note and fact_note not in (existing_notes or ""):
            competition["notes"] = f"{existing_notes} | 📌 {fact_note}".strip(" |")

    # 费用 / 参赛形式补充
    if "报名费" in facts and not competition.get("fee_amount"):
        competition["fee_amount"] = facts["报名费"]
        competition["is_free"] = (facts["报名费"] == "免费")
    if "参赛形式" in facts and not competition.get("participation_type"):
        comp_type = facts["参赛形式"]
        if "团队" in comp_type:
            competition["participation_type"] = "团队"
            competition["registration_form"] = "团队"
        elif "个人" in comp_type:
            competition["participation_type"] = "个人"
            competition["registration_form"] = "个人"

    return competition


def check_date_sanity(competition: dict, today_str: str) -> list[str]:
    """检查日期是否与常识模式冲突，返回警告列表。"""
    warnings = []
    facts = find_fact_match(competition.get("name", ""))
    if not facts:
        return warnings

    dl = competition.get("registration_deadline", "")
    if not dl or dl == "未知":
        return warnings

    if "蓝桥杯" in competition.get("name", ""):
        if dl.startswith("2026-04") or dl.startswith("2026-05"):
            warnings.append("⚠️ 蓝桥杯省赛通常在4月，此截止日期可能是补报/国赛信息，请确认")
    if "数学建模" in competition.get("name", "") or "数模" in competition.get("name", ""):
        if dl > "2026-10":
            warnings.append("⚠️ 国赛通常在9月举行，此日期可能不是国赛报名截止日，请到 mcm.edu.cn 确认")

    return warnings


def find_related_case(name: str) -> dict | None:
    """匹配相关案例。"""
    best = None
    best_score = 0
    for case in REAL_CASES:
        score = 0
        for kw in case["match"]:
            if kw.lower() in name.lower():
                score += 1
        if score > best_score:
            best_score = score
            best = case
    return best if best_score > 0 else None
