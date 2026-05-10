"""
竞赛常识库 — 84 项教育部 A 类竞赛 + 分类/好处/避坑/案例/标签。
竞赛数据从 84项A类竞赛知识库.json 加载；静态内容（好处/避坑/案例等）保留在此文件。
"""

import json
import os
import re as _re

# ═══════════════════════════════════════════════════════════
# 0. 加载 84 项 A 类竞赛数据
# ═══════════════════════════════════════════════════════════
_KB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "84项A类竞赛知识库.json")
_KB_PATH = os.path.normpath(os.path.abspath(_KB_PATH))

try:
    with open(_KB_PATH, "r", encoding="utf-8") as f:
        _kb_raw = json.load(f)
    # 转为 dict，key 为竞赛名称（用于模糊匹配）
    COMPETITION_FACTS: dict[str, dict] = {}
    for entry in _kb_raw:
        names = [entry.get("name", "")]
        alt = entry.get("alt_name", "")
        if alt:
            for a in alt.split(";"):
                a = a.strip()
                if a:
                    names.append(a)
        for n in names:
            if n:
                COMPETITION_FACTS[n] = entry
    print(f"[knowledge_base] 已加载 {len(_kb_raw)} 条 A 类竞赛数据")
except Exception as e:
    print(f"[knowledge_base] 加载 JSON 失败: {e}，降级到内置 9 条")
    # 降级：内置备用
    COMPETITION_FACTS = {}  # 下面会重新构建

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
# 5. 竞赛常识库（从 JSON 加载 84 条，降级时用内置 9 条）
# ═══════════════════════════════════════════════════════════
if not COMPETITION_FACTS:
    # 降级内置（仅 JSON 加载失败时使用）
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
    """在 COMPETITION_FACTS 中模糊匹配竞赛名（双向包含 + 归一化回退）。"""
    name_lower = name.lower()
    best_key = None
    best_len = 0

    # 第一轮：双向包含（输入包含键名，或键名包含输入）
    for key in COMPETITION_FACTS:
        kl = key.lower()
        if kl in name_lower or name_lower in kl:
            if len(kl) > best_len:
                best_len = len(kl)
                best_key = key

    # 第二轮：字母数字归一化匹配（回退）
    if not best_key:
        def _norm(s):
            return _re.sub(r'[^a-z0-9一-鿿]', '', s.lower())
        nn = _norm(name_lower)
        for key in COMPETITION_FACTS:
            nk = _norm(key)
            if nk == nn or (len(nk) >= 4 and nk in nn) or (len(nn) >= 4 and nn in nk):
                best_key = key
                break

    if best_key:
        return COMPETITION_FACTS[best_key]
    return None


def enrich_with_facts(competition: dict) -> dict:
    """用内置常识库修正/补充竞赛信息。

    从 84 项 A 类竞赛 JSON 读取：url, timing, format, work_type, requirements, fee, form, note, track 等。
    """
    facts = find_fact_match(competition.get("name", ""))
    if not facts:
        # 尝试用全称匹配
        alt = competition.get("full_name") or competition.get("alt_name", "")
        if alt:
            facts = find_fact_match(alt)
    if not facts:
        return competition

    competition["_verified_by_facts"] = True

    # --- 官网修正 ---
    known_url = (facts.get("url") or facts.get("official_url") or "").rstrip("/")
    comp_url = (competition.get("official_url") or "").rstrip("/")
    if known_url and known_url != comp_url:
        old_url = competition.get("official_url", "")
        if old_url and old_url not in ("未知", "无", ""):
            competition["_url_was"] = old_url
            competition["_url_fixed"] = True
        competition["official_url"] = known_url
    elif known_url and known_url == comp_url:
        competition["_url_verified"] = True

    # --- 时间规律补充 ---
    timing = facts.get("timing", "")
    if timing:
        existing_dl = competition.get("deadline_reference", "")
        if existing_dl and existing_dl not in ("未知", "无", ""):
            competition["deadline_reference"] = f"{existing_dl} | 📌 {timing}"
        else:
            competition["deadline_reference"] = timing

    # --- 费用补充 ---
    fee = facts.get("fee", "")
    if fee and not competition.get("fee_amount"):
        competition["fee_amount"] = fee
        competition["is_free"] = (fee == "免费")

    # --- 参赛形式补充 ---
    form = facts.get("form", "")
    if form and not competition.get("participation_type"):
        if "团队" in form:
            competition["participation_type"] = "团队"
            competition["registration_form"] = "团队"
        elif "个人" in form:
            competition["participation_type"] = "个人"
            competition["registration_form"] = "个人"

    # --- 备注/备注补充 ---
    note = facts.get("note", "")
    if note:
        existing_notes = competition.get("notes", "")
        if note not in (existing_notes or ""):
            competition["notes"] = f"{existing_notes} | 📌 {note}".strip(" |")

    # --- 赛道/组别补充到 desc ---
    extra_desc_parts = []
    for field, label in [("track", "赛道"), ("group", "组别"), ("category", "类别")]:
        val = facts.get(field, "")
        if val and val not in competition.get("desc", ""):
            extra_desc_parts.append(f"{label}: {val}")
    if extra_desc_parts:
        existing_desc = competition.get("desc", "")
        competition["desc"] = f"{existing_desc} | {'; '.join(extra_desc_parts)}".strip(" |")

    # --- 参赛要求补充 ---
    req = facts.get("requirements", "")
    if req and not competition.get("requirements_text"):
        competition["requirements_text"] = req

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


# ═══════════════════════════════════════════════════════════
# 本地优先匹配 — 从 84 项 A 类知识库中匹配（不联网，不用 LLM）
# ═══════════════════════════════════════════════════════════

def _extract_profile_keywords(profile: dict) -> set[str]:
    """从学生画像提取有意义的搜索关键词（已分词、小写）。"""
    keywords: set[str] = set()

    for field in ["major", "interests", "skills", "other_skills"]:
        text = str(profile.get(field, "")).strip()
        if text:
            for word in _re.split(r'[,，、\s/()（）]+', text):
                word = word.strip().lower()
                if len(word) >= 2:
                    keywords.add(word)

    for d in profile.get("tech_directions", []) or []:
        d = str(d).strip().lower()
        if len(d) >= 2:
            keywords.add(d)

    for g in profile.get("goals", []) or []:
        g = str(g).strip()
        # 目标 → 扩展关键词
        goal_words = {
            "保研加分": ["保研", "综测", "加分"],
            "求职直通": ["企业", "offer", "直通", "实习"],
            "能力锻炼": ["实践", "实训", "项目"],
            "拿奖": ["获奖", "获奖率"],
        }
        keywords.update(goal_words.get(g, [g]))

    # 移除太短或太泛的词
    stop_words = {"的", "了", "是", "在", "和", "与", "或", "我", "你", "他", "她",
                  "有", "不", "都", "要", "也", "就", "能", "会", "可以", "这个",
                  "那个", "一个", "什么", "怎么", "哪些", "他们", "我们"}
    keywords -= stop_words

    return keywords


def _kb_entry_to_result(entry: dict, score: int, hit_count: int) -> dict:
    """将知识库条目转为匹配结果 dict（与 LLM 输出格式兼容）。"""
    name = entry.get("name", "")
    fee = entry.get("fee", "")
    form_val = entry.get("form", "")
    is_team = "团队" in str(form_val)
    url = entry.get("url", "")

    # 描述：格式说明（截断到 150 字）+ 作品类型摘要
    fmt = str(entry.get("format", ""))
    wt = str(entry.get("work_type", ""))
    desc_base = fmt if len(fmt) > 20 else wt
    desc = desc_base[:150]

    # 推荐指数
    if score >= 88:
        rec_idx = 5
    elif score >= 80:
        rec_idx = 4
    elif score >= 70:
        rec_idx = 3
    else:
        rec_idx = 2

    return {
        "type": "competition",
        "name": name,
        "match_score": score,
        "match_reason": (
            f"专业匹配度:关键词命中{hit_count}个A类竞赛;"
            "年级/时间合适度:待确认;兴趣/目标契合度:A类优先推荐"
        ),
        "cat": "🏫 学校/教育部类",
        "benefits": "",
        "pitfalls": "",
        "recommend_index": rec_idx,
        "registration_form": "团队" if is_team else "个人",
        "registration_url": url,
        "official_url": url,
        "registration_deadline": "未知",
        "suitable_majors": "",
        "cross_school_allowed": True,
        "participation_type": "团队" if is_team else "个人",
        "is_free": (fee == "免费" or fee == ""),
        "fee_amount": fee if fee else "未知",
        "notes": entry.get("note", ""),
        "source_url": url,
        "source_type": "官方",
        "desc": desc,
        "deadline_reference": entry.get("timing", ""),
        "focus": "保研加分,拿奖率高",
        "_from_kb": True,
        "_kb_id": entry.get("id"),
    }


def local_match_from_kb(profile: dict, top_n: int = 15) -> list[dict]:
    """从 84 项 A 类竞赛知识库中本地匹配（不联网，不用 LLM）。

    匹配策略：
    1. 从学生画像提取关键词（专业/兴趣/技能/目标）
    2. 遍历 84 项竞赛，在 name + work_type + requirements 中查找关键词
    3. 命中关键词越多分数越高，名称命中额外加分
    4. 返回 top_n 条，按分数降序排列
    """
    keywords = _extract_profile_keywords(profile)
    if not keywords:
        return []

    seen_ids: set = set()
    scored: list[tuple[dict, int, int]] = []  # (entry, score, hit_count)

    for key, entry in COMPETITION_FACTS.items():
        cid = entry.get("id")
        if cid in seen_ids:
            continue
        seen_ids.add(cid)

        # 构建竞赛搜索文本
        comp_text = " ".join([
            str(entry.get("name", "")),
            str(entry.get("work_type", "")),
            str(entry.get("requirements", "")),
        ]).lower()

        # 统计命中关键词
        hits = 0
        name_hits = 0
        comp_name_lower = str(entry.get("name", "")).lower()
        for kw in keywords:
            if kw in comp_text:
                hits += 1
                if kw in comp_name_lower:
                    name_hits += 1

        if hits == 0:
            continue

        # 计分：基础 50 + 每命中 8 分 + 名称命中额外 5 分
        score = min(50 + hits * 8 + name_hits * 5, 95)
        scored.append((entry, score, hits))

    # 按分数排序
    scored.sort(key=lambda x: x[1], reverse=True)

    # 转换为结果 dict
    results = []
    for entry, score, hits in scored[:top_n]:
        results.append(_kb_entry_to_result(entry, score, hits))

    return results


def get_kb_competition_list() -> str:
    """生成 84 项 A 类竞赛的紧凑列表文本，用于注入 LLM prompt。

    返回值按编号排列，格式为「序号. 竞赛名（别称）」。
    """
    seen_ids: set = set()
    lines: list[str] = []

    for key, entry in COMPETITION_FACTS.items():
        cid = entry.get("id")
        if cid in seen_ids:
            continue
        seen_ids.add(cid)

        name = entry.get("name", key)
        alt = entry.get("alt_name", "")
        timing = entry.get("timing", "")

        if alt:
            line = f"{cid}. {name}（{alt}）— {timing}"
        else:
            line = f"{cid}. {name} — {timing}"

        lines.append(line)

    # 按 id 排序
    lines.sort(key=lambda x: int(x.split(".")[0]) if x.split(".")[0].isdigit() else 999)

    return "\n".join(lines)
