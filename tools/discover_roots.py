#!/usr/bin/env python3
"""Phase 2: propose new verb roots from guesser output (build/corpus_guesses.jsonl).

A root is proposed only if it is attested in several *distinctly verbal* forms: perfect with a
subject suffix other than 3m.sg, prefixed imperfect/jussive, negated or object-bearing forms.
Bare shapes (imperative 2m.sg, 3m.sg perfect, prefixless imperfect) are not counted: nouns and
adjectives take those shapes too.  Competing parses of the same words are left to EM later.
A root must also show >= MIN_CORE subject-suffixed perfects (no object) and >= MIN_CORE prefixed
imperfect/jussive cells, so that suffixed nouns and prepositions are not taken for verbs.
Output: build/root_candidates.tsv"""
import json, csv, os, sys
from collections import defaultdict
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs('build', exist_ok=True)
MIN_CORE = 2
MIN_CELLS, MIN_TOKENS, MIN_FORMS = int(sys.argv[1]) if len(sys.argv) > 1 else 4, 20, 4


def marked(t):
    if t.get('Neg') or t.get('Obj'):
        return True
    if t.get('Colloq'):
        return False
    if t['TAM'] == 'Perf':
        return t['Subj'] != '3SgM'
    if t['TAM'] in ('Impf', 'Jus'):
        return True
    return t['Subj'] != '2SgM'                    # imperative with a suffix


sys.path.insert(0, '.')
from tigmorph.analyzer import Analyzer
A = Analyzer(); A.ranker = None
CLITICS = ('ለ', 'ወ', 'ከ', 'በ')        # relative la-, wa- 'and', kə-/bə- prepositions (Phase 3 clitics)
clitic_skipped = 0


def clitic_artifact(w):
    """True if the word is just a clitic + a form we already analyse (ለዐለት = la + ዐለት)."""
    return len(w) > 2 and w[0] in CLITICS and bool(A.analyze(w[1:], guess=False, n=1))


stats = defaultdict(lambda: dict(cells=set(), forms={}, tokens=0.0, marked_tokens=0.0, perf=set(), pref=set()))
for line in open('build/corpus_guesses.jsonl', encoding='utf-8'):
    d = json.loads(line)
    if clitic_artifact(d['w']):
        clitic_skipped += 1
        continue
    best = min(a[3] for a in d['a'])
    an = [a for a in d['a'] if a[3] <= best + 1.0]           # only near-best guesses
    share = d['c'] / len(an)
    for root, tags, raz, w in an:
        k = (root, tags['Type'], tags['Deriv'])
        s = stats[k]
        s['tokens'] += share
        if tags['TAM'] == 'Perf' and not tags.get('Obj') and tags['Subj'] != '3SgM':
            s['perf'].add(tags['Subj'])
        if tags['TAM'] in ('Impf', 'Jus') and not tags.get('Colloq'):
            s['pref'].add(tags['TAM'] + tags['Subj'])
        if marked(tags):
            cell = '|'.join(tags.get(x, '') for x in ('TAM', 'Subj', 'Obj', 'Neg'))
            s['cells'].add(cell)
            s['marked_tokens'] += share
            s['forms'][d['w']] = d['c']
rows = []
for (root, typ, der), s in stats.items():
    # nouns, adjectives, pronouns and prepositions with possessive suffixes (ህቶም, ዲቦም, አፉከ) look like
    # verbs with object suffixes; demand subject-inflected perfects AND person-prefixed imperfect/jussive
    if len(s['perf']) < MIN_CORE or len(s['pref']) < MIN_CORE:
        continue
    if len(s['cells']) >= MIN_CELLS and s['marked_tokens'] >= MIN_TOKENS and len(s['forms']) >= MIN_FORMS:
        ex = sorted(s['forms'].items(), key=lambda x: -x[1])[:6]
        rows.append(dict(root_latin=root, type=typ, deriv=der, cells=len(s['cells']), forms=len(s['forms']),
                         marked_tokens=round(s['marked_tokens'], 1), tokens=round(s['tokens'], 1),
                         examples=' '.join(f'{w}({c})' for w, c in ex)))
rows.sort(key=lambda r: (-r['cells'], -r['marked_tokens']))
with open('build/root_candidates.tsv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, list(rows[0]), delimiter='\t'); w.writeheader(); w.writerows(rows)
print('clitic artifacts skipped', clitic_skipped)
print('candidate stems', len(rows), 'roots', len({r['root_latin'] for r in rows}))
for r in rows[:25]:
    print(r['root_latin'], r['type'], r['deriv'], r['cells'], r['forms'], r['marked_tokens'], r['examples'][:70])
