# -*- coding: utf-8 -*-
"""s08_metrics_tables.py — шаг 8 статьи: метрики R1 и таблицы результатов (2, 5) с интервалами Уилсона.

Пути задаются через argparse; общие функции — в common/.
Статистика: интервал Уилсона для доли; z-критерий для разности долей (формула, проверена на значениях статьи).

Шаг статьи → скрипт → выход → таблица:
  «охват списка 99,9%; охват реестра 48,7%; археологические 0%; 47 и 46; 95 из 2198; 18 ниже 0,60»
  → s08 → results_long_fixed.csv + tables_2_5.csv → таблицы 2, 5.
"""
import csv, os, re, math, argparse, sys, difflib
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.io import load_csv
from common.normalize import regkey, share

PILOTS = ('Солтонский', 'Красногорский', 'Змеиногорский')

def wilson_ci(k, n, z=1.96):
    """Интервал Уилсона для доли k/n. Возвращает (lo, hi) в долях."""
    if n == 0: return (0.0, 0.0)
    p = k / n; z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))

def z_test_two_props(k1, n1, k2, n2):
    """z-критерий для разности двух долей (пул-оценка). Возвращает z."""
    if n1 == 0 or n2 == 0: return 0.0
    p_pool = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    if se == 0: return 0.0
    return (k1/n1 - k2/n2) / se

def parse_list(list_csv):
    return [r for r in csv.reader(open(list_csv, encoding='utf-8'), delimiter=';')][1:]

def main(egrkn_csv, meta_csv, list_csv, matches_csv, out_dir):
    E = load_csv(egrkn_csv)
    META = {r['record_id']: r for r in load_csv(meta_csv)} if meta_csv else {}
    altai = [r for r in E if r['in_altai_region'] == 'true']
    L = parse_list(list_csv)
    list_regs = set(regkey(r[7]) for r in L if r[7].strip())
    M = load_csv(matches_csv)
    exact = sum(1 for m in M if m['match_type'] == 'exact_registry')
    dump_in_list = [r for r in altai if regkey(r['registry_number']) in list_regs]

    RES = []
    def add(table, group, metric, value, note=''):
        RES.append([table, group, metric, value, note])

    add('R1', 'край', 'записей дампа (регион «Алтайский край»)', len(altai))
    add('R1', 'край', 'записей дампа всего в срезе', len(E), 'включая записи иных субъектов, попавшие по префиксу 22')
    declared = 2204
    add('R1', 'край', 'записей списка ГУКН (заявлено)', declared)
    add('R1', 'край', 'записей списка ГУКН (восстановлено)', len(L))
    add('R1', 'край', 'записей списка, найденных в дампе по номеру', exact)
    add('R1', 'край', 'доля записей списка, найденных в дампе, %', share(exact, len(L)))
    add('R1', 'край', 'записей дампа, представленных в списке', len(dump_in_list))
    add('R1', 'край', 'доля дампа, представленная в списке, %', share(len(dump_in_list), len(altai)))
    add('R1', 'край', 'записей дампа вне списка', len(altai) - len(dump_in_list))
    add('R1', 'край', 'записей списка, не найденных в дампе', len(L) - exact)
    add('R1', 'край', 'повторяющихся регистрационных номеров в дампе', sum(1 for v in defaultdict(list, {}).values() if 0))
    for key, label in (('category', 'категория'), ('typologies', 'типология')):
        grp = defaultdict(lambda: [0, 0])
        for r in altai:
            k = (r[key] or 'не указано').split(';')[0].strip() or 'не указано'
            grp[k][0] += 1; grp[k][1] += (regkey(r['registry_number']) in list_regs)
        for k, (n, c) in sorted(grp.items(), key=lambda x: -x[1][0])[:10]:
            add('R1', f'{label}: {k}', 'записей дампа / доля в списке, %', n, share(c, n))

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'results_long_fixed.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['table', 'group', 'metric', 'value', 'note'])
        w.writerows(RES)

    # --- Таблица 2: охват с интервалами Уилсона ---
    def row_t2(label, k, n):
        lo, hi = wilson_ci(k, n)
        return [label, k, n, round(k/n*100, 2) if n else 0, round(lo*100, 1), round(hi*100, 1)]
    t2 = [
        row_t2('охват списка', exact, len(L)),
        row_t2('охват реестра', len(dump_in_list), len(altai)),
        row_t2('археологические', sum(1 for r in altai if 'археолог' in (r['typologies'] or '').lower() and regkey(r['registry_number']) in list_regs), sum(1 for r in altai if 'археолог' in (r['typologies'] or '').lower())),
        row_t2('остальные виды', sum(1 for r in altai if 'археолог' not in (r['typologies'] or '').lower() and regkey(r['registry_number']) in list_regs), sum(1 for r in altai if 'археолог' not in (r['typologies'] or '').lower())),
        row_t2('федеральное значение', sum(1 for r in altai if 'федеральн' in (r['category'] or '').lower() and regkey(r['registry_number']) in list_regs), sum(1 for r in altai if 'федеральн' in (r['category'] or '').lower())),
        row_t2('региональное значение', sum(1 for r in altai if 'региональн' in (r['category'] or '').lower() and regkey(r['registry_number']) in list_regs), sum(1 for r in altai if 'региональн' in (r['category'] or '').lower())),
        row_t2('сельские поселения', sum(1 for r in altai if r['settlement_type'] == 'сельское' and regkey(r['registry_number']) in list_regs), sum(1 for r in altai if r['settlement_type'] == 'сельское')),
        row_t2('городские поселения', sum(1 for r in altai if r['settlement_type'] == 'городское' and regkey(r['registry_number']) in list_regs), sum(1 for r in altai if r['settlement_type'] == 'городское')),
    ]
    with open(os.path.join(out_dir, 'table_2_coverage.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['metric', 'numerator', 'denominator', 'pct', 'wilson_lo', 'wilson_hi'])
        w.writerows(t2)

    # --- Таблица 5: расхождения наименований и регномера ---
    pairs = []
    E_by_id = {r['record_id']: r for r in E}
    for m in M:
        if m['match_type'] == 'exact_registry':
            lr = L[int(m['list_row_index'])]
            d = E_by_id.get(m['dump_record_id'], {})
            if lr[0].strip() and d.get('name', '').strip():
                import unicodedata
                def nn(s):
                    s = unicodedata.normalize('NFC', str(s or '')).lower()
                    s = re.sub(r"[«»\"„“”'(),./-]", ' ', s)
                    return re.sub(r'\s+', ' ', s).strip()
                ratio = difflib.SequenceMatcher(None, nn(lr[0]), nn(d['name'])).ratio()
                pairs.append(ratio)
    N = len(pairs)
    mismatch = sum(1 for r in pairs if r < 1.0)
    below_60 = sum(1 for r in pairs if r < 0.60)
    zero_loss = [(i, r[7]) for i, r in enumerate(L) if r[7].strip() and len(re.sub(r'\D', '', r[7])) < 15]
    dump_regs = set(regkey(r['registry_number']) for r in E if r['registry_number'].strip())
    restored = sum(1 for _, rn in zero_loss if regkey(rn) in dump_regs)
    t5 = [
        ['расхождение наименований (ratio<1.0)', mismatch, N, round(mismatch/N*100, 2) if N else 0, 'метрика SequenceMatcher(norm_name(list), norm_name(dump)).ratio(); порог <1.0'],
        ['сходство ниже 60/100 (ratio<0.6)', below_60, N, round(below_60/N*100, 2) if N else 0, 'порог <0.60'],
        ['регномера с утраченным нулём (<15 цифр)', len(zero_loss), len(L), round(len(zero_loss)/len(L)*100, 2), ''],
        ['однозначно восстановлено', restored, len(zero_loss), round(restored/len(zero_loss)*100, 2) if zero_loss else 0, 'regkey zfill(15) найден в дампе'],
    ]
    with open(os.path.join(out_dir, 'table_5_discrepancies.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['metric', 'numerator', 'denominator', 'pct', 'note'])
        w.writerows(t5)

    # --- Таблица 3: полнота полей по группам ---
    # Группы: все; непубличные (археологические, is_public=False); публичные; сельские; городские.
    # Показатели: адрес, населённый пункт, предмет охраны, датировка (содержательная),
    #   документы об охране, координаты, принадлежность к ВОВ (wow_value='Да').
    # «Датировка (содержательная)» = general.createDate непустое И не содержит «не определена»
    #   (стандартная формулировка отсутствия даты; опечатки формулировки из таблицы 5 не исключаются).
    def has_dating_content(r):
        v = (META.get(r['record_id'], {}).get('general_createDate') or '').strip()
        return bool(v) and 'не определена' not in v.lower()
    def is_arch(r): return 'археологи' in (r['typologies'] or '').lower()
    groups3 = [
        ('Все записи', altai),
        ('Непубличные (археол. зап.)', [r for r in altai if is_arch(r)]),
        ('Публичные записи', [r for r in altai if not is_arch(r)]),
        ('Сельские поселения', [r for r in altai if r['settlement_type'] == 'сельское']),
        ('Городские поселения', [r for r in altai if r['settlement_type'] == 'городское']),
    ]
    indicators = [
        ('Адрес, %', lambda r: bool((r['address_full'] or '').strip())),
        ('Населенный пункт, %', lambda r: bool((r['settlement'] or '').strip())),
        ('Предмет охраны, %', lambda r: bool((r['security_info'] or '').strip())),
        ('Датировка (содержательная), %', has_dating_content),
        ('Документы об охране, %', lambda r: bool((r['documents'] or '').strip())),
        ('Координаты, %', lambda r: bool(r['lat'].strip())),
        ('Принадлежность к ВОВ, %', lambda r: (META.get(r['record_id'], {}).get('wow_value') or '') == 'Да'),
    ]
    t3 = []
    for ind, fn in indicators:
        row = [ind]
        for gname, rows in groups3:
            k = sum(1 for r in rows if fn(r))
            row.extend([k, len(rows), round(k/len(rows)*100, 1) if rows else 0])
        t3.append(row)
    with open(os.path.join(out_dir, 'table_3_field_completeness.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['indicator'] + sum(([f'{g}_k', f'{g}_n', f'{g}_pct'] for g, _ in groups3), []))
        w.writerows(t3)

    # --- Таблица 4: группы (сельские vs городские) с интервалами Уилсона и z ---
    # «Мемориалы ВОВ» = первая типология «Памятник истории» + wow_value='Да';
    # «Прочие памятники истории» = первая типология «Памятник истории» + wow_value!='Да';
    # «Градостроительство и архитектура» = первая типология «Памятник градостроительства и архитектуры».
    def first_typ(r): return (r['typologies'] or '').split(';')[0].strip()
    def has_wow(r): return (META.get(r['record_id'], {}).get('wow_value') or '') == 'Да'
    def has_sec(r): return bool((r['security_info'] or '').strip())
    def has_coord(r): return bool(r['lat'].strip())
    groups4 = [
        ('Все записи с адресом', lambda r: True),
        ('Мемориалы ВОВ', lambda r: first_typ(r) == 'Памятник истории' and has_wow(r)),
        ('Прочие памятники истории', lambda r: first_typ(r) == 'Памятник истории' and not has_wow(r)),
        ('Градостроительство и архитектура', lambda r: first_typ(r) == 'Памятник градостроительства и архитектуры'),
    ]
    t4 = []
    for gname, cond in groups4:
        sel = [r for r in altai if (r['settlement_type'] in ('сельское', 'городское')) and cond(r)]
        sel_s = [r for r in sel if r['settlement_type'] == 'сельское']
        sel_g = [r for r in sel if r['settlement_type'] == 'городское']
        row = [gname, len(sel_s), len(sel_g)]
        cells = []
        zvals = []
        for fn in (has_coord, has_sec):
            ks, kg = sum(1 for r in sel_s if fn(r)), sum(1 for r in sel_g if fn(r))
            los, his = wilson_ci(ks, len(sel_s)); log, hig = wilson_ci(kg, len(sel_g))
            cells.append(f'{ks/len(sel_s)*100:.1f} ({los*100:.1f}–{his*100:.1f}) / {kg/len(sel_g)*100:.1f} ({log*100:.1f}–{hig*100:.1f})' if sel_s and sel_g else '')
            zvals.append(round(z_test_two_props(ks, len(sel_s), kg, len(sel_g)), 1))
        row.extend(cells + [f'{zvals[0]}; {zvals[1]}'])
        t4.append(row)
    with open(os.path.join(out_dir, 'table_4_groups.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['group', 'n_rural', 'n_urban', 'coords_pct_rural_ci / urban_ci', 'security_pct_rural_ci / urban_ci', 'z_coords; z_security'])
        w.writerows(t4)

    print(f's08: results_long_fixed ({len(RES)} строк); table_2 ({len(t2)}); table_3 ({len(t3)}); table_4 ({len(t4)}); table_5 ({len(t5)})')
    print(f'  охват списка {exact}/{len(L)}={share(exact,len(L))}%; охват реестра {len(dump_in_list)}/{len(altai)}={share(len(dump_in_list),len(altai))}%')
    print(f'  расхождение {mismatch}/{N}; ниже 0.6: {below_60}; регномера <15: {len(zero_loss)}, восстановлено {restored}')
    return RES, t2, t5

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--egrkn', required=True)
    ap.add_argument('--meta', required=True, help='egrkn_meta.csv (выход s03: general_createDate, wow_value, is_public)')
    ap.add_argument('--list', required=True)
    ap.add_argument('--matches', required=True)
    ap.add_argument('--out-dir', required=True)
    a = ap.parse_args()
    main(a.egrkn, a.meta, a.list, a.matches, a.out_dir)
