#!/usr/bin/env python3
"""Ingest the Littmann–Höfner (1962) verb list (tigre_verbs.xlsx) into a tigmorph lexicon TSV.

Each headword is the perfect 3m.sg citation form.  From its fidel orders we infer
(following Raz 1973, Ch. 5) the root, Raz type (A/B/C/D), weak class and any
derivational prefix.  Ambiguous or irregular shapes are flagged for review instead
of being guessed silently.
Usage: python3 -I tools/ingest_lh.py data/source/tigre_verbs.xlsx data/lexicon/verbs_lh.tsv
"""
import sys, re, csv, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import openpyxl
from tigmorph.fidel import letters, to_fidel, LARYNGALS

FIELDS = ['id', 'headword', 'variants', 'root', 'root_latin', 'n_rad', 'type', 'weak',
          'deriv', 'status', 'note', 'gloss_en', 'gloss_ar', 'lh_reliability', 'source']


def root_str(cons):
    return '-'.join(to_fidel(c, '') for c in cons), '-'.join(cons)


def weak_flags(cons):
    """Raz weak classes from the root consonants."""
    f = []
    n = len(cons)
    for i, c in enumerate(cons):
        pos = 'I' if i == 0 else ('II' if i == 1 else ('III' if i == n - 1 and n == 3 else str(i + 1)))
        if c in LARYNGALS:
            f.append(f'{pos}-L')
        elif c in 'wy':
            f.append(f'{pos}-{c}')
    if n == 3 and cons[1] == cons[2]:
        f.append('doubled')
    return f


def classify(hw):
    """Return dict(root, n_rad, type, deriv, status, note) from a fidel headword."""
    L = letters(hw)
    C = [l[0] for l in L]
    O = [l[1] for l in L]
    n = len(L)
    r = dict(cons=C, type='', deriv='base', status='ok', note='')
    lab = any(l[3] for l in L)
    if lab:
        r['note'] = 'labialized consonant; '
    if n == 0:
        r.update(status='review', note='no fidel letters'); return r
    # final vowel: perfect 3m.sg ends in -a (1st order); 4th order on a laryngal = same
    final_sv = False
    if O[-1] == 4 and C[-1] in LARYNGALS:
        O[-1] = 1; r['note'] += 'final ā on laryngal read as a; '
    elif O[-1] == 4:
        # LH writes final -ā on verbs whose last radical is a semivowel (Raz: fanta, nawna)
        O[-1] = 1; final_sv = True; r['status'] = 'ambiguous'
        r['note'] += 'final ā read as final-semivowel verb (cf. Raz fanta, § 5.9.2); '
    elif O[-1] != 1:
        r['status'] = 'review'; r['note'] += f'last letter is order {O[-1]}, not a perfect -a ending; '

    # derived-only headwords: tə- (ተ/ት...) and ʼa- (አ + vowelless R1)
    if n >= 4 and C[0] == 't' and O[0] in (1, 6) and O[1] == 1:
        r['deriv'] = 'tə'; r['note'] += 'possible tə- form (check); '
    if n >= 4 and C[0] == 'ʼ' and O[0] == 1 and O[1] == 6:
        r.update(deriv='ʼa', cons=C[1:]); C, O = C[1:], O[1:]; n -= 1
        if O[0] == 6 and O[1] == 1:   # ʼa-A: R1 vowelless (ʼafgara); restore base A shape
            O[1] = 6 if n == 3 else O[1]; O[0] = 1
        r['note'] += 'listed as ʼa- form; '
    if n >= 4 and C[0] == 'ʼ' and O[0] == 1 and C[1] in 'ns' and O[1] == 6:
        r.update(deriv='ʼan' if C[1] == 'n' else 'ʼas', cons=C[2:]); C, O = C[2:], O[2:]; n -= 2
        r['note'] += 'listed as ʼan-/ʼas- form; '

    if final_sv:
        C = C + ['y']; O = O + [1]; n += 1; r['cons'] = C
        if n == 3 and O[0] == 1 and O[1] == 1:   # CaCā: treat as type A III-SV (šaqa)
            r['type'] = 'A'; return r
    if n == 2:
        if O[0] == 5:
            r.update(cons=[C[0], 'y', C[1]], type='A', status='ambiguous',
                     note=r['note'] + 'CēCa: hollow triradical (like gēda) OR quadriradical C-y-C-SV (like gega, § 5.9.2); ')
        elif O[0] == 7:
            r.update(cons=[C[0], 'w', C[1]], type='A', status='ambiguous',
                     note=r['note'] + 'CoCa: hollow triradical (like dora) OR quadriradical C-w-C-SV (like gola, § 5.9.2); ')
        elif O[0] == 1:
            r.update(cons=[C[0], C[1], 'y'], type='A', status='ambiguous',
                     note=r['note'] + 'CaCa: final semivowel (like šaqa) OR doubled root (like ʿaqqa); ')
        elif O[0] == 4:
            r.update(cons=[C[0], 'w', C[1]], type='?', status='review', note=r['note'] + 'CāCa shape; ')
        else:
            r.update(status='review', note=r['note'] + f'2-letter shape with order {O[0]}; ')
    elif n == 3:
        o1, o2 = O[0], O[1]
        if o1 == 1 and o2 == 6:
            r['type'] = 'A'
        elif o1 == 1 and o2 == 1:
            if C[1] in LARYNGALS:
                r.update(type='A', status='ambiguous', note=r['note'] + 'CaLaCa: type A of II-laryngal (like ṣaʿana), B also possible; ')
            elif C[2] in LARYNGALS:
                r.update(type='B', status='ambiguous', note=r['note'] + 'CaCaLa: type B, or A of III-laryngal; ')
            else:
                r['type'] = 'B'
        elif o1 == 4 and o2 == 1:
            r['type'] = 'C'
        elif o1 in (6, 4) and C[0] in LARYNGALS and o2 in (6, 1):
            r.update(type='A', note=r['note'] + 'initial laryngal spelled with ə/ā (type A, like ḥaṣba); ')
        elif o1 == 5 and o2 == 1:
            r.update(cons=[C[0], 'y', C[1], C[2]], type='Q', note=r['note'] + 'quadriradical C-y-C-C, y→e (like deraba, § 5.9.2); ')
        elif o1 == 7 and o2 == 1:
            r.update(cons=[C[0], 'w', C[1], C[2]], type='Q', note=r['note'] + 'quadriradical C-w-C-C, w→o (like gorata, § 5.9.2); ')
        else:
            r.update(type='?', status='review', note=r['note'] + f'3-letter orders {O[:3]}; ')
    elif n == 4:
        if O[1] == 4 and C[1] == C[2]:
            r.update(cons=[C[0], C[1], C[3]], type='D', note=r['note'] + 'type D (R2 repeated); ')
        elif O[:2] == [1, 6]:
            r['type'] = 'Q'
            if C[0] == C[2] and C[1] == C[3]:
                r['note'] += 'reduplicated 2+2 (like ṭafṭafa); '
        elif O[:2] == [1, 4]:
            r['type'] = 'QC'
            if C[2] == C[3]:
                r['note'] += 'final radical repeated (like qarāṭaṭa); '
        elif O[:2] == [1, 7]:
            r['type'] = 'QO'; r['note'] += 'o-group (like ḥanobaza); '
        elif O[:3] == [1, 1, 1] and C[1] in LARYNGALS:
            r.update(type='Q', note=r['note'] + 'quadriradical with 2nd-radical laryngal (like č̣aʿarara); ')
        elif O[:2] in ([6, 6], [4, 6]) and C[0] in LARYNGALS:
            r.update(type='Q', note=r['note'] + 'quadriradical with initial laryngal (like ʼambata); ')
        elif O[:2] == [1, 1]:
            r.update(type='Q?', status='review', note=r['note'] + 'CaCaCaCa shape; ')
        else:
            r.update(type='?', status='review', note=r['note'] + f'4-letter orders {O[:4]}; ')
    elif n == 5:
        if O[:4] == [1, 1, 6, 1] and C[1] == C[3] and C[2] == C[4]:
            r['type'] = 'P'; r['note'] += 'reduplicated 1+2+2 (like balač̣lač̣a); '
        elif O[:2] in ([1, 6], [1, 1], [1, 4]):
            r.update(type='P', status='review', note=r['note'] + '5-letter, not a clean 1+2+2 reduplication; ')
        else:
            r.update(type='?', status='review', note=r['note'] + f'5-letter orders {O}; ')
    else:
        r.update(type='?', status='review', note=r['note'] + f'{n} letters; ')
    return r


def main(src, dst):
    wb = openpyxl.load_workbook(src, read_only=True)
    rows = [x for x in wb['Tigre Verbs'].iter_rows(values_only=True)][1:]
    out = []
    for i, row in enumerate(rows):
        if not row or not row[0]:
            continue
        full, cit, ar, en, rel = (row[0] or '').strip(), (row[1] or '').strip(), row[2] or '', row[3] or '', row[4] or ''
        variants = [v for v in re.split(r'\s*(?:,|\bu\.|\(|\)|፡|:)\s*', full) if v and re.search('[ሀ-፿]', v)]
        rec = dict(id=f'LH{i + 1:04d}', headword=cit, variants='|'.join(v for v in variants if v != cit),
                   gloss_en=en.strip(), gloss_ar=ar.strip(), lh_reliability=rel, source='Littmann–Höfner 1962')
        if re.search(r'[\s፡:]', cit) or 'ቤለ' in full and len(letters(cit)) > 3 and re.search(r'[\s፡:]', full):
            rec.update(root='', root_latin='', n_rad='', type='', weak='', deriv='compound', status='compound',
                       note='compound verb (X + bela/ʼabala); handled by compound rules')
        else:
            c = classify(re.sub(r'[^ሀ-፿]', '', cit))
            rf, rl = root_str(c['cons'])
            rec.update(root=rf, root_latin=rl, n_rad=len(c['cons']), type=c['type'],
                       weak=','.join(weak_flags(c['cons'])), deriv=c['deriv'], status=c['status'], note=c['note'].strip('; '))
            if '(ት)' in full or full.startswith('(ቴ'):
                rec['note'] = (rec['note'] + '; ' if rec['note'] else '') + 'tə- form also listed'
            if rel.startswith('Low'):
                rec['status'] = 'review' if rec['status'] == 'ok' else rec['status']
                rec['note'] = (rec['note'] + '; ' if rec['note'] else '') + 'headword spelling uncertain in source'
        out.append(rec)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, FIELDS, delimiter='\t')
        w.writeheader(); w.writerows(out)
    return out


if __name__ == '__main__':
    out = main(sys.argv[1], sys.argv[2])
    from collections import Counter
    print(len(out), 'entries')
    print('status', Counter(r['status'] for r in out))
    print('type', Counter(r['type'] for r in out))
    print('deriv', Counter(r['deriv'] for r in out))
