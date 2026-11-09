#!/usr/bin/env python3
"""Phase 2: turn build/root_candidates.tsv into lexicon rows (data/lexicon/extra/corpus_roots.tsv).

Rules
  * evidence: >= MIN_CELLS distinct marked paradigm cells, >= MIN_FORMS word forms, >= MIN_TOK marked tokens
  * drop (root, type, deriv) already in the lexicon
  * drop clitic artifacts: 4/5-radical roots starting l-/w-/k-/b- whose remainder is a known or candidate root
  * drop 4/5-radical roots with identical final radicals (object/laryngal artifacts: s-m-ʿ-ʿ)
  * readings with the *same* attested forms cannot be told apart in writing (B vs C, w vs y): keep them
    all, the first as 'candidate', the rest as 'candidate-alt' (heavier weight)
  * a stem that is only attested in forms that are a subset of a stronger candidate's forms is dropped
Also writes build/candidates_review.tsv for a human check (one line per root)."""
import csv, os, sys
from collections import defaultdict
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs('build', exist_ok=True)
sys.path.insert(0, '.')
from tigmorph.build import lexicon_rows
from tigmorph.fidel import latin_to_fidel

MIN_CELLS, MIN_FORMS, MIN_TOK = 6, 5, 25
known = {(r['root_latin'], r['type'], 'Base' if r['deriv'] == 'base' else r['deriv'])
         for r in lexicon_rows() if 'corpus_roots' not in r.get('source', '')}
known_roots = {k[0] for k in known}
cands = [r for r in csv.DictReader(open('build/root_candidates.tsv', encoding='utf-8'), delimiter='\t')
         if int(r['cells']) >= MIN_CELLS and int(r['forms']) >= MIN_FORMS and float(r['marked_tokens']) >= MIN_TOK]
cand_roots = {r['root_latin'] for r in cands}


def forms(r):
    return frozenset(x.rsplit('(', 1)[0] for x in r['examples'].split())


NOT_VERBS = {r['root_latin'] for r in csv.DictReader(open('data/lexicon/not_verbs.tsv', encoding='utf-8'), delimiter='\t')}


def artifact(root):
    """Clitic / prefix / suffix artifacts of a root we already have, and known non-verbs."""
    rad = root.split('-')
    if root in NOT_VERBS:
        return True
    if len(rad) >= 4 and rad[-1] == rad[-2]:
        return True
    have = lambda r: r in known_roots or r in cand_roots
    if len(rad) >= 4 and rad[0] in ('l', 'w', 'k', 'b', 'ʼ', 't') and have('-'.join(rad[1:])):
        return True                                   # la-/wa- clitics, ʼa-written, ʼasta- t
    if len(rad) >= 4 and rad[-1] in ('w', 'y') and have('-'.join(rad[:-1])):
        return True                                   # 3pl.f -aya / 3pl.m -aw read as a final semivowel
    return False


drop = defaultdict(int)
kept = []
for r in cands:
    key = (r['root_latin'], r['type'], r['deriv'])
    if key in known:
        drop['known'] += 1
    elif artifact(r['root_latin']):
        drop['clitic/artifact'] += 1
    else:
        kept.append(r)
# subset rule: a stem whose example forms are all claimed by a stronger stem of another root is dropped
kept.sort(key=lambda r: (-int(r['cells']), -float(r['marked_tokens'])))
final, groups = [], {}
for r in kept:
    fs = forms(r)
    owner = next((g for g in groups if fs == groups[g]['fs']), None)
    if owner is not None:                                        # indistinguishable alternative
        groups[owner]['alts'].append(r); continue
    if any(fs < g['fs'] and g['root'] != r['root_latin'] for g in groups.values()):
        drop['subset'] += 1; continue
    groups[len(groups)] = dict(fs=fs, root=r['root_latin'], main=r, alts=[])
REVIEWED = {r['root_latin'] for r in csv.DictReader(open('data/lexicon/reviewed_roots.tsv', encoding='utf-8'), delimiter='\t')
            if r['verdict'] == 'verb'}
rows = []
for g in groups.values():
    for i, r in enumerate([g['main']] + g['alts']):
        rad = r['root_latin'].split('-')
        rows.append(dict(root='-'.join(latin_to_fidel(x + 'ə') for x in rad), root_latin=r['root_latin'],
                         n_rad=len(rad), type=r['type'], deriv='base' if r['deriv'] == 'Base' else r['deriv'],
                         cls='', citation='', gloss='',
                         certainty=('reviewed' if r['root_latin'] in REVIEWED else 'candidate') if i == 0 else 'candidate-alt', source='corpus_roots',
                         lh_id=f"cells={r['cells']};forms={r['forms']};tok={r['marked_tokens']}"))
F = ['root', 'root_latin', 'n_rad', 'type', 'deriv', 'cls', 'citation', 'gloss', 'certainty', 'source', 'lh_id']
with open('data/lexicon/extra/corpus_roots.tsv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, F, delimiter='\t'); w.writeheader(); w.writerows(rows)
with open('build/candidates_review.tsv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['root', 'root_latin', 'readings', 'cells', 'forms', 'marked_tokens', 'examples', 'verdict (ok / wrong / type)'])
    for g in groups.values():
        m = g['main']
        rd = ', '.join(f"{r['type']}/{r['deriv']}" for r in [m] + g['alts'])
        w.writerow(['-'.join(latin_to_fidel(x + 'ə') for x in m['root_latin'].split('-')), m['root_latin'], rd,
                    m['cells'], m['forms'], m['marked_tokens'], m['examples'], ''])
print('kept stems', len(rows), 'groups', len(groups), 'roots', len({r['root_latin'] for r in rows}), dict(drop))
