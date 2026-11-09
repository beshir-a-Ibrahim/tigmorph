#!/usr/bin/env python3
"""Extract Raz's transcribed example sentences from a .docx copy of the thesis, for tools/eval_running_text.py.

Raz, R. (1973). A Descriptive Study of Tigre Grammar (PhD thesis). Chapters 2-4 and 6-9.
A line is taken as a Tigre sentence when it has at least 3 words, at least 40% of them carry Raz's special
letters (ʼ ʿ ə ā č ǧ š ṣ ṭ ḥ), none is a common English word, and all are in Raz's transcription alphabet.
Needs python-docx (pip install python-docx).
Usage: python3 tools/extract_raz_sentences.py THESIS.docx data/gold/raz_sentences.json"""
import sys, re, json
from docx import Document

CHAPTERS = {'Two', 'Three', 'Four', 'Six', 'Seven', 'Eight', 'Nine'}
EN = set('the and of to is a in he she it they was were his her their that this with for from be by as not '
         'you we i on at which who said'.split())
doc = Document(sys.argv[1])
cur, sents = None, []
for p in doc.paragraphs:
    t = p.text
    if p.style.name == 'Heading 1' and 'Chapter' in t:
        cur = t.split()[-1]
    if p.style.name == 'Heading 1' and 'TEXTS' in t:
        cur = None
    if cur not in CHAPTERS:
        continue
    for line in t.split('\n'):
        l = re.sub(r'\[p\. \d+\]', '', line).strip()
        l = re.sub(r'\s*[–-]\s*$', '', l)
        if not l or l.startswith(('§', '(', '“', '"')):
            continue
        toks = [re.sub(r'^[\.\(\[“"‘…]+|[\.\,\?\!\:\;\)\]”"’…]+$', '', w) for w in l.split()]
        toks = [x for x in toks if x]
        if len(toks) < 3:
            continue
        marked = sum(1 for x in toks if re.search(r'[ʼʿəāčǧšṣṭḥ]', x))
        if marked / len(toks) >= 0.4 and not any(x.lower() in EN for x in toks) and \
                all(re.match(r"^[ʼʿa-zəāčǧšžṣṭḥ̣ -]+$", x) for x in toks):
            sents.append(toks)
json.dump(sents, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
print(len(sents), 'sentences,', sum(len(s) for s in sents), 'words')
