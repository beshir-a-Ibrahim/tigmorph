"""Classify a Raz Latin perfect-3m.sg citation form into root, type, derivational prefix.

Raz's transcription marks gemination and vowel length, so the type is visible:
  A  CaCCa / CaCaCa (laryngal) / CeCa, CoCa (hollow) / CaCa (final SV, doubled CaCCa)
  B  CaCCaCa      C  CāCaCa      D  CaCāCaCa
Prefixes: tə-/ta-, ʼa-, ʼat-, ʼatta-, ʼan-, ʼas-, ʼattan-, ʼattas-.
Context labels from Raz's tables ('type A', 'ʼa-A', 'tə-C', ...) override guesses.
"""
import re, unicodedata

CONS = 'bcdfghjklmnpqrstvwyzčšžǧḥṣṭʼʿ'
LAR = set('ʼʿhḥ')


def toks(w):
    w = unicodedata.normalize('NFC', w)
    out, i = [], 0
    while i < len(w):
        if w[i:i + 2] in ('č̣', 'p̣'):
            out.append(w[i:i + 2]); i += 2
        else:
            out.append(w[i]); i += 1
    return out


def is_c(t):
    return t in CONS or t in ('č̣', 'p̣')


def skeleton(tk):
    """consonant/vowel skeleton with gemination: e.g. qattala -> C a CC a C a"""
    s = []
    for t in tk:
        if is_c(t):
            if s and s[-1][0] == 'C' and s[-1][1] == t:
                s[-1] = ('CC', t)
            else:
                s.append(('C', t))
        else:
            s.append(('V', t))
    return s


PREFIXES = [('ʼattan', 'ʼattan'), ('ʼattas', 'ʼattas'), ('ʼatta', 'ʼatta'), ('ʼat', 'ʼat'),
            ('ʼan', 'ʼan'), ('ʼas', 'ʼas'), ('ʼa', 'ʼa'), ('tə', 'tə'), ('ta', 'tə')]


def classify(form, label=''):
    """Return dict(root, type, deriv, shape, note)."""
    f = form.strip().split('/')[0]
    lab = label.replace('_', '').strip().rstrip(':')
    deriv, typ = None, None
    m = re.match(r'(tə|ʼa|ʼat|ʼatta|ʼan|ʼas|ʼattan|ʼattas)-([ABCD])', lab)
    if m:
        deriv, typ = m.group(1), m.group(2)
    else:
        m = re.match(r'type ([ABCD])', lab, re.I)
        if m:
            deriv, typ = 'base', m.group(1)
    tk = toks(f)
    stem = tk
    if deriv and deriv != 'base':
        p = toks(deriv)
        if tk[:len(p)] == p:
            stem = tk[len(p):]
        elif deriv == 'tə' and tk[:2] == ['t', 'a']:
            stem = tk[2:]
    elif deriv is None:
        deriv = 'base'
        for p, d in PREFIXES:
            pt = toks(p)
            if tk[:len(pt)] != pt:
                continue
            rest = tk[len(pt):]
            # prefix only if what remains still looks like a verb stem ending in -a
            if len(rest) >= 3 and rest[-1] == 'a':
                if d == 'tə' and p == 'ta' and rest[0] not in LAR:
                    continue
                if d in ('ʼa', 'ʼat', 'ʼatta', 'ʼan', 'ʼas', 'ʼattan', 'ʼattas') and (not is_c(rest[0]) or rest[0] == rest[1]):
                    continue
                if d in ('ʼan', 'ʼas', 'ʼattan', 'ʼattas') and sum(1 for t in rest if is_c(t)) < 4:
                    continue
                stem, deriv = rest, d
                break
    sk = skeleton(stem)
    shape = ''.join(('CC' if k == 'CC' else ('C' if k == 'C' else v)) for k, v in sk)
    cons = []
    for k, v in sk:
        if k in ('C', 'CC'):
            cons.append(v)
    note = ''
    # ʼa-A with vowelless R1 (ʼafgara): stem = CCaCa
    if typ is None:
        if shape in ('CaCCa', 'CaCaCa') and not any(k == 'CC' for k, _ in sk):
            typ = 'A' if shape == 'CaCCa' or (len(cons) == 3 and cons[1] in LAR) or cons[0] in LAR else 'A?'
        if shape == 'CCaCa':
            typ = 'A'                           # ʼa-A / ʼat-A: R1 vowelless
        if shape == 'CaCCaCa' and any(k == 'CC' for k, _ in sk):
            typ = 'B'
        if re.fullmatch(r'Cā(C|CC)a(C)?a', shape) or shape == 'CāCaCa':
            typ = 'C'
        if re.fullmatch(r'CaCāCaCa', shape):
            if len(cons) == 4 and cons[1] == cons[2]:
                typ = 'D'; cons = [cons[0], cons[1], cons[3]]
            else:
                typ = 'QC'
        if shape in ('CeCa', 'CoCa', 'CēCa', 'CōCa'):
            typ = 'A'; cons = [cons[0], 'w' if 'o' in shape or 'ō' in shape else 'y', cons[1]]; note = 'hollow / or 4-rad'
        if shape == 'CaCa':
            typ = 'A'; cons = cons + ['y']; note = 'final SV'
        if shape == 'CaCCa' and any(k == 'CC' for k, _ in sk):
            typ = 'A'; note = 'doubled'; cons = cons + [cons[-1]]
        if shape in ('CaCCaCa',) and not any(k == 'CC' for k, _ in sk):
            typ = 'Q'
        if shape in ('CaCaCCaCa',):
            typ = 'P'
    # dedupe doubled geminate consonant lists (CC counts once already)
    return dict(root='-'.join(cons), n_rad=len(cons), type=typ or '?', deriv=deriv, shape=shape, note=note)


if __name__ == '__main__':
    import sys
    for w in sys.argv[1:]:
        print(w, classify(w))
