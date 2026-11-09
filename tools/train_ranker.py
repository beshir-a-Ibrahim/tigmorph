#!/usr/bin/env python3
"""Learn ranking priors from raw corpus text with EM (no annotated data needed).

Each analysis a of a word gets   score(a) = λ·w(a) − log P(stem) − log P(cell)
  w(a)   : grammar cost from the FST (spelling variants, unlisted type/derivation, …)
  stem   : (root, Type, Deriv), or (lemma, POS) for closed-class words
  cell   : (TAM, Subj, Obj, Neg, Colloq) or (POS, Poss, Art, Dem, Neg), plus clitics (wa-/ka-, la-, -ma)
Word types are weighted by log(1 + frequency) so that very frequent function words that happen to
look like verbs (እንዴ, ምነ) cannot dominate the statistics.
Output: tigmorph/fst/ranker.json
"""
import json, math, sys, os
from collections import defaultdict
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs('build', exist_ok=True)
LAM, BETA, ALPHA, ITERS = 1.0, 2.0, 2.0, 10


sys.path.insert(0, '.')
from tigmorph.analyzer import rank_keys


def keys(a):
    root, tags, raz, w = a
    stem, td, cell = rank_keys(root, tags)
    return stem, td, cell, w


data = []
for line in open('build/corpus_analyses.jsonl', encoding='utf-8'):
    d = json.loads(line)
    data.append((math.log1p(d['c']), [keys(a) for a in d['a']]))   # damped: frequent function words must not dominate
print('word types', len(data), 'tokens', sum(c for c, _ in data))

stem_c, td_c, cell_c = defaultdict(float), defaultdict(float), defaultdict(float)
pi = 0.5
for c, an in data:                                   # initialise from grammar costs only
    z = sum(math.exp(-LAM * w) for _, _, _, w in an)
    for s, t, ce, w in an:
        p = c * math.exp(-LAM * w) / z
        stem_c[s] += p; td_c[t] += p; cell_c[ce] += p

for it in range(ITERS):
    N_td = sum(td_c.values()); N_stem = sum(stem_c.values()); N_cell = sum(cell_c.values())
    P_td = {k: v / N_td for k, v in td_c.items()}
    n_cells = len(cell_c)
    lp_stem = lambda s, t: math.log((stem_c.get(s, 0) + BETA * P_td.get(t, 1e-6)) / (N_stem + BETA))
    lp_cell = lambda ce: math.log((cell_c.get(ce, 0) + ALPHA) / (N_cell + ALPHA * n_cells))
    new_s, new_t, new_c = defaultdict(float), defaultdict(float), defaultdict(float)
    nv, ll, tot = 0.0, 0.0, 0.0
    for c, an in data:
        scores = [lp_stem(s, t) + lp_cell(ce) - LAM * w for s, t, ce, w in an]
        m = max(scores)
        zv = sum(math.exp(x - m) for x in scores) * (1 - pi)
        zn = 0.0                       # NONVERB option disabled: it collapses under EM without labelled data
        Z = zv + zn
        ll += c * (m + math.log(Z)); tot += c
        nv += c * zn / Z
        for (s, t, ce, w), x in zip(an, scores):
            p = c * (1 - pi) * math.exp(x - m) / Z
            new_s[s] += p; new_t[t] += p; new_c[ce] += p
    stem_c, td_c, cell_c = new_s, new_t, new_c
    pi = nv / tot
    print(f'iter {it + 1:2d}  loglik/token {ll / tot:.4f}  P(nonverb) {pi:.3f}')

N_td = sum(td_c.values()); N_stem = sum(stem_c.values()); N_cell = sum(cell_c.values())
model = dict(lam=2.0,   # λ at run time: chosen on corpus-weighted gold accuracy (tools/eval_ranking.py)
              beta=BETA, alpha=ALPHA, n_stem=N_stem, n_cell=N_cell, n_cells=len(cell_c),
             td={k: v / N_td for k, v in td_c.items()},
             stem={k: round(v, 3) for k, v in stem_c.items() if v >= 0.05},
             cell={k: round(v, 3) for k, v in cell_c.items()})
json.dump(model, open('tigmorph/fst/ranker.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('stems', len(model['stem']), 'cells', len(model['cell']))
top = sorted(cell_c.items(), key=lambda x: -x[1])[:15]
for k, v in top:
    print(f'  {v / N_cell:.3f}  {k}')
