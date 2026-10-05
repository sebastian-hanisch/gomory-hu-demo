"""Orakel-Regressionstest: beliebige kleine Netze (auch unzusammenhängend, viele Gleichstände, Kapazitäten 1 bis 10) gegen networkx.

Unabhängige Rechenwege: `networkx.maximum_flow_value` je Paar (statt Baum und eigener Flüsse), Klassen und Kantenschwelle über
networkx-Komponenten, die drei Flussverfahren auf gerichteten Zufallsnetzen gegen networkx."""

import random
from itertools import combinations

import pytest

nx = pytest.importorskip("networkx")

import gh_evaluation as ev  # noqa: E402
import gh_scenario as sc  # noqa: E402
import gh_tree as tr  # noqa: E402


def _graph(rng, n):
    cmax, p = rng.choice([1, 2, 3, 10]), rng.choice([0.15, 0.3, 0.6, 1.0])
    edges = tuple((u, v, rng.randint(1, cmax)) for u, v in combinations(range(n), 2) if rng.random() < p)
    return sc.Graph(n, tuple(f"S{i}" for i in range(n)), tuple((3 * i % 100, 7 * i % 100) for i in range(n)), edges, (0,) * n)


def _nx(g):
    G = nx.Graph()
    G.add_nodes_from(range(g.n))
    G.add_edges_from((u, v, {"capacity": c}) for u, v, c in g.edges)
    return G


def _components(G):
    lab = {}
    for i, comp in enumerate(nx.connected_components(G)):
        lab.update({x: i for x in comp})
    return lab


def test_gusfield_pair_values_equal_networkx_on_random_nets():
    rng = random.Random(1)
    for _ in range(60):
        g = _graph(rng, rng.randint(2, 10))
        G = _nx(g)
        ref = {(u, v): nx.maximum_flow_value(G, u, v) for u, v in combinations(range(g.n), 2)}
        for algo in tr.ALGORITHMS:
            t = tr.gusfield(g, algo)
            assert ev.pair_values(t) == ref and t.flows == g.n - 1
            for s in t.steps:
                assert s.s in s.side and s.t not in s.side and tr.cut_capacity(g, s.side) == s.value
        t = tr.gusfield(g)
        for k in (1, 2, 3, 5):
            H = nx.Graph()
            H.add_nodes_from(range(g.n))
            H.add_edges_from(pr for pr, v in ref.items() if v >= k)
            cls, lab = tr.classes(t, k), _components(H)
            assert all((cls[a] == cls[b]) == (lab[a] == lab[b]) for a, b in combinations(range(g.n), 2))
            T = nx.Graph()
            T.add_nodes_from(range(g.n))
            T.add_edges_from((u, v) for u, v, c in g.edges if c >= k)
            thr, lab = tr.threshold_components(g, k), _components(T)
            assert all((thr[a] == thr[b]) == (lab[a] == lab[b]) for a, b in combinations(range(g.n), 2))


def test_min_cut_of_all_flow_methods_on_directed_nets():
    rng = random.Random(5)
    for _ in range(60):
        n = rng.randint(2, 8)
        arcs = tuple((u, v, rng.randint(1, 6), 0, 0) for u in range(n) for v in range(n) if u != v and rng.random() < 0.35)
        s, t = rng.sample(range(n), 2)
        net = sc.Net(tuple(map(str, range(n))), tuple(map(str, range(n))), ((0, 0),) * n, arcs, s, t, False)
        D = nx.DiGraph()
        D.add_nodes_from(range(n))
        D.add_edges_from((u, v, {"capacity": c}) for u, v, c, _, _ in arcs)
        ref = nx.maximum_flow_value(D, s, t)
        for algo in tr.ALGORITHMS:
            value, side, _ = tr.min_cut(net, algo)
            assert value == ref and s in side and t not in side
            assert sum(c for u, v, c, _, _ in arcs if u in side and v not in side) == ref
