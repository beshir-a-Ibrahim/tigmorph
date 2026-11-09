#!/usr/bin/env python3
"""Annotation sheet for the final all-class accuracy check.

300 word tokens drawn at random from the corpus (each token equally likely, so frequent words appear as often
as they do in real text), with their sentence and tigmorph's three best readings.
The annotator marks which reading is right (1, 2, 3, or 0 = none) and, for 0, the right word class.
Score with tools/score_annotation.py.
Output: contrib/annotation_sheet.xlsx and build/annotation_items.json"""
import os, sys, re, glob, random, json
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs('build', exist_ok=True)
sys.path.insert(0, '.')
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from tigmorph.analyzer import Analyzer, normalize_geez

N = 300
random.seed(2026)
WORD = re.compile(r'[ሀ-ፚ]+')
lines = []
for p in sorted(glob.glob('data/corpus/*.txt')):
    for line in open(p, encoding='utf-8'):
        k = len(WORD.findall(line))
        if 4 <= k <= 60:
            lines.append((line.strip(), k))
total = sum(k for _, k in lines)
cum, s = [], 0
for _, k in lines:
    s += k; cum.append(s)
A = Analyzer()
items, seen = [], set()
import bisect
while len(items) < N:
    r = random.randrange(total)
    i = bisect.bisect_right(cum, r)
    line, k = lines[i]
    toks = list(WORD.finditer(line))
    j = r - (cum[i] - k)
    m = toks[min(j, len(toks) - 1)]
    if (i, m.start()) in seen:
        continue
    seen.add((i, m.start()))
    w = normalize_geez(m.group())
    an = A.analyze(w, n=3)
    lo, hi = max(0, m.start() - 70), min(len(line), m.end() + 70)
    ctx = ('…' if lo else '') + line[lo:m.start()] + '【' + m.group() + '】' + line[m.end():hi] + ('…' if hi < len(line) else '')

    def show(a):
        t = a.tags
        pos = t.get('POS') or ('V>N' if t.get('TAM') in ('PartAct', 'PartPass', 'Agent', 'Inf', 'Instr') else 'V')
        keys = [f'{k}={v}' for k, v in t.items() if k not in ('POS',)]
        g = f' "{a.gloss[:40]}"' if a.gloss else ''
        return f'{pos} {a.root} ⟨{a.raz}⟩ ' + ' '.join(keys) + g + (' [guess]' if a.guess else '')
    items.append(dict(word=m.group(), norm=w, context=ctx, readings=[show(a) for a in an],
                      raw=[[a.root_latin, a.tags, a.raz, a.guess] for a in an]))
json.dump(items, open('build/annotation_items.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

wb = Workbook()
ins = wb.active; ins.title = 'Instructions'
F = Font(name='Arial', size=10)
for row in [
    ['tigmorph v2.0: final accuracy check'],
    [''],
    ['Each row is one word taken at random from the corpus, shown in its sentence (the word is in 【 】).'],
    ['Columns D-F show tigmorph\'s three best readings, best first. Fill in the yellow columns:'],
    ['  G  Correct reading: 1, 2 or 3 = that reading is right; 0 = none of them is right.'],
    ['  H  Only if G is 0: the right word class (verb, noun, adjective, name, pronoun, preposition, conjunction, adverb, number, other).'],
    ['  I  Optional note (for example the right root or meaning).'],
    ['"Right" means: right word class, right root/lemma, and right main features (tense, person, number, ending).'],
    ['If two readings are both right in this sentence, put the better one.'],
    [''],
    ['Example of a filled-in row: word ለዐለ, reading 1 = "V ው-ዕ-ል ⟨la-ʿala⟩ ... Rel=Yes", G = 1.'],
    ['Reading codes: V = verb, V>N = noun or participle made from a verb, NOUN, ADJ, PROPN = name, PRON, DEM = this/that, COP = copula,'],
    ['PREP, CONJ, SCONJ, ADV, NUM, INTJ, AUX. Poss = pronoun ending, Rel = relative la-, Art = article la-, Cl = wa-/ka-, Prep = attached preposition.'],
]:
    ins.append(row)
for r in ins.iter_rows():
    for c in r:
        c.font = F
ins['A1'].font = Font(name='Arial', size=12, bold=True)
ins.column_dimensions['A'].width = 140
ws = wb.create_sheet('Words')
hdr = ['#', 'Word', 'Context', 'Reading 1', 'Reading 2', 'Reading 3', 'Correct reading (0-3)', 'Right class if 0', 'Note']
ws.append(hdr)
for c in ws[1]:
    c.font = Font(name='Arial', size=10, bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='305496')
    c.alignment = Alignment(wrap_text=True, vertical='center')
Y = PatternFill('solid', fgColor='FFF2CC')
for k, it in enumerate(items, 1):
    rd = it['readings'] + [''] * (3 - len(it['readings']))
    ws.append([k, it['word'], it['context'], rd[0] or '(no analysis)', rd[1], rd[2], '', '', ''])
for row in ws.iter_rows(min_row=2):
    for c in row:
        c.font = F; c.alignment = Alignment(wrap_text=True, vertical='top')
    for c in row[6:9]:
        c.fill = Y
dv = DataValidation(type='list', formula1='"0,1,2,3"', allow_blank=True)
ws.add_data_validation(dv); dv.add(f'G2:G{ws.max_row}')
dv2 = DataValidation(type='list', formula1='"verb,noun,adjective,name,pronoun,preposition,conjunction,adverb,number,other"', allow_blank=True)
ws.add_data_validation(dv2); dv2.add(f'H2:H{ws.max_row}')
for col, w in zip('ABCDEFGHI', [5, 12, 55, 42, 42, 42, 12, 14, 24]):
    ws.column_dimensions[col].width = w
ws.freeze_panes = 'C2'
wb.save('contrib/annotation_sheet.xlsx')
print('items', len(items), 'no analysis', sum(1 for it in items if not it['readings']),
      'guess only', sum(1 for it in items if it['raw'] and it['raw'][0][3]))
