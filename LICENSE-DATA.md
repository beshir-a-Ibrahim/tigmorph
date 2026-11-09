# Data licences

The **code** (everything in `tigmorph/*.py`, `tools/`, `tests/`) is under the MIT licence (`LICENSE`).

The **data** is released under the least restrictive licence each source allows:

| Files | Licence | Why |
|---|---|---|
| `data/lexicon/verbs.tsv`, `verbs_lh.tsv`, `extra/lh_alt.tsv`, `data/source/tigre_verbs.xlsx` | **CC0 1.0** (public domain dedication) | verb list compiled by the project team |
| `data/lexicon/closed_class.tsv`, `raz_nouns.tsv`, `compounds.tsv`, `demote.tsv`, `not_verbs.tsv`, `gloss_override.tsv`, `reviewed_roots.tsv`; `data/gold/*` | **CC0 1.0** | grammatical facts and word forms described in Raz (1973), compiled by the project team; please cite Raz (see `CITATION.cff`) |
| `data/wiktionary/tig-wiktionary.xml`, `data/lexicon/nouns.tsv`, `wikt_entries.tsv`, `wikt_glosses.tsv`, `compounds_wiktionary.tsv`, `extra/wiktionary_verbs.tsv`, `contrib/wiktionary_verbs_to_check.xlsx` | **CC BY-SA 4.0** | derived from the Tigre Wiktionary (Wikimedia Incubator, Wt/tig); Wiktionary content is CC BY-SA, so derived data must keep that licence. Attribution: "Tigre Wiktionary contributors". |
| `data/lexicon/extra/corpus_roots.tsv`, `tigmorph/fst/ranker.json`, `tigmorph/fst/standard.tsv` (spelling table), `contrib/unknown_words.xlsx`, `contrib/annotation_sheet.xlsx` | **CC BY 4.0** | derived from the BeitTigreAI Tigre monolingual corpus (CC BY 4.0): https://huggingface.co/datasets/BeitTigreAI/tigre-data-monolingual-text |
| `tigmorph/fst/*` (the compiled analyzer data shipped with the package) | **CC BY-SA 4.0** | built from all of the above, including Wiktionary data |

In practice: you can use, change and redistribute everything, also commercially. If you redistribute the
Wiktionary-derived files or the compiled `tigmorph/fst/` data, credit the sources above and keep the CC BY-SA 4.0
licence on those files. The code itself stays MIT.

The corpus itself is not included; download it from the link above (see README, "Rebuilding").
Raz's thesis text is not included; `tools/extract_raz_sentences.py` rebuilds the running-text test set from your
own copy.
