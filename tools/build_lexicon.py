#!/usr/bin/env python3
"""Merge Raz gold lemmas (authoritative) with the Littmann–Höfner list into data/lexicon/verbs.tsv.

One row per (root, type, deriv) stem.  Raz rows carry certainty 'raz'; LH-only rows carry the
type inferred from LH spelling with certainty 'lh-hint' (LH spelling does not mark gemination or
always mark ā, so the type is a hint until confirmed by Raz or corpus evidence).
"""
import sys, os, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tigmorph.gold import parse
from tigmorph.fidel import to_fidel


def fidel_root(latin_root):
    return '-'.join(to_fidel(c, '') for c in latin_root.split('-')) if latin_root else ''


def main():
    _, _, lemmas = parse('data/gold/raz_ch5.gold')
    lh = list(csv.DictReader(open('data/lexicon/verbs_lh.tsv', encoding='utf-8'), delimiter='\t'))
    rows, seen = [], set()
    for L in lemmas:
        k = (L['root'], L['type'], L['deriv'])
        if k in seen:
            continue
        seen.add(k)
        rows.append(dict(root=fidel_root(L['root']), root_latin=L['root'], n_rad=len(L['root'].split('-')),
                         type=L['type'], deriv=L['deriv'], cls=L.get('class', ''), citation=L['lemma'],
                         gloss=L.get('gloss', ''), certainty='raz', source=f"Raz § {L.get('sec', '')}", lh_id=''))
    raz_roots = {r['root_latin'] for r in rows}
    from tigmorph.fidel import latin_to_fidel
    raz_spell = {latin_to_fidel(L['lemma'].split('.')[0]) for L in lemmas} | \
                {latin_to_fidel(L['lemma'].split('.')[0].replace('ā', 'a')) for L in lemmas}
    for r in lh:
        if r['status'] == 'compound' or not r['root_latin']:
            continue
        typ = r['type'] if r['type'] in ('A', 'B', 'C', 'D') else ('A' if r['type'] in ('Q', 'P') else ('C' if r['type'] == 'QC' else ''))
        k = (r['root_latin'], typ, r['deriv'])
        certainty = 'lh-hint' if r['status'] == 'ok' else ('lh-ambiguous' if r['status'] == 'ambiguous' else 'lh-review')
        if r['root_latin'] in raz_roots or r['headword'] in raz_spell:
            certainty += '+raz-root'          # Raz analyses this root/word: LH's reading is only a fallback
        if k in seen:
            for x in rows:
                if (x['root_latin'], x['type'], x['deriv']) == k:
                    x['lh_id'] = (x['lh_id'] + ' ' + r['id']).strip()
            continue
        seen.add(k)
        rows.append(dict(root=r['root'], root_latin=r['root_latin'], n_rad=r['n_rad'], type=typ, deriv=r['deriv'],
                         cls='', citation=r['headword'], gloss=r['gloss_en'], certainty=certainty,
                         source='Littmann–Höfner 1962' + (f" ({r['note']})" if r['note'] else ''), lh_id=r['id']))
    F = ['root', 'root_latin', 'n_rad', 'type', 'deriv', 'cls', 'citation', 'gloss', 'certainty', 'source', 'lh_id']
    with open('data/lexicon/verbs.tsv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, F, delimiter='\t'); w.writeheader(); w.writerows(rows)
    from collections import Counter
    print(len(rows), 'stems;', len({r['root_latin'] for r in rows}), 'roots')
    print(Counter(r['certainty'] for r in rows))


if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))
    main()
