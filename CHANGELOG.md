# Changelog

## 2.1.0 — 2026-11-09
Spelling normalizer.
- `tigmorph.Normalizer` and `tigmorph normalize`: write Tigre text in one standard spelling. Levels `chars`, `safe`
  and `full`. Reads txt, jsonl, csv, tsv and parquet. Options to keep the original text, log every change and write
  a before/after report.
- Spelling table learned from the BeitTigreAI corpus (`tigmorph/fst/standard.tsv`, 9,709 pairs, 2,152 safe).
- `Normalizer.learn` / `--learn` learns a table from your own corpus.

## 2.0.0 — 2026-11-09
All word classes.
- Nouns, adjectives and names: Raz Ch. 2 nouns (plurals, gender, irregular possessives) and Tigre Wiktionary entries;
  pronoun endings with their junctures, suffixed plurals, article.
- Deverbal nominals from every verb root: active and passive participles, agent nouns, infinitives, instrument nouns,
  including hollow roots.
- Function words (pronouns, demonstratives, copula, prepositions with endings, conjunctions, adverbs, numerals) and
  clitics (ወ-, ከ-, relative/article ለ-, attached prepositions, -መ, -ዲ, copula -ቱ).
- One corpus-trained ranker for every class.
- Corpus spellings of the negative: ኢቀድር (1sg) and ይዐለ / ይሀለ.
- Running-text evaluation on Raz's example sentences.

## 1.2.0
- Verbs from the Tigre Wiktionary (386 new stems, 30 compounds); English glosses on about 3,300 stems.
- 92 verb roots discovered in the corpus and confirmed by native-speaker review.

## 1.1.0
- Corpus spellings: ʼa- kept in imperfects (ለአፍህም), ሀሌት/ህሌት, መጸአ.
- Alternative roots for ambiguous shapes in the verb list.

## 1.0.0
- All verb forms of Raz Ch. 5: types A–D, nine derivations, weak and irregular roots, object suffixes, negation,
  compounds; Ge'ez spelling layer; guesser; corpus-trained ranking; pure-Python runtime.
