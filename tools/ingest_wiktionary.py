#!/usr/bin/env python3
"""Ingest the Tigre Wiktionary export (Wt/tig) into tigmorph.

1. All entries (every part of speech) -> data/lexicon/wikt_entries.tsv  (headword, pos, tr, gloss_en, gloss_ar).
   Non-verbs are kept for Phase 3.
2. Verb headwords (perfect 3m.sg citation forms) that the analyzer does not already read as a perfect 3m.sg
   of a known root -> classified from their fidel orders (same rules as the Littmann–Höfner ingest, after Raz Ch. 5)
   -> data/lexicon/extra/wiktionary_verbs.tsv (certainty wikt-hint / wikt-ambiguous).
   Multiword verbs ending in a light verb (ቤለ, አበለ, ወዳ, ገአ ...) -> data/lexicon/compounds_wiktionary.tsv.
   Headwords whose shape cannot be classified -> build/wikt_verbs_review.tsv.
Usage: python3 tools/ingest_wiktionary.py data/wiktionary/tig-wiktionary.xml"""
import sys, os, re, csv, html
from collections import defaultdict
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs('build', exist_ok=True)
sys.path.insert(0, '.'); sys.path.insert(0, 'tools')
from tigmorph.analyzer import Analyzer, normalize_geez
from tigmorph.fidel import letters, to_fidel
from ingest_lh import classify, root_str, weak_flags

if '--verify' in sys.argv:
    # second pass, after `python3 -m tigmorph.build --lex-only`: keep only rows whose citation form the grammar
    # actually generates as a perfect 3m.sg of that root; the rest go to the review list
    A = Analyzer()
    p = 'data/lexicon/extra/wiktionary_verbs.tsv'
    rows = list(csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'))
    keep, bad = [], []
    for x in rows:
        cits = [x['citation']]
        L = letters(x['citation'])
        if L and L[-1][1] == 4:                  # Littmann–Höfner write final -a of semivowel verbs as ā (ሕጋ = ሕገ)
            cits.append(x['citation'][:-1] + to_fidel(L[-1][0], 'a'))
        ok = any(a.root_latin == x['root_latin'] and a.tags['TAM'] == 'Perf' and a.tags['Subj'] == '3SgM'
                 and 'Obj' not in a.tags for c in cits for a in A.analyze(c, guess=False, n=30))
        (keep if ok else bad).append(x)
    with open(p, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]), delimiter='\t'); w.writeheader(); w.writerows(keep)
    with open('build/wikt_verbs_review.tsv', 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        for x in bad:
            w.writerow([x['citation'], x['lh_id'], x['gloss'], f"shape read as {x['root_latin']} {x['type']}/{x['deriv']}, "
                        'but the grammar does not generate this citation form'])
    print('verified', len(keep), 'moved to review', len(bad))
    sys.exit()
src = [a for a in sys.argv[1:] if not a.startswith('--')]
src = src[0] if src else 'data/wiktionary/tig-wiktionary.xml'
raw = open(src, encoding='utf-8').read()
pages = re.findall(r'<page><title>Wt/tig/(.*?)</title><ns>0</ns>.*?<text[^>]*>(.*?)</text>', raw, re.S)


def clean(s):
    s = re.sub(r'\{\{Wt/tig/t\|[^|}]*\|([^|}]*)\|[^|}]*(?:\|([^}]*))?\}\}', lambda m: m.group(2) or m.group(1), s)
    s = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', s)
    s = re.sub(r'\{\{[^}]*\}\}', '', s)
    return re.sub(r"''+", '', s).strip()


def sections(text):
    """Split one page into (pos, tr, en glosses, ar glosses) per part-of-speech section."""
    out = []
    parts = re.split(r'\n=== \{\{Wt/tig/S\|([^}]+)\}\} ===\n', '\n' + text)
    for pos, body in zip(parts[1::2], parts[2::2]):
        if pos in ('translations', 'related', 'etymology'):
            continue
        body = body.split('\n=== ')[0]
        m = re.search(r'\{\{Wt/tig/head\|[^|}]*(?:\|tr=([^|}]*))?', body)
        tr = m.group(1) if m and m.group(1) else ''
        tl = body.split('==== {{Wt/tig/S|translations}} ====')
        en, ar, cur = [], [], None
        if len(tl) > 1:
            for line in tl[1].split('\n'):
                if line.startswith('==== '):
                    break
                if line.startswith('* {{Wt/tig/L|'):
                    cur = line[len('* {{Wt/tig/L|'):].split('}')[0]
                elif line.startswith('*#'):
                    g = clean(line[2:])
                    (en if cur == 'en' else ar if cur == 'ar' else []).append(g)
        out.append(dict(pos=pos, tr=tr, en=en, ar=ar))
    return out


def short_gloss(en):
    if not en:
        return ''
    g = en[0]
    m = re.search(r'\((to [^()]*(?:\([^()]*\)[^()]*)*)\)\s*$', g)
    return (m.group(1) if m else g).strip()


entries = []
for title, text in pages:
    for s in sections(html.unescape(text)):
        entries.append(dict(headword=title, pos=s['pos'], tr=s['tr'], gloss_en=' | '.join(s['en']),
                            gloss_ar=' | '.join(s['ar']), short=short_gloss(s['en'])))
with open('data/lexicon/wikt_entries.tsv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, ['headword', 'pos', 'tr', 'gloss_en', 'gloss_ar'], delimiter='\t', extrasaction='ignore')
    w.writeheader(); w.writerows(entries)

LIGHT = {'ቤለ': 'bela', 'በለ': 'bela', 'ቤላ': 'bela', 'አበለ': 'ʼabala', 'ኣበለ': 'ʼabala', 'አትበለ': 'ʼattabala',
         'ወዳ': 'wada', 'ወደ': 'wada', 'ገአ': 'gaʼa'}
A = Analyzer()
F = ['root', 'root_latin', 'n_rad', 'type', 'deriv', 'cls', 'citation', 'gloss', 'certainty', 'source', 'lh_id']
rows, comps, review, covered, glosses = [], [], [], 0, []
seen = set()
for e in entries:
    if e['pos'] != 'verb':
        continue
    hw = e['headword'].strip()
    if hw in seen:
        continue
    seen.add(hw)
    words = hw.split()
    if len(words) > 1:
        if words[-1] in LIGHT:
            comps.append(dict(first=' '.join(words[:-1]), verb=LIGHT[words[-1]], gloss=e['short'], source='Wiktionary'))
        else:
            review.append(dict(headword=hw, tr=e['tr'], gloss=e['short'], reason='multiword, no light verb'))
        continue
    g = normalize_geez(hw)
    if not g:
        continue
    L = letters(g)
    if not e['tr'] and len(L) >= 2 and L[-1][1] == 4 and not L[-1][3]:
        # entries without a transliteration (the English-Tigre part of the wordlist) write the perfect's final -a as 4th order (ሐስባ for ሐስበ);
        # the corpus has ሐስበ 340 : ሐስባ 12, ቀትለ 320 : ቀትላ 16, so read it as -a
        g = g[:-1] + to_fidel(L[-1][0], 'a')
    if re.match(r"(?i)(they|you|we|i|she|there|not)\b", e['short']):
        review.append(dict(headword=hw, tr=e['tr'], gloss=e['short'], reason='inflected form (gloss names a person)'))
        continue
    an = A.analyze(g, guess=False, n=20)
    hits = [a for a in an if a.tags['TAM'] == 'Perf' and a.tags['Subj'] == '3SgM' and 'Obj' not in a.tags
            and 'Neg' not in a.tags and 'Colloq' not in a.tags]
    if hits:
        covered += 1
        if e['short']:
            a = hits[0]
            glosses.append(dict(root_latin=a.root_latin, type=a.tags['Type'], deriv=a.tags['Deriv'],
                                citation=hw, gloss=e['short']))
        continue
    c = classify(re.sub(r'[^ሀ-፿]', '', g))
    typ = c['type'] if c['type'] in ('A', 'B', 'C', 'D') else {'Q': 'A', 'P': 'A', 'QC': 'C'}.get(c['type'], '')
    if not typ or c['status'] == 'review':
        review.append(dict(headword=hw, tr=e['tr'], gloss=e['short'], reason=c['note'].strip('; ')))
        continue
    rf, rl = root_str(c['cons'])
    rows.append(dict(root=rf, root_latin=rl, n_rad=len(c['cons']), type=typ, deriv=c['deriv'],
                     cls=','.join(weak_flags(c['cons'])), citation=g, gloss=e['short'],
                     certainty='wikt-hint' if c['status'] == 'ok' else 'wikt-ambiguous',
                     source='Wiktionary (Wt/tig)', lh_id=e['tr']))
with open('data/lexicon/extra/wiktionary_verbs.tsv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, F, delimiter='\t'); w.writeheader(); w.writerows(rows)
with open('data/lexicon/compounds_wiktionary.tsv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, ['first', 'verb', 'gloss', 'source'], delimiter='\t'); w.writeheader(); w.writerows(comps)
with open('build/wikt_verbs_review.tsv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, ['headword', 'tr', 'gloss', 'reason'], delimiter='\t'); w.writeheader(); w.writerows(review)
with open('data/lexicon/wikt_glosses.tsv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, ['root_latin', 'type', 'deriv', 'citation', 'gloss'], delimiter='\t'); w.writeheader(); w.writerows(glosses)
pos = defaultdict(int)
for e in entries:
    pos[e['pos']] += 1
print('entries', len(entries), dict(sorted(pos.items(), key=lambda x: -x[1])))
print('verb headwords', len(seen), 'already analysed', covered, 'new rows', len(rows),
      'compounds', len(comps), 'to review', len(review))
