# detect_districts_v2.py — день 1: назначение муниципальных территорий всем записям среза ЕГРОКН
# Вход в текущей папке: egrkn_altai_full.csv + ОКТМО-перечень (*.docx)
# Выход: egrkn_altai_full_v2_districts.csv, district_stats.csv, urban_rural_stats.csv, контрольная сумма в консоль
import csv, glob, os, re, zipfile, hashlib

def load_oktmo(path):
    xml = zipfile.ZipFile(path).read('word/document.xml').decode('utf-8')
    xml = xml.replace('</w:p>','\n').replace('</w:tc>',' | ').replace('</w:tr>','\n')
    txt = re.sub(r'<[^>]+>','',xml)
    terr = []
    for line in txt.splitlines():
        m = re.search(r'-\s*(.+?)\s*(?:\||$)', line)
        if not m: continue
        name = m.group(1).strip()
        if not name: continue
        if name.startswith('Муниципальный округ'):
            core = name.replace('Муниципальный округ','').strip()
            base = core[:-6] if core.endswith(' район') else core
            terr.append(('округ', base))
        elif name.endswith('муниципальный район'):
            terr.append(('район', name[:-19].strip()))
        elif name.startswith('город '):
            terr.append(('город', name.replace('город ','').strip()))
        elif name.endswith('район') and 'муниципальный' not in name:
            terr.append(('район', name[:-6].strip()))
    return terr

def stem(b):
    b = b.lower()
    for suf in ('ский','ской','цкий','ний','ной','ный','ий','ый','ой','ое','ья'):
        if b.endswith(suf): return b[:-len(suf)]
    return b

def build_patterns(terr):
    pats = []
    for kind, base in terr:
        s = stem(base)
        if len(s) >= 4:
            pats.append((f'{base} ({kind})' if kind != 'город' else f'г. {base}', kind, s))
    return pats

def make_detect(pats):
    def detect(address):
        segs = [s.strip().lower() for s in str(address or '').split(',')]
        for seg in segs:
            if 'район' in seg or 'округ' in seg:
                for name, kind, s in pats:
                    if kind in ('район','округ') and s in seg:
                        return name
        for seg in segs:
            for name, kind, s in pats:
                if kind == 'город' and s in seg:
                    return name
        return ''
    return detect

def selt_type(st):
    st = (st or '').lower().strip()
    if re.match(r'^(с\.|п\.|д\.|пгт|ст\.|рзд|село|деревня)', st): return 'сельское'
    if re.match(r'^(г\.|город)', st): return 'городское'
    return ''

def main():
    docx = next((f for f in glob.glob('*.docx') if 'erechen' in f.lower() or 'октмо' in f.lower()), None) or next(iter(glob.glob('*.docx')), None)
    pats = build_patterns(load_oktmo(docx))
    detect = make_detect(pats)
    rows = list(csv.DictReader(open('egrkn_altai_full.csv', encoding='utf-8'), delimiter=';'))
    fields = list(rows[0].keys()) + ['district_oktmo','settlement_type']
    stats, grp = {}, {}
    for r in rows:
        d = detect(r['address_full']); t = selt_type(r['settlement'])
        r['district_oktmo'] = d; r['settlement_type'] = t or 'не определено'
        if d:
            s = stats.setdefault(d, dict(n=0, coords=0, addr=0, docs=0, dat=0, sec=0)); s['n'] += 1
            for k, f in (('coords','lat'), ('addr','address_full'), ('docs','documents'), ('dat','dating_extracted'), ('sec','security_info')):
                s[k] += bool((r[f] or '').strip())
        g = grp.setdefault(r['settlement_type'], dict(n=0, coords=0, addr=0, docs=0, dat=0, sec=0)); g['n'] += 1
        for k, f in (('coords','lat'), ('addr','address_full'), ('docs','documents'), ('dat','dating_extracted'), ('sec','security_info')):
            g[k] += bool((r[f] or '').strip())
    with open('egrkn_altai_full_v2_districts.csv','w',newline='',encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=';'); w.writeheader(); w.writerows(rows)
    with open('district_stats.csv','w',encoding='utf-8') as f:
        f.write('territory;records;share_of_all_%;with_coords_%;with_address_%;with_documents_%;with_dating_%;with_security_info_%\n')
        for d, s in sorted(stats.items(), key=lambda x: -x[1]['n']):
            f.write(f"{d};{s['n']};{s['n']/len(rows)*100:.2f};{s['coords']/s['n']*100:.1f};{s['addr']/s['n']*100:.1f};{s['docs']/s['n']*100:.1f};{s['dat']/s['n']*100:.1f};{s['sec']/s['n']*100:.1f}\n")
    with open('urban_rural_stats.csv','w',encoding='utf-8') as f:
        f.write('group;records;share_of_all_%;with_coords_%;with_address_%;with_documents_%;with_dating_%;with_security_info_%\n')
        for t in ('сельское','городское','не определено'):
            g = grp.get(t)
            if g:
                f.write(f"{t};{g['n']};{g['n']/len(rows)*100:.2f};{g['coords']/g['n']*100:.1f};{g['addr']/g['n']*100:.1f};{g['docs']/g['n']*100:.1f};{g['dat']/g['n']*100:.1f};{g['sec']/g['n']*100:.1f}\n")
    chk = hashlib.sha256('\n'.join(sorted(f"{r['record_id']}|{r['district_oktmo']}" for r in rows)).encode()).hexdigest()
    n_all = sum(1 for r in rows if r['district_oktmo'])
    print(f'территорий в паттернах: {len(pats)}; назначено районов: {n_all} из {len(rows)} ({n_all/len(rows)*100:.1f}%)')
    print(f'КОНТРОЛЬНАЯ СУММА назначений: {chk}')
    print('ОЖИДАЛОСЬ: 56fe27e57794c3c431c8809c97fdf101f6cf2031ce3bd6cffcd2805746b9e06b')
    print('СОВПАДЕНИЕ:', chk == '56fe27e57794c3c431c8809c97fdf101f6cf2031ce3bd6cffcd2805746b9e06b')

if __name__ == '__main__': main()
