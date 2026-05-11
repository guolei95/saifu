#!/usr/bin/env python3
"""
竞赛选赛助手 V1.7 (CLI本地终端) — 两类分类 + 智能去重 + URL正确性校验 + 手动分析

用法:
  # 自动搜索模式
  python 0503-match_competitions.py --school "..." --major "..." --grade "..." --interests "..."
  # 手动分析模式（不搜索网络，纯知识库分析）
  python 0503-match_competitions.py --school "..." --major "..." --grade "..." --analyze "蓝桥杯"

依赖: pip install ddgs openai

V1.6 变更:
  - cross_source_verify() L1交叉验证: 同一竞赛在多个搜索结果中比对日期/URL一致性
  - self_review_results() L2 LLM自我审查: 第二次调用LLM回顾输出,对照搜索材料挑错
  - 主动验证三层: L1交叉验证 → L2自我审查 → L3常识库兜底
V1.5 变更:
  - COMPETITION_FACTS 竞赛常识库：热门竞赛已知正确信息优先于搜索结果
  - verify_url() URL可达性校验：输出前HEAD检查官网是否存活
  - check_date_sanity() 日期合理性检查：常识库模式与搜索值冲突时告警
  - enrich_with_facts() 常识库修正：自动覆盖/补充官方URL、时间规律、备注
  - 用户反馈持久化：save_correction/apply_corrections 保存纠正到本地JSON
  - 搜索查询优化：限定 site:edu.cn/site:gov.cn + 热门竞赛专属精确查询
V1.4 变更:
  - 用户画像模板(--profile) + parse_profile_template()解析
  - 保研/企业赛搜索维度 + FOCUS_LABELS(4类焦点标签)
  - 新增输出: desc(竞赛内容)/official_url(官网)/dl_ref(历史时间)/focus(保研/企业/能力/拿奖)
  - 匹配理由三段式: 专业匹配度/年级合适度/兴趣契合度 分行展示
  - profile_text 4→14字段, JSON 18→22字段, max_tokens 8K→16K
V1.3 历史:
  - 竞赛目录/排行榜分离展示 + 手动/批量分析 + type字段
"""

import os, json, argparse, sys, time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# 配置
# ============================================================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
LLM_MODEL = "deepseek-chat"
# 联网搜索 — 默认且唯一模式（不联网怎么查最新竞赛信息？）

# ============================================================
# 竞赛知识库（融合自 jc-competition-selector skill）
# ============================================================

# 竞赛分类速查 — 仅两类：学校/教育部主办 vs 企业主办
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

# 六大好处模板
BENEFIT_TEMPLATES = {
    "实践能力": "把课堂知识变成真本事，赛中遇到的问题逼你自学解决——这是企业最看重的「学习能力」",
    "综测保研": "高层次竞赛（如互联网+国奖）可直接获保研名额。保外校面试核心考察科研和比赛经历",
    "考研复试": "科研和比赛经历在复试中权重极高——协和医院331分考生凭SCI逆袭390分对手",
    "求职简历": "比赛经历是仅次于实习的高含金量简历内容，既能证明硬实力又能证明软实力",
    "企业直通": "很多企业赛的终极大奖是预录用offer或直通终面卡——不用投简历直接进终面",
    "跨专业跳板": "想转行？用比赛证明你有跨界能力——比「我感兴趣」有说服力100倍",
}

# 避坑规则
PITFALL_RULES = {
    "企业赛": "⚠️ 部分企业赛不计入综测加分！选赛前务必确认你学校的综测规则",
    "需要导师": "⚠️ 此竞赛需要指导老师，大一的同学建议提前联系专业课老师或辅导员",
    "团队赛": "👥 需要组队参赛，建议找专业互补的队友（技术+文案+表达各一人）",
    "高难度": "⚠️ 难度较高，建议有一定基础后再报，或者先跟学长学姐打下手积累经验",
    "时间冲突": "⚠️ 注意比赛时间是否与期末考试冲突，合理安排",
    "费用": "⚠️ 此竞赛有报名费，确认学校是否报销",
}

# V1.4: 保研/企业赛维度标签
FOCUS_LABELS = {
    "保研加分": "🎓 该竞赛在多数高校计入综测加分，高层次获奖可直接获保研名额或面试加分",
    "企业直通": "💼 企业主办或冠名，终极大奖常含实习/预录用offer/直通终面卡，企业认可度高",
    "能力锻炼": "💪 侧重实践能力成长，适合积累项目经验，丰富简历，提升综合竞争力",
    "拿奖率高": "🏆 门槛相对较低、获奖比例较高，适合首次参赛建立信心和履历",
}

# ═══════════════════════════════════════════════════════════
# V1.5 竞赛常识库：已知正确信息，优先于搜索结果
# 当你发现信息错误时，更新此字典即可全局生效
# ═══════════════════════════════════════════════════════════
COMPETITION_FACTS = {
    "蓝桥杯": {
        "official_url": "https://dasai.lanqiao.cn",
        "报名窗口": "前一年10月—12月（学校统一报名）；补报至当年3月",
        "省赛时间": "当年4月（通常中旬）",
        "国赛时间": "当年5月底—6月初",
        "报名费": "300元/人",
        "组别": "研究生组/大学A组(985/211)/B组(普通本科)/C组(专科)",
        "备赛建议": "暑假开始刷题，图书馆借算法书，官网题库+历年真题",
        "备注": "⚠️ 主要报名期是10-12月！3月仅是个人补报最终截止日，绝大多数学校在12月统一报名",
        "参赛形式": "个人",
    },
    "华为ICT大赛": {
        "official_url": "https://e.huawei.com/cn/talent/ict-academy",
        "报名窗口": "每年9月左右启动（关注华为ICT学院官网或学校通知）",
        "赛制": "实践赛(网络/云/基础软件/AI四赛道)+创新赛+编程赛+挑战赛",
        "级别": "省赛→中国区决赛→全球总决赛",
        "报名费": "免费",
        "参赛形式": "团队(3人+1指导老师)",
        "备注": "⚠️ 该URL是华为ICT学院总览页，大赛启动后会有当年专题子站。建议9月直接搜索「华为ICT大赛 2026」找最新入口",
    },
    "数学建模": {
        "official_url": "https://www.mcm.edu.cn",
        "全称": "高教社杯全国大学生数学建模竞赛(CUMCM)",
        "比赛时间": "每年9月上旬（第一个周四18:00起，连续72小时）",
        "报名时间": "赛前2-4周（通常8月）",
        "报名费": "约200-300元/队",
        "参赛形式": "团队(3人)",
        "备赛建议": "暑假集中备赛：学经典模型+练2-3道真题+找靠谱队友",
        "备注": "国赛(CUMCM)官网 mcm.edu.cn；美赛(MCM/ICM)是另一赛事，官网 comap.com",
    },
    "计算机设计大赛": {
        "official_url": "https://jsjds.blcu.edu.cn",
        "全称": "中国大学生计算机设计大赛(4C大赛)",
        "时间线": "校赛3-4月 → 省赛5月 → 国赛7-8月",
        "报名费": "免费",
        "参赛形式": "团队(2-5人)",
        "大类": "软件应用与开发/物联网/AI应用/大数据/数媒等11类",
        "备注": "教育部A类赛事，2026年允许使用国产AI工具辅助开发，需标注使用情况",
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
        "时间线": "校赛秋季→省赛次年春→国赛次年夏（两年一届，大小年交替）",
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
        "级别": "校级→省级→国家级立项",
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

# 10个真实案例（来自 skill 05-cases.md）
REAL_CASES = [
    {
        "id": 1,
        "title": "双非大一进前9%决赛",
        "match": ["挑战杯", "互联网+", "创新创业"],
        "story": "三个双非大一学生，在各种名校队伍中进入前9%决赛",
        "lesson": "学校牌子不是决定因素，关键是你愿不愿意做",
    },
    {
        "id": 2,
        "title": "没得奖也能写进简历",
        "match": ["欧莱雅", "宝洁", "联合利华", "商赛", "企业赛"],
        "story": "参加联合利华商赛没得奖，但完整走完全流程，简历写了调研和策划过程",
        "lesson": "面试官看的是你做了什么、怎么做的，不只是奖项本身",
    },
    {
        "id": 3,
        "title": "企业赛直通offer",
        "match": ["华为", "民生银行", "金融科技", "企业赛"],
        "story": "参加民生银行金融科技挑战赛，特等奖直接获预录用offer",
        "lesson": "企业赛的最大价值不是奖金，而是绕过了简历筛选直接见面试官",
    },
    {
        "id": 4,
        "title": "跨专业入职华为",
        "match": ["编程", "Python", "数学建模", "蓝桥杯", "软件"],
        "story": "机械专业同学参加编程比赛，凭借比赛项目经历跨专业入职华为做程序员",
        "lesson": "比赛是跨专业求职的第一步——用比赛证明你有这个能力",
    },
    {
        "id": 5,
        "title": "成绩不好靠比赛逆袭",
        "match": ["华为", "企业赛", "销售", "营销"],
        "story": "大三之前成绩一般还挂过科，靠华为销售挑战赛拿东北区金奖直通终面入职华为",
        "lesson": "成绩不好不代表没路，用比赛证明自己",
    },
    {
        "id": 6,
        "title": "大创一鱼多吃",
        "match": ["大创", "挑战杯", "互联网+"],
        "story": "一个大创项目改题目参加挑战杯，两个比赛都得奖",
        "lesson": "同一份努力，换个包装可以收获两份——这是很多学长不会告诉你的套路",
    },
    {
        "id": 7,
        "title": "数学建模找外援",
        "match": ["数学建模", "数模", "美赛"],
        "story": "拿到题目先找博士生聊3小时请教经验，比自己摸索3天还有用",
        "lesson": "大学竞赛不是闭卷考试，找到有经验的人请教比埋头苦干高效得多",
    },
    {
        "id": 8,
        "title": "商赛进全国前200",
        "match": ["欧莱雅", "商赛", "营销", "品牌"],
        "story": "欧莱雅Brandstorm每年2万+队伍，进前200本身就是简历亮点，凭此找到大厂实习",
        "lesson": "商赛即使没拿大奖，进到一定轮次就是简历亮点",
    },
    {
        "id": 9,
        "title": "指导老师层级决定奖项",
        "match": ["大创", "挑战杯", "互联网+"],
        "story": "唯一做出实物并成功飞行的项目只拿校一等奖，室友没做出来拿国二——指导老师是院长",
        "lesson": "选指导老师尽量找职称高的，这虽然不公平但就是现实",
    },
    {
        "id": 10,
        "title": "考研复试331逆袭390",
        "match": ["学术", "科研", "论文"],
        "story": "北京协和医院复试，331分考生凭SCI论文经历逆袭390分对手",
        "lesson": "科研和比赛经历在复试中权重极高，能弥补初试差距",
    },
]


def classify_competition(name: str) -> str:
    """根据竞赛名称判断分类（两类：学校/教育部类 vs 企业类）"""
    name_lower = name.lower()
    for cat, info in COMPETITION_CATEGORIES.items():
        for kw in info["keywords"]:
            if kw.lower() in name_lower:
                return cat
    # 默认：名字带"大赛/竞赛/杯"且无企业关键词 → 学校/教育部类
    if "大赛" in name or "竞赛" in name or "杯" in name:
        return "🏫 学校/教育部类"
    return "🏫 学校/教育部类"  # 安全默认


def get_benefit_text(name: str, benefits_text: str = "") -> str:
    """根据竞赛类型生成好处说明"""
    cat = classify_competition(name)
    parts = []

    if "企业类" in cat:
        parts.append("💼 求职直通：{}".format(BENEFIT_TEMPLATES["企业直通"]))
    else:
        parts.append("🎓 综测保研：{}。{}".format(
            BENEFIT_TEMPLATES["综测保研"][:50],
            BENEFIT_TEMPLATES["考研复试"][:40]
        ))
    parts.append("📋 专业技能：{}".format(BENEFIT_TEMPLATES["实践能力"]))

    if benefits_text:
        parts.append(benefits_text)
    return "\n│ ".join(parts)


def get_pitfall_text(name: str, is_team: bool, is_free: bool, fee: str) -> str:
    """生成避坑提醒"""
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


def find_related_case(name: str) -> dict | None:
    """匹配相关案例"""
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


def parse_profile_template(filepath: str) -> dict:
    """解析用户画像模板文件，提取字段到 dict。

    模板格式: - **字段名**: 值
    留空字段(_或___)视为未填写。
    """
    import re
    result = {}
    KEY_MAP = {
        "学校": "school", "专业": "major", "年级": "grade",
        "兴趣技能": "interests", "具体技能": "skills",
        "主要目标": "goals", "次要目标": "secondary_goals",
        "编程语言": "programming_langs", "工具/框架": "tools",
        "技术方向": "tech_directions",
        "其他技能": "other_skills", "每周可投入时间": "time_commitment",
        "可参赛月份": "available_months", "寒暑假可集中备赛": "summer_winter",
        "赛事规模": "preference", "团队vs个人": "team_preference",
        "指导老师": "has_advisor", "跨校组队": "can_cross_school",
        "避免类型": "avoid_types", "GPA/排名": "gpa_rank",
        # V1.8 新增字段：过往经历 + 比赛形态偏好
        "国家级及以上获奖": "past_national",
        "省级获奖": "past_provincial",
        "校级获奖": "past_school",
        "代表性项目": "representative_projects",
        "比赛周期偏好": "preferred_duration",
        "比赛形式偏好": "preferred_format",
        "报名费预算": "fee_budget",
        "语言偏好": "language_pref",
        "组队规模偏好": "preferred_team_size",
    }
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                m = re.match(r'- \*\*(.+?)\*\*:?\s*(.+)', line)
                if m:
                    key_raw, value = m.group(1).strip(), m.group(2).strip()
                    if key_raw in KEY_MAP:
                        clean = value
                        # 以 ___ 或 _ 开头 = 未填写，跳过
                        if clean.startswith("___") or clean.startswith("_"):
                            continue
                        # 去掉末尾括号内的选项说明（如：选一项，如：...）
                        clean = re.sub(r'\s*[（(][^）)]*[）)]', '', clean).strip()
                        clean = clean.rstrip("_").strip()
                        if not clean:
                            continue
                        # goals 类字段按逗号/分号拆分
                        field = KEY_MAP[key_raw]
                        if field in ("goals", "secondary_goals"):
                            clean = [g.strip() for g in re.split(r'[,，/]', clean) if g.strip()]
                        result[field] = clean
        return result
    except FileNotFoundError:
        print(f"   ⚠️ 画像模板文件不存在: {filepath}")
        return {}
    except Exception as e:
        print(f"   ⚠️ 解析画像模板失败: {e}")
        return {}


# ═══════════════════════════════════════════════════════════
# V1.5 校验与修正模块
# ═══════════════════════════════════════════════════════════

def verify_url(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    """HEAD请求检查URL是否可达。

    返回 (可达?, 状态描述)。不可达不一定是永久失效，可能是临时波动。
    """
    if not url or url in ("未知", "无", "未找到", ""):
        return False, "未提供URL"
    import urllib.request
    try:
        req = urllib.request.Request(url, method="HEAD", headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        if resp.status < 400:
            return True, f"可达({resp.status})"
        else:
            return False, f"HTTP {resp.status}"
    except Exception as e:
        err = str(e)
        if "certificate" in err.lower():
            return True, "可达(证书警告)"
        if "403" in err or "Forbidden" in err:
            return True, "可达(403,HEAD被拒但站点存活)"
        return False, "不可达"


def find_fact_match(name: str) -> dict | None:
    """在 COMPETITION_FACTS 中查找匹配的竞赛。

    支持模糊匹配：名称包含关键字即可命中。
    """
    name_lower = name.lower()
    best_key = None
    best_len = 0
    for key in COMPETITION_FACTS:
        if key.lower() in name_lower:
            if len(key) > best_len:  # 最长匹配优先
                best_len = len(key)
                best_key = key
    if best_key:
        return COMPETITION_FACTS[best_key]
    return None


def enrich_with_facts(competition: dict) -> dict:
    """用内置常识库修正/补充竞赛信息。

    对于 COMPETITION_FACTS 中存在的竞赛：
    - official_url: 用已知正确值覆盖可疑的搜索值
    - deadline_reference: 补全时间规律
    - notes: 追加备注
    - 标记 source_confidence 为 'verified'

    返回修改后的 competition（原地修改+返回）。
    """
    facts = find_fact_match(competition.get("name", ""))
    if not facts:
        return competition

    # 标记已通过常识库校验
    competition["_verified_by_facts"] = True

    # 官网：常识库优先 + 标记URL是否被修正
    known_url = facts.get("official_url", "").rstrip("/")
    comp_url = competition.get("official_url", "").rstrip("/")
    if known_url and known_url != comp_url:
        old_url = competition.get("official_url", "")
        if old_url and old_url not in ("未知", "无", ""):
            competition["_url_was"] = old_url  # 保留旧值供参考
            competition["_url_fixed"] = True   # 🆕 标记：URL被常识库修正过
        competition["official_url"] = known_url
    elif known_url and known_url == comp_url:
        competition["_url_verified"] = True    # 🆕 标记：URL与常识库一致，可信

    # 时间规律：常识库补充
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
            # 两者都保留，常识库的标 📌
            competition["deadline_reference"] = f"{existing} | 📌 {', '.join(dl_ref_parts)}"
        else:
            competition["deadline_reference"] = ", ".join(dl_ref_parts)

    # 备注：常识库追加
    if "备注" in facts:
        existing_notes = competition.get("notes", "")
        fact_note = facts["备注"]
        if fact_note and fact_note not in (existing_notes or ""):
            competition["notes"] = f"{existing_notes} | 📌 {fact_note}".strip(" |")

    # 费⽤：常识库补充
    if "报名费" in facts and not competition.get("fee_amount"):
        competition["fee_amount"] = facts["报名费"]
        competition["is_free"] = (facts["报名费"] == "免费")

    # 参赛形式：常识库补充
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
    """检查日期是否与常识模式冲突，返回警告列表。

    规则示例：
    - 蓝桥杯省赛在4月，如果 deadline 在4月之后大概率是错的
    - 数学建模在9月，如果 deadline 在9月之后可能混淆了报名和比赛
    """
    warnings = []
    facts = find_fact_match(competition.get("name", ""))
    if not facts:
        return warnings

    dl = competition.get("registration_deadline", "")
    if not dl or dl == "未知":
        return warnings

    # 蓝桥杯省赛4月，报名截止如果在4月之后 → 可能是国赛截止或其他信息
    if "蓝桥杯" in competition.get("name", ""):
        if dl.startswith("2026-04") or dl.startswith("2026-05"):
            # 4-5月的DDL对蓝桥杯来说大概率不是省赛报名
            warnings.append("⚠️ 蓝桥杯省赛通常在4月，此截止日期可能是补报/国赛/其他信息，请确认")

    # 数学建模在9月比赛，如果deadline在10月之后 → 可能是混淆
    if "数学建模" in competition.get("name", "") or "数模" in competition.get("name", ""):
        if dl > "2026-10":
            warnings.append("⚠️ 国赛通常在9月举行，此日期可能不是国赛报名截止日，请到 mcm.edu.cn 确认")

    return warnings


# ═══════════════════════════════════════════════════════════
# V1.6 主动验证层：交叉验证 + LLM自我审查
# ═══════════════════════════════════════════════════════════

def cross_source_verify(competitions: list[dict], search_results: list[dict]) -> list[dict]:
    """L1: 跨搜索结果交叉验证。

    对每个竞赛，在所有搜索结果中查找相关条目，提取日期/URL信息，
    比对一致性。如果多个来源信息矛盾，降低置信度并标注。
    """
    import re
    from datetime import date

    today = date.today()

    for comp in competitions:
        comp_name = comp.get("name", "")
        if not comp_name:
            continue

        # 在搜索结果中找相关条目
        related = []
        for r in search_results:
            title = r.get("title", "")
            content = r.get("content", "")
            combined = f"{title} {content}"
            # 竞赛名中的关键词命中
            keywords = comp_name.split("·")[-1] if "·" in comp_name else comp_name
            # 取竞赛名中较长的词做关键词
            kw_parts = [kw for kw in keywords.replace("（", " ").replace("）", " ").replace("(", " ").replace(")", " ").split() if len(kw) >= 2]
            hit = sum(1 for kw in kw_parts if kw.lower() in combined.lower())
            if hit >= 2:  # 至少命中2个关键词才算相关
                related.append(r)

        if len(related) < 2:
            continue  # 只有一个来源，无法交叉验证

        # 提取所有日期
        date_pattern = re.compile(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})?[日号]?')
        all_dates = []
        for r in related:
            found = date_pattern.findall(r.get("content", "") + r.get("title", ""))
            for y, m, d in found:
                d = d or "1"
                try:
                    dt = date(int(y), int(m), int(d))
                    if dt.year >= today.year - 1:  # 只保留近两年日期
                        all_dates.append((dt, r.get("url", "")))
                except ValueError:
                    pass

        # 分析日期一致性
        if len(all_dates) >= 3:
            dates_only = [d[0] for d in all_dates]
            from statistics import stdev
            # 转换为天数
            base = min(dates_only)
            day_diffs = [(d - base).days for d in dates_only]
            try:
                spread = stdev(day_diffs) if len(day_diffs) > 1 else 0
            except Exception:
                spread = 0

            # 标准差 > 30天说明日期极度不一致
            if spread > 60:
                comp["_date_confidence"] = "low"
                existing = comp.get("notes", "")
                comp["notes"] = f"{existing} | ⚠️ 交叉验证: {len(related)}个来源日期不一致(标准差{spread:.0f}天)，请到官网确认"
            elif spread > 15:
                comp["_date_confidence"] = "medium"
                comp["_cross_warning"] = f"多个来源日期有{spread:.0f}天偏差，建议核实"
            else:
                comp["_date_confidence"] = "high"

        # 🆕 URL一致性检查
        urls_found = set()
        for r in related:
            u = r.get("url", "")
            # 提取域名
            domain_match = re.search(r'https?://([^/]+)', u)
            if domain_match:
                urls_found.add(domain_match.group(1))

        comp_url = comp.get("official_url", "")
        if comp_url and comp_url not in ("未知", "未找到", ""):
            comp_domain_match = re.search(r'https?://([^/]+)', comp_url)
            if comp_domain_match:
                comp_domain = comp_domain_match.group(1)
                if comp_domain not in urls_found and len(urls_found) > 0:
                    # LLM输出的URL域名在搜索结果中没出现过
                    comp["_url_from_search"] = list(urls_found)[:3]  # 保留搜索结果中的域名供参考

    return competitions


def self_review_results(competitions: list[dict], search_results: list[dict], profile: dict) -> list[dict]:
    """L2: LLM自我审查 —— 让LLM回顾自己的输出，对照原始搜索材料挑错。

    原理：第二次调用LLM，给它的任务是「审查」而非「生成」。
    审查模式下的LLM比生成模式更擅长发现矛盾。
    """
    if not competitions:
        return competitions

    # 构建简洁的审查材料
    comp_summary = ""
    for i, c in enumerate(competitions[:10], 1):  # 最多审查前10条
        comp_summary += f"""
[{i}] {c.get('name', '?')}
    deadline: {c.get('registration_deadline', '?')}
    url: {c.get('official_url', '?')}
    url_original: {c.get('source_url', '?')}
    fee: {c.get('fee_amount', '?')}
    desc: {c.get('desc', '')[:80]}
    match_reason: {c.get('match_reason', '')[:60]}
"""

    search_summary = ""
    for i, r in enumerate(search_results[:20], 1):
        search_summary += f"[S{i}] {r.get('title','')[:80]}\n    URL: {r.get('url','')}\n    {r.get('content','')[:150]}\n\n"

    review_prompt = f"""你是竞赛信息审查员。请审查以下AI生成的竞赛推荐结果，对照原始搜索材料，找出可能的错误。

## 审查规则
1. **日期矛盾**: deadline是否与搜索结果中提到的日期一致？如果搜索结果明确说「X月比赛/报名」，但输出写了不同的月份，标记为「日期存疑」
2. **URL来源**: official_url是否在搜索结果中出现过？如果没有，它从哪来的？
3. **费用矛盾**: 费用与搜索结果是否一致？
4. **逻辑矛盾**: deadline已过期却被标为「报名中」的，标记为「状态矛盾」
5. **信息缺失**: 关键字段为「未知」的，如果搜索结果中有明确信息，标记为「遗漏」

## 学生画像
学校: {profile.get('school','?')} | 专业: {profile.get('major','?')} | 年级: {profile.get('grade','?')}

## AI生成的竞赛推荐
{comp_summary}

## 原始搜索材料
{search_summary}

请输出JSON数组，每条指出一个发现的问题：
[{{"competition_index": 竞赛编号, "field": "deadline/url/fee/status/desc", "issue": "问题描述(20字内)", "severity": "high/medium/low", "suggestion": "建议修正方案(30字内)"}}]

如果没有发现问题，输出空数组 []。
⚠️ 只输出JSON数组，不要其他文字。"""

    print("   🔍 正在自我审查（LLM回顾+挑错）...")
    review_results = _call_llm(review_prompt)

    if not review_results:
        return competitions

    # 将审查发现的问题附加到竞赛条目
    for issue in review_results:
        idx = issue.get("competition_index", 0) - 1
        if 0 <= idx < len(competitions):
            field = issue.get("field", "")
            severity = issue.get("severity", "low")
            suggestion = issue.get("suggestion", "")

            sev_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "")

            if severity == "high":
                # 高风险：直接追加到 pitfalls
                existing = competitions[idx].get("pitfalls", "")
                competitions[idx]["pitfalls"] = f"{existing} | {sev_icon}自审查[{field}]: {suggestion}".strip(" |")
                competitions[idx]["_self_review_warning"] = f"{field}: {suggestion}"
            else:
                # 中低风险：追加到 notes
                existing = competitions[idx].get("notes", "")
                competitions[idx]["notes"] = f"{existing} | {sev_icon}自审查: {issue.get('issue','')}".strip(" |")

    high_issues = sum(1 for i in review_results if i.get("severity") == "high")
    if high_issues:
        print(f"      ⚠️ 发现 {high_issues} 个高风险问题，已标注到注意事项中")
    print(f"      审查完成，共 {len(review_results)} 条反馈")

    return competitions


# ═══════════════════════════════════════════════════════════
# V1.5 用户反馈持久化模块
# ═══════════════════════════════════════════════════════════

FEEDBACK_FILE = None  # 延迟初始化，见 _get_feedback_path()

def _get_feedback_path() -> Path:
    """获取反馈文件的路径（创建在脚本同级的 03-素材/ 下）"""
    global FEEDBACK_FILE
    if FEEDBACK_FILE is None:
        script_dir = Path(__file__).resolve().parent.parent  # 02-方案 的父目录 = 项目根
        material_dir = script_dir / "03-素材"
        material_dir.mkdir(parents=True, exist_ok=True)
        FEEDBACK_FILE = material_dir / "竞赛信息纠正.json"
    return FEEDBACK_FILE


def load_corrections() -> dict:
    """加载历史用户纠正记录"""
    path = _get_feedback_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_correction(competition_name: str, field: str, wrong_value: str, correct_value: str):
    """记录用户纠正到本地JSON，下次运行自动应用"""
    corrections = load_corrections()
    key = f"{competition_name}::{field}"
    corrections[key] = {
        "wrong": wrong_value,
        "correct": correct_value,
        "corrected_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    _get_feedback_path().write_text(
        json.dumps(corrections, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"   📝 已记录纠正: {competition_name} → {field}")


def apply_corrections(competitions: list[dict]) -> list[dict]:
    """加载历史纠正并应用到竞赛列表"""
    corrections = load_corrections()
    if not corrections:
        return competitions

    for comp in competitions:
        name = comp.get("name", "")
        for key, correction in corrections.items():
            # key 格式: "竞赛名::字段名"
            parts = key.split("::", 1)
            if len(parts) != 2:
                continue
            comp_key, field = parts
            if comp_key.lower() in name.lower():
                if comp.get(field) == correction["wrong"]:
                    comp[field] = correction["correct"]
                    comp["_corrected_by_feedback"] = True

    return competitions


# ============================================================
# 第一步：DuckDuckGo 搜索（免费，替代 Tavily）
# ============================================================
def generate_search_queries(profile: dict) -> list[str]:
    """V1.5: 生成搜索查询 — 加入官方域限定 + 热门竞赛精确查询"""
    school = profile.get("school", "")
    major = profile.get("major", "")
    grade = profile.get("grade", "")
    interests = profile.get("interests", "")
    goals = profile.get("goals", [])

    # 如果没从模板提取到 goals，从 interests/requirements 推断
    if not goals:
        all_text = f"{interests} {profile.get('requirements', '')}".lower()
        if any(kw in all_text for kw in ["保研", "加分", "综测"]):
            goals = ["保研加分"]
        elif any(kw in all_text for kw in ["求职", "实习", "企业", "工作"]):
            goals = ["求职直通"]

    queries = []

    # 🆕 V1.5: 为热门竞赛生成精确查询（限定官方域名 + 当前年份）
    HOT_COMPETITIONS = [
        "蓝桥杯", "华为ICT大赛", "数学建模", "计算机设计大赛",
        "挑战杯", "互联网+", "服创大赛", "信息安全竞赛",
        "全国大学生电子设计竞赛", "全国大学生英语竞赛",
    ]
    for comp in HOT_COMPETITIONS:
        queries.append(f"{comp} 2026 报名通知 site:edu.cn")
        queries.append(f"{comp} 2026 大赛 官网 比赛时间")

    # 专业相关查询（限定官方域）
    if major:
        queries.append(f"{major} 大学生 学科竞赛 2026 报名 site:edu.cn")
        queries.append(f"{major} 大学生 可以参加的 竞赛 2026")
    if interests:
        queries.append(f"2026年 大学生 {interests} 竞赛 报名 site:edu.cn")
    if school:
        queries.append(f"{school} 竞赛通知 2026 site:edu.cn")

    # 通用排行榜
    queries.append("全国大学生 学科竞赛 排行榜 2026 报名 site:edu.cn")
    queries.append("2026年 大学生 创新创业 竞赛 通知 site:gov.cn")
    queries.append("2026 大学生竞赛 日历 报名时间 site:edu.cn")

    if grade in ["大一", "大二"]:
        queries.append("适合低年级 大学生 竞赛 零基础 2026")

    # V1.4: 保研加分维度
    if any(g in ["保研加分", "保研"] for g in goals):
        m = major or "大学生"
        queries.append(f"2026年 {m} 保研加分 竞赛 报名 site:edu.cn")
        queries.append("全国大学生 保研 竞赛 排行榜 加分")

    # V1.4: 企业赛/求职直通维度
    if any(g in ["求职直通", "求职", "企业"] for g in goals):
        queries.append("2026 企业赛 大学生 华为 宝洁 欧莱雅 工行杯 报名通知")
        queries.append("2026年 大学生 企业竞赛 实习直通 offer")

    return queries


def search_competitions(queries: list[str]) -> list[dict]:
    """DuckDuckGo 实时搜索 — 默认且唯一模式，联网才能查到最新竞赛信息"""
    all_results = []
    seen_urls = set()

    # 导入 DuckDuckGo 搜索库
    DDGS = None
    try:
        from ddgs import DDGS  # 新包名
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # 旧包名（兼容）
        except ImportError:
            print("   ❌ 未安装搜索库，请执行: pip install ddgs")
            return all_results

    if DDGS is None:
        print("   ❌ 搜索库不可用，请检查安装")
        return all_results

    try:
        with DDGS() as ddgs:
            for query in queries:
                try:
                    results = list(ddgs.text(query, max_results=8))
                    for r in results:
                        url = r.get("href", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append({
                                "title": r.get("title", ""),
                                "url": url,
                                "content": r.get("body", "")[:300],
                            })
                    print(f"  ✅ [{query[:40]}...] → {len(results)}条")
                    time.sleep(0.8)
                except Exception as e:
                    print(f"  ⚠️  [{query[:40]}...] 失败: {e}")
                    time.sleep(1)
    except Exception as e:
        print(f"  ❌ DuckDuckGo 搜索异常: {e}")

    return all_results


# ============================================================
# 第二步：DeepSeek 匹配 + 知识增强
# ============================================================
def _call_llm(prompt: str) -> list[dict]:
    from openai import OpenAI

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=16384,
    )
    text = resp.choices[0].message.content.strip()

    # 清理 markdown
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # 清洗不可见字符
    text = text.encode("utf-8", "ignore").decode("utf-8")
    text = "".join(c for c in text if c.isprintable() or c in "\n\r\t ")

    # 多重 JSON 修复
    import re
    strategies = [text, text.rstrip().rstrip(",") + "\n]"]
    for pattern in [r'\}\s*,?\s*\n', r'\}']:
        matches = list(re.finditer(pattern, text))
        if matches:
            strategies.append(text[:matches[-1].end()].rstrip().rstrip(",") + "\n]")
    last_brace = text.rfind("}")
    if last_brace > 0:
        strategies.append(text[:last_brace+1].rstrip().rstrip(",") + "\n]")

    # 🆕 如果文本看起来像单对象，也尝试包裹成数组
    trimmed = text.strip()
    if trimmed.startswith("{") and not trimmed.startswith("[{"):
        strategies.insert(0, "[" + trimmed + "]")

    for s in strategies:
        try:
            result = json.loads(s)
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):  # 🆕 单对象也接受
                return [result]
        except Exception:
            pass
    return []


def match_and_enrich(profile: dict, results: list[dict]) -> dict:
    from datetime import date
    today = date.today().isoformat()

    # 构建搜索结果文本（限制条数）
    results_text = ""
    for i, r in enumerate(results[:25]):
        results_text += f"[{i+1}] {r['title']}\n    URL: {r['url']}\n    {r['content'][:250]}\n\n"

    # V1.4: 丰富画像
    goals_str = ", ".join(profile.get("goals", [])) if profile.get("goals") else "未指定"
    profile_text = f"""- 学校: {profile.get('school', '未知')}
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
- 过往国家级获奖: {profile.get('past_national', '未填写')}
- 过往省级获奖: {profile.get('past_provincial', '未填写')}
- 过往校级获奖: {profile.get('past_school', '未填写')}
- 代表性项目: {profile.get('representative_projects', '未填写')}
- 比赛周期偏好: {profile.get('preferred_duration', '不限')}
- 比赛形式偏好: {profile.get('preferred_format', '不限')}
- 报名费预算: {profile.get('fee_budget', '不限')}
- 语言偏好: {profile.get('language_pref', '不限')}
- 组队规模偏好: {profile.get('preferred_team_size', '不限')}"""

    # 🆕 嵌入的竞赛知识（帮助 DeepSeek 做判断）
    knowledge_text = """## 竞赛分类（两类，简单分清）
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

    json_tpl = """{"type":"competition或resource","name":"竞赛全称","match_score":85,"match_reason":"专业匹配度:XX;年级/时间合适度:XX;兴趣/目标契合度:XX","cat":"🏫 学校/教育部类或💼 企业类","benefits":"参加好处(结合六大好处，40字)","pitfalls":"避坑提醒","recommend_index":4,"registration_form":"个人/团队","registration_url":"信息页链接","registration_deadline":"YYYY-MM-DD或未知","suitable_majors":"适合专业","cross_school_allowed":true,"participation_type":"个人/团队/均可","is_free":true,"fee_amount":"免费或金额","notes":"备注（含金量/难度/竞争对手）","source_url":"来源URL","source_type":"官方/非官方","desc":"100-150字描述竞赛内容和考核形式","official_url":"竞赛组委会官网地址(与registration_url区分，找不到填'未知')","deadline_reference":"当registration_deadline未知时:往年时间规律参考(如'往年通常4月省赛,10月报名';已知时空字符串)","focus":"从[保研加分,企业直通,能力锻炼,拿奖率高]中选1-3个逗号分隔"}}"""

    rules = f"""当前日期: {today}
{knowledge_text}

规则(必须严格遵守):
1. type: 具体竞赛填"competition"，竞赛目录/汇总清单/排行榜填"resource"
2. match_score=专业匹配(30)+年级合适(20)+兴趣匹配(30)+可操作(20)
3. recommend_index(1-5): 1=不推荐 2=勉强 3=可以报 4=推荐 5=强烈推荐
4. match_reason: 三段式"专业匹配度:XX;年级/时间合适度:XX;兴趣/目标契合度:XX"，每段15-25字
5. benefits: 结合六大好处写出具体好处，不写空话
6. pitfalls: 企业类必须写⚠️可能不计综测，团队赛必须提组队
7. cat: 只填"🏫 学校/教育部类"或"💼 企业类"，不要填别的；resource类型填"📋 竞赛目录"
8. 竞赛名中如有引号必须用「」
9. type="resource"时，notes写明这个页面列出了哪些竞赛
10. desc: 100-150字描述竞赛内容+考核形式+赛制流程
11. official_url: 组委会官网(与registration_url区分)，找不到填"未知"
12. deadline_reference: 仅registration_deadline未知时填写往年规律(如"往年通常4月省赛,10月报名")，已知时留空
13. focus: 学校/教育部类→"保研加分"；企业类→"企业直通"；门槛低获奖率高→"拿奖率高"；其余→"能力锻炼"
14. 必须只输出JSON数组
"""

    open_prompt = f"""找出报名截止日期>={today}或未知、适合此学生的竞赛。

{profile_text}

## 搜索结果
{results_text}

## JSON格式(必须严格，每条包含全部18个字段)
[{json_tpl}]

{rules}

⚠️ 关键要求:
- type="competition"的具体竞赛：至少输出12条（尽力多找）
- type="resource"的竞赛目录/汇总清单：有多少输出多少（不占competition名额）
- match_score < 50 不要输出
- match_reason 三段式:"专业匹配度:XX;年级/时间合适度:XX;兴趣/目标契合度:XX"，每段具体
- desc 必须100-150字描述竞赛内容，让用户不点链接就知道比什么
- official_url 必须填组委会官网(与url区分)，找不到填"未知"
- dl 未知时 dl_ref 必须填往年时间规律，参考知识库
- focus 必须标注:学校/教育部类→"保研加分"，企业类→"企业直通"
- 不允许输出与专业完全无关的竞赛
- registration_deadline 未知的竞赛也要输出
- 去重：同一竞赛不重复
- 竞赛目录/排行榜(type="resource")不参加匹配度排序，单独标注"""

    closed_prompt = f"""找出报名已截止但非常值得关注的竞赛（供明年规划参考）。

{profile_text}

## 搜索结果
{results_text}

## JSON格式(必须严格，每条包含全部18个字段)
[{json_tpl}]

{rules}

⚠️ 关键要求:
- 最多输出1条已截止的竞赛（挑含金量最高、最值得明年准备的那条）
- dl末尾标注"(已截止，建议明年X月关注)"，dl_ref填往年时间规律
- r 三段式、desc 100-150字、official_url、focus 等要求同报名中竞赛
- 必须与专业高度相关，不相关的不输出
- 没有值得关注的已截止竞赛就不输出"""

    print("   🤖 正在匹配「报名中」的竞赛...")
    open_list = _call_llm(open_prompt)
    print(f"      找到 {len(open_list)} 条")

    print("   🤖 正在匹配「已截止」的竞赛...")
    closed_list = _call_llm(closed_prompt)
    print(f"      找到 {len(closed_list)} 条")

    # 🆕 V1.5: 用内置常识库修正所有结果
    print("   🔍 常识库校验中...")
    open_list = [enrich_with_facts(m) for m in open_list]
    closed_list = [enrich_with_facts(m) for m in closed_list]
    fixed_count = sum(1 for m in open_list + closed_list if m.get("_verified_by_facts"))
    print(f"      已用常识库修正 {fixed_count} 条竞赛信息")

    # 🆕 V1.6: L1 跨搜索结果交叉验证
    if results:
        print("   🔬 跨源交叉验证中...")
        open_list = cross_source_verify(open_list, results)
        closed_list = cross_source_verify(closed_list, results)
        date_low = sum(1 for m in open_list if m.get("_date_confidence") == "low")
        if date_low:
            print(f"      ⚠️ {date_low} 条竞赛的日期在多个来源中不一致")

    # 🆕 V1.6: L2 LLM自我审查
    print("   🧠 LLM自我审查中...")
    open_list = self_review_results(open_list, results, profile)
    closed_list = self_review_results(closed_list, results, profile)

    return {"open": open_list, "closed": closed_list}


# ============================================================
# 🆕 手动分析模式：用户自己指定的竞赛 → AI深度分析
# ============================================================
def analyze_one_competition(profile: dict, competition_name: str) -> dict:
    """分析用户指定的单个竞赛，不搜索网络"""
    from datetime import date
    today = date.today().isoformat()

    goals_str = ", ".join(profile.get("goals", [])) if profile.get("goals") else "未指定"
    profile_text = f"""- 学校: {profile.get('school', '未知')}
- 专业: {profile.get('major', '未知')}
- 年级: {profile.get('grade', '未知')}
- 兴趣/技能: {profile.get('interests', '不限')}
- 具体技能: {profile.get('skills', profile.get('interests', '未填写'))}
- 参赛目标: {goals_str}
- 每周时间投入: {profile.get('time_commitment', '未填写')}
- 赛事偏好: {profile.get('preference', '不限')}
- 团队/个人偏好: {profile.get('team_preference', '不限')}
- 是否有指导老师: {profile.get('has_advisor', '未知')}
- 是否可跨校: {profile.get('can_cross_school', '未知')}
- 想避免的竞赛类型: {profile.get("avoid_types", "无")}
- 过往国家级获奖: {profile.get("past_national", "未填写")}
- 过往省级获奖: {profile.get("past_provincial", "未填写")}
- 过往校级获奖: {profile.get("past_school", "未填写")}
- 代表性项目: {profile.get("representative_projects", "未填写")}
- 比赛周期偏好: {profile.get("preferred_duration", "不限")}
- 比赛形式偏好: {profile.get("preferred_format", "不限")}
- 报名费预算: {profile.get("fee_budget", "不限")}
- 语言偏好: {profile.get("language_pref", "不限")}
- 组队规模偏好: {profile.get("preferred_team_size", "不限")}"""
knowledge_text = """## 竞赛分类（两类，简单分清）
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

    json_tpl = """{"name":"竞赛全称","match_score":85,"match_reason":"专业匹配度:XX;年级/时间合适度:XX;兴趣/目标契合度:XX","cat":"🏫 学校/教育部类或💼 企业类","benefits":"参加好处(结合六大好处，40字)","pitfalls":"避坑提醒","recommend_index":4,"registration_form":"个人/团队","registration_deadline":"YYYY-MM-DD或未知","suitable_majors":"适合专业","cross_school_allowed":true,"participation_type":"个人/团队/均可","is_free":true,"fee_amount":"免费或金额","notes":"备注（含金量/难度）","desc":"100-150字描述竞赛内容和考核形式","official_url":"竞赛组委会官网地址(找不到填'未知')","deadline_reference":"当registration_deadline未知时:往年时间规律(如'往年通常4月省赛,10月报名';已知时空字符串)","focus":"从[保研加分,企业直通,能力锻炼,拿奖率高]中选1-3个逗号分隔"}"""

    prompt = f"""请分析以下竞赛是否适合此学生，输出完整分析。

学生画像:
{profile_text}

竞赛名称: {competition_name}

{knowledge_text}

当前日期: {today}

## JSON格式(必须严格，输出单条JSON对象，非数组)
{json_tpl}

规则:
1. s(匹配度)=专业匹配(30)+年级合适(20)+兴趣匹配(30)+可操作(20)，低于30分说明完全不适合
2. wi(推荐指数1-5): 1=不推荐 2=勉强 3=可以报 4=推荐 5=强烈推荐
3. r: 必须从专业/年级/兴趣三方面具体说明匹配/不匹配原因
4. ben: 结合六大好处写出具体好处，不适合也要写"如果参加能获得什么"
5. pit: 必须检查避坑要点
6. cat: 根据竞赛分类判断
7. 如果不知道此竞赛的具体信息（报名方式/费用/截止日期等），标注"未知"或根据常识推断
8. 必须只输出单条JSON对象，不要数组"""

    print("   🤖 正在分析指定竞赛...")
    result = _call_llm(prompt)
    if result and isinstance(result, list) and len(result) > 0:
        return result[0]
    elif result and isinstance(result, dict):
        return result
    return {}


def analyze_multiple(profile: dict, names: list[str]) -> list[dict]:
    """批量分析多个竞赛"""
    results = []
    for i, name in enumerate(names, 1):
        name = name.strip()
        if not name:
            continue
        print(f"\n   [{i}/{len(names)}] {name}")
        result = analyze_one_competition(profile, name)
        if result:
            results.append(result)
    return results


# ============================================================
# 输出格式化（融合知识库增强）
# ============================================================
def _val(m, *keys):
    """取字段值，支持新旧两种命名"""
    for k in keys:
        v = m.get(k)
        if v is not None and v != "":
            return v
    return None

def print_one(m, i, label=""):
    name = _val(m, "name", "n") or "未知"
    score = _val(m, "match_score", "s") or 0
    stars = "⭐" * min(5, int(score) // 20)
    category = m.get("cat", "未知")
    reason = _val(m, "match_reason", "r") or "未提供"
    benefits = _val(m, "benefits", "ben") or "未提供"
    pitfalls = _val(m, "pitfalls", "pit") or ""
    worth_it = _val(m, "recommend_index", "wi") or 3
    wi_stars = "⭐" * int(worth_it)
    wi_text = ["", "不推荐", "勉强可报", "可以报名", "推荐报名", "强烈推荐"][int(worth_it)]

    # V1.4 新字段
    desc = _val(m, "desc", "description") or ""
    official_url = _val(m, "official_url") or ""
    dl_ref = _val(m, "deadline_reference", "dl_ref") or ""
    focus = _val(m, "focus") or "能力锻炼"

    # 三段式理由拆分
    if ";" in reason or "；" in reason:
        reason_parts = [p.strip() for p in reason.replace("；", ";").split(";")]
    else:
        reason_parts = [reason]  # 兼容旧格式

    # focus 标签
    focus_badges = ""
    for fi in [f.strip() for f in focus.split(",")]:
        if "保研" in fi:
            focus_badges += "🎓保研加分 "
        elif "企业" in fi:
            focus_badges += "💼企业直通 "
        elif "拿奖" in fi:
            focus_badges += "🏆拿奖率高 "
        elif "能力" in fi:
            focus_badges += "💪能力锻炼 "
    if not focus_badges:
        focus_badges = "💪能力锻炼"

    # 🆕 V1.5: URL 可达性校验
    url_to_check = official_url if official_url and official_url not in ("未知", "未找到", "") else ""
    url_status = ""
    if url_to_check:
        ok, status = verify_url(url_to_check)
        if ok:
            url_status = f"  ✅ URL可达"
        else:
            url_status = f"  ⚠️ URL不可达"
    elif not official_url or official_url in ("未知", "未找到", ""):
        url_status = "  ⚠️ 未提供官网"

    # 🆕 V1.7: URL 正确性标识
    url_correct_badge = ""
    if m.get("_url_verified"):
        url_correct_badge = "  ✅ URL与常识库一致"
    elif m.get("_url_fixed"):
        old = m.get("_url_was", "")
        if old:
            url_correct_badge = f"  ⚠️ URL已修正（原: {old[:40]}）"
        else:
            url_correct_badge = "  ✅ 已用常识库URL"

    # 🆕 V1.5: 日期合理性警告
    date_warnings = check_date_sanity(m, time.strftime("%Y-%m-%d"))

    # 常识库修正标识
    verified_badge = "  📌 已用常识库校验" if m.get("_verified_by_facts") else ""
    corrected_badge = "  ✏️ 已用历史纠正修正" if m.get("_corrected_by_feedback") else ""

    # 🆕 V1.6: 交叉验证置信度
    date_conf = m.get("_date_confidence", "")
    cross_badge = ""
    if date_conf == "low":
        cross_badge = "  🔴 多源日期不一致"
    elif date_conf == "medium":
        cross_badge = "  🟡 日期略有偏差"
    elif date_conf == "high":
        cross_badge = "  🟢 多源日期一致"
    cross_warning = m.get("_cross_warning", "")

    # 🆕 V1.6: 自审查标识
    self_review_warning = m.get("_self_review_warning", "")

    # 来源
    st = _val(m, "source_type", "st") or "未知"
    source_label = "🏛️ 官方" if "官方" in str(st) else "⚠️ 非官方"

    # 费用
    is_free = _val(m, "is_free", "fr")
    fee = _val(m, "fee_amount", "fee") or "未知"
    fee_label = "🆓 免费" if (is_free and str(fee or "免费") in ["免费", "未知", "True", "true"]) else f"💰 {fee}"

    # 参赛形式
    pt = _val(m, "participation_type", "pt") or _val(m, "registration_form") or "未知"
    if "个人" in str(pt) and "团队" not in str(pt):
        team_label = "🧑 仅个人"
    elif "团队" in str(pt) and "个人" not in str(pt):
        team_label = "👥 仅团队"
    elif "均" in str(pt):
        team_label = "🧑/👥 均可"
    else:
        team_label = str(pt)

    # 相关案例
    case = find_related_case(name)

    # 组装三段式理由输出
    reason_lines = ""
    if len(reason_parts) >= 1:
        reason_lines += f"\n│   专业: {reason_parts[0][:58]}"
    if len(reason_parts) >= 2:
        reason_lines += f"\n│   年级: {reason_parts[1][:58]}"
    if len(reason_parts) >= 3:
        reason_lines += f"\n│   兴趣: {reason_parts[2][:58]}"

    # 组装 desc 分两行
    desc_line1 = desc[:58] if desc else "未提供"
    desc_line2 = desc[58:116] if len(desc) > 58 else ""

    print(f"""
┌{'─'*62}┐
│ {label}{name[:52]}
├{'─'*62}┤
│ 📊 匹配度: {stars} ({score}分)     📂 类型: {category}
│ 🏷️  标签: {focus_badges.strip()}
├{'─'*62}┤
│ 📖 竞赛内容: {desc_line1}{"│" + " " * 14 + desc_line2[:58] if desc_line2 else ""}
├{'─'*62}┤
│ 📝 匹配理由:{reason_lines}
├{'─'*62}┤
│ 💡 为什么参加: {benefits[:58]}
│                {benefits[58:118] if len(benefits)>58 else ''}
├{'─'*62}┤
│ ⚠️  注意事项: {pitfalls[:58] if pitfalls else '暂无明显坑点'}
│                {pitfalls[58:118] if len(pitfalls)>58 else ''}
├{'─'*62}┤
│ 📋 推荐指数: {wi_stars} ({wi_text})
├{'─'*62}┤
│ 参赛形式: {team_label}     截止: {_val(m, 'registration_deadline', 'dl') or '未知'}
│ 报名方式: {_val(m, 'registration_form', 'f') or '未知'}     费用: {fee_label}
│ 适合专业: {_val(m, 'suitable_majors', 'mj') or '未知'}
│ 跨校参赛: {'✅ 可以' if _val(m, 'cross_school_allowed', 'cs') else '❌ 不可以'}
│ 官网:     {official_url[:52] if official_url else '未找到'}{url_status}{url_correct_badge}
│ 时间参考: {dl_ref[:55] if dl_ref else '无历史数据'}
│ 来源类型: {source_label}     来源: {(_val(m, 'source_url', 'src') or '')[:40]}
│ 备注: {(_val(m, 'notes', 'note') or '无')[:55]}""" +
    (f"\n│ ⚠️ 日期提醒: {date_warnings[0][:55]}" if date_warnings else "") +
    (f"\n│ {verified_badge}{corrected_badge}" if (verified_badge or corrected_badge) else "") +
    (f"\n│ {cross_badge}" if cross_badge else "") +
    (f"\n│   ↳ {cross_warning[:55]}" if cross_warning else "") +
    (f"\n│ 🧠 自审查: {self_review_warning[:55]}" if self_review_warning else "") +
    (f"\n├{'─'*62}┤\n│ 📖 案例「{case['title']}」: {case['lesson'][:45]}" if case else "") +
    f"""
└{'─'*62}┘""")


def print_results(data: dict):
    open_list = data.get("open", [])
    closed_list = data.get("closed", [])

    # 🆕 分离：具体竞赛 vs 资源页面
    competitions = [m for m in open_list if m.get("type", "competition") != "resource"]
    resources = [m for m in open_list if m.get("type", "competition") == "resource"]

    # 🆕 后处理过滤：s < 50 的不显示（仅对具体竞赛）
    competitions = [m for m in competitions if int(_val(m, "match_score", "s") or 0) >= 50]
    # 🆕 按匹配度从高到低排序
    competitions = sorted(competitions, key=lambda m: int(_val(m, "match_score", "s") or 0), reverse=True)

    # 🆕 V1.7: 去重 — 已截止列表中如果和报名中列表有同名竞赛，去掉
    import re as _re
    # 归一化竞赛名：去第X届/引号/年份/尾缀，提取核心名称
    def _norm_name(n):
        n = n.lower().strip()
        n = _re.sub(r'第[一二三四五六七八九十\d]+届', '', n)
        n = _re.sub(r'[「」『』""（）()“”]', '', n)
        n = _re.sub(r'[\d]{4}[\s\-_]*(?:[\d]{4})?', '', n)  # 去掉年份如 2025-2026
        n = _re.sub(r'(中国赛|全球赛|省赛|国赛|校赛|区域赛|选拔赛|决赛)$', '', n)
        n = _re.sub(r'[\s\-_]+', '', n)  # 去空格和连接符
        return n.strip()
    open_norm = set()
    for m in competitions:
        name = _val(m, "name", "n") or ""
        open_norm.add(_norm_name(name))
    closed_list = [m for m in closed_list if _norm_name(_val(m, "name", "n") or "") not in open_norm]

    # 🆕 已截止最多保留 1 条
    if len(closed_list) > 1:
        closed_list = sorted(closed_list, key=lambda m: int(_val(m, "match_score", "s") or 0), reverse=True)[:1]

    if not competitions and not resources and not closed_list:
        print("\n😔 没有找到高度匹配的竞赛。试试换个关键词或扩大兴趣范围。")
        return

    # --- 具体竞赛 ---
    if competitions:
        print("\n" + "━" * 64)
        print(f"  🟢 正在报名中 / 即将开始报名（共 {len(competitions)} 条）")
        print("━" * 64)
        for i, m in enumerate(competitions, 1):
            label = f"第{i}名: " if i == 1 else f"  #{i}: "
            print_one(m, i, label)

    # --- 参考资源页面 ---
    if resources:
        print("\n" + "━" * 64)
        print(f"  📋 找到的竞赛资源页面（共 {len(resources)} 条，建议打开查看有无遗漏）")
        print("━" * 64)
        for i, m in enumerate(resources, 1):
            name = _val(m, "name", "n") or "未知"
            url = _val(m, "registration_url", "url") or _val(m, "source_url", "src") or ""
            note = _val(m, "notes", "note") or ""
            print(f"""
  📄 #{i}: {name[:60]}
     🔗 {url[:80]}
     📝 {note[:100]}
  {'─'*60}""")

    # --- 已截止 ---
    if closed_list:
        print("\n" + "━" * 64)
        print("  🔴 今年已截止（可提前规划，明年再战）")
        print("━" * 64)
        for i, m in enumerate(closed_list, 1):
            print_one(m, i, f"参考: ")


# ============================================================
# 三大误区提醒（选赛结束后输出一次）
# ============================================================
MYTHS = [
    "❌ 「只有大佬才能参赛」→ ✅ 大佬都是从小白成长的，双非大一也能进前9%决赛",
    "❌ 「等学了专业课再参加」→ ✅ 不是学会了再比，是在比赛中学会",
    "❌ 「不得奖就白参加了」→ ✅ 认真做了就能写进简历，面试官看过程不看奖状",
]

TIPS = [
    "💡 报名前务必去官网核实截止日期和参赛要求，网络信息可能有误",
    "💡 同类型比赛建议只报 2-3 个，精力分散反而难出成绩",
    "💡 大一优先报低门槛的积累经验 → 大二大三再冲高含金量赛事",
    "💡 📌=常识库校验 🟢/🔴=交叉验证置信度 🧠=AI自我审查标识 — 多重校验帮你发现可疑信息",
]


def print_tips():
    print(f"""
{'='*64}
  💡 选赛小贴士
{'='*64}""")
    for myth in MYTHS:
        print(f"  {myth}")
    print()
    for tip in TIPS:
        print(f"  {tip}")
    print()


# 🆕 V1.7: 素材收集报告 — 让用户看到搜到了什么
def print_search_summary(results: list[dict], profile: dict):
    """搜索完成后展示素材来源摘要，让用户看清收集质量"""
    import re
    from collections import Counter

    total = len(results)
    if total == 0:
        return

    # 按域名类型分类
    edu_urls = []
    gov_urls = []
    noise_urls = []
    other_urls = []
    school_notices = []  # 最有价值的学校竞赛通知

    noise_keywords = ["每日大赛", "吃瓜", "色情", "淫水", "高潮", "福利姬",
                      "白虎", "嫩穴", "榨精", "手冲", "OnlyFans", "裸"]

    for r in results:
        url = r.get("url", "")
        title = r.get("title", "")
        content = r.get("content", "")
        combined = f"{title} {content}".lower()

        # 噪声检测：垃圾域名 + 关键词
        is_noise = False
        for nk in noise_keywords:
            if nk.lower() in combined:
                is_noise = True
                break
        if not is_noise:
            # 检查域名是否可疑
            domain_match = re.search(r'https?://([^/]+)', url)
            if domain_match:
                domain = domain_match.group(1)
                suspicious_tlds = ['.cc', '.xyz', '.top', '.club', '.cf', '.ga', '.ml']
                if any(domain.endswith(tld) for tld in suspicious_tlds):
                    is_noise = True

        if is_noise:
            noise_urls.append(r)
            continue

        # 教育网站
        if ".edu.cn" in url:
            edu_urls.append(r)
            # 检测是否为竞赛通知（最有价值的一类）
            notice_keywords = ["关于组织", "报名通知", "竞赛通知", "选拔赛",
                               "关于举办", "参赛通知", "大赛通知", "学科竞赛"]
            if any(kw in combined for kw in notice_keywords):
                school_notices.append(r)
        elif ".gov.cn" in url:
            gov_urls.append(r)
        else:
            other_urls.append(r)

    # 统计学校来源
    school_counter = Counter()
    for r in edu_urls:
        m = re.search(r'https?://([^/]+)', r.get("url", ""))
        if m:
            school_counter[m.group(1)] += 1

    top_schools = school_counter.most_common(5)

    sep = "─" * 50
    print(f"""
{sep}
 📡 素材收集报告
{sep}
 🌐 搜索关键词: {len(profile.get('_queries', [])) or 'N'} 条
 📊 共收集到 {total} 条原始搜索结果

 🏫 学校官网          {len(edu_urls)} 条
 🏛️  政府网站          {len(gov_urls)} 条
 📚 其他来源          {len(other_urls)} 条
 🗑️  已过滤噪声        {len(noise_urls)} 条""")

    if school_notices:
        print(f"""
 📌 学校竞赛通知（最有价值来源，共 {len(school_notices)} 条）:""")
        for i, r in enumerate(school_notices[:8], 1):
            title = r.get("title", "")[:55]
            url = r.get("url", "")
            domain = re.search(r'https?://([^/]+)', url)
            domain_str = domain.group(1) if domain else url[:40]
            print(f"    {i}. [{domain_str}] {title}")

    if top_schools:
        print(f"\n 🏫 信息来源最丰富的学校:")
        for domain, cnt in top_schools:
            print(f"    • {domain}  → {cnt} 条")

    if noise_urls:
        print(f"\n 🗑️  已过滤 {len(noise_urls)} 条噪声内容（色情/垃圾站点）")

    print(f"{sep}\n")


# ============================================================
# 主流程
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="竞赛选赛助手 V1.7 (CLI本地终端) — 两类分类+去重+URL校验")
    parser.add_argument("--school", default="", help="学校全称")
    parser.add_argument("--major", default="", help="专业名称")
    parser.add_argument("--grade", default="", help="年级")
    parser.add_argument("--interests", default="", help="兴趣技能(逗号分隔)")
    parser.add_argument("--requirements", default="", help="特殊要求")
    parser.add_argument("--profile", default="", help="用户画像模板文件路径(.md格式，见03-素材/用户画像模板.md)")
    parser.add_argument("--analyze", default="", help="手动分析模式：输入竞赛名称，AI深度分析是否适合你")
    parser.add_argument("--batch", default="", help="批量分析模式：输入包含竞赛名称的文本文件路径（每行一个）")

    args = parser.parse_args()

    if not DEEPSEEK_API_KEY:
        print("❌ 缺少 DEEPSEEK_API_KEY 环境变量")
        print("设置: set DEEPSEEK_API_KEY=你的DeepSeek密钥")
        sys.exit(1)

    # V1.4: 从画像模板加载扩展信息
    extended_profile = {}
    if args.profile:
        extended_profile = parse_profile_template(args.profile)
        if extended_profile:
            print(f"   ✅ 已从画像模板加载: {args.profile}")
        else:
            print(f"   ⚠️ 未能解析画像模板，使用命令行参数")

    # 🆕 手动分析模式：不需要搜索，直接分析
    if args.analyze or args.batch:
        if not args.school or not args.major or not args.grade:
            print("❌ 手动分析模式也需要提供画像信息：--school --major --grade")
            sys.exit(1)
        # V1.4: 合并画像模板 + CLI参数
        profile = {
            "school": extended_profile.get("school", args.school),
            "major": extended_profile.get("major", args.major),
            "grade": extended_profile.get("grade", args.grade),
            "interests": extended_profile.get("interests", args.interests),
            "requirements": args.requirements,
            "skills": extended_profile.get("skills", ""),
            "goals": extended_profile.get("goals", []),
            "time_commitment": extended_profile.get("time_commitment", ""),
            "preference": extended_profile.get("preference", ""),
            "team_preference": extended_profile.get("team_preference", ""),
            "avoid_types": extended_profile.get("avoid_types", ""),
            "has_advisor": extended_profile.get("has_advisor", ""),
            "can_cross_school": extended_profile.get("can_cross_school", ""),
            "gpa_rank": extended_profile.get("gpa_rank", ""),
        }
        print(f"""
╔══════════════════════════════════════════════════════════╗
║        🔍 竞赛选赛助手 V1.7 (CLI本地终端) — 手动分析模式          ║
║              不搜索网络，用知识库深度分析               ║
╚══════════════════════════════════════════════════════════╝
""")
        print(f"👤 {profile['school']} | {profile['major']} | {profile['grade']}")
        if profile["interests"]:
            print(f"🎯 兴趣: {profile['interests']}")

        if args.analyze:
            # 单条分析
            print(f"\n📝 目标竞赛: {args.analyze}")
            result = analyze_one_competition(profile, args.analyze)
            if result:
                print("\n" + "=" * 64)
                print("                    📊 分析结果")
                print("=" * 64)
                print_one(result, 1, "分析: ")
            else:
                print("❌ 分析失败，请检查竞赛名称后重试。")

        elif args.batch:
            # 批量分析
            batch_path = args.batch
            if not os.path.exists(batch_path):
                print(f"❌ 文件不存在: {batch_path}")
                sys.exit(1)
            with open(batch_path, "r", encoding="utf-8") as f:
                names = f.readlines()
            names = [n.strip() for n in names if n.strip()]
            print(f"\n📋 批量分析 {len(names)} 个竞赛...")
            results = analyze_multiple(profile, names)
            if results:
                print("\n" + "=" * 64)
                print(f"                    📊 批量分析结果（共 {len(results)} 条）")
                print("=" * 64)
                for i, m in enumerate(results, 1):
                    print_one(m, i, f"#{i}: ")

        print_tips()
        return

    # 自动搜索模式（原有流程）
    # V1.4: 合并画像模板 + CLI参数（提前合并以支持模板替代CLI参数）
    profile = {
        "school": extended_profile.get("school", args.school),
        "major": extended_profile.get("major", args.major),
        "grade": extended_profile.get("grade", args.grade),
        "interests": extended_profile.get("interests", args.interests),
        "requirements": args.requirements,
        "skills": extended_profile.get("skills", ""),
        "goals": extended_profile.get("goals", []),
        "time_commitment": extended_profile.get("time_commitment", ""),
        "preference": extended_profile.get("preference", ""),
        "team_preference": extended_profile.get("team_preference", ""),
        "avoid_types": extended_profile.get("avoid_types", ""),
        "has_advisor": extended_profile.get("has_advisor", ""),
        "can_cross_school": extended_profile.get("can_cross_school", ""),
        "gpa_rank": extended_profile.get("gpa_rank", ""),
    }

    # V1.4: 检查必需字段（模板或CLI参数任一提供即可）
    if not profile.get("school") or not profile.get("major") or not profile.get("grade"):
        print("❌ 自动搜索模式需要提供：--school --major --grade (或通过 --profile 模板提供)")
        sys.exit(1)

    print("""
╔══════════════════════════════════════════════════════════╗
║        🔍 竞赛选赛助手 V1.7 (CLI本地终端) — 学校/企业分类+去重+URL校验     ║
║  画像 → 搜索 → 收集报告 → 匹配 → 常识库校验 → 交叉验证 → 自审查           ║
╚══════════════════════════════════════════════════════════╝
""")
    print(f"👤 {profile['school']} | {profile['major']} | {profile['grade']}")
    if profile.get("goals"):
        print(f"🎯 目标: {', '.join(profile['goals'])}")
    if profile["interests"]:
        print(f"🎯 兴趣: {profile['interests']}")

    # 1. 联网搜索（默认唯一模式）
    queries = generate_search_queries(profile)
    print(f"\n📋 第一步：生成 {len(queries)} 条搜索关键词...")
    for q in queries:
        print(f"   → {q}")
    print(f"\n🌐 第二步：DuckDuckGo 实时搜索中...")
    results = search_competitions(queries)

    print(f"   📊 共 {len(results)} 条结果")

    if not results:
        print("❌ 没搜到结果。检查网络或换关键词。")
        return

    # 🆕 V1.7: 素材收集报告
    profile["_queries"] = queries
    print_search_summary(results, profile)

    # 2. 匹配+知识增强
    print("\n🧠 第三步：DeepSeek 匹配 + 知识增强（约15-30秒）...")
    data = match_and_enrich(profile, results)

    # 🆕 V1.5: 应用历史纠正
    data["open"] = apply_corrections(data.get("open", []))
    data["closed"] = apply_corrections(data.get("closed", []))

    # 3. 输出
    print("\n" + "=" * 64)
    print("                    📊 匹配结果")
    print("=" * 64)
    print_results(data)

    # 4. 小贴士
    print_tips()

    print("💡 信息来自网络搜索+内置竞赛知识库，报名前请到官网核实！")


if __name__ == "__main__":
    main()
