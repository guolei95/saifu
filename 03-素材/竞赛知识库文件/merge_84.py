# -*- coding: utf-8 -*-
import json, re, openpyxl, os

# Switch to the script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Load DOCX extracted text
docx_data = []
with open('_docx_extracted.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or '--' in line[:5] or '序 |' in line or '序号' in line:
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 3:
            docx_data.append({'seq': parts[0], 'name': parts[1], 'url': parts[2] if len(parts) > 2 else ''})

print(f'DOCX entries: {len(docx_data)}')

# Load XLSX
xlsx_files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
xlsx_path = xlsx_files[0]
wb = openpyxl.load_workbook(xlsx_path)
ws = wb.active
xlsx_data = []

for row in ws.iter_rows(min_row=4, values_only=True):
    if row[0] is None or row[1] is None:
        continue
    vals = [str(c).strip() if c else '' for c in row[:7]]
    # Skip notes row
    if vals[0].startswith('注'):
        break
    xlsx_data.append({
        'seq': vals[0], 'name': vals[1],
        'timing': vals[2], 'format': vals[3],
        'work_type': vals[4], 'side_events': vals[5],
        'requirements': vals[6]
    })

print(f'XLSX entries: {len(xlsx_data)}')

# Normalize: only keep alphanumeric + Chinese chars
def norm(name):
    n = re.sub(r'[（\(][^）\)]*[）\)]', '', name)
    n = re.sub(r'[^A-Za-z0-9一-鿿]', '', n)
    return n

# Match DOCX to XLSX
matched = set()
merged = []

for d in docx_data:
    dn = norm(d['name'])
    best_xi = None
    best_score = 0

    for xi, x in enumerate(xlsx_data):
        if xi in matched:
            continue
        xn = norm(x['name'])
        if dn == xn:
            best_xi = xi; best_score = 100; break
        common = sum(1 for c in dn if c in xn)
        if max(len(dn), len(xn)) > 0:
            score = common / max(len(dn), len(xn)) * 100
            if score > 60 and score > best_score:
                best_score = score; best_xi = xi

    sid = int(d['seq']) if d['seq'].isdigit() else 999
    entry = {'id': sid, 'name': d['name'], 'url': d['url'],
             'timing': '', 'format': '', 'work_type': '',
             'side_events': '', 'requirements': '', 'source': 'docx'}

    if best_xi is not None and best_score >= 70:
        x = xlsx_data[best_xi]
        for field in ('timing', 'format', 'work_type', 'side_events', 'requirements'):
            v = x[field]
            entry[field] = v if v and v != 'None' else ''
        entry['source'] = 'both'
        matched.add(best_xi)

    merged.append(entry)

# Add unmatched XLSX entries
for xi, x in enumerate(xlsx_data):
    if xi in matched:
        continue
    nums = re.findall(r'\d+', norm(x['seq']))
    sid = int(nums[0]) if nums else 999
    entry = {'id': sid, 'name': x['name'], 'url': '',
             'timing': x['timing'] if x['timing'] != 'None' else '',
             'format': x['format'] if x['format'] != 'None' else '',
             'work_type': x['work_type'] if x['work_type'] != 'None' else '',
             'side_events': x['side_events'] if x['side_events'] != 'None' else '',
             'requirements': x['requirements'] if x['requirements'] != 'None' else '',
             'source': 'xlsx'}
    merged.append(entry)

merged.sort(key=lambda e: e['id'])

both_n = sum(1 for e in merged if e['source'] == 'both')
docx_n = sum(1 for e in merged if e['source'] == 'docx')
xlsx_n = sum(1 for e in merged if e['source'] == 'xlsx')
print(f'Total: {len(merged)} | Both: {both_n} | DOCX-only: {docx_n} | XLSX-only: {xlsx_n}')

# Save JSON
output = '84项A类竞赛知识库.json'
with open(output, 'w', encoding='utf-8') as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
print(f'Saved: {output} ({len(json.dumps(merged, ensure_ascii=False, indent=2))} chars)')
