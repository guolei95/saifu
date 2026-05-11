# -*- coding: utf-8 -*-
"""验证前端收集的画像数据是否完整传给 LLM"""
import sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from match.engine import _build_profile_text, _build_rules
from datetime import date

# 模拟前端 collectProfile() 实际收集的完整数据
profile = {
    'school': '华中科技大学', 'major': '软件工程', 'grade': '大二',
    'interests': 'AI/大模型、Web开发', 'skills': 'Python编程、React前端',
    'tech_directions': ['AI应用/大模型', 'Web前端', 'Web后端'],
    'tools': ['ChatGPT/Claude/Copilot等AI工具', 'Vue/React', 'Git'],
    'other_skills': '参加过数学建模校赛',
    'goals': ['保研加分', '丰富简历'],
    'time_commitment': '每周10-15小时',
    'available_months': '3月、4月、5月、7月、8月',
    'summer_winter': '是',
    'preference': '国家级', 'team_preference': '团队赛',
    'preferred_duration': '1-3个月', 'preferred_format': '线上提交',
    'fee_budget': '免费', 'language_pref': '只中文',
    'has_advisor': '没有指导老师', 'can_cross_school': '可以跨校',
    'avoid_types': '纯笔试/死记硬背型',
    'past_highest_award': '校级获奖',
    'representative_projects': ['用Python写了个校园二手交易平台'],
    'has_portfolio': True, 'portfolio_link': 'https://github.com/test',
    'has_lab': False, 'join_school_team': True, 'need_teammate': True,
    'min_award': '省级', 'ideal_goal': '国家级一等奖',
    'strategy': '兼顾含金量和概率',
}

text = _build_profile_text(profile)
rules = _build_rules(date.today().isoformat())

# 前端所有字段（来自 collectProfile）
frontend_fields = {
    'school': '基本信息-学校', 'major': '基本信息-专业', 'grade': '基本信息-年级',
    'interests': '基本信息-兴趣领域', 'skills': '专业能力-核心技能',
    'tech_directions': '专业能力-技能领域', 'tools': '专业能力-常用工具',
    'other_skills': '专业能力-补充说明', 'goals': '参赛目标',
    'time_commitment': '时间投入-每周可投入', 'available_months': '时间投入-空闲月份',
    'summer_winter': '时间投入-寒暑假', 'preference': '参赛偏好-赛事级别',
    'team_preference': '参赛偏好-个人/团队', 'preferred_duration': '参赛偏好-比赛周期',
    'preferred_format': '参赛偏好-比赛形式', 'fee_budget': '参赛偏好-报名费',
    'language_pref': '参赛偏好-语言', 'has_advisor': '参赛偏好-指导老师',
    'can_cross_school': '参赛偏好-跨校组队', 'avoid_types': '避免类型',
    'past_highest_award': '过往经历-最高获奖', 'representative_projects': '过往经历-项目',
    'has_portfolio': '过往经历-作品集', 'portfolio_link': '过往经历-作品集链接',
    'has_lab': '同校组队-实验室', 'join_school_team': '同校组队-加入团队',
    'need_teammate': '同校组队-需要队友', 'min_award': '期望获奖-最低',
    'ideal_goal': '期望获奖-理想', 'strategy': '期望获奖-策略',
}

results = []
for key, label in frontend_fields.items():
    val = profile.get(key, '')
    if isinstance(val, list):
        val_str = '、'.join(str(v) for v in val) if val else ''
    elif isinstance(val, bool):
        val_str = '有' if val else ('否' if key.startswith('has_') or key == 'join_school_team' else '否')
    elif isinstance(val, str):
        val_str = val
    else:
        val_str = str(val)

    in_text = val_str in text if val_str else '[空值]'
    results.append((label, key, val_str[:40], in_text))

# 输出
print('=' * 70)
print('前端字段 -> LLM 接收情况检查')
print('=' * 70)
present = 0
missing = 0
for label, key, val, status in results:
    if status == True:
        print(f'  [OK]  {label}  ->  "{val}"')
        present += 1
    elif status == '[空值]':
        print(f'  [EMPTY] {label}  (未填写)')
    else:
        print(f'  [MISS] {label} ({key})  ->  "{val}"  未传给LLM!')
        missing += 1

print()
print(f'总计: {present} 个字段已传, {missing} 个字段缺失, {len(results)-present-missing} 个为空')

# 规则检查
print()
print('=' * 70)
print('规则检查')
print('=' * 70)
print(f'  年级/时间评估框架: {"[OK] 存在" if "年级/时间合适度评估框架" in rules else "[MISS]"}')
print(f'  禁止待确认: {"[OK] 存在" if "禁止" in rules and "待确认" in rules else "[MISS]"}')
print(f'  空闲月份提示: {"[OK] 存在" if "空闲月份" in rules else "[MISS]"}')

# 输出结果文件
output = {
    'profile_text': text,
    'fields_present': present,
    'fields_missing': missing,
    'missing_fields': [label for label, key, val, status in results if status == False],
    'rules_have_grade_framework': '年级/时间合适度评估框架' in rules,
    'rules_ban_uncertain': ('禁止' in rules and '待确认' in rules),
}
with open(os.path.join(os.path.dirname(__file__), 'test_verify_result.json'), 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print()
print('详细结果已写入 test_verify_result.json')
