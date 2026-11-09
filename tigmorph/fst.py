"""Compile tigmorph's finite-state transducers with pynini.

Levels (all strings are UTF-8):
  upper  : root radicals (Raz Latin) + tag symbols          e.g.  q t l ⟨A⟩⟨Base⟩⟨Impf⟩⟨3SgM⟩
  middle : Raz phonological transcription                  e.g.  ləqattəl
  lower  : Ge'ez                                           e.g.  ልቀትል

MORPH  maps upper → middle; it is root-independent (radical slots accept any consonant of the
       right class), so it doubles as the guesser.
LEX    is a weighted acceptor over upper strings: known (root, type, deriv) = 0, known root
       with an unlisted type/derivation = LEX_OTHER, unknown root (guess) = GUESS.
ORTH   maps middle → lower (Ge'ez), with weighted spelling variants seen in the corpus.
"""
import os, pickle
from collections import defaultdict
import pynini as pn
from pynini.lib import pynutil

from .paradigm import all_cells, TYPES, DENT
from .fidel import BASE, ORDER_OFFSET, LARYNGALS

U = 'utf8'
VARIANT_W = {'': 0.0, 'assim': 0.4, 'tə-drop': 1.5, 'doubled': 0.0, 'colloq': 0.5, 'transp': 0.2,
             'short-imp': 0.4, 'schwa-drop': 0.3, 'schwa': 0.6, 'w-y': 0.4, 'haba': 0.6, 'biradical': 0.4,
             'lar-elide': 0.6, 'lar-a': 0.5, 'lar-c': 0.4, 'degem': 0.5, 'schwa-a': 0.4, 'reduce': 0.6, 'tə-elide': 1.0, 'ne': 0.5, 'awu': 0.4, 'kuwo': 0.0,
             'ah-schwa': 0.3, 'assim-reduce': 0.8, 'a-written': 0.0, 'nom': 0.3, 'nom2': 0.6, 'nom3': 0.9, 'nom-hollow': 0.3, 'neg-contract': 0.0, 'fin-lar-a': 0.6}
CERTAINTY_W = {'raz': 0.0, 'corpus': 0.05, 'lh-hint': 0.1, 'lh-ambiguous': 0.3, 'lh-review': 0.5, 'lh-alt': 0.5,
               'lh-demoted': 0.8, 'candidate': 0.8, 'candidate-alt': 1.2,
               'reviewed': 0.1, 'wikt-hint': 0.15, 'wikt-ambiguous': 0.35}
LEX_OTHER = 1.0
GUESS = 3.0

ALL_CONS = [c for c in BASE]
STRONG = [c for c in ALL_CONS if c not in LARYNGALS and c not in 'wy']
_pairs = lambda xs: [(c, c) for c in xs]
# radical classes as (upper letter, surface realisation) pairs
CLASSES = {'C': _pairs(STRONG), 'DENT': _pairs([c for c in STRONG if c in DENT]), 'L': _pairs(sorted(LARYNGALS)),
           'S': _pairs('wy'), 'w': _pairs('w'), 'y': _pairs('y'), 'N': _pairs(STRONG + ['w', 'y']),
           'ANY': _pairs(ALL_CONS), 'wo': [('w', 'o')], 'ye': [('y', 'e')]}


from .tags import TAG_ORDER, _TAG_VALUES, TAG2CH, CH2TAG, tagstr  # noqa: E402,F401


def acc(s, w=None):
    a = pn.accep(s, token_type=U)
    return a if w is None else pn.accep(s, token_type=U, weight=w)


def cross(i, o, w=0.0):
    t = pn.cross(acc(i), acc(o))
    return pn.cross(acc(i), acc(o)) if not w else (t + pn.accep('', weight=w))


# ---------------------------------------------------------------- MORPH
def split_template(tpl, nrad):
    """'lə1a22ə3o' -> prefix 'lə', blocks ['1a', '22ə', '3'], suffix 'o' (blocks keep digits)."""
    pos = [i for i, ch in enumerate(tpl) if ch.isdigit()]
    if not pos:
        return tpl, [''] * nrad, ''
    prefix, suffix = tpl[:pos[0]], tpl[pos[-1] + 1:]
    body = tpl[pos[0]:pos[-1] + 1]
    blocks = [''] * nrad
    present = sorted({int(ch) for ch in body if ch.isdigit()})
    for j, k in enumerate(present):
        start = body.index(str(k))
        end = body.index(str(present[j + 1])) if j + 1 < len(present) else len(body)
        blocks[k - 1] = body[start:end]
    return prefix, blocks, suffix


def slot_fst(k, block, pairs):
    """Read radical k (upper letter u) and write its block with the slot realised as l."""
    return pn.union(*[cross(u, block.replace(str(k), l)) for u, l in pairs])


def _slot_pairs(k, shape, constraints):
    pairs = CLASSES[shape[k - 1]]
    c = constraints.get(k)
    if c == 'DENT':
        pairs = [(u, l) for u, l in pairs if u in DENT]
    elif c == 'GLOT':
        pairs = [(u, l) for u, l in pairs if u == 'ʼ']
    return pairs


def stem_fst(blocks, constraints, shape):
    """Concatenate radical slots; SAME2 makes slot 3 copy slot 2 (doubled roots)."""
    parts, k, n = [], 0, len(blocks)
    while k < n:
        if k + 1 == 2 and constraints.get(3) == 'SAME2':
            parts.append(pn.union(*[cross(u + u, blocks[1].replace('2', l) + blocks[2].replace('3', l))
                                     for u, l in _slot_pairs(2, shape, constraints)]))
            k += 2
            continue
        pairs = _slot_pairs(k + 1, shape, constraints)
        if not pairs:
            return None
        parts.append(slot_fst(k + 1, blocks[k], pairs))
        k += 1
    out = parts[0]
    for p in parts[1:]:
        out = out + p
    return out


def build_morph(shapes=None):
    """Union over root shapes of all paradigm cells, plus the irregular verbs listed in full."""
    from .paradigm import SHAPES, irregular_cells
    shapes = shapes or [(r, sh) for r in (3, 4, 5) for sh in SHAPES[r]]
    groups = defaultdict(list)
    for rad, shape in shapes:
        for cell in all_cells(rad, shape):
            pre, blocks, suf = split_template(cell.template, rad)
            key = (rad, shape, pre, tuple(blocks), tuple(sorted(cell.constraints.items())))
            groups[key].append((tagstr(cell.tags), suf, sum(VARIANT_W.get(v, 0.5) for v in cell.variant.split('+')) if cell.variant else 0.0))
    fsts = []
    for (rad, shape, pre, blocks, cons), ends in groups.items():
        st = stem_fst(list(blocks), dict(cons), shape)
        if st is None:
            continue
        tail = pn.union(*[cross(t, s, w) for t, s, w in set(ends)])
        fsts.append((cross('', pre) + st + tail).optimize())
    irr = [cross(root.replace('-', '') + tagstr(c.tags), c.template) for root, c in irregular_cells()]
    morph = pn.union(*fsts, *irr).optimize()
    # optional assimilation of n to m before b and vice versa (ʼambata ~ ʼanbata, § 1.2.4)
    sigma = pn.union(*[acc(x) for x in ALL_CONS + VOWELS]).closure().optimize()
    mn = pn.cdrewrite(cross('m', 'n', 0.3), '', 'b', sigma, mode='opt')
    return (morph @ mn).optimize()


# ---------------------------------------------------------------- ORTH (Raz Latin → Ge'ez)
VOWELS = ['a', 'u', 'i', 'ā', 'e', 'ə', 'o']
LAR_A4 = {'ʼ': 0x12A3, 'ʿ': 0x12D3, 'ḥ': 0x1213, 'h': 0x1203}      # ኣ ዓ ሓ ሃ
W_A_LONG_PLAIN = 0.3        # ā written with 1st order (ከተበ for kātaba): the common spelling
W_A_LONG_MARKED = 0.6       # ā written with 4th order (ካተበ)
W_LAR_A4 = 1.2              # laryngal + a written with 4th order (ኣ ዓ ሓ ሃ)
W_FINAL_YA = 0.0            # word-final ya written ያ (house spelling)
W_FINAL_YE = 0.2            # word-final ya written የ (corpus majority; accepted)


LATIN = ALL_CONS + VOWELS


def build_orth():
    """Raz Latin -> Ge'ez.  Step 1 (obligatory): a geminate is written once (qatta -> qata).
    Step 2: each consonant + vowel is one fidel letter; ə and no vowel both give the 6th order."""
    sigma = pn.union(*[acc(x) for x in LATIN]).closure().optimize()
    collapse = pn.cdrewrite(pn.union(*[cross(c + c, c) for c in ALL_CONS]), '', '', sigma).optimize()
    syl = []
    for c in ALL_CONS:
        for v in VOWELS + ['']:
            if v == 'ā':
                syl.append(cross(c + v, chr(BASE[c] + ORDER_OFFSET['a']), W_A_LONG_PLAIN))
                syl.append(cross(c + v, chr(BASE[c] + ORDER_OFFSET['ā']), W_A_LONG_MARKED))
                continue
            syl.append(cross(c + v, chr(BASE[c] + ORDER_OFFSET[v])))
            if v == 'a' and c in LAR_A4:
                syl.append(cross(c + v, chr(LAR_A4[c]), W_LAR_A4))
    syllabify = pn.union(*syl).closure().optimize()
    # word-final -ya (3pl.f perfect -aya, imperfect -ya) is also written ያ (በልዐያ for በልዐየ);
    # የ is ~95% of corpus tokens, so ያ carries a small cost
    YA, YE = chr(BASE['y'] + ORDER_OFFSET['ā']), chr(BASE['y'])
    final_ya = syllabify + cross('ya', YA, W_FINAL_YA)
    orth = (collapse @ pn.union(syllabify, final_ya)).optimize()
    # house spelling (user decision): word-final -ya is written ያ; የ stays accepted at a small cost
    geez = [chr(c) for c in range(0x1200, 0x1380)] + [chr(0xE000 + i) for i in range(0)]
    out_sigma = pn.union(*[acc(ch) for ch in geez]).closure()
    not_ye = pn.union(*[acc(ch) for ch in geez if ch != YE])
    pref = pn.union(out_sigma + acc(YE, W_FINAL_YE), out_sigma + not_ye, acc('')).optimize()
    return (orth @ pref).optimize()


# ---------------------------------------------------------------- LEX
GUESS_QUAD = 1.0


def build_lex(entries):
    """entries: iterable of (root_latin_string, type, deriv, weight).  Returns three weighted acceptors
    over upper strings: exact lexicon matches, known roots with another type/derivation, and guesses."""
    tag_sigma = pn.union(*[acc(ch) for ch in CH2TAG]).closure()
    cons_sigma = pn.union(*[acc(c) for c in ALL_CONS])
    known = defaultdict(dict)
    for root, typ, deriv, w in entries:
        known[root][(typ, deriv)] = min(w, known[root].get((typ, deriv), 9))
    typ_any = pn.union(*[acc(TAG2CH[('Type', t)]) for t in _TAG_VALUES['Type']])
    der_any = pn.union(*[acc(TAG2CH[('Deriv', d)]) for d in _TAG_VALUES['Deriv']])
    roots_exact, roots_any = [], []
    for root, combos in known.items():
        ex = pn.union(*[acc(TAG2CH[('Type', t)] + TAG2CH[('Deriv', d)], w) for (t, d), w in combos.items()])
        roots_exact.append(acc(root) + ex)
        roots_any.append(acc(root))
    exact = pn.union(*roots_exact).optimize() + tag_sigma
    other = (pn.union(*roots_any).optimize() + typ_any + der_any + tag_sigma) + pn.accep('', weight=LEX_OTHER)
    # prior: most Tigre verbs are triradical; a 4/5-radical guess must beat a triradical + prefix reading
    nrad = pn.union(pn.closure(cons_sigma, 3, 3), pn.closure(cons_sigma, 4, 4) + pn.accep('', weight=GUESS_QUAD),
                    pn.closure(cons_sigma, 5, 5) + pn.accep('', weight=2 * GUESS_QUAD))   # Fst.closure is destructive
    guess = (nrad + typ_any + der_any + tag_sigma) + pn.accep('', weight=GUESS)
    return exact.optimize(), other.optimize(), guess.optimize()


