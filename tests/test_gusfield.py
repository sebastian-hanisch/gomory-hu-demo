"""Gusfields Gomory-Hu-Baum gegen Handrechnung, eigene Flüsse für alle Paare und networkx: Werte, Schnitteigenschaft, Ultrametrik, Klassensatz, Abfragen."""

from itertools import combinations

import networkx as nx
import pytest

import gh_constants as C
import gh_evaluation as ev
import gh_scenario as sc
import gh_tree as tr


def _weights(tree):
    return sorted(w for _, _, w in tree.edges())


def test_dumbbell_by_hand():
    """Zwei Dreiecke (Kapazität 5) durch eine Verbindung 2: Schnitt innerhalb eines Dreiecks 10 (Knotengrad), zwischen den Dreiecken 2; Baumgewichte 2, 10, 10, 10, 10."""
    g = sc.dumbbell()
    t = tr.gusfield(g)
    assert t.flows == 5 and _weights(t) == [2, 10, 10, 10, 10]
    vals = ev.pair_values(t)
    assert vals[(0, 1)] == 10 and vals[(0, 2)] == 10 and vals[(0, 3)] == 2 and vals[(2, 5)] == 2 and vals[(4, 5)] == 10


def test_star_by_hand():
    """Stern mit Kapazität 3: alle 15 Paare haben den Schnitt 3; der Baum ist der Stern selbst."""
    g = sc.star()
    t = tr.gusfield(g)
    assert set(ev.pair_values(t).values()) == {3} and len(ev.pair_values(t)) == 15 and ev.depth(t) == 1


def test_grid_by_hand():
    """Gitter 3 x 3, Kapazität 2: eine Ecke hat den Grad 4, ein Randknoten 6, die Mitte 8. Alle 36 Paare haben den Schnitt = kleinerer Knotengrad: 26 mal 4 (ein Paar mit Ecke), 10 mal 6."""
    g = sc.grid3()
    t = tr.gusfield(g)
    vals, deg = ev.pair_values(t), g.degree()
    assert all(v == min(deg[a], deg[b]) for (a, b), v in vals.items())
    assert sorted(vals.values()).count(4) == 26 and sorted(vals.values()).count(6) == 10


def test_a_single_edge_and_a_path():
    """Ein Pfad 1 - 2 - 3 mit Kapazitäten 5 und 2: der Baum ist der Pfad selbst; Schnitt 1-2: 5, 2-3: 2, 1-3: 2."""
    g = sc.Graph(3, ("a", "b", "c"), ((0, 0), (1, 0), (2, 0)), ((0, 1, 5), (1, 2, 2)), (0, 0, 0))
    t = tr.gusfield(g)
    v = ev.pair_values(t)
    assert (v[(0, 1)], v[(1, 2)], v[(0, 2)]) == (5, 2, 2) and t.flows == 2


@pytest.mark.parametrize("seed", C.SWEEP_SEEDS[:20])
def test_tree_answers_equal_own_flows_and_networkx(seed):
    g = sc.generate(8 + seed % 9, 3, 3, 30, seed % 2, seed)
    t = tr.gusfield(g)
    ap, _, _ = tr.all_pairs(g)
    vals = ev.pair_values(t)
    G = nx.Graph()
    for u, v, c in g.edges:
        G.add_edge(u, v, capacity=c)
    T = nx.gomory_hu_tree(G)
    for (u, v), val in ap.items():
        pth = nx.shortest_path(T, u, v)
        assert vals[(u, v)] == val == min(T[a][b]["weight"] for a, b in zip(pth, pth[1:]))
        assert tr.query(t, u, v)[0] == val


@pytest.mark.parametrize("seed", C.SWEEP_SEEDS[:20])
def test_every_tree_edge_is_a_minimum_cut_of_its_weight(seed):
    g = sc.generate(10 + seed % 7, 3, 3, 30, 0, seed)
    t = tr.gusfield(g)
    for i, p, w in t.edges():
        side = tr.tree_side(t, i, p)
        assert tr.cut_capacity(g, side) == w and 0 < len(side) < g.n
        assert tr.min_cut(sc.with_terminals(g.to_net(), i, p))[0] == w


@pytest.mark.parametrize("seed", C.SWEEP_SEEDS[:10])
def test_ultrametric_and_at_most_n_minus_one_distinct_values(seed):
    g = sc.generate(12, 3, 3, 30, 0, seed)
    v = ev.pair_values(tr.gusfield(g))
    for a, b, c in combinations(range(g.n), 3):
        assert v[(a, c)] >= min(v[(a, b)], v[(b, c)])
    assert len(set(v.values())) <= g.n - 1


@pytest.mark.parametrize("seed", C.SWEEP_SEEDS[:10])
def test_classes_are_exactly_the_k_connected_pairs(seed):
    g = sc.generate(14, 3, 3, 30, seed % 2, seed)
    t = tr.gusfield(g)
    vals = ev.pair_values(t)
    for k in range(1, 12):
        cls = tr.classes(t, k)
        assert all((cls[a] == cls[b]) == (vals[(a, b)] >= k) for (a, b) in vals)


@pytest.mark.parametrize("algo", tr.ALGORITHMS)
def test_all_flow_methods_build_trees_with_the_same_pair_values(algo):
    g = sc.generate(16, 3, 3, 30, 0, 100003)
    assert ev.pair_values(tr.gusfield(g, algo)) == ev.pair_values(tr.gusfield(g, "bk"))


def test_query_path_and_weakest_edge():
    g = sc.dumbbell()
    t = tr.gusfield(g)
    value, pth, edge = tr.query(t, 0, 5)
    assert value == 2 and pth[0] == 0 and pth[-1] == 5 and edge[2] == 2


def test_one_way_edge_breaks_the_tree():
    """Negativkontrolle: Kette 1-2-3-4 mit Einbahn 2 -> 3. Der Baum antwortet für 1 und 4 mit 0; der Fluss von 1 nach 4 ist 4, von 4 nach 1 ist 0."""
    g = sc.oneway_chain()
    t = tr.gusfield(g)
    assert tr.query(t, 0, 3)[0] == 0
    net = g.to_net()
    assert tr.min_cut(sc.with_terminals(net, 0, 3))[0] == 4 and tr.min_cut(sc.with_terminals(net, 3, 0))[0] == 0


def test_rand_index_and_threshold_components():
    assert tr.rand_index((0, 0, 1, 1), (5, 5, 7, 7)) == 1.0 and tr.rand_index((0, 0, 0, 0), (0, 1, 2, 3)) == 0.0 + 0
    g = sc.dumbbell()
    assert len(set(tr.threshold_components(g, 3))) == 2 and len(set(tr.threshold_components(g, 1))) == 1
