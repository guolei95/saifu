"""
搜索模块 — 搜索查询词生成 + DuckDuckGo 搜索执行。
v2: 按专业方向动态生成竞赛查询，不再硬编码 STEM 搜索词。
"""
import time
from config import MAX_SEARCH_RESULTS_PER_QUERY, SLEEP_BETWEEN_QUERIES


# ═══════════════════════════════════════════════════════════
# 专业方向 → 该方向的热门竞赛（用于精确搜索）
# ═══════════════════════════════════════════════════════════
CATEGORY_KEYWORDS = {
    "人文社科": [
        "文学", "历史", "哲学", "法学", "政治", "社会", "教育", "新闻", "传播",
        "外语", "英语", "翻译", "日语", "法语", "德语", "汉语言", "中文",
        "考古", "民族", "宗教", "马克思", "思政", "国际关系", "外交", "公共管理",
        "心理", "社工",
    ],
    "理科": [
        "数学", "物理", "化学", "生物", "统计", "地理", "天文", "大气",
        "海洋", "地质", "地球物理", "力学", "心理",
    ],
    "工科": [
        "计算机", "软件", "电子", "机械", "自动化", "电气", "通信", "土木",
        "化工", "材料", "能源", "环境", "测绘", "矿业", "纺织", "轻工",
        "交通", "船舶", "航空", "兵器", "核工程", "农业工程", "生物工程",
        "食品", "安全工程", "公安技术", "物联网", "人工智能", "数据科学",
        "机器人", "智能制造", "微电子", "光电", "信息", "网络",
    ],
    "商科": [
        "市场", "营销", "金融", "会计", "管理", "经济", "工商", "国贸",
        "商务", "财务", "审计", "保险", "税务", "物流", "电商", "供应链",
        "人力资源", "旅游", "酒店", "会展",
    ],
    "艺术设计": [
        "美术", "设计", "音乐", "舞蹈", "戏剧", "影视", "动画", "数媒",
        "视觉", "环艺", "产品设计", "服装", "工业设计", "雕塑", "摄影",
        "书法", "播音", "编导", "表演", "导演",
    ],
    "医学": [
        "医学", "临床", "药学", "护理", "口腔", "公卫", "中医", "中药",
        "法医", "影像", "检验", "康复", "麻醉", "儿科", "预防", "基础医学",
    ],
}


# 每个方向的热门竞赛查询（4-5条，确保覆盖面但不泛滥）
CATEGORY_QUERIES = {
    "人文社科": [
        "全国大学生英语竞赛 2026 报名 官网",
        "外研社 英语演讲 写作 阅读大赛 2026 报名",
        "全国大学生广告艺术大赛 大广赛 2026 报名",
        "全国大学生语言文字能力大赛 2026 报名",
        "全国大学生 模拟法庭 辩论赛 2026 报名 site:edu.cn",
    ],
    "理科": [
        "全国大学生数学建模竞赛 2026 报名 官网",
        "全国大学生数学竞赛 2026 报名 site:edu.cn",
        "全国大学生物理实验竞赛 2026 报名",
        "全国大学生化学实验竞赛 2026 报名",
        "全国大学生生命科学竞赛 2026 报名",
    ],
    "工科": [
        "蓝桥杯 全国软件大赛 2026 报名 官网",
        "华为ICT大赛 2026 报名 官网",
        "全国大学生电子设计竞赛 2026 报名",
        "中国大学生计算机设计大赛 2026 报名",
        "ACM ICPC 程序设计竞赛 2026 报名",
    ],
    "商科": [
        "欧莱雅 Brandstorm 商赛 2026 报名",
        "宝洁 CEO挑战赛 商赛 2026 报名",
        "全国大学生市场调查与分析大赛 2026 报名",
        "三创赛 电子商务 创新创意创业 2026 报名",
        "工行杯 金融科技大赛 2026 报名",
    ],
    "艺术设计": [
        "全国大学生广告艺术大赛 大广赛 2026 报名",
        "全国高校数字艺术设计大赛 NCDA 2026 报名",
        "中国大学生计算机设计大赛 数媒 设计类 2026 报名",
        "MUSE设计奖 大学生 2026",
        "中国大学生 动漫 游戏 创意设计 大赛 2026",
    ],
    "医学": [
        "全国大学生基础医学创新大赛 2026 报名",
        "全国大学生临床技能竞赛 2026 报名",
        "全国大学生生命科学竞赛 科学探究 2026 报名",
        "全国大学生医学技术技能大赛 2026 报名",
    ],
}


# 全方向通用竞赛（每个方向最多选3条，挑最适合的）
UNIVERSAL_QUERIES_ALL = [
    "挑战杯 大学生 课外学术 2026 报名 site:edu.cn",
    "中国国际大学生创新大赛 互联网+ 2026 报名",
    "大创 大学生创新创业训练计划 2026 申报 site:edu.cn",
]


def classify_major(major: str) -> str:
    """根据专业名称判断所属方向。返回分类名，未匹配返回 '通用'。"""
    if not major:
        return "通用"

    major_lower = major.lower()

    # 按关键词精确度排序：长的先匹配，避免「生物医学工程」被「医学」误匹配
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in sorted(keywords, key=len, reverse=True):
            if kw in major_lower:
                return cat

    return "通用"


def generate_search_queries(profile: dict) -> list[str]:
    """根据用户画像生成搜索查询词（v2：按专业方向动态生成）。

    生成策略：
    1. 判断专业方向 → 选择对应竞赛查询（4-5条）
    2. 通用竞赛查询（挑战杯/互联网+/大创，选2条）
    3. 专业名+学科竞赛搜索（2条）
    4. 兴趣/技能相关搜索（1-2条）
    5. 学校相关搜索（1条）
    6. 通用排行榜/日历（2-3条）
    7. 年级/目标/企业赛等补充查询
    """
    school = profile.get("school", "")
    major = profile.get("major", "")
    grade = profile.get("grade", "")
    interests = profile.get("interests", "")
    skills = profile.get("skills", "")
    goals = profile.get("goals", [])

    # 从 interests 推断 goals（如果没填）
    if not goals:
        all_text = f"{interests} {skills}".lower()
        if any(kw in all_text for kw in ["保研", "加分", "综测"]):
            goals = ["保研加分"]
        elif any(kw in all_text for kw in ["求职", "实习", "企业", "工作"]):
            goals = ["求职直通"]

    queries = []

    # ── 1. 按专业方向 → 对应竞赛精确搜索（4-5条）──
    category = classify_major(major)
    cat_queries = CATEGORY_QUERIES.get(category, [])
    queries.extend(cat_queries)

    # ── 2. 通用竞赛（每条方向最多2条，避免噪音）──
    # 挑战杯适合所有方向；互联网+适合有创业意愿的
    if category in ["工科", "理科", "商科"]:
        # 这些方向更可能用到互联网+/大创
        queries.append(UNIVERSAL_QUERIES_ALL[0])  # 挑战杯
        queries.append(UNIVERSAL_QUERIES_ALL[1])  # 互联网+
    elif category == "医学":
        queries.append(UNIVERSAL_QUERIES_ALL[0])  # 挑战杯（有自然科学类）
        queries.append(UNIVERSAL_QUERIES_ALL[2])  # 大创（可申报科研项目）
    else:
        # 人文/艺术/通用：只加挑战杯（有社科调研类）
        queries.append(UNIVERSAL_QUERIES_ALL[0])  # 挑战杯

    # ── 3. 专业名搜索（让搜索引擎自然召回相关竞赛）──
    if major:
        # 用专业名精确搜索
        queries.append(f"{major} 大学生 可以参加的 竞赛 2026")
        # 去掉学校限定，扩大搜索范围
        queries.append(f"{major} 学科竞赛 推荐 2026")

    # 如果被分类为"通用"但填了专业，补一条更宽泛的
    if category == "通用" and major:
        queries.append(f"大学生 {major} 竞赛 报名 2026")

    # ── 4. 兴趣/技能相关搜索 ──
    if interests:
        queries.append(f"2026年 大学生 {interests} 竞赛 报名")
    if skills and skills != interests:
        # 技能和兴趣不同时才单独搜
        skill_text = skills[:20]  # 截断过长的技能列表
        queries.append(f"2026年 大学生 {skill_text} 竞赛 通知")

    # ── 5. 学校相关 ──
    if school:
        queries.append(f"{school} 竞赛通知 2026 site:edu.cn")

    # ── 6. 通用排行榜/日历（帮助 LLM 了解竞赛全貌）──
    queries.append("全国大学生 学科竞赛 排行榜 2026 site:edu.cn")
    queries.append("2026 大学生竞赛 日历 报名时间")

    # ── 7. 年级补充 ──
    if grade in ["大一", "大二"]:
        queries.append(f"适合{grade}学生 大学生 竞赛 零基础 2026")

    # ── 8. 目标维度补充 ──
    if any(g in ["保研加分", "保研"] for g in goals):
        m = major or "大学生"
        queries.append(f"2026年 {m} 保研加分 竞赛 报名 site:edu.cn")
        queries.append(f"全国大学生 保研 竞赛 排行榜 综测加分")

    if any(g in ["求职直通", "求职", "企业"] for g in goals):
        # 企业赛也按方向来
        if category == "商科":
            queries.append("2026 大学生 商业挑战赛 企业赛 快消 咨询 金融 报名")
        elif category == "工科":
            queries.append("2026 大学生 企业赛 华为 百度 腾讯 阿里 报名")
        elif category == "人文社科":
            queries.append("2026 大学生 企业赛 品牌策划 营销 内容创作 报名")
        else:
            queries.append("2026 大学生 企业竞赛 实习直通 offer 报名")

    return queries


def search_competitions(queries: list[str]) -> list[dict]:
    """DuckDuckGo 搜索执行 — 循环执行多条查询，按 URL 去重。

    Args:
        queries: 搜索查询词列表

    Returns:
        list[dict]: 统一格式的搜索结果 [{"title", "url", "content"}, ...]
    """
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
            raise RuntimeError(
                "未安装 DuckDuckGo 搜索库。请执行: pip install ddgs"
            )

    try:
        with DDGS() as ddgs:
            for query in queries:
                try:
                    results = list(ddgs.text(query, max_results=MAX_SEARCH_RESULTS_PER_QUERY))
                    for r in results:
                        url = r.get("href", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append({
                                "title": r.get("title", ""),
                                "url": url,
                                "content": r.get("body", "")[:300],
                            })
                    time.sleep(SLEEP_BETWEEN_QUERIES)
                except Exception:
                    # 单条查询失败不中断整体流程
                    time.sleep(1)
    except Exception:
        pass

    return all_results
