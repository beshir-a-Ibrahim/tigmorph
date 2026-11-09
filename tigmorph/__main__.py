"""Command line:  python -m tigmorph ልቀትል ኢትቅተል   |   python -m tigmorph --latin ləqattəl
                 python -m tigmorph --gen q-t-l Type=A Deriv=Base TAM=Impf Subj=3SgM
                 python -m tigmorph --guess ዘረጠ        (force the guesser)"""
import sys, argparse
from .analyzer import Analyzer


def main(argv=None):
    ap = argparse.ArgumentParser(prog='tigmorph')
    ap.add_argument('words', nargs='*')
    ap.add_argument('--latin', action='store_true', help='input is Raz transcription')
    ap.add_argument('--gen', action='store_true', help='generate: ROOT Key=Val ...')
    ap.add_argument('--guess', action='store_true', help='always include guesser analyses')
    ap.add_argument('--rebuild', action='store_true')
    ap.add_argument('-n', type=int, default=10)
    a = ap.parse_args(argv)
    A = Analyzer(rebuild=a.rebuild)  # rebuild needs pynini
    if a.gen:
        root, *kv = a.words
        tags = dict(x.split('=', 1) for x in kv)
        for raz, gz in A.generate(root, tags):
            print(f'{gz}\t⟨{raz}⟩')
        return
    words = a.words or [w for line in sys.stdin for w in line.split()]
    for w in words:
        res = A.analyze_latin(w, guess=True if a.guess else 'auto') if a.latin else \
            A.analyze(w, guess=True if a.guess else 'auto')
        print(w)
        for r in res[:a.n]:
            print('   ', r)
        if not res:
            print('    (no analysis)')


if __name__ == '__main__':
    main()
