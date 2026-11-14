# geo_qc_blindzone.py — заход 2б: геодиагностика + метрики качества + модуль «слепая зона»
# Вход в текущей папке: egrkn_altai.csv, gukn_registry_pilot.csv, gukn_spisok_all.csv, matches.csv,
#   boundary_1.json / boundary_2.json / boundary_3.json (или *.geojson), prikazy_vokn_2019_2026.csv
# Выход: geo_diagnostics.csv, pilot_points.png (если есть matplotlib), qc_metrics.csv,
#   verification_sample.csv, blind_zone_report.csv
import csv, json, math, os, random, re, unicodedata
from collections import Counter

SEED = 42
DISTRICT_PATTERNS = {'Солтонский': ['солтонск'], 'Красногорский': ['красногорск'], 'Змеиногорский': ['змеиногорск']}
PILOT = tuple(DISTRICT_PATTERNS)
DUP_MAX_M = 150.0
STOP = {'стоянка','курган','могильник','поселение','памятник','братская','одиночный','грунтовый',
        'церковь','курганный','место','объект','селище','городище','могила','и','в','на','у','от','имени'}

def norm_name(s):
    if not s: return ''
    s = unicodedata.normalize('NFC', str(s)).lower()
    s = re.sub(r"[«»\"„“”'(),./-]", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def canon(name):
    n = (name or '').lower()
    for d, pats in DISTRICT_PATTERNS.items():
        if any(p in n for p in pats): return d
    return ''

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0; p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

def load(p, delim=';'):
    return list(csv.DictReader(open(p, encoding='utf-8'), delimiter=delim)) if os.path.exists(p) else []

def main():
    E_all = load('egrkn_altai.csv'); E = [r for r in E_all if r.get('district') in PILOT]
    G = load('gukn_registry_pilot.csv'); M = load('matches.csv')
    # --- геодиагностика (пилотный срез ЕГРОКН против границ) ---
    polys = {}
    import glob as _glob
    bfiles = sorted(_glob.glob('boundary_*.json')) + sorted(_glob.glob('*.geojson'))
    if bfiles:
        from matplotlib.path import Path
        for bf in bfiles:
            try:
                fc = json.load(open(bf, encoding='utf-8'))
            except Exception as e:
                print(f'границы: {bf}: ошибка чтения {type(e).__name__}'); continue
            feats = fc.get('features', []) if isinstance(fc, dict) and fc.get('type') == 'FeatureCollection' else ([fc] if isinstance(fc, dict) and fc.get('type') == 'Feature' else [])
            stem = os.path.splitext(os.path.basename(bf))[0]
            for ft in feats:
                props = ft.get('properties') or {}
                raw_name = props.get('district') or props.get('name') or props.get('display_name') or stem
                name = canon(raw_name)
                g = ft.get('geometry') or {}
                ring = g['coordinates'][0] if g.get('type') == 'Polygon' else (g['coordinates'][0][0] if g.get('type') == 'MultiPolygon' else None)
                if ring and name: polys[name] = Path(ring)
        print('границы загружены из:', bfiles, '->', list(polys))
    out = []
    for r in E:
        lat, lon = r.get('lat',''), r.get('lon','')
        if lat in ('', None): out.append([r['record_id'], r['district'], '', 'нет координат', '', '']); continue
        try: p = (float(lon), float(lat))
        except ValueError: out.append([r['record_id'], r['district'], '', 'невалидные координаты', lat, lon]); continue
        hit = next((n for n, pth in polys.items() if pth.contains_point(p)), '')
        cls = 'вне пилотных районов' if not hit else ('ок' if hit == r['district'] else 'вне своего района')
        out.append([r['record_id'], r['district'], hit, cls, lat, lon])
    with open('geo_diagnostics.csv','w',newline='',encoding='utf-8') as f:
        csv.writer(f, delimiter=';').writerows([['record_id','district_declared','district_geo','class','lat','lon']] + out)
    if polys:
        try:
            import matplotlib
            matplotlib.use('Agg'); import matplotlib.pyplot as plt
            plt.rcParams['font.family'] = 'DejaVu Sans'
            fig, ax = plt.subplots(figsize=(8, 6))
            colors = {'ок':'green','нет координат':'gray','невалидные координаты':'orange','вне пилотных районов':'red','вне своего района':'blue'}
            for name, pth in polys.items():
                v = pth.vertices; ax.plot(list(v[:,0])+[v[0,0]], list(v[:,1])+[v[0,1]], 'k-', lw=1)
                ax.annotate(name, (v[:,0].mean(), v[:,1].mean()), fontsize=8)
            for row in out:
                if row[4]: ax.scatter(float(row[5]), float(row[4]), c=colors.get(row[3],'black'), s=25)
            ax.set_xlabel('lon'); ax.set_ylabel('lat'); ax.set_title('ЕГРОКН: геодиагностика (пилот)')
            fig.savefig('pilot_points.png', dpi=150); plt.close(fig)
        except Exception as e:
            print('карта пропущена:', e)
    # --- метрики ---
    met = []
    def add(m, v, u, c): met.append([m, v, u, c])
    if E_all:
        withc_all = [r for r in E_all if r.get('lat')]
        add('M0_krai_records', len(E_all), 'записей', 'алтайский срез дампа')
        add('M2a_krai_share_with_coords', round(len(withc_all)/len(E_all), 4), 'доля', 'по краю')
        for src, cnt in Counter(r.get('coord_source','') or 'нет' for r in E_all).items():
            add(f'M2c_krai_coord_source_{src}', cnt, 'записей', 'происхождение координат (край)')
    if E:
        add('M0_pilot_records', len(E), 'записей', 'пилотный срез дампа')
        withc = [r for r in E if r.get('lat')]
        add('M2a_pilot_share_with_coords', round(len(withc)/len(E), 4), 'доля', 'пилот')
        bad = [d for d in out if d[3] == 'вне своего района']
        add('M2b_outside_district', round(len(bad)/len(withc), 4) if withc else '', 'доля', 'точки вне своего района (пилот)')
        dups = 0
        for i in range(len(E)):
            for j in range(i+1, len(E)):
                if E[i]['name_norm'] and E[i]['name_norm'] == E[j]['name_norm'] and E[i].get('lat') and E[j].get('lat'):
                    if haversine_m(float(E[i]['lat']), float(E[i]['lon']), float(E[j]['lat']), float(E[j]['lon'])) <= DUP_MAX_M: dups += 1
        add('M3_duplicate_pairs_S1', dups, 'пары', 'name_norm + <=150 м (пилот)')
        for fld in ('address_raw','category','registry_number'):
            add(f'M4_fill_{fld}', round(sum(1 for r in E if r.get(fld))/len(E), 4), 'доля', f'заполненность {fld} (пилот)')
        for cls, cnt in Counter(d[3] for d in out).items():
            add(f'M5_geo_{cls}', cnt, 'записей', 'класс геодиагностики (пилот)')
    if G:
        cov = len({m['id_gukn'] for m in M}) / len(G)
        add('M1a_coverage_spisok_by_dump', round(cov, 4), 'доля', 'покрытие краевого списка дампом (пилот)')
        add('M5_orphans_spisok', len(G) - len({m['id_gukn'] for m in M}), 'записей', 'записи списка без кандидата в дампе')
    with open('qc_metrics.csv','w',newline='',encoding='utf-8') as f:
        csv.writer(f, delimiter=';').writerows([['metric','value','unit','comment']] + met)
    # --- верификационная выборка (заполняет только человек) ---
    random.seed(SEED)
    pool = [('S1', r['record_id']) for r in E] + [('S2', r['record_id']) for r in G]
    k = min(max(20, int(0.1*len(pool))), len(pool)) if pool else 0
    sample = random.sample(pool, k) if k else []
    with open('verification_sample.csv','w',newline='',encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['record_id','source','field_to_check','value','verdict','checker','check_date','comment'])
        for src, rid in sample: w.writerow([rid, src, '', '', '', '', '', ''])
    # --- модуль «слепая зона» ---
    corpus = [('ЕГРОКН', r['record_id'], norm_name(r['name_raw']), (r.get('address_raw') or '').lower()) for r in E_all]
    for i, r in enumerate(load('gukn_spisok_all.csv')):
        corpus.append(('Список_ГУКН', f'row{i}', norm_name(r.get('name_raw','')), ((r.get('address') or '') + ' ' + (r.get('district_raw') or '')).lower()))
    res = []
    for p in load('prikazy_vokn_2019_2026.csv'):
        kt = {t for t in norm_name(p['object_name']).split() if t not in STOP and len(t) > 2}
        name_hits, addr_hits = [], []
        for src, rid, nn, addr in corpus:
            if kt and kt <= set(nn.split()): name_hits.append(f'{src}:{rid}')
            elif kt and kt <= set(addr.split()): addr_hits.append(f'{src}:{rid}')
        verdict = 'НАЙДЕН по имени' if name_hits else ('ТОЛЬКО адресное совпадение (не объект)' if addr_hits else 'НЕ НАЙДЕН')
        res.append([p['date'], p['number'], p['object_name'], verdict, '; '.join(name_hits[:5]), '; '.join(addr_hits[:5])])
    with open('blind_zone_report.csv','w',newline='',encoding='utf-8') as f:
        csv.writer(f, delimiter=';').writerows([['prikaz_date','prikaz_number','object_name','verdict','name_hits','address_hits']] + res)
    print(f'geo={len(out)}, метрик={len(met)}, выборка={len(sample)}, слепая зона={dict(Counter(r[3] for r in res))}')

if __name__ == '__main__': main()
