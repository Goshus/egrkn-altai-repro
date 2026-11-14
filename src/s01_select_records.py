# -*- coding: utf-8 -*-
"""s01_select_records.py — шаг 1 статьи: отбор записей Алтайского края из дампа ЕГРОКН (17 файлов JSON).

Источник: egrkn_pipeline_v131.py (заход 1-бис). Рефакторинг: убран устаревший detect_district
(заменён на s06_assign_districts.py v3 по перечню ОКТМО); пути через argparse; общие функции в common/.
Логика отбора и контрольные суммы НЕ изменены.

Шаг статьи → скрипт → выход → таблица:
  «дамп ЕГРОКН: 4518 записей края» → s01 → egrkn_altai.csv + probe_report.csv + manifest_run1.csv → таблица 1, рис. 2.

Контроль приёмки: ровно 4518 записей; sha256 сортированных регномеров = 86afa4ab… (см. common/hashes.py).
"""
import csv, glob, hashlib, json, os, re, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.io import find_records, get_general
from common.normalize import norm_name_pipeline
from common.hashes import sha256_file, EXPECTED_N, EXPECTED_SHA_REG

def first_latlon_from_geojson(geom):
    if not isinstance(geom, dict): return None
    pts = []
    def collect(x):
        if isinstance(x, (list, tuple)) and len(x) >= 2 and all(isinstance(v, (int, float)) for v in x[:2]):
            pts.append((float(x[0]), float(x[1])))
        elif isinstance(x, (list, tuple)):
            for y in x: collect(y)
    collect(geom.get('coordinates'))
    if not pts: return None
    return (round(sum(p[1] for p in pts)/len(pts), 6), round(sum(p[0] for p in pts)/len(pts), 6))

def parse_point_string(s):
    nums = re.findall(r'-?\d+[.,]?\d*', str(s))
    if len(nums) < 2: return None
    a, b = float(nums[0].replace(',', '.')), float(nums[1].replace(',', '.'))
    lat, lon = (a, b); swapped = False
    if not (49.0 <= lat <= 56.0 and 78.0 <= lon <= 91.0) and (49.0 <= b <= 56.0 and 78.0 <= a <= 91.0):
        lat, lon, swapped = b, a, True
    return (lat, lon, swapped)

def extract(g):
    addr = g.get('address') or {}; coords = g.get('coords') or {}
    lat = lon = ''; src = ''
    ll = first_latlon_from_geojson(addr.get('mapPosition'))
    if ll: lat, lon, src = ll[0], ll[1], 'mapPosition'
    elif coords.get('selfCoord'):
        p = parse_point_string(coords['selfCoord'][0].get('point', ''))
        if p: lat, lon, src = p[0], p[1], 'selfCoord' + ('_swapped' if p[2] else '')
    elif coords.get('yandexCoord'):
        ll = first_latlon_from_geojson(coords.get('yandexCoord'))
        if ll: lat, lon, src = ll[0], ll[1], 'yandex_auto'
    typo = g.get('typologies') or []
    return dict(registry_number=str(g.get('regNumber', '') or ''), name_raw=str(g.get('name', '') or ''),
        name_norm=norm_name_pipeline(g.get('name', '') or ''),
        category=str((g.get('categoryType') or {}).get('value', '') or ''),
        obj_type=str((g.get('objectType') or {}).get('value', '') or ''),
        address_raw=str(addr.get('fullAddress', '') or ''), lat=lat, lon=lon, coord_source=src,
        typologies='; '.join(str(t.get('value','')) for t in typo if isinstance(t, dict)),
        parent_id=str(g.get('parentId', '') or ''), is_actual=str(g.get('isActual', '')),
        protection_year=str(g.get('protectionYear', '') or ''))

def main(json_dir, out_dir):
    files = [f for f in sorted(glob.glob(os.path.join(json_dir, '*.json')), key=lambda x: (len(os.path.basename(x)), x))
             if 'structure' not in os.path.basename(f).lower()]
    hdr = ['record_id','registry_number','name_raw','name_norm','category','obj_type','dating',
           'address_raw','settlement','district','lat','lon','coord_source','source_file','source_row',
           'typologies','parent_id','is_actual','protection_year']
    rows, probe, manifest = [], [], []
    for fp in files:
        manifest.append([os.path.basename(fp), sha256_file(fp), os.path.getsize(fp)])
        try: data = json.load(open(fp, encoding='utf-8'))
        except Exception as e:
            probe.append([os.path.basename(fp), -1, 0, 0, f'ОШИБКА {type(e).__name__}: {e}']); continue
        recs = find_records(data); by_reg = by_num = both = 0
        for i, r in enumerate(recs):
            if not isinstance(r, dict): continue
            g = get_general(r)
            reg = str((g.get('region') or {}).get('value', '')); rn = str(g.get('regNumber', '') or '')
            f1 = 'алтайский' in reg.lower(); f2 = rn.startswith('22')
            by_reg += f1; by_num += f2; both += (f1 and f2)
            if not (f1 or f2): continue
            e = extract(g)
            rows.append([f'E{len(rows)+1:05d}', e['registry_number'], e['name_raw'], e['name_norm'],
                e['category'], e['obj_type'], '', e['address_raw'], '', '',
                e['lat'], e['lon'], e['coord_source'], os.path.basename(fp), i,
                e['typologies'], e['parent_id'], e['is_actual'], e['protection_year']])
        probe.append([os.path.basename(fp), len(recs), by_reg, by_num, by_reg - both])
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'egrkn_altai.csv'), 'w', newline='', encoding='utf-8') as f:
        csv.writer(f, delimiter=';').writerows([hdr] + rows)
    with open(os.path.join(out_dir, 'probe_report.csv'), 'w', newline='', encoding='utf-8') as f:
        csv.writer(f, delimiter=';').writerows([['file','records_total','altai_by_region','altai_by_regnum22','region_not_regnum']] + probe)
    with open(os.path.join(out_dir, 'manifest_run1.csv'), 'w', newline='', encoding='utf-8') as f:
        csv.writer(f, delimiter=';').writerows([['filename','sha256','bytes']] + manifest)
    checksum = hashlib.sha256('\n'.join(sorted(r[1] for r in rows)).encode()).hexdigest()
    ok = len(rows) == EXPECTED_N and checksum == EXPECTED_SHA_REG
    print(f's01: записей {len(rows)}; sha256 регномеров {checksum}; совпадение с эталоном: {ok}')
    return ok

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--json-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    a = ap.parse_args()
    sys.exit(0 if main(a.json_dir, a.out_dir) else 1)
