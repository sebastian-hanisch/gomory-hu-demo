"""Szenario: ein ungerichtetes Verbindungsnetz zwischen Standorten mit geplanten Regionen, dazu feste Lehrnetze.

Standorte liegen auf einer Karte in Regionen (Werke, Verteilzentren und Filialen eines Liefergebiets gehören zusammen); jeder Standort ist mit seinen k nächsten Nachbarn verbunden, jede Verbindung hat eine ganzzahlige
Kapazität (Fahrten je Tag in beide Richtungen). Innerhalb einer Region sind die Verbindungen kräftig, zwischen Regionen schwach (`cross`: Prozent der inneren Kapazität). Optional gibt es **eine starke Brücke** zwischen
zwei Regionen. Gefragt wird nach dem **minimalen Schnitt zwischen zwei Standorten** (der kleinsten Kapazität, die man kappen muss, um sie zu trennen) - für alle Paare.

Alles ist ganzzahlig und läuft über einen eigenen Zufallsgenerator (SplitMix64 auf Python-Ints) statt über `numpy.random`: numpy garantiert keine über Versionen stabilen Zufallsströme, die CI installiert aber
wöchentlich die neueste Version. So sind Voreinstellungen, Seeds und jede im Text genannte Zahl auf Windows und Linux dieselben.
"""

from dataclasses import dataclass, replace
from math import cos, pi, sin

_MASK = (1 << 64) - 1
MAP = 100


class SplitMix64:
    """Kleiner, gut gemischter 64-Bit-Zufallsgenerator (Vigna); reine Ganzzahl-Arithmetik."""

    def __init__(self, seed):
        self.state = seed & _MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return z ^ (z >> 31)

    def below(self, n):
        """Ganzzahl in 0..n-1 (die Modulo-Verzerrung bei n <= 1e6 liegt unter 1e-13)."""
        return self.next() % n


@dataclass(frozen=True)
class Net:
    names: tuple      # Anzeigename je Knoten (Hover)
    labels: tuple     # Kurzbeschriftung je Knoten (Karte)
    pos: tuple        # ((x, y), ...) je Knoten
    arcs: tuple       # ((u, v, Kapazität, Kosten je Einheit, Art), ...)
    s: int
    t: int
    logistic: bool    # True: Werke/DCs/Filialen; False: Lehrnetz mit frei benannten Knoten

    @property
    def n(self):
        return len(self.names)

    @property
    def m(self):
        return len(self.arcs)

    def total_capacity_out_of_s(self):
        return sum(c for u, _, c, _, _ in self.arcs if u == self.s)


@dataclass(frozen=True)
class Graph:
    n: int
    names: tuple
    pos: tuple
    edges: tuple          # ((u, v, Kapazität), ...) mit u < v, ungerichtet
    region: tuple         # geplante Region je Knoten (Lehrnetze: 0)
    oneway: tuple = ()    # Indizes der Verbindungen, die nur von u nach v befahrbar sind (nur die Negativkontrolle)
    kind: str = "random"

    def degree(self):
        d = [0] * self.n
        for u, v, c in self.edges:
            d[u] += c
            d[v] += c
        return tuple(d)

    def to_net(self, s=0, t=1):
        """Flussnetz: je Verbindung zwei Kanten gleicher Kapazität (bei Einbahnkanten nur von u nach v)."""
        arcs = []
        for i, (u, v, c) in enumerate(self.edges):
            arcs.append((u, v, c, 0, 0))
            if i not in self.oneway:
                arcs.append((v, u, c, 0, 0))
        return Net(self.names, self.names, self.pos, tuple(arcs), s, t, False)


def with_terminals(net, s, t):
    return replace(net, s=s, t=t)


def generate(n, k, regions, cross, bridge, seed):
    """Zufallsnetz. `n` Standorte in `regions` Regionen (Standort i gehört zu Region i % regions), Verbindungen zu den `k` nächsten Standorten (symmetrisch ergänzt);
    innere Kapazität 5 bis 10, Verbindung zwischen Regionen `cross` Prozent davon (mindestens 1); `bridge` = 1 fügt zwischen Region 0 und 1 eine starke Brücke der Kapazität 20 zu den dichtesten Standorten hinzu.
    Die Zufallszahlen werden in fester Reihenfolge gezogen, so ändern `cross` und `bridge` nur die Kapazitäten, nicht die Lage."""
    rng = SplitMix64(seed)
    R = max(1, regions)
    centers = [(MAP // 2 + round(30 * cos(2 * pi * r / R)), MAP // 2 + round(30 * sin(2 * pi * r / R))) if R > 1 else (MAP // 2, MAP // 2) for r in range(R)]
    spread = 22 if R > 1 else 40
    pos = []
    for i in range(n):
        cx, cy = centers[i % R]
        pos.append((cx + rng.below(2 * spread + 1) - spread, cy + rng.below(2 * spread + 1) - spread))
    region = tuple(i % R for i in range(n))
    inner = [5 + rng.below(6) for _ in range(n * n)]                       # eine Zahl je Knotenpaar in fester Reihenfolge
    pairs = {}
    for i in range(n):
        near = sorted((j for j in range(n) if j != i), key=lambda j: ((pos[i][0] - pos[j][0]) ** 2 + (pos[i][1] - pos[j][1]) ** 2, j))
        for j in near[:k]:
            pairs[(min(i, j), max(i, j))] = True
    # zusammenhängend machen: Komponenten über die kürzesten fehlenden Verbindungen verbinden
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (u, v) in pairs:
        parent[find(u)] = find(v)
    while len({find(i) for i in range(n)}) > 1:
        best = min(((pos[u][0] - pos[v][0]) ** 2 + (pos[u][1] - pos[v][1]) ** 2, u, v) for u in range(n) for v in range(u + 1, n) if find(u) != find(v))
        pairs[(best[1], best[2])] = True
        parent[find(best[1])] = find(best[2])
    edges = []
    for (u, v) in sorted(pairs):
        base = inner[u * n + v]
        cap = base if region[u] == region[v] else max(1, base * cross // 100)
        edges.append([u, v, cap])
    if bridge and R > 1:
        a = min((i for i in range(n) if region[i] == 0), key=lambda i: ((pos[i][0] - centers[1][0]) ** 2 + (pos[i][1] - centers[1][1]) ** 2, i))
        b = min((i for i in range(n) if region[i] == 1), key=lambda i: ((pos[i][0] - centers[0][0]) ** 2 + (pos[i][1] - centers[0][1]) ** 2, i))
        key = (min(a, b), max(a, b))
        for e in edges:
            if (e[0], e[1]) == key:
                e[2] = 20
                break
        else:
            edges.append([key[0], key[1], 20])
            edges.sort()
    names = tuple(f"Standort {i + 1}" for i in range(n))
    return Graph(n, names, tuple(pos), tuple(tuple(e) for e in edges), region, (), "random")


# --- feste Lehrnetze ------------------------------------------------------------------------------------------------------------

def _lesson(names, pos, edges, oneway=(), kind="lesson"):
    n = len(names)
    return Graph(n, tuple(names), tuple(pos), tuple(sorted((min(u, v), max(u, v), c) for u, v, c in edges)), tuple(0 for _ in range(n)), tuple(oneway), kind)


def dumbbell():
    """Hantel: zwei Dreiecke (Kapazität 5) durch eine einzige Verbindung der Kapazität 2 verbunden. Innerhalb eines Dreiecks ist der Schnitt 10 (der Knotengrad), zwischen den Dreiecken 2 (die Brücke)."""
    pos = [(15, 30), (15, 70), (35, 50), (65, 50), (85, 30), (85, 70)]
    edges = [(0, 1, 5), (0, 2, 5), (1, 2, 5), (3, 4, 5), (3, 5, 5), (4, 5, 5), (2, 3, 2)]
    return _lesson([f"Standort {i + 1}" for i in range(6)], pos, edges)


def star():
    """Stern: eine Mitte mit fünf Blättern der Kapazität 3. Jedes Paar hat den Schnitt 3 (das schwächere Blatt)."""
    pos = [(50, 50)] + [(50 + round(35 * cos(2 * pi * i / 5)), 50 + round(35 * sin(2 * pi * i / 5))) for i in range(5)]
    return _lesson([f"Standort {i + 1}" for i in range(6)], pos, [(0, i, 3) for i in range(1, 6)])


def grid3():
    """Gitter 3 x 3, alle Verbindungen Kapazität 2: ein Eckknoten hat den Grad 4 (2 Verbindungen), also ist jeder Schnitt mit einer Ecke 4; die übrigen Paare haben 6 oder mehr."""
    pos = [(25 + 25 * x, 25 + 25 * y) for y in range(3) for x in range(3)]
    edges = []
    for y in range(3):
        for x in range(3):
            i = 3 * y + x
            if x + 1 < 3:
                edges.append((i, i + 1, 2))
            if y + 1 < 3:
                edges.append((i, i + 3, 2))
    return _lesson([f"Standort {i + 1}" for i in range(9)], pos, edges)


def oneway_chain():
    """Negativkontrolle: eine Kette 1 - 2 - 3 - 4, alle Verbindungen Kapazität 4, aber 2 - 3 nur von 2 nach 3 befahrbar. Als ungerichtetes Netz wäre der Schnitt zwischen 1 und 4 gleich 4; von 4 nach 1 gibt es gar keinen Weg."""
    pos = [(15, 50), (40, 50), (65, 50), (90, 50)]
    return _lesson([f"Standort {i + 1}" for i in range(4)], pos, [(0, 1, 4), (1, 2, 4), (2, 3, 4)], oneway=(1,), kind="oneway")


LESSONS = {"hantel": dumbbell, "stern": star, "gitter": grid3, "einbahn": oneway_chain}


def build(net, n, k, regions, cross, bridge, seed):
    """Netz zu den Einstellungen; feste Lehrnetze ignorieren die Zufallsparameter."""
    if net != "random":
        return LESSONS[net]()
    return generate(n, k, regions, cross, bridge, seed)
