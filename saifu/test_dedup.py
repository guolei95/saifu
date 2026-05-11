"""测试去重效果 — 调用 /api/match 后检查是否有重复竞赛"""
import requests
import json
import time

PROFILES = {
    "文科-汉语言文学": {
        "school": "北京大学",
        "major": "汉语言文学",
        "grade": "大二",
        "interests": "写作 文学创作 文案",
        "goals": ["保研加分"],
    },
    "工科-计算机科学": {
        "school": "清华大学",
        "major": "计算机科学与技术",
        "grade": "大三",
        "interests": "编程 算法 AI",
        "goals": ["求职直通"],
    },
    "商科-市场营销": {
        "school": "复旦大学",
        "major": "市场营销",
        "grade": "大二",
        "interests": "品牌策划 市场分析",
        "goals": ["求职直通"],
    },
}

def normalize(name):
    """归一化名称"""
    import re
    n = name.lower().strip()
    n = re.sub(r'第[一二三四五六七八九十\d]+届', '', n)
    n = re.sub(r'[「」' '"''""（）()" "]', '', n)
    n = re.sub(r'[\d]{4}[\s\-_]*(?:[\d]{4})?', '', n)
    n = re.sub(r'(中国赛|全球赛|省赛|国赛|校赛|区域赛|选拔赛|决赛)$', '', n)
    n = re.sub(r'[\s\-_]+', '', n)
    return n.strip()

def check_duplicates(name, competitions):
    """在 competitions 列表中查找重复项"""
    comp_name = normalize(name)
    found = []
    for c in competitions:
        cn = normalize(c.get("name", ""))
        if cn == comp_name:
            found.append(c.get("name", ""))
    return found

for label, profile in PROFILES.items():
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    # 提交匹配任务
    resp = requests.post("http://localhost:8000/api/match", json=profile)
    if not resp.ok:
        print(f"  FAIL: {resp.status_code}")
        continue

    task_id = resp.json()["task_id"]
    print(f"  task_id: {task_id}")

    # 轮询直到完成
    for _ in range(30):
        time.sleep(2)
        r = requests.get(f"http://localhost:8000/api/match/{task_id}")
        data = r.json()
        if data["status"] == "done":
            result = data["result"]
            if not result.get("success"):
                print(f"  ERROR: {result.get('error')}")
                break

            open_list = result.get("open", [])

            # 检查重复
            seen = {}
            dupes = []
            for c in open_list:
                norm = normalize(c.get("name", ""))
                if norm in seen:
                    dupes.append((seen[norm], c.get("name", "")))
                else:
                    seen[norm] = c.get("name", "")

            print(f"  推荐竞赛: {len(open_list)}个")

            if dupes:
                print(f"  [重复] {len(dupes)} 组重复:")
                for a, b in dupes:
                    print(f"    - {a}")
                    print(f"    - {b}")
                    print()
            else:
                print(f"  [通过] 没有重复竞赛!")

            # 列出所有推荐
            for i, c in enumerate(open_list, 1):
                score = c.get("match_score", "?")
                name = c.get("name", "?")
                print(f"    {i}. [{score}] {name}")

            break
        elif data["status"] == "error":
            print(f"  ERROR: {data.get('error')}")
            break
        else:
            print(f"  ...{data['status']}")

    print()

print("Done!")
