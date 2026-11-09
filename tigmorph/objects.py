"""Object (pronominal) suffixes, Raz (1973) § 5.12.

attach_objects() takes the subject cells of one paradigm (templates with radical digits, before
the initial-laryngal adjustments) and returns new cells with an object suffix and an Obj tag.

Object suffixes (§ 5.12):  1sg -ni/-nni  1pl -na/-nna  2sm -ka/-kka  2sf -ki/-kki
2pm -kum/-kkum  2pf -kən/-kkən  3sm -o/-wo/-yo/-hu/-yu  3sf -a/-wa/-ya/-ha
3pm -om/-wom/-yom/-hom  3pf -an/-wan/-yan/-han
"""
import re
from collections import defaultdict

OBJ12 = {'1sg': 'ni', '1pl': 'na', '2sm': 'ka', '2sf': 'ki', '2pm': 'kum', '2pf': 'kən'}
OBJ12_G = {'1sg': 'nni', '1pl': 'nna', '2sm': 'kka', '2sf': 'kki', '2pm': 'kkum', '2pf': 'kkən'}
V_C = {'3sm': 'o', '3sf': 'a', '3pm': 'om', '3pf': 'an'}      # after a consonant
V_H = {'3sm': 'u', '3sf': 'a', '3pm': 'om', '3pf': 'an'}      # after transitional h / y (qatlayu, qatalkahu)
OBJ_TAG = {'1sg': '1Sg', '2sm': '2SgM', '2sf': '2SgF', '3sm': '3SgM', '3sf': '3SgF',
           '1pl': '1Pl', '2pm': '2PlM', '2pf': '2PlF', '3pm': '3PlM', '3pf': '3PlF'}
TAG_P = {v: k for k, v in OBJ_TAG.items()}
OBJS = list(OBJ_TAG)


def _ok(subj, obj):
    """No reflexive combinations: 1st person with 1st, 2nd with 2nd."""
    return subj[0] != obj[0] or subj[0] == '3'


def _last_digit(t):
    m = [i for i, ch in enumerate(t) if ch.isdigit()]
    return m[-1] if m else -1


def _first_digit(t):
    for i, ch in enumerate(t):
        if ch.isdigit():
            return i
    return len(t)


def _transpose(stem, v_none, v_after_a):
    """Insert the transposed subject vowel before the last radical (§ 5.12, (2a); § 5.12.2):
    a before R3 → e/o ; ə or nothing before R3 → i/u.  Gemination of R2 when the stem lost it."""
    i = _last_digit(stem)
    if i <= 0:
        return None
    if stem[i - 1] == 'a':
        return stem[:i - 1] + v_after_a + stem[i:]
    if stem[i - 1] == 'ə':
        return stem[:i - 1] + v_none + stem[i:]
    if stem[i - 1].isdigit():                        # CC: insert the vowel
        return stem[:i] + v_none + stem[i:]
    return None


# ---------------------------------------------------------------- perfect (§ 5.12.1)
PERF_ENDINGS = {'1sg': ['ko'], '2sm': ['ka'], '2sf': ['ki'], '3sm': ['a'], '3sf': ['at', 'et'], '1pl': ['na'],
                '2pm': ['kum'], '2pf': ['kən'], '3pm': ['aw'], '3pf': ['aya']}


def _perf(t, subj, obj):
    """Return list of (template, variant) for perfect + object."""
    end = next((e for e in PERF_ENDINGS[subj] if t.endswith(e)), None)
    if end is None:
        return []
    b = t[:-len(end)]
    out = []
    if obj in OBJ12:
        o1, og = OBJ12[obj], OBJ12_G[obj]
        alt = {'1sg': [('ko' + o1, '')], '2sm': [('ka' + og, '')], '2sf': [('ki' + o1, '')],
               '3sm': [('e' + og, '')], '3sf': [(end[0] + 'tta' + og, '')], '1pl': [('na' + o1, '')],
               '2pm': [('ku' + o1, '')], '2pf': [('kəna' + o1, ''), ('kna' + o1, 'schwa-drop')],
               '3pm': [('aw' + o1, ''), ('awu' + o1, 'awu'), ('ayu' + o1, 'awu'), ('u' + o1, 'awu')],
               '3pf': [('aya' + o1, '')]}[subj]
        if obj == '1sg':                                       # -ni ~ -ne (§ 5.12.7 a)
            alt = alt + [(a[:-1] + 'e', 'ne') for a, _ in alt]
    else:
        vc, vh = V_C[obj], V_H[obj]
        alt = {'1sg': [('kw' + vc, ''), ('kuw' + vc, 'kuwo')],
               '2sm': [('kah' + vh, ''), ('kəh' + vh, 'ah-schwa'), ('kh' + vh, 'ah-schwa')],
               '2sf': [('kəy' + vc, ''), ('ky' + vc, 'schwa-drop')],
               '3sm': [('ay' + vh, '')], '3sf': [(end[0] + 'tt' + vc, '')],
               '1pl': [('nah' + vh, ''), ('nəh' + vh, 'ah-schwa')],
               '2pm': [('kum' + vc, '')],
               '2pf': [('kənah' + vh, ''), ('knah' + vh, 'schwa-drop'), ('kənəh' + vh, 'ah-schwa')],
               '3pm': [('aw' + vc, '')], '3pf': [('ayah' + vh, ''), ('ayəh' + vh, 'ah-schwa')]}[subj]
    for a, v in alt:
        out.append((b + a, v))
    return out


# ---------------------------------------------------------------- imperfect / jussive / imperative
def _nonperf(pre, stem, tail, nos, sfx, subj, obj, fin, persons_suffix):
    """pre: prefix; stem: this cell's stem (through last radical); tail: subject ending;
    nos: the no-suffix stem of the paradigm; sfx: the suffixed stem; fin: 'L' / 'S' / ''."""
    out = []
    if fin == 'S':                                            # final semivowel (§ 5.12.5)
        body = stem
        if obj in OBJ12:
            if tail in ('e',):
                out.append((pre + body + 'e' + OBJ12_G[obj], ''))
            out.append((pre + body + tail + OBJ12[obj], ''))
            return out
        vc, vh = V_C[obj], V_H[obj]
        if tail == 'e':
            out += [(pre + body + 'əy' + vc, ''), (pre + body + 'y' + vc, 'schwa-drop'), (pre + body + 'ay' + vc, '')]
        elif tail == 'i':
            out.append((pre + body + 'iy' + vc, ''))
        elif tail == 'u':
            out += [(pre + body + 'əw' + vc, ''), (pre + body + 'w' + vc, 'schwa-drop')]
        elif tail in ('ay', 'aw'):
            out.append((pre + body + tail + vc, ''))
        elif tail in ('ya', 'aya'):
            out += [(pre + body + tail + 'h' + vh, ''), (pre + body + tail[:-1] + 'əh' + vh, 'ah-schwa')]
        return out
    if obj in OBJ12:                                          # 1st/2nd person objects
        bases = [(sfx or stem, '')]
        i = _last_digit(bases[0][0])
        b0 = bases[0][0]
        if fin == 'L' and i > 0 and b0[i - 1] == 'ə':
            bases.append((b0[:i - 1] + b0[i:], 'schwa-drop'))          # ʼəmaṣṣʼakka
        if i > 1 and b0[i - 1].isdigit() and 'ā' in b0:
            bases.append((b0[:i] + 'ə' + b0[i:], 'schwa'))              # təkāləsakki
        for base, bv in bases:
            if not tail:
                out.append((pre + base + 'a' + OBJ12_G[obj], bv))
                if obj == '1sg':
                    out.append((pre + base + 'a' + 'nne', 'ne'))
            else:
                v = {'i': 'i', 'o': 'u', 'u': 'u', 'a': 'a'}.get(tail, tail)
                out.append((pre + base + v + OBJ12[obj], bv))
                if obj == '1sg':
                    out.append((pre + base + v + 'ne', 'ne'))
        return out
    vc, vh = V_C[obj], V_H[obj]
    if fin == 'L':                                            # final laryngal (§ 5.12.4): no transposition
        base = sfx or stem
        if not tail:
            out.append((pre + base + vc, ''))
        elif tail == 'i':
            out.append((pre + base + 'iy' + vc, ''))
        elif tail in ('o', 'u'):
            out.append((pre + base + 'əw' + vc, ''))
            if base.endswith('ə' + base[-1]):
                pass
            i = _last_digit(base)
            if i > 0 and base[i - 1] == 'ə':
                out.append((pre + base[:i - 1] + base[i:] + 'əw' + vc, 'schwa-drop'))
        elif tail == 'a':
            out += [(pre + base + 'ah' + vh, ''), (pre + base + 'əh' + vh, 'ah-schwa')]
        return out
    if not tail:                                              # final radical geminated (ʼəqattəllo, qətallo)
        i = _last_digit(stem)
        out.append((pre + stem + stem[i] + vc, ''))
    elif tail == 'i':
        t = _transpose(nos or stem, 'i', 'e')
        if t:
            out.append((pre + t + vc, ''))
    elif tail in ('o', 'u'):
        t = _transpose(nos or stem, 'u', 'o')
        if t:
            out.append((pre + t + vc, ''))
    elif tail == 'a':
        base = sfx or stem
        out += [(pre + base + 'ah' + vh, ''), (pre + base + 'əh' + vh, 'ah-schwa')]
    return out


def attach_objects(cells, fin=''):
    """fin: '' (strong final radical), 'L' (final laryngal), 'S' (final semivowel)."""
    from .paradigm import Cell, TAG_SUBJ
    groups = defaultdict(list)
    for c in cells:
        if c.tags.get('Neg') or c.tags.get('Colloq') or c.variant in ('transp',):
            continue
        groups[(c.tags['TAM'], c.tags['Type'], c.tags['Deriv'], c.variant)].append(c)
    out = []
    for (tam, typ, deriv, var), cs in groups.items():
        # reference stems of the paradigm
        nos = sfx = None
        for c in cs:
            subj = TAG_SUBJ[c.tags['Subj']]
            t = c.template
            li = _last_digit(t)
            if li < 0:
                continue
            fd = _first_digit(t)
            if subj in ('3sm', '2sm') and not t[li + 1:] and nos is None:
                nos = t[fd:li + 1]
            if subj in ('2sf', '2pm', '3pm', '2pf', '3pf') and t[li + 1:] and sfx is None:
                sfx = t[fd:li + 1]
        for c in cs:
            subj = TAG_SUBJ[c.tags['Subj']]
            t = c.template
            for obj in OBJS:
                if not _ok(subj, obj):
                    continue
                if tam == 'Perf':
                    alts = _perf(t, subj, obj)
                else:
                    li = _last_digit(t)
                    if li < 0:
                        continue
                    fd = _first_digit(t)
                    pre, stem, tail = t[:fd], t[fd:li + 1], t[li + 1:]
                    alts = _nonperf(pre, stem, tail, nos, sfx, subj, obj, fin, None)
                for tpl, v in alts:
                    out.append(Cell(tpl, dict(c.tags, Obj=OBJ_TAG[obj]), c.constraints, '+'.join(x for x in (c.variant, v) if x)))
    return out
