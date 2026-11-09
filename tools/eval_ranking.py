#!/usr/bin/env python3
"""Corpus-weighted ranking accuracy on Raz's verbs.
For every gold Ge'ez spelling that occurs in the corpus, the correct readings are all gold analyses
with that spelling.  Top-1 accuracy is weighted by corpus frequency (how often a reader meets it).
Usage: python3 tools/eval_ranking.py [lam ...]"""
import sys, os, re, glob, json
from collections import Counter, defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs('build', exist_ok=True)
from tigmorph.gold import parse
from tigmorph.analyzer import Analyzer, normalize_geez
from eval_gold import expected, match

F, _, _ = parse('data/gold/raz_ch5.gold')
cnt = Counter()
for p in glob.glob('data/corpus/*.txt'):
    for w in re.findall(r'[ሀ-፿]+', open(p, encoding='utf-8').read()):
        cnt[normalize_geez(w)] += 1
by_form = defaultdict(list)
for f in F:
    by_form[normalize_geez(f.fidel)].append(f)
forms = [(w, fs) for w, fs in by_form.items() if cnt[w] > 0]
A = Analyzer()
model = A.ranker
lams = [float(x) for x in sys.argv[1:]] or [None]
res = {}
for lam in ['grammar'] + lams:
    if lam == 'grammar':
        A.ranker = None
    else:
        A.ranker = dict(model, lam=lam if lam is not None else model['lam'])
    tok = ok_tok = typ = ok_typ = 0
    for w, fs in forms:
        an = A.analyze(w, guess=False)
        top = an[:1]
        ok = any(match(a, f, expected(f)) for a in top for f in fs)
        tok += cnt[w]; ok_tok += cnt[w] * ok; typ += 1; ok_typ += ok
    res[str(lam)] = dict(types=typ, tokens=tok, top1_tokens=ok_tok / tok, top1_types=ok_typ / typ)
    print(f'{str(lam):8s} types={typ} tokens={tok}  top-1 by tokens {100 * ok_tok / tok:.1f}%   by types {100 * ok_typ / typ:.1f}%')
A.ranker = model
json.dump(res, open('build/eval_ranking.json', 'w'), indent=1)
