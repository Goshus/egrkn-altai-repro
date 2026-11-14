# REPRODUCE.md — пошаговое воспроизведение

## Предварительные условия
- Python 3.12 (проверено); зависимости — `pip install -r requirements.txt` (matplotlib — рисунки, pyproj — расстояния до границы, PyYAML — необязательно).
- Для тестов: `pip install pytest`.

## Входные данные для перегенерации

| Файл | Источник | Где взять |
|---|---|---|
| `1.json` … `17.json` — дамп ЕГРОКН | Минкультуры России, публичная часть ЕГРОКН (esb.mkrf.ru), получен 09.09.2026 | по запросу к авторам; sha256 и размеры — `data/input_manifest/manifest_dump.csv` |
| `Spisok-obektov-kulturnogo-naslediya (ukn.alregn.ru).md` — краевой список в формате Markdown | PDF с сайта ukn.alregn.ru (94 с.), преобразованный в Markdown; sha256 `1d0d97cbb308489bd4cc044749683e05bfc1ef203b26dd00ef33800dfb102518` | по запросу к авторам; структуру проверяет `python src/verify_markdown.py --md <файл>` |
| Перечень муниципальных образований Алтайского края на 01.01.2026 (`.docx`) | открытые данные, набор 7705851331-egrkn | `data/reference/` |
| `boundary_1.json` … `boundary_3.json` — границы районов | OpenStreetMap, ODbL 1.0 | `data/boundaries/` |

## Шаги
1. Положить входные файлы в папку `inputs/` (или указать другую через `--inputs`).
2. `python src/run_all.py --inputs inputs` — перегенерирует `data/derived/`:
   - `s06` → `egrkn_altai_final.csv` (32 колонки; 4518 записей, sha256 регистрационных номеров `86afa4ab…`, sha256 районов `8734de19…`);
   - `s04` → `gukn_spisok_all_fixed.csv` (2204 записи);
   - `s05` → `matches_fixed.csv`, `list_only_fixed.csv`, `dump_only_pilot_fixed.csv`;
   - `s07` → `geo_diagnostics.csv`;
   - `s03` → `egrkn_meta.csv`;
   - `s08` → `results_long_fixed.csv`, `table_2_coverage.csv`, `table_3_field_completeness.csv`, `table_4_groups.csv`, `table_5_discrepancies.csv`.
3. `python src/run_all.py --check` — сверка контрольных значений и sha256 результатов.
4. Объекты из приказов о включении в перечень выявленных:
   `python src/s09_orders_trace.py --egrkn data/derived/egrkn_altai_final.csv --list data/derived/gukn_spisok_all_fixed.csv --manual data/manual/blind_zone_report_manual.csv --out data/derived/blind_zone_report.csv`
5. Рисунки 1 и 2 (PNG, 300 dpi):
   `python src/s10_figures.py --geo data/derived/geo_diagnostics.csv --boundaries-dir data/boundaries --perechen data/manual/perechen_check.csv --auto data/derived/blind_zone_report.csv --out-dir figures`
   Скрипт выводит числа по районам и результат автоматической проверки наложений подписей.

## Проверка без перегенерации
`python src/run_all.py --check` сверяет `data/derived/` с контрольными значениями; `sha256sum -c CHECKSUMS.sha256` проверяет файлы репозитория.

## Ручная разметка
`data/manual/blind_zone_report_manual.csv` (реестр приказов), `data/manual/perechen_check.csv` (наличие объектов в перечне выявленных на апрель 2026 г.) и `data/manual/verification_sample_FINAL_checked.xlsx` (контрольная выборка из 20 записей, отобранная авторами из записей пилотных районов и проверенная вручную; отбор скриптом не воспроизводится) — результаты ручной работы авторов; шаги скриптов используют их как входные данные.

## Метрика расстояния до границы
Расстояние до границы района считается в локальной азимутальной эквидистантной проекции на эллипсоиде WGS 84; значения для 12 записей Змеиногорского района — в `data/derived/geo_boundary_distances.csv` (минимум 6707,864 м, запись E02493).
