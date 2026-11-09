"""Nouns (Raz Ch. 2 lexicon: singular, plural, possessive forms) and deverbal nominals (§ 2.7)."""
import os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from eval_nominal import nominal_gold, noun_gold
from tigmorph.analyzer import Analyzer
from tigmorph.fidel import latin_to_fidel

A = Analyzer()
NOUNS = list(noun_gold())
DEV = list(nominal_gold())


@pytest.mark.parametrize('form,lemma,feats', NOUNS, ids=[g[0] for g in NOUNS])
def test_noun(form, lemma, feats):
    if form == 'ʼaddāmātāt':
        pytest.skip('double plural, not modelled')
    an = A.analyze(latin_to_fidel(form), n=40)
    assert any(a.root_latin == lemma and all(a.tags.get(k) == v for k, v in feats.items()) for a in an)


@pytest.mark.parametrize('form,root,typ,der,tam,gn,src', DEV, ids=[g[0] for g in DEV])
def test_deverbal(form, root, typ, der, tam, gn, src):
    an = A.analyze(latin_to_fidel(form), guess=True, n=40)
    assert any(a.root_latin == root and a.tags.get('TAM') == tam and a.tags.get('Subj', '')[1:] == gn for a in an)
