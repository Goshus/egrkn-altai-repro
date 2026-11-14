# -*- coding: utf-8 -*-
"""io.py — ввод-вывод CSV/JSON/docx (из layers_and_results.py + build_final_table.py)."""
import csv, json, os, re, zipfile

def load_csv(p, delim=';'):
    return list(csv.DictReader(open(p, encoding='utf-8'), delimiter=delim)) if os.path.exists(p) else []

def write_csv(path, header, rows, delim=';'):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=delim); w.writerow(header); w.writerows(rows)

def find_records(obj):
    if isinstance(obj, list): return obj
    if isinstance(obj, dict):
        for k in ('data', 'items', 'records', 'features'):
            if isinstance(obj.get(k), list): return obj[k]
        for v in obj.values():
            if isinstance(v, list) and v and isinstance(v[0], dict): return v
    return []

def get_general(r):
    g = r.get('general') or {}
    if not g: g = (r.get('data') or {}).get('general') or {}
    return g if isinstance(g, dict) else {}

def docx_rows(path):
    xml = zipfile.ZipFile(path).read('word/document.xml').decode('utf-8')
    out = []
    for tr in re.findall(r'<w:tr[ >].*?</w:tr>', xml, re.S):
        out.append([''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', tc)).strip() for tc in re.findall(r'<w:tc>.*?</w:tc>', tr, re.S)])
    return out
