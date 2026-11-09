"""tigmorph analyzer: Ge'ez (or Raz Latin) word -> ranked morphological analyses.

Pure Python at run time: the compiled transducers in tigmorph/fst/ are read by tigmorph.runtime.
"""
import os, unicodedata
from dataclasses import dataclass

from . import runtime as R
from .tags import CH2TAG, tagstr
from .fidel import decompose, to_fidel
from .nominal import poss_splits, plural_splits
from .paradigm import NOMINAL_TAMS
import csv, re

# light verbs of compounds (§ 5.11): (root, derivative) -> lemma
LIGHT = {('b-h-l', 'Base'): 'bela', ('b-h-l', 'ʼa'): 'ʼabala', ('b-h-l', 'ʼatta'): 'ʼattabala',
         ('w-d-y', 'Base'): 'wada', ('g-ʼ-y', 'Base'): 'gaʼa'}
SEP = re.compile(r'[\s፡:]+')


@dataclass
class Analysis:
    root: str          # Ge'ez radicals, e.g. ቅ-ት-ል
    root_latin: str
    tags: dict
    raz: str           # Raz transcription of the word
    weight: float
    guess: bool = False

    gloss: str = ''
    grammar_weight: float = 0.0     # cost from the grammar alone (before corpus ranking)

    def __str__(self):
        if 'POS' in self.tags:
            t = ' '.join(f'{k}={v}' for k, v in self.tags.items() if k != 'POS')
            gl = f'  "{self.gloss}"' if self.gloss else ''
            return f"{self.root}  {self.tags['POS']}  {t}  ⟨{self.raz}⟩{gl}  ({self.weight:.2f})"
        if self.tags.get('TAM') in NOMINAL_TAMS:
            tg = {('Num' if k == 'Subj' else k): (v[1:] if k == 'Subj' else v) for k, v in self.tags.items()}
            t = ' '.join(f'{k}={v}' for k, v in tg.items())
            gl = f'  "{self.gloss}"' if self.gloss else ''
            return f"{self.root}  V>N  {t}  ⟨{self.raz}⟩" + ('  Guess=Yes' if self.guess else '') + gl + f"  ({self.weight:.2f})"
        t = ' '.join(f'{k}={v}' for k, v in self.tags.items() if k not in ('Neg', 'Colloq', 'Cmp')) + \
            ''.join(f' {k}=Yes' for k in ('Neg', 'Colloq') if self.tags.get(k))
        cmp_ = f"  Cmp={self.tags['Cmp']}" if self.tags.get('Cmp') else ''
        gl = f'  "{self.gloss}"' if self.gloss else ''
        return f"{self.root}  V  {t}{cmp_}  ⟨{self.raz}⟩" + ('  Guess=Yes' if self.guess else '') + gl + f"  ({self.weight:.2f})"


def normalize_geez(word):
    """Canonical fidel: ሠ→ሰ, ኀ→ሐ, ፀ→ጸ etc.; strip punctuation."""
    out = []
    for ch in unicodedata.normalize('NFC', word):
        d = decompose(ch)
        if not d:
            continue
        cons, order, vowel, lab = d
        if lab:
            out.append(to_fidel(cons, '')); out.append(to_fidel('w', vowel))
            continue
        if ch in ('ኣ', 'ዓ', 'ሓ', 'ሃ'):           # 4th-order laryngals are kept: ORTH has them as variants
            out.append(ch); continue
        out.append(to_fidel(cons, vowel if order != 6 else ''))
    return ''.join(out)


def _split_root(s):
    out, i = [], 0
    while i < len(s):
        if s[i:i + 2] in ('č̣', 'p̣'):
            out.append(s[i:i + 2]); i += 2
        else:
            out.append(s[i]); i += 1
    return out


class Analyzer:
    def __init__(self, rebuild=False, directory=R.FST_DIR):
        if rebuild or not os.path.exists(os.path.join(directory, 'morph.bin')):
            from .build import build
            build(out=directory)
        self.orth_inv = R.Fst('orth', inverted=True, directory=directory)
        self.morph_inv = R.Fst('morph', inverted=True, directory=directory)
        self.lex = {k: R.Fst('lex_' + k, directory=directory) for k in ('exact', 'other', 'guess')}
        self._gen = None
        self.ranker = None
        rp = os.path.join(directory, 'ranker.json')
        if os.path.exists(rp):
            import json, math
            m = json.load(open(rp, encoding='utf-8'))
            self.ranker = m
            self._log = math.log
        gp = os.path.join(directory, 'glosses.json')
        import json as _json
        self.glosses = _json.load(open(gp, encoding='utf-8')) if os.path.exists(gp) else {}
        cl = os.path.join(directory, 'closed.json')
        self.closed = _json.load(open(cl, encoding='utf-8')) if os.path.exists(cl) else {}
        np_ = os.path.join(directory, 'nouns.json')
        self.nouns = _json.load(open(np_, encoding='utf-8')) if os.path.exists(np_) else {}
        self.compounds = {}
        cp = os.path.join(directory, 'compounds.tsv')
        if os.path.exists(cp):
            for r in csv.DictReader(open(cp, encoding='utf-8'), delimiter='\t'):
                self.compounds.setdefault((normalize_geez(r['first'].replace(' ', '')), r['verb']), r['gloss'])

    def _decode(self, raz, upper, w, guess):
        root = ''.join(ch for ch in upper if ch not in CH2TAG)
        tags = {}
        for ch in upper:
            if ch in CH2TAG:
                k, v = CH2TAG[ch]; tags[k] = v
        rl = _split_root(root)
        gl = '' if guess else self.glosses.get(f"{'-'.join(rl)}|{tags.get('Type')}|{tags.get('Deriv')}", '')
        return Analysis(root='-'.join(to_fidel(c, '') for c in rl), root_latin='-'.join(rl), tags=tags,
                        raz=raz, weight=w, guess=guess, gloss=gl)

    def _run(self, word, latin, guess, n, normalize=True, rank=True):
        res = {}

        def collect(kind, is_guess):
            if latin:      # word is already Raz transcription: skip the spelling layer
                paths = [(word, up, w) for _, up, w in R.cascade(word, _IDENT, self.morph_inv, self.lex[kind], nbest=n)]
            else:
                paths = R.cascade(word, self.orth_inv, self.morph_inv, self.lex[kind], nbest=n)
            for raz, up, w in paths:
                a = self._decode(raz, up, w, is_guess)
                r = a.root_latin.split('-')
                if is_guess and ((len(r) == 4 and r[1] == r[2]) or (len(r) == 5 and r[2] == r[3])):
                    continue        # quadri-/quinqueradicals never geminate (§ 5.9)
                key = (a.root_latin, tuple(sorted(a.tags.items())), a.raz)
                if key not in res or res[key].weight > w:
                    if not (is_guess and key in res):
                        res[key] = a

        if guess != 'only':
            collect('exact', False)
            collect('other', False)
        if (guess == 'auto' and not res) or guess is True or guess == 'only':
            collect('guess', True)
        if not rank:
            for a in res.values():
                a.grammar_weight = a.weight
            return list(res.values())
        return self.rank(list(res.values()), normalize)

    def rank(self, analyses, normalize=True):
        """Re-rank with corpus-learned priors (tools/train_ranker.py):
        score = λ·grammar cost − log P(stem) − log P(cell); reported relative to the best analysis."""
        for a in analyses:
            a.grammar_weight = a.weight
        m = self.ranker
        if m and analyses:
            L = self._log
            for a in analyses:
                if a.tags.get('POS') in CLOSED_POS and getattr(a, 'src', '') != 'nominal':      # function words: few word types each, so the type-based
                    a.weight = m['lam'] * a.grammar_weight + CLOSED_SCORE   # stem/cell priors do not apply
                    continue
                stem, td, cell = rank_keys(a.root_latin, a.tags)
                lp_s = L((m['stem'].get(stem, 0) + m['beta'] * m['td'].get(td, 1e-6)) / (m['n_stem'] + m['beta']))
                lp_c = L((m['cell'].get(cell, 0) + m['alpha']) / (m['n_cell'] + m['alpha'] * m['n_cells']))
                a.weight = m['lam'] * a.grammar_weight - lp_s - lp_c
            if normalize:
                best = min(a.weight for a in analyses)
                for a in analyses:
                    a.weight = round(a.weight - best, 3)
        return sorted(analyses, key=lambda a: (a.weight, a.grammar_weight))

    def analyze(self, word, guess='auto', n=50):
        """Analyze a Ge'ez word, or a verb compound such as 'ሰኒ ቤለ' (§ 5.11).
        Returns analyses ranked by weight (lower = better)."""
        parts = [p for p in SEP.split(word.strip()) if p]
        if len(parts) > 1:
            return self.analyze_compound(parts, guess, n)
        g = normalize_geez(word)
        if not g:
            return []
        if guess == 'only':
            return self._run(g, False, 'only', n)
        out = self._word(g, n, clitics=True)
        if (guess == 'auto' and not out) or guess is True:
            out += self._run(g, False, 'only', n, rank=False)
        return self.rank(out)

    def candidates(self, g, n=30):
        """All exact analyses with grammar weights only (for ranker training)."""
        return self._word(normalize_geez(g), n, clitics=True)

    def _closed(self, g):
        out = []
        for lemma, pos, feats, form, w, gloss, lemma_g in self.closed.get(g, []):
            tags = {'POS': pos}
            if feats:
                tags.update(kv.split('=') for kv in feats.split(','))
            out.append(Analysis(lemma_g, lemma, tags, form, w, False, gloss, w))
        return out

    def _nominal(self, g, n):
        """Nouns, adjectives etc. from the Wiktionary lexicon with pronominal suffixes and suffixed plurals,
        and deverbal nominals (participles, infinitives, agent nouns) with pronominal suffixes."""
        out = []
        for stem, pf, c in poss_splits(g):
            for s2, nf, c2 in [(stem, {}, 0.0)] + plural_splits(stem):
                for lemma, pos, number, gloss, w, feats in self.nouns.get(s2, []):
                    ef = dict(kv.split('=') for kv in feats.split(',')) if feats else {}
                    if nf and (pos not in ('NOUN', 'ADJ') or number or 'Poss' in ef):
                        continue
                    if pf and (pos not in ('NOUN', 'ADJ', 'PROPN', 'ADP', 'PRON', 'NUM') or 'Poss' in ef):
                        continue
                    tags = {'POS': pos}
                    if number:
                        tags['Number'] = number
                    tags.update(ef); tags.update(nf); tags.update(pf)
                    raz = lemma + ('+' + nf.get('Plural', 'F' if nf.get('Gender') else '') if nf else '') + \
                        ('+' + pf['Poss'] if pf else '')
                    a = Analysis(_lemma_geez(lemma), lemma, tags, raz, w + c + c2, False, gloss, w + c + c2)
                    a.src = 'nominal'
                    out.append(a)
            if pf:                                         # suffixed deverbal nominal: qərubu, nādqu
                for a in self._run(stem, False, False, n, rank=False):
                    if a.tags.get('TAM') in NOMINAL_TAMS and 'Obj' not in a.tags:
                        a.tags = dict(a.tags, **pf)
                        a.weight += c; a.grammar_weight = a.weight
                        a.raz += '+' + pf['Poss']
                        out.append(a)
        return out

    def _word(self, g, n, clitics, enc=2):
        """Closed-class + verb analyses of g, plus proclitic splits (wa-/ka-, la-, fused prepositions and
        conjunctions) and enclitic splits (-ma, -di, copula -tu/-tom)."""
        closed = self._closed(g)
        verbs = self._run(g, False, False, n, rank=False)
        if closed:                                     # Raz lists the word as a function word: verb readings
            for a in verbs:                            # of the same spelling start with a penalty
                a.weight += VERB_VS_CLOSED
        if g[:1] in ('ይ', 'የ') and len(g) > 2:          # corpus ይዐለ / ይሀለ = ʼiʿala / ʼihalla 'was / is not'
            for a in self._run('ኢ' + g[1:], False, False, n, rank=False):
                if a.tags.get('Neg') == 'Yes' and a.root_latin in NEG_Y_ROOTS:
                    a.raz = ('yə' if g[0] == 'ይ' else 'ya') + a.raz[2:]; a.weight += 0.1; a.grammar_weight = a.weight
                    verbs.append(a)
        out = closed + verbs + self._nominal(g, n)
        if clitics:
            for pre, key, val, latin, cost in PROCLITICS:
                if not (g.startswith(pre) and len(g) > len(pre)):
                    continue
                # wa-/ka- may be followed by la- and a preposition; la- by nothing else; prepositions by la-
                host_cl = {'Cl': 'all', 'Rel': None, 'Prep': 'rel'}[key]
                for h in self._word(g[len(pre):], n, clitics=host_cl, enc=enc):
                    if not _clitic_ok(key, h):
                        continue
                    tags = dict(h.tags)
                    if key == 'Rel' and (tags.get('POS') not in (None, 'COP', 'PREP', 'AUX') or
                                         tags.get('TAM') in NOMINAL_TAMS):
                        k2, v2 = 'Art', 'Def'                      # la- before a nominal is the article
                    else:
                        k2, v2 = key, ('Yes' if key == 'Rel' else val)
                    if k2 in tags:
                        continue
                    tags[k2] = v2
                    out.append(Analysis(h.root, h.root_latin, tags, latin + '-' + h.raz, h.weight + cost, h.guess,
                                        h.gloss, h.weight + cost))
        if enc:
            for suf, key, val, latin, cost in ENCLITICS:
                if not (g.endswith(suf) and len(g) - len(suf) >= 2):
                    continue
                for h in self._word(g[:-len(suf)], n, clitics=clitics, enc=enc - 1):
                    if key in h.tags or h.tags.get('POS') in ('DET', 'CONJ', 'PART', 'COP'):
                        continue
                    if key == 'Cop' and not (h.tags.get('POS') in CLOSED_POS and getattr(h, 'src', '') != 'nominal'):
                        continue                         # copula -ቱ after particles and suffixed forms (§ 4.1.6)
                    out.append(Analysis(h.root, h.root_latin, dict(h.tags, **{key: val}), h.raz + '-' + latin,
                                        h.weight + cost, h.guess, h.gloss, h.weight + cost))
        return out

    def analyze_compound(self, parts, guess='auto', n=50):
        """First element(s) + inflected light verb (bela, ʼabala, ʼattabala, wada, gaʼa)."""
        first = normalize_geez(''.join(parts[:-1]))
        out = []
        for a in self._run(normalize_geez(parts[-1]), False, False, n):
            lv = LIGHT.get((a.root_latin, a.tags.get('Deriv')))
            if not lv:
                continue
            gloss = self.compounds.get((first, lv))
            tags = dict(a.tags, Cmp=' '.join(parts[:-1]))
            out.append(Analysis(a.root, a.root_latin, tags, ' '.join(parts[:-1]) + ' ' + a.raz,
                                a.weight + (0.0 if gloss is not None else 1.0), a.guess, gloss or ''))
        return sorted(out, key=lambda x: x.weight)

    def analyze_latin(self, raz_word, guess='auto', n=50):
        """Analyze a word in Raz transcription."""
        return self._run(unicodedata.normalize('NFC', raz_word), True, guess, n)

    def generate(self, root_latin, tags):
        """root_latin 'q-t-l', tags dict -> list of (Raz form, Ge'ez form)."""
        if self._gen is None:
            d = os.path.dirname(self.orth_inv.__dict__.get('_dir', R.FST_DIR))
            self._gen = (R.Fst('morph'), R.Fst('orth'))
        morph, orth = self._gen
        upper = root_latin.replace('-', '') + tagstr(tags)
        out = {}
        for raz, gz, w in R.cascade(upper, morph, orth, None, nbest=20):
            if raz not in out or out[raz][1] > w:
                out[raz] = (gz, w)
        return [(raz, gz) for raz, (gz, w) in sorted(out.items(), key=lambda x: (x[1][1], x[0]))]


def _lemma_geez(lemma):
    from .fidel import latin_to_fidel
    return lemma if not lemma or '\u1200' <= lemma[0] <= '\u137f' else latin_to_fidel(lemma)


def rank_keys(root_latin, tags):
    """(stem, stem class, cell) used by the corpus ranker, for verbs and for closed-class words."""
    pos = tags.get('POS', 'V')
    cl = '|'.join(tags.get(k, '') for k in ('Cl', 'Rel', 'Encl', 'Prep', 'Cop'))
    if pos == 'V':
        td = f"{tags.get('Type')}|{tags.get('Deriv')}"
        return f"{root_latin}|{td}", td, '|'.join(tags.get(k, '') for k in ('TAM', 'Subj', 'Obj', 'Neg', 'Colloq')) + '|' + cl
    if pos in ('NOUN', 'ADJ', 'PROPN', 'X', 'ADP'):
        td = 'N|' + pos
        return f"{root_latin}|{td}", td, '|'.join([pos] + [tags.get(k, '') for k in ('Number', 'Plural', 'Gender', 'Poss', 'Art')]) + '|' + cl
    td = 'C|' + pos
    return f"{root_latin}|{td}", td, '|'.join([pos] + [tags.get(k, '') for k in ('Poss', 'Art', 'Dem', 'Neg')]) + '|' + cl


VERB_VS_CLOSED = 2.0
NEG_Y_ROOTS = ('w-ʿ-l', 'h-l-l')   # negative written ይ- (ይዐለ 3,931 vs ኢዐለ 890; ይሀለ 740)
CLOSED_SCORE = 6.0
NOUN_SCORE = 8.0              # ranker score of a dictionary noun/adjective reading            # ranker score of a function-word reading (a good verb reading scores about 7-9)
NOUN_POS = ('NOUN', 'ADJ', 'PROPN', 'X', 'ADP')
CLOSED_POS = ('AUX', 'PRON', 'DEM', 'COP', 'DET', 'PART', 'PREP', 'ADJ', 'CONJ', 'SCONJ', 'ADV', 'INTJ', 'NUM')          # a function word's own reading beats a verb reading of the same spelling
# (Ge'ez prefix, tag, value, Raz form, cost); la- is the relative pronoun on verbs (§ 3.6) and the article elsewhere
# costs are small: the corpus ranker's cell priors (which include the clitics) do most of the work
PROCLITICS = [('ወ', 'Cl', 'wa', 'wa', 0.3), ('ከ', 'Cl', 'ka', 'ka', 0.6), ('ለ', 'Rel', 'la', 'la', 0.2)] + \
    [(g, 'Prep', l, l, 1.0) for g, l in (('ዲብ', 'dib'), ('እብ', 'ʼəb'), ('እት', 'ʼət'), ('ምን', 'mən'),
                                       ('እግል', 'ʼəgəl'), ('ክምሰል', 'kəmsal'), ('ክም', 'kəm'), ('ሐቆ', 'ḥaqo'),
                                       ('እንዴ', 'ʼənde'), ('እንዶ', 'ʼəndo'))]
# enclitics: -ma 'also, even', -di 'indeed', the copula -tu / -tom (§ 4.1.6, written attached in the corpus)
ENCLITICS = [('መ', 'Encl', 'ma', 'ma', 0.5), ('ዲ', 'Encl', 'di', 'di', 1.0),
             ('ቱ', 'Cop', 'tu', 'tu', 1.0), ('ቶም', 'Cop', 'tom', 'tom', 1.0)]


def _clitic_ok(key, h):
    pos = h.tags.get('POS', 'V')
    if key == 'Cl':
        return 'Cl' not in h.tags
    if key == 'Prep':                                 # fused conjunction/preposition before a verb (ምንገብእ, ዲብለትፈናተ)
        return 'Prep' not in h.tags and (pos in ('V', 'COP', 'ADV', 'AUX') and h.tags.get('TAM') != 'Imp')
    if key == 'Rel':                                  # la-: relative before a verb, copula or suffixed preposition,
        if pos == 'V':                                # article before nominals (§ 2.11, § 3.6)
            return h.tags.get('TAM') in ('Perf', 'Impf') + NOMINAL_TAMS
        if pos == 'COP':
            return h.tags.get('Person') == '3' and 'Neg' not in h.tags and 'Rel' not in h.tags
        if pos in ('PREP', 'AUX'):
            return 'Poss' in h.tags
        return pos in ('NOUN', 'ADJ', 'NUM', 'PRON', 'X') and h.tags.get('PronType') in (None, 'Poss', 'Ind')
    return True


class _Identity:
    """Identity 'transducer' over any label: lets cascade() start from Raz transcription."""
    start = 0
    final = {0: 0.0}

    def arcs(self, s, label):
        return ((label, 0.0, 0),) if label else ()


_IDENT = _Identity()
