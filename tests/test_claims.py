"""Jede Zahl, die README, Hilfetexte und Beispieltexte nennen, ist hier belegt (Standardnetz: 24 Standorte, 3 Nachbarn, 3 Regionen, Kapazität zwischen Regionen 30 %, feste Netze ab Seed 100000).
Netze, Bäume, Schnittwerte und durchsuchte Kanten sind ganzzahlig und deterministisch (eigener Zufallsstrom); Mittelwerte über Netze werden mit Bändern geprüft."""

import pytest

import gh_constants as C
import gh_evaluation as ev
import gh_tree as tr

P = ev.DEFAULT_PARAMS


def _analyse(name):
    p = C.PRESETS[name]
    return ev.analyse(ev.Params(p["net"], p["n"], p["k"], p["regions"], p["cross"], p["bridge"], p["seed"], p["algorithm"]))


def test_default_preset_numbers():
    """Regionen, Seed 7: 24 Standorte, 45 Verbindungen, 23 Flüsse statt 276, 16 verschiedene Schnittwerte, 53 Paare mit Schnitt = Knotengrad, Baumtiefe 8, höchster Grad 7, 6 037 durchsuchte Kanten.
    Region 3 (8 Standorte) hängt an einer einzigen Verbindung der Kapazität 1 (Standorte 20 und 21): 8 x 16 = 128 Paare haben den Schnitt 1."""
    a = _analyse("🗺️ Regionen")
    assert (a["graph"].n, len(a["graph"].edges), a["tree"].flows, a["pairs"], a["distinct"], a["trivial"], a["depth"], a["max_degree"], a["tree"].scanned) == (24, 45, 23, 276, 16, 53, 8, 7, 6037)
    assert a["counts"][1] == 128 == 8 * 16 and a["counts"][3] == 64
    t, g = a["tree"], a["graph"]
    weak = [(i, p, w) for i, p, w in t.edges() if w == 1]
    assert len(weak) == 1
    side = tr.tree_side(t, weak[0][0], weak[0][1])
    assert min(len(side), g.n - len(side)) == 8
    assert [(u + 1, v + 1, c) for _, u, v, c in tr.cut_edges(g, side)] == [(20, 21, 1)] and {g.region[x] for x in side} in ({2}, {0, 1})


def test_uniform_bridge_and_sparse_presets():
    """Gleichmäßiges Netz (eine Region): 15 verschiedene Werte, 104 Paare mit Schnitt = Knotengrad, 80 Paare mit Schnitt 7. Starke Brücke: beim besten k Rand-Index der Baumklassen 0,924 (k = 16),
    der Kantenschwelle 0,859 (k = 8). Dünnes Netz (k = 2): 32 Verbindungen, 11 verschiedene Werte, 176 von 276 Paaren mit Schnitt 1, Tiefe 10, höchster Grad 3, 3 354 durchsuchte Kanten."""
    u = _analyse("⚖️ Gleichmäßiges Netz")
    assert (u["distinct"], u["trivial"], u["counts"][7]) == (15, 104, 80)
    b = _analyse("🌉 Starke Brücke")
    t, g = b["tree"], b["graph"]
    best_t = max(range(1, 25), key=lambda k: tr.rand_index(tr.classes(t, k), g.region))
    best_h = max(range(1, 25), key=lambda k: tr.rand_index(tr.threshold_components(g, k), g.region))
    assert best_t == 16 and round(tr.rand_index(tr.classes(t, best_t), g.region), 3) == 0.924
    assert best_h == 8 and round(tr.rand_index(tr.threshold_components(g, best_h), g.region), 3) == 0.859
    s = _analyse("🕸️ Dünnes Netz")
    assert (len(s["graph"].edges), s["distinct"], s["counts"][1], s["depth"], s["max_degree"], s["tree"].scanned) == (32, 11, 176, 10, 3, 3354)


def test_lesson_presets_by_hand():
    """Hantel: 5 Flüsse statt 15, 2 verschiedene Werte (9 Paare mit 2, 6 mit 10); Stern: 15 Paare mit 3, Tiefe 1; Gitter: 26 Paare mit 4, 10 mit 6, alle mit Schnitt = Knotengrad, 8 Flüsse statt 36;
    Einbahnkante: der Baum antwortet 0 für 1 und 4, der Fluss von 1 nach 4 ist 4, der von 4 nach 1 ist 0."""
    h = _analyse("🏋️ Hantel")
    assert h["tree"].flows == 5 and h["pairs"] == 15 and h["counts"] == {2: 9, 10: 6}
    s = _analyse("⭐ Stern")
    assert s["counts"] == {3: 15} and s["depth"] == 1
    g = _analyse("🔲 Gitter 3 × 3")
    assert g["counts"] == {4: 26, 6: 10} and g["trivial"] == g["pairs"] == 36 and g["tree"].flows == 8
    e = _analyse("➡️ Einbahnkante")
    assert e["values"][(0, 3)] == 0
    from gh_scenario import with_terminals
    net = e["graph"].to_net()
    assert tr.min_cut(with_terminals(net, 0, 3))[0] == 4 and tr.min_cut(with_terminals(net, 3, 0))[0] == 0


@pytest.fixture(scope="module")
def dist():
    return ev.distribution(P)


def test_distribution_at_default_settings(dist):
    """40 feste Netze: 23 Flüsse statt 276; im Mittel 15,7 verschiedene Schnittwerte (von 276 Paaren), in 15,7 % der Paare Schnitt = Knotengrad, Baumtiefe 9,5, höchster Grad 5,4;
    alle Paare kosten (Mittel über 5 Netze) das 10,2-Fache an durchsuchten Kanten."""
    assert dist["flows_tree"] == 23 and dist["flows_all"] == 276 and dist["pairs"] == 276
    assert dist["distinct"] == pytest.approx(15.7, abs=0.6) and dist["trivial"] == pytest.approx(0.157, abs=0.01) and dist["depth"] == pytest.approx(9.5, abs=0.4) and dist["max_degree"] == pytest.approx(5.4, abs=0.4)
    assert dist["scan_ratio"] == pytest.approx(10.2, abs=0.5)


def test_uniform_and_bridge_nets():
    """Ohne Regionen: 25,7 % der Paare mit Schnitt = Knotengrad, Tiefe 7,85, Aufwandsverhältnis 12,2; mit Brücke 18,6 %."""
    u = ev.distribution(P._replace(regions=1, cross=100))
    assert u["trivial"] == pytest.approx(0.257, abs=0.01) and u["depth"] == pytest.approx(7.85, abs=0.4) and u["scan_ratio"] == pytest.approx(12.2, abs=0.6)
    assert ev.distribution(P._replace(bridge=1))["trivial"] == pytest.approx(0.186, abs=0.01)


def test_the_tree_depth_falls_with_more_neighbours():
    """Tiefe des Baums: bei 5 Nachbarn im Mittel 5,2, bei 3 Nachbarn 9,5, bei 2 Nachbarn 11,2."""
    depth = {k: ev.distribution(P._replace(k=k), seeds=C.SWEEP_SEEDS, scan_seeds=())["depth"] for k in (2, 3, 5)}
    assert depth[5] == pytest.approx(5.2, abs=0.4) and depth[3] == pytest.approx(9.5, abs=0.4) and depth[2] == pytest.approx(11.2, abs=0.5)


def test_the_saving_follows_the_flow_ratio():
    """Durchsuchte Kanten Gusfield / alle Paare (Mittel über 5 Netze): 8 Standorte 994 / 3 831 (3,9-fach bei 4-fach weniger Flüssen), 40 Standorte 17 241 / 350 007 (20,3-fach bei 20-fach weniger Flüssen)."""
    rows = {r["n"]: r for r in ev.scaling()}
    assert rows[8]["tree"] == pytest.approx(994, rel=0.03) and rows[8]["all"] == pytest.approx(3831, rel=0.03) and rows[8]["all"] / rows[8]["tree"] == pytest.approx(3.9, abs=0.2)
    assert rows[40]["tree"] == pytest.approx(17241, rel=0.03) and rows[40]["all"] == pytest.approx(350007, rel=0.03) and rows[40]["all"] / rows[40]["tree"] == pytest.approx(20.3, abs=0.8)
    assert rows[8]["flows_all"] / rows[8]["flows_tree"] == 4.0 and rows[40]["flows_all"] // rows[40]["flows_tree"] == 20
    ratios = [r["all"] / r["tree"] for r in rows.values()]
    assert ratios == sorted(ratios)


def test_the_tree_matches_all_pairs_on_small_nets():
    """40 Netze mit 10 Standorten: 1 800 von 1 800 Paaren wie ein eigener Fluss, 360 von 360 Baumkanten = Schnitt ihres Gewichts, 4 800 von 4 800 Tripeln erfüllen die Ultrametrik-Regel."""
    assert ev.small_check() == dict(nets=40, pairs_ok=1800, pairs_total=1800, edges_ok=360, edges_total=360, ultra_ok=4800, ultra_total=4800)


def test_classes_versus_edge_threshold():
    """Wiederfinden der Regionen (Rand-Index beim besten Schwellenwert, 40 Netze): Kapazität zwischen Regionen 30 %: Baum 0,966, Kantenschwelle 0,992 (Kantenschwelle besser in 16 Netzen, Baum in 0);
    60 %: 0,914 gegen 0,941 (22 gegen 7); mit starker Brücke: Baum 0,874, Kantenschwelle 0,842 (Baum besser in 24, Schwelle in 11)."""
    a = ev.classes_experiment(P)
    assert a["tree"] == pytest.approx(0.966, abs=0.006) and a["threshold"] == pytest.approx(0.992, abs=0.006) and (a["tree_better"], a["threshold_better"]) == (0, 16)
    c = ev.classes_experiment(P._replace(cross=60))
    assert c["tree"] == pytest.approx(0.914, abs=0.006) and c["threshold"] == pytest.approx(0.941, abs=0.006) and (c["tree_better"], c["threshold_better"]) == (7, 22)
    b = ev.classes_experiment(P._replace(bridge=1))
    assert b["tree"] == pytest.approx(0.874, abs=0.006) and b["threshold"] == pytest.approx(0.842, abs=0.006) and (b["tree_better"], b["threshold_better"]) == (24, 11)
