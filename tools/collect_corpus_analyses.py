#!/usr/bin/env python3
"""Analyse the most frequent corpus word types once and cache the results (for ranking training).
Usage: python3 tools/collect_corpus_analyses.py [top_types] -> build/corpus_analyses.jsonl"""
import sys, os, re, glob, json, time
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tigmorph.analyzer import Analyzer, normalize_geez
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs('build', exist_ok=True)
top = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
cnt = Counter()
for p in glob.glob('data/corpus/*.txt'):
    for w in re.findall(r'[ሀ-፿]+', open(p, encoding='utf-8').read()):
        cnt[normalize_geez(w)] += 1
cnt.pop('', None)
A = Analyzer()
t = time.time()
with open('build/corpus_analyses.jsonl', 'w', encoding='utf-8') as out:
    for i, (w, c) in enumerate(cnt.most_common(top)):
        an = A.candidates(w, n=30)          # grammar weights only, no corpus ranking (avoids feedback)
        if not an:
            continue
        out.write(json.dumps(dict(w=w, c=c, a=[[a.root_latin, a.tags, a.raz, round(a.grammar_weight, 3)] for a in an]),
                             ensure_ascii=False) + '\n')
print('types', len(cnt), 'tokens', sum(cnt.values()), 'time', round(time.time() - t))
