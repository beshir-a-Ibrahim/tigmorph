#!/usr/bin/env python3
"""Deverbal nominals (data/gold/raz_nominal.gold) and Raz Ch. 2 nouns (data/lexicon/raz_nouns.tsv: singular,
plural and listed possessive forms), Ge'ez input. found = an analysis matches; top1 = the first one does.
Deverbal forms are checked with the guesser on (roots outside the lexicon are reached through it)."""
import sys, os, csv, json
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs('build', exist_ok=True)
sys.path.insert(0, '.')
from tigmorph.analyzer import Analyzer
from tigmorph.fidel import latin_to_fidel


def nominal_gold():
    for line in open('data/gold/raz_nominal.gold', encoding='utf-8'):
        if line.startswith('#') or not line.strip():
            continue
        yield line.rstrip('\n').split('\t')


def noun_gold():
    for r in csv.DictReader(open('data/lexicon/raz_nouns.tsv', encoding='utf-8'), delimiter='\t'):
        yield r['latin'], r['latin'], {}
        for pl in filter(None, r['pl'].split(';')):
            yield pl, r['latin'], {'Number': 'Pl'}
        for f in filter(None, r['forms'].split(';')):
            form, cell = f.split(':')
            yield form, r['latin'], {'Poss': cell}


def main():
    A = Analyzer()
    res = {}
    miss = []
    n = f = t = 0
    tn = 0
    for form, root, typ, der, tam, gn, src in nominal_gold():
        an = A.analyze(latin_to_fidel(form), guess=True, n=40)
        hit = [i for i, a in enumerate(an) if a.root_latin == root and a.tags.get('TAM') == tam
               and a.tags.get('Subj', '')[1:] == gn and a.tags.get('Type') == typ and a.tags.get('Deriv') == der]
        n += 1; f += bool(hit); t += bool(hit) and hit[0] == 0
        tn += bool(an) and (an[0].tags.get('TAM') in ('PartAct', 'PartPass', 'Agent', 'Inf', 'Instr') or
                            an[0].tags.get('POS') in ('NOUN', 'ADJ'))
        if not hit:
            miss.append(('nominal', form, root, typ, der, tam, gn, str(an[0])[:70] if an else '-'))
    res['deverbal'] = (n, f, t)
    res['deverbal_top1_nominal'] = tn
    n = f = t = 0
    for form, lemma, feats in noun_gold():
        an = A.analyze(latin_to_fidel(form), n=40)
        hit = [i for i, a in enumerate(an) if a.root_latin == lemma and all(a.tags.get(k) == v for k, v in feats.items())]
        n += 1; f += bool(hit); t += bool(hit) and hit[0] == 0
        if not hit:
            miss.append(('noun', form, lemma, feats, str(an[0])[:70] if an else '-'))
    res['nouns'] = (n, f, t)
    print(f"deverbal: best reading is a nominal (this participle or a dictionary noun/adjective of the same word): "
          f"{tn}/{res['deverbal'][0]}")
    for k, v in res.items():
        if not isinstance(v, tuple):
            continue
        n, f, t = v
        print(f'{k:9s} {n:4d} forms   found {f}/{n} = {100 * f / n:.1f}%   top-1 {t}/{n} = {100 * t / n:.1f}%')
    if '-v' in sys.argv:
        for m in miss:
            print('  ', m)
    json.dump(dict(res=res, miss=[list(map(str, m)) for m in miss]), open('build/eval_nominal.json', 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
