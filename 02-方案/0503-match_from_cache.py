#!/usr/bin/env python3
"""用缓存的搜索结果 + DeepSeek API 进行竞赛匹配"""
import json, os, sys
from datetime import date
from openai import OpenAI

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

def call_llm(system_prompt: str) -> list:
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": system_prompt}],
        temperature=0.3, max_tokens=8192,
    )
    text = resp.choices[0].message.content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    text = text.encode("utf-8", "ignore").decode("utf-8")
    text = "".join(c for c in text if c.isprintable() or c in "\n\r\t ")

    # Multiple recovery strategies
    strategies = [
        text,
        text.rstrip().rstrip(",") + "\n]",
    ]
    # try cutting at last }, }
    for pattern in [r'\}\s*,?\s*\n', r'\}']:
        import re
        matches = list(re.finditer(pattern, text))
        if matches:
            strategies.append(text[:matches[-1].end()].rstrip().rstrip(",") + "\n]")
    last_brace = text.rfind("}")
    if last_brace > 0:
        strategies.append(text[:last_brace+1].rstrip().rstrip(",") + "\n]")

    for s in strategies:
        try:
            result = json.loads(s)
            if isinstance(result, list):
                return result
        except:
            pass
    return []

def match_major(major: str, profile: dict, results: list, extra_results: list) -> dict:
    today = date.today().isoformat()

    all_results = results + extra_results
    results_text = ""
    for i, r in enumerate(all_results[:25]):
        results_text += f"[{i+1}] {r['title']}\n    URL: {r['url']}\n    {r['content'][:250]}\n\n"

    profile_text = f"""- 学校: {profile.get('school','未知')}
- 专业: {profile.get('major','未知')}
- 年级: {profile.get('grade','未知')}
- 兴趣/技能: {profile.get('interests','不限')}
- 特殊要求: {profile.get('requirements','无')}"""

    json_tpl = """{"n":"竞赛全称","s":85,"r":"理由(20字)","f":"个人/团队","url":"链接","dl":"截止日期","mj":"专业","cs":true,"pt":"个人/团队/均可","fr":true,"fee":"免费或金额","note":"备注(30字)","src":"来源URL","st":"官方/非官方"}"""

    rules = f"""当前日期: {today}
规则:
1. s(匹配度) = 专业匹配(30) + 年级合适(20) + 兴趣匹配(30) + 可操作(20)
2. 未知信息写"未知"
3. 最多4条「报名中」和2条「已截止」，每条压缩在300字符内
4. src必须来自搜索结果中的实际URL
5. st: .edu.cn/政府/学校域名标"官方"，其他标"非官方"
6. fr: 免费true收费false；fee写"免费"或金额
7. 必须只输出JSON数组，不要其他文字
8. 竞赛名称中如有引号必须用「」代替，绝不能用双引号"
9. fee字段: 有具体金额写金额（如"300元/人""49元/人""免费"），搜索结果中提到收费的一定要写出来"""

    open_prompt = f"""你是大学生竞赛匹配助手。找出报名截止日期在{today}之后或尚未公布、适合这个学生的竞赛。

{profile_text}

## 搜索结果
{results_text}

## 输出格式
[{json_tpl}]

## 筛选条件
报名截止日期 >= {today} 或未知（尚未公布），最多4条。
{rules}"""

    closed_prompt = f"""你是大学生竞赛匹配助手。找出报名已截止但值得关注的竞赛（供明年规划参考）。

{profile_text}

## 搜索结果
{results_text}

## 输出格式
[{json_tpl}]

## 筛选条件
dl(报名截止日期) < {today}，已过期但值得明年参加。dl末尾加"（已截止）"。最多2条。
{rules}"""

    print(f"   🤖 匹配「{major}」报名中...")
    open_list = call_llm(open_prompt)
    print(f"   🤖 匹配「{major}」已截止...")
    closed_list = call_llm(closed_prompt)
    return {"open": open_list, "closed": closed_list}


def print_one(m, i, label=""):
    score = m.get("s", 0)
    stars = "⭐" * min(5, int(score) // 20)
    st = m.get("st", "未知")
    source_label = "🏛️ 官方" if "官方" in str(st) else "⚠️ 非官方"
    is_free = m.get("fr", True)
    fee = m.get("fee", "未知")
    fee_label = "🆓 免费" if (is_free and fee in ["免费","未知"]) else f"💰 {fee}"
    pt = m.get("pt", "未知")
    if "个人" in str(pt) and "团队" not in str(pt): team_label = "🧑 仅个人参赛"
    elif "团队" in str(pt) and "个人" not in str(pt): team_label = "👥 仅团队"
    elif "均" in str(pt): team_label = "🧑/👥 均可"
    else: team_label = str(pt)

    print(f"""
┌{'─'*58}┐
│ {label}{m.get('n','未知')[:50]}
├{'─'*58}┤
│ 匹配度: {stars} ({score}分)
│ 理由:   {m.get('r','无')}
│ 参赛形式: {team_label}
│ 报名:   {m.get('f','未知')}
│ 截止:   {m.get('dl','未知')}
│ 费用:   {fee_label}
│ 适合:   {m.get('mj','未知')}
│ 跨校:   {'✅ 可以' if m.get('cs') else '❌ 不可以'}
│ 来源类型: {source_label}
│ 备注:   {m.get('note','无')}
│ 来源:   {m.get('src','无')[:55]}
└{'─'*58}┘""")


def print_results(data: dict, major: str):
    print(f"\n{'='*60}")
    print(f"  📊 {major}专业 匹配结果")
    print(f"{'='*60}")

    open_list = data.get("open", [])
    closed_list = data.get("closed", [])

    if open_list:
        print("\n" + "━"*60)
        print("  🟢 正在报名中 / 即将开始报名")
        print("━"*60)
        for i, m in enumerate(open_list, 1):
            print_one(m, i, f"Top {i}: ")

    if closed_list:
        print("\n" + "━"*60)
        print("  🔴 今年已截止（可提前规划，明年再战）")
        print("━"*60)
        for i, m in enumerate(closed_list, 1):
            print_one(m, i, f"Top {i}: ")

    if not open_list and not closed_list:
        print("\n😔 没有找到高度匹配的竞赛。")


def main():
    if not DEEPSEEK_API_KEY:
        print("❌ 缺少 DEEPSEEK_API_KEY")
        sys.exit(1)

    # Load cached results
    with open("D:/.claude/search_results_cache.json", "r", encoding="utf-8") as f:
        cache = json.load(f)

    general = cache.get("通用竞赛", [])

    profiles = [
        {"school": "湖北师范大学文理学院", "major": "会计学", "grade": "大一", "interests": "财经,数据分析", "requirements": "", "cache_key": "会计学"},
        {"school": "湖北师范大学文理学院", "major": "汉语言文学", "grade": "大一", "interests": "写作,阅读", "requirements": "", "cache_key": "汉语言文学"},
        {"school": "湖北师范大学文理学院", "major": "经济学", "grade": "大一", "interests": "金融,数据分析", "requirements": "", "cache_key": "经济学"},
        {"school": "湖北师范大学文理学院", "major": "英语", "grade": "大一", "interests": "英语写作,翻译", "requirements": "", "cache_key": "英语"},
        {"school": "湖北师范大学文理学院", "major": "法学", "grade": "大一", "interests": "法律研究,辩论", "requirements": "", "cache_key": "法学"},
        {"school": "湖北师范大学文理学院", "major": "土木工程", "grade": "大一", "interests": "结构设计,BIM", "requirements": "", "cache_key": "土木工程"},
    ]

    print("""
╔══════════════════════════════════════════════════════════╗
║     竞赛选赛助手 — 批量测试（缓存+DeepSeek）            ║
╚══════════════════════════════════════════════════════════╝
""")

    all_results = {}
    for p in profiles:
        key = p["cache_key"]
        major_results = cache.get(key, [])
        print(f"\n🧠 正在分析「{p['major']}」专业...")
        data = match_major(p["major"], p, major_results, general)
        all_results[key] = data
        print_results(data, p["major"])

    # Save raw results
    with open("D:/.claude/all_match_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 完整结果已保存至 D:/.claude/all_match_results.json")
    print("💡 信息来自网络搜索，报名前请到官网核实！")


if __name__ == "__main__":
    main()
