# data/boundaries/ — границы пилотных районов

Файлы `boundary_1.json`, `boundary_2.json`, `boundary_3.json` — границы районов Алтайского края из OpenStreetMap (сервис Nominatim, `polygon_geojson=1`).

| Файл | Район | OSM ID (relation) | Вершин |
|---|---|---|---|
| boundary_1.json | Змеиногорский | 1083293 | 3484 |
| boundary_2.json | Красногорский | 1150926 | 3953 |
| boundary_3.json | Солтонский | 1150924 | 2213 |

Идентификаторы OSM записаны в самих файлах (`properties.osm_id`).

## Лицензия
ODbL 1.0 (Open Data Commons Open Database License), © участники OpenStreetMap. При использовании границ указывайте источник: © OpenStreetMap contributors, ODbL 1.0.

## Проверка и повторная выгрузка
- Сверка контрольных сумм без сети: `python src/s00_fetch_boundaries.py --mode verify --boundaries-dir data/boundaries --frozen-dir data/boundaries`.
- Повторная выгрузка из Nominatim со сравнением по числу вершин, без перезаписи файлов: `python src/s00_fetch_boundaries.py --mode refetch --boundaries-dir data/boundaries --cache-dir cache_nominatim` (нужен доступ в интернет).

Подробности — в `docs/S00_BOUNDARIES.md`.
