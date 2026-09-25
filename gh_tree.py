"""Gomory-Hu-Baum nach Gusfield (1990): alle minimalen Schnitte eines ungerichteten Netzes mit n - 1 statt n (n - 1) / 2 Flussberechnungen.

Ein **Gomory-Hu-Baum** hat dieselben Knoten wie das Netz und n - 1 gewichtete Kanten. Zwei Eigenschaften machen ihn zum Schnitt-Verzeichnis des Netzes:
(1) der minimale Schnitt zwischen u und v ist die **kleinste Kante auf dem Baumpfad** von u nach v;
(2) jede Baumkante ist selbst ein minimaler Schnitt: entfernt man sie, zerfällt der Baum in zwei Teile, und die Knotenmengen dieser Teile bilden im Netz einen Schnitt, dessen Kapazität genau das Kantengewicht ist.

Gusfields Verfahren braucht keine Kontraktion: es hält für jeden Knoten einen Elternknoten p[s] (zunächst der Knoten 0) und rechnet für s = 1..n-1 einen Fluss zwischen s und p[s]. Alle Knoten auf der s-Seite des gefundenen
Schnitts, die bisher an p[s] hingen, hängen danach an s; liegt der Elternknoten von p[s] auf der s-Seite, tauschen s und p[s] ihre Plätze (das macht den Baum zu einem echten Schnittbaum).

Aufwand wird in durchsuchten Kanten des Flussverfahrens gezählt (Boykov-Kolmogorov), nie in Sekunden.
"""

from dataclasses import dataclass
from itertools import combinations

import gh_bk
import gh_dinic
import gh_edmonds_karp as ek
import gh_scenario as sc

ALGORITHMS = ("bk", "dinic", "bfs")


def min_cut(net, algorithm="bk"):
    """Minimaler Schnitt zwischen net.s und net.t. Rückgabe (Wert, Knotenmenge der s-Seite, durchsuchte Kanten)."""
    if algorithm == "bk":
        res = gh_bk.bk_maxflow(net)
        scanned = res.scanned_total
    elif algorithm == "dinic":
        res = gh_dinic.dinic(net, keep_flows=False)
        scanned = res.scanned_total
    else:
        res = ek.max_flow(net, rule="bfs", keep_flows=False)
        scanned = res.scanned_total
    return res.value, frozenset(v for v in range(net.n) if res.reach[v]), scanned


@dataclass(frozen=True)
class Step:
    s: int
    t: int
    value: int
    side: frozenset         # Knoten auf der s-Seite des gefundenen Schnitts
    scanned: int
    parent: tuple           # Elternknoten je Knoten NACH diesem Schritt (Wurzel: -1)
    weight: tuple           # Kantengewicht zum Elternknoten je Knoten NACH diesem Schritt
    swapped: bool


@dataclass(frozen=True)
class Tree:
    n: int
    parent: tuple           # Elternknoten je Knoten (Wurzel: -1)
    weight: tuple           # Gewicht der Kante zum Elternknoten (Wurzel: 0)
    steps: tuple            # ein Schritt je Fluss
    scanned: int

    @property
    def flows(self):
        return len(self.steps)

    def edges(self):
        return tuple((i, self.parent[i], self.weight[i]) for i in range(self.n) if self.parent[i] >= 0)

    def adjacency(self):
        adj = [[] for _ in range(self.n)]
        for i, p, w in self.edges():
            adj[i].append((p, w))
            adj[p].append((i, w))
        return adj


def gusfield(graph, algorithm="bk"):
    """Gomory-Hu-Baum (Schnittbaum-Variante nach Gusfield). Knoten 0 ist die Wurzel."""
    n = graph.n
    base = graph.to_net()
    p = [0] * n
    p[0] = -1
    fl = [0] * n
    steps, total = [], 0
    for s in range(1, n):
        t = p[s]
        value, side, scanned = min_cut(sc.with_terminals(base, s, t), algorithm)
        total += scanned
        fl[s] = value
        for i in range(n):
            if i != s and i in side and p[i] == t:
                p[i] = s
        swapped = False
        if p[t] >= 0 and p[t] in side:
            p[s] = p[t]
            p[t] = s
            fl[s] = fl[t]
            fl[t] = value
            swapped = True
        steps.append(Step(s, t, value, side, scanned, tuple(p), tuple(fl), swapped))
    return Tree(n, tuple(p), tuple(fl), tuple(steps), total)


def path(tree, u, v):
    """Knotenfolge im Baum von u nach v."""
    adj = tree.adjacency()
    prev = {u: None}
    stack = [u]
    while stack:
        x = stack.pop()
        if x == v:
            break
        for y, _ in adj[x]:
            if y not in prev:
                prev[y] = x
                stack.append(y)
    out = [v]
    while out[-1] != u:
        out.append(prev[out[-1]])
    return out[::-1]


def query(tree, u, v):
    """Minimaler Schnitt zwischen u und v: die kleinste Kante auf dem Baumpfad. Rückgabe (Wert, Pfad, die Kante (a, b, Gewicht), die ihn bestimmt)."""
    pth = path(tree, u, v)
    w = {}
    for i, p, weight in tree.edges():
        w[(i, p)] = w[(p, i)] = weight
    best = min(((w[(a, b)], a, b) for a, b in zip(pth, pth[1:])), key=lambda x: x[0])
    return best[0], pth, (best[1], best[2], best[0])


def tree_side(tree, a, b):
    """Knotenmenge auf der Seite von `a`, wenn die Baumkante (a, b) entfernt wird."""
    adj = tree.adjacency()
    seen, stack = {a}, [a]
    while stack:
        x = stack.pop()
        for y, _ in adj[x]:
            if (x, y) in ((a, b), (b, a)) or y in seen:
                continue
            seen.add(y)
            stack.append(y)
    return frozenset(seen)


def cut_edges(graph, side):
    """Verbindungen, die zwischen `side` und dem Rest verlaufen: (Index, u, v, Kapazität)."""
    return tuple((i, u, v, c) for i, (u, v, c) in enumerate(graph.edges) if (u in side) != (v in side))


def cut_capacity(graph, side):
    return sum(c for _, _, _, c in cut_edges(graph, side))


def classes(tree, k):
    """Klassen der Knoten, die paarweise mindestens k-verbunden sind (Schnitt >= k): die Komponenten des Baums ohne Kanten unter k. Rückgabe: Klassennummer je Knoten."""
    parent = list(range(tree.n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, p, w in tree.edges():
        if w >= k:
            parent[find(i)] = find(p)
    ids = {}
    return tuple(ids.setdefault(find(i), len(ids)) for i in range(tree.n))


def threshold_components(graph, k):
    """Komponenten des Netzes, wenn alle Verbindungen unter Kapazität k gelöscht werden (Kantenschwelle). Rückgabe: Komponentennummer je Knoten."""
    parent = list(range(graph.n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v, c in graph.edges:
        if c >= k:
            parent[find(u)] = find(v)
    ids = {}
    return tuple(ids.setdefault(find(i), len(ids)) for i in range(graph.n))


def all_pairs(graph, algorithm="bk"):
    """Zum Vergleich: für jedes Paar ein eigener Fluss. Rückgabe (Matrix als Dict {(u, v): Wert} mit u < v, durchsuchte Kanten insgesamt, Zahl der Flüsse)."""
    base = graph.to_net()
    out, total = {}, 0
    for u, v in combinations(range(graph.n), 2):
        value, _, scanned = min_cut(sc.with_terminals(base, u, v), algorithm)
        out[(u, v)] = value
        total += scanned
    return out, total, len(out)


def rand_index(a, b):
    """Rand-Index zweier Einteilungen (Anteil der Knotenpaare, die beide gleich behandeln: zusammen oder getrennt)."""
    n = len(a)
    agree = sum(1 for i, j in combinations(range(n), 2) if (a[i] == a[j]) == (b[i] == b[j]))
    return agree / (n * (n - 1) // 2)
