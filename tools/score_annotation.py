#!/usr/bin/env python3
"""Score a filled annotation sheet (contrib/annotation_sheet.xlsx, sheet 'Words').
top-1 = column G is 1; top-3 = G in 1-3; coverage = some reading offered. Also by word class of the chosen reading.
Usage: python3 tools/score_annotation.py FILLED.xlsx"""
import sys
from collections import Counter
from openpyxl import load_workbook
ws = load_workbook(sys.argv[1], data_only=True)['Words']
n = t1 = t3 = 0
cls = Counter(); cls_ok = Counter()
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[6] in (None, ''):
        continue
    g = int(row[6]); n += 1
    t1 += g == 1; t3 += g in (1, 2, 3)
    pos = (str(row[3]).split() or ['?'])[0] if g == 0 else (str(row[2 + g]).split() or ['?'])[0]
    c = row[7] if g == 0 and row[7] else pos
    cls[c] += 1; cls_ok[c] += g == 1
print(f'annotated {n}   top-1 {t1}/{n} = {100 * t1 / max(n, 1):.1f}%   top-3 {t3}/{n} = {100 * t3 / max(n, 1):.1f}%')
for c, k in cls.most_common():
    print(f'  {c:12s} {k:4d}   top-1 {100 * cls_ok[c] / k:5.1f}%')
