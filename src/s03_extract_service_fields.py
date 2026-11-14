# -*- coding: utf-8 -*-
"""s03_extract_service_fields.py — шаг 3 статьи: служебные поля дампа ЕГРОКН (метаданные, диагностика полноты).

Источник: egrkn_extract_meta.py (заход 2б-мета). Рефакторинг: пути через argparse; общие функции в common/.
Логика и состав колонок НЕ изменены.

Шаг статьи → скрипт → выход → таблица:
  «диагностика полноты полей: mapPosition, fias, документы, фото, security_len» → s03 → egrkn_meta.csv (29 колонок) + schema_key_counts.csv → таблица 3.
"""
import csv, glob, json, os, argparse
from collections import Counter
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.io import find_records, get_general as get_block_alias

def get_block(r, name):
    b = r.get(name) or {}
    if not b: b = (r.get('data') or {}).get(name) or {}
    return b if isinstance(b, dict) else {}

def ne(v):
    if v is None: return False
    if isinstance(v, (list, dict, str)): return len(v) > 0
    return True

def ln(v): return len(str(v)) if ne(v) else 0

def main(json_dir, out_dir):
    hdr = ['record_id','registry_number','source_file','source_row','is_public','is_actual','general_createDate','info_createDate','info_updateDate',
           'full_address_len','installation_address_len','street_len','address_comment_len','fias_any','mapPosition_type','additionalCoordinates_n',
           'selfCoord_n','yandexCoord_present','border_len','security_len','regime_len','photo_present','documents_n','protection_year','restoration_year',
           'heritage_type','unesco','status_value','wow_value']
    files = [f for f in sorted(glob.glob(os.path.join(json_dir, '*.json')), key=lambda x: (len(os.path.basename(x)), x)) if 'structure' not in os.path.basename(f).lower()]
    rows, keycount, n_all = [], {'general': Counter(), 'address': Counter(), 'coords': Counter(), 'info': Counter()}, 0
    for fp in files:
        try: data = json.load(open(fp, encoding='utf-8'))
        except Exception as e:
            print(fp, 'ОШИБКА', e); continue
        for i, r in enumerate(find_records(data)):
            if not isinstance(r, dict): continue
            g = get_block(r, 'general'); info = get_block(r, 'info')
            reg = str((g.get('region') or {}).get('value', '')); rn = str(g.get('regNumber', '') or '')
            if not ('алтайский' in reg.lower() or rn.startswith('22')): continue
            n_all += 1
            a = g.get('address') or {}; c = g.get('coords') or {}; mp = a.get('mapPosition') or {}
            fias = any(ne(v) for k, v in a.items() if k.lower().startswith('fias'))
            rows.append([f'E{n_all:05d}', rn, os.path.basename(fp), i, g.get('isPublic',''), g.get('isActual',''), g.get('createDate',''),
                info.get('createDate',''), info.get('updateDate',''), ln(a.get('fullAddress')), ln(a.get('installationAddress')), ln(a.get('street')),
                ln(a.get('comment')), int(fias), (mp.get('type','') if isinstance(mp, dict) else ''), len(g.get('additionalCoordinates') or []),
                len(c.get('selfCoord') or []) if isinstance(c, dict) else 0, int(ne(c.get('yandexCoord')) if isinstance(c, dict) else 0), ln(g.get('borderInfo')),
                ln(g.get('securityInfo')), ln(g.get('regimeInfo')), int(ne((g.get('photo') or {}).get('url')) if isinstance(g.get('photo'), dict) else 0),
                len(g.get('documents') or []), g.get('protectionYear',''), g.get('restorationYear',''),
                (g.get('heritageType') or {}).get('value','') if isinstance(g.get('heritageType'), dict) else '',
                (g.get('unesco') or {}).get('value','') if isinstance(g.get('unesco'), dict) else '',
                (g.get('status') or {}).get('value','') if isinstance(g.get('status'), dict) else '',
                (g.get('wow') or {}).get('value','') if isinstance(g.get('wow'), dict) else ''])
            for k, v in g.items():
                if ne(v): keycount['general'][k] += 1
            for k, v in a.items():
                if ne(v): keycount['address'][k] += 1
            if isinstance(c, dict):
                for k, v in c.items():
                    if ne(v): keycount['coords'][k] += 1
            for k, v in info.items():
                if ne(v): keycount['info'][k] += 1
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'egrkn_meta.csv'), 'w', newline='', encoding='utf-8') as f:
        csv.writer(f, delimiter=';').writerows([hdr] + rows)
    with open(os.path.join(out_dir, 'schema_key_counts.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['block','key','records_nonempty','of_total'])
        for blk, cn in keycount.items():
            for k, v in sorted(cn.items()): w.writerow([blk, k, v, n_all])
    print(f's03: {n_all} записей -> egrkn_meta.csv (29 колонок) + schema_key_counts.csv')
    return n_all

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--json-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    a = ap.parse_args()
    sys.exit(0 if main(a.json_dir, a.out_dir) else 1)
