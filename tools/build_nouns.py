#!/usr/bin/env python3
"""Nominal and other open/closed-class lexicon from the Tigre Wiktionary (Phase 3, Milestone 7).

data/lexicon/wikt_entries.tsv (+ inflected forms in the XML) -> data/lexicon/nouns.tsv
Columns: geez (normalised headword), pos (NOUN, ADJ, PROPN, ADV, ADP, CONJ, PRON, NUM, INTJ, PART, X),
lemma (headword the form belongs to), number (Sg/Pl/''), gloss, tr, source.
Words already in closed_class.tsv keep their Raz analysis; Wiktionary adds a second reading only if the
class differs."""
import csv, os, re, sys, html
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, '.')
from tigmorph.analyzer import normalize_geez
from tigmorph.fidel import letters, to_fidel

POS = {'noun': 'NOUN', 'adjective': 'ADJ', 'proper noun': 'PROPN', 'adverb': 'ADV', 'preposition': 'ADP',
       'conjunction': 'CONJ', 'pronoun': 'PRON', 'numeral': 'NUM', 'interjection': 'INTJ', 'particle': 'PART',
       'phrase': 'X', 'other': 'X'}
rows = list(csv.DictReader(open('data/lexicon/wikt_entries.tsv', encoding='utf-8'), delimiter='\t'))
raw = html.unescape(open('data/wiktionary/tig-wiktionary.xml', encoding='utf-8').read())
form_of = {}
for t, x in re.findall(r'<page><title>Wt/tig/(.*?)</title><ns>0</ns>.*?<text[^>]*>(.*?)</text>', raw, re.S):
    m = re.search(r'\{\{Wt/tig/form\|([^}|]+)', x)
    if m:
        form_of[t] = m.group(1)
out, seen = [], set()


def add(geez, pos, lemma, number, gloss, tr, src):
    g = normalize_geez(geez)
    if not g or ' ' in geez.strip():
        return
    k = (g, pos, lemma)
    if k in seen:
        return
    seen.add(k)
    out.append(dict(geez=g, pos=pos, lemma=lemma, number=number, gloss=gloss, tr=tr, source=src))


for r in rows:
    pos = POS.get(r['pos'])
    hw = r['headword'].strip()
    gloss = '; '.join(g.strip() for g in r['gloss_en'].split(' | ')[:3]) if r['gloss_en'] else ''
    if pos:
        number = 'Pl' if '(plural' in r['gloss_en'] else ''
        gloss = re.sub(r'\s*\(plural[^)]*\)', '', gloss)
        add(hw, pos, hw, number, gloss, r['tr'], 'Wiktionary')
        L = letters(normalize_geez(hw))
        if False and pos in ('NOUN', 'ADJ') and not r['tr'] and len(L) >= 3 and L[-1][1] == 4 and not L[-1][3]:
            # disabled: for nominals the 4th order is usually real (ሐበራ 'signal'), and the -a reading collides
            # with verb perfects (ሐበረ)
            # the English-Tigre wordlist sometimes writes a final -a as 4th order (cf. verbs, Phase 2)
            add(normalize_geez(hw)[:-1] + to_fidel(L[-1][0], 'a'), pos, hw, number, gloss, r['tr'], 'Wiktionary (-a)')
    elif False and r['pos'] == 'inflected form' and hw in form_of:     # inflected forms: the morphology derives them
        lem = form_of[hw]
        lr = [x for x in rows if x['headword'] == lem and POS.get(x['pos']) in ('NOUN', 'ADJ', 'PROPN')]
        if lr:
            add(hw, POS[lr[0]['pos']], lem, 'Pl' if 'plural' in r['gloss_en'] else '',
                lr[0]['gloss_en'].split(' | ')[0], r['tr'], 'Wiktionary (inflected form)')
with open('data/lexicon/nouns.tsv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, ['geez', 'pos', 'lemma', 'number', 'gloss', 'tr', 'source'], delimiter='\t')
    w.writeheader(); w.writerows(out)
from collections import Counter
print(len(out), Counter(x['pos'] for x in out))
