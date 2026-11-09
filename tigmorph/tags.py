"""Tag symbols: each Key=Value tag is one private-use character in the FSTs."""

TAG_ORDER = ['Type', 'Deriv', 'TAM', 'Subj', 'Obj', 'Neg', 'Colloq', 'Cmp']
_TAG_VALUES = {
    'Type': ['A', 'B', 'C', 'D'],
    'Deriv': ['Base', 'tə', 'ʼa', 'ʼat', 'ʼatta', 'ʼan', 'ʼas', 'ʼattan', 'ʼattas', 'ʼasta'],
    'TAM': ['Perf', 'Impf', 'Jus', 'Imp', 'PartAct', 'PartPass', 'Agent', 'Inf', 'Instr'],
    'Subj': ['1Sg', '2SgM', '2SgF', '3SgM', '3SgF', '1Pl', '2PlM', '2PlF', '3PlM', '3PlF'],
    'Obj': ['1Sg', '2SgM', '2SgF', '3SgM', '3SgF', '1Pl', '2PlM', '2PlF', '3PlM', '3PlF'],
    'Neg': ['Yes'], 'Colloq': ['Yes'], 'Cmp': ['Yes'],
}
TAG2CH, CH2TAG = {}, {}
_cp = 0xE000
for k in TAG_ORDER:
    for v in _TAG_VALUES[k]:
        TAG2CH[(k, v)] = chr(_cp); CH2TAG[chr(_cp)] = (k, v); _cp += 1


def tagstr(tags):
    return ''.join(TAG2CH[(k, tags[k])] for k in TAG_ORDER if k in tags and tags[k])


