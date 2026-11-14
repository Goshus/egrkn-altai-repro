# -*- coding: utf-8 -*-
"""verify_markdown.py — проверка структуры Markdown-выгрузки краевого списка ГУКН.

Шаг PDF→Markdown выполнен внешним инструментом; исходный код инструмента не установлен.
Скрипт только проверяет структуру результата (8 столбцов, 2204 записи, шапка), не воспроизводя
преобразование. PDF списка и сам дамп ЕГРОКН в репозиторий не копируются (см. data/input_manifest/).

Контроль:
  - таблица с шапкой «Наименование объекта | Район | Адрес | Категория | Вид | Ансамбль | Видовая | Рег. номер»;
  - ровно 8 столбцов на запись;
  - число записей = заявленное «Всего записей» в начале файла (2204).
"""
import re, argparse, sys

EXPECTED_COLS = 8
HEADER_TOKEN = 'Наименование объекта'

def verify(md_path):
    text = open(md_path, encoding='utf-8').read()
    m = re.search(r'Всего записей:\s*\*{0,2}(\d+)', text)
    declared = int(m.group(1)) if m else None
    rows, buf = [], ''
    bad = []
    for line in text.splitlines():
        if not line.strip().startswith('|'): continue
        buf += line.strip()
        if buf.count('|') >= 9:
            cells = [c.strip() for c in buf.split('|')[1:-1]]
            if len(cells) != EXPECTED_COLS:
                bad.append(('cols', len(cells), buf[:60]))
            if 'Наименование объекта' not in cells[0] and not (cells[0] and set(cells[0]) <= {'-'}) and (cells[0] or cells[7].strip()):
                rows.append(cells)
            buf = ''
    has_header = HEADER_TOKEN in text
    print(f'verify_markdown: заявлено {declared}; восстановлено {len(rows)}; колонок {EXPECTED_COLS}; шапка {"есть" if has_header else "НЕТ"}')
    if bad:
        print(f'  строк с нарушением числа колонок: {len(bad)}; примеры: {bad[:3]}')
    ok = declared == len(rows) and has_header and not bad
    print(f'  итог: {"OK" if ok else "НЕ СОВПАЛО"}')
    return ok, declared, len(rows)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--md', required=True)
    a = ap.parse_args()
    ok, declared, n = verify(a.md)
    sys.exit(0 if ok else 1)
