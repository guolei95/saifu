# -*- coding: utf-8 -*-
import requests, json, time, os

BASE_URL = "http://localhost:8000"

PROFILES = {
    "W1_文科_汉语言文学": {"school":"北京师范大学","major":"汉语言文学","grade":"大二","interests":"写作、文学创作、文化研究","skills":"文案写作、编辑","goals":["保研加分","能力锻炼"],"time_commitment":"每周5-8小时","preference":"个人赛为主"},
    "W2_理科_物理学": {"school":"北京大学","major":"物理学","grade":"大三","interests":"实验物理、计算模拟","skills":"Python、Matlab、数据分析","goals":["保研加分","科研经历"],"time_commitment":"每周10小时","preference":"不限"},
    "W3_工科_计算机科学": {"school":"华中科技大学","major":"计算机科学与技术","grade":"大二","interests":"算法竞赛、Web开发、AI","skills":"C++、Python、React","goals":["求职直通","能力锻炼"],"time_commitment":"每周10-15小时","preference":"不限"},
    "W4_商科_市场营销": {"school":"上海财经大学","major":"市场营销","grade":"大三","interests":"品牌策划、数据分析、商业案例","skills":"PPT、Excel、市场调研","goals":["求职直通","企业实习"],"time_commitment":"每周5-8小时","preference":"团队赛为主"},
    "W5_艺术_视觉传达设计": {"school":"中央美术学院","major":"视觉传达设计","grade":"大二","interests":"平面设计、数字艺术、品牌视觉","skills":"PS、AI、Figma、插画","goals":["能力锻炼","作品集积累"],"time_commitment":"每周3-5小时","preference":"不限"},
    "W6_医学_临床医学": {"school":"复旦大学","major":"临床医学","grade":"大三","interests":"医学研究、临床技能、医学写作","skills":"文献检索、SPSS、基础实验","goals":["保研加分","科研经历"],"time_commitment":"每周5-8小时","preference":"不限"},
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    task_ids = {}

    # Submit
    for label, profile in PROFILES.items():
        resp = requests.post(f"{BASE_URL}/api/match", json=profile, timeout=10)
        task_id = resp.json().get("task_id", "")
        task_ids[label] = task_id

    # Wait
    results = {}
    pending = set(task_ids.values())
    waited = 0
    while pending and waited < 300:
        time.sleep(5)
        waited += 5
        still = []
        for tid in pending:
            data = requests.get(f"{BASE_URL}/api/match/{tid}", timeout=10).json()
            if data.get("status") == "done":
                label = [k for k,v in task_ids.items() if v==tid][0]
                results[label] = data.get("result", {})
            elif data.get("status") == "error":
                label = [k for k,v in task_ids.items() if v==tid][0]
                results[label] = {"success":False, "error":data.get("error","?")}
            else:
                still.append(tid)
        pending = set(still)
        if pending:
            # plain ascii status
            pass

    for tid in pending:
        label = [k for k,v in task_ids.items() if v==tid][0]
        results[label] = {"success":False, "error":"TIMEOUT"}

    # Write raw JSON
    with open(os.path.join(BASE_DIR, "test_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    # Build report
    lines = ["# SaiFu Match Accuracy Test Report",
             f"Time: {time.strftime('%Y-%m-%d %H:%M')}",
             f"Profiles: {len(PROFILES)}",
             ""]

    # STEM keywords hardcoded in search.py
    STEM_KW = ["lanqiao","huawei","数学建模","计算机设计","电子设计","信息安全","软件","算法","CTF","服创","物联网","编程","人工智能","蓝桥杯","华为"]
    LIBERAL_KW = ["英语","翻译","写作","文学","演讲","辩论","广告","品牌","营销","商赛","欧莱雅","宝洁","联合利华","大广赛","设计","美术"]

    for label, result in results.items():
        lines.append(f"## {label}")
        major = PROFILES[label]["major"]

        if not result.get("success"):
            lines.append(f"- FAIL: {result.get('error')}")
            continue

        queries = result.get("search_queries_used", [])
        lines.append(f"- Search queries: {len(queries)}条")

        open_comps = result.get("open", [])
        lines.append(f"")
        lines.append(f"### Open competitions ({len(open_comps)} total):")

        stem_count = 0
        liberal_count = 0
        for i, comp in enumerate(open_comps[:10]):
            name = comp.get("name", "?")
            score = comp.get("match_score", "?")
            cat = comp.get("cat", "?")
            focus = comp.get("focus", "")
            reason = comp.get("match_reason", "")

            if any(kw in name for kw in STEM_KW):
                stem_count += 1
            if any(kw in name for kw in LIBERAL_KW):
                liberal_count += 1

            lines.append(f"{i+1}. [{score}分] {name}")
            lines.append(f"   Category: {cat} | Focus: {focus}")
            lines.append(f"   Reason: {reason}")

        # Analysis
        total = len(open_comps)
        lines.append(f"")
        lines.append(f"### Analysis for {label} ({major}):")
        lines.append(f"- STEM competitions: {stem_count}/{total} ({stem_count/total*100:.0f}%)" if total else "- No results")
        lines.append(f"- Liberal/Business competitions: {liberal_count}/{total} ({liberal_count/total*100:.0f}%)" if total else "")

        # Judge relevance
        is_liberal = any(kw in major for kw in ["文学","英语","历史","哲学","法学","政治","社会","教育","新闻","传播","艺术","设计","音乐","美术"])
        is_business = any(kw in major for kw in ["市场","营销","金融","会计","管理","经济","工商","国贸","商务"])
        is_medical = any(kw in major for kw in ["医学","临床","药学","护理","口腔","公卫"])

        if is_liberal and stem_count/total > 0.3 if total else False:
            lines.append(f"- *** DEVIATION: Liberal arts major getting {stem_count}/{total} STEM competitions ***")
        if is_business and stem_count/total > 0.3 if total else False:
            lines.append(f"- *** DEVIATION: Business major getting {stem_count}/{total} STEM competitions ***")
        if is_medical and liberal_count == 0:
            lines.append(f"- *** DEVIATION: Medical major getting no medical competitions ***")

        # Resources
        resources = result.get("resources", [])
        if resources:
            lines.append(f"")
            lines.append(f"### Resources ({len(resources)}):")
            for r in resources:
                lines.append(f"- {r.get('name','?')}")

        lines.append("")

    # Root cause
    lines.append("---")
    lines.append("## Root Cause Analysis")
    lines.append("")
    lines.append("`services/search.py` hardcodes 8 STEM competition queries:")
    lines.append("1. 蓝桥杯 2026 报名通知 官网")
    lines.append("2. 华为ICT大赛 2026 报名通知 官网")
    lines.append("3. 数学建模 2026 报名通知 官网")
    lines.append("4. 计算机设计大赛 2026 报名通知 官网")
    lines.append("5. 挑战杯 2026 报名通知 官网")
    lines.append("6. 互联网+ 2026 报名通知 官网")
    lines.append("7. 服创大赛 2026 报名通知 官网")
    lines.append("8. 信息安全竞赛 2026 报名通知 官网")
    lines.append("")
    lines.append("These are injected regardless of user's major. Search results become dominated by STEM content,")
    lines.append("and DeepSeek can only match from what it sees.")

    with open(os.path.join(BASE_DIR, "test_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("DONE. Results saved to test_results.json and test_report.md")

if __name__ == "__main__":
    main()
