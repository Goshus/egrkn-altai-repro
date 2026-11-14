# -*- coding: utf-8 -*-
"""tests/test_reproduce.py — проверка контрольных значений пайплайна (pytest).

Запуск: pytest tests/test_reproduce.py
Эквивалентно `python src/run_all.py --check`, но как модульные проверки.
"""
import os, sys, csv, hashlib, math
from collections import Counter, defaultdict
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DERIVED = os.path.join(REPO, 'data', 'derived')
sys.path.insert(0, os.path.join(REPO, 'src'))
from common.normalize import regkey
from common.hashes import EXPECTED_SHA_REG, EXPECTED_SHA_DIST

def _load(p):
    return list(csv.DictReader(open(p, encoding='utf-8'), delimiter=';'))

def test_egrkn_records():
    E = _load(os.path.join(DERIVED, 'egrkn_altai_final.csv'))
    altai = [r for r in E if r['in_altai_region'] == 'true']
    assert len(E) == 4518
    assert len(altai) == 4516

def test_sha256_regnumbers():
    E = _load(os.path.join(DERIVED, 'egrkn_altai_final.csv'))
    sha = hashlib.sha256('\n'.join(sorted(r['registry_number'] for r in E)).encode()).hexdigest()
    assert sha == EXPECTED_SHA_REG

def test_sha256_districts():
    E = _load(os.path.join(DERIVED, 'egrkn_altai_final.csv'))
    sha = hashlib.sha256('\n'.join(sorted(f"{r['record_id']}|{r['district_oktmo']}" for r in E)).encode()).hexdigest()
    assert sha == EXPECTED_SHA_DIST

def test_districts_assigned():
    E = _load(os.path.join(DERIVED, 'egrkn_altai_final.csv'))
    n = sum(1 for r in E if r['district_oktmo'].strip())
    assert n == 2131

def test_no_district_with_coords():
    E = _load(os.path.join(DERIVED, 'egrkn_altai_final.csv'))
    n = sum(1 for r in E if r['in_altai_region'] == 'true' and not r['district_oktmo'].strip() and r['lat'].strip())
    assert n == 39

def test_list_records():
    L = [r for r in csv.reader(open(os.path.join(DERIVED, 'gukn_spisok_all_fixed.csv'), encoding='utf-8'), delimiter=';')][1:]
    assert len(L) == 2204

def test_exact_matches():
    M = _load(os.path.join(DERIVED, 'matches_fixed.csv'))
    assert sum(1 for m in M if m['match_type'] == 'exact_registry') == 2201

def test_dump_in_list():
    E = _load(os.path.join(DERIVED, 'egrkn_altai_final.csv'))
    L = [r for r in csv.reader(open(os.path.join(DERIVED, 'gukn_spisok_all_fixed.csv'), encoding='utf-8'), delimiter=';')][1:]
    list_regs = set(regkey(r[7]) for r in L if r[7].strip())
    altai = [r for r in E if r['in_altai_region'] == 'true']
    assert sum(1 for r in altai if regkey(r['registry_number']) in list_regs) == 2200

def test_geo_classes():
    geo = _load(os.path.join(DERIVED, 'geo_diagnostics.csv'))
    cnt = Counter(g['class'] for g in geo)
    assert cnt.get('ок', 0) == 12 and cnt.get('вне своего района', 0) == 0 and cnt.get('вне пилотных районов', 0) == 0

def test_polygon():
    E = _load(os.path.join(DERIVED, 'egrkn_altai_final.csv'))
    L = [r for r in csv.reader(open(os.path.join(DERIVED, 'gukn_spisok_all_fixed.csv'), encoding='utf-8'), delimiter=';')][1:]
    list_regs = set(regkey(r[7]) for r in L if r[7].strip())
    def stem(b):
        b = b.lower()
        for s in ('ский', 'ской', 'цкий'):
            if b.endswith(s): return b[:-len(s)]
        return b
    def pilot_of(t):
        for p in ('Солтонский', 'Красногорский', 'Змеиногорский'):
            if stem(p) in (t or '').lower(): return p
        return ''
    pil_dump = [r for r in E if pilot_of((r['district_oktmo'] or '').split(' (')[0].replace('г. ', '').strip())]
    pil_list = [r for r in L if pilot_of(r[1])]
    assert len(pil_dump) == 99
    assert sum(1 for r in pil_dump if regkey(r['registry_number']) in list_regs) == 97
    assert len(pil_list) == 97
    by_dump = Counter(pilot_of((r['district_oktmo'] or '').split(' (')[0].replace('г. ', '').strip()) for r in pil_dump)
    assert by_dump == Counter({'Змеиногорский': 67, 'Красногорский': 19, 'Солтонский': 13})
    by_list = Counter(pilot_of(r[1]) for r in pil_list)
    assert by_list == Counter({'Змеиногорский': 65, 'Красногорский': 19, 'Солтонский': 13})

def test_regnumbers_zero_loss():
    import re
    L = [r for r in csv.reader(open(os.path.join(DERIVED, 'gukn_spisok_all_fixed.csv'), encoding='utf-8'), delimiter=';')][1:]
    zl = sum(1 for r in L if r[7].strip() and len(re.sub(r'\D', '', r[7])) < 15)
    assert zl == 47
    E = _load(os.path.join(DERIVED, 'egrkn_altai_final.csv'))
    dump_regs = set(regkey(r['registry_number']) for r in E if r['registry_number'].strip())
    restored = sum(1 for r in L if r[7].strip() and len(re.sub(r'\D', '', r[7])) < 15 and regkey(r[7]) in dump_regs)
    assert restored == 46

def test_name_discrepancies():
    import re, difflib, unicodedata
    E = _load(os.path.join(DERIVED, 'egrkn_altai_final.csv'))
    L = [r for r in csv.reader(open(os.path.join(DERIVED, 'gukn_spisok_all_fixed.csv'), encoding='utf-8'), delimiter=';')][1:]
    M = _load(os.path.join(DERIVED, 'matches_fixed.csv'))
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
    assert len(ratios) == 2198
    assert sum(1 for r in ratios if r < 1.0) == 95
    assert sum(1 for r in ratios if r < 0.60) == 18

def test_v2_v3_diffs():
    vd = _load(os.path.join(DERIVED, 'v2_v3_diffs.csv'))
    assert len(vd) == 102

def test_boundary_distances():
    """расстояние от 12 точек внутри полигона до границы района
    в ОДНОЙ метрике AEQD/WGS84. (а) вершины = (б) отрезки = 6707,864 м (E02493),
    т.к. ближайшая точка границы — вершина; условие (б) ≤ (а) для каждой точки."""
    bd = _load(os.path.join(DERIVED, 'geo_boundary_distances.csv'))
    assert len(bd) == 12
    mv = min(bd, key=lambda r: float(r['dist_vertices_m']))
    assert mv['record_id'] == 'E02493'
    assert abs(float(mv['dist_vertices_m']) - 6707.864) < 1.0
    ms = min(bd, key=lambda r: float(r['dist_segments_m']))
    assert ms['record_id'] == 'E02493'
    assert abs(float(ms['dist_segments_m']) - 6707.864) < 1.0
    # одна метрика: (б) ≤ (а) для каждой точки
    for r in bd:
        assert float(r['dist_segments_m']) <= float(r['dist_vertices_m']) + 1e-6
