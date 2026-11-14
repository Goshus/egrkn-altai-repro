ЧЕРНОВИК, ждёт решения авторов.

RELEASE_CHECKLIST.md — контрольный список выпуска версии

Этапы оформления релиза репозитория egrkn-altai-repro (порядок действий).

1. Метка версии
   - [ ] Установить номер версии в CITATION.cff (поле version) — текущий кандидат 1.0.0-rc1.
   - [ ] Присвоить git-тег вида v1.0.0 (annotate): git tag -a v1.0.0 -m "Release 1.0.0".
   - [ ] Проверить, что дата date-released в CITATION.cff соответствует дате релиза.

2. Архив
   - [ ] Собрать ZIP из чистого дерева (без __pycache__/, *.pyc, временных файлов):
         zip -r egrkn-altai-repro-v1.0.0.zip egrkn-altai-repro -x '*/__pycache__/*' '*.pyc'.
   - [ ] Вычислить sha256 архива и записать в журнал приёма и в описание релиза:
         sha256sum egrkn-altai-repro-v1.0.0.zip.
   - [ ] Проверить целостность: sha256sum -c CHECKSUMS.sha256 — все OK.

3. Воспроизводимость (чистый прогон)
   - [ ] Распаковать архив в пустую папку; создать чистое виртуальное окружение
         (python -m venv venv; source venv/bin/activate); установить зависимости
         без сети: pip install --no-index --find-links=wheelhouse -r requirements.txt
         (предварительно собрать wheelhouse: pip download -r requirements.txt -d wheelhouse).
   - [ ] python src/run_all.py --check — ожидается «ВСЕ СОВПАЛО».
   - [ ] pytest tests/test_reproduce.py — ожидается 14 passed.
   - [ ] Повторный прогон: сравнить sha256 всех выходных файлов data/derived/
         между двумя запусками — ожидается полное совпадение (детерминированность).

4. DOI и публикация
   - [ ] Зарегистрировать репозиторий в Zenodo (или аналогичном архиве) и получить DOI.
   - [ ] Внести DOI в CITATION.cff (поле doi) и в repository-code (URL).
   - [ ] Указать DOI в README.md и в описании релиза.

5. Лицензии и сторонние данные
   - [ ] Подтвердить выбор лицензий (LICENSE — MIT для кода; LICENSE-DATA — CC BY 4.0
         для авторской документации и ручной разметки) — снять метку «ЧЕРНОВИК».
   - [ ] Уточнить у правообладателей условия использования данных ЕГРОКН
         (Минкультуры РФ), краевого списка (ukn.alregn.ru), перечня ОКТМО —
         заменить «не установлено» в THIRD_PARTY.md на подтверждённые условия.
   - [ ] Границы OSM: сохранить атрибуцию «© участники OpenStreetMap, ODbL 1.0»
         во всех производных (рисунки, geo_diagnostics).

6. Финальная сверка
   - [ ] Перечень выходных таблиц и рисунков соответствует таблицам/рисункам статьи.
   - [ ] sha256-журнал (data/input_manifest/manifest_dump.csv, CHECKSUMS.sha256,
         expected/sha256_derived.csv) актуализирован.
