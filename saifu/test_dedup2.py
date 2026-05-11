"""Test dedup - write results to JSON file"""
import requests, json, time, re, os

def normalize(name):
    n = name.lower().strip()
    n = re.sub(r'[第][一-九十\d]+[届]', '', n)
    n = re.sub(r'[「」『』"（）()" "]', '', n)
    n = re.sub(r'[\d]{4}[\s\-_]*(?:[\d]{4})?', '', n)
    n = re.sub(r'(中国赛|全球赛|省赛|国赛|校赛|区域赛|选拔赛|决赛)$', '', n)
    n = re.sub(r'[\s\-_]+', '', n)
    return n.strip()

PROFILES = {
    "文科-汉语言文学": {"school": "北京大学", "major": "汉语言文学", "grade": "大二", "interests": "写作 文学创作 文案", "goals": ["保研加分"]},
    "工科-计算机科学": {"school": "清华大学", "major": "计算机科学与技术", "grade": "大三", "interests": "编程 算法 AI", "goals": ["求职直通"]},
    "商科-市场营销": {"school": "复旦大学", "major": "市场营销", "grade": "大二", "interests": "品牌策划 市场分析", "goals": ["求职直通"]},
}

results = {}

for label, profile in PROFILES.items():
    print(f"[{label}] Submitting...", flush=True)

    resp = requests.post("http://localhost:8000/api/match", json=profile, timeout=10)
    if not resp.ok:
        results[label] = {"error": f"HTTP {resp.status_code}"}
        continue

    task_id = resp.json()["task_id"]

    for i in range(90):
        time.sleep(2)
        r = requests.get(f"http://localhost:8000/api/match/{task_id}", timeout=10)
        data = r.json()
        if data["status"] == "done":
            open_list = data["result"].get("open", [])

            seen = {}
            dupes = []
            for c in open_list:
                norm = normalize(c.get("name", ""))
                if norm in seen:
                    dupes.append({"dup_a": seen[norm], "dup_b": c.get("name", "")})
                else:
                    seen[norm] = c.get("name", "")

            results[label] = {
                "total": len(open_list),
                "duplicate_groups": len(dupes),
                "duplicates": dupes,
                "competitions": [{"score": c.get("match_score"), "name": c.get("name")} for c in open_list],
            }
            print(f"[{label}] Done - {len(open_list)} items, {len(dupes)} duplicate groups", flush=True)
            break
        elif data["status"] == "error":
            results[label] = {"error": data.get("error")}
            print(f"[{label}] Error: {data.get('error')}", flush=True)
            break
    else:
        results[label] = {"error": "timeout after 3min"}
        print(f"[{label}] Timeout", flush=True)

out_path = r"D:\我的竞赛项目-AI赋能竞赛系统\saifu\dedup_results.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nResults saved to: {out_path}")
