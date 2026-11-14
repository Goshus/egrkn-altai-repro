# -*- coding: utf-8 -*-
"""s09_orders_trace.py — шаг 9 статьи: сопоставление приказов ВОКН с дампом и списком (слепая зона).

Источник: layers_and_results.py:267-288 (R4). Рефакторинг: пути через argparse; общие функции в common/.
Логика поиска (строгое/нечёткое/адресное совпадение токенов) НЕ изменена.

Шаг статьи → скрипт → выход → таблица:
  «слепая зона: приказы ВОКН 2019–2026 vs дамп/список» → s09 → blind_zone_report.csv → таблица 4 (R4).
  Примечание: update_blind_zone.py (ручная разметка реестра приказов) в репозиторий НЕ входит;
  публикуется только итоговый реестр prikazy_vokn_2019_2026.csv как вручную размеченные данные (data/manual/).
"""
import csv, os, argparse, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.io import load_csv
from common.normalize import norm_name

STOP = {'стоянка', 'курган', 'могильник', 'поселение', 'памятник', 'братская', 'одиночный', 'грунтовый',
        'церковь', 'курганный', 'место', 'объект', 'селище', 'городище', 'могила', 'и', 'в', 'на', 'у', 'от', 'имени'}

def search(corp, strict, loose):
    sh = [f'{s}:{i}' for s, i, nn, a in corp if strict and strict <= set(nn.split())]
    lh = [f'{s}:{i}' for s, i, nn, a in corp if loose and loose <= set(nn.split())]
    ah = [f'{s}:{i}' for s, i, nn, a in corp if loose and loose <= set(a.split())]
    if len(sh) == 1: v = 'НАЙДЕН (единственное совпадение)'
    elif len(sh) > 1: v = f'НАЙДЕН (неоднозначно: {len(sh)})'
    elif lh: v = f'ВОЗМОЖНО (без номера в наименовании: {len(lh)})'
    elif ah: v = 'ТОЛЬКО адресное совпадение'
    else: v = 'НЕ НАЙДЕН'
    return v, (sh or lh or ah)[:5]

def main(egrkn_csv, list_csv, manual_csv, out_path):
    """manual_csv — эталон ручной части (data/manual/blind_zone_report_manual.csv, 7 столбцов):
    prikaz_date, prikaz_number, object_name + ручные verdict/name_hits/address_hits/comment.
    s09 читает первые три столбца (реквизиты) и вычисляет автоматические вхождения;
    ручные столбцы эталона не перезаписываются (сравнение — в отчёте захода 13)."""
    E = load_csv(egrkn_csv)
    L = [r for r in csv.reader(open(list_csv, encoding='utf-8'), delimiter=';')][1:]
    corpus = [('ЕГРОКН', r['record_id'], norm_name(r['name']), (r['address_full'] or '').lower()) for r in E]
    corpus_l = [('Список', f'row{i}', norm_name(lr[0]), (lr[2] + ' ' + lr[1]).lower()) for i, lr in enumerate(L)]
    bz = []
    for p in load_csv(manual_csv):
        toks = [t for t in norm_name(p['object_name']).split() if t not in STOP and (len(t) > 2 or t.isdigit())]
        strict, loose = set(toks), {t for t in toks if not t.isdigit()}
        vd, hd = search(corpus, strict, loose)
        vl, hl = search(corpus_l, strict, loose)
        year = int(p['prikaz_date'].split('.')[-1])
        bz.append([p['prikaz_date'], p['prikaz_number'], p['object_name'], '2019–2024' if year <= 2024 else '2025–2026', vd, '; '.join(hd), vl, '; '.join(hl)])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['prikaz_date', 'prikaz_number', 'object_name', 'wave', 'in_dump', 'dump_hits', 'in_list', 'list_hits'])
        w.writerows(bz)
    print(f's09: {len(bz)} приказов -> {out_path}')
    return len(bz)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--egrkn', required=True)
    ap.add_argument('--list', required=True)
    ap.add_argument('--manual', required=True, help='data/manual/blind_zone_report_manual.csv (эталон ручной части)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    main(a.egrkn, a.list, a.manual, a.out)
