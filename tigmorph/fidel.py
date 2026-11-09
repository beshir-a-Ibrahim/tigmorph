"""Ge'ez (fidel) <-> consonant/vowel decomposition for Tigre.

Latin conventions follow Raz (1973): a u i ā e ə o; ʼ ʿ ḥ ṣ ṭ č̣ š ž ǧ.
A fidel letter = consonant + order (1..7).  Order 6 is ə *or* no vowel.
"""
import unicodedata

# Unicode name stem -> Raz consonant
_CONS = {
    'H': 'h', 'L': 'l', 'HH': 'ḥ', 'M': 'm', 'SZ': 's', 'R': 'r', 'S': 's', 'SH': 'š',
    'Q': 'q', 'QH': 'q', 'B': 'b', 'V': 'v', 'T': 't', 'C': 'č', 'X': 'ḥ', 'N': 'n',
    'NY': 'ñ', 'GLOTTAL': 'ʼ', 'K': 'k', 'KX': 'k', 'W': 'w', 'PHARYNGEAL': 'ʿ',
    'Z': 'z', 'ZH': 'ž', 'Y': 'y', 'D': 'd', 'DD': 'd', 'J': 'ǧ', 'G': 'g', 'GG': 'g',
    'TH': 'ṭ', 'CH': 'č̣', 'PH': 'p̣', 'TS': 'ṣ', 'TZ': 'ṣ', 'F': 'f', 'P': 'p',
}
_VOW = {'A': (1, 'a'), 'U': (2, 'u'), 'I': (3, 'i'), 'AA': (4, 'ā'), 'EE': (5, 'e'),
        'E': (6, 'ə'), 'O': (7, 'o')}
LARYNGALS = set('ʼʿhḥ')
SEMIVOWELS = set('wy')

# Raz consonant -> base code point (first order); used for Latin -> fidel
BASE = {'h': 0x1200, 'l': 0x1208, 'ḥ': 0x1210, 'm': 0x1218, 'r': 0x1228, 's': 0x1230,
        'š': 0x1238, 'q': 0x1240, 'b': 0x1260, 'v': 0x1268, 't': 0x1270, 'č': 0x1278,
        'n': 0x1290, 'ñ': 0x1298, 'ʼ': 0x12A0, 'k': 0x12A8, 'w': 0x12C8, 'ʿ': 0x12D0,
        'z': 0x12D8, 'ž': 0x12E0, 'y': 0x12E8, 'd': 0x12F0, 'ǧ': 0x1300, 'g': 0x1308,
        'ṭ': 0x1320, 'č̣': 0x1328, 'p̣': 0x1330, 'ṣ': 0x1338, 'f': 0x1348, 'p': 0x1350}
ORDER_OFFSET = {'a': 0, 'u': 1, 'i': 2, 'ā': 3, 'e': 4, 'ə': 5, '': 5, 'o': 6}


def decompose(ch):
    """Return (consonant, order, vowel, labialized) for one fidel char, or None."""
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return None
    if not name.startswith('ETHIOPIC SYLLABLE '):
        return None
    parts = name[len('ETHIOPIC SYLLABLE '):].split()
    if parts[0] in ('GLOTTAL', 'PHARYNGEAL'):
        cons, vow = parts[0], parts[1]
        lab = False
    else:
        syl = parts[-1]
        # split syllable into consonant stem + vowel by longest consonant prefix
        for k in sorted(_CONS, key=len, reverse=True):
            if not syl.startswith(k):
                continue
            rest = syl[len(k):]
            if rest in _VOW:
                cons, vow, lab = k, rest, False
                break
            if rest.startswith('W') and rest[1:] in _VOW:
                cons, vow, lab = k, rest[1:], True
                break
        else:
            return None
    if vow not in _VOW:
        return None
    order, v = _VOW[vow]
    return _CONS[cons], order, v, lab


def letters(word):
    """Decompose a fidel word into a list of (consonant, order, vowel, labialized)."""
    out = []
    for ch in word:
        d = decompose(ch)
        if d:
            out.append(d)
    return out


def to_fidel(cons, vowel=''):
    return chr(BASE[cons] + ORDER_OFFSET[vowel])


def tokens(latin):
    latin = unicodedata.normalize('NFC', latin)
    i = 0
    while i < len(latin):
        if latin[i:i + 2] in ('č̣', 'p̣'):
            yield latin[i:i + 2]; i += 2
        else:
            yield latin[i]; i += 1


def latin_to_fidel(word):
    """Raz Latin -> fidel (gemination collapses; vowelless consonant -> 6th order)."""
    toks = [t for t in tokens(word) if t not in '_-']
    out, i = [], 0
    while i < len(toks):
        c = toks[i]
        if c in BASE:
            if i + 1 < len(toks) and toks[i + 1] == c:   # geminate
                i += 1
                continue
            v = toks[i + 1] if i + 1 < len(toks) and toks[i + 1] in ORDER_OFFSET and toks[i + 1] else ''
            out.append(to_fidel(c, v))
            i += 2 if v else 1
        elif c in ORDER_OFFSET and c:
            out.append(to_fidel('ʼ', c)); i += 1
        else:
            out.append(c); i += 1
    return ''.join(out)
