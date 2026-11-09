"""Compile the grammar with pynini and export it for the pure-Python runtime.

Only needed when the grammar or lexicon changes:   python -m tigmorph.build
(requires pynini; on macOS see README).  End users never need this.
"""
import os, csv, sys, re
from . import runtime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')


def lexicon_rows(lexicon='verbs.tsv'):
    """verbs.tsv (from tools/build_lexicon.py) plus every data/lexicon/extra/*.tsv (Phase 2 additions)."""
    import glob
    paths = [os.path.join(DATA, 'lexicon', lexicon)] + sorted(glob.glob(os.path.join(DATA, 'lexicon', 'extra', '*.tsv')))
    for p in paths:
        yield from csv.DictReader(open(p, encoding='utf-8'), delimiter='\t')


def _write_compounds(out):
    """compounds.tsv (Raz) + compounds_wiktionary.tsv -> fst/compounds.tsv"""
    rows, seen = [], set()
    for name in ('compounds.tsv', 'compounds_wiktionary.tsv'):
        p = os.path.join(DATA, 'lexicon', name)
        if os.path.exists(p):
            for r in csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'):
                k = (r['first'].replace(' ', ''), r['verb'])
                if k not in seen:
                    seen.add(k); rows.append(dict(first=r['first'], verb=r['verb'], gloss=r['gloss'], source=r['source']))
    with open(os.path.join(out, 'compounds.tsv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, ['first', 'verb', 'gloss', 'source'], delimiter='\t'); w.writeheader(); w.writerows(rows)


def _write_glosses(out, lexicon='verbs.tsv'):
    """English glosses per stem (root|type|deriv): lexicon rows first (Raz, LH), then Wiktionary."""
    import json
    g = {}
    srcs = list(lexicon_rows(lexicon))
    p = os.path.join(DATA, 'lexicon', 'wikt_glosses.tsv')
    if os.path.exists(p):
        srcs += list(csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'))
    for r in srcs:
        gl = re.sub(r'\s*\([^()]*(?:ʼ|§|type|[ABCD] of|tə-|ʼa-)[^()]*\)', '', (r.get('gloss') or '')).strip()
        if not gl or gl.startswith('(') or not r.get('root_latin'):
            continue
        d = 'Base' if r['deriv'] in ('base', 'Base') else r['deriv']
        g.setdefault(f"{r['root_latin']}|{r['type']}|{d}", gl)
    po = os.path.join(DATA, 'lexicon', 'gloss_override.tsv')
    if os.path.exists(po):
        for r in csv.DictReader(open(po, encoding='utf-8'), delimiter='\t'):
            g[f"{r['root_latin']}|{r['type']}|{r['deriv']}"] = r['gloss']
    json.dump(g, open(os.path.join(out, 'glosses.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)


def _write_nouns(out):
    """Nominal lexicon -> fst/nouns.json  {geez: [[lemma, pos, number, gloss, weight, feats], ...]}
    - Raz Ch. 2 nouns (data/lexicon/raz_nouns.tsv, Latin; spelled through ORTH) with plurals and listed
      possessive forms;
    - Wiktionary nominals and other classes (data/lexicon/nouns.tsv, from tools/build_nouns.py)."""
    import json
    from .analyzer import _IDENT, normalize_geez
    orth = runtime.Fst('orth', directory=out)
    d = {}

    def put(g, rec):
        g = normalize_geez(g)
        if not g:
            return
        lst = d.setdefault(g, [])
        for x in lst:
            if x[:4] == rec[:4] and x[5] == rec[5]:
                x[4] = min(x[4], rec[4]); return
        lst.append(rec)

    def spell(latin):
        paths = runtime.cascade(latin, _IDENT, orth, None, nbest=6)
        best = min((p[2] for p in paths), default=0)
        return [(gz, round(w - best, 3)) for _, gz, w in paths if w - best <= 1.0]

    p = os.path.join(DATA, 'lexicon', 'raz_nouns.tsv')
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'):
            g = f"Gender={r['gender']}" if r['gender'] else ''
            for gz, w in spell(r['latin']):
                put(gz, [r['latin'], 'NOUN', '', r['gloss'], w, g])
            for pl in filter(None, r['pl'].split(';')):
                for gz, w in spell(pl):
                    put(gz, [r['latin'], 'NOUN', 'Pl', r['gloss'], w, 'Plural=Broken' if pl.startswith('ʼa') or 'ā' not in pl[-3:] else ''])
            for f in filter(None, r['forms'].split(';')):
                form, cell = f.split(':')
                for gz, w in spell(form):
                    put(gz, [r['latin'], 'NOUN', '', r['gloss'], w, 'Poss=' + cell])
    p = os.path.join(DATA, 'lexicon', 'nouns.tsv')
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'):
            w = (0.3 if '(-a)' in r['source'] else 0.1) + (0.0 if r['pos'] in ('NOUN', 'ADJ', 'PROPN') else 0.3)
            same = [x for x in d.get(r['geez'], []) if x[1] == r['pos'] and not ('\u1200' <= x[0][:1] <= '\u137f')]
            if same:                                   # Raz already has this noun: keep Raz's analysis,
                for x in same:                         # take the spelling's weight from the dictionary
                    x[4] = min(x[4], 0.0)
                continue
            put(r['geez'], [r['lemma'], r['pos'], r['number'], r['gloss'], w, ''])
    json.dump(d, open(os.path.join(out, 'nouns.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('nominal spellings:', len(d))


def build(lexicon='verbs.tsv', out=runtime.FST_DIR, lex_only=False):
    from . import fst as F                      # imports pynini
    morph = None if lex_only else F.build_morph()
    orth = None if lex_only else F.build_orth()
    entries = []
    demote = {(d['root_latin'], d['type'], d['deriv']) for d in
              csv.DictReader(open(os.path.join(DATA, 'lexicon', 'demote.tsv'), encoding='utf-8'), delimiter='\t')}
    for r in lexicon_rows(lexicon):
        if (r['root_latin'], r['type'], r['deriv']) in demote:
            r = dict(r, certainty='lh-demoted')
        if not (r['root_latin'] and r['type'] in ('A', 'B', 'C', 'D')) or '+raz-root' in r['certainty']:
            continue
        entries.append((r['root_latin'].replace('-', ''), r['type'],
                        'Base' if r['deriv'] == 'base' else r['deriv'], F.CERTAINTY_W.get(r['certainty'], 0.5)))
    ex, ot, gu = F.build_lex(entries)
    for name, f in (('morph', morph), ('orth', orth), ('lex_exact', ex), ('lex_other', ot), ('lex_guess', gu)):
        if f is not None:
            runtime.export(f, name, out)
    _write_compounds(out)
    _write_glosses(out, lexicon)
    from .closed import build_closed
    n = build_closed(out, DATA, runtime.Fst('orth', directory=out))
    print('closed-class spellings:', n)
    _write_nouns(out)
    return out


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    print('wrote', build(*args, lex_only='--lex-only' in sys.argv))
