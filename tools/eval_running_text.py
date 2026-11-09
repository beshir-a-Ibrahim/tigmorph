#!/usr/bin/env python3
"""Running-text accuracy without a human annotator, from Raz's own example sentences.

Raz writes his 473 example sentences (5,275 words, chapters 2-4 and 6-9) in a transcription that shows what
Ge'ez spelling hides: vowel length, ə, gemination, the clitics. Each word is converted to Ge'ez, analysed by
tigmorph, and the transcription implied by tigmorph's reading is compared with Raz's. A reading that reproduces
Raz's exact pronunciation has the right stem, the right inflection class and (with one exception, below) the right
cell. The best reading is "consistent" if it does; a word counts as "found" if any of the 10 best does.

Readings whose transcription cannot be derived (nouns that come from the Ge'ez-only Wiktionary list) are
reported apart, as "not checkable".
Identical transcriptions with different features (e.g. 2m.sg. and 3f.sg. imperfect, both təqattəl) cannot be told
apart this way, so this measures "right word, right pronunciation", a little above full feature accuracy.
The sentence file is not distributed (it is text from Raz's thesis). Build it from your copy of the thesis with
    python3 tools/extract_raz_sentences.py THESIS.docx data/gold/raz_sentences.json
Usage: python3 tools/eval_running_text.py [-v] [SENTENCES.json]"""
import sys, os, json, re
from collections import Counter
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs('build', exist_ok=True)
sys.path.insert(0, '.')
from tigmorph.analyzer import Analyzer
from tigmorph.fidel import latin_to_fidel

A = Analyzer()
_args = [a for a in sys.argv[1:] if not a.startswith('-')]
sents = json.load(open(_args[0] if _args else 'data/gold/raz_sentences.json', encoding='utf-8'))


def surface(a):
    """Raz transcription implied by a reading, or None if it cannot be derived."""
    r = a.raz
    if any('\u1200' <= ch <= '\u137f' for ch in r):
        return None                                # Ge'ez lemma (Wiktionary noun): no transcription
    if '+' in r:
        return None                                # nominal with ending: the form itself is not stored
    if getattr(a, 'src', '') == 'nominal' and any(k in a.tags for k in ('Poss', 'Number', 'Plural')):
        return None                                # Raz noun: the lemma is stored, not the inflected form
    return r.replace('-', '')


def norm(t):
    return t.replace('-', '')


tot = cons = found = unchk = noan = anychk = 0
by = Counter(); byok = Counter()
bad = []
for s in sents:
    for t in s:
        tot += 1
        an = A.analyze(latin_to_fidel(t), n=10)
        if not an:
            noan += 1; bad.append((t, '-')); continue
        surf = [surface(a) for a in an]
        found += any(x == norm(t) for x in surf if x)
        anychk += any(surf)
        if surf[0] is None:
            unchk += 1; continue
        ok = surf[0] == norm(t)
        pos = an[0].tags.get('POS') or ('V>N' if an[0].tags.get('TAM') in ('PartAct', 'PartPass', 'Agent', 'Inf', 'Instr') else 'V')
        by[pos] += 1; byok[pos] += ok
        cons += ok
        if not ok:
            bad.append((t, str(an[0])[:90]))
chk = tot - unchk - noan
print(f'Raz example sentences: {len(sents)} sentences, {tot} words')
print(f'  best reading checkable: {chk} ({100 * chk / tot:.1f}%); not checkable (dictionary noun with ending, or Wiktionary noun): {unchk}; no analysis: {noan}')
print(f'  best reading consistent with Raz: {cons}/{chk} = {100 * cons / chk:.1f}%')
print(f'  analysed at all: {tot - noan}/{tot} = {100 * (tot - noan) / tot:.1f}%')
print(f'  Raz pronunciation among the 10 best (words with a checkable reading): {found}/{anychk} = {100 * found / anychk:.1f}%')
for k, v in by.most_common():
    print(f'    {k:6s} {v:5d}  consistent {100 * byok[k] / v:5.1f}%')
json.dump(dict(words=tot, sentences=len(sents), checkable=chk, consistent=cons, found=found, anychk=anychk, unchecked=unchk,
               none=noan, by={k: [by[k], byok[k]] for k in by}), open('build/eval_running_text.json', 'w'), indent=1)
if '-v' in sys.argv:
    for b in bad[:150]:
        print('  ', b)
