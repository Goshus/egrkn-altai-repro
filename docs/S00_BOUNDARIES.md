# s00_fetch_boundaries.py — загрузка и сверка границ районов

Скрипт `src/s00_fetch_boundaries.py` получает границы трёх пилотных районов из OpenStreetMap (сервис Nominatim, лицензия ODbL 1.0) и сверяет их с файлами в `data/boundaries/`.

## Идентификаторы OSM (из `properties.osm_id`)

| Файл | Район | Тип | osm_id | Вершин | sha256 |
|---|---|---|---|---|---|
| data/boundaries/boundary_1.json | Змеиногорский | relation | 1083293 | 3484 | fec3699e8930565ed7e8942c22e0582d921c335849621c66b41f1db5af83171b |
| data/boundaries/boundary_2.json | Красногорский | relation | 1150926 | 3953 | 3f16453b645c13f17aa570b1da9bd67fbeb10edc64e8208e76b59f567429a323 |
| data/boundaries/boundary_3.json | Солтонский | relation | 1150924 | 2213 | 97c15ebfaf43e593724350a973fce80acfe1ef4fb6eb234234999ed0b74b90b2 |

## Режим `--mode verify` (без сети)

Сверяет sha256 файлов `boundary_*.json` в `--boundaries-dir` с файлами в `--frozen-dir`.

```bash
python src/s00_fetch_boundaries.py --mode verify --boundaries-dir data/boundaries --frozen-dir data/boundaries
```

Ожидаемый результат: для каждого из трёх файлов строка `boundary_N: <sha256> == <sha256> → совпал`, код возврата 0. При расхождении выводится `РАСХОЖДЕНИЕ`, код возврата 1.

## Режим `--mode refetch` (нужен доступ к nominatim.openstreetmap.org)

Запрашивает актуальную геометрию трёх relation (`polygon_geojson=1`) и сравнивает число вершин с файлами репозитория; сами файлы не перезаписываются. Ответы сохраняются в `--cache-dir` (по умолчанию `cache_nominatim/`). Режим не входит в автоматическую проверку `run_all.py --check`.

```bash
python src/s00_fetch_boundaries.py --mode refetch --boundaries-dir data/boundaries --cache-dir cache_nominatim
```

Ожидаемый результат при неизменных границах в OSM: число вершин 3484, 3953 и 2213 и `совпадение по числу вершин: True` для каждого района.

Если число вершин отличается, границу района изменили в OSM после выгрузки: это обновление источника. Новую границу сохраняют в режиме `--mode fetch`, фиксируют дату выгрузки и пересчитывают `geo_diagnostics.csv` и `geo_boundary_distances.csv`. Сообщение `запрос не выполнен` означает отсутствие сети, недоступность сервиса или превышение лимита запросов; пауза между запросами — 1 с, при ответе 429 её увеличивают.

## Режим `--mode fetch`

Сохраняет выгруженную геометрию в `--boundaries-dir`; используется для первичной выгрузки или планового обновления границ.

## Условия использования

© участники OpenStreetMap, лицензия ODbL 1.0. Производные данные (`geo_diagnostics.csv`, `geo_boundary_distances.csv`, рисунок 1) сохраняют условия ODbL; атрибуция OSM обязательна при публикации (см. `THIRD_PARTY.md`, `LICENSE-DATA`).
