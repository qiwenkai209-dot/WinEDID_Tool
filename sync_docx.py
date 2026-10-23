# -*- coding: utf-8 -*-
import zipfile
import xml.etree.ElementTree as ET
import json
import re
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

script_dir = os.path.dirname(os.path.abspath(__file__))
docx_path = os.path.join(script_dir, "多媒体工程师全栈手册.docx")
html_path = os.path.join(script_dir, "多媒体工程师全栈手册_查询系统.html")

DATA_START = "<!-- === ANTIGRAVITY_MANUAL_DATA_START === -->"
DATA_END = "<!-- === ANTIGRAVITY_MANUAL_DATA_END === -->"

if not os.path.exists(docx_path):
    print(f"错误: 未找到 Word 文档: {docx_path}")
    sys.exit(1)

if not os.path.exists(html_path):
    print(f"错误: 未找到目标 HTML 文件: {html_path}")
    sys.exit(1)

print(f"正在读取并解析: {docx_path} ...")
z = zipfile.ZipFile(docx_path)
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
root = ET.fromstring(z.read('word/document.xml'))
body = root.find('w:body', ns)

raw_blocks = []
for child in body:
    tag = child.tag.split('}')[-1]
    if tag == 'p':
        runs = child.findall('.//w:r', ns)
        texts = []
        is_bold = False
        max_sz = 0
        for r in runs:
            rPr = r.find('w:rPr', ns)
            if rPr is not None:
                if rPr.find('w:b', ns) is not None:
                    is_bold = True
                sz = rPr.find('w:sz', ns)
                if sz is not None:
                    try:
                        v = int(sz.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '0'))
                        if v > max_sz: max_sz = v
                    except:
                        pass
            t = ''.join([elem.text for elem in r.findall('.//w:t', ns) if elem.text])
            texts.append(t)
        full_text = ''.join(texts).strip()
        if full_text:
            raw_blocks.append({'type': 'p', 'text': full_text, 'bold': is_bold, 'sz': max_sz})
    elif tag == 'tbl':
        rows = child.findall('.//w:tr', ns)
        table_matrix = []
        for r in rows:
            row_cells = []
            for c in r.findall('.//w:tc', ns):
                paras = c.findall('.//w:p', ns)
                lines = [''.join([t.text for t in p.findall('.//w:t', ns) if t.text]).strip() for p in paras]
                row_cells.append('\n'.join([l for l in lines if l]))
            table_matrix.append(row_cells)
        raw_blocks.append({'type': 'table', 'data': table_matrix})

chapters = []
curr_ch = {'id': 'ch_0', 'title': '多媒体工程师全栈手册 · 导读与总则', 'level': 1, 'sections': []}
chapters.append(curr_ch)
curr_sec = {'id': 'sec_0_0', 'title': '通用说明与执行原则', 'level': 2, 'blocks': []}
curr_ch['sections'].append(curr_sec)
ch_idx, sec_idx = 0, 0

for b in raw_blocks:
    if b['type'] == 'p':
        txt, sz, bold = b['text'], b['sz'], b['bold']
        if sz == 52:
            curr_sec['blocks'].append(b)
            continue
        is_major = (sz == 36) or (sz >= 32 and (re.match(r'^(?:[0-9]{1,2}|[0-9]{1,2}-[A-Z])[\.\s].+', txt) or txt.startswith('附录：')) and not re.match(r'^(?:[0-9]{1,2}\.[0-9]{1,2}|附录\s*[A-Z])', txt))
        if is_major:
            ch_idx += 1
            sec_idx = 0
            curr_ch = {'id': f'ch_{ch_idx}', 'title': txt, 'level': 1, 'sections': []}
            chapters.append(curr_ch)
            curr_sec = {'id': f'sec_{ch_idx}_{sec_idx}', 'title': '引言与核心要点', 'level': 2, 'blocks': []}
            curr_ch['sections'].append(curr_sec)
            continue
        is_sub = (sz == 32 and bold) or (sz >= 30 and re.match(r'^(?:[0-9]{1,2}\.[0-9]{1,2}|[0-9]{1,2}-[A-Z]\.[0-9]{1,2}|附录\s*[A-Z])[\.\s:].+', txt))
        if is_sub:
            sec_idx += 1
            curr_sec = {'id': f'sec_{ch_idx}_{sec_idx}', 'title': txt, 'level': 2, 'blocks': []}
            curr_ch['sections'].append(curr_sec)
            continue
        curr_sec['blocks'].append(b)
    else:
        curr_sec['blocks'].append(b)

for ch in chapters:
    ch['sections'] = [s for s in ch['sections'] if s['blocks'] or s['title'] != '引言与核心要点']

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_data_block = f"{DATA_START}\n  <script id=\"inlined-manual-data\">\n    window.INITIAL_MANUAL_DATA = {json.dumps(chapters, ensure_ascii=False)};\n  </script>\n  {DATA_END}"

if DATA_START in content and DATA_END in content:
    start_i = content.find(DATA_START)
    end_i = content.find(DATA_END) + len(DATA_END)
    new_content = content[:start_i] + new_data_block + content[end_i:]
else:
    pattern = r'window\.INITIAL_MANUAL_DATA\s*=\s*[\s\S]*?;\s*<\/script>'
    new_content = re.sub(pattern, lambda m: f'window.INITIAL_MANUAL_DATA = {json.dumps(chapters, ensure_ascii=False)};\n  </script>', content, count=1)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

total_tbl = sum(len([b for b in s['blocks'] if b['type'] == 'table']) for ch in chapters for s in ch['sections'])
print(f"成功！已将最新 Word 内容全量同步并固化到 HTML 程序中！")
print(f"统计：共写入 {len(chapters)} 个大章节、{sum(len(c['sections']) for c in chapters)} 个小节、{total_tbl} 个工程表格。")
print(f"提示：HTML 程序已自包含最新数据，外部 Word 文档已可安全归档或删除！")
