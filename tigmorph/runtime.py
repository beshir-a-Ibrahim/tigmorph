"""Pure-Python runtime for tigmorph's compiled transducers (no pynini/OpenFst needed).

The grammar is compiled with pynini (tigmorph.build) and exported to small binary files
(tigmorph/fst/*.bin).  This module loads them and does weighted lookup by on-the-fly
composition of a word with a cascade  T1 ∘ T2 ∘ (acceptor).

Labels are Unicode code points (0 = epsilon); weights are tropical (lower = better).
"""
import os, json, heapq
from array import array

FST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fst')


class Fst:
    """Arc-indexed transducer. If inverted, input/output labels are swapped on load."""

    def __init__(self, name, inverted=False, directory=FST_DIR):
        meta = json.load(open(os.path.join(directory, name + '.json')))
        n_arcs = meta['arcs']
        raw = {}
        with open(os.path.join(directory, name + '.bin'), 'rb') as fh:
            for key, code in (('src', 'i'), ('ilab', 'i'), ('olab', 'i'), ('dst', 'i'), ('w', 'f')):
                a = array(code)
                a.fromfile(fh, n_arcs)
                raw[key] = a
        self.start = meta['start']
        self.final = {int(k): v for k, v in meta['final'].items()}
        il, ol = (raw['olab'], raw['ilab']) if inverted else (raw['ilab'], raw['olab'])
        # index: state -> {input label -> [(output, weight, next)]}
        idx = {}
        for k in range(n_arcs):
            d = idx.setdefault(raw['src'][k], {})
            d.setdefault(il[k], []).append((ol[k], raw['w'][k], raw['dst'][k]))
        self.idx = idx

    def arcs(self, s, label):
        return self.idx.get(s, {}).get(label, ())


def export(fst, name, directory=FST_DIR):
    """Write a pynini Fst in the runtime format (used at build time only)."""
    os.makedirs(directory, exist_ok=True)
    src, il, ol, dst, w = array('i'), array('i'), array('i'), array('i'), array('f')
    final = {}
    zero = None
    for s in fst.states():
        fw = fst.final(s)
        sw = str(fw)
        if sw not in ('Infinity', 'inf'):
            final[s] = float(sw)
        for a in fst.arcs(s):
            src.append(s); il.append(a.ilabel); ol.append(a.olabel); dst.append(a.nextstate)
            w.append(float(str(a.weight)))
    with open(os.path.join(directory, name + '.bin'), 'wb') as fh:
        for a in (src, il, ol, dst, w):
            a.tofile(fh)
    json.dump(dict(start=fst.start(), final=final, arcs=len(src)), open(os.path.join(directory, name + '.json'), 'w'))


def cascade(word, t1, t2, acc=None, nbest=50, max_pops=300000):
    """n-best paths of  word ∘ t1 ∘ t2 ∘ acc.

    Returns list of (middle, upper, weight) where middle is the output of t1 (= input of t2)
    and upper is the output of t2.  acc (optional) is an acceptor applied to upper.
    """
    word = [ord(c) for c in word]
    n = len(word)
    start = (0, t1.start, t2.start, acc.start if acc else 0)
    heap = [(0.0, 0, start, '', '')]
    seen = set()
    results, keys = [], set()
    counter = 0
    pops = 0
    while heap and len(results) < nbest and pops < max_pops:
        w, _, (i, s1, s2, s3), mid, up = heapq.heappop(heap)
        pops += 1
        key = (i, s1, s2, s3, mid, up)
        if key in seen:
            continue
        seen.add(key)
        if w == float('inf'):
            continue
        # final?
        if i == n and s1 in t1.final and s2 in t2.final and (acc is None or s3 in acc.final):
            # a final state can also have outgoing arcs: record and keep exploring
            fw = w + t1.final[s1] + t2.final[s2] + (acc.final[s3] if acc else 0.0)
            heapq.heappush(heap, (fw, counter, ('F', s1, s2, s3), mid, up)); counter += 1
        if i == 'F':
            if (mid, up) not in keys:
                keys.add((mid, up))
                results.append((mid, up, w))
            continue
        # moves that consume nothing from the word: t2 input-epsilon arcs
        for (y, w2, n2) in t2.arcs(s2, 0):
            for s3n, w3 in _acc_step(acc, s3, y):
                heapq.heappush(heap, (w + w2 + w3, counter, (i, s1, n2, s3n), mid, up + _ch(y))); counter += 1
        # t1 arcs: consume word[i] (or epsilon input)
        labels = [0] + ([word[i]] if i < n else [])
        for lab in labels:
            for (x, w1, n1) in t1.arcs(s1, lab):
                ni = i + (1 if lab else 0)
                if x == 0:
                    heapq.heappush(heap, (w + w1, counter, (ni, n1, s2, s3), mid, up)); counter += 1
                    continue
                for (y, w2, n2) in t2.arcs(s2, x):
                    for s3n, w3 in _acc_step(acc, s3, y):
                        heapq.heappush(heap, (w + w1 + w2 + w3, counter, (ni, n1, n2, s3n), mid + chr(x), up + _ch(y)))
                        counter += 1
    return results


def _ch(y):
    return chr(y) if y else ''


def _acc_step(acc, s, y):
    if acc is None or y == 0:
        return ((s, 0.0),)
    return [(nx, w) for (_, w, nx) in acc.arcs(s, y)]


def transduce(word, t, nbest=20, max_pops=100000):
    """n-best outputs of a single transducer applied to word: list of (output, weight)."""
    word = [ord(c) for c in word]
    n = len(word)
    heap = [(0.0, 0, 0, t.start, '')]
    counter, out, seen, pops = 0, [], set(), 0
    while heap and len(out) < nbest and pops < max_pops:
        w, _, i, s, o = heapq.heappop(heap); pops += 1
        if (i, s, o) in seen:
            continue
        seen.add((i, s, o))
        if i == 'F':
            out.append((o, w)); continue
        if i == n and s in t.final:
            heapq.heappush(heap, (w + t.final[s], counter, 'F', s, o)); counter += 1
        for lab in [0] + ([word[i]] if i < n else []):
            for (x, wa, nx) in t.arcs(s, lab):
                heapq.heappush(heap, (w + wa, counter, i + (1 if lab else 0), nx, o + _ch(x))); counter += 1
    return out
