#!/usr/bin/env python3
"""Evaluate closed-class words and clitics against data/gold/raz_closed.gold (Ge'ez input).
found = some analysis has the gold lemma, POS and features; top1 = the first analysis does.
Usage: python3 tools/eval_closed.py [-v] [--json]"""
import sys, os, json
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs('build', exist_ok=True)
sys.path.insert(0, '.')
from tigmorph.analyzer import Analyzer
from tigmorph.fidel import latin_to_fidel


def load(path='data/gold/raz_closed.gold'):
    out = []
    for line in open(path, encoding='utf-8'):
        if line.startswith('#') or not line.strip():
            continue
        form, lemma, pos, feats, src = line.rstrip('\n').split('\t')
        f = {} if feats == '_' else dict(kv.split('=') for kv in feats.split(','))
        out.append((form, lemma, pos, f, src))
    return out


def ok(a, lemma, pos, f):
    return a.root_latin == lemma and a.tags.get('POS') == pos and all(a.tags.get(k) == v for k, v in f.items())


def main():
    A = Analyzer()
    gold = load()
    found = top1 = 0
    misses = []
    for form, lemma, pos, f, src in gold:
        g = latin_to_fidel(form)
        an = A.analyze(g, n=30)
        hit = [i for i, a in enumerate(an) if ok(a, lemma, pos, f)]
        found += bool(hit)
        top1 += bool(hit) and hit[0] == 0
        if not hit or hit[0] != 0:
            misses.append((form, g, lemma, pos, f, src, str(an[0]) if an else '-', hit[0] if hit else None))
    n = len(gold)
    print(f'closed-class gold: {n} forms   found {found}/{n} = {100 * found / n:.1f}%   top-1 {top1}/{n} = {100 * top1 / n:.1f}%')
    if '-v' in sys.argv:
        for m in misses:
            print('  ', m)
    if '--json' in sys.argv:
        json.dump(dict(n=n, found=found, top1=top1, misses=[list(map(str, m)) for m in misses]),
                  open('build/eval_closed.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
