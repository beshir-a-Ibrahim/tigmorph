#!/usr/bin/env python3
"""Run the guesser over corpus word types that have no known-root analysis (Phase 2 root discovery).
Output: build/corpus_guesses.jsonl"""
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
A = Analyzer(); A.ranker = None
t = time.time(); n = 0
with open('build/corpus_guesses.jsonl', 'w', encoding='utf-8') as out:
    for w, c in cnt.most_common(top):
        if c < 2 or A.analyze(w, guess=False, n=5):
            continue
        an = A.analyze(w, guess='only', n=40)
        if an:
            n += 1
            out.write(json.dumps(dict(w=w, c=c, a=[[a.root_latin, a.tags, a.raz, round(a.weight, 3)] for a in an]),
                                 ensure_ascii=False) + '\n')
print('guessed types', n, 'time', round(time.time() - t))
