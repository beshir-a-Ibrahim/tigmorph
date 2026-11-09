"""Raz (1973) Ch. 5 verb paradigms as *templates*.

A template is a Raz-Latin word in which root radicals are written as digits 1..5, e.g.
'lə1a22ə3' (imperfect 3m.sg of type A: ləqattəl).  Templates are root-independent, so the
same machinery serves known roots (lexicon) and unknown roots (guesser).

A root *shape* gives the class of each radical:
  C   strong consonant (not laryngal, not w/y)          L   laryngal ʼ ʿ h ḥ
  S   semivowel w or y (initial or final position)      w, y  medial semivowel (3 radicals)
  N   any non-laryngal (w/y behave as consonants)       ANY any consonant
  wo  w realised as the vowel o (gola, gorata, ḥanobaza; § 5.9.2, 5.10.1)
  ye  y realised as the vowel e (gega, deraba; § 5.9.2)
Each cell is a Cell(template, tags, constraints, variant).  Section numbers refer to Raz.
"""
import re
from dataclasses import dataclass, field

from .objects import attach_objects

SG = ['1sg', '2sm', '2sf', '3sm', '3sf']
PL = ['1pl', '2pm', '2pf', '3pm', '3pf']
PERSONS = SG + PL
IMP_PERSONS = ['2sm', '2sf', '2pm', '2pf']
SUBJ_TAG = {'1sg': '1Sg', '2sm': '2SgM', '2sf': '2SgF', '3sm': '3SgM', '3sf': '3SgF',
            '1pl': '1Pl', '2pm': '2PlM', '2pf': '2PlF', '3pm': '3PlM', '3pf': '3PlF'}
TAG_SUBJ = {v: k for k, v in SUBJ_TAG.items()}

# § 5.3.1 perfect suffixes
PERF_SUF = {'1sg': 'ko', '2sm': 'ka', '2sf': 'ki', '3sm': 'a', '3sf': 'at',
            '1pl': 'na', '2pm': 'kum', '2pf': 'kən', '3pm': 'aw', '3pf': 'aya'}
CONS_SUF = {p for p in PERSONS if not PERF_SUF[p].startswith('a')}
# § 5.3.1 imperfect/jussive formatives
PRE_BASE = {'1sg': 'ʼə', '2sm': 'tə', '2sf': 'tə', '3sm': 'lə', '3sf': 'tə',
            '1pl': 'ʼən', '2pm': 'tə', '2pf': 'tə', '3pm': 'lə', '3pf': 'lə'}
SUF = {'1sg': '', '2sm': '', '2sf': 'i', '3sm': '', '3sf': '', '1pl': '', '2pm': 'o', '2pf': 'a', '3pm': 'o', '3pf': 'a'}
IMP_SUF = {'2sm': '', '2sf': 'i', '2pm': 'o', '2pf': 'a'}
# § 5.5.3 endings of verbs with a final semivowel
SV_IMPF = {'1sg': 'e', '2sm': 'e', '2sf': 'i', '3sm': 'e', '3sf': 'e', '1pl': 'e', '2pm': 'u', '2pf': 'ya', '3pm': 'u', '3pf': 'ya'}
SV_JUSS = {'1sg': 'e', '2sm': 'e', '2sf': 'ay', '3sm': 'e', '3sf': 'e', '1pl': 'e', '2pm': 'aw', '2pf': 'aya', '3pm': 'aw', '3pf': 'aya'}
SV_IMP = {'2sm': 'e', '2sf': 'ay', '2pm': 'aw', '2pf': 'aya'}
SV_IMP_I = {'2sm': 'e', '2sf': 'i', '2pm': 'u', '2pf': 'ya'}
SV_PERF = {'3sm': 'a', '3sf': 'et', '3pm': 'aw', '3pf': 'aya'}

DENT = set('tdṭsṣzšžčǧ') | {'č̣'}       # § 5.3.5.1: t of tə/ʼat assimilates to these


def jus_pre(p):
    return 'nə' if p == '1pl' else PRE_BASE[p]


def i_pre(p):
    """Jussive prefixes with i (initial-semivowel and hollow verbs, § 5.5.1–5.5.2)."""
    return {'1sg': 'ʼi', '1pl': 'ni'}.get(p, 'li' if p in ('3sm', '3pm', '3pf') else 'ti')


def derived_prefix(head, person):
    """Prefixes of derivatives: ʼa- → ʼa/ta/la/na; ʼat- → ʼat/tat/lat/nat; ʼatta- → ʼatta/tatta/…"""
    first = {'1sg': 'ʼ', '1pl': 'n'}.get(person, 'l' if person in ('3sm', '3pm', '3pf') else 't')
    return first + 'a' + head


def tə_prefix(person, jussive=False):
    """tə- derivatives in imperfect/jussive: ʼət-, tət-, lət-, nət- (§ 5.3.5.1)."""
    first = {'1sg': 'ʼə', '1pl': 'nə'}.get(person, 'lə' if person in ('3sm', '3pm', '3pf') else 'tə')
    return first + 't'


def u_for_o(s):
    """Masculine-plural suffix o is u after a final laryngal (§ 5.4.3)."""
    return 'u' if s == 'o' else s


@dataclass
class Cell:
    template: str
    tags: dict
    constraints: dict = field(default_factory=dict)
    variant: str = ''


def _tags(typ, rad, deriv, tam, person):
    return dict(Type=typ, Rad=str(rad), Deriv=deriv, TAM=tam, Subj=SUBJ_TAG[person])


class _Out(list):
    def __init__(self, typ, rad, deriv):
        super().__init__(); self.k = (typ, rad, deriv)

    def add(self, tpl, tam, p, cons=None, variant=''):
        self.append(Cell(tpl, _tags(self.k[0], self.k[1], self.k[2], tam, p), cons or {}, variant))


# ================================================================ strong triradicals (§ 5.3)
def stems3(typ):
    if typ == 'A':
        return dict(perf12='1a2a3', perf3='1a23', impf='1a22ə3', impf_s='1a23', juss='12a3', imp='1ə2a3')
    if typ == 'B':
        return dict(perf12='1a22a3', perf3='1a22a3', impf='1a22ə3', impf_s='1a23')
    if typ == 'C':
        return dict(perf12='1ā2a3', perf3='1ā2a3', impf='1ā2ə3', impf_s='1ā23')
    if typ == 'D':
        return dict(perf12='1a2ā2a3', perf3='1a2ā2a3', impf='1a2ā2ə3', impf_s='1a2ā23')


def _istem(st, p, suf=None):
    return st['impf_s'] if (SUF[p] if suf is None else suf) else st['impf']


def strong3(typ, deriv, init_sv=False, nogem2=False):
    """Strong triradical paradigm.  init_sv: initial w/y (jussive/imperative of A, § 5.5.1).
    nogem2: medial w/y as consonant, never geminated (§ 5.5.2 (1b))."""
    o = _Out(typ, 3, deriv)
    st = dict(stems3(typ))
    if nogem2:
        st = {k: v.replace('22', '2') for k, v in st.items()}
    if deriv == 'Base':
        for p in PERSONS:
            o.add((st['perf3'] if p.startswith('3') else st['perf12']) + PERF_SUF[p], 'Perf', p)
            o.add(PRE_BASE[p] + _istem(st, p) + SUF[p], 'Impf', p)
            if typ == 'A' and init_sv:
                o.add(i_pre(p) + '2a3' + SUF[p], 'Jus', p)                   # ʼiras, tirasi (§ 5.5.1)
            elif typ == 'A':
                o.add(jus_pre(p) + st['juss'] + SUF[p], 'Jus', p)
            else:
                o.add(jus_pre(p) + _istem(st, p) + SUF[p], 'Jus', p)
        for p in IMP_PERSONS:
            o.add((st['imp'] if typ == 'A' else _istem(st, p, IMP_SUF[p])) + IMP_SUF[p], 'Imp', p)
            if typ == 'A' and init_sv:
                o.add('2a3' + IMP_SUF[p], 'Imp', p, variant='short-imp')    # rad, ladi
    elif deriv == 'tə':
        s = {'A': '1a22a3', 'B': '1a22a3', 'C': '1ā2a3', 'D': '1a2ā2a3'}[typ]
        if nogem2:
            s = s.replace('22', '2')
        for p in PERSONS:
            o.add('tə' + s + PERF_SUF[p], 'Perf', p)
            o.add(s + PERF_SUF[p], 'Perf', p, variant='tə-drop')
            o.add('t' + s + PERF_SUF[p], 'Perf', p, variant='tə-elide')                 # tkabbatawa
            for tam in ('Impf', 'Jus'):
                pre = tə_prefix(p)
                o.add(pre + s + SUF[p], tam, p)
                o.add(pre[:-1] + '1' + s + SUF[p], tam, p, cons={1: 'DENT'}, variant='assim')
        for p in IMP_PERSONS:
            o.add('tə' + s + IMP_SUF[p], 'Imp', p)
    elif deriv == 'ʼa':
        if typ == 'A':
            for p in PERSONS:
                o.add('ʼa12a3' + PERF_SUF[p], 'Perf', p)
                o.add(derived_prefix('', p) + ('1a23' if SUF[p] else ('1a2ə3' if nogem2 else '1a22ə3')) + SUF[p], 'Impf', p)
                o.add(derived_prefix('', p) + '12ə3' + SUF[p], 'Jus', p)
            for p in IMP_PERSONS:
                o.add('ʼa12ə3' + IMP_SUF[p], 'Imp', p)
        elif typ in ('B', 'C'):
            for p in PERSONS:
                o.add('ʼa' + st['perf12'] + PERF_SUF[p], 'Perf', p)
                for tam in ('Impf', 'Jus'):
                    o.add(derived_prefix('', p) + _istem(st, p) + SUF[p], tam, p)
            for p in IMP_PERSONS:
                o.add('ʼa' + _istem(st, p, IMP_SUF[p]) + IMP_SUF[p], 'Imp', p)
    elif (deriv == 'ʼat' and typ in ('B', 'C', 'D')) or (deriv == 'ʼasta' and typ in ('A', 'C')):
        head = 't' if deriv == 'ʼat' else 'sta'
        for p in PERSONS:
            o.add('ʼa' + head + st['perf12'] + PERF_SUF[p], 'Perf', p)
            if deriv == 'ʼat':
                o.add('ʼa1' + st['perf12'] + PERF_SUF[p], 'Perf', p, cons={1: 'DENT'}, variant='assim')
            for tam in ('Impf', 'Jus'):
                pre = derived_prefix(head, p)
                o.add(pre + _istem(st, p) + SUF[p], tam, p)
                if deriv == 'ʼat':
                    o.add(pre[:-1] + '1' + _istem(st, p) + SUF[p], tam, p, cons={1: 'DENT'}, variant='assim')
        for p in IMP_PERSONS:
            o.add('ʼa' + head + _istem(st, p, IMP_SUF[p]) + IMP_SUF[p], 'Imp', p)
            if deriv == 'ʼat':
                o.add('ʼa1' + _istem(st, p, IMP_SUF[p]) + IMP_SUF[p], 'Imp', p, cons={1: 'DENT'}, variant='assim')
    elif deriv == 'ʼatta' and typ in ('A', 'B', 'C'):
        perf = {'A': '12a3', 'B': st['perf12'], 'C': '1ā2a3'}[typ]
        for p in PERSONS:
            o.add('ʼatta' + perf + PERF_SUF[p], 'Perf', p)
            for tam in ('Impf', 'Jus'):
                o.add(derived_prefix('tta', p) + ('12ə3' if typ == 'A' else _istem(st, p)) + SUF[p], tam, p)
        for p in IMP_PERSONS:
            o.add('ʼatta' + ('12ə3' if typ == 'A' else _istem(st, p, IMP_SUF[p])) + IMP_SUF[p], 'Imp', p)
    return o


def at_A(o, perf='1a2a3', ij='1a2ə3', ij_s='1a23'):
    """ʼat-A: exists for initial/medial laryngal roots (§ 5.4.1 (1b), (2d); § 5.4.2)."""
    for p in PERSONS:
        o.add('ʼat' + perf + PERF_SUF[p], 'Perf', p)
        for tam in ('Impf', 'Jus'):
            o.add(derived_prefix('t', p) + (ij_s if SUF[p] else ij) + SUF[p], tam, p)
    for p in IMP_PERSONS:
        o.add('ʼat' + (ij_s if IMP_SUF[p] else ij) + IMP_SUF[p], 'Imp', p)
    return o


# ================================================================ medial laryngal (§ 5.4.2)
def med_lar(typ, deriv):
    o = _Out(typ, 3, deriv)
    if typ == 'A' and deriv == 'Base':
        for p in PERSONS:
            o.add('1a2a3' + PERF_SUF[p], 'Perf', p)                     # CaLaC throughout
            o.add('1ā2a3' + PERF_SUF[p], 'Perf', p, variant='lar-c')     # qaḥara = qāḥara (§ 5.4.2 (c))
            o.add(PRE_BASE[p] + '12ə3' + SUF[p], 'Impf', p)               # CLəC
            if p == '1pl':
                o.add('nə12ə3', 'Impf', p)
                o.add('ʼənə12ə3', 'Impf', p)
            o.add(jus_pre(p) + '12a3' + SUF[p], 'Jus', p)                 # CLaC
        for p in IMP_PERSONS:
            o.add('1a2a3' + IMP_SUF[p], 'Imp', p)                         # CaLaC
            o.add('1ə2a3' + IMP_SUF[p], 'Imp', p, variant='reduce')       # rəḥomom (with object)
    elif typ == 'A' and deriv == 'tə':
        for p in PERSONS:
            o.add('tə1a2a3' + PERF_SUF[p], 'Perf', p)
            o.add('tə1ā2a3' + PERF_SUF[p], 'Perf', p, variant='lar-c')   # təbaʼasa = təbāʼasa
            for tam in ('Impf', 'Jus'):
                o.add(tə_prefix(p) + '1a2a3' + SUF[p], tam, p)
                o.add(tə_prefix(p) + '1ə2a3' + SUF[p], tam, p, variant='reduce')            # lətkəḥodo
                o.add(tə_prefix(p)[:-1] + '11a2a3' + SUF[p], tam, p, cons={1: 'DENT'}, variant='assim')
                o.add(tə_prefix(p)[:-1] + '11ə2a3' + SUF[p], tam, p, cons={1: 'DENT'}, variant='assim-reduce')   # ləssəʼolom
        for p in IMP_PERSONS:
            o.add('tə1a2a3' + IMP_SUF[p], 'Imp', p)
    elif typ == 'A' and deriv == 'ʼa':
        for p in PERSONS:
            o.add('ʼa12a3' + PERF_SUF[p], 'Perf', p)
            for tam in ('Impf', 'Jus'):
                o.add(derived_prefix('', p) + '12ə3' + SUF[p], tam, p)   # C(ə)LəC
        for p in IMP_PERSONS:
            o.add('ʼa12ə3' + IMP_SUF[p], 'Imp', p)
    elif typ == 'A' and deriv == 'ʼat':
        at_A(o, perf='1a2a3', ij='1ə2ə3', ij_s='1ə2ə3')                   # CəLəC (latləḥəm)
        for p in PERSONS:                                                  # ʼat + s → ʼass (ʼassaʼala)
            o.add('ʼa11a2a3' + PERF_SUF[p], 'Perf', p, cons={1: 'DENT'}, variant='assim')
            for tam in ('Impf', 'Jus'):
                o.add(derived_prefix('', p) + '11ə2ə3' + SUF[p], tam, p, cons={1: 'DENT'}, variant='assim')
    elif typ in ('C', 'D'):
        return strong3(typ, deriv)
    return o


# ================================================================ final laryngal (§ 5.4.3)
def fin_lar(typ, deriv):
    o = _Out(typ, 3, deriv)

    def suffixed(stem_s, p, tam, prefix, allow_trans=True, imp=False):
        s = u_for_o(IMP_SUF[p] if imp else SUF[p])
        if not s:
            return
        o.add(prefix + stem_s + s, tam, p)
        if allow_trans and s in ('i', 'u') and stem_s.endswith('ə3'):
            o.add(prefix + stem_s[:-2] + s + '3', tam, p, variant='transp')     # təballiʿ, təbluʿ

    if deriv == 'Base' and typ == 'A':
        for p in PERSONS:
            o.add(('1a23a' if p in CONS_SUF else '1a23') + PERF_SUF[p], 'Perf', p)   # balʿako, balʿa
            o.add(('1a2a3a' if p in CONS_SUF else '1a2a3') + PERF_SUF[p], 'Perf', p,   # corpus: መጸአ beside መጽአ
                  variant='fin-lar-a')
            if SUF[p]:
                suffixed('1a22ə3', p, 'Impf', PRE_BASE[p])
                suffixed('12ə3', p, 'Jus', jus_pre(p))
            else:
                o.add(PRE_BASE[p] + '1a22ə3', 'Impf', p)
                o.add(jus_pre(p) + '12a3', 'Jus', p)
        for p in IMP_PERSONS:
            if IMP_SUF[p]:
                o.add('1ə23' + u_for_o(IMP_SUF[p]), 'Imp', p)                   # bəlʿi, bəlʿu, bəlʿa
                if IMP_SUF[p] in ('i', 'o'):
                    o.add('1ə2' + ('i' if p == '2sf' else 'u') + '3', 'Imp', p, variant='transp')
                    o.add('12' + ('i' if p == '2sf' else 'u') + '3', 'Imp', p, variant='transp')   # nəsuʼ ~ nsuʼ
                o.add('1ə2ə3' + u_for_o(IMP_SUF[p]), 'Imp', p, variant='schwa')
            else:
                o.add('1ə2a3', 'Imp', p)
        return o
    P = {('B', 'Base'): ('1a22ə3', '1a22ə3', '1a22ə3', ''),
         ('C', 'Base'): ('1ā2ə3', '1ā2ə3', '1ā2ə3', ''),
         ('D', 'Base'): ('1a2ā2ə3', '1a2ā2ə3', '1a2ā2ə3', ''),
         ('A', 'tə'): ('1a22ə3', '1a22a3', '1a22ə3', 'tə'), ('B', 'tə'): ('1a22ə3', '1a22a3', '1a22ə3', 'tə'),
         ('C', 'tə'): ('1ā2ə3', '1ā2a3', '1ā2ə3', 'tə'), ('D', 'tə'): ('1a2ā2ə3', '1a2ā2a3', '1a2ā2ə3', 'tə'),
         ('B', 'ʼa'): ('1a22ə3', '1a22ə3', '1a22ə3', 'ʼa'), ('C', 'ʼa'): ('1ā2ə3', '1ā2ə3', '1ā2ə3', 'ʼa'),
         ('B', 'ʼat'): ('1a22ə3', '1a22ə3', '1a22ə3', 'ʼat'), ('C', 'ʼat'): ('1ā2ə3', '1ā2ə3', '1ā2ə3', 'ʼat'),
         ('D', 'ʼat'): ('1a2ā2ə3', '1a2ā2ə3', '1a2ā2ə3', 'ʼat'),
         ('A', 'ʼatta'): ('12ə3', '12ə3', '12ə3', 'ʼatta'), ('B', 'ʼatta'): ('1a22ə3', '1a22ə3', '1a22ə3', 'ʼatta'),
         ('A', 'ʼa'): ('12ə3', None, None, 'ʼa')}
    if (typ, deriv) not in P:
        return o
    perf, ij, ij_s, head = P[(typ, deriv)]
    for p in PERSONS:
        o.add(head + perf + ('a' + PERF_SUF[p] if p in CONS_SUF else PERF_SUF[p]), 'Perf', p)
        if typ in ('C', 'D'):
            o.add(head + perf.replace('ə3', '3') + ('a' + PERF_SUF[p] if p in CONS_SUF else PERF_SUF[p]), 'Perf', p,
                  variant='schwa-drop')                                        # šārʿa, ʼatfarārha
            o.add(head + perf.replace('ə3', 'a3') + PERF_SUF[p], 'Perf', p, variant='schwa-a')   # sāraḥa
    if (typ, deriv) == ('A', 'ʼa'):                                           # ʼasməʿa: lasamməʿ / lasməʿ / ʼasməʿ
        for p in PERSONS:
            if SUF[p]:
                suffixed('1a22ə3', p, 'Impf', derived_prefix('', p))
                suffixed('12ə3', p, 'Jus', derived_prefix('', p))
            else:
                o.add(derived_prefix('', p) + '1a22ə3', 'Impf', p)
                o.add(derived_prefix('', p) + '12ə3', 'Jus', p)
        for p in IMP_PERSONS:
            o.add('ʼa12ə3' + u_for_o(IMP_SUF[p]), 'Imp', p)
        return o
    pre = {'': lambda p: (PRE_BASE[p], jus_pre(p)), 'tə': lambda p: (tə_prefix(p), tə_prefix(p)),
           'ʼa': lambda p: (derived_prefix('', p),) * 2, 'ʼat': lambda p: (derived_prefix('t', p),) * 2,
           'ʼatta': lambda p: (derived_prefix('tta', p),) * 2}[head]
    for p in PERSONS:
        pi, pj = pre(p)
        for tam, px in (('Impf', pi), ('Jus', pj)):
            if SUF[p]:
                suffixed(ij_s, p, tam, px, allow_trans=(typ != 'C'))
                if typ == 'C':
                    o.add(px + ij_s[:-2] + '3' + u_for_o(SUF[p]), tam, p, variant='schwa-drop')
            else:
                o.add(px + ij, tam, p)
    for p in IMP_PERSONS:
        if IMP_SUF[p]:
            suffixed(ij_s, p, 'Imp', head, allow_trans=(typ != 'C'), imp=True)
            if typ == 'C':
                o.add(head + ij_s[:-2] + '3' + u_for_o(IMP_SUF[p]), 'Imp', p, variant='schwa-drop')
        else:
            o.add(head + ij, 'Imp', p)
    return o


# ================================================================ medial semivowel (§ 5.5.2)
def hollow(typ, deriv, sv, init_lar=False):
    """sv = 'w' or 'y'.  Type A and ʼa-A are biradical (perfect, jussive, imperative)."""
    V = {'w': ('o', 'u'), 'y': ('e', 'i')}[sv]
    o = _Out(typ, 3, deriv)
    if typ == 'A' and deriv == 'Base':
        for p in PERSONS:
            o.add(('1' + V[0] + '3' if p.startswith('3') else '1ə3') + PERF_SUF[p], 'Perf', p)   # geda / gədko
            o.add(PRE_BASE[p] + ('1a23' if SUF[p] else '1a2ə3') + SUF[p], 'Impf', p)              # ləgayəd
            if not SUF[p]:
                o.add(PRE_BASE[p] + '1a23', 'Impf', p, variant='schwa-drop')                    # ʼəgayd
            if sv == 'w':                                       # mota, ṣoma: imperfect with y (§ 5.5.2.1)
                o.add(PRE_BASE[p] + ('1ay3' if SUF[p] else '1ayə3') + SUF[p], 'Impf', p, variant='w-y')
            jp = jus_pre(p) if init_lar else i_pre(p)           # ligid; ləḥis with an initial laryngal
            o.add(jp + '1' + V[1] + '3' + SUF[p], 'Jus', p)
        for p in IMP_PERSONS:
            o.add('1' + V[1] + '3' + IMP_SUF[p], 'Imp', p)
        if init_lar and sv == 'y':                              # haba: biradical stem hab (§ 5.6.6)
            for p in PERSONS:
                o.add('1a3' + PERF_SUF[p], 'Perf', p, variant='haba')
                o.add(jus_pre(p) + '1a3' + SUF[p], 'Jus', p, variant='haba')
            for p in IMP_PERSONS:
                o.add('1a3' + IMP_SUF[p], 'Imp', p, variant='haba')
    elif typ == 'A' and deriv == 'ʼa':
        for p in PERSONS:
            o.add('ʼa' + ('1' + V[0] + '3' if p.startswith('3') else '1ə3') + PERF_SUF[p], 'Perf', p)
            o.add(derived_prefix('', p) + ('1a23' if SUF[p] else '1a2ə3') + SUF[p], 'Impf', p)
            if sv == 'w':
                o.add(derived_prefix('', p) + ('1ay3' if SUF[p] else '1ayə3') + SUF[p], 'Impf', p, variant='w-y')
            o.add(derived_prefix('', p) + '1' + V[1] + '3' + SUF[p], 'Jus', p)
        for p in IMP_PERSONS:
            o.add('ʼa1' + V[1] + '3' + IMP_SUF[p], 'Imp', p)
    else:
        o = strong3(typ, deriv, nogem2=True)                    # w/y consonantal, not geminated
    return o


# ================================================================ final semivowel (§ 5.5.3–5.5.4, 5.6)
def final_sv(typ, deriv, init_sv=False, med='C'):
    """med: class of R2 ('C'; 'L' for C-L-SV like raʼa; 'w'/'y' for medial + final semivowel)."""
    o = _Out(typ, 3, deriv)
    g = '2' if med in ('w', 'y', 'L') else '22'                 # medial semivowel/laryngal never geminated

    def perf(stem12, stem3, head=''):
        for p in PERSONS:
            if p in SV_PERF:
                o.add(head + stem3 + SV_PERF[p], 'Perf', p)
            else:
                o.add(head + stem12 + 'e' + PERF_SUF[p], 'Perf', p)

    if typ == 'A' and deriv == 'Base':
        if med == 'L':                                          # raʼa, rəʼet, rəʼena (§ 5.6.1)
            for p in PERSONS:
                if p in ('3sm', '3pm', '3pf'):
                    o.add('1a2' + SV_PERF[p], 'Perf', p)
                elif p == '3sf':
                    o.add('1ə2et', 'Perf', p)
                else:
                    o.add('1ə2e' + PERF_SUF[p], 'Perf', p)
        else:
            perf('1a2', '1a2')
        for p in PERSONS:
            istem = '12' if med == 'L' else ('1a2' if SV_IMPF[p] == 'ya' else '1a' + g)
            o.add(PRE_BASE[p] + istem + SV_IMPF[p], 'Impf', p)
            if SV_IMPF[p] == 'ya' and med != 'L':
                o.add(PRE_BASE[p] + '1ay2a', 'Impf', p, variant='transp')          # təwadya / təwayda
            if init_sv and med != 'L':
                o.add(i_pre(p) + '2' + SV_JUSS[p], 'Jus', p)                     # ʼide, tiday, lidaw (wada)
            else:
                o.add(jus_pre(p) + '12' + SV_JUSS[p], 'Jus', p)
        for p in IMP_PERSONS:
            if med == 'L':
                o.add(('1ə2e' if p == '2sm' else '1a2' + SV_IMP[p]), 'Imp', p)
            elif init_sv:
                o.add('2' + SV_IMP[p], 'Imp', p)                                  # de, day
                o.add('1ə2' + SV_IMP[p], 'Imp', p, variant='short-imp')          # wəde, wəday
            else:
                o.add('1ə2' + SV_IMP[p], 'Imp', p)
                if p == '2sm':
                    o.add('1e2e', 'Imp', p, variant='haba')                       # ḥeye (§ 5.6.3)
        return o
    stems = {('B', 'Base'): ('1a' + g, ''), ('C', 'Base'): ('1ā2', ''), ('D', 'Base'): ('1a2ā2', ''),
             ('A', 'tə'): ('1a' + g, 'tə'), ('B', 'tə'): ('1a' + g, 'tə'), ('C', 'tə'): ('1ā2', 'tə'),
             ('D', 'tə'): ('1a2ā2', 'tə'), ('A', 'ʼa'): ('12', 'ʼa'), ('B', 'ʼa'): ('1a' + g, 'ʼa'),
             ('C', 'ʼa'): ('1ā2', 'ʼa'), ('B', 'ʼat'): ('1a' + g, 'ʼat'), ('C', 'ʼat'): ('1ā2', 'ʼat'),
             ('D', 'ʼat'): ('1a2ā2', 'ʼat'), ('A', 'ʼatta'): ('12', 'ʼatta'), ('C', 'ʼatta'): ('1ā2', 'ʼatta'),
             ('B', 'ʼatta'): ('1a' + g, 'ʼatta')}
    if (typ, deriv) not in stems:
        return o
    s, head = stems[(typ, deriv)]
    perf(s, s, head)
    if head == 'ʼat':                                                       # ʼaddāla (t assimilated)
        for p in PERSONS:
            o.add('ʼa1' + s + (SV_PERF[p] if p in SV_PERF else 'e' + PERF_SUF[p]), 'Perf', p, cons={1: 'DENT'}, variant='assim')
    if deriv == 'tə':
        for p in PERSONS:
            for tam in ('Impf', 'Jus'):
                st = '1ə2' if med == 'L' and typ in ('A', 'B') else s             # lətrəʼe (§ 5.6.1)
                o.add(tə_prefix(p) + st + SV_JUSS[p], tam, p)                   # tə-: jussive endings
        if med == 'L' and typ in ('A', 'B'):
            perf('1ā2', '1ā2', 'tə')                                             # tərāʼa
        for p in IMP_PERSONS:
            o.add('tə' + s + SV_IMP[p], 'Imp', p)
    elif (typ, deriv) == ('A', 'ʼa'):
        for p in PERSONS:
            ist = '12' if med == 'L' else ('1a2' if med in ('w', 'y') or SV_IMPF[p] == 'ya' else '1a22')
            o.add(derived_prefix('', p) + ist + SV_IMPF[p], 'Impf', p)          # labadde, ladawe, larʼe
            o.add(derived_prefix('', p) + '12' + SV_JUSS[p], 'Jus', p)          # labde, ladwe
        for p in IMP_PERSONS:
            o.add('ʼa12' + SV_IMP[p], 'Imp', p)
    else:
        hd = {'': '', 'ʼa': '', 'ʼat': 't', 'ʼatta': 'tta'}[head]
        for p in PERSONS:
            px = PRE_BASE[p] if head == '' else derived_prefix(hd, p)
            st = s[:-1] if (SV_IMPF[p] == 'ya' and s.endswith('22')) else s
            o.add(px + st + SV_IMPF[p], 'Impf', p)                                 # non-tə: imperfect endings
            o.add((jus_pre(p) if head == '' else px) + st + SV_IMPF[p], 'Jus', p)
        for p in IMP_PERSONS:
            o.add(head + s + SV_IMP_I[p], 'Imp', p)
    return o


# ================================================================ C-y-L (baʼa, § 5.6.4)
def cyl(typ, deriv):
    o = _Out(typ, 3, deriv)
    if typ == 'A' and deriv == 'Base':
        for p in PERSONS:
            o.add('1a3' + PERF_SUF[p], 'Perf', p)                                   # biradical perfect
            o.add(PRE_BASE[p] + ('1a23' if SUF[p] else '1a2ə3') + u_for_o(SUF[p]), 'Impf', p)
            for st in ('12a3', '1a3'):                                               # with / without medial y
                if SUF[p]:
                    o.add(i_pre(p) + st + u_for_o(SUF[p]), 'Jus', p)
                    if SUF[p] in ('i', 'o'):
                        o.add(i_pre(p) + st[:-2] + ('i' if SUF[p] == 'i' else 'u') + '3', 'Jus', p, variant='transp')
                else:
                    o.add(i_pre(p) + st, 'Jus', p)
            if p == '1sg':
                o.add('ʼə12a3', 'Jus', p)
        for p in IMP_PERSONS:
            s = IMP_SUF[p]
            if s:
                o.add('1ə23' + u_for_o(s), 'Imp', p)                                # bəyʼi
                o.add('1ə3' + u_for_o(s), 'Imp', p)                                 # bəʼi
                if s in ('i', 'o'):
                    v = 'i' if s == 'i' else 'u'
                    o.add('1ə2' + v + '3', 'Imp', p, variant='transp')              # bəyiʼ
                    o.add('1' + v + '3', 'Imp', p, variant='transp')                # biʼ
            else:
                o.add('1ə2a3', 'Imp', p)                                            # bəyaʼ
                o.add('1a3', 'Imp', p)                                              # baʼ
    elif typ == 'A' and deriv == 'ʼa':
        for p in PERSONS:
            o.add('ʼa13' + PERF_SUF[p], 'Perf', p)                                 # ʼabʼa
    return o


# ================================================================ initial-laryngal adjustments (§ 5.4.1)
def lar_initial(cells_, d='1'):
    """Rewrite templates whose first stem radical (slot d) is a laryngal."""
    out = []
    for c in cells_:
        t = c.template
        if t.startswith('ʼə' + d):
            rest = t[2:]
            if c.tags['TAM'] == 'Jus' and len(rest) > 1 and rest[1].isdigit():
                t = d + 'i' + rest[1:]                                    # ḥiṣab, ḥize, ḥiye
            else:
                t = rest                                                  # ḥaṣṣəb, ʿaddəm, ḥaye
                if '22' in t and c.tags['TAM'] == 'Impf':
                    out.append(Cell(t.replace('22', '2', 1), c.tags, c.constraints, 'degem'))   # ḥaze
        elif t.startswith('ʼən' + d):
            t = 'na' + t[3:]                                              # naḥaṣṣəb
        t2 = re.sub(r'^([tlnʼ])ə' + d + '(?=[aā])', r'\1a' + d, t)        # taḥaṣṣəb, laʼambət, tahayaba
        t2 = re.sub(r'ə' + d + r'(?=\d)', 'ə' + d + 'ə', t2)              # təḥəṣab, ləḥəze (VLCV → VLəCV)
        out.append(Cell(t2, c.tags, c.constraints, c.variant))
        if t2 != t and re.match(r'^tə' + d + '[aā]', t) and c.tags['TAM'] == 'Impf':
            out.append(Cell('t' + t[2:], c.tags, c.constraints, 'lar-elide'))   # tḥaṣṣəb
    return out


# ================================================================ triradical dispatcher
def cells3(typ, deriv, sh):
    r1, r2, r3 = sh
    if r1 == 'L' and deriv in ('ʼa', 'ʼatta'):
        return []                                                         # § 5.4.1 (1b), (1c)
    if r2 == 'L' and (typ == 'B' or deriv == 'ʼatta'):
        return []                                                         # § 5.4.2 (a)
    if r3 == 'S':
        o = final_sv(typ, deriv, init_sv=(r1 == 'S'), med=('L' if r2 == 'L' else (r2 if r2 in ('w', 'y') else 'C')))
        if r1 == 'L' and typ == 'A' and deriv == 'ʼat':                   # ʼatʿasa, ʼathada
            o = _Out('A', 3, 'ʼat')
            for p in PERSONS:
                o.add('ʼat1a2' + (SV_PERF[p] if p in SV_PERF else 'e' + PERF_SUF[p]), 'Perf', p)
                for tam in ('Impf', 'Jus'):
                    o.add(derived_prefix('t', p) + '1a2' + SV_IMPF[p], tam, p)
    elif r2 in ('w', 'y') and r3 == 'L':
        o = cyl(typ, deriv) if (r2 == 'y' and typ == 'A') else strong3(typ, deriv, nogem2=True)
    elif r2 in ('w', 'y'):
        o = hollow(typ, deriv, r2, init_lar=(r1 == 'L'))
        if r1 == 'L' and typ == 'A' and deriv == 'ʼat':
            o = at_A(_Out('A', 3, 'ʼat'))                                 # ʼathayaba, lathayəb
    elif r2 == 'L':
        o = med_lar(typ, deriv)
        if r1 == 'S' and typ == 'A' and deriv == 'Base':                # ḥada, laḥad; ʿala (§ 5.6.5, 5.7.1)
            extra = _Out('A', 3, 'Base')
            for p in PERSONS:
                extra.add('2a3' + PERF_SUF[p], 'Perf', p, variant='biradical')
                extra.add(jus_pre(p) + '2a3' + SUF[p], 'Jus', p, variant='biradical')
            o.extend(lar_initial(extra, d='2'))
    elif r3 == 'L':
        o = fin_lar(typ, deriv)
    else:
        o = strong3(typ, deriv, init_sv=(r1 == 'S'))
        if r1 == 'L' and typ == 'A' and deriv == 'ʼat':
            o = at_A(_Out('A', 3, 'ʼat'))                                 # ʼatḥalafa, latḥaləf
        if (r1, r2, r3) == ('C', 'C', 'C') and typ == 'A' and deriv in ('tə', 'ʼat'):
            head = 'tə' if deriv == 'tə' else 'ʼat'                      # doubled roots (§ 5.8)
            for p in PERSONS:
                o.add(head + ('1a22' if p.startswith('3') else '1a2a2') + PERF_SUF[p], 'Perf', p,
                      cons={3: 'SAME2'}, variant='doubled')
    o = list(o) + attach_objects(o, fin={'L': 'L', 'S': 'S'}.get(r3, ''))
    if r1 == 'L':
        o = lar_initial(o)
    if r1 == 'L' and deriv == 'ʼasta' and typ == 'A':               # ʼastahala < Ar. istaʼhala: ʼ elided
        for p in PERSONS:
            o.append(Cell('ʼasta2a3' + PERF_SUF[p], _tags('A', 3, 'ʼasta', 'Perf', p), {1: 'GLOT'}))
    return o


# ================================================================ quadriradicals (§ 5.9)
def cells4(typ, deriv, sh):
    r1, r2, r3, r4 = sh
    if typ not in ('A', 'C'):
        return []
    heads = {'Base': None, 'tə': None, 'ʼa': '', 'ʼat': 't', 'ʼatta': 'tta', 'ʼan': 'n', 'ʼas': 's', 'ʼattan': 'ttan', 'ʼattas': 'ttas'}
    if deriv not in heads or (r1 == 'L' and deriv in ('ʼa', 'ʼatta')):
        return []
    o = _Out(typ, 4, deriv)
    sv, lar4, ov = r4 == 'S', r4 == 'L', r2 in ('wo', 'ye')
    if ov:
        if typ == 'C':
            return []                                                     # w/y keep their shape in C (§ 5.9.2)
        v = 'e' if r2 == 'ye' else 'ə'                                    # lədereb, laserer / ləgorət
        perf, ij, ij_s = ('123', '123', '123') if sv else ('123a4', '123' + v + '4', '123' + v + '4')
    elif typ == 'A':
        perf, ij, ij_s = ('1a23', '1a23', '1a23') if sv else ('1a23a4', '1a23ə4', '1a23ə4')
    else:
        perf, ij, ij_s = ('1a2ā3', '1a2ā3', '1a2ā3') if sv else ('1a2ā3a4', '1a2ā3ə4', '1a2ā34')
    if lar4:
        perf = perf[:-2] + 'ə4'                                           # qarqəḥa
    if r2 == 'L':                                                         # č̣aʿarara, təmahalala
        perf, ij, ij_s = (s.replace('1a23', '1a2a3', 1) for s in (perf, ij, ij_s))

    def end_perf(p):
        if sv:
            return SV_PERF[p] if p in SV_PERF else 'e' + PERF_SUF[p]
        return 'a' + PERF_SUF[p] if lar4 and p in CONS_SUF else PERF_SUF[p]

    def ij_of(p, s=None):
        s = SUF[p] if s is None else s
        return ij if (sv or not s) else ij_s

    if deriv == 'Base':
        for p in PERSONS:
            o.add(perf + end_perf(p), 'Perf', p)
            for tam, px in (('Impf', PRE_BASE[p]), ('Jus', jus_pre(p))):
                end = SV_IMPF[p] if sv else SUF[p]
                o.add(px + ij_of(p) + end, tam, p)
                if r2 == 'L' and px.endswith('ə'):
                    o.add(px[:-1] + 'a' + ij_of(p) + end, tam, p, variant='lar-a')       # lač̣aʿarər
                if sv and SV_IMPF[p] == 'ya':
                    o.add(px + ij[:-1] + 'y' + ij[-1] + 'a', tam, p, variant='transp')   # goyla
        for p in IMP_PERSONS:
            o.add(ij_of(p, IMP_SUF[p]) + (SV_IMP_I[p] if sv else IMP_SUF[p]), 'Imp', p)
    elif deriv == 'tə':
        for p in PERSONS:
            o.add('tə' + perf + end_perf(p), 'Perf', p)
            for tam in ('Impf', 'Jus'):
                pre = tə_prefix(p)
                tail = perf + (SV_JUSS[p] if sv else SUF[p])
                o.add(pre + tail, tam, p)
                o.add(pre[:-1] + '1' + tail, tam, p, cons={1: 'DENT'}, variant='assim')
        for p in IMP_PERSONS:
            o.add('tə' + perf + (SV_IMP[p] if sv else IMP_SUF[p]), 'Imp', p)
    else:
        h = heads[deriv]
        pf, i1, i2 = perf, ij, ij_s
        if deriv == 'ʼa' and r2 == 'L':                                   # ʼamʿadaga: VLCV → LVCV (§ 5.9.1 fn 2)
            pf, i1, i2 = (s.replace('1a2a3', '12a3', 1) for s in (pf, i1, i2))
        for p in PERSONS:
            o.add('ʼa' + h + pf + end_perf(p), 'Perf', p)
            for tam in ('Impf', 'Jus'):
                o.add(derived_prefix(h, p) + (i1 if (sv or not SUF[p]) else i2) + (SV_IMPF[p] if sv else SUF[p]), tam, p)
        for p in IMP_PERSONS:
            o.add('ʼa' + h + (i1 if (sv or not IMP_SUF[p]) else i2) + (SV_IMP_I[p] if sv else IMP_SUF[p]), 'Imp', p)
    o = list(o) + attach_objects(o, fin={'L': 'L', 'S': 'S'}.get(r4, ''))
    if r1 == 'L':
        o = lar_initial(o)
    return o


# ================================================================ quinqueradicals (§ 5.10)
def cells5(typ, deriv, sh):
    r1, r2, r3, r4, r5 = sh
    if typ not in ('A', 'C') or deriv not in ('Base', 'ʼa', 'ʼat', 'ʼatta') or (r1 == 'L' and deriv in ('ʼa', 'ʼatta')):
        return []
    sv = r5 == 'S'
    o = _Out(typ, 5, deriv)
    if r3 == 'wo':                                                        # ḥanobaza, ʼagdoda (§ 5.10.1 (2))
        if typ == 'C':
            return []
        b = '1a23' if deriv == 'Base' else '123'
        perf, ij, ij_s = (b + '4', b + '4', b + '4') if sv else (b + '4a5', b + '4ə5', b + '4ə5')
    elif typ == 'A':
        perf, ij, ij_s = ('12a34a5', '12a34ə5', '12a34ə5') if deriv == 'ʼa' else ('1a2a34a5', '1a2a34ə5', '1a2a34ə5')
    else:
        perf, ij, ij_s = '1a2a3ā4a5', '1a2a3ā4ə5', '1a2a3ā45'
    head = {'Base': '', 'ʼa': 'ʼa', 'ʼat': 'ʼat', 'ʼatta': 'ʼatta'}[deriv]
    for p in PERSONS:
        if sv:
            o.add(head + perf + ({'3sm': 'a', '3sf': 'at', '3pm': 'aw', '3pf': 'aya'}[p] if p.startswith('3') else 'e' + PERF_SUF[p]),
                  'Perf', p)
        else:
            o.add(head + perf + PERF_SUF[p], 'Perf', p)
        for tam, px in (('Impf', PRE_BASE[p] if deriv == 'Base' else derived_prefix(head[2:], p)),
                        ('Jus', jus_pre(p) if deriv == 'Base' else derived_prefix(head[2:], p))):
            o.add(px + (ij if (sv or not SUF[p]) else ij_s) + (SV_IMPF[p] if sv else SUF[p]), tam, p)
    for p in IMP_PERSONS:
        o.add(head + (ij if (sv or not IMP_SUF[p]) else ij_s) + (SV_IMP_I[p] if sv else IMP_SUF[p]), 'Imp', p)
    o = list(o) + attach_objects(o, fin={'L': 'L', 'S': 'S'}.get(r5, ''))
    if r1 == 'L':
        o = lar_initial(o)
    return o


# ================================================================ irregular verbs listed in full (§ 5.7)
IRREGULAR = {
    # bela 'to say' (root b-h-l), § 5.7.2; slot 1 = b, 3 = l, the h never surfaces in type A
    ('b-h-l', 'A', 'Base'): {
        'Perf': {'1sg': ['ʼə1e'], '2sm': ['tə1e', 'te3ka'], '2sf': ['tə1ay', 'te3ki'], '3sm': ['1e3a'],
                 '3sf': ['1e3at', 'tə1e'], '1pl': ['ʼən1e'], '2pm': ['tə1aw', 'te3kum'], '2pf': ['tə1aya', 'te3kən'],
                 '3pm': ['1e3aw'], '3pf': ['1e3aya']},
        'Impf': {'1sg': ['ʼə1ə3'], '2sm': ['tə1ə3'], '2sf': ['tə13i'], '3sm': ['lə1ə3'], '3sf': ['tə1ə3'],
                 '1pl': ['nə1ə3', 'ʼən1ə3'], '2pm': ['tə13o'], '2pf': ['tə13a'], '3pm': ['lə13o'], '3pf': ['lə13a']},
        'Jus': {'1sg': ['ʼi1a3'], '2sm': ['ti1a3'], '2sf': ['ti1a3i'], '3sm': ['li1a3'], '3sf': ['ti1a3'],
                '1pl': ['ni1a3'], '2pm': ['ti1a3o'], '2pf': ['ti1a3a'], '3pm': ['li1a3o'], '3pf': ['li1a3a']},
        'Imp': {'2sm': ['1a3'], '2sf': ['1a3i'], '2pm': ['1a3o'], '2pf': ['1a3a']}},
    ('b-h-l', 'A', 'ʼa'): {'Perf': {p: ['ʼa1a3' + PERF_SUF[p]] for p in PERSONS},
                           'Impf': {p: [derived_prefix('', p) + ('13' if SUF[p] else '1ə3') + SUF[p]] for p in PERSONS},
                           'Jus': {p: [derived_prefix('', p) + ('13' if SUF[p] else '1ə3') + SUF[p]] for p in PERSONS}},
    ('b-h-l', 'A', 'ʼatta'): {'Perf': {p: ['ʼatta1a3' + PERF_SUF[p]] for p in PERSONS},
                              'Impf': {p: [derived_prefix('tta', p) + ('13' if SUF[p] else '1ə3') + SUF[p]] for p in PERSONS},
                              'Jus': {p: [derived_prefix('tta', p) + ('13' if SUF[p] else '1ə3') + SUF[p]] for p in PERSONS}},
    # halla 'to be, exist' (type B per Raz § 5.2)
    # Raz's text has halleko, halleka, lahallet (§ 5.11, 6.9); the corpus agrees (ሀሌኮ 425, ሀሌት 3162 vs ሀለት 19)
    ('h-l-l', 'B', 'Base'): {'Perf': {p: (['1a22' + PERF_SUF[p]] if p in ('3sm', '3pm', '3pf') else
                                          ['1a22et', '1a22at'] if p == '3sf' else
                                          ['1a22e' + PERF_SUF[p].lstrip('ə'), '1a22ə' + PERF_SUF[p]]) for p in PERSONS}},
}


def irregular_cells():
    """(root, Cell) pairs for the irregular verbs; templates are realised into literal words."""
    from .objects import V_C, OBJ_TAG
    out = []
    for (root, typ, deriv), tams in IRREGULAR.items():
        rad = len(root.split('-'))
        rl = root.split('-')
        cs = _Out(typ, rad, deriv)
        for tam, persons in tams.items():
            for p, forms in persons.items():
                for f in forms:
                    cs.add(f, tam, p)
        allc = list(cs)
        if root == 'b-h-l':
            allc += attach_objects(cs)
            if deriv == 'Base':                     # ʼəbello, təbello, bello: e-forms + ll + o (§ 5.12.6)
                for c in cs:
                    if c.tags['TAM'] == 'Perf' and (c.template.endswith('1e') or c.template == '1e3a'):
                        stem = c.template if c.template.endswith('1e') else '1e'
                        for obj in ('3sm', '3sf', '3pm', '3pf'):
                            allc.append(Cell(stem + '33' + V_C[obj], dict(c.tags, Obj=OBJ_TAG[obj])))
                for subj, link, vset in (('2sm', 'te33', 'c'), ('2sf', 'te3y', 'c'), ('2pm', 'te3w', 'c'), ('2pf', 'te3yah', 'h')):
                    for obj in ('3sm', '3sf', '3pm', '3pf'):          # tello, telyo, telwo, telyahu (§ 5.12.6 fn)
                        v = V_C[obj] if vset == 'c' else {'3sm': 'u', '3sf': 'a', '3pm': 'om', '3pf': 'an'}[obj]
                        allc.append(Cell(link + v, dict(_tags('A', 3, 'Base', 'Perf', subj), Obj=OBJ_TAG[obj])))
        if root == 'h-l-l':                          # corpus ህለ / ህሌት beside ሀለ / ሀሌት (həlla; 21k vs 26k tokens)
            allc += [Cell('1ə' + c.template[2:], c.tags) for c in allc if c.template.startswith('1a')]
        for c in allc:
            word = realize(c.template, rl)
            out.append((root, Cell(word, c.tags)))
            if c.tags['TAM'] != 'Imp':
                out.append((root, Cell('ʼi' + word, dict(c.tags, Neg='Yes'))))
                if word.startswith('ʼə'):
                    out.append((root, Cell('ʼi' + word[2:], dict(c.tags, Neg='Yes'))))
    return out


# ================================================================ negation, colloquial, entry point
def _neg_colloq(out, deriv):
    neg = [Cell('ʼi' + c.template, dict(c.tags, Neg='Yes'), c.constraints, c.variant)
           for c in out if c.tags['TAM'] in ('Perf', 'Impf', 'Jus')]
    # corpus: ʼi + ʼə- (1sg) contracts: ኢቀድር 1,508 vs ኢእቀድር 32
    neg += [Cell('ʼi' + c.template[2:], dict(c.tags, Neg='Yes'), c.constraints,
                 '+'.join(x for x in (c.variant, 'neg-contract') if x))
            for c in out if c.tags['TAM'] in ('Impf', 'Jus') and c.template.startswith('ʼə')]
    col = []
    if deriv == 'Base':
        for c in out:
            if c.tags['TAM'] != 'Impf':
                continue
            if c.tags['Subj'][0] == '1':
                col.append(Cell(c.template, dict(c.tags, Colloq='Yes'), c.constraints, '+'.join(x for x in (c.variant, 'colloq') if x)))
            else:
                m = re.match(r'^(tə|lə|ta|la|t)(?=\d)', c.template)
                if m:
                    col.append(Cell(c.template[m.end():], dict(c.tags, Colloq='Yes'), c.constraints, '+'.join(x for x in (c.variant, 'colloq') if x)))
    return list(out) + neg + col


A_DERIVS = ('ʼa', 'ʼat', 'ʼatta', 'ʼan', 'ʼas', 'ʼattan', 'ʼattas', 'ʼasta')


def _a_written(out, deriv):
    """Modern spelling keeps the ʼa of causative prefixes after the person prefix:
    Raz lafgər / latḥazze are usually written ለአፍግር / ለአትሐዜ (laʼafgər, laʼatḥazze) in the corpus."""
    if deriv not in A_DERIVS:
        return out
    extra = []
    for c in out:
        if c.tags['TAM'] in ('Impf', 'Jus') and re.match(r'^[ltn]a', c.template) and not c.template.startswith('na1'):
            extra.append(Cell(c.template[0] + 'aʼa' + c.template[2:], c.tags, c.constraints,
                              '+'.join(x for x in (c.variant, 'a-written') if x)))
    return list(out) + extra


def cells(rad, typ, deriv, shape=None):
    shape = tuple(shape or ('C',) * rad)
    if rad == 3:
        out = cells3(typ, deriv, shape)
    elif rad == 4:
        out = cells4(typ, deriv, shape)
    else:
        out = cells5(typ, deriv, shape)
    return _neg_colloq(_a_written(out, deriv), deriv)


TYPES = {3: ['A', 'B', 'C', 'D'], 4: ['A', 'C'], 5: ['A', 'C']}
DERIVS = {3: ['Base', 'tə', 'ʼa', 'ʼat', 'ʼatta', 'ʼasta'],
          4: ['Base', 'tə', 'ʼa', 'ʼat', 'ʼatta', 'ʼan', 'ʼas', 'ʼattan', 'ʼattas'],
          5: ['Base', 'ʼa', 'ʼat', 'ʼatta']}

SHAPES = {
    3: [(a, b, c) for a in ('C', 'L', 'S') for b in ('C', 'L', 'w', 'y') for c in ('C', 'L', 'S')],
    4: [(a, b, 'ANY', d) for a in ('N', 'L') for b in ('N', 'L', 'wo', 'ye') for d in ('C', 'L', 'S')],
    5: [(a, 'ANY', c, 'ANY', e) for a in ('N', 'L') for c in ('ANY', 'wo') for e in ('C', 'L', 'S')],
}


# ================================================================ deverbal nominals (§ 2.7)
NOMINAL_TAMS = ('PartAct', 'PartPass', 'Agent', 'Inf', 'Instr')
_GN = {'m': '3sm', 'f': '3sf', 'mp': '3pm', 'fp': '3pf'}


def nominals3(typ, deriv, sh):
    """Participles, agent nouns, infinitives and instrument nouns of triradicals (Raz § 2.7.1-2.7.3).
    Gender/number are carried in Subj (3SgM, 3SgF, 3PlM, 3PlF)."""
    r1, r2, r3 = sh
    hollow = r2 in ('w', 'y')
    if hollow and (typ, deriv) != ('A', 'Base'):
        return []
    o = []

    def add(tam, gn, tpl, w=''):
        if hollow:                                   # medial semivowel kept as a consonant (ḥāyəs, ḥəwuz)
            w = '+'.join(x for x in (w, 'nom-hollow') if x)
        o.append(Cell(tpl, _tags(typ, 3, deriv, tam, _GN[gn]), {}, w))

    S3 = r3 == 'S'
    if (typ, deriv) == ('A', 'Base'):
        # active participle qātəl (§ 2.7.1 a i); medial laryngal: səʼən; final semivowel: wāqi
        if r2 == 'L':
            add('PartAct', 'm', '1ə2ə3', 'nom'); add('PartAct', 'f', '1ə23at', 'nom')
        else:
            # qātəl is spelled like the prefixless imperfect qattəl (ፈግር); Raz's texts favour the imperfect
            add('PartAct', 'm', '1ā2i' if S3 else '1ā2ə3', 'nom2'); add('PartAct', 'f', '1ā23at', 'nom3')
        # qātlat / qātlāt are spelled like the perfect 3f.sg. qatlat when ā is not marked: heavier weights
        add('PartAct', 'mp', '1ā23ām', 'nom'); add('PartAct', 'fp', '1ā23āt', 'nom3')
        add('Agent', 'm', '1ā23āy', 'nom2'); add('Agent', 'f', '1ā23āyt', 'nom2'); add('Agent', 'mp', '1ā23at', 'nom3')
        # passive participle qətul (§ 2.7.1 b): qərub, qərbət/qərəb, qərubām; bəzuḥ, bəzḥām; ḥəruy, ḥərit
        add('PartPass', 'm', '1ə2u3', 'nom')
        if S3:
            add('PartPass', 'f', '1ə2it', 'nom')
        else:
            add('PartPass', 'f', '1ə23ət', 'nom'); add('PartPass', 'f', '1ə2ə3', 'nom2')
        if r3 == 'L':
            add('PartPass', 'mp', '1ə23ām', 'nom'); add('PartPass', 'fp', '1ə23āt', 'nom')
        else:
            add('PartPass', 'mp', '1ə2u3ām', 'nom'); add('PartPass', 'fp', '1ə2u3āt', 'nom')
        # infinitives qatil, qətlat, qətlo, məqtāl, qətle, qətlān (§ 2.7.2 a)
        add('Inf', 'm', '1a2i' if S3 else ('1ə2i3' if r2 == 'L' else '1a2i3'), 'nom2')
        for t in ('1ə23at', '1ə23o', 'mə12ā3', '1ə23e', '1ə23ān'):
            add('Inf', 'm', t, 'nom3')
        add('Instr', 'm', 'ma12a3i', 'nom3')                      # maktabi 'writing implement' (§ 2.7.3)
        if hollow:                                                 # *əy -> i, *əw -> u: ḥilat, ḥile, ḥilān (§ 2.7.2 a iii)
            v = 'i' if r2 == 'y' else 'u'
            for t in ('1' + v + '3at', '1' + v + '3e', '1' + v + '3ān', '1' + v + '3o'):
                add('Inf', 'm', t, 'nom2')
    elif deriv == 'Base' and typ in ('B', 'C'):
        g2 = '22' if typ == 'B' else '2'
        v1 = 'a' if typ == 'B' else 'ā'
        add('Agent', 'm', 'ma1' + v1 + '23āy', 'nom2'); add('Agent', 'f', 'ma1' + v1 + '23āyt', 'nom2')
        add('Agent', 'mp', 'ma1' + v1 + '23at', 'nom2')
        if typ == 'B':
            add('PartPass', 'm', '1ə22u3', 'nom'); add('PartPass', 'f', '1ə22ə3ət', 'nom')
            add('PartPass', 'f', '1ə22ə3', 'nom2')
            add('PartPass', 'mp', '1ə22u3ām', 'nom'); add('PartPass', 'fp', '1ə22u3āt', 'nom')
        else:
            add('PartPass', 'm', '1u2u3', 'nom'); add('PartPass', 'f', '1u23ət', 'nom')
            add('PartPass', 'mp', '1u2u3ām', 'nom'); add('PartPass', 'fp', '1u2u3āt', 'nom')
        add('Inf', 'm', '1' + v1 + g2 + 'a3ot', 'nom2')           # ʿallabot, sāqalot (§ 2.7.2 b i)
    elif deriv in ('ʼa', 'ʼat') and typ == 'A':
        pre = 'ʼa' if deriv == 'ʼa' else 'ʼat'
        add('Inf', 'm', pre + '12a3ot' if deriv == 'ʼa' else 'ʼa1' + '1a2a3ot', 'nom2')
        if deriv == 'ʼa':
            add('Agent', 'm', 'ma12ə3āy', 'nom2'); add('Agent', 'f', 'ma12ə3āyt', 'nom2')
            add('Agent', 'mp', 'ma12ə3at', 'nom2')
            add('PartPass', 'm', 'ʼə12u3', 'nom2')
    elif deriv == 'tə':
        g = '1a22ə3' if typ in ('A', 'B') else '1ā23'
        add('Agent', 'm', 'mat' + g + 'āy', 'nom2'); add('Agent', 'f', 'mat' + g + 'āyt', 'nom2')
        add('Agent', 'mp', 'mat' + g + 'at', 'nom2')
    return o


def all_cells(rad, shape=None):
    for typ in TYPES[rad]:
        for d in DERIVS[rad]:
            yield from cells(rad, typ, d, shape)
            if rad == 3:
                yield from nominals3(typ, d, tuple(shape or ('C',) * 3))


def realize(template, root, shape=None):
    """Fill a template with a root (list of radicals); o/e classes realise w/y as vowels."""
    out = template
    for k in range(len(root), 0, -1):
        c = root[k - 1]
        if shape and shape[k - 1] == 'wo':
            c = 'o'
        elif shape and shape[k - 1] == 'ye':
            c = 'e'
        out = out.replace(str(k), c)
    return out
