# -*- coding: utf-8 -*-
import http.server
import socketserver
import json
import re
import os
import sys
import time
import threading
import zipfile
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')

script_dir = os.path.dirname(os.path.abspath(__file__))
docx_name = "多媒体工程师全栈手册.docx"
html_name = "多媒体工程师全栈手册_查询系统.html"
docx_path = os.path.join(script_dir, docx_name)
html_path = os.path.join(script_dir, html_name)
PORT = 8899

DATA_START = "<!-- === ANTIGRAVITY_MANUAL_DATA_START === -->"
DATA_END = "<!-- === ANTIGRAVITY_MANUAL_DATA_END === -->"

def parse_docx_file(file_path):
    if not os.path.exists(file_path):
        return None
    z = zipfile.ZipFile(file_path)
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
                    if rPr.find('w:b', ns) is not None: is_bold = True
                    sz = rPr.find('w:sz', ns)
                    if sz is not None:
                        try:
                            v = int(sz.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '0'))
                            if v > max_sz: max_sz = v
                        except: pass
                t = ''.join([elem.text for elem in r.findall('.//w:t', ns) if elem.text])
                texts.append(t)
            full_text = ''.join(texts).strip()
            if full_text: raw_blocks.append({'type': 'p', 'text': full_text, 'bold': is_bold, 'sz': max_sz})
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

    return chapters

def save_chapters_to_html(chapters=None, quote_data=None, quote_db=None):
    if not os.path.exists(html_path):
        return False, "HTML文件不存在"
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if chapters:
            new_data_block = f"{DATA_START}\n  <script id=\"inlined-manual-data\">\n    window.INITIAL_MANUAL_DATA = {json.dumps(chapters, ensure_ascii=False)};\n  </script>\n  {DATA_END}"
            if DATA_START in content and DATA_END in content:
                start_i = content.find(DATA_START)
                end_i = content.find(DATA_END) + len(DATA_END)
                content = content[:start_i] + new_data_block + content[end_i:]

        if quote_data:
            pattern = r'window\.INITIAL_QUOTE_DATA\s*=\s*[\s\S]*?;\s*<\/script>'
            replacement = f'window.INITIAL_QUOTE_DATA = {json.dumps(quote_data, ensure_ascii=False)};\n  </script>'
            content = re.sub(pattern, lambda m: replacement, content, count=1)

        if quote_db:
            pattern_db = r'window\.INITIAL_QUOTATION_DB\s*=\s*[\s\S]*?;\s*\n'
            replacement_db = f'window.INITIAL_QUOTATION_DB = {json.dumps(quote_db, ensure_ascii=False)};\n'
            content = re.sub(pattern_db, lambda m: replacement_db, content, count=1)

        temp_path = html_path + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(temp_path, html_path)
        
        msg = "成功固化写入HTML程序！"
        if chapters:
            total_tbl = sum(len([b for b in s['blocks'] if b['type'] == 'table']) for ch in chapters for s in ch['sections'])
            msg += f"(含{len(chapters)}个大章、{total_tbl}个表格)"
        if quote_data:
            msg += "及最新工程报价单"
        if quote_db:
            msg += "及最新设备选型数据库(含已维护价格)"
        return True, msg
    except Exception as e:
        return False, str(e)

# 后台自动监听与固化服务
def background_watcher():
    last_mod = None
    if os.path.exists(docx_path):
        last_mod = os.path.getmtime(docx_path)
    while True:
        try:
            time.sleep(2.0)
            if os.path.exists(docx_path):
                current_mod = os.path.getmtime(docx_path)
                if last_mod is not None and current_mod != last_mod:
                    print(f"\n[自动检测] 发现《{docx_name}》已更新！正在自动重新编译并保存到 HTML 程序中...")
                    chapters = parse_docx_file(docx_path)
                    if chapters:
                        ok, msg = save_chapters_to_html(chapters=chapters)
                        if ok:
                            print(f"[自动固化] ✅ {msg}")
                            print(f"[提示] HTML程序自身已更新为最新版本，外部编辑文档可随时安全归档或删除。")
                    last_mod = current_mod
                elif last_mod is None:
                    last_mod = current_mod
        except Exception as e:
            print(f"[监控异常] {e}")

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=script_dir, **kwargs)

    def do_GET(self):
        if self.path == '/api/sync_docx':
            if os.path.exists(docx_path):
                chapters = parse_docx_file(docx_path)
                if chapters:
                    ok, msg = save_chapters_to_html(chapters=chapters)
                    self.send_response(200 if ok else 500)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': ok, 'message': msg}, ensure_ascii=False).encode('utf-8'))
                    return
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Docx file not found')
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/save_html':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                chapters = data.get('chapters')
                quote_data = data.get('quoteData')
                quote_db = data.get('quoteDb')
                ok, msg = save_chapters_to_html(chapters=chapters, quote_data=quote_data, quote_db=quote_db)
                self.send_response(200 if ok else 500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': ok, 'message': msg}, ensure_ascii=False).encode('utf-8'))
                if ok:
                    print(f"[API保存] 前端手动触发固化：{msg}")
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        elif self.path == '/api/sync_docx':
            if os.path.exists(docx_path):
                chapters = parse_docx_file(docx_path)
                if chapters:
                    ok, msg = save_chapters_to_html(chapters)
                    self.send_response(200 if ok else 500)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': ok, 'message': msg}, ensure_ascii=False).encode('utf-8'))
                    return
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Docx file not found')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Endpoint not found')

def run_server():
    server = socketserver.TCPServer(('127.0.0.1', PORT), CustomHandler)
    t = threading.Thread(target=background_watcher, daemon=True)
    t.start()
    print("=======================================================================")
    print("  多媒体工程师全栈手册 · 智能服务已启动 (支持自动固化与热重载)")
    print(f"  服务地址: http://127.0.0.1:{PORT}/{html_name}")
    print("  特性: Word 保存后自动编译并写回 HTML 程序中，外部文档可随时删除。")
    print("=======================================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
        server.shutdown()

if __name__ == '__main__':
    run_server()
