#!/usr/bin/env python3
"""Fast check of the paradigm generator against the gold standard (no FST).
Usage: python3 -I tools/check_paradigms.py [strong|all] [max_fails]"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from collections import Counter
from tigmorph.gold import parse
from tigmorph.paradigm import cells, realize, SUBJ_TAG, SHAPES, TYPES, DERIVS, irregular_cells
from tigmorph.fst import CLASSES
from tigmorph.fidel import LARYNGALS

TAM = {'perf': 'Perf', 'impf': 'Impf', 'juss': 'Jus', 'imp': 'Imp'}


def shapes_for(root):
    out = []
    for sh in SHAPES[len(root)]:
        ok = True
        for c, cl in zip(root, sh):
            if c not in [u for u, _ in CLASSES[cl]]:
                ok = False; break
        if ok:
            out.append(sh)
    return out


def generate_all(root, typ, deriv):
    """{(TAM, Subj, Neg, Colloq): set(forms)} for a root over all compatible shapes."""
    res = {}
    for sh in shapes_for(root):
        for c in cells(len(root), typ, deriv, sh):
            cons_ok = True
            for s, cl in c.constraints.items():
                if cl == 'DENT' and root[s - 1] not in [u for u, _ in CLASSES['DENT']]:
                    cons_ok = False
                if cl == 'GLOT' and root[s - 1] != 'ʼ':
                    cons_ok = False
                if cl == 'SAME2' and root[s - 1] != root[1]:
                    cons_ok = False
            if not cons_ok:
                continue
            k = (c.tags['TAM'], c.tags['Subj'], c.tags.get('Neg', ''), c.tags.get('Colloq', ''), c.tags.get('Obj', ''))
            form = realize(c.template, root, sh)
            res.setdefault(k, set()).add(form)
            if 'mb' in form:
                res[k].add(form.replace('mb', 'nb'))          # optional m/n before b (FST rule)
    for r, c in irregular_cells():
        if r.split('-') == root and c.tags['Type'] == typ and c.tags['Deriv'] == deriv:
            k = (c.tags['TAM'], c.tags['Subj'], c.tags.get('Neg', ''), c.tags.get('Colloq', ''), c.tags.get('Obj', ''))
            res.setdefault(k, set()).add(c.template)
    return res


def strong(root):
    return not any(c in LARYNGALS or c in 'wy' for c in root)


def main(scope='all', maxf='300'):
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    F, _, _ = parse('data/gold/raz_ch5.gold')
    cache = {}
    res = Counter(); fails = []
    for f in F:
        root = f.root.split('-')
        if (scope == 'strong' and (f.obj or not strong(root))) or (scope == 'noobj' and f.obj) or (scope == 'obj' and not f.obj):
            continue
        typs = {f.type} | ({'A', 'B'} if f.deriv == 'tə' and f.type in 'AB' else set())
        deriv = 'Base' if f.deriv == 'base' else f.deriv
        want = (TAM[f.tense], SUBJ_TAG[f.person], 'Yes' if f.neg else '', 'Yes' if f.colloq else '',
                SUBJ_TAG[f.obj] if f.obj else '')
        got = set()
        for t in typs:
            key = (tuple(root), t, deriv)
            if key not in cache:
                cache[key] = generate_all(root, t, deriv)
            got |= cache[key].get(want, set())
        ok = f.form in got
        sec = '.'.join(f.sec.split('.')[:2])
        res[(sec, ok)] += 1
        if not ok:
            fails.append((f.sec, f.lemma, f.root, f.type, deriv, f.tense, f.person, f.form, sorted(got)[:4]))
    tot = sum(res.values()); ok = sum(v for (s, o), v in res.items() if o)
    print(f'{ok}/{tot} gold forms generated')
    for s in sorted({s for s, _ in res}, key=lambda x: [int(p) for p in x.split('.')]):
        print(f'  § {s}: {res[(s, True)]}/{res[(s, True)] + res[(s, False)]}')
    for x in fails[:int(maxf)]:
        print('FAIL', *x)


if __name__ == '__main__':
    main(*sys.argv[1:])
