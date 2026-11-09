#!/usr/bin/env python3
"""Share of corpus tokens that receive a verb analysis (known root / guesser).
Usage: python3 -I tools/corpus_coverage.py [top_types]"""
import sys, os, re, glob, json
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tigmorph.analyzer import Analyzer, normalize_geez
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs('build', exist_ok=True)
top = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
cnt = Counter()
for p in glob.glob('data/corpus/*.txt'):
    cnt.update(re.findall(r'[ሀ-፿]+', open(p, encoding='utf-8').read()))
A = Analyzer()
tot = sum(cnt.values()); known = guess = 0; seen = 0
examples = []
for w, c in cnt.most_common(top):
    seen += c
    r = A.analyze(w, guess=False, n=5)
    if r:
        known += c
        if len(examples) < 40:
            examples.append((w, c, str(r[0])))
    elif A.analyze(w, guess='only', n=3):
        guess += c
print(f'tokens {tot:,}; top {top:,} types cover {seen:,} tokens')
print(f'known-root verb analysis: {known:,} ({100 * known / seen:.1f}% of covered tokens)')
print(f'guesser only:            {guess:,} ({100 * guess / seen:.1f}%)')
json.dump(dict(tot=tot, seen=seen, known=known, guess=guess, examples=examples),
          open('build/corpus_coverage.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for e in examples[:25]:
    print(*e)
