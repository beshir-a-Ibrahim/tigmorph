"""Closed-class words (Raz Ch. 3, 4, 7, 8): pronouns, demonstratives, copula, prepositions, conjunctions,
adverbs, numerals, interjections — with pronominal suffixes (§ 2.10.2), the enclitic article (§ 2.11.2)
and preposition + demonstrative fusion (ʼəbbəlli, ʼəttəlli; § 8.1.5).

expand() turns data/lexicon/closed_class.tsv into (Latin form, entry, features, weight) tuples.
build_closed() (build time) spells them in Ge'ez with the ORTH transducer -> fst/closed.json.
"""
import csv, os, json

SUFFIXES = [('1Sg', 'ye'), ('2SgM', 'ka'), ('2SgF', 'ki'), ('3SgM', 'u'), ('3SgF', 'a'),
            ('1Pl', 'na'), ('2PlM', 'kum'), ('2PlF', 'kən'), ('3PlM', 'om'), ('3PlF', 'an')]
PAL = {'t': 'č', 'd': 'ǧ', 's': 'š', 'z': 'ž', 'ṣ': 'č̣', 'ṭ': 'č̣'}
VOWELS = set('aāeiouə')
DEMS = ['ʼəlli', 'ʼəlla', 'ʼəllom', 'ʼəllan']


def _last(stem):
    return stem[-2:] if stem.endswith('̣') else stem[-1]


def attach(stem, cls, sfx):
    """Pronominal suffix on a particle or noun-like stem (§ 2.10). Returns [(form, weight)]."""
    v = sfx[0] in 'aou'
    last = _last(stem)
    ends_v = last in VOWELS
    if sfx == 'ye':
        if cls == 'el':
            return [('ʼəlye', 0), ('ʼəye', 0.2)]
        if ends_v:
            return [(stem + 'ye', 0)]
        if last == 'y':
            return [(stem + 'e', 0)]
        if last in PAL:
            p = PAL[last]
            out = [(stem[:-len(last)] + p + p + 'e', 0)]                  # ʼət -> ʼəčče, warāt -> warāčče
            if cls == 'cvc':
                out.append((stem[:-len(last)] + p + 'e', 0.3))            # nos -> noše
            return out
        return [(stem + 'ye', 0)]
    if cls == 'h':
        return [(stem + ('h' if v else '') + sfx, 0)]                       # ḥaqohu, ḥanteka, kəmsalhu
    if cls == 'el':                                                         # ʼəlu, ʼəlom, ʼəlka; ʼəla/ʼəlom/ʼəlan
        return [(stem + sfx, 0.3 if sfx in ('a', 'om', 'an') else 0)]      # share spellings with ʼəlla/ʼəllom/ʼəllan
    if cls == 'gem':
        if v:                                                               # mənnu, ʼəttu, dibbu; 3f.sg. = article form
            return [(stem + last + sfx, 0.2 if sfx == 'a' else 0)]
        out = [(stem + sfx, 0.1 if sfx == 'na' else 0)]                    # mənna 'from us' = mənna 'from the'
        if sfx == 'na':
            out.append((stem + 'ə' + sfx, 0.2))                             # mənəna
        return out
    if cls == 'b':                                                          # ʼəb: ʼəbbu / bu, bəka
        if v:
            return [('ʼəbb' + sfx, 0.2 if sfx == 'a' else 0), ('b' + sfx, 0.1)]
        return [('bə' + sfx, 0), ('ʼəb' + sfx, 0.2)]
    if cls == 'cvc':
        if v and len(stem) >= 3 and stem[-2] == 'ə' and stem[-3] not in VOWELS and any(c in VOWELS for c in stem[:-2]):
            return [(stem[:-2] + last + sfx, 0.2 if sfx == 'a' else 0)]     # məsəl -> məslu, ʼəgəl -> ʼəglu
        return [(stem + sfx, 0)]
    return [(stem + sfx, 0)]                                                # plain: nāyu, nāyka


def load(path):
    return [r for r in csv.DictReader(open(path, encoding='utf-8'), delimiter='\t') if r['latin']]


def feats_of(r):
    return {} if r['feats'] in ('', '_') else dict(kv.split('=') for kv in r['feats'].split(','))


def expand(rows):
    """-> list of (latin_form, row, extra_feats, weight)"""
    out = []
    for r in rows:
        lat = r['latin']
        if ' ' in lat:
            continue
        base = float(r.get('w') or 0)            # per-entry prior: >0 for words that are more often something else
        out.append((lat, r, {}, base))
        if r['pos'] == 'PRON' and r['feats'].startswith('Person='):            # ʼiʼana 'I am not' (§ 4.1.1)
            out.append(('ʼi' + lat, r, {'Neg': 'Yes', 'Cop': 'Yes'}, 0.2))
        if r['sfx'] not in ('none', ''):
            for cell, s in SUFFIXES:
                for form, w in attach(lat, r['sfx'], s):
                    out.append((form, r, {'Poss': cell}, w + base))
        if r['art'] in ('assim', 'plain'):                                    # ʼət + la -> ʼətta (§ 2.11.2)
            last = _last(lat)
            if r['art'] == 'assim' and last not in VOWELS:
                out.append((lat + last + 'a', r, {'Art': 'Def'}, 0.0))
            out.append((lat + 'la', r, {'Art': 'Def'}, 0.1))
        if r['pos'] == 'PREP' and r['sfx'] in ('gem', 'b'):                     # ʼəb + ʼəlli -> ʼəbbəlli
            for d in DEMS:
                out.append((lat + _last(lat) + 'ə' + d[2:], r, {'Dem': d}, 0.1))
    return out


def build_closed(out_dir, data_dir, orth):
    """Spell every closed-class form in Ge'ez (n-best through ORTH) -> closed.json"""
    from . import runtime as R
    from .analyzer import _IDENT, normalize_geez
    from .fidel import latin_to_fidel
    rows = load(os.path.join(data_dir, 'lexicon', 'closed_class.tsv'))
    table = {}

    def add(gz, rec):
        gz = normalize_geez(gz)
        lst = table.setdefault(gz, [])
        for x in lst:
            if x[:4] == rec[:4] and x[5] == rec[5]:
                x[4] = min(x[4], rec[4]); return
        lst.append(rec)

    for form, r, extra, w in expand(rows):
        f = dict(feats_of(r), **extra)
        rec_base = [r['latin'], r['pos'], ','.join(f'{k}={v}' for k, v in f.items()), form, 0.0, r['gloss'],
                    latin_to_fidel(r['latin'])]
        paths = R.cascade(form, _IDENT, orth, None, nbest=8)
        best = min((p[2] for p in paths), default=0)
        for _, gz, pw in paths:
            if pw - best <= 1.0:
                add(gz, rec_base[:4] + [round(w + pw - best, 3)] + rec_base[5:])
        if extra == {} and r.get('geez_extra'):
            for gz in r['geez_extra'].split(';'):
                add(gz.strip(), rec_base[:4] + [0.2] + rec_base[5:])
    json.dump(table, open(os.path.join(out_dir, 'closed.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    return len(table)
