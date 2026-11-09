"""Spelling normalization for Tigre text (tigmorph 2.1).

Corpora collected from many sources write the same word in several ways (ሀለ / ህለ, ይዐለ / ኢዐለ, ለአፍህም / ለፍህም,
ā written or not, ሠ for ሰ, ፡ between words ...). The Normalizer writes every word in one standard spelling, so that
NLP models see one type per word.

Levels
  chars  character level only: Unicode NFC, letters with the same sound in Tigre (ሠ→ሰ, ፀ→ጸ, ኀ→ሐ), the old word
         separator ፡, punctuation, stray symbol-font characters, spaces.
  safe   chars + word level: a word is rewritten only if (1) tigmorph reads it as the same word (same root or
         lemma, same class, same features, same consonants) as a more frequent spelling, (2) every plausible
         reading agrees on that standard, and (3) the two spellings differ only by a known free alternation of
         Tigre writing: the vowel written on a laryngal (ሀ/ህ, አ/ኣ, ሐ/ሓ, ዐ/ዓ), an inserted አ (ለአፍህም / ለፍህም),
         ኸ/ከ, ቐ/ቀ, and the negative prefix ይ-/የ-/ኢ-. This is the default.
         Pairs confirmed by native-speaker review (kind 'reviewed', fst/standard_review.tsv) are applied too.
  full   chars + every row of the table, including words that differ in other letters (kind 'form', e.g.
         ቃድር / ቀድር) and words with competing readings. Review the table before using this level.

The word-level standard is a table (variant -> standard). The table shipped with the package was learned from the
BeitTigreAI Tigre corpus: in each group of spellings of the same word, the most frequent spelling is the standard.
You can learn a table from your own corpus (Normalizer.learn / `tigmorph normalize --learn`) and edit it by hand.

    from tigmorph import Normalizer
    N = Normalizer()                 # level='safe'
    N.normalize('ህሌት እት ዓድ ...')
"""
import csv, os, re, unicodedata
from collections import Counter, defaultdict

from .fidel import decompose, to_fidel

HERE = os.path.dirname(__file__)
DEFAULT_TABLE = os.path.join(HERE, 'fst', 'standard.tsv')
DEFAULT_REVIEW = os.path.join(HERE, 'fst', 'standard_review.tsv')


def load_review(path=DEFAULT_REVIEW):
    """(variant, standard) -> 'same' | 'different', from a reviewed TSV (lines starting with # are comments)."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        lines = [l for l in f if not l.startswith('#')]
    return {(r['variant'], r['standard']): r['verdict'] for r in csv.DictReader(lines, delimiter='\t')}
WORD = re.compile(r'[ሀ-ፚᎀ-᎙ⶀ-ⷞꬁ-ꬮ]+')

# letters that have the same sound in Tigre: ሠ-row -> ሰ-row, ፀ-row -> ጸ-row, ኀ-row -> ሐ-row
_HOMO = {}
for start, cons in ((0x1220, 's'), (0x1340, 'ṣ'), (0x1280, 'ḥ')):
    for k in range(7):
        ch = chr(start + k)
        d = decompose(ch)
        if d:
            _HOMO[ch] = to_fidel(cons, d[2] if d[1] != 6 else '')

GEEZ = r'[ሀ-ፚ]'


def normalize_chars(text, wordspace=True, punctuation=True):
    """Character-level normalization (level 'chars')."""
    t = unicodedata.normalize('NFC', text)
    t = ''.join(_HOMO.get(c, c) for c in t)
    t = re.sub(r'[-]', '', t)                  # symbol-font bullets pasted from word processors
    if punctuation:
        t = re.sub(rf'({GEEZ})[ \t]*(?:::|፡፡)', r'\1።', t)         # "::" / ፡፡ typed for ።
        t = re.sub(rf'({GEEZ})[ \t]*[:፡][ \t]*$', r'\1።', t, flags=re.M)   # ፡ or : ending a line -> ።
        t = re.sub(rf'({GEEZ})[ \t]*[:፡](?=\s|["«“(])', r'\1፣', t)  # ፡ or : before a space is a comma -> ፣
    if wordspace:
        t = re.sub(r'[ \t]*፡[ \t]*', ' ', t)                 # ፡ between words (old word separator) -> space
    if punctuation:
        t = re.sub(rf'(?<={GEEZ})\.(?=\s|$|["”’»)])', '።', t)   # full stop after a Tigre word -> ።
        t = re.sub(rf'({GEEZ})[ \t]*,(?=\s|$)', r'\1፣', t)    # comma after a Tigre word -> ፣
        t = t.replace('፧', '?')                            # the corpus mostly uses ? (18,320 vs 2,625)
        t = t.replace('።።', '።')
        t = re.sub(r'\s+([።፣፤፥፦?!])', r'\1', t)            # no space before punctuation
    t = re.sub(r'[ \t ​]+', ' ', t)
    return '\n'.join(line.strip() for line in t.split('\n'))


def _skeleton(raz):
    """Consonants of the pronunciation, ignoring what only spelling varies: vowel quality and length, gemination,
    the written ʼa of causatives (laʼafhəm = lafhəm), the negative written y- (yəʿala = ʼiʿala)."""
    if any('\u1200' <= ch <= '\u137f' for ch in raz):
        return raz                                  # dictionary noun stored in Ge'ez: compare as is
    s = raz.replace('-', '')
    s = re.sub(r'^(?:wa|ka|la)*(yə|ya)', lambda m: m.group(0)[:-2] + 'ʼi', s)
    s = s.replace('aʼa', 'a')
    s = re.sub(r'[aāeēiīoōuūə]', '', s)
    return re.sub(r'(.)\1+', r'\1', s)


_LARYNGAL = {'ʼ', 'ʿ', 'h', 'ḥ', 'ḫ'}


def _canon(word):
    """Spelling with the known free alternations of Tigre writing removed: the vowel order written on a
    laryngal (ሀ/ህ, አ/ኣ, ሐ/ሓ/ሔ, ዐ/ዓ), an inserted አ/ኣ inside the word, ኸ/ከ, and the negative prefix
    ይ-/የ-/ኢ- after the proclitics ወ ከ ለ. Two spellings with the same canon differ only in spelling."""
    out = []
    for i, ch in enumerate(word):
        d = decompose(ch)
        if d is None:
            out.append(ch); continue
        cons, order = d[0], d[1]
        if cons in _LARYNGAL and order in (1, 4, 5, 6):
            if cons == 'ʼ' and i > 0:
                continue
            out.append(cons + '*'); continue
        out.append(cons + str(order))
    s = ' '.join(out)
    return re.sub(r'^((?:[wkl]1 )*)(?:y6|y1|ʼ3)\b', r'\1NEG', s)


def _key(a):
    """What makes two spellings 'the same word': root or lemma, class, all features, and the same consonants.
    Different realisations of one cell (bahalat / tibe, fərqat / farīq) stay apart."""
    t = {k: v for k, v in a.tags.items() if k != 'Guess'}
    return (a.root_latin, tuple(sorted(t.items())), _skeleton(a.raz))


class Normalizer:
    def __init__(self, level='safe', table=None, analyzer=None, wordspace=True, punctuation=True):
        if level not in ('chars', 'safe', 'full'):
            raise ValueError("level must be 'chars', 'safe' or 'full'")
        self.level, self.wordspace, self.punctuation = level, wordspace, punctuation
        self.map = {}
        if level != 'chars':
            self.load(table or DEFAULT_TABLE)
        self._A = analyzer

    # ------------------------------------------------------------------ table
    def load(self, path):
        self.map = {}
        if not os.path.exists(path):
            return
        for r in csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'):
            if r['safe'] == 'yes' or self.level == 'full':
                self.map[r['variant']] = r['standard']

    @staticmethod
    def learn(texts, analyzer=None, min_count=2, margin=1.0, out=None, progress=False, review=DEFAULT_REVIEW):
        """Learn a variant -> standard table from an iterable of texts (lines). Returns the rows.
        review: TSV of native-speaker verdicts; 'same' pairs are always applied, 'different' pairs never merged."""
        rev = load_review(review)
        from .analyzer import Analyzer
        A = analyzer or Analyzer()
        cnt = Counter()
        for line in texts:
            cnt.update(WORD.findall(normalize_chars(line)))
        groups = defaultdict(list)          # key of best reading -> [(spelling, count)]
        near = {}                           # spelling -> keys of its plausible readings
        for i, (w, c) in enumerate(cnt.most_common()):
            if c < min_count:
                break
            an = A.analyze(w, guess=False, n=10)
            if not an:
                continue
            groups[_key(an[0])].append((w, c))
            near[w] = {_key(a) for a in an if a.weight <= margin}
            if progress and i % 20000 == 0:
                print('  learned', i, 'word types')
        std_of_key = {k: max(v, key=lambda x: (x[1], -len(x[0])))[0] for k, v in groups.items()}
        rows = []
        for k, v in groups.items():
            if len(v) < 2:
                continue
            std = std_of_key[k]
            cstd = dict(v)[std]
            for w, c in v:
                if w == std:
                    continue
                verdict = rev.get((w, std))
                if verdict == 'different':
                    continue
                if verdict == 'same':
                    kind, safe = 'reviewed', True
                else:
                    kind = 'spelling' if _canon(w) == _canon(std) else 'form'
                    safe = kind == 'spelling' and all(std_of_key.get(k2) == std for k2 in near[w])
                rows.append(dict(variant=w, standard=std, count_variant=c, count_standard=cstd,
                                 kind=kind, safe='yes' if safe else 'no'))
        have = {r['variant'] for r in rows}
        for (w, std), verdict in rev.items():          # reviewed pairs the analyzer did not group
            if verdict == 'same' and w not in have and cnt[w] and cnt[std]:
                rows.append(dict(variant=w, standard=std, count_variant=cnt[w], count_standard=cnt[std],
                                 kind='reviewed', safe='yes'))
        rows.sort(key=lambda r: -r['count_variant'])
        if out:
            with open(out, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, ['variant', 'standard', 'count_variant', 'count_standard', 'kind', 'safe'], delimiter='\t')
                w.writeheader(); w.writerows(rows)
        return rows

    # ------------------------------------------------------------------ apply
    def normalize(self, text, log=None):
        """Normalize a string. If log is a Counter, (original, normalized) word pairs are counted in it."""
        t = normalize_chars(text, self.wordspace, self.punctuation)
        if self.level == 'chars':
            return t
        m = self.map

        def sub(mo):
            w = mo.group()
            s = m.get(w)
            if s is None:
                return w
            if log is not None:
                log[(w, s)] += 1
            return s
        return WORD.sub(sub, t)

    __call__ = normalize


# ---------------------------------------------------------------------- command line
def _open_out(path):
    return open(path, 'w', encoding='utf-8', newline='') if path and path != '-' else None


def _records(path, fmt, field):
    """Yield (record, text) for each record of a file. record is what gets written back."""
    import json
    if fmt == 'txt':
        with open(path, encoding='utf-8') as f:
            for line in f:
                yield line.rstrip('\n'), line.rstrip('\n')
    elif fmt == 'jsonl':
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    yield r, r.get(field) or ''
    elif fmt in ('csv', 'tsv'):
        csv.field_size_limit(1 << 30)
        with open(path, encoding='utf-8', newline='') as f:
            for r in csv.DictReader(f, delimiter=',' if fmt == 'csv' else '\t'):
                yield r, r.get(field) or ''
    elif fmt == 'parquet':
        try:
            import pyarrow.parquet as pq
        except ImportError:
            raise SystemExit('reading parquet needs pyarrow:  pip install pyarrow')
        for batch in pq.ParquetFile(path).iter_batches():
            for r in batch.to_pylist():
                yield r, r.get(field) or ''


def _fmt_of(path, fmt):
    if fmt != 'auto':
        return fmt
    ext = os.path.splitext(path)[1].lower().lstrip('.')
    return {'jsonl': 'jsonl', 'json': 'jsonl', 'csv': 'csv', 'tsv': 'tsv', 'parquet': 'parquet'}.get(ext, 'txt')


def cli(argv=None):
    import argparse, json, sys, time
    from . import __version__
    ap = argparse.ArgumentParser(prog='tigmorph normalize', description='Write Tigre text in one standard spelling.')
    ap.add_argument('inputs', nargs='*', help='input files (txt, jsonl, csv, tsv, parquet); stdin if none')
    ap.add_argument('-o', '--output', help='output file (one input) or directory (several inputs); stdout if none')
    ap.add_argument('--level', default='safe', choices=['chars', 'safe', 'full'])
    ap.add_argument('--table', help='variant -> standard table (TSV); default: the table shipped with tigmorph')
    ap.add_argument('--learn', metavar='TABLE', help='learn a table from the inputs, write it to TABLE and stop')
    ap.add_argument('--min-count', type=int, default=2, help='with --learn: ignore spellings seen fewer times')
    ap.add_argument('--format', default='auto', choices=['auto', 'txt', 'jsonl', 'csv', 'tsv', 'parquet'])
    ap.add_argument('--field', '--column', dest='field', default='text', help='text field of jsonl/csv/tsv/parquet')
    ap.add_argument('--keep-original', action='store_true',
                    help='keep the original text: txt lines become "original<TAB>normalized"; '
                         'records get a FIELD_original field')
    ap.add_argument('--no-wordspace', action='store_true', help='keep ፡ as written')
    ap.add_argument('--no-punctuation', action='store_true', help='keep punctuation as written')
    ap.add_argument('--log', help='write every change with its count (TSV) to this file')
    ap.add_argument('--report', help='write a summary report (Markdown) to this file')
    a = ap.parse_args(argv)
    inputs = a.inputs or ['-']

    if a.learn:
        def texts():
            for p in inputs:
                if p == '-':
                    yield from sys.stdin
                else:
                    for _, t in _records(p, _fmt_of(p, a.format), a.field):
                        yield t
        rows = Normalizer.learn(texts(), min_count=a.min_count, out=a.learn, progress=True)
        print(f'{len(rows)} variants, {sum(r["safe"] == "yes" for r in rows)} safe -> {a.learn}', file=sys.stderr)
        return

    N = Normalizer(level=a.level, table=a.table, wordspace=not a.no_wordspace, punctuation=not a.no_punctuation)
    log = Counter()
    before, after, unknown = Counter(), Counter(), Counter()
    want_stats = bool(a.report)
    t0 = time.time()
    nrec = 0
    for p in inputs:
        fmt = 'txt' if p == '-' else _fmt_of(p, a.format)
        if a.output and len(inputs) > 1:
            os.makedirs(a.output, exist_ok=True)
            base = os.path.splitext(os.path.basename(p))[0]
            outp = os.path.join(a.output, base + ('.txt' if fmt == 'txt' else '.jsonl'))
        else:
            outp = a.output
        f = _open_out(outp) or sys.stdout
        src = ((l.rstrip('\n'), l.rstrip('\n')) for l in sys.stdin) if p == '-' else _records(p, fmt, a.field)
        writer = None
        for rec, text in src:
            nrec += 1
            norm = N.normalize(text, log=log)
            if want_stats:
                before.update(WORD.findall(text)); after.update(WORD.findall(norm))
            if fmt == 'txt':
                f.write((text + '\t' + norm if a.keep_original else norm) + '\n')
            elif fmt in ('csv', 'tsv') and outp and outp.endswith(('.csv', '.tsv')):
                rec = dict(rec)
                if a.keep_original:
                    rec[a.field + '_original'] = text
                rec[a.field] = norm
                if writer is None:
                    writer = csv.DictWriter(f, list(rec), delimiter=',' if outp.endswith('.csv') else '\t')
                    writer.writeheader()
                writer.writerow(rec)
            else:                                            # records are written as JSON lines
                rec = dict(rec)
                if a.keep_original:
                    rec[a.field + '_original'] = text
                rec[a.field] = norm
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + '\n')
        if f is not sys.stdout:
            f.close()
    secs = time.time() - t0

    if a.log:
        with open(a.log, 'w', encoding='utf-8', newline='') as g:
            g.write('original\tnormalized\tcount\n')
            for (w, s), c in log.most_common():
                g.write(f'{w}\t{s}\t{c}\n')
    if a.report:
        from .analyzer import Analyzer
        A = Analyzer()
        for w, c in after.most_common(20000):
            if not A.analyze(w, guess=False, n=1):
                unknown[w] = c
        tok = sum(before.values())
        changed = sum(log.values())
        L = [f'# Normalization report', '',
             f'tigmorph {__version__}, level `{a.level}`, table `{a.table or "built-in"}`, '
             f'word separator {"kept" if a.no_wordspace else "normalized"}, '
             f'punctuation {"kept" if a.no_punctuation else "normalized"}', '',
             f'Inputs: {", ".join(inputs)}  ', f'Records: {nrec:,}  ', f'Time: {secs:.1f} s', '',
             '| | Before | After |', '|---|---:|---:|',
             f'| Word tokens | {tok:,} | {sum(after.values()):,} |',
             f'| Distinct words | {len(before):,} | {len(after):,} |', '',
             f'Word tokens rewritten by the table: {changed:,} ({100 * changed / max(tok, 1):.2f}%), '
             f'{len(log):,} distinct changes.', '',
             '## Most frequent changes', '', '| Original | Normalized | Count |', '|---|---|---:|']
        L += [f'| {w} | {s} | {c:,} |' for (w, s), c in log.most_common(50)]
        L += ['', '## Most frequent words tigmorph does not analyse', '', '| Word | Count |', '|---|---:|']
        L += [f'| {w} | {c:,} |' for w, c in unknown.most_common(50)]
        with open(a.report, 'w', encoding='utf-8') as g:
            g.write('\n'.join(L) + '\n')
