"""
搜索模块 — 搜索查询词生成 + DuckDuckGo 搜索执行。
"""
import time
from config import MAX_SEARCH_RESULTS_PER_QUERY, SLEEP_BETWEEN_QUERIES


def generate_search_queries(profile: dict) -> list[str]:
    """根据用户画像生成 20+ 条搜索查询词。

    包含：热门竞赛精确查询 + 专业相关查询 + 保研/企业维度查询。
    """
    school = profile.get("school", "")
    major = profile.get("major", "")
    grade = profile.get("grade", "")
    interests = profile.get("interests", "")
    goals = profile.get("goals", [])

    # 如果没提供 goals，从 interests 推断
    if not goals:
        all_text = f"{interests}".lower()
        if any(kw in all_text for kw in ["保研", "加分", "综测"]):
            goals = ["保研加分"]
        elif any(kw in all_text for kw in ["求职", "实习", "企业", "工作"]):
            goals = ["求职直通"]

    queries = []

    # 热门竞赛精确查询（限定官方域 + 当前年份）
    hot_competitions = [
        "蓝桥杯", "华为ICT大赛", "数学建模", "计算机设计大赛",
        "挑战杯", "互联网+", "服创大赛", "信息安全竞赛",
        "全国大学生电子设计竞赛", "全国大学生英语竞赛",
    ]
    for comp in hot_competitions:
        queries.append(f"{comp} 2026 报名通知 site:edu.cn")
        queries.append(f"{comp} 2026 大赛 官网 比赛时间")

    # 专业相关查询
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

    # 保研加分维度
    if any(g in ["保研加分", "保研"] for g in goals):
        m = major or "大学生"
        queries.append(f"2026年 {m} 保研加分 竞赛 报名 site:edu.cn")
        queries.append("全国大学生 保研 竞赛 排行榜 加分")

    # 企业赛/求职直通维度
    if any(g in ["求职直通", "求职", "企业"] for g in goals):
        queries.append("2026 企业赛 大学生 华为 宝洁 欧莱雅 工行杯 报名通知")
        queries.append("2026年 大学生 企业竞赛 实习直通 offer")

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
