# tigmorph tag scheme

Readable tags that use Raz's own terms (Raz 1973, *A Descriptive Study of Tigre Grammar*).
A mapping to UniMorph is given at the end for interoperability.

## Fields

| Field | Values | Raz term |
|---|---|---|
| `Root` | Ge'ez radicals, e.g. `ቅ-ት-ል` (+ Latin `q-t-l`) | root |
| `POS` | `V` for finite verbs; other classes below | |
| `Type` | `A` `B` `C` `D` | types A–D (§ 5.1) |
| `Rad` | `3` `4` `5` | tri-/quadri-/quinqueradical |
| `Deriv` | `Base` `tə` `ʼa` `ʼat` `ʼatta` `ʼan` `ʼas` `ʼattan` `ʼattas` `ʼasta` | prefixed derivatives (§ 5.2.1) |
| `TAM` | `Perf` `Impf` `Jus` `Imp` | perfect, imperfect, jussive, imperative |
| `Subj` | `1Sg 2SgM 2SgF 3SgM 3SgF 1Pl 2PlM 2PlF 3PlM 3PlF` | person |
| `Obj` | same values, or absent | pronominal suffix (§ 5.12) |
| `Neg` | `Yes` | negation ʼi- (§ 5.3.3) |
| `Colloq` | `Yes` | prefixless imperfect (§ 5.3.4) |
| `Cmp` | first element, e.g. `ሰኒ` | verb compound (§ 5.11) |
| `Guess` | `Yes` | root not in lexicon (guesser) |

ASCII aliases for code and file names: `tə=T`, `ʼa=A`, `ʼat=AT`, `ʼatta=ATTA`, `ʼan=AN`,
`ʼas=AS`, `ʼattan=ATTAN`, `ʼattas=ATTAS`, `ʼasta=ASTA`.

## Output example

```
$ python3 -m tigmorph -n 2 ልቀትሎ
ልቀትሎ
    ቅ-ት-ል  V  Type=A Deriv=Base TAM=Impf Subj=3PlM  ⟨ləqatlo⟩  "to kill"  (0.00)
    ቅ-ት-ል  V  Type=A Deriv=Base TAM=Impf Subj=3SgM Obj=3SgM  ⟨ləqattəllo⟩  "to kill"  (1.37)
```

The number in brackets is the ranking score relative to the best reading (0.00 = best).

The Raz transcription ⟨…⟩ shows what Ge'ez spelling hides (gemination, ə), which is why the two
readings above look identical in Ge'ez.

## UniMorph mapping

| tigmorph | UniMorph |
|---|---|
| `Perf` / `Impf` / `Jus` / `Imp` | `PFV` / `IPFV` / `JUS` / `IMP` |
| `Subj=3SgM` | `3;SG;MASC` |
| `Obj=3SgF` | `ACC(3,SG,FEM)` |
| `Neg=Yes` | `NEG` |
| `Deriv=tə` | `PASS` or `REFL` (lexical) |
| `Deriv=ʼa`, `ʼat`, `ʼatta` | `CAUS` |
| `Type=C` | `RECP` when reciprocal; otherwise unmarked |
| `Type=D` | `ITER` |

## Phase 3 tags (v2.0): every word class

Readings of words that are not finite verbs carry `POS`. The class codes follow Universal Dependencies where they can.

| Tag | Values | Meaning |
|---|---|---|
| `POS` | `NOUN`, `ADJ`, `PROPN`, `PRON`, `DEM`, `COP`, `AUX`, `PREP`, `ADP`, `CONJ`, `SCONJ`, `ADV`, `NUM`, `INTJ`, `DET`, `PART`, `X` | word class (`PREP` = Raz's prepositions, `ADP` = Wiktionary's) |
| `TAM` (verb-made nominals, shown as `V>N`) | `PartAct`, `PartPass`, `Agent`, `Inf`, `Instr` | active / passive participle, agent noun, infinitive, instrument noun (Raz § 2.7); gender and number are shown as `Num=SgM` etc. |
| `Poss` | `1Sg` … `3PlF` | pronoun ending: "my, your, his …" on nouns; "to him, from us …" on prepositions |
| `Number` | `Pl` | plural noun; `Plural=āt/otāt/ot/ač/ām/at/Broken` gives the plural type |
| `Gender` | `M`, `F` | lexical gender (Raz Ch. 2), or feminine adjective in -ət |
| `Art` | `Def` | article la- (§ 2.11), written attached or fused with a preposition (እተ = ʼət + la) |
| `Rel` | `Yes` | relative la- before a verb, the copula or a preposition with an ending (§ 3.6) |
| `Cl` | `wa`, `ka` | attached ወ- "and", ከ- "and so, then" |
| `Prep` | `dib`, `ʼəb`, `ʼət`, `mən`, `ʼəgəl`, `kəm`, `kəmsal`, `ḥaqo`, `ʼənde`, `ʼəndo` | preposition or conjunction written attached to the next word |
| `Encl` | `ma`, `di` | -መ "also, even", -ዲ "indeed" |
| `Cop` | `tu`, `tom` | copula written attached (ክምሰልቱ) |
| `Dem` | `ʼəlli` … | preposition fused with a demonstrative (እብሊ = ʼəbbəlli) |
| `PronType`, `Person`, `NumType`, `Deixis`, `Expl`, `Subord` | | pronoun type, person, numeral type, near/far, explicative copula tətu, subordinate copula ʼəntu |

UniMorph: `Poss=3SgM` → `PSS3SM`; `Number=Pl` → `PL`; `Art=Def` → `DEF`; `PartAct`/`PartPass` → `V.PTCP;ACT`/`V.PTCP;PASS`; `Inf` → `V.MSDR`.
