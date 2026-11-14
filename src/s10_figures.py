# -*- coding: utf-8 -*-
"""s10_figures.py — рисунки статьи.

Рис. 1. Геопривязка записей реестра в пилотных районах (Змеиногорский, Красногорский, Солтонский).
Рис. 2. Наличие объектов из приказов о включении в перечень выявленных в четырёх массивах.
Все числа на рисунках вычисляются из файлов данных.

Запуск из корня репозитория:
  python src/s10_figures.py --geo data/derived/geo_diagnostics.csv --boundaries-dir data/boundaries \
      --perechen data/manual/perechen_check.csv --auto data/derived/blind_zone_report.csv --out-dir figures

Результат: figures/Ris1_geopolygon.png и figures/Ris2_flow.png (300 dpi, шрифт DejaVu Sans).
Границы районов: © участники OpenStreetMap, лицензия ODbL 1.0.
"""
import argparse, csv, json, math, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon, FancyBboxPatch, Rectangle, ConnectionPatch
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, FixedLocator

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['figure.autolayout'] = False
BG, PANEL, INK, GRID, MUTED = '#F4F4EE', '#FAFAF6', '#1D333B', '#E2E2DA', '#6B7B80'
RED = '#C0392B'
DISTRICTS = {  # файл границы -> район, цвета заливки и контура
    'Змеиногорский': dict(file='boundary_1.json', fc='#C9D3DE', ec='#7D8A99'),
    'Красногорский': dict(file='boundary_2.json', fc='#CFE3CD', ec='#7F9A7B'),
    'Солтонский': dict(file='boundary_3.json', fc='#F5DCC3', ec='#B08A66'),
}


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter=';'))


def comma(fmt):
    return FuncFormatter(lambda v, _: fmt.format(v).replace('.', ','))


def plural(n, one, few, many):
    n10, n100 = n % 10, n % 100
    if n10 == 1 and n100 != 11:
        return one
    if 2 <= n10 <= 4 and not 12 <= n100 <= 14:
        return few
    return many


def load_rings(path):
    """Внешние контуры района из GeoJSON (Feature, FeatureCollection, Polygon, MultiPolygon)."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    def find(o):
        if isinstance(o, dict):
            if o.get('type') in ('Polygon', 'MultiPolygon') and 'coordinates' in o:
                return o
            for k in ('geometry', 'geojson', 'features'):
                if k in o:
                    g = find(o[k])
                    if g:
                        return g
            for v in o.values():
                if isinstance(v, (dict, list)):
                    g = find(v)
                    if g:
                        return g
        elif isinstance(o, list):
            for x in o:
                g = find(x)
                if g:
                    return g
        return None

    g = find(data)
    if g is None:
        raise ValueError('в %s не найдена геометрия Polygon/MultiPolygon' % path)
    polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
    return [[(float(p[0]), float(p[1])) for p in poly[0]] for poly in polys]


def bbox_overlap(a, b):
    return not (a.x1 <= b.x0 or b.x1 <= a.x0 or a.y1 <= b.y0 or b.y1 <= a.y0)


def fig1(geo_csv, bdir, out_png):
    rows = read_csv(geo_csv)
    stats = {d: [0, 0] for d in DISTRICTS}          # всего записей, с координатами
    pts = []
    for r in rows:
        d = r['district']
        if d not in stats:
            continue
        stats[d][0] += 1
        if r['lat'].strip():
            stats[d][1] += 1
            if r['class'] == 'ок':
                pts.append((float(r['lon']), float(r['lat'])))
    rings = {d: load_rings(os.path.join(bdir, v['file'])) for d, v in DISTRICTS.items()}
    allp = [p for rs in rings.values() for r in rs for p in r]
    b = {d: (min(p[0] for r in rs for p in r), max(p[0] for r in rs for p in r),
             min(p[1] for r in rs for p in r), max(p[1] for r in rs for p in r)) for d, rs in rings.items()}
    lon0, lon1 = min(p[0] for p in allp) - 0.15, max(p[0] for p in allp) + 0.15
    lat0, lat1 = min(p[1] for p in allp) - 0.12, max(p[1] for p in allp) + 0.12
    latc = (lat0 + lat1) / 2
    k = math.cos(math.radians(latc))
    # размеры в дюймах: равный масштаб по осям с поправкой на широту
    Wf, left, right, bottom, top = 10.4, 0.95, 0.25, 1.45, 0.2
    aw = Wf - left - right
    ah = aw * (lat1 - lat0) / ((lon1 - lon0) * k)
    Hf = bottom + ah + top
    fig = plt.figure(figsize=(Wf, Hf), dpi=300, facecolor=BG)
    ax = fig.add_axes([left / Wf, bottom / Hf, aw / Wf, ah / Hf], facecolor=PANEL)
    ax.set_xlim(lon0, lon1)
    ax.set_ylim(lat0, lat1)
    ax.set_aspect(1 / k, adjustable='box')
    ax.grid(True, color=GRID, lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_color('#9AA5A8')
    for d, v in DISTRICTS.items():
        for r in rings[d]:
            ax.add_patch(MplPolygon(r, closed=True, fc=v['fc'], ec=v['ec'], lw=0.9, zorder=2))
    ax.xaxis.set_major_locator(FixedLocator(list(range(int(math.ceil(lon0)), int(lon1) + 1))))
    ax.xaxis.set_major_formatter(comma('{:.0f}'))
    ax.yaxis.set_major_locator(FixedLocator([round(x * 0.5, 1) for x in range(int(lat0 * 2) + 1, int(lat1 * 2) + 1)]))
    ax.yaxis.set_major_formatter(comma('{:.1f}'))
    ax.tick_params(colors=INK, labelsize=10)
    ax.set_xlabel('Долгота, ° в. д.', color=INK, fontsize=11)
    ax.set_ylabel('Широта, ° с. ш.', color=INK, fontsize=11)

    # подписи районов (счётчики вычисляются из данных)
    texts = []
    def label(d, x, y, ha, va):
        t = ax.text(x, y, '%s район\nзаписей %d, с координатами %d' % (d, stats[d][0], stats[d][1]),
                    ha=ha, va=va, fontsize=9, color=INK, zorder=6,
                    bbox=dict(boxstyle='round,pad=0.25', fc=BG, ec='none', alpha=0.9))
        texts.append(t)
    zl, zr, zb, zt = b['Змеиногорский']
    kl, kr, kb, kt = b['Красногорский']
    sl, sr, sb, st = b['Солтонский']
    label('Змеиногорский', zl, zt + 0.10, 'left', 'bottom')
    label('Красногорский', kl - 0.10, kt - 0.22, 'right', 'center')
    label('Солтонский', sl - 0.10, st - 0.12, 'right', 'center')

    # точки записей на обзорной карте
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=14, c=RED, edgecolors='white', linewidths=0.5, zorder=5)
    ax.plot([cx], [cy], marker='o', ms=15, mfc='none', mec=INK, mew=1.2, zorder=6)

    # увеличенный фрагмент (врезка) в свободной части карты
    Lg, Hg = 0.016, 0.010                                   # размер врезки в градусах
    kz = math.cos(math.radians(cy))
    win = 2.5
    hin = win * Hg / (Lg * kz)
    in_lon = zr + 0.55
    in_lat = lat0 + 0.0 + (51.0 - lat0)
    x_in = left + (in_lon - lon0) / (lon1 - lon0) * aw
    y_in = bottom + (in_lat - lat0) / (lat1 - lat0) * ah
    axi = fig.add_axes([x_in / Wf, y_in / Hf, win / Wf, hin / Hf], facecolor='white')
    axi.set_xlim(cx - Lg / 2, cx + Lg / 2)
    axi.set_ylim(cy - Hg / 2, cy + Hg / 2)
    axi.set_aspect('auto')
    axi.scatter([p[0] for p in pts], [p[1] for p in pts], s=48, c=RED, edgecolors='white', linewidths=0.8, zorder=3)
    xt = [round(cx - 0.0075 + 0.005 * i, 3) for i in range(4)]
    yt = [round(cy - 0.004 + 0.004 * i, 3) for i in range(3)]
    axi.xaxis.set_major_locator(FixedLocator(xt)); axi.yaxis.set_major_locator(FixedLocator(yt))
    axi.xaxis.set_major_formatter(comma('{:.3f}°')); axi.yaxis.set_major_formatter(comma('{:.3f}°'))
    axi.yaxis.tick_right()
    axi.tick_params(colors=INK, labelsize=8)
    axi.grid(True, color=GRID, lw=0.6)
    for s in axi.spines.values():
        s.set_color(INK); s.set_linewidth(1.1)
    ti = axi.set_title('Увеличенный фрагмент:\nг. Змеиногорск, %d записей' % len(pts), fontsize=9, color=INK, pad=4)
    texts.append(ti)
    for corner in ((0, 1), (0, 0)):
        con = ConnectionPatch(xyA=(cx, cy), coordsA='data', axesA=ax, xyB=corner, coordsB='axes fraction', axesB=axi,
                              color=INK, lw=0.9, ls=(0, (4, 3)), alpha=0.85, zorder=4)
        con.set_clip_on(False)
        axi.add_artist(con)

    # масштабная линейка 10 км (на широте линейки)
    yb = lat0 + 0.16
    dlon = 10.0 / (111.32 * math.cos(math.radians(yb)))
    xb1 = lon1 - 0.35
    xb0 = xb1 - dlon
    ax.plot([xb0, xb1], [yb, yb], color=INK, lw=2.2, solid_capstyle='butt', zorder=6)
    for x in (xb0, xb1):
        ax.plot([x, x], [yb - 0.03, yb + 0.03], color=INK, lw=1.2, zorder=6)
    tb = ax.text((xb0 + xb1) / 2, yb + 0.06, '10 км', ha='center', va='bottom', fontsize=9, color=INK, zorder=6)
    texts.append(tb)

    # легенда и примечание под картой
    handles = [Line2D([], [], marker='o', ls='none', mfc=RED, mec='white', ms=8, label='запись с координатами внутри своего района'),
               Line2D([], [], marker='o', ls='none', mfc='none', mec=INK, mew=1.2, ms=11, label='положение увеличенного фрагмента')]
    lg = fig.legend(handles=handles, loc='lower center', ncol=2, frameon=False, fontsize=9.5,
                    bbox_to_anchor=(0.5, 0.32 / Hf), labelcolor=INK)
    fig.text(0.5, 0.12 / Hf, 'Система координат WGS 84 (принята; в записи реестра не указана). '
             'Границы районов © участники OpenStreetMap, лицензия ODbL 1.0.',
             ha='center', va='bottom', fontsize=8.5, color=MUTED)

    # автоматическая проверка наложений
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    issues = []
    boxes = [(t.get_text().split('\n')[0], t.get_window_extent(rend)) for t in texts]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if bbox_overlap(boxes[i][1], boxes[j][1]):
                issues.append('наложение подписей: %s / %s' % (boxes[i][0], boxes[j][0]))
    axi_bb = axi.get_window_extent(rend)
    for name, bb in boxes[:3]:
        if bbox_overlap(bb, axi_bb):
            issues.append('подпись «%s» перекрывает врезку' % name)
    for name, bb in boxes[:3]:
        for d, rs in rings.items():
            hit = False
            for r in rs:
                for (x, y) in r[::3]:
                    px, py = ax.transData.transform((x, y))
                    if bb.x0 <= px <= bb.x1 and bb.y0 <= py <= bb.y1:
                        hit = True; break
                if hit: break
            if hit and not name.startswith(d):
                issues.append('подпись «%s» налезает на контур района %s' % (name, d))
            if hit and name.startswith(d):
                issues.append('подпись «%s» налезает на собственный контур' % name)
    tl = [t.get_window_extent(rend) for t in axi.get_xticklabels() if t.get_text()]
    for i in range(len(tl) - 1):
        if bbox_overlap(tl[i], tl[i + 1]):
            issues.append('наложение подписей делений на врезке')
    for bb in tl:
        for d, rs in rings.items():
            for r in rs:
                for (x, y) in r[::3]:
                    px, py = ax.transData.transform((x, y))
                    if bb.x0 <= px <= bb.x1 and bb.y0 <= py <= bb.y1:
                        issues.append('подписи делений врезки на контуре %s' % d); break
    fig.savefig(out_png, dpi=300, facecolor=BG)
    plt.close(fig)
    return issues, stats, len(pts)


def fig2(perechen_csv, auto_csv, out_png):
    P = read_csv(perechen_csv)
    A = {(r['prikaz_date'], r['prikaz_number']): r for r in read_csv(auto_csv)}
    years = lambda r: int(r['prikaz_date'].split('.')[-1])
    waves = {'ранняя': [r for r in P if years(r) <= 2024], 'поздняя': [r for r in P if years(r) >= 2025]}
    info = []
    prob_nums = []
    for name, rs in waves.items():
        n = len(rs)
        ys = [years(r) for r in rs]
        lbl = '%d–%d гг.' % (min(ys), max(ys))
        k_per = sum(1 for r in rs if r['in_perechen'].strip() == 'да')
        ok = sum(1 for r in rs if r['reestr_status'] == 'подтверждённое')
        prob = [r for r in rs if r['reestr_status'] == 'вероятное']
        prob_nums += [r['prikaz_number'] for r in prob]
        k_list = sum(1 for r in rs if A[(r['prikaz_date'], r['prikaz_number'])]['in_list'].startswith('НАЙДЕН'))
        info.append(dict(label=lbl, n=n, per=k_per, ok=ok, prob=len(prob), lst=k_list))
    GREEN, GRAY, YELLOW, HEAD, LAB = '#D3EBD6', '#E4E4DF', '#FFF1B8', '#DCE6F1', '#EFEFEA'
    W, H = 11.2, 5.75
    fig = plt.figure(figsize=(W, H), dpi=300, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
    cw, gap = 2.45, 0.30
    x0 = (W - (4 * cw + 3 * gap)) / 2
    xs = [x0 + i * (cw + gap) for i in range(4)]

    inside = []

    def box(x, y, w, h, fc, text=None, fs=12, bold=False, color=INK):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.08', fc=fc, ec=INK, lw=1.0))
        if text:
            t = ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs, color=color,
                        fontweight='bold' if bold else 'normal', linespacing=1.3)
            inside.append((t, (x, y, w, h)))

    heads = ['Приказ о включении\nв перечень выявленных', 'Действующий перечень\nвыявленных (04.2026)',
             'Реестр\n(ЕГРОКН)', 'Краевой\nсписок']
    for x, t in zip(xs, heads):
        box(x, 4.55, cw, 0.95, HEAD, t, fs=10.5, bold=True)
    rows_y = [2.95, 1.45]
    for y, d in zip(rows_y, info):
        h = 1.1
        n = d['n']
        box(xs[0], y, cw, h, LAB, '%s\n%d %s' % (d['label'], n, plural(n, 'приказ', 'приказа', 'приказов')), fs=11)
        box(xs[1], y, cw, h, GREEN if d['per'] else GRAY, '%d из %d' % (d['per'], n), fs=14)
        if d['prob']:
            hh = h * 0.30
            box(xs[2], y + hh, cw, h - hh, GREEN, '%d подтверждённых' % d['ok'], fs=12)
            box(xs[2], y, cw, hh, YELLOW, '+ %d вероятное*' % d['prob'], fs=10.5)
        else:
            box(xs[2], y, cw, h, GREEN if d['ok'] else GRAY, '%d из %d' % (d['ok'], n), fs=14)
        box(xs[3], y, cw, h, GREEN if d['lst'] else GRAY, '%d из %d' % (d['lst'], n), fs=14)
        for i in range(3):
            ax.plot([xs[i] + cw + 0.04, xs[i + 1] - 0.04], [y + h / 2] * 2, color=MUTED, lw=1.0)
    # примечание и легенда
    note = '* Приказ № %s: совпадение с записью реестра вероятное.' % ', '.join(prob_nums) if prob_nums else ''
    ax.text(W / 2, 1.05, note, ha='center', va='center', fontsize=10, color=INK, style='italic')
    ax.text(W / 2, 0.72, 'Показано число объектов из приказов, найденных в каждом массиве; '
            'последовательность прохождения не подразумевается.', ha='center', va='center', fontsize=10, color=INK)
    items = [(GREEN, 'есть'), (GRAY, 'нет'), (YELLOW, 'вероятное совпадение')]
    widths = [1.0, 0.9, 2.3]
    lx = (W - (sum(widths) + 0.3 * 3)) / 2
    for (c, t), w in zip(items, widths):
        ax.add_patch(Rectangle((lx, 0.18), 0.28, 0.2, fc=c, ec=INK, lw=0.9))
        ax.text(lx + 0.38, 0.28, t, ha='left', va='center', fontsize=10, color=INK)
        lx += w + 0.3 + 0.35
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    issues = []
    for t, (x, y, w, h) in inside:
        (tx0, ty0), (tx1, ty1) = inv.transform(t.get_window_extent(rend).get_points())
        if tx0 < x + 0.08 or tx1 > x + w - 0.08 or ty0 < y + 0.02 or ty1 > y + h - 0.02:
            issues.append('подпись «%s» не помещается в рамку' % t.get_text().replace('\n', ' / '))
    fig.savefig(out_png, dpi=300, facecolor=BG)
    plt.close(fig)
    return info, issues


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--geo', required=True, help='data/derived/geo_diagnostics.csv')
    ap.add_argument('--boundaries-dir', required=True, help='data/boundaries')
    ap.add_argument('--perechen', required=True, help='data/manual/perechen_check.csv')
    ap.add_argument('--auto', required=True, help='data/derived/blind_zone_report.csv')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--mode', default='final', help=argparse.SUPPRESS)  # совместимость с прежним интерфейсом
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    issues, stats, npts = fig1(a.geo, a.boundaries_dir, os.path.join(a.out_dir, 'Ris1_geopolygon.png'))
    print('Рис. 1: записей/с координатами по районам: %s; точек во врезке: %d' % (stats, npts))
    print('Рис. 1: проверка наложений: %s' % ('замечаний нет' if not issues else '; '.join(issues)))
    info, issues2 = fig2(a.perechen, a.auto, os.path.join(a.out_dir, 'Ris2_flow.png'))
    print('Рис. 2: %s' % info)
    print('Рис. 2: проверка вложенности подписей: %s' % ('замечаний нет' if not issues2 else '; '.join(issues2)))
    return 1 if (issues or issues2) else 0


if __name__ == '__main__':
    sys.exit(main())
