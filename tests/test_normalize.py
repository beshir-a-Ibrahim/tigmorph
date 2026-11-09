import json
import pytest
from tigmorph import Normalizer, normalize_chars
from tigmorph.normalize import _canon, cli

N = Normalizer()

CASES = [
    ('ህለ', 'ሀለ'), ('ኢዐለ', 'ይዐለ'), ('የዐለ', 'ይዐለ'), ('ከፎ', 'ከአፎ'), ('ኣምር', 'አምር'),
    ('ሠብ', 'ሰብ'), ('ቀድር', 'ቀድር'),
]


@pytest.mark.parametrize('w,std', CASES)
def test_words(w, std):
    assert N(w) == std


def test_reviewed_pairs():
    assert N('ቃድር') == 'ቀድር'                 # reviewed: same word
    assert N('ፋግር') == 'ፋግር'                 # reviewed: different words, never merged
    assert Normalizer('full')('ፋግር') == 'ፋግር'


def test_form_pairs_only_at_full():
    assert N('ብዙሕ') == 'ብዙሕ'
    assert Normalizer('full')('ብዙሕ') == 'ብዞሕ'


def test_chars():
    assert normalize_chars('ሰብ፡ዓድ::  ሰብ , ዓድ.') == 'ሰብ ዓድ። ሰብ፣ ዓድ።'
    assert Normalizer('chars')('ህለ') == 'ህለ'


def test_idempotent():
    import os
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gold', 'raz_closed.gold')
    text = open(path, encoding='utf-8').read()
    once = Normalizer('full')(text)
    assert Normalizer('full')(once) == once
    once = N(text)
    assert N(once) == once


def test_canon():
    assert _canon('ህለ') == _canon('ሀለ')
    assert _canon('ለለአርኤ') == _canon('ለለርኤ')
    assert _canon('ቃድር') != _canon('ቀድር')


def test_table_safe_rows_are_spelling():
    import csv
    from tigmorph.normalize import DEFAULT_TABLE
    for r in csv.DictReader(open(DEFAULT_TABLE, encoding='utf-8'), delimiter='\t'):
        if r['safe'] == 'yes' and r['kind'] != 'reviewed':
            assert r['kind'] == 'spelling'
            assert _canon(r['variant']) == _canon(r['standard'])


def test_cli_jsonl(tmp_path):
    src = tmp_path / 'in.jsonl'
    src.write_text(json.dumps({'id': 1, 'text': 'ህለ ኢዐለ'}, ensure_ascii=False) + '\n', encoding='utf-8')
    out = tmp_path / 'out.jsonl'
    cli([str(src), '-o', str(out), '--keep-original', '--log', str(tmp_path / 'log.tsv')])
    r = json.loads(out.read_text(encoding='utf-8'))
    assert r == {'id': 1, 'text': 'ሀለ ይዐለ', 'text_original': 'ህለ ኢዐለ'}
    assert 'ህለ\tሀለ\t1' in (tmp_path / 'log.tsv').read_text(encoding='utf-8')
