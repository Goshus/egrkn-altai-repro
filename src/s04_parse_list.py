# -*- coding: utf-8 -*-
"""s04_parse_list.py — шаг 4 статьи: разбор краевого списка ГУКН (Markdown → CSV).

Источник: layers_and_results.py:47-60 (parse_spisok_md) ИСПРАВЛЕННАЯ версия (заход 11).
Эталонный sha256 старой версии layers_and_results.py (1d8dcb3b…) относится к версии С ОШИБКОЙ
(условие строки 57 `cells[0] and not set(cells[0]) <= {'-'}` пропускало запись с пустым наименованием
даже при наличии регномера; `set('') = {} ⊆ {'-'}` → для пустого cells[0] условие ложно).
Исправление: `(cells[0] or cells[7].strip())` + `not (cells[0] and set(cells[0]) <= {'-'})`.
Результат: восстановлено 2204 (было 2201); заявлено 2204.

Шаг статьи → скрипт → выход → таблица:
  «список ГУКН: 2204 записи» → s04 → gukn_spisok_all_fixed.csv → таблица 2.
"""
import csv, os, re, argparse, sys

def parse_spisok_md(path):
    """ИСПРАВЛЕННЫЙ parse_spisok_md (заход 11). Возвращает (rows, declared)."""
    text = open(path, encoding='utf-8').read()
    m = re.search(r'Всего записей:\s*\*{0,2}(\d+)', text)
    declared = int(m.group(1)) if m else None
    rows, buf = [], ''
    for line in text.splitlines():
        if not line.strip().startswith('|'): continue
        buf += line.strip()
        if buf.count('|') >= 9:
            cells = [c.strip() for c in buf.split('|')[1:-1]]
            # ИСПРАВЛЕНИЕ: не пропускаем запись с пустым наименованием при наличии регномера (cells[7])
            if len(cells) == 8 and (cells[0] or cells[7].strip()) and not (cells[0] and set(cells[0]) <= {'-'}) and 'Наименование объекта' not in cells[0]:
                rows.append(cells)
            buf = ''
    return rows, declared

def main(md_path, out_path):
    L, declared = parse_spisok_md(md_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['name_raw', 'district_raw', 'address', 'category', 'obj_type', 'ensemble', 'general_type', 'registry_number'])
        w.writerows(L)
    print(f's04: заявлено {declared}; восстановлено (fixed) {len(L)} -> {out_path}')
    return len(L), declared

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--md', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    main(a.md, a.out)
