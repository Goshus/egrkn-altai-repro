# -*- coding: utf-8 -*-
"""s07_geo_control.py — шаг 7 статьи: географический контроль пилотных районов (point-in-polygon).

Пути задаются через argparse; общие функции — в common/

Шаг статьи → скрипт → выход → таблица:
  «полигон: 12/0/0 с координатами; минимальное расстояние до границы 6707,864 м (E02493, AEQD/WGS84)» → s07 → geo_diagnostics.csv, geo_boundary_distances.csv → таблица 4, рис. 1.
"""
import csv, json, os, glob, math, argparse, sys
import pyproj
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.io import load_csv
from common.normalize import stem

PILOTS = ('Солтонский', 'Красногорский', 'Змеиногорский')
def pilot_of(text):
    t = (text or '').lower()
    for p in PILOTS:
        if stem(p) in t: return p
    return ''

def point_in_poly(x, y, ring):
    inside = False; n = len(ring); j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]; xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-18) + xi:
            inside = not inside
        j = i
    return inside

def load_boundaries(boundaries_dir):
    polys = {}
    for bf in sorted(glob.glob(os.path.join(boundaries_dir, 'boundary_*.json'))):
        try: obj = json.load(open(bf, encoding='utf-8'))
        except Exception: continue
        feats = obj.get('features', []) if obj.get('type') == 'FeatureCollection' else ([obj] if obj.get('type') == 'Feature' else [])
        for ft in feats:
            pr = ft.get('properties') or {}
            nm = pilot_of(pr.get('district') or pr.get('name') or pr.get('display_name') or bf)
            g = ft.get('geometry') or {}
            ring = g['coordinates'][0] if g.get('type') == 'Polygon' else (g['coordinates'][0][0] if g.get('type') == 'MultiPolygon' else None)
            if ring and nm: polys[nm] = ring
    return polys

def haversine_m(lat1, lon1, lat2, lon2):
    """Сферическое расстояние (R=6371000, haversine). Оставлено для совместимости;
    в метрике «расстояние до границы» не используется — см. AEQD-функции ниже."""
    R = 6371000.0; p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

# Одна метрика для (а) и (б) — локальная азимутальная эквидистантная
# проекция (AEQD) вокруг точки P на эллипсоиде WGS84. AEQD сохраняет расстояние от центра P,
# поэтому P→вершина в плоскости = истинное геодезическое P→вершина; P→отрезок (планарное,
# с проекцией t∈[0,1]) ≤ P→вершина, т.к. концы отрезка — вершины. Условие (б) ≤ (а) — гарантировано.
_GEOD = pyproj.Geod(ellps='WGS84')

def _aeqd_project(plat, plon, ring):
    """Локальная AEQD-проекция вокруг P; вершины в (x,y) метров, P в (0,0)."""
    proj = pyproj.Proj(proj='aeqd', lat_0=plat, lon_0=plon, ellps='WGS84')
    xs, ys = [], []
    for v in ring:
        x, y = proj(v[0], v[1])  # lon, lat -> метры
        xs.append(x); ys.append(y)
    return xs, ys

def dist_to_boundary_vertices_m(plat, plon, ring):
    """(а) Расстояние от точки P до границы полигона по вершинам в метрике AEQD/WGS84:
    min геодезическое P→вершина (= планарное расстояние от центра AEQD)."""
    xs, ys = _aeqd_project(plat, plon, ring)
    return min(math.hypot(x, y) for x, y in zip(xs, ys))

def dist_to_boundary_segments_m(plat, plon, ring):
    """(б) Расстояние от точки P до границы полигона по отрезкам в той же метрике AEQD/WGS84:
    min планарное расстояние от P (центр) до отрезка с проекцией t∈[0,1]. Гарантия (б) ≤ (а)."""
    xs, ys = _aeqd_project(plat, plon, ring)
    best = None; n = len(xs)
    for i in range(n):
        ax, ay = xs[i], ys[i]; bx, by = xs[(i+1) % n], ys[(i+1) % n]
        dx, dy = bx-ax, by-ay; L2 = dx*dx + dy*dy
        if L2 == 0:
            d = math.hypot(ax, ay)
        else:
            t = max(0.0, min(1.0, (-ax*dx - ay*dy)/L2))  # проекция из (0,0) на отрезок
            d = math.hypot(ax + t*dx, ay + t*dy)
        if best is None or d < best: best = d
    return best

def main(egrkn_csv, boundaries_dir, out_path):
    E = load_csv(egrkn_csv)
    for r in E:
        r['_base'] = (r['district_oktmo'] or '').split(' (')[0].replace('г. ', '').strip()
        r['_pilot'] = pilot_of(r['_base']) if r['district_oktmo'] else ''
    pil_dump = [r for r in E if r['_pilot']]
    polys = load_boundaries(boundaries_dir)
    geo = []
    for r in pil_dump:
        if not r['lat']: cls = 'нет координат'
        else:
            try:
                la, lo = float(r['lat']), float(r['lon'])
                hit = next((n for n, ring in polys.items() if point_in_poly(lo, la, ring)), '')
                cls = 'вне пилотных районов' if not hit else ('ок' if hit == r['_pilot'] else 'вне своего района')
            except ValueError: cls = 'невалидные координаты'
        geo.append([r['record_id'], r['_pilot'], cls, r['lat'], r['lon']])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['record_id', 'district', 'class', 'lat', 'lon'])
        w.writerows(geo)
    from collections import Counter
    cnt = Counter(g[2] for g in geo)
    # расстояния от точек внутри полигона (класс «ок») до границы района
    # (а) по вершинам и (б) по отрезкам в проекции AEQD/WGS84
    rows_bd, min_v, min_s = [], None, None
    for g in geo:
        if g[2] != 'ок': continue
        plat, plon = float(g[3]), float(g[4])
        ring = polys.get(g[1])
        if not ring: continue
        dv = dist_to_boundary_vertices_m(plat, plon, ring)
        ds = dist_to_boundary_segments_m(plat, plon, ring)
        rows_bd.append([g[0], g[1], plat, plon, round(dv, 3), round(ds, 3)])
        if min_v is None or dv < min_v[1]: min_v = (g[0], dv)
        if min_s is None or ds < min_s[1]: min_s = (g[0], ds)
    bd_path = os.path.join(os.path.dirname(out_path), 'geo_boundary_distances.csv')
    with open(bd_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['record_id', 'district', 'lat', 'lon', 'dist_vertices_m', 'dist_segments_m'])
        w.writerows(rows_bd)
    print(f's07: {len(geo)} точек; классы {dict(cnt)}')
    print(f'  расстояние до границы, (а) по вершинам: мин {min_v[1]:.3f} м ({min_v[0]})')
    print(f'  расстояние до границы, (б) по отрезкам: мин {min_s[1]:.3f} м ({min_s[0]})')
    for row in rows_bd:
        print(f'    {row[0]}: вершины {row[4]:.3f} м; отрезки {row[5]:.3f} м')
    return cnt, min_v, min_s

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--egrkn', required=True)
    ap.add_argument('--boundaries-dir', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    main(a.egrkn, a.boundaries_dir, a.out)
