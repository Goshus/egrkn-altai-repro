# -*- coding: utf-8 -*-
"""run_all.py — оркестратор пайплайна ЕГРОКН-Алтай.

Режимы:
  --inputs DIR  : папка с входными данными (1.json…17.json, Spisok…md, перечень ОКТМО .docx,
                  boundary_1..3.json); перегенерирует все derived в data/derived/.
  --check       : проверка замороженных derived-файлов (data/derived/) на контрольные значения
                  и sha256; не требует входных дампов (они не входят в репозиторий).

Приёмка (статья): 4518/4516; 2204; 2201 из 2204; 2200 из 4516; район не установлен 2385 (2131 назначено);
полигон 97 из 99 (67/19/13; 65/19/13); 12/0/0; 39 без района с координатами; мин. расстояние 6707,864 м;
47 и 46; 95 из 2198; 18 ниже 0,60; sha256 86afa4ab… и 8734de19….
"""
import argparse, csv, hashlib, os, re, sys, math
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DERIVED = os.path.join(REPO, 'data', 'derived')
sys.path.insert(0, HERE)
from common.normalize import regkey
from common.hashes import sha256_file, EXPECTED_N, EXPECTED_SHA_REG, EXPECTED_SHA_DIST

def load(p):
    return list(csv.DictReader(open(p, encoding='utf-8'), delimiter=';'))

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0; p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

def check():
    fails = []
    def expect(cond, msg):
        print(('  OK  ' if cond else ' FAIL ') + msg)
        if not cond: fails.append(msg)

    # egrkn_altai_final.csv
    ef = os.path.join(DERIVED, 'egrkn_altai_final.csv')
    E = load(ef)
    altai = [r for r in E if r['in_altai_region'] == 'true']
    sha_reg = hashlib.sha256('\n'.join(sorted(r['registry_number'] for r in E)).encode()).hexdigest()
    sha_dist = hashlib.sha256('\n'.join(sorted(f"{r['record_id']}|{r['district_oktmo']}" for r in E)).encode()).hexdigest()
    districts = sum(1 for r in E if r['district_oktmo'].strip())
    expect(len(E) == 4518, f'egrkn_altai_final: записей {len(E)} (ожидалось 4518)')
    expect(len(altai) == 4516, f'in_altai_region=true: {len(altai)} (ожидалось 4516)')
    expect(sha_reg == EXPECTED_SHA_REG, f'sha256 регномеров: {sha_reg} (ожидалось 86afa4ab…)')
    expect(sha_dist == EXPECTED_SHA_DIST, f'sha256 районов: {sha_dist} (ожидалось 8734de19…)')
    expect(districts == 2131, f'районов назначено: {districts} (ожидалось 2131; не установлено {4516-districts})')
    # 39 без района с координатами
    no_dist_with_coord = sum(1 for r in altai if not r['district_oktmo'].strip() and r['lat'].strip())
    expect(no_dist_with_coord == 39, f'без района с координатами: {no_dist_with_coord} (ожидалось 39)')

    # gukn_spisok_all_fixed.csv
    L = [r for r in csv.reader(open(os.path.join(DERIVED, 'gukn_spisok_all_fixed.csv'), encoding='utf-8'), delimiter=';')][1:]
    expect(len(L) == 2204, f'gukn_spisok_all_fixed: {len(L)} (ожидалось 2204)')

    # matches_fixed.csv
    M = load(os.path.join(DERIVED, 'matches_fixed.csv'))
    exact = sum(1 for m in M if m['match_type'] == 'exact_registry')
    expect(exact == 2201, f'matches_fixed exact: {exact} (ожидалось 2201 из 2204)')

    # dump_in_list
    list_regs = set(regkey(r[7]) for r in L if r[7].strip())
    dump_in_list = sum(1 for r in altai if regkey(r['registry_number']) in list_regs)
    expect(dump_in_list == 2200, f'дамп в списке: {dump_in_list} (ожидалось 2200 из 4516)')

    # geo_diagnostics.csv: 12/0/0; расстояние до границы в ОДНОЙ метрике AEQD/WGS84
    geo = load(os.path.join(DERIVED, 'geo_diagnostics.csv'))
    cnt = Counter(g['class'] for g in geo)
    expect(cnt.get('ок', 0) == 12 and cnt.get('вне своего района', 0) == 0 and cnt.get('вне пилотных районов', 0) == 0,
            f'geo: {dict(cnt)} (ожидалось 12/0/0)')
    bd = load(os.path.join(DERIVED, 'geo_boundary_distances.csv'))
    expect(len(bd) == 12, f'geo_boundary_distances: {len(bd)} точек (ожидалось 12)')
    if bd:
        mv = min(bd, key=lambda r: float(r['dist_vertices_m']))
        ms = min(bd, key=lambda r: float(r['dist_segments_m']))
        expect(mv['record_id'] == 'E02493' and abs(float(mv['dist_vertices_m']) - 6707.864) < 1.0,
                f'мин. расстояние до границы (а) вершины AEQD: {mv["dist_vertices_m"]} м, {mv["record_id"]} (ожидалось 6707,864 E02493)')
        expect(ms['record_id'] == 'E02493' and abs(float(ms['dist_segments_m']) - 6707.864) < 1.0,
                f'мин. расстояние до границы (б) отрезки AEQD: {ms["dist_segments_m"]} м, {ms["record_id"]} (ожидалось 6707,864 E02493)')
        # условие (б) ≤ (а) для каждой точки (одна метрика)
        bad = [r['record_id'] for r in bd if float(r['dist_segments_m']) > float(r['dist_vertices_m']) + 1e-6]
        expect(not bad, f'(б) ≤ (а) нарушено для: {bad}')

    # полигон: 97 из 99 (67/19/13; 65/19/13)
    PILOTS = ('Солтонский', 'Красногорский', 'Змеиногорский')
    def stem(b):
        b = b.lower()
        for suf in ('ский', 'ской', 'цкий'):
            if b.endswith(suf): return b[:-len(suf)]
        return b
    def pilot_of(t):
        t = (t or '').lower()
        for p in PILOTS:
            if stem(p) in t: return p
        return ''
    pil_dump = [r for r in E if pilot_of((r['district_oktmo'] or '').split(' (')[0].replace('г. ', '').strip())]
    pil_list = [r for r in L if pilot_of(r[1])]
    pil_dump_in = sum(1 for r in pil_dump if regkey(r['registry_number']) in list_regs)
    expect(len(pil_dump) == 99, f'полигон дамп: {len(pil_dump)} (ожидалось 99)')
    expect(pil_dump_in == 97, f'полигон дамп в списке: {pil_dump_in} (ожидалось 97)')
    expect(len(pil_list) == 97, f'полигон список: {len(pil_list)} (ожидалось 97)')
    by_p_dump = Counter(pilot_of((r['district_oktmo'] or '').split(' (')[0].replace('г. ', '').strip()) for r in pil_dump)
    by_p_list = Counter(pilot_of(r[1]) for r in pil_list)
    expect(by_p_dump == Counter({'Змеиногорский': 67, 'Красногорский': 19, 'Солтонский': 13}),
            f'полигон дамп по районам: {dict(by_p_dump)} (ожидалось 67/19/13)')
    expect(by_p_list == Counter({'Змеиногорский': 65, 'Красногорский': 19, 'Солтонский': 13}),
            f'полигон список по районам: {dict(by_p_list)} (ожидалось 65/19/13)')

    # таблица 5: 47 и 46; 95 из 2198; 18 ниже 0.60
    zero_loss = sum(1 for r in L if r[7].strip() and len(re.sub(r'\D', '', r[7])) < 15)
    dump_regs = set(regkey(r['registry_number']) for r in E if r['registry_number'].strip())
    restored = sum(1 for r in L if r[7].strip() and len(re.sub(r'\D', '', r[7])) < 15 and regkey(r[7]) in dump_regs)
    expect(zero_loss == 47, f'регномера <15 цифр: {zero_loss} (ожидалось 47)')
    expect(restored == 46, f'восстановлено: {restored} (ожидалось 46)')

    import difflib, unicodedata
    def nn(s):
        s = unicodedata.normalize('NFC', str(s or '')).lower()
        s = re.sub(r"[«»\"„“”'(),./-]", ' ', s)
        return re.sub(r'\s+', ' ', s).strip()
    E_by_id = {r['record_id']: r for r in E}
    ratios = []
    for m in M:
        if m['match_type'] == 'exact_registry':
            lr = L[int(m['list_row_index'])]; d = E_by_id.get(m['dump_record_id'], {})
            if lr[0].strip() and d.get('name', '').strip():
                ratios.append(difflib.SequenceMatcher(None, nn(lr[0]), nn(d['name'])).ratio())
    N = len(ratios)
    mismatch = sum(1 for r in ratios if r < 1.0)
    below_60 = sum(1 for r in ratios if r < 0.60)
    expect(N == 2198, f'пар сравнения наименований: {N} (ожидалось 2198)')
    expect(mismatch == 95, f'расхождение (ratio<1.0): {mismatch} (ожидалось 95)')
    expect(below_60 == 18, f'сходство ниже 0.60: {below_60} (ожидалось 18)')

    # v2_v3_diffs
    vd = load(os.path.join(DERIVED, 'v2_v3_diffs.csv'))
    expect(len(vd) == 102, f'v2_v3_diffs: {len(vd)} (ожидалось 102)')

    print()
    print(f'ИТОГ --check: {"ВСЕ СОВПАЛО" if not fails else f"НЕ СОВПАЛО ({len(fails)}): {fails}"}')
    return 0 if not fails else 1

def run_inputs(inputs_dir, derived_dir):
    import subprocess, glob
    md = next((f for f in glob.glob(os.path.join(inputs_dir, '*.md'))), None)
    oktmo = next((f for f in glob.glob(os.path.join(inputs_dir, '*.docx')) if 'ОКТМО' in open(f, 'rb').read(65536).decode('utf-8', errors='ignore') or 'Муниципальные образования' in open(f, 'rb').read(65536).decode('utf-8', errors='ignore')), None)
    bd = inputs_dir if glob.glob(os.path.join(inputs_dir, 'boundary_*.json')) else os.path.join(REPO, 'data', 'boundaries')
    print(f'run_inputs: md={md}; oktmo={oktmo}; boundaries={bd}')
    # s06: egrkn_altai_final.csv
    subprocess.run([sys.executable, os.path.join(HERE, 's06_assign_districts.py'), '--json-dir', inputs_dir, '--oktmo-docx', oktmo, '--out', os.path.join(derived_dir, 'egrkn_altai_final.csv')], check=True)
    ef = os.path.join(derived_dir, 'egrkn_altai_final.csv')
    # s04: gukn_spisok_all_fixed.csv
    subprocess.run([sys.executable, os.path.join(HERE, 's04_parse_list.py'), '--md', md, '--out', os.path.join(derived_dir, 'gukn_spisok_all_fixed.csv')], check=True)
    lf = os.path.join(derived_dir, 'gukn_spisok_all_fixed.csv')
    # s05: matches/list_only/dump_only
    subprocess.run([sys.executable, os.path.join(HERE, 's05_link_layers.py'), '--egrkn', ef, '--list', lf, '--out-dir', derived_dir], check=True)
    # s07: geo_diagnostics
    subprocess.run([sys.executable, os.path.join(HERE, 's07_geo_control.py'), '--egrkn', ef, '--boundaries-dir', bd, '--out', os.path.join(derived_dir, 'geo_diagnostics.csv')], check=True)
    # s08: results_long + tables (требует egrkn_meta.csv — выход s03)
    meta_f = os.path.join(derived_dir, 'egrkn_meta.csv')
    if not os.path.exists(meta_f):
        subprocess.run([sys.executable, os.path.join(HERE, 's03_extract_service_fields.py'), '--json-dir', inputs_dir, '--out-dir', derived_dir], check=True)
    subprocess.run([sys.executable, os.path.join(HERE, 's08_metrics_tables.py'), '--egrkn', ef, '--meta', meta_f, '--list', lf, '--matches', os.path.join(derived_dir, 'matches_fixed.csv'), '--out-dir', derived_dir], check=True)
    print('run_inputs: завершено; запуск --check для приёмки')
    return check()

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--inputs', default=None)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        sys.exit(check())
    elif a.inputs:
        sys.exit(run_inputs(a.inputs, DERIVED))
    else:
        ap.error('укажите --inputs DIR или --check')
