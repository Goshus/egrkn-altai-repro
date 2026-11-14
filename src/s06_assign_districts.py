# -*- coding: utf-8 -*-
"""s06_assign_districts.py — шаг 6 статьи: назначение районов по перечню ОКТМО + обогащение полей.

Пути задаются через argparse; общие функции — в common/.
Логика детектора районов v3, правил датировки, geo-QC НЕ изменены.

Шаг статьи → скрипт → выход → таблица:
  «район не установлен 2385 (2131 назначено)» → s06 → egrkn_altai_final.csv (32 колонки) → таблицы 1, 2, 3, 4.
  Контроль: 4518 записей; sha256 регномеров 86afa4ab…; sha256 районов 8734de19… (см. common/hashes.py).
"""
import csv, glob, hashlib, json, os, re, sys, zipfile

EXPECTED_N = 4518
EXPECTED_SHA_REG = '86afa4ab35e33724e918b387718ecea5590a9d98f39159f05cbe61a1f00bad89'
EXPECTED_SHA_DIST = '8734de19653642edd80310aa0dc5cd1db862fb9169ca538285c91165eb9196ac'  # детектор районов v3
LOG = []
def log(msg):
    print(msg); LOG.append(str(msg))

def find_records(obj):
    if isinstance(obj, list): return obj
    if isinstance(obj, dict):
        for k in ('data', 'items', 'records', 'features'):
            if isinstance(obj.get(k), list): return obj[k]
        for v in obj.values():
            if isinstance(v, list) and v and isinstance(v[0], dict): return v
    return []

def get_general(r):
    g = r.get('general') or {}
    if not g: g = (r.get('data') or {}).get('general') or {}
    return g if isinstance(g, dict) else {}

def first_ll(geom):
    if not isinstance(geom, dict): return None
    pts = []
    def coll(x):
        if isinstance(x, (list, tuple)) and len(x) >= 2 and all(isinstance(v, (int, float)) for v in x[:2]):
            pts.append((float(x[0]), float(x[1])))
        elif isinstance(x, (list, tuple)):
            for y in x: coll(y)
    coll(geom.get('coordinates'))
    if not pts: return None
    return (round(sum(p[1] for p in pts) / len(pts), 6), round(sum(p[0] for p in pts) / len(pts), 6))

def coords_of(g):
    addr = g.get('address') or {}; coords = g.get('coords') or {}
    ll = first_ll(addr.get('mapPosition'))
    if ll: return ll[0], ll[1], 'mapPosition'
    if coords.get('selfCoord'):
        nums = re.findall(r'-?\d+[.,]?\d*', str(coords['selfCoord'][0].get('point', '')))
        if len(nums) >= 2:
            a, b = float(nums[0].replace(',', '.')), float(nums[1].replace(',', '.'))
            return (a, b, 'selfCoord') if 49 <= a <= 56 and 78 <= b <= 91 else (b, a, 'selfCoord_swapped')
    ll = first_ll(coords.get('yandexCoord'))
    if ll: return ll[0], ll[1], 'yandex_auto'
    return '', '', ''

def extract_settlement(addr):
    if not addr: return ''
    m = re.search(r'((?:с|п|г|пос|дер|пгт|ст|рзд)\.?\s+[А-ЯЁ][^,;]+)', str(addr))
    if m and 'край' not in m.group(1).lower() and 'район' not in m.group(1).lower():
        return m.group(1).strip()
    return ''

# ---------- прежнее правило датировки (для преемственности чисел) ----------
LEGACY_RE = re.compile(r'(эпоха[^,.;)]{0,50}|верхнего палеолита|неолита?[^,.;)]{0,30}|бронз[^,.;)]{0,30}|средневеков[^,.;)]{0,25}|(?:XVIII|XIX|XX|XVII|XVI|[IVX]{1,4})\s*вв?\.[^,.;)]{0,30}|(?:1[5-9]\d{2}|20\d{2})\s*(?:[-–—]\s*(?:1[5-9]\d{2}|20\d{2}))?\s*гг?)', re.I)
def legacy_dating(*texts):
    for t in texts:
        if not t: continue
        m = LEGACY_RE.search(str(t))
        if m: return m.group(0).strip()
    return ''

# ---------- новое правило: дата объекта и период события ----------
Q = r'(?:(?:[Нн]ач|[Кк]он|[Сс]ер)\.?\s*|[12]\s*-?\s*я\s+пол(?:\.|овина)?\s*)?'
ROM = r'[IVX]{1,5}'
BCE = r'(?:\s*до\s*н\.?\s*э\.?|\s*н\.?\s*э\.?)?'
CENT_RE = re.compile(Q + ROM + r'(?:\s*[-–—]\s*' + ROM + r')?\s*вв?\.' + BCE)
MILL_RE = re.compile(Q + ROM + r'(?:\s*[-–—]\s*' + ROM + r')?\s*тыс\.' + BCE)
YEAR_RE = re.compile(r'(?<!\d)(?:1[5-9]\d{2}|20[0-2]\d)(?:\s*[-–—]\s*(?:1[5-9]\d{2}|20[0-2]\d))?\s*гг?\.?')
DEC_RE = re.compile(r'(?<!\d)1[5-9]\d0\s*-?\s*х\s*гг?\.?')
EPOCH_RE = re.compile(r'эпох[аиуе]\s+(?:(?:верхнего|нижнего|среднего|раннего|позднего|финального)\s+)?[а-яё]+|(?:верхн|нижн|средн)\w+\s+палеолит\w*|(?:нео|энео)лит\w*', re.I)
WAR_RE = re.compile(r'1941\s*[-–—]\s*1945')

def extract_dates(text):
    spans = []
    for rx in (CENT_RE, MILL_RE, YEAR_RE, DEC_RE, EPOCH_RE):
        for m in rx.finditer(text or ''):
            spans.append((m.start(), m.end(), m.group(0).strip()))
    spans.sort(key=lambda s: (s[0], -s[1]))
    out, last_end = [], -1
    for s, e, t in spans:
        if s >= last_end:
            out.append(t); last_end = e
    return out

def dating_new(name, sec):
    d_name, d_sec = extract_dates(name), extract_dates(sec)
    event = any(WAR_RE.search(t) for t in d_name + d_sec)
    obj, src = [], ''
    for s, ds in (('name', d_name), ('security_info', d_sec)):
        cand = [t for t in ds if not WAR_RE.search(t)]
        if cand: obj, src = cand, s; break
    return '; '.join(dict.fromkeys(obj[:4])), ('1941–1945' if event else ''), src

# ---------- ОКТМО и районы ----------
def load_oktmo(path):
    xml = zipfile.ZipFile(path).read('word/document.xml').decode('utf-8')
    xml = xml.replace('</w:p>', '\n').replace('</w:tc>', ' | ').replace('</w:tr>', '\n')
    txt = re.sub(r'<[^>]+>', '', xml)
    terr = []
    for line in txt.splitlines():
        m = re.search(r'-\s*(.+?)\s*(?:\||$)', line)
        if not m: continue
        name = m.group(1).strip()
        if not name: continue
        if name.startswith('Муниципальный округ'):
            core = name.replace('Муниципальный округ', '').strip()
            terr.append(('округ', core[:-6] if core.endswith(' район') else core))
        elif name.endswith('муниципальный район'):
            terr.append(('район', name[:-19].strip()))
        elif name.startswith('город '):
            terr.append(('город', name.replace('город ', '').strip()))
        elif name.endswith('район') and 'муниципальный' not in name:
            terr.append(('район', name[:-6].strip()))
    return terr

def stem(b):
    b = b.lower()
    for suf in ('ский', 'ской', 'цкий', 'ний', 'ной', 'ный', 'ий', 'ый', 'ой', 'ое', 'ья'):
        if b.endswith(suf): return b[:-len(suf)]
    return b

def make_detect(terr):
    bases = {'район': {}, 'округ': {}, 'город': {}}
    for kind, base in terr:
        if kind == 'округ' and base.lower().startswith('город '):
            kind, base = 'город', base[6:].strip()
        bases[kind][stem(base)] = f'{base} ({kind})' if kind != 'город' else f'г. {base}'
    def detect(address):
        segs = [s.strip().lower() for s in str(address or '').split(',')]
        for seg in segs:
            m = re.search(r'([а-яё]+(?:-[а-яё]+)*)\s+(?:муниципальный\s+)?(?:район|округ)\b', seg)
            if m:
                w = stem(m.group(1))
                for kind in ('район', 'округ'):
                    if w in bases[kind]: return bases[kind][w]
        for seg in segs:
            m = re.search(r'(?:^|[\s.])(?:г\.|город)\s*([а-яё]+(?:-[а-яё]+)*)', seg)
            if m and stem(m.group(1)) in bases['город']:
                return bases['город'][stem(m.group(1))]
        return ''
    return detect, sum(len(v) for v in bases.values())

def settlement_type(st):
    st = (st or '').lower().strip()
    if re.match(r'^(с\.|п\.|д\.|пгт|ст\.|рзд|село|деревня)', st): return 'сельское'
    if re.match(r'^(г\.|город)', st): return 'городское'
    return 'не определено'

def find_oktmo_docx():
    for f in sorted(glob.glob('*.docx')):
        try:
            xml = zipfile.ZipFile(f).read('word/document.xml').decode('utf-8')
        except Exception:
            continue
        if 'ОКТМО' in xml and 'Муниципальные образования Алтайского края' in re.sub(r'<[^>]+>', '', xml):
            return f
    return None

HDR_BASE = ['record_id', 'registry_number', 'con_number', 'name', 'region_value', 'category', 'obj_type', 'typologies',
            'address_full', 'address_comment', 'settlement', 'border_info', 'security_info', 'dating_extracted_v1',
            'documents', 'lat', 'lon', 'coord_source', 'is_actual', 'protection_year', 'parent_id', 'source_file', 'source_row']
HDR_NEW = ['security_len', 'in_altai_region', 'address_region_anomaly', 'coord_outside_krai', 'settlement_type',
           'district_oktmo', 'dating_object', 'dating_event', 'dating_source']

def enrich(r, detect):
    addr = r['address_full']; seg0 = addr.split(',')[0].strip().lower() if addr else ''
    r['in_altai_region'] = 'true' if 'алтайский' in r['region_value'].lower() else 'false'
    r['address_region_anomaly'] = 'true' if (r['in_altai_region'] == 'true' and 'край' in seg0 and seg0 != 'алтайский край') else 'false'
    out = False
    if r['lat'] not in ('', None):
        try:
            la, lo = float(r['lat']), float(r['lon'])
            out = not (49.0 <= la <= 54.5 and 76.0 <= lo <= 88.5)
        except ValueError:
            out = True
    r['coord_outside_krai'] = 'true' if out else 'false'
    r['settlement_type'] = settlement_type(r['settlement'])
    r['district_oktmo'] = detect(addr)
    sec_full = r.get('_sec_full', r['security_info'])
    r['dating_object'], r['dating_event'], r['dating_source'] = dating_new(r['name'], sec_full)
    r['security_len'] = len(sec_full or '')
    return r

def read_dump(files):
    rows = []
    for fp in files:
        try:
            data = json.load(open(fp, encoding='utf-8'))
        except Exception as e:
            log(f'{os.path.basename(fp)}: ОШИБКА {type(e).__name__}: {e}'); continue
        n = 0
        for i, rec in enumerate(find_records(data)):
            if not isinstance(rec, dict): continue
            g = get_general(rec)
            reg = str((g.get('region') or {}).get('value', ''))
            rn = str(g.get('regNumber', '') or '')
            if not ('алтайский' in reg.lower() or rn.startswith('22')): continue
            addr = g.get('address') or {}
            docs = g.get('documents') or []
            doc_s = ' | '.join(f"{d.get('name', '')} №{d.get('number', '')} от {d.get('date', '')}" for d in docs if isinstance(d, dict))
            lat, lon, csrc = coords_of(g)
            sec = str(g.get('securityInfo', '') or '')
            name = str(g.get('name', '') or '')
            rows.append({
                'record_id': f'E{len(rows) + 1:05d}', 'registry_number': rn, 'con_number': str(g.get('conNumber', '') or ''),
                'name': name, 'region_value': reg, 'category': str((g.get('categoryType') or {}).get('value', '') or ''),
                'obj_type': str((g.get('objectType') or {}).get('value', '') or ''),
                'typologies': '; '.join(str(t.get('value', '')) for t in (g.get('typologies') or []) if isinstance(t, dict)),
                'address_full': str(addr.get('fullAddress', '') or ''), 'settlement': extract_settlement(addr.get('fullAddress', '')),
                'border_info': str(g.get('borderInfo', '') or '')[:300], 'security_info': sec[:300],
                'dating_extracted_v1': legacy_dating(sec, name), 'documents': doc_s[:300],
                'lat': lat, 'lon': lon, 'coord_source': csrc, 'is_actual': str(g.get('isActual', '')).lower(),
                'protection_year': str(g.get('protectionYear', '') or ''), 'parent_id': str(g.get('parentId', '') or ''),
                'address_comment': str(addr.get('comment', '') or ''),
                'source_file': os.path.basename(fp), 'source_row': i, '_sec_full': sec})
            n += 1
        log(f'{os.path.basename(fp)}: край += {n}')
    return rows

def main():
    from_csv = sys.argv[1] if len(sys.argv) > 1 else None
    docx = find_oktmo_docx()
    if not docx:
        log('СТОП: не найден docx с перечнем муниципальных образований (текст «ОКТМО»).'); sys.exit(1)
    detect, npat = make_detect(load_oktmo(docx))
    log(f'ОКТМО: {docx}; территорий в справочнике: {npat}')
    if from_csv:
        rows = list(csv.DictReader(open(from_csv, encoding='utf-8'), delimiter=';'))
        for r in rows:
            r['dating_extracted_v1'] = r.get('dating_extracted', r.get('dating_extracted_v1', ''))
            r['_sec_full'] = r['security_info']
    else:
        files = [f for f in sorted(glob.glob('*.json') + glob.glob('*/*.json'), key=lambda x: (len(os.path.basename(x)), os.path.basename(x)))
                 if re.match(r'^(data-)?\d+\.json$', os.path.basename(f))]
        log(f'файлов дампа: {len(files)}')
        if len(files) != 17: log('ВНИМАНИЕ: ожидалось 17 файлов дампа')
        rows = read_dump(files)
    for r in rows: enrich(r, detect)
    with open('egrkn_altai_final.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=HDR_BASE + HDR_NEW, delimiter=';', extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    n = len(rows)
    sha_reg = hashlib.sha256('\n'.join(sorted(r['registry_number'] for r in rows)).encode()).hexdigest()
    sha_dist = hashlib.sha256('\n'.join(sorted(f"{r['record_id']}|{r['district_oktmo']}" for r in rows)).encode()).hexdigest()
    log(f'ИТОГО записей: {n}; в регионе «Алтайский край»: {sum(r["in_altai_region"] == "true" for r in rows)}')
    log(f'районов назначено: {sum(1 for r in rows if r["district_oktmo"])}')
    log(f'аномалий записи региона в адресе: {sum(r["address_region_anomaly"] == "true" for r in rows)}; координат вне края: {sum(r["coord_outside_krai"] == "true" for r in rows)}')
    log(f'dating_object непусто: {sum(1 for r in rows if r["dating_object"])}; dating_event (1941–1945): {sum(1 for r in rows if r["dating_event"])}; прежнее dating_extracted_v1: {sum(1 for r in rows if r["dating_extracted_v1"])}')
    if not from_csv:
        log(f'КОНТРОЛЬ n==4518: {n == EXPECTED_N}')
        log(f'КОНТРОЛЬ sha256 регномеров: {sha_reg}  совпадение: {sha_reg == EXPECTED_SHA_REG}')
    log(f'КОНТРОЛЬ sha256 районов: {sha_dist}  совпадение: {sha_dist == EXPECTED_SHA_DIST}')
    open('build_log.txt', 'w', encoding='utf-8').write('\n'.join(LOG))

def run(json_dir, oktmo_docx, out_path):
    import shutil, tempfile
    cwd = os.getcwd()
    tmp = tempfile.mkdtemp(prefix='s06_')
    try:
        # симлинки на json (чтобы не копировать 750 МБ)
        for f in sorted(glob.glob(os.path.join(json_dir, '*.json'))):
            if 'structure' not in os.path.basename(f).lower():
                os.symlink(os.path.abspath(f), os.path.join(tmp, os.path.basename(f)))
        shutil.copy(oktmo_docx, tmp)
        os.chdir(tmp)
        main()
        os.chdir(cwd)
        shutil.move(os.path.join(tmp, 'egrkn_altai_final.csv'), out_path)
        for extra in ('build_log.txt',):
            src = os.path.join(tmp, extra)
            if os.path.exists(src): shutil.copy(src, os.path.dirname(out_path))
    finally:
        os.chdir(cwd)
        import shutil as _sh
        # очистка симлинков
        for f in glob.glob(os.path.join(tmp, '*')):
            try: os.unlink(f)
            except: pass
        try: os.rmdir(tmp)
        except: pass

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--json-dir', required=True)
    ap.add_argument('--oktmo-docx', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    run(a.json_dir, a.oktmo_docx, a.out)
