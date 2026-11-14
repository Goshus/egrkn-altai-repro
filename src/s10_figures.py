# -*- coding: utf-8 -*-
"""s10_figures.py — шаг 10 статьи: рисунки 1 (геополигон) и 2 (схема процедуры).

RECONSTRUCTED — восстановлен по результатам и изображениям, не исходный код автора.
Рис. 1 (Ris1_geopolygon.png) и Рис. 2 (Ris2_flow.png) созданы автором; исходного кода рисунков нет.
Два режима: as_published (повторяет рисунки статьи) и revised (с правками заходов 12→15).

Числа берутся из data/derived/results_long_fixed.csv и geo_diagnostics.csv, не вводятся вручную.

Рис. 1 revised (заход 15): тонкая прямоугольная рамка фрагмента на обзорной карте со
связующими линиями (ConnectionPatch) к правой панели-фрагменту (без засечек-мишень);
легенда вынесена за контуры районов (вниз фигуры); подписи районов с линиями-указателями
в свободные зоны (без наложения на границы); компактный макет, панели выровнены по верху
(anchor='N'); десятичная запятая в подписях осей и справке (FuncFormatter); метка
«12 записей (г. Змеиногорск)»; линейка масштаба 10 км; WGS 84 (принята; в записи не указана).
Числа не меняются: Змеиногорский 67/12, Красногорский 19/0, Солтонский 13/0.

Рис. 2 revised (заход 15): «10 подтверждённых, 1 вероятное*» без сокращений; примечание
тёмным цветом; для значений «нет» — нейтральный серый фон, цвет только для «есть»
(зелёный) и «вероятное» (жёлтый); строка с расшифровкой цветов.
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
    """Рис. 1 — геополигон пилотных районов (заход 15).

    Две панели, выровненные по верху (anchor='N'): обзорная (слева) с тонкой прямоугольной
    рамкой увеличенного фрагмента и масштабной линейкой; увеличенный фрагмент вокруг 12 точек
    (справа). Связующие линии (ConnectionPatch) от правых углов рамки к левым углам панели
    фрагмента. Легенда вынесена за контуры районов (вниз фигуры). Подписи районов — с
    линиями-указателями в свободные зоны, без наложения на границы. Десятичная запятая в
    подписях осей и справке. Оси «Широта, ° с. ш.» / «Долгота, ° в. д.»; без заголовков панелей.
    Справка «всего записей / с координатами»: Змеиногорский 67/12, Красногорский 19/0,
    Солтонский 13/0 (вычисляется из geo_diagnostics.csv); WGS 84 (принята; в записи реестра
    не указана); © участники OpenStreetMap, ODbL 1.0. PNG 300 dpi.
    """
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.font_manager as fm
    for fp in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf'):
        try: fm.fontManager.addfont(fp)
        except Exception: pass
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, ConnectionPatch
    from matplotlib.ticker import FuncFormatter
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Noto Sans SC']; plt.rcParams['axes.unicode_minus'] = False

    # десятичная запятая в числовых подписях
    comma = FuncFormatter(lambda x, pos: ('%g' % x).replace('.', ','))

    geo = load_csv(geo_csv)
    polys = load_boundaries(boundaries_dir)
    ok = [g for g in geo if g['class'] == 'ок']
    from collections import Counter
    total = Counter(g['district'] for g in geo)
    withc = Counter(g['district'] for g in geo if g['lat'])
    info = {d: (total.get(d, 0), withc.get(d, 0)) for d in ('Змеиногорский', 'Красногорский', 'Солтонский')}

    # границы увеличенного фрагмента — вокруг всех 12 точек с полем
    lats = [float(g['lat']) for g in ok]; lons = [float(g['lon']) for g in ok]
    pad = 0.004
    zm = (min(lats)-pad, max(lats)+pad, min(lons)-pad, max(lons)+pad)  # lat0,lat1,lon0,lon1

    # общий bbox районов для обзорной панели + поле
    all_lons, all_lats = [], []
    for ring in polys.values():
        all_lons += [p[0] for p in ring]; all_lats += [p[1] for p in ring]
    mlon = max(all_lons)-min(all_lons); mlat = max(all_lats)-min(all_lats)
    ext_lon = mlon*0.06; ext_lat = mlat*0.06
    lon0, lon1 = min(all_lons)-ext_lon, max(all_lons)+ext_lon
    lat0, lat1 = min(all_lats)-ext_lat, max(all_lats)+ext_lat

    # компактный макет: ax1 (обзорная) шире, ax2 (фрагмент) уже; выровнены по верху (anchor='N')
    fig = plt.figure(figsize=(12, 6.0))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.7, 1.0],
                          left=0.055, right=0.985, top=0.965, bottom=0.135, wspace=0.22)
    ax1 = fig.add_subplot(gs[0, 0]); ax2 = fig.add_subplot(gs[0, 1])
    lat_mid = 51.5; asp = 1.0 / math.cos(math.radians(lat_mid))
    for ax in (ax1, ax2):
        ax.set_aspect(asp); ax.set_anchor('N')
    ax1.set_xlim(lon0, lon1); ax1.set_ylim(lat0, lat1)
    ax1.set_xlabel('Долгота, ° в. д.'); ax1.set_ylabel('Широта, ° с. ш.')
    ax1.xaxis.set_major_formatter(comma); ax1.yaxis.set_major_formatter(comma)
    ax2.set_xlabel('Долгота, ° в. д.'); ax2.set_ylabel('Широта, ° с. ш.')
    ax2.xaxis.set_major_formatter(comma); ax2.yaxis.set_major_formatter(comma)

    # --- обзорная панель: районы ---
    cents = {}
    for n, ring in polys.items():
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        ax1.plot(xs, ys, 'k-', lw=0.8)
        cents[n] = (sum(xs)/len(xs), sum(ys)/len(ys))
    # точки (только с координатами — 12 в Змеиногорском)
    for g in geo:
        if g['lat']:
            ax1.scatter(float(g['lon']), float(g['lat']), c='#2ca02c', edgecolor='black', linewidth=0.4, s=16, alpha=0.9, zorder=5)

    # --- тонкая прямоугольная рамка фрагмента (без засечек-мишень) ---
    ax1.add_patch(Rectangle((zm[2], zm[0]), zm[3]-zm[2], zm[1]-zm[0],
                            fill=False, edgecolor='red', lw=1.0, linestyle='-', zorder=6))

    # --- подписи районов с линиями-указателями в свободные зоны (без наложения на границы) ---
    # Змеиногорский (большой, запад): подпись в свободную зону запад-верх, указатель к центроиду
    cx, cy = cents['Змеиногорский']
    ax1.annotate('Змеиногорский', xy=(cx, cy), xytext=(81.95, 52.55), fontsize=8, ha='center', va='center',
                 arrowprops=dict(arrowstyle='-', lw=0.6, color='dimgray', shrinkA=0, shrinkB=0), zorder=7)
    # Красногорский (восток-середина): подпись в свободный центр-низ
    cx, cy = cents['Красногорский']
    ax1.annotate('Красногорский', xy=(cx, cy), xytext=(84.35, 52.00), fontsize=8, ha='center', va='center',
                 arrowprops=dict(arrowstyle='-', lw=0.6, color='dimgray', shrinkA=0, shrinkB=0), zorder=7)
    # Солтонский (восток-верх, маленький): подпись в свободный центр-верх
    cx, cy = cents['Солтонский']
    ax1.annotate('Солтонский', xy=(cx, cy), xytext=(84.05, 52.80), fontsize=8, ha='center', va='center',
                 arrowprops=dict(arrowstyle='-', lw=0.6, color='dimgray', shrinkA=0, shrinkB=0), zorder=7)

    # --- масштабная линейка ~10 км в свободную зону (запад-верх, рядом со справкой) ---
    rlon, rlat = 81.78, 52.95
    km_per_deg = 111.32; deg10 = 10 / (km_per_deg * math.cos(math.radians(rlat)))
    ax1.plot([rlon, rlon + deg10], [rlat, rlat], 'k-', lw=2.5, zorder=8)
    ax1.plot([rlon, rlon], [rlat-0.03, rlat+0.03], 'k-', lw=1, zorder=8)
    ax1.plot([rlon+deg10, rlon+deg10], [rlat-0.03, rlat+0.03], 'k-', lw=1, zorder=8)
    ax1.text(rlon + deg10/2, rlat + 0.06, '10 км', fontsize=7, ha='center', zorder=8)

    # --- справка «всего / с координатами» в свободную зону (запад-верх) ---
    infotxt = 'всего / с координатами:\n' + '\n'.join(f'{d}: {v[0]}/{v[1]}' for d, v in info.items())
    ax1.text(0.015, 0.985, infotxt, transform=ax1.transAxes, fontsize=7, ha='left', va='top',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.9), zorder=9)

    # --- увеличенный фрагмент ---
    for n, ring in polys.items():
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        ax2.plot(xs, ys, 'k-', lw=1.0)
    for g in ok:
        ax2.scatter(float(g['lon']), float(g['lat']), c='#2ca02c', edgecolor='black', linewidth=0.5, s=42, alpha=0.9, zorder=5)
    ax2.set_xlim(zm[2], zm[3]); ax2.set_ylim(zm[0], zm[1])
    ax2.text(0.02, 0.98, f'г. Змеиногорск\n{len(ok)} записей', transform=ax2.transAxes, fontsize=8, va='top',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.9), zorder=6)

    # --- связующие линии от правых углов рамки (ax1) к левым углам панели фрагмента (ax2) ---
    cp_top = ConnectionPatch(xyA=(zm[3], zm[1]), coordsA=ax1.transData,
                             xyB=(zm[2], zm[1]), coordsB=ax2.transData,
                             color='red', lw=0.8, linestyle='--', zorder=6)
    cp_bot = ConnectionPatch(xyA=(zm[3], zm[0]), coordsA=ax1.transData,
                             xyB=(zm[2], zm[0]), coordsB=ax2.transData,
                             color='red', lw=0.8, linestyle='--', zorder=6)
    fig.add_artist(cp_top); fig.add_artist(cp_bot)

    # --- легенда вынесена за контуры районов (вниз фигуры, под осями) ---
    h_pts = ax1.scatter([], [], c='#2ca02c', edgecolor='black', linewidth=0.4, s=30,
                        label='записи с координатами\nвнутри своего пилотного района')
    from matplotlib.lines import Line2D
    h_frm = Line2D([], [], color='red', lw=1.0, linestyle='-', label='рамка увеличенного\nфрагмента')
    h_lnk = Line2D([], [], color='red', lw=0.8, linestyle='--', label='связующие линии\nфрагмент → панель')
    fig.legend(handles=[h_pts, h_frm, h_lnk], loc='lower center', bbox_to_anchor=(0.5, 0.045),
               ncol=3, fontsize=7, frameon=False)

    # --- подпись внизу ---
    fig.text(0.5, 0.012, 'WGS 84 (принята; в записи реестра не указана). © участники OpenStreetMap, ODbL 1.0.',
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
      цвета: голубой — шапка, зелёный — есть, серый — нет, жёлтый — вероятное.

    Числа вычисляются из данных (не вводятся вручную), заход 14:
      - 11 / 8 — число приказов по волнам в data/manual/perechen_check.csv;
      - «в перечне» — in_perechen из perechen_check.csv (сопоставление 19 приказов с 8 объектами
        gukn_vokn.csv по номеру приказа); ранним 11 — «нет» (0 из 11), поздним 8 — «да» (8 из 8);
        согласовано с таблицей 5 статьи (8 из 8);
      - «в реестре» — reestr_status из perechen_check.csv: ранние — 10 подтверждённых + 1 вероятное
        (приказ № 183, «ВЕРОЯТНО ТОТ ЖЕ ОБЪЕКТ») = 11 (согласовано с таблицей 5: 11 из 11);
        поздние — 0 из 8 (новые выявленные, в ЕГРОКН отсутствуют);
      - «в списке» — s09_orders_trace.py (auto_csv): все 19 «НЕ НАЙДЕН» (0 из 11, 0 из 8).

    Режим revised (заход 15): в ячейке реестра ранней группы — «10 подтверждённых, 1 вероятное*»
    без сокращений; сноска и примечание тёмным цветом; для «нет» — нейтральный серый фон, цвет
    только для «есть» (зелёный) и «вероятное» (жёлтый); строка с расшифровкой цветов; нейтральные
    соединители; подпись — показано наличие записей в массивах, а не обязательная последовательность.
    Режим as_published — авторская схема (стрелки, 11 из 11).
    """
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.font_manager as fm
    for fp in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf'):
        try: fm.fontManager.addfont(fp)
        except Exception: pass
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
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
    # цвета: шапка — голубой; «есть» — зелёный; «нет» — нейтральный серый; «вероятное» — жёлтый
    C_HDR, C_WAVE, C_OK, C_NO, C_PROB = '#cfe8ff', '#f0f0f0', '#c8f0c8', '#d9d9d9', '#fff3c0'
    DARK = '#333333'
    fig, ax = plt.subplots(figsize=(11, 6.6), constrained_layout=True); ax.axis('off')
    ax.set_xlim(0, 4); ax.set_ylim(-1.1, 3)
    xs = [0.05, 1.05, 2.05, 3.05]; bw, bh = 0.9, 0.62
    ys = {'hdr': 2.3, '2019–2024': 1.25, '2025–2026': 0.25}

    def cell(x, y, text, color, fs=8.5, weight='normal'):
        ax.add_patch(Rectangle((x, y - bh/2), bw, bh, facecolor=color, edgecolor='black', lw=0.8))
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
            cell(xs[2], y, f'{conf} подтверждённых,\n{prob} вероятное*', C_PROB, fs=9)
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
        # сноска и примечание — тёмным цветом
        ax.text(2, -0.25, '* приказ № 183 — совпадение вероятное («ВЕРОЯТНО ТОТ ЖЕ ОБЪЕКТ»)',
                ha='center', fontsize=8, style='italic', color=DARK)
        ax.text(2, -0.5, 'Показано наличие записей в массивах, а не обязательная последовательность действий.',
                ha='center', fontsize=8, color=DARK)
        # строка с расшифровкой цветов
        legend_y = -0.9
        items = [(C_OK, 'есть (совпадение)'), (C_NO, 'нет'), (C_PROB, 'вероятное'), (C_HDR, 'шапка / заголовок')]
        xcur = 0.15
        for color, label in items:
            ax.add_patch(Rectangle((xcur, legend_y - 0.10), 0.18, 0.20, facecolor=color, edgecolor='black', lw=0.6))
            ax.text(xcur + 0.24, legend_y, label, ha='left', va='center', fontsize=8, color=DARK)
            xcur += 0.24 + 0.075 * len(label) + 0.45
    fig.savefig(out_path, dpi=300); plt.close(fig)
    print(f's10 fig2 ({mode}) -> {out_path}')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--geo', required=True)
    ap.add_argument('--boundaries-dir', required=True)
    ap.add_argument('--results', required=False, default=None, help='results_long_fixed.csv (не используется; оставлено для совместимости)')
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
