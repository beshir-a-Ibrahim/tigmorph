#!/usr/bin/env python3
"""Corpus coverage over all word classes, from build/corpus_analyses.jsonl (top 100k word types).
A token is covered when its word has an analysis from the lexicon (verb root, function word, clitic split),
not just from the guesser. Top-1 class = class of the best-ranked analysis.
Usage: python3 tools/coverage_all.py [--json]"""
import sys, os, json
from collections import Counter
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs('build', exist_ok=True)
sys.path.insert(0, '.')
from tigmorph.analyzer import Analyzer, Analysis

A = Analyzer()
tot = cov = 0
by = Counter()
for line in open('build/corpus_analyses.jsonl', encoding='utf-8'):
    d = json.loads(line)
    an = [Analysis('', r, t, raz, w) for r, t, raz, w in d['a']]
    best = A.rank(an)[0]
    pos = best.tags.get('POS', 'V')
    cl = any(k in best.tags for k in ('Cl', 'Rel', 'Prep', 'Encl', 'Cop')) or 'Art' in best.tags and pos != 'PREP'
    by[pos + ('+clitic' if cl else '')] += d['c']
    cov += d['c']
# total corpus tokens (all types, not only the analysed ones)
TOTAL = 10949380
print(f'tokens covered by the lexicon: {cov:,} / {TOTAL:,} = {100 * cov / TOTAL:.1f}%')
for k, v in by.most_common():
    print(f'  {k:16s} {v:10,d}  {100 * v / TOTAL:5.1f}%')
if '--json' in sys.argv:
    json.dump(dict(total=TOTAL, covered=cov, by=dict(by)), open('build/coverage_all.json', 'w'), indent=1)
