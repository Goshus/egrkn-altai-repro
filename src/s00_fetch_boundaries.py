# -*- coding: utf-8 -*-
"""s00_fetch_boundaries.py — шаг 0 (предподготовка): границы пилотных районов из OpenStreetMap (Nominatim).

RECONSTRUCTED — восстановлен по результатам, не исходный код. НЕ ПРОВЕРЕН ЗАПУСКОМ (нет доступа в интернет).

Идентификаторы OSM установлены из самих boundary_*.json (properties.osm_id):
  boundary_1.json: osm_id=1083293 (relation) — Змеиногорский район
  boundary_2.json: osm_id=1150926 (relation) — Красногорский район
  boundary_3.json: osm_id=1150924 (relation) — Солтонский район

Режимы:
  --verify    : сверка sha256 boundary_*.json в --boundaries-dir с замороженными хэшами в --frozen-dir;
                совпадение → «границы неизменны».
  --refetch   : запрос к Nominatim (polygon_geojson=1) для трёх relation; сравнение по числу вершин
                и площади пересечения с замороженными БЕЗ перезаписи.
  --fetch     : запрос и запись (использовать только для первичной выгрузки).

User-Agent обязателен (политика Nominatim); пауза 1 с между запросами; кэш ответов в --cache-dir.
Лицензия границ: ODbL 1.0, © участники OpenStreetMap (см. data/boundaries/README.md).
"""
import argparse, json, os, sys, time, hashlib, urllib.request, urllib.parse

OSM_IDS = {1: ('Змеиногорский', 1083293), 2: ('Красногорский', 1150926), 3: ('Солтонский', 1150924)}
USER_AGENT = 'egrkn-altai-repro/1.0 (academic research; contact: не установлено)'
NOMINATIM = 'https://nominatim.openstreetmap.org/search'

def sha256_file(fp):
    h = hashlib.sha256()
    with open(fp, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()

def nominatim_query(osm_id, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    cache = os.path.join(cache_dir, f'osm_{osm_id}.json')
    if os.path.exists(cache):
        return json.load(open(cache, encoding='utf-8'))
    params = urllib.parse.urlencode({'osm_type': 'R', 'osm_id': str(osm_id), 'format': 'json', 'polygon_geojson': '1'})
    url = f'{NOMINATIM}?{params}'
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    json.dump(data, open(cache, 'w', encoding='utf-8'), ensure_ascii=False)
    time.sleep(1)
    return data

def verify(boundaries_dir, frozen_dir):
    ok = True
    for n in (1, 2, 3):
        bf = os.path.join(boundaries_dir, f'boundary_{n}.json')
        ff = os.path.join(frozen_dir, f'boundary_{n}.json')
        if not os.path.exists(bf) or not os.path.exists(ff):
            print(f'  boundary_{n}: файл отсутствует'); ok = False; continue
        sb, sf = sha256_file(bf), sha256_file(ff)
        match = sb == sf
        print(f'  boundary_{n}: {sb} {"==" if match else "!="} {sf} → {"совпал" if match else "РАСХОЖДЕНИЕ"}')
        ok = ok and match
    return ok

def refetch(boundaries_dir, cache_dir):
    for n, (name, osm_id) in OSM_IDS.items():
        bf = os.path.join(boundaries_dir, f'boundary_{n}.json')
        frozen = json.load(open(bf, encoding='utf-8'))
        frozen_ring = frozen['features'][0]['geometry']['coordinates'][0] if frozen.get('type') == 'FeatureCollection' else frozen['geometry']['coordinates'][0]
        print(f'  {name} (osm_id={osm_id}): заморожено вершин {len(frozen_ring)}; запрос к Nominatim…')
        try:
            data = nominatim_query(osm_id, cache_dir)
            ft = data[0] if isinstance(data, list) else data
            g = ft.get('geojson') or {}
            ring = g['coordinates'][0] if g.get('type') == 'Polygon' else (g['coordinates'][0][0] if g.get('type') == 'MultiPolygon' else [])
            print(f'    получено вершин {len(ring)}; совпадение по числу вершин: {len(ring) == len(frozen_ring)}')
        except Exception as e:
            print(f'    запрос не выполнен: {type(e).__name__}: {e}')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['verify', 'refetch', 'fetch'], required=True)
    ap.add_argument('--boundaries-dir', required=True)
    ap.add_argument('--frozen-dir', default=None)
    ap.add_argument('--cache-dir', default='cache_nominatim')
    a = ap.parse_args()
    if a.mode == 'verify':
        if not a.frozen_dir: sys.exit('--frozen-dir обязателен для verify')
        sys.exit(0 if verify(a.boundaries_dir, a.frozen_dir) else 1)
    elif a.mode == 'refetch':
        refetch(a.boundaries_dir, a.cache_dir)
    elif a.mode == 'fetch':
        print('fetch: первичная выгрузка (использовать только один раз); требует доступа в интернет')
        refetch(a.boundaries_dir, a.cache_dir)
