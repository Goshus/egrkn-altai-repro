# -*- coding: utf-8 -*-
"""s02_extract_fields.py — шаг 2 статьи: вторичное извлечение полей из дампа ЕГРОКН.

Источник: egrkn_extract_full.py (заход 2а). Рефакторинг: пути через argparse; общие функции в common/.
Логика извлечения и состав колонок НЕ изменены.

Шаг статьи → скрипт → выход → таблица:
  «поля ЕГРОКН: адрес, координаты, категория, типология, документы, предмет охраны, датировка»
  → s02 → egrkn_altai_full.csv (24 колонки) → таблицы 1, 3, 4.
"""
import csv, glob, json, os, re, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.io import find_records, get_general

DATING_RE = re.compile(r'(эпоха[^,.;)]{0,50}|верхнего палеолита|неолита?[^,.;)]{0,30}|бронз[^,.;)]{0,30}|средневеков[^,.;)]{0,25}|(?:XVIII|XIX|XX|XVII|XVI|[IVX]{1,4})\s*вв?\.[^,.;)]{0,30}|(?:1[5-9]\d{2}|20\d{2})\s*(?:[-–—]\s*(?:1[5-9]\d{2}|20\d{2}))?\s*гг?)', re.I)

def extract_dating(*texts):
    for t in texts:
        if not t: continue
        m = DATING_RE.search(str(t))
        if m: return m.group(0).strip()
    return ''

def extract_settlement(addr):
    if not addr: return ''
    m = re.search(r'((?:с|п|г|пос|дер|пгт|ст|рзд)\.?\s+[А-ЯЁ][^,;]+)', str(addr))
    if m and 'край' not in m.group(1).lower() and 'район' not in m.group(1).lower():
        return m.group(1).strip()
    return ''

def coords_of(g):
    addr = g.get('address') or {}; coords = g.get('coords') or {}
    def first_ll(geom):
        if not isinstance(geom, dict): return None
        pts = []
        def coll(x):
            if isinstance(x, (list, tuple)) and len(x) >= 2 and all(isinstance(v, (int, float)) for v in x[:2]):
                pts.append((float(x[0]), float(x[1])))
            elif isinstance(x, (list, tuple)):
                for y in x: coll(y)
        coll(geom.get('coordinates'))
        if not pts: return None
        return (round(sum(p[1] for p in pts)/len(pts), 6), round(sum(p[0] for p in pts)/len(pts), 6))
    ll = first_ll(addr.get('mapPosition'))
    if ll: return ll[0], ll[1], 'mapPosition', ''
    if coords.get('selfCoord'):
        nums = re.findall(r'-?\d+[.,]?\d*', str(coords['selfCoord'][0].get('point', '')))
        if len(nums) >= 2:
            a, b = float(nums[0].replace(',', '.')), float(nums[1].replace(',', '.'))
            return (a, b, 'selfCoord', '') if 49 <= a <= 56 and 78 <= b <= 91 else (b, a, 'selfCoord_swapped', '')
    ll = first_ll(coords.get('yandexCoord'))
    if ll: return ll[0], ll[1], 'yandex_auto', ''
    return '', '', '', ''

def main(json_dir, out_dir):
    hdr = ['record_id','registry_number','con_number','name','region_value','category','obj_type','typologies',
           'address_full','address_comment','settlement','border_info','security_info','dating_extracted',
           'documents','lat','lon','coord_source','coord_note','is_actual','protection_year','parent_id',
           'source_file','source_row']
    out = []
    files = [f for f in sorted(glob.glob(os.path.join(json_dir, '*.json')), key=lambda x: (len(os.path.basename(x)), x))
             if 'structure' not in os.path.basename(f).lower()]
    for fp in files:
        try: data = json.load(open(fp, encoding='utf-8'))
        except Exception as e:
            print(f'{fp}: ОШИБКА {e}'); continue
        n = 0
        for i, r in enumerate(find_records(data)):
            if not isinstance(r, dict): continue
            g = get_general(r)
            reg = str((g.get('region') or {}).get('value', '')); rn = str(g.get('regNumber', '') or '')
            if not ('алтайский' in reg.lower() or rn.startswith('22')): continue
            addr = g.get('address') or {}
            docs = g.get('documents') or []
            doc_s = ' | '.join(f"{d.get('name','')} №{d.get('number','')} от {d.get('date','')}" for d in docs if isinstance(d, dict))
            lat, lon, csrc, cnote = coords_of(g)
            sec = str(g.get('securityInfo', '') or '')
            out.append([f'E{len(out)+1:05d}', rn, str(g.get('conNumber','') or ''), str(g.get('name','') or ''),
                reg, str((g.get('categoryType') or {}).get('value','') or ''),
                str((g.get('objectType') or {}).get('value','') or ''),
                '; '.join(str(t.get('value','')) for t in (g.get('typologies') or []) if isinstance(t, dict)),
                str(addr.get('fullAddress','') or ''), str(addr.get('comment','') or ''),
                extract_settlement(addr.get('fullAddress','')),
                str(g.get('borderInfo','') or '')[:300], sec[:300],
                extract_dating(sec, g.get('name','')), doc_s[:300], lat, lon, csrc, cnote,
                str(g.get('isActual','')).lower(), str(g.get('protectionYear','') or ''), str(g.get('parentId','') or ''),
                os.path.basename(fp), i])
            n += 1
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'egrkn_altai_full.csv'), 'w', newline='', encoding='utf-8') as f:
        csv.writer(f, delimiter=';').writerows([hdr] + out)
    print(f's02: {len(out)} записей -> egrkn_altai_full.csv (24 колонки)')
    return len(out)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--json-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    a = ap.parse_args()
    sys.exit(0 if main(a.json_dir, a.out_dir) else 1)
