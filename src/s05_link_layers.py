# -*- coding: utf-8 -*-
"""s05_link_layers.py — шаг 5 статьи: сшивка списка ГУКН с дампом ЕГРОКН.

Пути задаются через argparse; общие функции — в common/. Правила сшивки:
  - exact_registry: совпадение по regkey (zfill 15) регистрационного номера;
  - name_fuzzy_unique: difflib.SequenceMatcher >= 0.85, единственное совпадение в районе;
  - list_only: не найдено в дампе;
  - dump_only_pilot: записи пилотных районов вне списка.

Шаг статьи → скрипт → выход → таблица:
  «сшивка список↔дамп: 2201 из 2204, 2200 из 4516» → s05 → matches_fixed.csv, list_only_fixed.csv, dump_only_pilot_fixed.csv → таблица 2.
"""
import csv, os, re, argparse, sys, difflib
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.io import load_csv
from common.normalize import norm_name, stem, regkey

PILOTS = ('Солтонский', 'Красногорский', 'Змеиногорский')
def pilot_of(text):
    t = (text or '').lower()
    for p in PILOTS:
        if stem(p) in t: return p
    return ''

def main(egrkn_csv, list_csv, out_dir):
    E = load_csv(egrkn_csv)
    L = [r for r in csv.reader(open(list_csv, encoding='utf-8'), delimiter=';')][1:]  # skip header
    for r in E:
        r['_base'] = (r['district_oktmo'] or '').split(' (')[0].replace('г. ', '').strip()
        r['_pilot'] = pilot_of(r['_base']) if r['district_oktmo'] else ''
    dump_by_reg = defaultdict(list)
    for r in E: dump_by_reg[regkey(r['registry_number'])].append(r)
    list_regs = set(regkey(r[7]) for r in L if r[7].strip())
    matches, list_only, used_dump = [], [], set()
    by_district = defaultdict(list)
    for r in E: by_district[stem(r['_base'])].append(r)
    for i, lr in enumerate(L):
        regn = regkey(lr[7])
        ld = re.sub(r'^(?:г\.|город)\s*', '', lr[1].replace(' район', '').strip())
        hit = dump_by_reg.get(regn)
        if hit:
            d = hit[0]; used_dump.add(d['record_id'])
            dres = 'в дампе район не определён' if not d['_base'] else ('совпал' if stem(d['_base']) == stem(ld) else 'РАСХОЖДЕНИЕ')
            matches.append([d['record_id'], i, 'exact_registry', 1.0, dres, ld, d['_base']])
        else:
            nn = norm_name(lr[0]); scores = []
            for d in by_district.get(stem(ld), []):
                if d['record_id'] in used_dump: continue
                scores.append((difflib.SequenceMatcher(None, nn, norm_name(d['name'])).ratio(), d))
            scores.sort(key=lambda x: -x[0])
            if scores and scores[0][0] >= 0.85 and (len(scores) == 1 or scores[1][0] < 0.85):
                best, bs = scores[0][1], scores[0][0]
                used_dump.add(best['record_id'])
                matches.append([best['record_id'], i, 'name_fuzzy_unique', round(bs, 3), '', ld, best['_base']])
            else:
                list_only.append([i, lr[0][:70], ld, lr[7].strip()])
    pil_dump = [r for r in E if r['_pilot']]
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'matches_fixed.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['dump_record_id', 'list_row_index', 'match_type', 'confidence', 'district_check', 'list_district', 'dump_district'])
        w.writerows(matches)
    with open(os.path.join(out_dir, 'list_only_fixed.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['list_row_index', 'name', 'list_district', 'registry_number'])
        w.writerows(list_only)
    with open(os.path.join(out_dir, 'dump_only_pilot_fixed.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['record_id', 'registry_number', 'name', 'district', 'address'])
        for r in pil_dump:
            if regkey(r['registry_number']) not in list_regs:
                w.writerow([r['record_id'], r['registry_number'], r['name'][:80], r['_pilot'], r['address_full'][:90]])
    exact = sum(1 for m in matches if m[2] == 'exact_registry')
    print(f's05: matches {len(matches)} (exact {exact}); list_only {len(list_only)}; dump_only_pilot {sum(1 for r in pil_dump if regkey(r["registry_number"]) not in list_regs)}')
    return len(matches), exact, len(list_only)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--egrkn', required=True)
    ap.add_argument('--list', required=True)
    ap.add_argument('--out-dir', required=True)
    a = ap.parse_args()
    main(a.egrkn, a.list, a.out_dir)
