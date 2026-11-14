# -*- coding: utf-8 -*-
"""normalize.py — нормализация наименований и районов."""
import re, unicodedata

PREFIXES = ['объект культурного наследия', 'окн регионального значения', 'окн федерального значения', 'окн',
 'памятник', 'памятника', 'памятнику', 'могила', 'могилы', 'могилу', 'здание', 'здания', 'зданию',
 'сооружение', 'сооружения', 'сооружению', 'объект', 'объекта', 'объекту', 'останки', 'остатки']

def norm_name(s):
    s = unicodedata.normalize('NFC', str(s or '')).lower()
    s = re.sub(r"[«»\"„“”'(),./-]", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def norm_name_pipeline(s):
    """Нормализация наименования со снятием префиксов (для s01)."""
    if not s: return ''
    s = norm_name(s)
    changed = True
    while changed:
        changed = False
        for p in PREFIXES:
            if s == p or s.startswith(p + ' '):
                s = s[len(p):].strip(' ,.-'); changed = True
    return s

def stem(b):
    b = (b or '').lower()
    for suf in ('ский', 'ской', 'цкий', 'ний', 'ной', 'ный', 'ий', 'ый', 'ой', 'ое', 'ья'):
        if b.endswith(suf): return b[:-len(suf)]
    return b

def regkey(x):
    d = re.sub(r'\D', '', str(x or ''))
    return d.zfill(15) if d and len(d) < 15 else d

def share(n, d):
    return round(n / d * 100, 1) if d else ''
