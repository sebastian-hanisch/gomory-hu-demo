"""Auswertung: Kennzahlen des Gomory-Hu-Baums, Verteilungen über feste Netze, Aufwand nach Größe, Klassenvergleich, Gegenproben.
Alle Zufallsnetze kommen aus festen Seeds (gh_constants.SWEEP_SEEDS), unabhängig vom Nutzer-Seed."""

import statistics
from collections import namedtuple

import gh_constants as C
import gh_scenario as sc
import gh_tree as tr

Params = namedtuple("Params", "net n k regions cross bridge seed algorithm")
DEFAULT_PARAMS = Params(C.DEFAULT_NET, C.DEFAULT_N, C.DEFAULT_K, C.DEFAULT_REGIONS, C.DEFAULT_CROSS, C.DEFAULT_BRIDGE, C.DEFAULT_SEED, C.DEFAULT_ALGORITHM)


def graph_of(params):
    return sc.build(params.net, params.n, params.k, params.regions, params.cross, params.bridge, params.seed)


def depth(tree):
    """Größte Zahl der Baumkanten von der Wurzel zu einem Knoten."""
    adj = tree.adjacency()
    d = {0: 0}
    stack = [0]
    while stack:
        x = stack.pop()
        for y, _ in adj[x]:
            if y not in d:
                d[y] = d[x] + 1
                stack.append(y)
    return max(d.values())


def max_degree(tree):
    return max(len(a) for a in tree.adjacency())


def pair_values(tree):
    """Minimaler Schnitt aller Paare aus dem Baum: {(u, v): Wert}."""
    n = tree.n
    adj = tree.adjacency()
    out = {}
    for u in range(n):
        best = {u: 10 ** 9}
        stack = [u]
        while stack:
            x = stack.pop()
            for y, w in adj[x]:
                if y not in best:
                    best[y] = min(best[x], w)
                    stack.append(y)
        for v in range(u + 1, n):
            out[(u, v)] = best[v]
    return out


def analyse(params):
    g = graph_of(params)
    tree = tr.gusfield(g, params.algorithm)
    values = pair_values(tree)
    deg = g.degree()
    trivial = sum(1 for (u, v), val in values.items() if val == min(deg[u], deg[v]))
    counts = {}
    for val in values.values():
        counts[val] = counts.get(val, 0) + 1
    return dict(graph=g, tree=tree, values=values, degree=deg, trivial=trivial, pairs=len(values), distinct=len(counts), counts=dict(sorted(counts.items())),
                depth=depth(tree), max_degree=max_degree(tree))


def distribution(params, seeds=C.SWEEP_SEEDS, scan_seeds=C.SCAN_SEEDS):
    """Kennzahlen über feste Netze mit den Einstellungen (Standorte, Verbindungen, Regionen, Kapazität zwischen Regionen, Brücke)."""
    rows = []
    for seed in seeds:
        g = sc.generate(params.n, params.k, params.regions, params.cross, params.bridge, seed)
        tree = tr.gusfield(g, params.algorithm)
        values = pair_values(tree)
        deg = g.degree()
        row = dict(seed=seed, trivial=sum(1 for (u, v), val in values.items() if val == min(deg[u], deg[v])) / len(values), distinct=len(set(values.values())),
                   depth=depth(tree), max_degree=max_degree(tree), scanned=tree.scanned)
        if seed in scan_seeds:
            _, all_scanned, flows = tr.all_pairs(g, params.algorithm)
            row.update(all_scanned=all_scanned, flows_all=flows)
        rows.append(row)
    n = params.n
    scan_rows = [r for r in rows if "all_scanned" in r]
    return dict(n=len(rows), nodes=n, flows_tree=n - 1, flows_all=n * (n - 1) // 2, trivial=statistics.fmean(r["trivial"] for r in rows), distinct=statistics.fmean(r["distinct"] for r in rows),
                pairs=n * (n - 1) // 2, depth=statistics.fmean(r["depth"] for r in rows), max_degree=statistics.fmean(r["max_degree"] for r in rows),
                scan_ratio=statistics.fmean(r["all_scanned"] / r["scanned"] for r in scan_rows) if scan_rows else None, rows=rows)


def classes_experiment(params, seeds=C.SWEEP_SEEDS, ks=C.K_RANGE):
    """Wiederfinden der geplanten Regionen (Rand-Index, bester Schwellenwert k über 1..24 = Orakel): Klassen des Gomory-Hu-Baums gegen Komponenten der Kantenschwelle."""
    tree_ri, thr_ri, tree_better, thr_better = [], [], 0, 0
    for seed in seeds:
        g = sc.generate(params.n, params.k, params.regions, params.cross, params.bridge, seed)
        tree = tr.gusfield(g, params.algorithm)
        a = max(tr.rand_index(tr.classes(tree, k), g.region) for k in ks)
        b = max(tr.rand_index(tr.threshold_components(g, k), g.region) for k in ks)
        tree_ri.append(a)
        thr_ri.append(b)
        tree_better += a > b + 1e-9
        thr_better += b > a + 1e-9
    return dict(n=len(tree_ri), tree=statistics.fmean(tree_ri), threshold=statistics.fmean(thr_ri), tree_better=tree_better, threshold_better=thr_better)


def scaling(sizes=C.SCALE_SIZES, seeds=C.SCAN_SEEDS, k=C.DEFAULT_K, regions=C.DEFAULT_REGIONS, cross=C.DEFAULT_CROSS, algorithm="bk"):
    """Flüsse und durchsuchte Kanten von Gusfield gegen alle Paare je Netzgröße (Mittel über feste Netze)."""
    rows = []
    for n in sizes:
        tree_scan, all_scan = [], []
        for seed in seeds:
            g = sc.generate(n, k, regions, cross, 0, seed)
            tree = tr.gusfield(g, algorithm)
            _, all_scanned, _ = tr.all_pairs(g, algorithm)
            tree_scan.append(tree.scanned)
            all_scan.append(all_scanned)
        rows.append(dict(n=n, flows_tree=n - 1, flows_all=n * (n - 1) // 2, tree=statistics.fmean(tree_scan), all=statistics.fmean(all_scan)))
    return rows


def small_check(seeds=C.SWEEP_SEEDS, n=10):
    """Kleine Netze: der Baum antwortet für jedes Paar wie ein eigener Fluss; jede Baumkante ist ein Schnitt der Kapazität ihres Gewichts; die Ultrametrik-Regel gilt."""
    pairs_ok = pairs_total = edges_ok = edges_total = ultra_ok = ultra_total = 0
    for seed in seeds:
        g = sc.generate(n, 3, 3, 30, seed % 2, seed)
        tree = tr.gusfield(g)
        ap, _, _ = tr.all_pairs(g)
        values = pair_values(tree)
        for key, val in ap.items():
            pairs_total += 1
            pairs_ok += values[key] == val
        for i, p, w in tree.edges():
            edges_total += 1
            edges_ok += tr.cut_capacity(g, tr.tree_side(tree, i, p)) == w
        for a in range(n):
            for b in range(a + 1, n):
                for c in range(b + 1, n):
                    ultra_total += 1
                    ultra_ok += values[(a, c)] >= min(values[(a, b)], values[(b, c)])
    return dict(nets=len(seeds), pairs_ok=pairs_ok, pairs_total=pairs_total, edges_ok=edges_ok, edges_total=edges_total, ultra_ok=ultra_ok, ultra_total=ultra_total)
