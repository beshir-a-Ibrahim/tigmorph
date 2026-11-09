"""Gold-standard regression tests (Raz 1973, Ch. 5).  Run: pytest -q"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import pytest
from tigmorph.gold import parse
from tigmorph.analyzer import Analyzer
from eval_gold import in_scope, expected, match

HERE = os.path.join(os.path.dirname(__file__), '..')
F, _, _ = parse(os.path.join(HERE, 'data', 'gold', 'raz_ch5.gold'))
A = Analyzer()
SCOPE = os.environ.get('TIGMORPH_SCOPE', 'all')
CASES = [f for f in F if in_scope(f, SCOPE)]


@pytest.mark.parametrize('f', CASES, ids=[f'{c.lemma}:{c.tense}.{c.person}{">" + c.obj if c.obj else ""}:{c.form}' for c in CASES])
def test_geez(f):
    e = expected(f)
    assert any(match(a, f, e) for a in A.analyze(f.fidel, guess=False)), [str(a) for a in A.analyze(f.fidel)[:5]]


@pytest.mark.parametrize('f', CASES, ids=[f'{c.lemma}:{c.form}' for c in CASES])
def test_guesser(f):
    e = expected(f)
    assert any(match(a, f, e) for a in A.analyze(f.fidel, guess='only', n=400))


def test_generate_qanṣa():
    assert ('ləqannəṣ', 'ልቀንጽ') in A.generate('q-n-ṣ', dict(Type='A', Deriv='Base', TAM='Impf', Subj='3SgM'))


def test_jussive_imperative_distinct():
    tams = {a.tags['TAM'] for a in A.analyze('ቅነጽ')} | {a.tags['TAM'] for a in A.analyze('ልቅነጽ')}
    assert {'Jus', 'Imp'} <= tams
