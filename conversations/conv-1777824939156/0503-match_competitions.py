#!/usr/bin/env python3
"""
竞赛选赛助手 V1.4 (CLI本地终端) — 全面收集 + 手动分析 + 资源分离

用法:
  # 自动搜索模式
  python 0503-match_competitions.py --school "..." --major "..." --grade "..." --interests "..."
  # 手动分析模式（不搜索网络，纯知识库分析）
  python 0503-match_competitions.py --school "..." --major "..." --grade "..." --analyze "蓝桥杯"

依赖: pip install ddgs openai

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

# 竞赛分类速查
COMPETITION_CATEGORIES = {
    "A类·创新创业": {
        "keywords": ["大创", "互联网+", "挑战杯", "创新创业", "创新大赛", "三创赛", "电子商务创新"],
        "主办方": "政府/教育部",
        "综测": "✅ 通常计入综测",
        "含金量": "最高",
        "适合": "全专业",
        "团队": "需要团队+指导老师",
    },
    "B类·专业技能": {
        "keywords": ["数学建模", "机械创新", "化工设计", "电子设计", "蓝桥杯", "英语竞赛",
                   "力学竞赛", "结构设计", "数字建筑", "汉语言", "语言文字", "翻译大赛",
                   "模拟法庭", "知识产权", "财会", "税收", "能源经济"],
        "主办方": "政府/教育部/学会",
        "综测": "✅ 通常计入综测",
        "含金量": "高",
        "适合": "专业对口",
        "团队": "部分个人，部分团队",
    },
    "C类·商科营销": {
        "keywords": ["欧莱雅", "宝洁", "联合利华", "华为精英", "苏宁", "商业精英",
                   "商务谈判", "营销大赛", "金融科技", "工行杯"],
        "主办方": "企业",
        "综测": "⚠️ 部分学校不计入综测，先确认",
        "含金量": "中高（企业认可度高）",
        "适合": "商科/跨专业",
        "团队": "通常需要团队",
    },
    "D类·公益实践": {
        "keywords": ["三下乡", "志愿服务", "社会实践"],
        "主办方": "学校/政府",
        "综测": "✅ 通常计入综测",
        "含金量": "较低",
        "适合": "全专业",
        "团队": "团队",
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
    """根据竞赛名称判断分类"""
    name_lower = name.lower()
    for cat, info in COMPETITION_CATEGORIES.items():
        for kw in info["keywords"]:
            if kw.lower() in name_lower:
                return cat
    return "B类·专业技能"  # 默认


def get_benefit_text(name: str, benefits_text: str = "") -> str:
    """根据竞赛类型生成好处说明"""
    cat = classify_competition(name)
    parts = []

    if "创新创业" in cat or "大创" in name or "互联网" in name or "挑战杯" in name:
        parts.append("🎓 综测保研：{}。{}".format(
            BENEFIT_TEMPLATES["综测保研"][:50],
            BENEFIT_TEMPLATES["考研复试"][:40]
        ))
    elif "商科" in cat or "企业" in cat.lower():
        parts.append("💼 求职直通：{}".format(BENEFIT_TEMPLATES["企业直通"]))
    else:
        parts.append("📋 专业技能：{}".format(BENEFIT_TEMPLATES["实践能力"]))

    if benefits_text:
        parts.append(benefits_text)
    return "\n│ ".join(parts)


def get_pitfall_text(name: str, is_team: bool, is_free: bool, fee: str) -> str:
    """生成避坑提醒"""
    cat = classify_competition(name)
    warnings = []

    if "商科" in cat or "C类" in cat:
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
        "其他技能": "other_skills", "每周可投入时间": "time_commitment",
        "可参赛月份": "available_months", "寒暑假可集中备赛": "summer_winter",
        "赛事规模": "preference", "团队vs个人": "team_preference",
        "指导老师": "has_advisor", "跨校组队": "can_cross_school",
        "避免类型": "avoid_types", "GPA/排名": "gpa_rank",
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


# ============================================================
# 第一步：DuckDuckGo 搜索（免费，替代 Tavily）
# ============================================================
def generate_search_queries(profile: dict) -> list[str]:
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
    if major:
        queries.append(f"2026年 大学生 {major} 学科竞赛 报名通知")
        queries.append(f"{major} 大学生 可以参加的 竞赛 2026")
    if interests:
        queries.append(f"2026年 大学生 {interests} 竞赛 报名")
    if school:
        queries.append(f"{school} 竞赛通知 2026")
    queries.append("全国大学生 学科竞赛 排行榜 2026 报名")
    queries.append("2026年 大学生 创新创业 竞赛 通知")
    queries.append("2026 大学生竞赛 日历 报名时间")
    if grade in ["大一", "大二"]:
        queries.append("适合低年级 大学生 竞赛 零基础 2026")

    # V1.4: 保研加分维度
    if any(g in ["保研加分", "保研"] for g in goals):
        m = major or "大学生"
        queries.append(f"2026年 {m} 保研加分 竞赛 报名")
        queries.append("全国大学生 保研 竞赛 排行榜 加分")
        if grade in ["大一", "大二"]:
            queries.append(f"{grade} 保研 竞赛 规划 2026")

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
- 参赛目标: {goals_str}
- 每周时间投入: {profile.get('time_commitment', '未填写')}
- 赛事偏好: {profile.get('preference', '不限')}
- 团队/个人偏好: {profile.get('team_preference', '不限')}
- 是否有指导老师: {profile.get('has_advisor', '未知')}
- 是否可跨校: {profile.get('can_cross_school', '未知')}
- 想避免的竞赛类型: {profile.get('avoid_types', '无')}"""

    # 🆕 嵌入的竞赛知识（帮助 DeepSeek 做判断）
    knowledge_text = """## 竞赛分类与好处（内置知识库）
- A类·创新创业(大创/互联网+/挑战杯): 政府主办,综测✅,最高含金量,全专业,团队赛+需指导老师
- B类·专业技能(数模/蓝桥杯/英语竞赛/NECCS/力学/结构等): 政府/学会主办,综测✅,高含金量,专业对口
- C类·商科营销(欧莱雅/宝洁/华为/工行杯等): 企业主办,综测⚠️可能不计入,企业认可度高,可直通offer
- D类·公益实践(三下乡等): 学校主办,综测✅,含金量较低

## 六大好处
1.实践能力: 把课堂变真本事,证明学习能力
2.综测保研: 高层次可获保研名额,复试核心考察
3.考研复试: 协和331逆袭390凭SCI论文
4.求职简历: 仅次于实习的高含金量内容
5.企业直通: 企业赛终极大奖=预录用offer/直通终面卡
6.跨专业跳板: 用比赛证明跨界能力

## 避坑要点
- 企业赛(C类)必须标注⚠️可能不计综测
- 团队赛标注👥需组队
- 收费赛标注💰金额+确认学校报销
- 大一标注门槛是否适合"""

    json_tpl = """{"type":"competition或resource","name":"竞赛全称","match_score":85,"match_reason":"专业匹配度:XX;年级/时间合适度:XX;兴趣/目标契合度:XX","cat":"A/B/C/D类·类型名","benefits":"参加好处(结合六大好处，40字)","pitfalls":"避坑提醒","recommend_index":4,"registration_form":"个人/团队","registration_url":"信息页链接","registration_deadline":"YYYY-MM-DD或未知","suitable_majors":"适合专业","cross_school_allowed":true,"participation_type":"个人/团队/均可","is_free":true,"fee_amount":"免费或金额","notes":"备注（含金量/难度/竞争对手）","source_url":"来源URL","source_type":"官方/非官方","desc":"100-150字描述竞赛内容和考核形式","official_url":"竞赛组委会官网地址(与registration_url区分，找不到填'未知')","deadline_reference":"当registration_deadline未知时:往年时间规律参考(如'往年通常4月省赛,10月报名';已知时空字符串)","focus":"从[保研加分,企业直通,能力锻炼,拿奖率高]中选1-3个逗号分隔"}}"""

    rules = f"""当前日期: {today}
{knowledge_text}

规则(必须严格遵守):
1. type: 具体竞赛填"competition"，竞赛目录/汇总清单/排行榜填"resource"
2. match_score=专业匹配(30)+年级合适(20)+兴趣匹配(30)+可操作(20)
3. recommend_index(1-5): 1=不推荐 2=勉强 3=可以报 4=推荐 5=强烈推荐
4. match_reason: 三段式"专业匹配度:XX;年级/时间合适度:XX;兴趣/目标契合度:XX"，每段15-25字
5. benefits: 结合六大好处写出具体好处，不写空话
6. pitfalls: 企业赛必须写⚠️可能不计综测，团队赛必须提组队
7. cat: A/B/C/D类+类型名；resource类型cat填"📋 竞赛目录"
8. 竞赛名中如有引号必须用「」
9. type="resource"时，notes写明这个页面列出了哪些竞赛
10. desc: 100-150字描述竞赛内容+考核形式+赛制流程
11. official_url: 组委会官网(与registration_url区分)，找不到填"未知"
12. deadline_reference: 仅registration_deadline未知时填写往年规律(如"往年通常4月省赛,10月报名")，已知时留空
13. focus: A类→"保研加分"；企业赛→"企业直通"；门槛低获奖率高→"拿奖率高"；其余→"能力锻炼"
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
- focus 必须标注:A类→"保研加分"，C类/企业主办→"企业直通"
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
- 想避免的竞赛类型: {profile.get('avoid_types', '无')}"""

    knowledge_text = """## 竞赛分类与好处（内置知识库）
- A类·创新创业(大创/互联网+/挑战杯): 政府主办,综测✅,最高含金量,全专业,团队赛+需指导老师
- B类·专业技能(数模/蓝桥杯/英语竞赛/NECCS/力学/结构等): 政府/学会主办,综测✅,高含金量,专业对口
- C类·商科营销(欧莱雅/宝洁/华为/工行杯等): 企业主办,综测⚠️可能不计入,企业认可度高,可直通offer
- D类·公益实践(三下乡等): 学校主办,综测✅,含金量较低

## 六大好处
1.实践能力: 把课堂变真本事,证明学习能力
2.综测保研: 高层次可获保研名额,复试核心考察
3.考研复试: 协和331逆袭390凭SCI论文
4.求职简历: 仅次于实习的高含金量内容
5.企业直通: 企业赛终极大奖=预录用offer/直通终面卡
6.跨专业跳板: 用比赛证明跨界能力

## 避坑要点
- 企业赛(C类)必须标注⚠️可能不计综测
- 团队赛标注👥需组队
- 收费赛标注💰金额+确认学校报销
- 大一标注门槛是否适合"""

    json_tpl = """{"name":"竞赛全称","match_score":85,"match_reason":"专业匹配度:XX;年级/时间合适度:XX;兴趣/目标契合度:XX","cat":"A/B/C/D类·类型名","benefits":"参加好处(结合六大好处，40字)","pitfalls":"避坑提醒","recommend_index":4,"registration_form":"个人/团队","registration_deadline":"YYYY-MM-DD或未知","suitable_majors":"适合专业","cross_school_allowed":true,"participation_type":"个人/团队/均可","is_free":true,"fee_amount":"免费或金额","notes":"备注（含金量/难度）","desc":"100-150字描述竞赛内容和考核形式","official_url":"竞赛组委会官网地址(找不到填'未知')","deadline_reference":"当registration_deadline未知时:往年时间规律(如'往年通常4月省赛,10月报名';已知时空字符串)","focus":"从[保研加分,企业直通,能力锻炼,拿奖率高]中选1-3个逗号分隔"}"""

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
│ 官网:     {official_url[:55] if official_url else '未找到'}
│ 时间参考: {dl_ref[:55] if dl_ref else '无历史数据'}
│ 来源类型: {source_label}     来源: {(_val(m, 'source_url', 'src') or '')[:40]}
│ 备注: {(_val(m, 'notes', 'note') or '无')[:55]}""" +
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


# ============================================================
# 主流程
# ============================================================
def main():
    if not DEEPSEEK_API_KEY:
        print("❌ 缺少 DEEPSEEK_API_KEY 环境变量")
        print("设置: set DEEPSEEK_API_KEY=你的DeepSeek密钥")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="竞赛选赛助手 V1.4 (CLI本地终端) — 全面收集+手动分析")
    parser.add_argument("--school", default="", help="学校全称")
    parser.add_argument("--major", default="", help="专业名称")
    parser.add_argument("--grade", default="", help="年级")
    parser.add_argument("--interests", default="", help="兴趣技能(逗号分隔)")
    parser.add_argument("--requirements", default="", help="特殊要求")
    parser.add_argument("--profile", default="", help="用户画像模板文件路径(.md格式，见03-素材/用户画像模板.md)")
    parser.add_argument("--analyze", default="", help="手动分析模式：输入竞赛名称，AI深度分析是否适合你")
    parser.add_argument("--batch", default="", help="批量分析模式：输入包含竞赛名称的文本文件路径（每行一个）")

    args = parser.parse_args()

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
║        🔍 竞赛选赛助手 V1.4 (CLI本地终端) — 手动分析模式          ║
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
║        🔍 竞赛选赛助手 V1.4 (CLI本地终端) — 全面收集+手动分析     ║
║  画像 → 搜索 → 匹配 → 理由/好处/避坑/推荐/官网/标签    ║
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

    # 2. 匹配+知识增强
    print("\n🧠 第三步：DeepSeek 匹配 + 知识增强（约15-30秒）...")
    data = match_and_enrich(profile, results)

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
