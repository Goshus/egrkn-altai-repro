# data/input_manifest/ — манифест входных файлов

Манифест описывает входные файлы пайплайна: контрольные суммы, размеры, источники и дату получения (09.09.2026).

## Файлы
- `manifest_dump.csv` — sha256 и размер 17 файлов дампа ЕГРОКН (`1.json` … `17.json`).
- `probe_report.csv` — результат отбора записей по каждому файлу дампа (`records_total`, `altai_by_region`, `altai_by_regnum22`, `region_not_regnum`); сумма `altai_by_region` равна 4516.
- `structure-17.json` — схема канонической модели Heritage (esb.mkrf.ru/cdm/v2/heritages), описывающая структуру записей дампа.

## Источники
- Дамп ЕГРОКН: выгрузка из esb.mkrf.ru (каноническая модель `ru.armf.mkesb.model.canonical.heritage.Heritage`), публичная часть реестра; файлы предоставляются авторами по запросу.
- Краевой список: ukn.alregn.ru (PDF), преобразованный в Markdown; структуру результата проверяет `src/verify_markdown.py`.
- Перечень ОКТМО: `data/reference/`.

## Контроль
Для сверки дампа с манифестом выполните `sha256sum` по файлам `1.json` … `17.json` и сравните со столбцом `sha256` в `manifest_dump.csv`.
