# data/boundaries/ — границы пилотных районов

Файлы `boundary_1.json`, `boundary_2.json`, `boundary_3.json` — границы административных районов Алтайского края из OpenStreetMap (выгрузка через Nominatim, `polygon_geojson=1`).

| Файл | Район | OSM ID (relation) | вершин |
|---|---|---|---|
| boundary_1.json | Змеиногорский | 1083293 | 3484 |
| boundary_2.json | Красногорский | 1150926 | 3953 |
| boundary_3.json | Солтонский | 1150924 | 2213 |

Идентификаторы OSM установлены из самих файлов (`properties.osm_id`).

## Лицензия
ODbL 1.0 (Open Data Commons Open Database License), © участники OpenStreetMap. При использовании границ необходимо указывать источник: © OpenStreetMap contributors, ODbL 1.0.

## Повторная выгрузка
`python ../../src/s00_fetch_boundaries.py --mode refetch --boundaries-dir . --cache-dir ../../cache_nominatim` — запрашивает Nominatim и сравнивает по числу вершин с замороженными файлами БЕЗ перезаписи. Скрипт RECONSTRUCTED, не проверен запуском (нет доступа в интернет). Режим `--verify` сверяет sha256 с замороженными.
