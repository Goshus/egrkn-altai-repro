# -*- coding: utf-8 -*-
"""s10_figures.py — шаг 10 статьи: рисунки 1 (геополигон) и 2 (схема процедуры).

RECONSTRUCTED — восстановлен по результатам и изображениям, не исходный код автора.
Рис. 1 (Ris1_geopolygon.png) и Рис. 2 (Ris2_flow.png) созданы автором; исходного кода рисунков нет.
Два режима: as_published (повторяет рисунки статьи) и revised (с правками задачи захода 12).

Числа берутся из data/derived/results_long_fixed.csv и geo_diagnostics.csv, не вводятся вручную.

Рис. 1 revised: без заголовка внутри картинки; равный масштаб осей с поправкой на широту (≈1/cos 51,5°)
на обеих панелях; метка «12 записей (точки сливаются, г. Змеиногорск)»; линейка масштаба;
подпись «WGS 84 (принята; в записи реестра не указана)»; правая панель — увеличенный фрагмент.
Рис. 2 revised: «11»→«11 объектов», «8»→«8 объектов»; ✓/✗ вместо различия только цветом;
нейтральные соединители вместо стрелок последовательности; сноска «для приказа № 183 совпадение вероятное».
"""
import csv, os, math, argparse, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.io import load_csv

def load_boundaries(boundaries_dir):
    import json, glob
    from common.normalize import stem
    PILOTS = ('Солтонский', 'Красногорский', 'Змеиногорский')
    def pilot_of(text):
        t = (text or '').lower()
        for p in PILOTS:
            if stem(p) in t: return p
        return ''
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

def fig1(geo_csv, boundaries_dir, out_path, mode='revised'):
    """Рис. 1 — геополигон пилотных районов (заход 14, задача 3).

    Две панели: обзорная (слева) с рамкой увеличенного фрагмента и масштабной линейкой
    в свободном углу; увеличенный фрагмент вокруг 12 точек (справа). Оси «Широта, ° с. ш.» /
    «Долгота, ° в. д.»; без заголовков панелей; подпись «Красногорский» с линией-указателем;
    легенда «записи с координатами внутри своего пилотного района»; справка
    «всего записей / с координатами»: Змеиногорский 67/12, Красногорский 19/0, Солтонский 13/0
    (вычисляется из geo_diagnostics.csv); WGS 84 (принята; в записи реестра не указана);
    © участники OpenStreetMap, ODbL 1.0. PNG 300 dpi.
    """
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.font_manager as fm
    for fp in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf'):
        try: fm.fontManager.addfont(fp)
        except Exception: pass
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Noto Sans SC']; plt.rcParams['axes.unicode_minus'] = False
    geo = load_csv(geo_csv)
    polys = load_boundaries(boundaries_dir)
    ok = [g for g in geo if g['class'] == 'ок']
    # справка: всего / с координатами по пилотным районам
    from collections import Counter
    total = Counter(g['district'] for g in geo)
    withc = Counter(g['district'] for g in geo if g['lat'])
    info = {d: (total.get(d, 0), withc.get(d, 0)) for d in ('Змеиногорский', 'Красногорский', 'Солтонский')}

    # границы увеличенного фрагмента — вокруг всех 12 точек с полем
    lats = [float(g['lat']) for g in ok]; lons = [float(g['lon']) for g in ok]
    pad = 0.004
    zm = (min(lats)-pad, max(lats)+pad, min(lons)-pad, max(lons)+pad)  # lat0,lat1,lon0,lon1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6.6), constrained_layout=True)
    fig.get_layout_engine().set(rect=[0.0, 0.05, 1.0, 1.0])  # резерв низа под подпись
    lat_mid = 51.5; asp = 1.0 / math.cos(math.radians(lat_mid))
    for ax in (ax1, ax2): ax.set_aspect(asp)
    ax1.set_xlabel('Долгота, ° в. д.'); ax1.set_ylabel('Широта, ° с. ш.')
    ax2.set_xlabel('Долгота, ° в. д.'); ax2.set_ylabel('Широта, ° с. ш.')

    # --- обзорная панель ---
    for n, ring in polys.items():
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        ax1.plot(xs, ys, 'k-', lw=0.9)
        cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
        if n == 'Красногорский':
            # маленький полигон — подпись с линией-указателем в свободное место
            ax1.annotate(n, xy=(cx, cy), xytext=(cx-0.35, cy+0.25), fontsize=8,
                         arrowprops=dict(arrowstyle='-', lw=0.6))
        else:
            ax1.text(cx, cy, n, fontsize=8, ha='center', va='center')
    # точки (только с координатами)
    for g in geo:
        if g['lat']:
            ax1.scatter(float(g['lon']), float(g['lat']), c='#2ca02c', edgecolor='black', linewidth=0.4, s=18, alpha=0.9, zorder=5)
    # рамка увеличенного фрагмента + угловые засечки-«мишень» (видны на обзорной шкале)
    ax1.add_patch(Rectangle((zm[2], zm[0]), zm[3]-zm[2], zm[1]-zm[0], fill=False, edgecolor='red', lw=1.5, linestyle='--', zorder=6))
    tk_lon, tk_lat = 0.18, 0.05  # длина засечек в градусах (видны на обзоре)
    for cx, cy in [(zm[2], zm[0]), (zm[3], zm[0]), (zm[2], zm[1]), (zm[3], zm[1])]:
        ax1.plot([cx-tk_lon, cx+tk_lon], [cy, cy], 'r-', lw=1.6, zorder=6)
        ax1.plot([cx, cx], [cy-tk_lat, cy+tk_lat], 'r-', lw=1.6, zorder=6)
    # масштабная линейка ~10 км в свободный угол (верхний-левый)
    lat0 = 51.95; lon0 = 79.3; km_per_deg = 111.32; deg10 = 10 / (km_per_deg * math.cos(math.radians(lat0)))
    ax1.plot([lon0, lon0 + deg10], [lat0, lat0], 'k-', lw=2.5)
    ax1.plot([lon0, lon0], [lat0-0.03, lat0+0.03], 'k-', lw=1); ax1.plot([lon0+deg10, lon0+deg10], [lat0-0.03, lat0+0.03], 'k-', lw=1)
    ax1.text(lon0 + deg10/2, lat0 + 0.06, '10 км', fontsize=7, ha='center')
    # легенда + справка
    ax1.scatter([], [], c='#2ca02c', edgecolor='black', linewidth=0.4, s=30, label='записи с координатами\nвнутри своего пилотного района')
    ax1.legend(loc='lower left', fontsize=7, framealpha=0.9)
    infotxt = 'всего / с координатами:\n' + '\n'.join(f'{d}: {v[0]}/{v[1]}' for d, v in info.items())
    ax1.text(0.98, 0.02, infotxt, transform=ax1.transAxes, fontsize=7, ha='right', va='bottom',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.9))

    # --- увеличенный фрагмент ---
    for n, ring in polys.items():
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        ax2.plot(xs, ys, 'k-', lw=1.0)
    for g in ok:
        ax2.scatter(float(g['lon']), float(g['lat']), c='#2ca02c', edgecolor='black', linewidth=0.5, s=45, alpha=0.9, zorder=5)
    ax2.set_xlim(zm[2], zm[3]); ax2.set_ylim(zm[0], zm[1])
    ax2.text(0.02, 0.98, f'г. Змеиногорск\n{len(ok)} записей', transform=ax2.transAxes, fontsize=8, va='top',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.9))

    fig.text(0.5, 0.02, 'WGS 84 (принята; в записи реестра не указана). © участники OpenStreetMap, ODbL 1.0.',
             ha='center', fontsize=8)
    if mode == 'as_published':
        fig.suptitle('ЕГРОКН: геодиагностика пилотных районов')
    fig.savefig(out_path, dpi=300); plt.close(fig)
    print(f's10 fig1 ({mode}) -> {out_path}; точек ок: {len(ok)}; справка {info}')
    return len(ok)

def fig2(perechen_csv, auto_csv, out_path, mode='revised'):
    """Рис. 2 — сопоставление приказов ВОКН с источниками (матрица 3×4, восстановлено по Ris2_flow.png).

    Структура (по изображению автора, VLM-описание захода 13):
      шапка: «Приказ о включении в перечень выявленных» | «Действующий перечень выявленных (04.2026)»
             | «Реестр (ЕГРОКН)» | «Краевой список»;
      строка 2019–2024 (11 приказов) и 2025–2026 (8 приказов);
      цвета: голубой — шапка, зелёный — совпадение, розовый — отсутствие.

    Числа вычисляются из данных (не вводятся вручную), заход 14:
      - 11 / 8 — число приказов по волнам в data/manual/perechen_check.csv;
      - «в перечне» — in_perechen из perechen_check.csv (сопоставление 19 приказов с 8 объектами
        gukn_vokn.csv по номеру приказа); ранним 11 — «нет» (0 из 11), поздним 8 — «да» (8 из 8);
        согласовано с таблицей 5 статьи (8 из 8);
      - «в реестре» — reestr_status из perechen_check.csv: ранние — 10 подтверждённых + 1 вероятное
        (приказ № 183, «ВЕРОЯТНО ТОТ ЖЕ ОБЪЕКТ») = 11 (согласовано с таблицей 5: 11 из 11);
        поздние — 0 из 8 (новые выявленные, в ЕГРОКН отсутствуют);
      - «в списке» — s09_orders_trace.py (auto_csv): все 19 «НЕ НАЙДЕН» (0 из 11, 0 из 8).

    Режим revised (заход 14): без ✓/✗; в ячейке реестра ранней группы — «10 подтв., 1 вероятн.*»;
    сноска под рисунком; нейтральные соединители; подпись — показано наличие записей в массивах,
    а не обязательная последовательность. Режим as_published — авторская схема (стрелки, 11 из 11).
    """
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.font_manager as fm
    for fp in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf'):
        try: fm.fontManager.addfont(fp)
        except Exception: pass
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Noto Sans SC']; plt.rcParams['axes.unicode_minus'] = False

    # --- числа из данных ---
    rows = load_csv(perechen_csv)
    waves = {'2019–2024': [], '2025–2026': []}
    for r in rows:
        year = int(r['prikaz_date'].split('.')[-1])
        waves['2019–2024' if year <= 2024 else '2025–2026'].append(r)
    auto = {r['prikaz_number']: r for r in load_csv(auto_csv)} if auto_csv and os.path.exists(auto_csv) else {}
    data = {}
    for w, rs in waves.items():
        n = len(rs)
        perechen = sum(1 for r in rs if r['in_perechen'] == 'да')
        conf = sum(1 for r in rs if r['reestr_status'] == 'подтверждённое')
        prob = sum(1 for r in rs if r['reestr_status'] == 'вероятное')
        spisok = sum(1 for r in rs if auto.get(r['prikaz_number'], {}).get('in_list', 'НЕ НАЙДЕН').startswith('НАЙДЕН'))
        data[w] = (n, perechen, conf, prob, spisok)

    HDR = ['Приказ о включении\nв перечень выявленных', 'Действующий перечень\nвыявленных (04.2026)', 'Реестр\n(ЕГРОКН)', 'Краевой\nсписок']
    C_HDR, C_WAVE, C_OK, C_NO, C_PROB = '#cfe8ff', '#f0f0f0', '#c8f0c8', '#f8d0d0', '#fff3c0'
    fig, ax = plt.subplots(figsize=(11, 6.2), constrained_layout=True); ax.axis('off')
    ax.set_xlim(0, 4); ax.set_ylim(-0.6, 3)
    xs = [0.05, 1.05, 2.05, 3.05]; bw, bh = 0.9, 0.62
    ys = {'hdr': 2.3, '2019–2024': 1.25, '2025–2026': 0.25}

    def cell(x, y, text, color, fs=8.5, weight='normal'):
        ax.add_patch(plt.Rectangle((x, y - bh/2), bw, bh, facecolor=color, edgecolor='black', lw=0.8))
        ax.text(x + bw/2, y, text, ha='center', va='center', fontsize=fs, fontweight=weight)

    for i, h in enumerate(HDR):
        cell(xs[i], ys['hdr'], h, C_HDR, fs=8.5, weight='bold')

    for w, y in (('2019–2024', ys['2019–2024']), ('2025–2026', ys['2025–2026'])):
        n, perechen, conf, prob, spisok = data[w]
        cell(xs[0], y, f'{w} гг.\n{n} приказов', C_WAVE)
        # перечень
        cell(xs[1], y, f'{perechen} из {n}', C_OK if perechen == n else (C_NO if perechen == 0 else C_PROB), fs=10)
        # реестр
        if w == '2019–2024' and mode == 'revised':
            cell(xs[2], y, f'{conf} подтв.,\n{prob} вероятн.*', C_PROB, fs=9)
        else:
            reestr = conf + prob
            cell(xs[2], y, f'{reestr} из {n}', C_OK if reestr == n else (C_NO if reestr == 0 else C_PROB), fs=10)
        # список
        cell(xs[3], y, f'{spisok} из {n}', C_OK if spisok == n else (C_NO if spisok == 0 else C_PROB), fs=10)
        # соединители
        arrow = dict(arrowstyle='-', lw=0.8) if mode == 'revised' else dict(arrowstyle='->', lw=0.9)
        for i in range(3):
            ax.annotate('', xy=(xs[i+1], y), xytext=(xs[i] + bw, y), arrowprops=arrow)

    if mode == 'revised':
        ax.text(2, -0.25, '* приказ № 183 — совпадение вероятное («ВЕРОЯТНО ТОТ ЖЕ ОБЪЕКТ»)', ha='center', fontsize=8, style='italic')
        ax.text(2, -0.5, 'Показано наличие записей в массивах, а не обязательная последовательность действий.', ha='center', fontsize=8, color='dimgray')
    fig.savefig(out_path, dpi=300); plt.close(fig)
    print(f's10 fig2 ({mode}) -> {out_path}')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--geo', required=True)
    ap.add_argument('--boundaries-dir', required=True)
    ap.add_argument('--results', required=False, default=None, help='results_long_fixed.csv (не используется в заходе 14; оставлено для совместимости)')
    ap.add_argument('--perechen', required=True, help='data/manual/perechen_check.csv (для рис. 2: in_perechen, reestr_status)')
    ap.add_argument('--auto', default=None, help='blind_zone_report.csv от s09 (для рис. 2: «в списке»)')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--mode', choices=['as_published', 'revised', 'both'], default='both')
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    modes = ['as_published', 'revised'] if a.mode == 'both' else [a.mode]
    for m in modes:
        fig1(a.geo, a.boundaries_dir, os.path.join(a.out_dir, f'Ris1_geopolygon_{m}.png'), m)
        fig2(a.perechen, a.auto, os.path.join(a.out_dir, f'Ris2_flow_{m}.png'), m)
