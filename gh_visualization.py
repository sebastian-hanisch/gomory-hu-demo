"""Plotly-Abbildungen: Karte des Netzes (Verbindungen nach Kapazität, Schnitt, Baumkanten, Klassen, Paar), Baum als Schema, Schnittwerte aller Paare, Aufwand, Klassenvergleich.
Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen. Karten haben gleichen Maßstab (scaleanchor) mit automatischem Bereich; der Rand kommt über zwei unsichtbare Punkte
(ein fest vorgegebener Bereich wird beim ersten Zeichnen in schmaler Breite eingefroren). Beschriftungen von Kanten sind Annotationen mit heller Hinterlegung."""

import plotly.graph_objects as go

import gh_constants as C


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.15), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _frame(fig, points, height, pad=8):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    fig.update_xaxes(visible=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False)
    fig.add_trace(go.Scatter(x=[min(xs) - pad, max(xs) + pad], y=[min(ys) - pad, max(ys) + pad], mode="markers", marker=dict(opacity=0), hoverinfo="skip", showlegend=False))
    return _base(fig, height)


def _lines(fig, segs, color, widths, name, dash=None, showlegend=True):
    """Kanten als Linienzüge; Kanten gleicher Breite teilen sich eine Spur."""
    by_width = {}
    for (x0, y0, x1, y1), w in zip(segs, widths):
        by_width.setdefault(w, []).append((x0, y0, x1, y1))
    first = True
    for w, items in sorted(by_width.items()):
        x, y = [], []
        for x0, y0, x1, y1 in items:
            x += [x0, x1, None]
            y += [y0, y1, None]
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=w, dash=dash), hoverinfo="skip", name=name, showlegend=showlegend and first))
        first = False


def _label(fig, x, y, text, color="#111"):
    fig.add_annotation(x=x, y=y, text=text, showarrow=False, font=dict(size=10, color=color), bgcolor="rgba(255,255,255,0.85)", borderpad=1)


def _width(cap, top):
    return round(1 + 4 * cap / top) if top else 1


def build_map(graph, tree=None, cut=(), side=None, pair=None, classes=None, tree_edges=False, label_tree=False, height=460):
    """Karte: graue Verbindungen (Breite ~ Kapazität); `cut`: Schnittverbindungen (Indizes) rot; `side`: Knotenmenge auf einer Seite des Schnitts (grün); `pair`: (s, t) orange umrandet;
    `classes`: Klassennummer je Knoten (Farbe); `tree_edges`: Baumkanten blau darüber (Breite ~ Gewicht), mit `label_tree` beschriftet."""
    fig = go.Figure()
    top = max((c for _, _, c in graph.edges), default=1)
    cut_set = set(cut)
    plain = [(graph.pos[u][0], graph.pos[u][1], graph.pos[v][0], graph.pos[v][1]) for i, (u, v, c) in enumerate(graph.edges) if i not in cut_set]
    plain_w = [_width(c, top) for i, (u, v, c) in enumerate(graph.edges) if i not in cut_set]
    _lines(fig, plain, C.COLORS["edge"], plain_w, "Verbindung (Breite = Kapazität)")
    if cut_set:
        segs = [(graph.pos[u][0], graph.pos[u][1], graph.pos[v][0], graph.pos[v][1]) for i, (u, v, c) in enumerate(graph.edges) if i in cut_set]
        _lines(fig, segs, C.COLORS["cut"], [_width(c, top) + 2 for i, (u, v, c) in enumerate(graph.edges) if i in cut_set], "Schnittverbindung")
        if len(cut_set) <= 12:
            for i in cut_set:
                u, v, c = graph.edges[i]
                _label(fig, (graph.pos[u][0] + graph.pos[v][0]) / 2, (graph.pos[u][1] + graph.pos[v][1]) / 2, f"{c}", C.COLORS["cut"])
    if tree_edges and tree is not None:
        segs, ws = [], []
        for i, p, w in tree.edges():
            segs.append((graph.pos[i][0], graph.pos[i][1], graph.pos[p][0], graph.pos[p][1]))
            ws.append(2)
            if label_tree:
                _label(fig, (graph.pos[i][0] + graph.pos[p][0]) / 2, (graph.pos[i][1] + graph.pos[p][1]) / 2, f"{w}", C.COLORS["tree"])
        _lines(fig, segs, C.COLORS["tree"], ws, "Baumkante (Gewicht = Schnitt)", dash="dot")
    n = graph.n
    if classes is not None:
        colors = [C.CLASS_COLORS[classes[v] % len(C.CLASS_COLORS)] for v in range(n)]
    elif side is not None:
        colors = [C.COLORS["side"] if v in side else "#8c8c8c" for v in range(n)]
    else:
        colors = [C.COLORS["node"]] * n
    size = 13 if n <= 16 else 10
    outline = [C.COLORS["pair"] if pair and v in pair else "#333" for v in range(n)]
    fig.add_trace(go.Scatter(x=[p[0] for p in graph.pos], y=[p[1] for p in graph.pos], mode="markers+text", text=[str(v + 1) for v in range(n)], textposition="top center", textfont=dict(size=9),
                             hovertext=[f"{graph.names[v]} (Region {graph.region[v] + 1})" for v in range(n)], hoverinfo="text", showlegend=False,
                             marker=dict(size=size, color=colors, line=dict(width=[3 if pair and v in pair else 1.2 for v in range(n)], color=outline))))
    return _frame(fig, graph.pos, height)


def tree_layout(tree):
    """Schema-Lage des Baums: y = Tiefe, x = Reihenfolge der Blätter (Tiefensuche)."""
    adj = tree.adjacency()
    children = {v: [] for v in range(tree.n)}
    seen, stack, order = {0}, [0], []
    while stack:
        x = stack.pop()
        order.append(x)
        for y, _ in sorted(adj[x], reverse=True):
            if y not in seen:
                seen.add(y)
                children[x].append(y)
                stack.append(y)
    pos, counter = {}, [0]

    def place(v, d):
        kids = children[v]
        if not kids:
            pos[v] = (counter[0], -d)
            counter[0] += 1
        else:
            for c in kids:
                place(c, d + 1)
            pos[v] = (sum(pos[c][0] for c in kids) / len(kids), -d)

    import sys
    sys.setrecursionlimit(max(1000, 4 * tree.n))
    place(0, 0)
    return pos


def build_tree(tree, highlight=(), current=None, height=380):
    """Der Gomory-Hu-Baum als Schema: Kanten mit dem Gewicht beschriftet und in der Breite ~ Gewicht; `highlight`: Knoten des Baumpfads (orange), `current`: Baumkante (a, b) rot."""
    fig = go.Figure()
    pos = tree_layout(tree)
    top = max((w for _, _, w in tree.edges()), default=1) or 1
    cur = set(current) if current else set()
    for i, p, w in tree.edges():
        x0, y0 = pos[i]
        x1, y1 = pos[p]
        is_cur = i in cur and p in cur
        fig.add_trace(go.Scatter(x=[x0, x1], y=[y0, y1], mode="lines", line=dict(color=C.COLORS["cut"] if is_cur else C.COLORS["tree"], width=1 + 4 * w / top), hoverinfo="skip", showlegend=False))
        _label(fig, (x0 + x1) / 2, (y0 + y1) / 2, f"{w}", C.COLORS["cut"] if is_cur else C.COLORS["tree"])
    ids = sorted(pos)
    fig.add_trace(go.Scatter(x=[pos[v][0] for v in ids], y=[pos[v][1] for v in ids], mode="markers+text", text=[str(v + 1) for v in ids], textposition="middle right", textfont=dict(size=9), hoverinfo="skip", showlegend=False,
                             marker=dict(size=11 if tree.n <= 24 else 8, color=[C.COLORS["pair"] if v in set(highlight) else C.COLORS["node"] for v in ids], line=dict(width=1, color="#333"))))
    xs = [pos[v][0] for v in ids]
    ys = [pos[v][1] for v in ids]
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.add_trace(go.Scatter(x=[min(xs) - 0.6, max(xs) + 0.6], y=[min(ys) - 0.6, max(ys) + 0.6], mode="markers", marker=dict(opacity=0), hoverinfo="skip", showlegend=False))
    return _base(fig, height)


def build_values(counts, height=300):
    """Wie viele Paare haben welchen minimalen Schnitt."""
    xs = sorted(counts)
    fig = go.Figure(go.Bar(x=[str(x) for x in xs], y=[counts[x] for x in xs], marker_color=C.COLORS["tree"], text=[str(counts[x]) for x in xs], textposition="outside"))
    fig.update_xaxes(title="minimaler Schnitt zwischen zwei Standorten", type="category")
    fig.update_yaxes(title="Paare")
    return _base(fig, height)


def build_scaling(rows, height=340):
    """Durchsuchte Kanten von Gusfield gegen alle Paare je Netzgröße (doppelt logarithmisch)."""
    fig = go.Figure()
    n = [r["n"] for r in rows]
    fig.add_trace(go.Scatter(x=n, y=[r["all"] for r in rows], mode="lines+markers", name="alle Paare (n (n-1)/2 Flüsse)", line=dict(color="#1f77b4", dash="dot")))
    fig.add_trace(go.Scatter(x=n, y=[r["tree"] for r in rows], mode="lines+markers", name="Gusfield (n-1 Flüsse)", line=dict(color=C.COLORS["cut"])))
    fig.update_xaxes(title="Standorte", type="log")
    fig.update_yaxes(title="durchsuchte Kanten", type="log")
    return _base(fig, height)
