"""Szenario (Regionen, Kapazitäten, Zusammenhang, Zufallsstrom) und Auswertung (Kennzahlen, Verteilungen, Aufwand)."""

import pytest

import gh_constants as C
import gh_evaluation as ev
import gh_scenario as sc
import gh_tree as tr

P = ev.DEFAULT_PARAMS


def _connected(g):
    parent = list(range(g.n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v, _ in g.edges:
        parent[find(u)] = find(v)
    return len({find(i) for i in range(g.n)}) == 1


def test_generation_is_deterministic_and_seed_dependent():
    a, b, c = sc.generate(16, 3, 3, 30, 0, 5), sc.generate(16, 3, 3, 30, 0, 5), sc.generate(16, 3, 3, 30, 0, 6)
    assert a == b and a != c


@pytest.mark.parametrize("seed", C.SWEEP_SEEDS[:20])
def test_every_random_net_is_connected_with_positive_integer_capacities(seed):
    g = sc.generate(8 + seed % 20, 2 + seed % 4, 1 + seed % 5, 10 + 10 * (seed % 10), seed % 2, seed)
    assert _connected(g) and all(isinstance(c, int) and c >= 1 and u < v for u, v, c in g.edges)


def test_regions_capacities_and_the_bridge():
    """Innere Kapazität 5 bis 10, zwischen Regionen 30 % davon (mindestens 1); die Brücke hat Kapazität 20."""
    g = sc.generate(24, 3, 3, 30, 0, 100000)
    inner = [c for u, v, c in g.edges if g.region[u] == g.region[v]]
    cross = [c for u, v, c in g.edges if g.region[u] != g.region[v]]
    assert 5 <= min(inner) and max(inner) <= 10 and 1 <= min(cross) and max(cross) <= 3
    b = sc.generate(24, 3, 3, 30, 1, 100000)
    assert max(c for _, _, c in b.edges) == 20 and len(b.edges) in (len(g.edges), len(g.edges) + 1)


def test_cross_and_bridge_change_only_capacities_not_positions():
    a, b = sc.generate(20, 3, 3, 30, 0, 100000), sc.generate(20, 3, 3, 60, 1, 100000)
    assert a.pos == b.pos and a.region == b.region


def test_single_region_has_uniform_inside_capacities():
    g = sc.generate(20, 3, 1, 100, 0, 100000)
    assert set(g.region) == {0} and all(5 <= c <= 10 for _, _, c in g.edges)


def test_lessons_and_build_dispatch():
    assert set(sc.LESSONS) == set(C.FIXED_NETS) and sc.build("hantel", 9, 9, 9, 9, 9, 1).n == 6
    assert sc.build("random", 12, 3, 2, 30, 0, 5) == sc.generate(12, 3, 2, 30, 0, 5)


def test_to_net_has_two_arcs_per_edge_except_one_way():
    g = sc.dumbbell()
    assert g.to_net().m == 2 * len(g.edges)
    o = sc.oneway_chain()
    assert o.to_net().m == 2 * len(o.edges) - 1


def test_analyse_shapes():
    a = ev.analyse(P)
    assert a["pairs"] == 276 and sum(a["counts"].values()) == 276 and a["distinct"] == len(a["counts"]) <= 23 and a["tree"].flows == 23
    assert 0 <= a["trivial"] <= 276 and a["depth"] >= 1 and a["max_degree"] >= 2


def test_pair_values_match_query():
    a = ev.analyse(P._replace(n=12))
    for (u, v), val in list(a["values"].items())[:30]:
        assert tr.query(a["tree"], u, v)[0] == val


def test_distribution_shapes():
    d = ev.distribution(P)
    assert d["n"] == 40 and d["flows_tree"] == 23 and d["flows_all"] == 276 and 0 < d["trivial"] < 1 and d["scan_ratio"] > 1 and len(d["rows"]) == 40


def test_scaling_rows_are_ordered_by_size():
    rows = ev.scaling(sizes=(8, 12), seeds=C.SCAN_SEEDS[:2])
    assert [r["n"] for r in rows] == [8, 12] and all(r["all"] > r["tree"] > 0 for r in rows)


def test_classes_experiment_shape():
    c = ev.classes_experiment(P, seeds=C.SWEEP_SEEDS[:5])
    assert c["n"] == 5 and 0 < c["tree"] <= 1 and 0 < c["threshold"] <= 1
