#!/usr/bin/env python3
"""Extract gold verb forms from the Raz (1973) Ch. 5 transcription.

Paradigm tables follow Raz's fixed order (fn. 2, p. 271): rows 1sg, 2sm, 2sf, 3sm, 3sf
in the singular column and 1pl, 2pm, 2pf, 3pm, 3pf in the plural column; imperative
tables list 2sm, 2sf, 2pm, 2pf.  Tables split by page breaks are continued.
Usage: python3 -I tools/extract_raz_gold.py RAZ_CH5_TEXT.txt data/gold/raz_ch5_raw.tsv
"""
import sys, re, csv, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tigmorph.fidel import latin_to_fidel

SG = ['1sg', '2sm', '2sf', '3sm', '3sf']
PL = ['1pl', '2pm', '2pf', '3pm', '3pf']
IMP = ['2sm', '2sf', '2pm', '2pf']
TENSES = [('imperfect/jussive', 'impf/juss'), ('imperfect', 'impf'), ('jussive', 'juss'),
          ('imperative', 'imp'), ('perfect', 'perf')]


def clean(cell):
    c = re.sub(r'\[\^\d+\]|\[\?\]|[_*]', '', cell).strip()
    return c


def tense_of(cell):
    c = clean(cell).lower().rstrip(':')
    for k, v in TENSES:
        if c == k:
            return v
    return None


def is_form(c):
    return bool(c) and re.fullmatch(r"[a-zāəčšžǧḥṣṭʼʿ̣/ \-]+", c) is not None and not c.startswith('∗')


def main(src, dst):
    lines = open(src, encoding='utf-8').read().split('\n')
    start = next(i for i, l in enumerate(lines) if l.startswith('## § 5.1 '))
    end = next(i for i, l in enumerate(lines) if l.startswith('## § 6') or l.startswith('# Chapter 6')) if any(
        l.startswith('## § 6') for l in lines) else len(lines)
    sec, sub, lemma, gloss = '', '', '', ''
    out = []
    cols, rowi = None, 0          # current paradigm column labels and row counter
    i = start
    while i < end:
        l = lines[i]
        if l.startswith('## § '):
            sec = l[5:].split('|')[0].strip(); sub = ''; cols = None
        elif l.startswith('### '):
            sub = l[4:].strip(); cols = None
        elif l.startswith(('CENTER _', 'PI _')) and '–' in l:
            m = re.match(r'(?:CENTER|PI) _([^_]+)_\s*(?:\([^)]*\))?\s*–\s*(.*)', l)
            if m:
                lemma, gloss = m.group(1).strip(), m.group(2).strip()
                cols = None
        elif l == 'TABLE':
            j = i + 1
            rows = []
            while j < end and lines[j] != 'END':
                rows.append([c for c in lines[j].split('|')])
                j += 1
            i = j
            # header?
            first = [clean(c) for c in rows[0]] if rows else []
            hdr = [tense_of(c) for c in rows[0]] if rows else []
            if any(hdr):
                # build column labels: each tense label spans following blank cells
                labels, cur = [], None
                for k, c in enumerate(first):
                    t = tense_of(rows[0][k])
                    if t:
                        cur = t; labels.append((t, 0))
                    elif cur and labels and labels[-1][0] == cur and labels[-1][1] == 0 and cur != 'imp':
                        labels.append((cur, 1))
                    else:
                        labels.append((None, 0))
                cols, rowi = labels, 0
                rows = rows[1:]
            elif rows and len(rows[0]) == 2 and tense_of(rows[0][0]) is None and any(tense_of(r[0]) for r in rows):
                pass
            # "Label: | form" tables
            if rows and all(len(r) == 2 for r in rows) and any(tense_of(r[0]) for r in rows):
                for r in rows:
                    t = tense_of(r[0])
                    f = clean(r[1])
                    if t and is_form(f):
                        out.append(dict(form=f, tense=t, person='2sm' if t == 'imp' else '3sm', lemma=lemma,
                                        gloss=gloss, section=sec, context=sub, line=i, kind='label'))
                cols = None
                i += 1; continue
            if cols is not None:
                for r in rows:
                    cells = [clean(c) for c in r]
                    if not any(is_form(c) for c in cells):
                        continue
                    for k, c in enumerate(cells):
                        if k >= len(cols) or not cols[k][0] or not is_form(c):
                            continue
                        t, pl = cols[k]
                        if t == 'imp':
                            # imperative column within a mixed table, or a single-column table
                            pers = IMP[rowi] if rowi < 4 else None
                        else:
                            pers = (PL if pl else SG)[rowi] if rowi < 5 else None
                        if not pers:
                            continue
                        for n, f in enumerate(c.split('/')):
                            f = f.strip()
                            tt = t
                            if t == 'impf/juss' and '/' in c:
                                tt = 'impf' if n == 0 else 'juss'
                            out.append(dict(form=f, tense=tt, person=pers, lemma=lemma, gloss=gloss, section=sec,
                                            context=sub, line=i, kind='paradigm'))
                    rowi += 1
            elif rows and all(len(r) == 1 for r in rows) and len(rows) == 4 and all(is_form(clean(r[0])) for r in rows):
                # bare 4-row table = imperative (e.g. § 5.3.2 qənaṣ ...) or negated imperative
                for k, r in enumerate(rows):
                    out.append(dict(form=clean(r[0]), tense='imp', person=IMP[k], lemma=lemma, gloss=gloss,
                                    section=sec, context=sub, line=i, kind='bare4'))
            elif rows and all(len(r) == 2 for r in rows) and len(rows) == 5 and all(is_form(clean(c)) for r in rows for c in r):
                # bare 5x2 table = a paradigm without header (e.g. colloquial imperfect)
                for k, r in enumerate(rows):
                    for pl, c in enumerate(r):
                        out.append(dict(form=clean(c), tense='impf', person=(PL if pl else SG)[k], lemma=lemma,
                                        gloss=gloss, section=sec, context=sub, line=i, kind='bare5'))
            else:
                # example tables: cells containing _form_ with labels like "type A:" "_tə_-A:" and
                # "imperfect/jussive: _x_"
                for r in rows:
                    raw = '|'.join(r)
                    lab = clean(r[0]).rstrip(':') if r else ''
                    forms = re.findall(r'_([^_]+)_', raw)
                    impfj = re.search(r'imperfect/jussive:\s*_([^_]+)_', raw)
                    for f in forms:
                        f = clean(f)
                        if not is_form(f) or (impfj and f == impfj.group(1)):
                            continue
                        out.append(dict(form=f, tense='?', person='?', lemma=lemma, gloss=gloss, section=sec,
                                        context=(sub + ' :: ' + lab).strip(' :'), line=i, kind='example'))
                    if impfj and is_form(clean(impfj.group(1))):
                        out.append(dict(form=clean(impfj.group(1)), tense='impf/juss', person='3sm', lemma=lemma,
                                        gloss=gloss, section=sec, context=(sub + ' :: ' + lab).strip(' :'), line=i,
                                        kind='example'))
        i += 1
    for o in out:
        o['fidel'] = ' '.join(latin_to_fidel(w) for w in o['form'].split())
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    F = ['fidel', 'form', 'tense', 'person', 'lemma', 'gloss', 'section', 'context', 'kind', 'line']
    with open(dst, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, F, delimiter='\t', extrasaction='ignore')
        w.writeheader(); w.writerows(out)
    return out


if __name__ == '__main__':
    from collections import Counter
    out = main(sys.argv[1], sys.argv[2])
    print(len(out), Counter(o['kind'] for o in out))
    print(Counter(o['section'].split('.')[1] if '.' in o['section'] else o['section'] for o in out))
