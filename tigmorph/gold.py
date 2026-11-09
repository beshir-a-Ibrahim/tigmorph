"""Parser for the tigmorph gold format (data/gold/*.gold)."""
import re
from dataclasses import dataclass, field
from .fidel import latin_to_fidel

SG = ['1sg', '2sm', '2sf', '3sm', '3sf']
PL = ['1pl', '2pm', '2pf', '3pm', '3pf']
IMP = ['2sm', '2sf', '2pm', '2pf']


@dataclass
class GoldForm:
    form: str               # Raz Latin
    fidel: str              # Ge'ez (mechanical)
    lemma: str
    root: str
    type: str
    deriv: str
    tense: str              # perf impf juss imp
    person: str             # 1sg … 3pf
    obj: str = ''           # object person or ''
    neg: bool = False
    colloq: bool = False
    tier: str = 'attested'  # attested | rule
    fix: str = ''
    from_ij: bool = False
    sec: str = ''
    cls: str = ''
    gloss: str = ''

    def key(self):
        return (self.root, self.type, self.deriv, self.tense, self.person, self.obj, self.neg)


def _variants(cell):
    out = []
    for v in cell.split(','):
        v = v.strip()
        if not v or v == '-':
            continue
        if '(ə)' in v:
            out += [v.replace('(ə)', 'ə'), v.replace('(ə)', '')]
        else:
            out.append(v)
    return out


def parse(path):
    forms, compounds, lemmas = [], [], []
    cur = {}
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        fix = ''
        tier = 'attested'
        m = re.search(r'\s+\[(fix:.*|rule.*|prefixless.*|-ne variant.*)\]\s*$', line)
        if m:
            tag = m.group(1)
            if tag.startswith('fix:'):
                fix = tag[4:].strip()
            elif tag.startswith('rule'):
                tier = 'rule'
            line = line[:m.start()]
        if line.startswith('@ '):
            parts = [p.strip() for p in line[2:].split('|')]
            cur = dict(lemma=parts[0].split('.')[0])
            for p in parts[1:]:
                k, _, v = p.partition('=')
                cur[k.strip()] = v.strip()
            lemmas.append(dict(cur))
            continue
        if line.startswith('cmp:'):
            first, verb, gloss = [p.strip() for p in line[4:].split('|')]
            compounds.append(dict(first=first, verb=verb, gloss=gloss))
            continue
        if line.startswith('cmpform:'):
            form, parts, slot, gloss = [p.strip() for p in line[8:].split('|')]
            compounds.append(dict(form=form, parts=parts, slot=slot, gloss=gloss))
            continue
        slot, _, rest = line.partition(':')
        slot = slot.strip()
        neg = slot.startswith('neg.')
        colloq = slot.startswith('colloq.')
        s = slot.split('.', 1)[1] if (neg or colloq) else slot
        # single cell?  e.g. impf.3sm>3sm
        m = re.fullmatch(r'(perf|impf|juss|ij|imp)\.(\w+?)(?:>(\w+))?', s)
        base = dict(lemma=cur.get('lemma', ''), root=cur.get('root', ''), type=cur.get('type', ''),
                    deriv=cur.get('deriv', ''), sec=cur.get('sec', ''), cls=cur.get('class', ''),
                    gloss=cur.get('gloss', ''), neg=neg, colloq=colloq, tier=tier, fix=fix)
        tenses = lambda t: ['impf', 'juss'] if t == 'ij' else [t]
        if m:
            t, pers, obj = m.group(1), m.group(2), m.group(3) or ''
            for tt in tenses(t):
                for v in _variants(rest):
                    forms.append(GoldForm(form=v, fidel=latin_to_fidel(v), tense=tt, person=pers, obj=obj, **base))
            continue
        t = s
        if t == 'imp':
            cells = rest.split()
            for k, c in enumerate(cells[:4]):
                for v in _variants(c):
                    forms.append(GoldForm(form=v, fidel=latin_to_fidel(v), tense='imp', person=IMP[k], **base))
            continue
        sg, _, pl = rest.partition('|')
        sgc, plc = sg.split(), pl.split()
        for tt in tenses(t):
            for persons, cells in ((SG, sgc), (PL, plc)):
                for k, c in enumerate(cells[:5]):
                    for v in _variants(c):
                        forms.append(GoldForm(form=v, fidel=latin_to_fidel(v), tense=tt, person=persons[k],
                                              from_ij=(t == 'ij'), **base))
    # every lemma header is itself a perfect 3m.sg citation form: add it when not given explicitly
    have = {f.lemma for f in forms if f.tense == 'perf' and f.person == '3sm' and not f.obj and not f.neg}
    for L in lemmas:
        if L['lemma'] not in have and L.get('class') != 'irregular' or (L['lemma'] not in have and L['lemma'] == 'ʿala'):
            v = L['lemma']
            forms.append(GoldForm(form=v, fidel=latin_to_fidel(v), lemma=v, root=L.get('root', ''), type=L.get('type', ''),
                                  deriv=L.get('deriv', ''), tense='perf', person='3sm', tier='citation',
                                  sec=L.get('sec', ''), cls=L.get('class', ''), gloss=L.get('gloss', '')))
            have.add(v)
    # 'juss.1pl' single-cell overrides an 'ij' 1pl: drop the ij-derived jussive 1pl when an override exists
    over = {f.lemma for f in forms if f.tense == 'juss' and f.person == '1pl' and not f.obj and not f.from_ij}
    seen, out = set(), []
    for f in forms:
        if f.from_ij and f.tense == 'juss' and f.person == '1pl' and not f.obj and f.lemma in over:
            continue
        k = (f.lemma, f.form, f.tense, f.person, f.obj, f.neg, f.colloq)
        if k in seen:
            continue
        seen.add(k)
        out.append(f)
    return out, compounds, lemmas
