# How accurate is tigmorph?

All figures are for v2.0. Each one can be reproduced with the script named in its section.

## 1. Running text: Raz's example sentences

`tools/eval_running_text.py`. The sentence file is built with `tools/extract_raz_sentences.py` from a copy of
the thesis.

Raz (1973) gives 470 example sentences (5,268 words), taken from Tigre texts, in chapters 2–4 and 6–9. They are written
in a transcription that shows what the Ge'ez script hides: vowel length, ə, gemination, and attached words. The test
works like this:

1. Each word is spelled in Ge'ez.
2. tigmorph analyses it.
3. The pronunciation implied by tigmorph's best reading is compared with Raz's.

A match means the right stem, the right verb type and the right inflected form. The text was not used to build the
grammar, so this is an independent check on real sentences.

| Measure | Result |
|---|---|
| Words with an analysis | 95.0% |
| Best reading reproduces Raz's pronunciation (words where this can be checked) | 89.9% |
| Raz's pronunciation among the 10 best readings | 94.8% |

By class of the best reading:

| Class | Consistent |
|---|---|
| Function words | 91–100% |
| Nouns | 93.6% |
| Verbs | 83.6% |
| Participles and similar | 57% |

Limits of this test:

- Some readings cannot be checked: dictionary nouns with an ending, and Wiktionary nouns, which are stored only in Ge'ez.
  This applies to 750 words.
- Forms that sound the same count as one, for example the 2m.sg. and 3f.sg. imperfect. The figure is therefore a little
  above full feature accuracy.
- Part of Raz's material is older narrative and Bible text.

## 2. Raz's paradigms and word lists

| Set | Script | Forms | Found | Best reading |
|---|---|---|---|---|
| Verb paradigms, Ch. 5 (Ge'ez, Raz transcription, and with the guesser alone) | `eval_gold.py all` | 2,013 | 100% / 100% / 100% | — |
| Verb compounds (§ 5.11) | `eval_gold.py` | 69 | 100% | — |
| Function words and clitics, Ch. 3, 4, 7, 8 | `eval_closed.py` | 245 | 100% | 97.6% |
| Participles, agent nouns, infinitives (§ 2.7) | `eval_nominal.py` | 94 | 100% | 80% |
| Nouns: singular, plural, possessive (Ch. 2 tables) | `eval_nominal.py` | 634 | 99.8% | 88% |

The noun set comes from the same Raz tables as part of the noun lexicon, so for nouns "found" mainly confirms spelling
and lookup. The verb paradigms, function words and participles test the grammar rules themselves.

## 3. Ranking weighted by frequency

`tools/eval_ranking.py`

The verb forms of the paradigms that occur in the corpus (946 word types, 361,000 tokens) are weighted by their
frequency. The right reading comes first for **96.9% of tokens** and 88.8% of types.

## 4. Coverage

`tools/coverage_all.py`, `tools/corpus_coverage.py`

- **83.8%** of the 10.9 million tokens in the corpus get an analysis from the lexicon, not from the guesser.
- For the 3,000 most frequent word types, the figure is 96.5% of their tokens.
- The rest are mostly nouns that are not in any dictionary yet, names, loanwords and abbreviations. The 1,000 most
  frequent of them are in `contrib/unknown_words.xlsx`.

## 5. Known weaknesses

- **Verb type B vs C.** Gemination (B) and long ā (C) are usually not written, so ሐበረ can be *ḥabbara* or *ḥābara*.
  The ranker picks the reading that is more frequent in the corpus.
- **Participle vs prefixless imperfect.** *bāṭər* (participle) and *baṭṭər* (imperfect) are both spelled ብጥር.
- **Noun vs verb with the same letters.** For example, ረአይ is both the noun "view" and the verb "see!".
- **Broken plurals of nouns not in the lexicon** cannot be predicted; Raz says the same (§ 2.5.2).
- **The ranker is unsupervised.** It does not look at the surrounding words. A context-aware ranker trained on annotated
  text would resolve most of the cases above.
