"""Nominal inflection in Ge'ez spelling (Raz Ch. 2): pronominal suffixes with their junctures (§ 2.10.1)
and suffixed plurals (§ 2.4), undone by string rules on the fidel letters at run time.

poss_splits(word)   -> [(stem, {'Poss': ...}, cost)]   (the word itself with {} first)
plural_splits(stem) -> [(singular stem, {'Number': 'Pl', 'Plural': ...}, cost)]
"""
from .fidel import letters, to_fidel

VOWEL = {1: 'a', 2: 'u', 3: 'i', 4: 'ā', 5: 'e', 6: '', 7: 'o'}
PALATAL = {'č': ['t'], 'ǧ': ['d'], 'š': ['s'], 'ž': ['z'], 'č̣': ['ṣ', 'ṭ']}


def _L(g):
    return letters(g)


def _six(c):
    return to_fidel(c, '')


def poss_splits(g):
    """Possible (stem, feats, cost) readings of g as stem + pronominal suffix."""
    out = [(g, {}, 0.0)]
    L = _L(g)
    n = len(L)
    if n < 2:
        return out
    c1, o1 = L[-1][0], L[-1][1]
    c2, o2 = (L[-2][0], L[-2][1]) if n >= 2 else (None, None)

    def add(stem, cell, cost):
        if stem:
            out.append((stem, {'Poss': cell}, cost))
            sl = _L(stem)
            if sl and sl[-1][1] == 2 and len(sl) >= 2:              # ʼabuka, ʼabuhu (§ 2.10.1 c)
                out.append((stem[:-1] + _six(sl[-1][0]), {'Poss': cell}, cost + 0.3))

    # consonant-initial suffixes: attached to the stem as written
    if (c1, o1) == ('k', 1):
        add(g[:-1], '2SgM', 0.1)
    if (c1, o1) == ('k', 3):
        add(g[:-1], '2SgF', 0.1)
    if (c1, o1) == ('n', 1):
        add(g[:-1], '1Pl', 0.2)
    if n >= 3 and (c2, o2, c1, o1) == ('k', 2, 'm', 6):
        add(g[:-2], '2PlM', 0.1)
    if n >= 3 and (c2, o2, c1, o1) == ('k', 6, 'n', 6):
        add(g[:-2], '2PlF', 0.1)
    if (c1, o1) == ('y', 5):
        add(g[:-1], '1Sg', 0.1)
    # 1sg after a dental: ʿad -> ʿaǧǧe, bet -> beče (§ 2.10.1 a)
    if o1 == 5 and c1 in PALATAL:
        for d in PALATAL[c1]:
            add(g[:-1] + _six(d), '1Sg', 0.1)
        add(g[:-1], '1Sg', 0.6)                                    # fem. juncture -t-: ʿəčče from ʿən
    # vowel-initial suffixes fused with a final consonant: betu, beta, betom, betan
    if o1 == 2 and c1 != 'h':
        add(g[:-1] + _six(c1), '3SgM', 0.1)
    if o1 == 4 and c1 != 'h':
        add(g[:-1] + _six(c1), '3SgF', 0.2)
    if n >= 3 and o2 == 7 and (c1, o1) == ('m', 6) and c2 != 'h':
        add(g[:-2] + _six(c2), '3PlM', 0.1)
    if n >= 3 and o2 == 4 and (c1, o1) == ('n', 6) and c2 != 'h':
        add(g[:-2] + _six(c2), '3PlF', 0.2)
    # transitional -h- after a vowel-final stem: ḥuhu, ʼədeha, səʼlihom, matlohan; a -> ə: morhu (mora)
    hs = []
    if (c1, o1) == ('h', 2):
        hs.append((g[:-1], '3SgM'))
    if c1 == 'h' and o1 in (1, 4):
        hs.append((g[:-1], '3SgF'))
    if n >= 3 and (c2, o2, c1, o1) == ('h', 7, 'm', 6):
        hs.append((g[:-2], '3PlM'))
    if n >= 3 and c2 == 'h' and o2 in (1, 4) and (c1, o1) == ('n', 6):
        hs.append((g[:-2], '3PlF'))
    for stem, cell in hs:
        sl = _L(stem)
        if not sl:
            continue
        if sl[-1][1] != 6:
            add(stem, cell, 0.1)
        else:
            add(stem[:-1] + to_fidel(sl[-1][0], 'a'), cell, 0.3)   # mora -> mor(ə)hu
            add(stem, cell, 0.4)                                   # kəmsalhu-type consonant stems
    # feminine juncture -t- with 3rd-person suffixes: ʿəntu (ʿən), walattu (walat)
    if c1 == 't' and o1 in (2, 4):
        add(g[:-1], '3SgM' if o1 == 2 else '3SgF', 0.4)
    if n >= 3 and c2 == 't' and o2 in (7, 4) and c1 in ('m', 'n') and o1 == 6:
        add(g[:-2], '3PlM' if o2 == 7 else '3PlF', 0.4)
    return out


def plural_splits(s):
    """Suffixed plurals (§ 2.4) and the adjective feminine -ət/-at -> singular stems."""
    out = []
    L = _L(s)
    n = len(L)
    if n < 3:
        return out
    (ca, oa), (cb, ob), (cc, oc) = (L[-3][0], L[-3][1]), (L[-2][0], L[-2][1]), (L[-1][0], L[-1][1])
    if (cc, oc) == ('t', 6) and (cb, ob) == ('t', 4) and oa == 7:       # -otāt: ʿaddotāt
        out.append((s[:-3] + _six(ca), {'Number': 'Pl', 'Plural': 'otāt'}, 0.3))
    if (cc, oc) == ('t', 6) and ob in (4, 1):                           # -āt / -at
        out.append((s[:-2] + _six(cb), {'Number': 'Pl', 'Plural': 'āt' if ob == 4 else 'at'}, 0.3 if ob == 4 else 0.5))
        if L[-2][0] == 'y' and ob == 4:                                 # -yāt after a vowel stem
            out.append((s[:-2], {'Number': 'Pl', 'Plural': 'yāt'}, 0.5))
    if (cc, oc) == ('t', 6) and ob == 7:                                # -ot
        out.append((s[:-2] + _six(cb), {'Number': 'Pl', 'Plural': 'ot'}, 0.5))
    if (cc, oc) == ('č', 6) and ob == 4:                                # -ač
        out.append((s[:-2] + _six(cb), {'Number': 'Pl', 'Plural': 'ač'}, 0.5))
    if (cc, oc) == ('m', 6) and ob == 4:                                # -ām
        out.append((s[:-2] + _six(cb), {'Number': 'Pl', 'Plural': 'ām'}, 0.4))
        if L[-2][0] == 'y':
            out.append((s[:-2], {'Number': 'Pl', 'Plural': 'yām'}, 0.5))
    if (cc, oc) == ('t', 6) and ob == 6:                                # adjective fem. -ət
        out.append((s[:-1], {'Gender': 'F'}, 0.5))
    return out
