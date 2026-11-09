#!/usr/bin/env python3
"""Evaluate tigmorph against the Raz gold standard.

For every gold form in scope, check that the expected analysis (root, Type, Deriv, TAM, Subj,
Neg, Colloq, Obj) is among the analyzer's outputs:
  latin  - input in Raz transcription (tests morphology alone)
  geez   - input in Ge'ez (morphology + orthography: the real task)
  guess  - Ge'ez input with the guesser forced (root treated as unknown)
Also reports the rank of the correct analysis in Ge'ez mode.
Usage: python3 -I tools/eval_gold.py [strong|all] [--fails N] [--json out.json]
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from collections import Counter, defaultdict
from tigmorph.gold import parse
from tigmorph.analyzer import Analyzer
from tigmorph.paradigm import SUBJ_TAG
from tigmorph.fidel import LARYNGALS

TAM = {'perf': 'Perf', 'impf': 'Impf', 'juss': 'Jus', 'imp': 'Imp'}


def in_scope(f, scope):
    root = f.root.split('-')
    if scope == 'strong':
        return not f.obj and f.cls != 'irregular' and not any(c in LARYNGALS or c in 'wy' for c in root)
    if scope == 'noobj':
        return not f.obj
    if scope == 'obj':
        return bool(f.obj)
    if scope == 'weak':
        return not f.obj and (f.cls == 'irregular' or any(c in LARYNGALS or c in 'wy' for c in root))
    return True


def expected(f):
    e = dict(Type=f.type, Deriv='Base' if f.deriv == 'base' else f.deriv, TAM=TAM[f.tense], Subj=SUBJ_TAG[f.person])
    if f.obj:
        e['Obj'] = SUBJ_TAG[f.obj]
    if f.neg:
        e['Neg'] = 'Yes'
    if f.colloq:
        e['Colloq'] = 'Yes'
    return e


def match(a, f, e):
    if e.get('Deriv') == 'tə' and e.get('Type') in ('A', 'B') and a.tags.get('Type') in ('A', 'B'):
        e = dict(e, Type=a.tags['Type'])          # tə-A and tə-B are formally identical (§ 5.3.5.1)
    return a.root_latin == f.root and all(a.tags.get(k) == v for k, v in e.items()) and \
        all(k in e for k in ('Obj', 'Neg', 'Colloq') if a.tags.get(k))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scope', nargs='?', default='strong')
    ap.add_argument('--fails', type=int, default=40)
    ap.add_argument('--json')
    ap.add_argument('--noguess', action='store_true')
    args = ap.parse_args()
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    F, C, _ = parse('data/gold/raz_ch5.gold')
    A = Analyzer()
    res = defaultdict(Counter)
    ranks = Counter()
    fails = []
    per_sec = defaultdict(Counter)
    for f in F:
        if not in_scope(f, args.scope):
            continue
        e = expected(f)
        sec = '.'.join(f.sec.split('.')[:2])
        lat = A.analyze_latin(f.form, guess=False)
        ok_l = any(match(a, f, e) for a in lat)
        gz = A.analyze(f.fidel, guess=False)
        hit = [i for i, a in enumerate(gz) if match(a, f, e)]
        ok_g = bool(hit)
        ok_q = None
        if not args.noguess:
            gq = A.analyze(f.fidel, guess='only', n=400)
            ok_q = any(match(a, f, e) for a in gq)
        for mode, ok in (('latin', ok_l), ('geez', ok_g), ('guess', ok_q)):
            if ok is not None:
                res[mode][ok] += 1
                per_sec[sec][(mode, ok)] += 1
        if ok_g:
            r = hit[0] + 1
            ranks['1' if r == 1 else ('2-3' if r <= 3 else '4+')] += 1
        if not (ok_l and ok_g):
            fails.append(dict(sec=f.sec, lemma=f.lemma, form=f.form, fidel=f.fidel, tense=f.tense, person=f.person,
                              obj=f.obj, latin=ok_l, geez=ok_g,
                              got=[str(a) for a in (gz or lat)[:3]]))
    # ---- compounds (§ 5.11): first element + light verb, analysed as one verb
    if args.scope in ('all', 'cmp'):
        from tigmorph.fidel import latin_to_fidel
        from tigmorph.analyzer import LIGHT
        lv_form = {'bela': 'ቤለ', 'ʼabala': 'አበለ', 'ʼattabala': 'አተበለ', 'wada': 'ወደ', 'gaʼa': 'ገአ'}
        lv_root = {v: k for k, v in LIGHT.items()}
        for c in C:
            if 'first' in c:
                first = ' '.join(latin_to_fidel(x) for x in c['first'].split())
                text = first + ' ' + lv_form[c['verb']]
                root, deriv = lv_root[c['verb']]
                an = A.analyze(text)
                ok = any(a.tags.get('Cmp') == first and a.root_latin == root and a.tags.get('Deriv') == deriv
                         and a.gloss for a in an)
            else:
                text = ' '.join(latin_to_fidel(x) for x in c['form'].split())
                an = A.analyze(text)
                tam, rest = c['slot'].replace('neg.', '').split('.', 1)
                subj, _, obj = rest.partition('>')
                want = dict(TAM=TAM[tam], Subj=SUBJ_TAG[subj], Obj=SUBJ_TAG[obj] if obj else None)
                ok = any(all(a.tags.get(k) == v for k, v in want.items() if v) and a.tags.get('Cmp') for a in an)
            res['compound'][ok] += 1
            if not ok:
                fails.append(dict(sec='5.11', lemma=c.get('verb', c.get('parts')), form=text, fidel=text, tense='',
                                  person='', obj='', latin=False, geez=False, got=[str(a) for a in an[:2]]))
    tot = sum(res['geez'].values())
    print(f"scope={args.scope}  forms={tot}")
    for m in ('latin', 'geez', 'guess', 'compound'):
        n = sum(res[m].values())
        if n:
            print(f"  {m:6s} {res[m][True]}/{n} = {100 * res[m][True] / n:.1f}%")
    print('  rank of correct analysis (geez):', dict(ranks))
    for s in sorted(per_sec, key=lambda x: [int(p) for p in x.split('.')]):
        c = per_sec[s]
        print(f"  § {s:5s} latin {c[('latin', True)]}/{c[('latin', True)] + c[('latin', False)]}  "
              f"geez {c[('geez', True)]}/{c[('geez', True)] + c[('geez', False)]}  "
              f"guess {c[('guess', True)]}/{c[('guess', True)] + c[('guess', False)]}")
    for x in fails[:args.fails]:
        print('FAIL', x['sec'], x['lemma'], x['tense'], x['person'], x['obj'], x['form'], x['fidel'],
              'L' if x['latin'] else '-', 'G' if x['geez'] else '-', x['got'][:2])
    if args.json:
        json.dump(dict(res={m: dict(c) for m, c in res.items()}, ranks=ranks, fails=fails,
                       per_sec={s: {f'{m}_{o}': v for (m, o), v in c.items()} for s, c in per_sec.items()}),
                  open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)


if __name__ == '__main__':
    main()
