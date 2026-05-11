"""
验证模块 — L1 跨搜索结果交叉验证 + L2 LLM 自我审查。
"""
import re
from datetime import date
from statistics import stdev
from services.ai_client import call_deepseek_json


def cross_source_verify(competitions: list[dict], search_results: list[dict]) -> list[dict]:
    """L1 跨搜索结果交叉验证。

    对每个竞赛，在所有搜索结果中找相关条目，
    比对日期一致性和 URL 来源一致性。
    """
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
            keywords = comp_name.split("·")[-1] if "·" in comp_name else comp_name
            kw_parts = [kw for kw in keywords.replace("（", " ").replace("）", " ").replace("(", " ").replace(")", " ").split() if len(kw) >= 2]
            hit = sum(1 for kw in kw_parts if kw.lower() in combined.lower())
            if hit >= 2:
                related.append(r)

        if len(related) < 2:
            continue

        # 提取所有日期
        date_pattern = re.compile(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})?[日号]?')
        all_dates = []
        for r in related:
            found = date_pattern.findall(r.get("content", "") + r.get("title", ""))
            for y, m, d in found:
                d = d or "1"
                try:
                    dt = date(int(y), int(m), int(d))
                    if dt.year >= today.year - 1:
                        all_dates.append((dt, r.get("url", "")))
                except ValueError:
                    pass

        # 日期一致性分析
        if len(all_dates) >= 3:
            dates_only = [d[0] for d in all_dates]
            base = min(dates_only)
            day_diffs = [(d - base).days for d in dates_only]
            try:
                spread_val = stdev(day_diffs) if len(day_diffs) > 1 else 0
            except Exception:
                spread_val = 0

            if spread_val > 60:
                comp["_date_confidence"] = "low"
                existing = comp.get("notes", "")
                comp["notes"] = f"{existing} | ⚠️ 交叉验证: {len(related)}个来源日期不一致，请到官网确认"
            elif spread_val > 15:
                comp["_date_confidence"] = "medium"
                comp["_cross_warning"] = f"多个来源日期有偏差，建议核实"
            else:
                comp["_date_confidence"] = "high"

        # URL 一致性检查
        urls_found = set()
        for r in related:
            u = r.get("url", "")
            domain_match = re.search(r'https?://([^/]+)', u)
            if domain_match:
                urls_found.add(domain_match.group(1))

        comp_url = comp.get("official_url", "")
        if comp_url and comp_url not in ("未知", "未找到", ""):
            comp_domain_match = re.search(r'https?://([^/]+)', comp_url)
            if comp_domain_match:
                comp_domain = comp_domain_match.group(1)
                if comp_domain not in urls_found and len(urls_found) > 0:
                    comp["_url_from_search"] = list(urls_found)[:3]

    return competitions


def self_review_results(competitions: list[dict], search_results: list[dict], profile: dict) -> list[dict]:
    """L2 LLM 自我审查 —— 让 LLM 回顾自己的输出，对照搜索材料挑错。

    第二次调用 DeepSeek，角色是「审查员」而非「生成者」。
    """
    if not competitions:
        return competitions

    # 构建简洁的审查材料
    comp_summary = ""
    for i, c in enumerate(competitions[:10], 1):
        comp_summary += f"""
[{i}] {c.get('name', '?')}
    deadline: {c.get('registration_deadline', '?')}
    url: {c.get('official_url', '?')}
    source_url: {c.get('source_url', '?')}
    fee: {c.get('fee_amount', '?')}
    desc: {c.get('desc', '')[:80]}
    match_reason: {c.get('match_reason', '')[:60]}
"""

    search_summary = ""
    for i, r in enumerate(search_results[:15]):
        search_summary += f"[{i+1}] {r.get('title', '')[:80]} | {r.get('url', '')[:60]}\n"

    review_prompt = f"""你是竞赛信息审查员。请审查以下竞赛匹配结果，对照原始搜索材料检查是否有错误。

## 匹配结果
{comp_summary}

## 原始搜索材料
{search_summary}

## 审查要求
检查以下 5 类问题：
1. 日期矛盾：截止日期是否与搜索材料中的日期冲突
2. URL 来源：官网地址是否可信、是否与搜索材料一致
3. 费用矛盾：报名费是否合理
4. 逻辑矛盾：匹配理由是否与竞赛实际内容矛盾
5. 信息遗漏：是否有重要信息未被提及

输出 JSON 数组，每条一个审查发现：
[{{"competition_index": 1, "issue": "日期矛盾", "severity": "high/medium/low", "detail": "具体问题描述", "suggestion": "修正建议"}}]

如果没有发现问题，输出空数组 []。"""

    try:
        review_results = call_deepseek_json(
            messages=[{"role": "user", "content": review_prompt}],
            temperature=0.2,
            max_tokens=4096,
        )
    except Exception:
        return competitions

    if not review_results:
        return competitions

    # 将审查发现附加到对应竞赛
    for review in review_results:
        idx = review.get("competition_index", 0) - 1
        if 0 <= idx < len(competitions):
            severity = review.get("severity", "medium")
            detail = review.get("detail", "")

            if severity == "high":
                existing_pitfalls = competitions[idx].get("pitfalls", "")
                competitions[idx]["pitfalls"] = f"{existing_pitfalls} | 🧠 审查: {detail}"
            else:
                existing_notes = competitions[idx].get("notes", "")
                competitions[idx]["notes"] = f"{existing_notes} | 🧠 审查: {detail}"

    return competitions
