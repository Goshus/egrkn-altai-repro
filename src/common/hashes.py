# -*- coding: utf-8 -*-
"""hashes.py — sha256 файлов и контрольных сумм (из egrkn_pipeline_v131.py:88-92, build_final_table.py:250-251)."""
import hashlib, os

def sha256_file(fp):
    h = hashlib.sha256()
    with open(fp, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()

def sha256_sorted(values):
    """sha256 от '\n'.join(sorted(values)) — контрольная сумма регномеров/районов (build_final_table.py:250-251)."""
    return hashlib.sha256('\n'.join(sorted(str(v) for v in values)).encode()).hexdigest()

# Эталоны (из build_final_table.py:9-10, egrkn_pipeline_v131.py:3)
EXPECTED_N = 4518
EXPECTED_SHA_REG = '86afa4ab35e33724e918b387718ecea5590a9d98f39159f05cbe61a1f00bad89'
EXPECTED_SHA_DIST = '8734de19653642edd80310aa0dc5cd1db862fb9169ca538285c91165eb9196ac'
