# REPRODUCE.md — пошаговое воспроизведение

## Предварительные условия
- Python 3.10+ (стандартная библиотека; matplotlib необязателен — только для рисунков).
- Входные данные (НЕ входят в репозиторий):
  - дамп ЕГРОКН: 17 файлов `1.json`…`17.json` (sha256 в `data/input_manifest/manifest_dump.csv`), получен 09.09.2026;
  - краевой список ГУКН: `Spisok-obektov-kulturnogo-naslediya (ukn.alregn.ru).md` (преобразование PDF→md выполнено внешним инструментом; проверить структуру: `python src/verify_markdown.py --md <path>`);
  - перечень муниципальных образований Алтайского края на 01.01.2026 (`.docx`) — `data/reference/`;
  - границы пилотных районов `boundary_1..3.json` — `data/boundaries/` (ODbL 1.0, © OpenStreetMap); для повторной выгрузки `python src/s00_fetch_boundaries.py --mode refetch --boundaries-dir data/boundaries --cache-dir cache_nominatim` (требует доступа в интернет; скрипт не проверен запуском).

## Шаги
1. Положить входные данные в папку `inputs/` (или использовать `--inputs <dir>`).
2. `python src/run_all.py --inputs inputs` — перегенерирует `data/derived/`:
   - s06 → `egrkn_altai_final.csv` (32 колонки; контроль 4518, sha256 регномеров 86afa4ab…, sha256 районов 8734de19…);
   - s04 → `gukn_spisok_all_fixed.csv` (2204);
   - s05 → `matches_fixed.csv`, `list_only_fixed.csv`, `dump_only_pilot_fixed.csv`;
   - s07 → `geo_diagnostics.csv`;
   - s08 → `results_long_fixed.csv`, `table_2_coverage.csv`, `table_5_discrepancies.csv`.
3. `python src/run_all.py --check` — приёмка контрольных значений и sha256.
4. (опционально) `python src/s09_orders_trace.py --egrkn data/derived/egrkn_altai_final.csv --list data/derived/gukn_spisok_all_fixed.csv --manual data/manual/blind_zone_report_manual.csv --out data/derived/blind_zone_report.csv`.
5. (опционально) `python src/s10_figures.py --geo data/derived/geo_diagnostics.csv --boundaries-dir data/boundaries --perechen data/manual/perechen_check.csv --auto data/derived/blind_zone_report.csv --out-dir figures/ --mode both` (рис. 1, 2; PNG 300 dpi; DejaVu Sans; числа из данных).

## Проверка замороженных файлов
Без перегенерации: `python src/run_all.py --check` сверяет `data/derived/` с контрольными значениями.
`sha256sum -c CHECKSUMS.sha256` — сверка всех файлов репозитория.

## Что НЕ воспроизводится из публичных источников
- Дамп ЕГРОКН (17 файлов JSON): выгрузка из esb.mkrf.ru, не публичный API; sha256 в манифесте, но сами файлы нужно получить у авторов или из источника.
- PDF краевого списка ГУКН (ukn.alregn.ru): преобразование в md выполнено внешним инструментом (не установлен); в репозитории только md (через `data/input_manifest/` указано отсутствие PDF).
- Верификационная выборка `verification_sample_FINAL_checked.xlsx` — ручная разметка (`data/manual/`).
- Эталон ручной части реестра приказов ВОКН `blind_zone_report_manual.csv` — ручная разметка (`data/manual/`); реквизиты 19 приказов сверены с прежним `prikazy_vokn_2019_2026.csv` (19/19 совпадение, см. отчёт захода 13).

## Известные расхождения
- Минимальное расстояние до границы (заход 14): локальная азимутальная эквидистантная проекция (AEQD), эллипсоид WGS 84 — 6707,864 м (E02493; ближайшая точка границы — вершина полигона). Значение зафиксировано в `data/derived/geo_boundary_distances.csv` и сверяется командой `python src/run_all.py --check`. Раннее значение 6693 м (заход 13) относилось к сферической метрике haversine (R=6371000) и заменено как менее точное.
- Минимальное расстояние 6693 м (приёмка) не воспроизведено: `layers_and_results.py` и `geo_qc_blindzone.py` не вычисляют мин. расстояние как отдельную метрику; `geo_qc_blindzone.py` считает дубликаты по `name_norm + haversine ≤ 150 м` (DUP_MAX_M). Ближайшие кандидаты в г. Барнаул (16 пар 6647–6766 м, мин. 6647 E00437–E01292); пилотные 12 точек Змеиногорского → 35,1 м (элементы «Комплекса исторического центра»). Контекст «6693 м» не установлен.
- z таблицы 4 (мемориалы 2,3; −0,5; прочие 0,8; −6,6; градостроительство −9,8; −10,6) — не воспроизведено: состав сравниваемых групп и пары (k1,n1)↔(k2,n2) не установлены из скриптов.
