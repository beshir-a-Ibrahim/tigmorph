# tigmorph

**A morphological analyzer and generator for Tigre** (ትግሬ, Ge'ez script), built from the description in
Shlomo Raz, *A Descriptive Study of Tigre Grammar* (University of London, 1973).

tigmorph takes a Tigre word in Ge'ez script and returns its possible analyses, ranked. Each analysis gives the root or
lemma, the word class and features, the pronunciation in Raz's transcription (which shows what the script hides:
gemination, ə, vowel length) and an English gloss. It covers every word class in Raz's grammar:

- **Verbs**: all four types (A–D), nine derivations (tə-, ʼa-, ʼat-, ʼatta-, ʼan-, ʼas-, ʼattan-, ʼattas-, ʼasta-),
  tri-, quadri- and quinqueradicals, weak roots (laryngal, semivowel, hollow, doubled), irregular verbs, object suffixes,
  negation, the prefixless imperfect, and verb compounds with light verbs (ሰኒ ቤለ).
- **Function words**: pronouns, demonstratives, the copula, 50 prepositions with pronoun endings, the article,
  conjunctions, adverbs and numerals.
- **Attached words**: ወ- "and", ከ- "and so", relative/article ለ-, prepositions and conjunctions written attached
  (ምንገብእ, ዲብለትፈናተ), -መ "also", -ዲ "indeed", the copula -ቱ.
- **Nouns, adjectives and names**: pronoun endings with their junctures, suffixed and broken plurals, gender, and the
  article. Participles, agent nouns, infinitives and instrument nouns are built from every verb root.
- **Unknown words**: a guesser proposes roots for verbs that are not in the lexicon.

The lexicon has about 3,300 verb stems, 9,000 nominal entries and 280 function words. The ranking was learned without
annotation from an 11-million-word Tigre corpus.

## Install

No dependencies. Python 3.8 or later on Linux, macOS or Windows.

```bash
pip install git+https://github.com/<your-account>/tigmorph.git
```

Or clone the repository and use it directly, without installing:

```bash
git clone https://github.com/<your-account>/tigmorph.git
cd tigmorph
python3 -m tigmorph ልቀትል
```

## Use

Command line:

```text
$ tigmorph -n 3 ወለዐለ ቤቼ ቅሩባት
ወለዐለ
    ው-ዕ-ል  V  Type=A Deriv=Base TAM=Perf Subj=3SgM Rel=Yes Cl=wa  ⟨wa-la-ʿala⟩  "to be (past: was, were); to pass the day"  (0.00)
    ...
ቤቼ
    ቤት  NOUN  Poss=1Sg  ⟨bet+1Sg⟩  "house"  (0.00)
ቅሩባት
    ቅ-ር-ብ  V>N  Type=A Deriv=Base TAM=PartPass Num=PlF  ⟨qərubāt⟩  "to approach"  (0.00)
    ...
```

```bash
tigmorph --latin ləqattəl                                         # input in Raz transcription
tigmorph --gen q-t-l Type=A Deriv=Base TAM=Perf Subj=3SgF         # generate: ቀትለት ⟨qatlat⟩
tigmorph --guess ዘረጠ                                             # include guesser readings
tigmorph "ሰኒ ቤለ"                                                 # verb compound (quote it)
cat words.txt | tigmorph -n 1                                     # words from standard input
```

Python:

```python
from tigmorph import Analyzer

A = Analyzer()
for a in A.analyze('ልቀትሎ')[:2]:
    print(a.root, a.tags, a.raz, a.gloss, a.weight)
# ቅ-ት-ል {'Type': 'A', 'Deriv': 'Base', 'TAM': 'Impf', 'Subj': '3PlM'} ləqatlo to kill 0.0
# ቅ-ት-ል {'Type': 'A', 'Deriv': 'Base', 'TAM': 'Impf', 'Subj': '3SgM', 'Obj': '3SgM'} ləqattəllo to kill 1.373

A.generate('q-t-l', {'Type': 'A', 'Deriv': 'Base', 'TAM': 'Perf', 'Subj': '3SgF'})
# [('qatlat', 'ቀትለት')]
```

`analyze` returns readings best first. `weight` is the ranking score relative to the best reading. The tags are
documented in [docs/TAGS.md](docs/TAGS.md).

## Normalize a corpus

Text collected from many sources writes the same word in several ways (ሀለ / ህለ, ይዐለ / ኢዐለ / የዐለ, ከፎ / ከአፎ,
ሠ for ሰ, ፡ between words, `::` for ።). `tigmorph normalize` writes every word in one standard spelling, so a corpus
built from several sources has one type per word.

```sh
tigmorph normalize corpus.txt -o corpus.norm.txt --report report.md --log changes.tsv
tigmorph normalize data.jsonl --field text -o data.norm.jsonl --keep-original
tigmorph normalize a.txt b.csv c.parquet --column text -o normalized/     # parquet needs pyarrow
```

```python
from tigmorph import Normalizer
N = Normalizer()                    # level='safe'
N('ህለ እት ዓድ፡ሠብ:: ኢዐለ')            # 'ሀለ እት ዓድ ሰብ። ይዐለ'
```

Levels:

- `chars`: character level only. Unicode NFC, letters with one sound in Tigre (ሠ→ሰ, ፀ→ጸ, ኀ→ሐ), ፡ as a space,
  Ge'ez punctuation, spaces.
- `safe` (default): `chars` plus the spelling table, but only for pairs that tigmorph reads as the same word and
  that differ only by a known free alternation. These alternations are the vowel on a laryngal (ሀ/ህ, አ/ኣ, ሐ/ሓ,
  ዐ/ዓ), an inserted አ, ኸ/ከ, ቐ/ቀ, and the negative ይ-/የ-/ኢ-.
- `full`: every row of the table, including pairs that differ in other letters (column `kind` = `form`). Review
  those first.

The table shipped with the package (`tigmorph/fst/standard.tsv`) was learned from the BeitTigreAI corpus. In each
group of spellings of one word, the most frequent spelling is the standard. It is a plain TSV, so you can edit it,
or learn your own table with `tigmorph normalize --learn my_table.tsv corpus/*.txt` and pass it with `--table`.
Normalization is idempotent, so running it twice changes nothing more.

## Accuracy

| Test | Words | Analysed | Best reading right |
|---|---|---|---|
| Raz's example sentences (running text, chapters 2–9) | 5,268 | 95.0% | 89.9% |
| Raz's verb paradigms (Ch. 5), Ge'ez input | 2,013 | 100% | — |
| Raz's function words and clitics (Ch. 3, 4, 7, 8) | 245 | 100% | 97.6% |
| Raz's deverbal nominals (§ 2.7) | 94 | 100% | 80% |
| Raz's nouns: singular, plural, possessive (Ch. 2) | 634 | 99.8% | 88% |
| Verb forms weighted by corpus frequency | 361k tokens | 100% | 96.9% |
| Corpus tokens (10.9M) analysed from the lexicon (not guessed) | | 83.8% | |

See [docs/ACCURACY.md](docs/ACCURACY.md) for how each figure is measured and for the known weaknesses. In short,
Ge'ez spelling hides gemination and vowel length, so some forms have two real readings that only context can settle.
The main cases are verb type B vs C, and a participle vs the prefixless imperfect.

## How it works

The grammar is written as root-independent templates (`tigmorph/paradigm.py`, following Raz Ch. 5 and Ch. 2).
[pynini](https://www.openfst.org/twiki/bin/view/GRM/Pynini) compiles the templates and the lexicon into finite-state
transducers with three levels:

```
root + tags   ⇄   Raz transcription   ⇄   Ge'ez spelling
```

Spelling variants are weighted, for example ā written with the 1st or the 4th order. Nominal endings
(`tigmorph/nominal.py`), function words (`tigmorph/closed.py`) and clitics (`tigmorph/analyzer.py`) are handled at run
time. The compiled transducers ship in `tigmorph/fst/`, and a small pure-Python runtime reads them
(`tigmorph/runtime.py`). Analysing a word takes about half a millisecond, and pynini is not needed to run.

## Rebuilding

You only need to rebuild if you change the grammar or the lexicon. This step needs pynini, which installs with pip on
Linux; on macOS or Windows, use Linux or Docker:

```bash
pip install pynini openpyxl pytest
python -m tigmorph.build              # full build (about 3 minutes)
python -m tigmorph.build --lex-only   # lexicon only (seconds)
pytest -q
```

The lexicon is `data/lexicon/verbs.tsv`, plus every file in `data/lexicon/extra/`, plus the nominal and function-word
tables. To add verbs, put a TSV in `data/lexicon/extra/` with the same columns.

Retraining the ranker needs the corpus. It is not included; download it from
[BeitTigreAI/tigre-data-monolingual-text](https://huggingface.co/datasets/BeitTigreAI/tigre-data-monolingual-text)
(CC BY 4.0) into `data/corpus/*.txt`, then run:

```bash
python tools/collect_corpus_analyses.py && python tools/train_ranker.py
```

Evaluation scripts are in `tools/`:

| Script | What it checks |
|---|---|
| `eval_gold.py` | verbs |
| `eval_closed.py` | function words |
| `eval_nominal.py` | nouns and deverbal nominals |
| `eval_ranking.py` | corpus-weighted ranking |
| `coverage_all.py` | corpus coverage |
| `eval_running_text.py` | Raz's sentences; build them first with `extract_raz_sentences.py` from your copy of the thesis |

## Contributing

The easiest way to help is to fill in one of the sheets in `contrib/`. Anything filled in there can be added to the
lexicon with the existing tools.

| Sheet | What to fill in |
|---|---|
| `contrib/unknown_words.xlsx` | the 1,000 most frequent corpus words the lexicon does not know yet: word class, lemma or root, meaning |
| `contrib/wiktionary_verbs_to_check.xlsx` | Wiktionary verb entries that could not be added automatically: the citation form (perfect 3m.sg.) or root |
| `contrib/annotation_sheet.xlsx` | 300 random corpus words in context: which reading is right; score it with `tools/score_annotation.py` |

Issues and pull requests are welcome. Please run `pytest -q` before submitting.

## Licence and citation

- **Code:** MIT licence ([LICENSE](LICENSE)).
- **Data:** CC0, CC BY 4.0 or CC BY-SA 4.0 depending on the source, as listed in [LICENSE-DATA.md](LICENSE-DATA.md).
  The Wiktionary-derived files and the compiled `tigmorph/fst/` data are CC BY-SA 4.0.
- **Citation:** if you use tigmorph, please cite it and Raz (1973); see [CITATION.cff](CITATION.cff).

## Acknowledgements

- **Grammar:** Shlomo Raz, *A Descriptive Study of Tigre Grammar* (PhD thesis, University of London, 1973).
- **Verb list:** compiled by the project team.
- **Lexical data:** the Tigre Wiktionary contributors.
- **Corpus:** the BeitTigreAI Tigre monolingual corpus.
