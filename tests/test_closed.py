"""Closed-class words and clitics (Raz Ch. 3, 4, 7, 8): every gold form must get its analysis."""
import os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from eval_closed import load, ok
from tigmorph.analyzer import Analyzer
from tigmorph.fidel import latin_to_fidel

GOLD = load(os.path.join(os.path.dirname(__file__), '..', 'data', 'gold', 'raz_closed.gold'))
A = Analyzer()


@pytest.mark.parametrize('form,lemma,pos,feats,src', GOLD, ids=[g[0] for g in GOLD])
def test_closed(form, lemma, pos, feats, src):
    an = A.analyze(latin_to_fidel(form), n=30)
    assert any(ok(a, lemma, pos, feats) for a in an), [str(a) for a in an[:5]]
