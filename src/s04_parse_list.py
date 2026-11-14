# -*- coding: utf-8 -*-
"""s04_parse_list.py — шаг 4 статьи: разбор краевого списка ГУКН (Markdown → CSV).

Разбор таблицы Markdown: запись принимается при непустом наименовании или непустом регистрационном номере (cells[7]);
строки-разделители и шапка пропускаются. Результат: 2204 записи; заявлено в документе 2204.

Шаг статьи → скрипт → выход → таблица:
  «список ГУКН: 2204 записи» → s04 → gukn_spisok_all_fixed.csv → таблица 2.
"""
import csv, os, re, argparse, sys

def parse_spisok_md(path):
    """Разбор краевого списка. Возвращает (rows, declared)."""
    text = open(path, encoding='utf-8').read()
    m = re.search(r'Всего записей:\s*\*{0,2}(\d+)', text)
    declared = int(m.group(1)) if m else None
    rows, buf = [], ''
    for line in text.splitlines():
        if not line.strip().startswith('|'): continue
        buf += line.strip()
        if buf.count('|') >= 9:
            cells = [c.strip() for c in buf.split('|')[1:-1]]
            # Не пропускаем запись с пустым наименованием при наличии регномера (cells[7])
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
