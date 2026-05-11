#!/usr/bin/env python3
"""
竞赛选赛助手 V1 - CLI
输入你的学校/专业/年级/兴趣 → 输出 Top5 匹配竞赛

用法:
  python match_competitions.py --school "湖北师范大学文理学院" --major "网络工程" --grade "大一" --interests "AI/编程"

依赖:
  pip install tavily-python openai
"""

import os
import json
import argparse
import sys

# Windows 终端 UTF-8 修复
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# 配置
# ============================================================
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")


def check_config():
    """检查配置是否完整"""
    errors = []
    if not TAVILY_API_KEY:
        errors.append("❌ 缺少 TAVILY_API_KEY 环境变量")
    if not DEEPSEEK_API_KEY:
        errors.append("❌ 缺少 DEEPSEEK_API_KEY 环境变量")
    if errors:
        print("\n".join(errors))
        print("\n设置方法:")
        print('  set TAVILY_API_KEY=你的Tavily密钥')
        print('  set DEEPSEEK_API_KEY=你的DeepSeek密钥')
        print("\n或者编辑 run_match.bat 填入 Key")
        sys.exit(1)


# ============================================================
# 第一步：根据用户画像生成搜索关键词
# ============================================================
def generate_search_queries(profile: dict) -> list[str]:
    school = profile.get("school", "")
    major = profile.get("major", "")
    grade = profile.get("grade", "")
    interests = profile.get("interests", "")
    requirements = profile.get("requirements", "")

    queries = []

    # 按专业搜
    if major:
        queries.append(f"2026年 大学生 {major} 学科竞赛 报名通知")

    # 按兴趣搜
    if interests:
        queries.append(f"2026年 大学生 {interests} 竞赛 报名")

    # 学校相关通知
    if school:
        queries.append(f"{school} 竞赛通知 2026")

    # 通用高价值竞赛
    queries.append("全国大学生 学科竞赛 排行榜 2026 报名时间")
    queries.append("2026年 大学生 创新创业 竞赛 通知")

    # 按年级适配
    if grade in ["大一", "大二"]:
        queries.append("适合低年级 大学生 竞赛 零基础 2026")
    elif grade in ["大三", "大四"]:
        queries.append("大学生 竞赛 保研加分 2026")

    # 用户特殊要求
    if requirements:
        queries.append(f"{requirements} 大学生竞赛 2026")

    return queries


# ============================================================
# 第二步：用 Tavily 搜索
# ============================================================
def search_competitions(queries: list[str]) -> list[dict]:
    from tavily import TavilyClient

    tavily = TavilyClient(api_key=TAVILY_API_KEY)
    all_results = []

    for query in queries:
        try:
            response = tavily.search(
                query=query,
                search_depth="advanced",
                max_results=10,
                include_raw_content=False,
            )
            results = response.get("results", [])
            all_results.extend(results)
            print(f"  ✅ [{query[:40]}...] → {len(results)}条")
        except Exception as e:
            print(f"  ⚠️  [{query[:40]}...] 失败: {e}")

    # 去重
    seen = set()
    unique = []
    for r in all_results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    return unique


# ============================================================
# 第三步：用 LLM 提取结构化信息 + 匹配打分
# ============================================================
def _call_llm(system_prompt: str) -> list[dict]:
    """调一次 LLM，返回竞赛列表"""
    from openai import OpenAI

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": system_prompt}],
        temperature=0.3,
        max_tokens=8192,
    )
    result_text = response.choices[0].message.content.strip()

    # 清理 markdown 包裹
    if result_text.startswith("```"):
        lines = result_text.split("\n")
        result_text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # 清洗不可见字符
    result_text = result_text.encode("utf-8", "ignore").decode("utf-8")
    result_text = "".join(c for c in result_text if c.isprintable() or c in "\n\r\t ")

    # 尝试修复截断的 JSON（中转站输出限制）
    import re

    # 先试直接解析
    try:
        result = json.loads(result_text)
        if isinstance(result, list):
            return result
    except Exception:
        pass

    # 修复策略：截断到最后一个完整的 JSON 对象，然后补 ]
    # 1. 补 ]
    try:
        result = json.loads(result_text.rstrip().rstrip(",") + "\n]")
        if isinstance(result, list):
            return result
    except Exception:
        pass

    # 2. 截断到最后一个 }, 或 }\n 处
    matches = list(re.finditer(r'\}\s*,?\s*(?=\n|$)', result_text))
    if matches:
        cut = matches[-1].end()
        try:
            result = json.loads(result_text[:cut].rstrip().rstrip(",") + "\n]")
            if isinstance(result, list):
                return result
        except Exception:
            pass

    # 3. 截断到最后一个 } 处
    last_brace = result_text.rfind("}")
    if last_brace > 0:
        try:
            result = json.loads(result_text[:last_brace+1].rstrip().rstrip(",") + "\n]")
            if isinstance(result, list):
                return result
        except Exception:
            pass

    # 全部失败 — 直接看 json.loads 报什么
    try:
        json.loads(result_text)
    except Exception as e:
        print(f"⚠️  JSON解析失败: {e}")
        print(f"   错误位置附近: {repr(result_text[max(0,getattr(e,'pos',0)-20):getattr(e,'pos',0)+20])}")
    return []


def match_and_rank(profile: dict, search_results: list[dict]) -> dict:
    """分两次调用 LLM，返回 {"open": [...], "closed": [...]}"""
    from datetime import date
    today = date.today().isoformat()

    # 准备搜索结果文本（限制20条，减少输出压力）
    results_text = ""
    for i, r in enumerate(search_results[:20]):
        title = r.get("title", "")
        url = r.get("url", "")
        content = (r.get("content") or "")[:200]
        results_text += f"[{i+1}] {title}\n    URL: {url}\n    {content}\n\n"

    profile_text = f"""- 学校: {profile.get('school', '未知')}
- 专业: {profile.get('major', '未知')}
- 年级: {profile.get('grade', '未知')}
- 兴趣/技能: {profile.get('interests', '不限')}
- 特殊要求: {profile.get('requirements', '无')}"""

    json_template = """{"n":"竞赛全称","s":85,"r":"理由(20字)","f":"个人/团队","url":"链接","dl":"截止日期","mj":"专业","cs":true,"pt":"个人/团队/均可","fr":true,"fee":"免费或金额","note":"备注(30字)","src":"来源URL","st":"官方/非官方"}"""

    common_rules = f"""当前日期: {today}
规则:
1. s(匹配度) = 专业匹配(30) + 年级合适(20) + 兴趣匹配(30) + 可操作(20)
2. 未知信息写"未知"
3. 最多3条，不足不凑。每条压缩在300字符内
4. src 必须来自搜索结果中的实际URL
5. st: .edu.cn/政府/学校域名标"官方"，其他标"非官方"
6. fr: 免费true收费false；fee写"免费"或金额如"300元/人"
7. 必须只输出 JSON 数组，不要任何其他文字
8. JSON字段: n=名称 s=分数 r=理由 f=报名方式 url=报名链接 dl=截止日期 mj=适合专业 cs=跨校(pt:布尔) pt=参赛形式 fr=免费(fr:布尔) fee=费用 note=备注 src=来源URL st=来源类型
9. ⚠️ 竞赛名称中如有引号，必须用「」代替，绝不能用双引号"！否则JSON会断裂"""

    # 第一次：报名中的
    open_prompt = f"""你是大学生竞赛匹配助手。找出报名截止日期在 {today} 之后（含今天）或尚未公布、适合这个学生的竞赛。

{profile_text}

## 搜索结果
{results_text}

## 输出格式
[{json_template}]

## 筛选条件
报名截止日期 >= {today} 或未知（尚未公布）

{common_rules}"""

    # 第二次：已截止的
    closed_prompt = f"""你是大学生竞赛匹配助手。找出报名已截止、但值得这个学生关注的竞赛（供明年规划参考）。

{profile_text}

## 搜索结果
{results_text}

## 输出格式
[{json_template}]
registration_deadline 字段末尾加"（已截止）"

## 筛选条件
dl(报名截止日期) < {today}，已过期但值得明年参加。dl末尾加"（已截止）"

{common_rules}"""

    print("   🤖 正在匹配「报名中」的竞赛...")
    open_list = _call_llm(open_prompt)

    print("   🤖 正在匹配「已截止」的竞赛...")
    closed_list = _call_llm(closed_prompt)

    return {"open": open_list, "closed": closed_list}


# ============================================================
# 输出格式化
# ============================================================
def print_one(m, i, label=""):
    """打印单条竞赛信息"""
    score = m.get("s", m.get("match_score", 0))
    stars = "⭐" * min(5, score // 20)
    source_type = m.get("st", m.get("source_type", "未知"))
    source_label = "🏛️ 官方" if "官方" in source_type else "⚠️ 非官方"
    is_free = m.get("fr", m.get("is_free", True))
    fee = m.get("fee", m.get("fee_amount", "未知"))
    fee_label = "🆓 免费" if is_free or fee == "免费" else f"💰 {fee}"
    participation = m.get("pt", m.get("participation_type", m.get("registration_form", "未知")))
    if "个人" in str(participation) and "团队" not in str(participation):
        team_label = "🧑 仅个人参赛"
    elif "团队" in str(participation) and "个人" not in str(participation):
        team_label = "👥 仅团队"
    elif "均" in str(participation):
        team_label = "🧑/👥 均可"
    else:
        team_label = str(participation)

    print(f"""
┌{'─' * 58}┐
│ {label}{m.get('n', m.get('name', '未知'))[:50]}
├{'─' * 58}┤
│ 匹配度: {stars} ({score}分)
│ 理由:   {m.get('r', m.get('match_reason', '无'))}
│ 参赛形式: {team_label}
│ 报名:   {m.get('f', m.get('registration_form', '未知'))}
│ 截止:   {m.get('dl', m.get('registration_deadline', '未知'))}
│ 费用:   {fee_label}
│ 适合:   {m.get('mj', m.get('suitable_majors', '未知'))}
│ 跨校:   {'✅ 可以' if m.get('cs', m.get('cross_school_allowed')) else '❌ 不可以'}
│ 来源类型: {source_label}
│ 备注:   {m.get('note', m.get('notes', '无'))}
│ 来源:   {m.get('src', m.get('source_url', '无'))[:55]}
└{'─' * 58}┘""")


def print_results(data: dict):
    open_list = data.get("open", [])
    closed_list = data.get("closed", [])

    if not open_list and not closed_list:
        print("\n😔 没有找到高度匹配的竞赛。")
        print("   建议：放宽搜索条件，换个关键词试试。")
        return

    # 报名中的
    if open_list:
        print("\n" + "━" * 60)
        print("  🟢 正在报名中 / 即将开始报名")
        print("━" * 60)
        for i, m in enumerate(open_list, 1):
            print_one(m, i, f"Top {i}: ")

    # 已截止的
    if closed_list:
        print("\n" + "━" * 60)
        print("  🔴 今年已截止（可提前规划，明年再战）")
        print("━" * 60)
        for i, m in enumerate(closed_list, 1):
            print_one(m, i, f"Top {i}: ")


# ============================================================
# 主流程
# ============================================================
def main():
    check_config()

    parser = argparse.ArgumentParser(
        description="竞赛选赛助手 - 找到适合你的比赛",
        epilog="示例: python match_competitions.py --school 湖北师范大学文理学院 --major 网络工程 --grade 大一 --interests AI"
    )
    parser.add_argument("--school", required=True, help="学校全称")
    parser.add_argument("--major", required=True, help="专业名称")
    parser.add_argument("--grade", required=True, help="年级（大一/大二/大三/大四/研一...）")
    parser.add_argument("--interests", default="", help="兴趣技能，逗号分隔（如: AI,编程,设计）")
    parser.add_argument("--requirements", default="", help="特殊要求（如: 只要国家级, 可跨校组队）")

    args = parser.parse_args()

    profile = {
        "school": args.school,
        "major": args.major,
        "grade": args.grade,
        "interests": args.interests,
        "requirements": args.requirements,
    }

    print("""
╔══════════════════════════════════════════════════════════╗
║           🔍 竞赛选赛助手 V1                            ║
║           输入画像 → 搜索 → AI匹配 → 输出清单            ║
╚══════════════════════════════════════════════════════════╝
""")
    print(f"👤 {profile['school']} | {profile['major']} | {profile['grade']}")
    if profile["interests"]:
        print(f"🎯 兴趣: {profile['interests']}")
    if profile["requirements"]:
        print(f"📋 要求: {profile['requirements']}")

    # 1. 生成搜索词
    print("\n📋 第一步：生成搜索关键词...")
    queries = generate_search_queries(profile)
    for q in queries:
        print(f"   → {q}")

    # 2. 搜索
    print(f"\n🌐 第二步：搜索竞赛信息（{len(queries)}条查询）...")
    results = search_competitions(queries)
    print(f"\n   📊 去重后共 {len(results)} 条结果")

    if not results:
        print("❌ 没有搜到结果。检查网络或 API Key。")
        return

    # 3. LLM匹配
    print("\n🧠 第三步：AI 匹配中（约10-20秒）...")
    data = match_and_rank(profile, results)

    # 4. 输出
    print("\n" + "=" * 60)
    print("                    📊 匹配结果")
    print("=" * 60)
    print_results(data)

    print("💡 信息来自网络搜索，报名前请到官网核实！")


if __name__ == "__main__":
    main()
