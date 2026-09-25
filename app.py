"""Gomory-Hu-Baum - eine Engpass-Karte für alle Paare - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EIN Verfahren - Gusfields Verfahren für den Gomory-Hu-Baum - und lässt stattdessen das Beispiel wachsen.
Dritte Erweiterung (Stück 15) der Netzwerkfluss-Linie der "Konzepte"-Reihe: nach Projektauswahl und Graph Cuts ist der minimale Schnitt hier die Struktur des ganzen Netzes. Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import time

import streamlit as st

import gh_constants as C
import gh_evaluation as ev
import gh_scenario as sc
import gh_tree as tr
from gh_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    seed_widget,
    sync_query_params,
)
from gh_tree import Tree
from gh_visualization import build_map, build_scaling, build_tree, build_values

st.set_page_config(page_title="Gomory-Hu-Baum – Sebastian Hanisch", layout="wide")


def _f(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _int(x):
    return f"{int(round(x)):,}".replace(",", " ")


def _pct(x, digits=0):
    return f"{100 * x:.{digits}f} %".replace(".", ",")


@st.cache_resource(show_spinner=False, max_entries=32)
def _analysis(params):
    return ev.analyse(ev.Params(*params))


@st.cache_resource(show_spinner=False, max_entries=16)
def _distribution(params):
    return ev.distribution(ev.Params(*params))


st.title("🌳 Gomory-Hu-Baum – eine Engpass-Karte für alle Paare")
st.markdown(
    """
Wie viel muss man kappen, um zwei Standorte eines Netzes voneinander zu trennen? Das ist der **minimale Schnitt** zwischen ihnen - und ein Netz mit 24 Standorten hat 276 solche Paare. Der **Gomory-Hu-Baum** beantwortet sie alle mit **einem Baum aus 23 Kanten**:
der Schnitt zwischen zwei Standorten ist die **kleinste Kante auf ihrem Baumpfad**, und jede Baumkante ist selbst ein minimaler Schnitt, der das Netz in zwei Teile trennt. Gebaut wird er mit nur **n − 1 Flussberechnungen** statt einer je Paar (Gusfield 1990, nach Gomory und Hu 1961).
Diese Demo zeigt, wie der Baum entsteht, wie man ihn befragt, was er über das Netz verrät (etwa die Klassen „mindestens k-fach verbunden“) - und wo er nicht mehr gilt: nur für **ungerichtete** Netze.
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - dritte Erweiterung der Netzwerkfluss-Linie der \"Konzepte\"-Reihe, nach \"Projektauswahl\" und \"Graph Cuts\" - **ein** Verfahren an einem wachsenden Beispiel. "
    "In den Vorgängern war der minimale Schnitt erst der *Beweis* des maximalen Flusses, dann eine *Entscheidung* (Auswahl, Beschriftung); hier ist er die **Struktur** des Netzes. Verwandt: die Zuverlässigkeit unter zufälligen Ausfällen in der Demo \"Zufällige Spannbäume\" (dort probabilistisch, hier die feste Kantenverbundenheit)."
)

with st.expander("So funktioniert Gusfields Verfahren", expanded=True):
    st.markdown(
        r"""
1. **Start:** alle Standorte hängen am Standort 1 (der Wurzel), $p[s]=1$ für alle $s$.
2. **Für $s=2,\dots,n$:** rechne einen minimalen Schnitt zwischen $s$ und seinem Elternknoten $t=p[s]$; das Ergebnis ist eine Knotenmenge $X$ auf der $s$-Seite und ein Wert $f$. Die Baumkante $(s,t)$ bekommt das Gewicht $f$.
3. **Umhängen:** jeder Standort $i\ne s$ auf der $s$-Seite, der bisher an $t$ hing, hängt jetzt an $s$. Liegt der Elternknoten von $t$ auf der $s$-Seite, **tauschen** $s$ und $t$ ihre Plätze (das macht aus dem Baum einen echten *Schnittbaum*).
4. **Ergebnis:** nach $n-1$ Flüssen ist der Baum fertig. Der Schnitt zwischen $u$ und $v$ ist die kleinste Kante auf dem Baumpfad; entfernt man diese Kante, zerfällt der Baum in zwei Teile, und ihre Knotenmengen sind ein minimaler Schnitt des Netzes.
5. **Klassen:** löscht man aus dem Baum alle Kanten unter $k$, sind die Komponenten genau die Klassen der Standorte, die **paarweise mindestens $k$-fach verbunden** sind (Schnitt $\ge k$).
        """
    )

st.caption("🎯 Schnellstart – ein Beispiel laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox("Netz", list(C.NETS), key="net_select", format_func=lambda k: C.NETS[k],
                           help="Ein zufälliges Netz mit Regionen oder ein festes Lehrnetz: Hantel (zwei Dreiecke, eine Brücke), Stern, Gitter 3 × 3 - oder die Einbahnkante als Negativkontrolle (der Baum gilt nur für ungerichtete Netze).")
    algorithm = st.radio("Flussverfahren", list(C.ALGORITHMS), key="algorithm_radio", format_func=lambda k: C.ALGORITHMS[k],
                         help="Alle drei liefern denselben Baum-Wert je Paar; sie unterscheiden sich in den durchsuchten Kanten. Voreinstellung ist Boykov–Kolmogorov (Stück 14).")
    if net_key == "random":
        seed_widget("n_slider")
        n = st.slider("Standorte", *bounds("n_slider"), key="n_slider", help="Anzahl der Standorte; bei n Standorten braucht Gusfield n − 1 Flüsse, alle Paare bräuchten n (n − 1) / 2.")
        st.session_state[KEPT["n_slider"]] = n
        seed_widget("k_slider")
        k = st.slider("Verbindungen je Standort (nächste Nachbarn)", *bounds("k_slider"), key="k_slider", help="Jeder Standort ist mit seinen k nächsten Nachbarn verbunden. Mehr Verbindungen: weniger Tiefe im Baum (bei 5 im Mittel 5,2, bei 3 rund 9,5).")
        st.session_state[KEPT["k_slider"]] = k
        seed_widget("regions_slider")
        regions = st.slider("Regionen", *bounds("regions_slider"), key="regions_slider", help="Geplante Regionen mit kräftigen inneren und schwachen Verbindungen dazwischen; bei 1 gibt es keine Regionen.")
        st.session_state[KEPT["regions_slider"]] = regions
        seed_widget("cross_slider")
        cross = st.slider("Kapazität zwischen Regionen [% der inneren]", *bounds("cross_slider"), key="cross_slider", step=10, help="Wie schwach die Verbindungen zwischen den Regionen sind. Bei 100 % gibt es keinen Unterschied zwischen innen und außen.")
        st.session_state[KEPT["cross_slider"]] = cross
        seed_widget("bridge_radio")
        bridge = st.radio("Brücke zwischen Region 1 und 2", list(C.BRIDGES), key="bridge_radio", format_func=lambda b: C.BRIDGES[b],
                          help="Eine einzelne starke Verbindung (Kapazität 20) schließt zwei Regionen kurz: die Kantenschwelle verbindet sie dann, der Gomory-Hu-Baum nicht.")
        st.session_state[KEPT["bridge_radio"]] = bridge
        seed_widget("seed_input")
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Zufalls-Seed. Die Verteilungen über 40 feste Netze weiter unten ändern sich dabei nicht.")
    else:
        n = int(st.session_state.get(KEPT["n_slider"], C.DEFAULT_N))
        k = int(st.session_state.get(KEPT["k_slider"], C.DEFAULT_K))
        regions = int(st.session_state.get(KEPT["regions_slider"], C.DEFAULT_REGIONS))
        cross = int(st.session_state.get(KEPT["cross_slider"], C.DEFAULT_CROSS))
        bridge = int(st.session_state.get(KEPT["bridge_radio"], C.DEFAULT_BRIDGE))
        seed = int(st.session_state.get(KEPT["seed_input"], C.DEFAULT_SEED))
        st.caption("Dieses Netz ist fest - es gibt nichts zu erzeugen. Standorte, Verbindungen, Regionen, Kapazität, Brücke und Seed gehören zum zufälligen Netz.")

sync_query_params({"net_select": net_key, "algorithm_radio": algorithm, "n_slider": int(n), "k_slider": int(k), "regions_slider": int(regions), "cross_slider": int(cross),
                   "bridge_radio": int(bridge), "seed_input": int(seed)})

# feste Lehrnetze ignorieren die Zufallsregler: sonst würden gleiche Netze unter verschiedenen Schlüsseln mehrfach berechnet
params = (net_key, int(n), int(k), int(regions), int(cross), int(bridge), int(seed), algorithm)
if net_key in C.FIXED_NETS:
    params = (net_key, C.DEFAULT_N, C.DEFAULT_K, C.DEFAULT_REGIONS, C.DEFAULT_CROSS, C.DEFAULT_BRIDGE, C.DEFAULT_SEED, algorithm)
with st.spinner("Rechne..."):
    a = _analysis(params)
g, tree = a["graph"], a["tree"]
N = g.n
label = lambda v: g.names[v]

# --- Baum bauen -------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Wie der Baum entsteht")
if st.session_state.get("gh_step_owner") != params:
    st.session_state["gh_step"] = N - 1
    st.session_state["gh_step_owner"] = params
step_col, play_col = st.columns([5, 2])
with step_col:
    step = st.slider("Fluss", 0, N - 1, key="gh_step", help="Schritt 0: das Netz ohne Baum; Schritt k: der k-te Fluss (Standort k + 1 gegen seinen Elternknoten) ist gerechnet, der Baum wächst um eine Kante.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch")
view_slot = st.empty()


def _render(kk):
    with view_slot.container():
        c1, c2 = st.columns(2)
        if kk == 0:
            c1.markdown("**Das Netz** - noch keine Flüsse gerechnet")
            c1.plotly_chart(build_map(g), width="stretch", key=f"map_{kk}")
            c2.markdown("**Der Baum** - alle Standorte hängen an Standort 1")
            c2.plotly_chart(build_tree(Tree(N, (-1,) + (0,) * (N - 1), (0,) * N, (), 0)), width="stretch", key=f"tree_{kk}")
            st.caption("Grau: Verbindungen (Breite = Kapazität). Im Baum hängt zu Beginn jeder Standort an der Wurzel; die Gewichte kommen mit den Flüssen.")
            return
        s = tree.steps[kk - 1]
        cut = [i for i, _, _, _ in tr.cut_edges(g, s.side)]
        c1.markdown(f"**Fluss {kk} von {N - 1}:** Standort {s.s + 1} gegen Standort {s.t + 1} - Schnitt {s.value}")
        c1.plotly_chart(build_map(g, cut=cut, side=s.side, pair=(s.s, s.t)), width="stretch", key=f"map_{kk}")
        partial_parent = tuple(-1 if (i == 0 or i > kk) else s.parent[i] for i in range(N))
        partial_weight = tuple(s.weight[i] if 0 < i <= kk else 0 for i in range(N))
        c2.markdown("**Der Baum bis hierher**")
        c2.plotly_chart(build_tree(Tree(N, partial_parent, partial_weight, (), 0), current=(s.s, s.t) if s.parent[s.s] == s.t else None), width="stretch", key=f"tree_{kk}")
        moved = [i for i in range(N) if i not in (s.s,) and i > kk and s.parent[i] == s.s]
        swap = " Der Elternknoten von Standort " + str(s.t + 1) + " lag auf der s-Seite: **Tausch** von " + str(s.s + 1) + " und " + str(s.t + 1) + "." if s.swapped else ""
        st.caption(f"Grün die s-Seite des minimalen Schnitts ({len(s.side)} Standorte), rot die Verbindungen, die er kappt (Kapazität {s.value}); orange umrandet die beiden Standorte. Der Fluss durchsuchte {_int(s.scanned)} Kanten. "
                   f"Danach hängen {len(moved)} noch nicht bearbeitete Standorte an Standort {s.s + 1}.{swap}")


if auto_play:
    for kk in range(N):
        _render(kk)
        time.sleep(min(0.7, 7.0 / max(N, 1)))
    step = N - 1
else:
    _render(step)

st.markdown("---")

# --- Frage an den Baum ------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Frage an den Baum: wie schwer sind zwei Standorte zu trennen?")
q1, q2 = st.columns(2)
u = q1.selectbox("Von", list(range(N)), index=0, format_func=lambda v: f"{v + 1}", key="pair_u")
v = q2.selectbox("Nach", list(range(N)), index=min(N - 1, N // 2), format_func=lambda v: f"{v + 1}", key="pair_v")
if u == v:
    st.info("Bitte zwei verschiedene Standorte wählen.")
else:
    value, pth, edge = tr.query(tree, u, v)
    side = tr.tree_side(tree, edge[0], edge[1])
    cut = [i for i, _, _, _ in tr.cut_edges(g, side)]
    fresh = tr.min_cut(sc.with_terminals(g.to_net(), u, v), algorithm)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Minimaler Schnitt (aus dem Baum)", f"{value}", help="Die kleinste Kante auf dem Baumpfad: eine Abfrage ohne neuen Fluss.")
    m2.metric("Kontrolle: frischer Fluss", f"{fresh[0]}", delta="gleich" if fresh[0] == value else "verschieden", delta_color="off", help="Ein eigener Fluss zwischen den beiden Standorten; im ungerichteten Netz stimmt er mit dem Baum immer überein.")
    m3.metric("Baumpfad", f"{len(pth) - 1} Kanten", delta=" → ".join(str(x + 1) for x in pth), delta_color="off")
    m4.metric("Schnittverbindungen", f"{len(cut)}", delta=f"Kapazität {tr.cut_capacity(g, side)}", delta_color="off", help="Die Verbindungen des Netzes zwischen den beiden Seiten der entscheidenden Baumkante: zusammen genau der Schnittwert.")
    c1, c2 = st.columns(2)
    c1.plotly_chart(build_map(g, cut=cut, side=side, pair=(u, v)), width="stretch", key="pair_map")
    c2.plotly_chart(build_tree(tree, highlight=pth, current=(edge[0], edge[1])), width="stretch", key="pair_tree")
    st.caption(f"Die schwächste Kante auf dem Baumpfad ist ({edge[0] + 1}, {edge[1] + 1}) mit dem Gewicht {edge[2]}: entfernt man sie, trennt der Baum die Standorte in zwei Mengen ({len(side)} und {N - len(side)} Standorte), und im Netz gibt es zwischen diesen Mengen genau {len(cut)} Verbindungen mit der Gesamtkapazität {tr.cut_capacity(g, side)}. Das ist ein minimaler Schnitt zwischen {u + 1} und {v + 1}.")
    if net_key == "einbahn":
        forward = tr.min_cut(sc.with_terminals(g.to_net(), 0, N - 1), algorithm)[0]
        backward = tr.min_cut(sc.with_terminals(g.to_net(), N - 1, 0), algorithm)[0]
        st.warning(f"⚠️ **Negativkontrolle:** die Verbindung 2 → 3 ist eine Einbahnstraße. Der Baum wurde mit Flüssen von Standort s nach seinem Elternknoten gebaut und antwortet für die Standorte 1 und 4: {tr.query(tree, 0, N - 1)[0]}. "
                   f"Der Fluss von 1 nach 4 ist aber {forward}, der von 4 nach 1 ist {backward}. Für gerichtete Netze gibt es keinen solchen Baum: der Schnitt hängt von der Richtung ab.")

st.markdown("---")

# --- Klassen ≥ k ------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Welche Standorte gehören zusammen? Klassen „mindestens k-fach verbunden“")
top = max(w for _, _, w in tree.edges())
kmax = max(2, top)
kk = st.slider("Schnitt mindestens k", 1, kmax, min(kmax, 4), key="k_class", help="Standorte, zwischen denen jeder Schnitt mindestens k ist, bilden eine Klasse; sie stehen im Baum durch Kanten mit Gewicht ab k zusammen.")
cls = tr.classes(tree, kk)
thr = tr.threshold_components(g, kk)
n_cls, n_thr = len(set(cls)), len(set(thr))
r1, r2, r3 = st.columns(3)
r1.metric("Klassen im Gomory-Hu-Baum", f"{n_cls}", help="Komponenten des Baums ohne Kanten unter k.")
r2.metric("Komponenten der Kantenschwelle", f"{n_thr}", help="Komponenten des Netzes, wenn alle Verbindungen unter Kapazität k gelöscht werden.")
if g.kind == "random" and regions > 1:
    r3.metric("Rand-Index gegen die Regionen", f"{_f(tr.rand_index(cls, g.region), 3)} gegen {_f(tr.rand_index(thr, g.region), 3)}", delta="Baum gegen Kantenschwelle", delta_color="off", help="1 = die geplanten Regionen werden genau wiedergefunden; links die Klassen des Baums, rechts die Kantenschwelle.")
cc1, cc2 = st.columns(2)
cc1.markdown("**Klassen des Baums** (Farbe = Klasse)")
cc1.plotly_chart(build_map(g, classes=cls, tree_edges=True, tree=tree), width="stretch", key="class_map")
cc2.markdown("**Komponenten der Kantenschwelle**")
cc2.plotly_chart(build_map(g, classes=thr), width="stretch", key="thr_map")
st.caption("Gleiche Farbe = gleiche Klasse. Die Klassen des Baums sind exakt die Standorte, die paarweise mindestens k-fach verbunden sind (im Test gegen alle Paare geprüft); die Kantenschwelle löscht nur einzelne schwache Verbindungen und kann dadurch Regionen über eine starke Einzelverbindung verschmelzen - oder einen Standort mit vielen schwachen Anschlüssen abtrennen.")

st.markdown("---")

# --- Verteilung -------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Was verrät der Baum über das Netz?")
mm1, mm2, mm3, mm4 = st.columns(4)
mm1.metric("Flüsse", f"{tree.flows} statt {a['pairs']}", help="Gusfield rechnet n − 1 Flüsse; alle Paare bräuchten n (n − 1) / 2.")
mm2.metric("Verschiedene Schnittwerte", f"{a['distinct']}", delta=f"bei {a['pairs']} Paaren", delta_color="off", help="Wie viele verschiedene Werte der minimale Schnitt über alle Paare annimmt: der Baum hat nur n − 1 Kanten, also höchstens n − 1 verschiedene.")
mm3.metric("Schnitt = Knotengrad", f"{a['trivial']} von {a['pairs']}", delta=_pct(a["trivial"] / a["pairs"]), delta_color="off", help="Paare, deren minimaler Schnitt gerade die Summe der Kapazitäten am schwächeren der beiden Standorte ist (der Engpass sitzt am Standort selbst).")
mm4.metric("Baum", f"Tiefe {a['depth']}, Grad {a['max_degree']}", help="Tiefe: längster Weg von der Wurzel; Grad: höchste Zahl der Baumkanten an einem Standort.")
st.plotly_chart(build_values(a["counts"]), width="stretch", key="values_chart")
st.caption("Alle Paare nach ihrem minimalen Schnitt: wenige verschiedene Werte, weil viele Paare durch dieselbe Baumkante getrennt werden.")
if net_key in C.FIXED_NETS:
    st.info("Festes Lehrnetz: es gibt nur diese eine Ziehung. Für die Verteilungen über viele Netze ein zufälliges Netz wählen.")
else:
    st.markdown(f"**Nicht nur dieses eine Netz:** 40 feste Netze mit denselben Einstellungen (Standorte {n}, Verbindungen {k}, Regionen {regions}, Kapazität zwischen Regionen {cross} %, Brücke: {C.BRIDGES[bridge]}), getrennt vom Seed oben.")
    dist = _distribution(params)
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Aufwand: alle Paare ÷ Gusfield", _f(dist["scan_ratio"], 1), delta=f"Flussverhältnis {_f(dist['flows_all'] / dist['flows_tree'], 1)}", delta_color="off", help="Durchsuchte Kanten aller Paar-Flüsse geteilt durch die von Gusfield (Mittel über 5 Netze); das Verhältnis der Flüsse (n / 2) steht darunter.")
    p2.metric("Verschiedene Schnittwerte", _f(dist["distinct"], 1), delta=f"bei {dist['pairs']} Paaren", delta_color="off")
    p3.metric("Schnitt = Knotengrad", _pct(dist["trivial"]), help="Mittlerer Anteil der Paare mit trivialem Schnitt.")
    p4.metric("Baumtiefe", _f(dist["depth"], 1), delta=f"Grad {_f(dist['max_degree'], 1)}", delta_color="off", help="Mittlere Tiefe des Baums und mittlerer höchster Grad über die Netze: der Baum ist eher ein langer Ast als ein Stern.")

st.markdown("---")

# --- Experimente -------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Wächst die Ersparnis mit dem Netz?")
st.caption("Durchsuchte Kanten von Gusfield gegen alle Paare, von 8 bis 40 Standorten (Boykov–Kolmogorov, Mittel über 5 feste Netze je Größe).")
if st.button("Netze durchrechnen (dauert wenige Sekunden)", key="scaling_start"):
    st.session_state["scaling_on"] = True
if st.session_state.get("scaling_on"):
    with st.spinner("Rechne 6 Größen × 5 Netze..."):
        rows = ev.scaling(algorithm=algorithm)
    st.plotly_chart(build_scaling(rows), width="stretch", key="scaling_chart")
    st.table({"Standorte": [r["n"] for r in rows], "Flüsse Gusfield": [r["flows_tree"] for r in rows], "Flüsse alle Paare": [r["flows_all"] for r in rows],
              "Kanten Gusfield": [_int(r["tree"]) for r in rows], "Kanten alle Paare": [_int(r["all"]) for r in rows], "Verhältnis": [_f(r["all"] / r["tree"], 1) for r in rows]})
    st.caption("Das Verhältnis der durchsuchten Kanten folgt dem der Flüsse: etwa n / 2. Jeder Fluss ist im Baumverfahren nicht teurer als ein Paar-Fluss.")

st.subheader("🔬 Finden die Klassen die Regionen besser als eine Kantenschwelle?")
st.caption("Für jedes der 40 festen Netze der Einstellung der bestmögliche Schwellenwert k (Orakel über 1 bis 24) und der Rand-Index gegen die geplanten Regionen: Klassen des Gomory-Hu-Baums gegen Komponenten der Kantenschwelle.")
if net_key != "random" or regions < 2:
    st.info("Für dieses Experiment ein zufälliges Netz mit mindestens zwei Regionen wählen.")
else:
    if st.button("Netze vergleichen (dauert wenige Sekunden)", key="classes_start"):
        st.session_state["classes_on"] = True
    if st.session_state.get("classes_on"):
        with st.spinner("Rechne 40 Netze..."):
            ce = ev.classes_experiment(ev.Params(*params))
        e1, e2, e3 = st.columns(3)
        e1.metric("Rand-Index Gomory-Hu-Klassen", _f(ce["tree"], 3))
        e2.metric("Rand-Index Kantenschwelle", _f(ce["threshold"], 3))
        e3.metric("Baum besser / Schwelle besser", f"{ce['tree_better']} / {ce['threshold_better']}", delta=f"von {ce['n']} Netzen", delta_color="off")
        st.caption("Bei kräftigen inneren und schwachen äußeren Verbindungen genügt schon die einfache Kantenschwelle; der Baum verliert dort, weil Standorte mit wenigen Anschlüssen nie ein hohes k erreichen und aus ihrer Klasse herausfallen. Mit einer **starken Brücke** zwischen zwei Regionen dreht sich das: die Kantenschwelle verschmilzt die Regionen, der Baum nicht (Regler „Brücke“ oben).")

st.subheader("🔬 Stimmt der Baum wirklich?")
st.caption("Gegenprobe auf 40 kleinen Netzen (10 Standorte): für jedes der 45 Paare ein eigener Fluss gegen die Antwort des Baums; jede Baumkante gegen die Kapazität ihres Schnitts; die Ultrametrik-Regel („zwischen u und w ist der Schnitt mindestens so groß wie der kleinere der Schnitte u–v und v–w“).")
if st.button("40 kleine Netze prüfen", key="check_start"):
    st.session_state["check_on"] = True
if st.session_state.get("check_on"):
    chk = ev.small_check()
    x1, x2, x3 = st.columns(3)
    x1.metric("Paare wie ein eigener Fluss", f"{chk['pairs_ok']} von {chk['pairs_total']}")
    x2.metric("Baumkanten = Schnitt", f"{chk['edges_ok']} von {chk['edges_total']}")
    x3.metric("Ultrametrik-Regel", f"{chk['ultra_ok']} von {chk['ultra_total']}")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist - und wer ansetzt |
|---|---|
| **Ungerichtetes Netz** | Bei gerichteten Netzen hängt der Schnitt von der Richtung ab; einen Gomory-Hu-Baum gibt es dort nicht (Preset „Einbahnkante“). Man rechnet dann je Paar einen Fluss oder wertet nur die Richtungen aus, die man braucht. |
| **Kapazitäten an Kanten** | Der Baum kennt nur Verbindungen. Kapazitäten an Standorten (ein Verteilzentrum mit Durchsatz) verlangen das geteilte Knotenmodell der Flussdemos. |
| **Knotenmengen statt Kantenmengen** | Der Baum liefert für jedes Paar *einen* minimalen Schnitt, nicht alle; die Schnitte der Baumkanten sind nicht immer verschachtelt. Der *Gleichgewichtsbaum* (equivalent flow tree) liefert nur die Werte, nicht die Schnitte (nur erwähnt). |
| **Feste Kapazitäten** | Fällt eine Verbindung aus oder wächst eine, muss der Baum neu gebaut werden; Verfahren für dynamische Netze sind ein eigenes Thema. |
| **Eine Ziehung** | Die Kapazitäten sind bekannt und fest; unter zufälligen Ausfällen (Zuverlässigkeit) ist die Frage eine andere (Demo „Zufällige Spannbäume“). |
"""
)
st.caption("Die Netzwerkfluss-Linie ist als Ganzes geplant: die zwölf Stücke der Hauptlinie (gebaut), dazu die Erweiterung E1: **Projektauswahl**, **Graph Cuts** und **Gomory-Hu-Baum** (dieses Stück, gebaut).")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Minimaler Schnitt.** Für ein ungerichtetes Netz $G=(V,E,c)$ und zwei Knoten $s,t$ sei $\lambda(s,t)=\min\{c(X,\bar X): s\in X,\ t\in\bar X\}=$ maximaler $s$-$t$-Fluss (Max-Flow = Min-Cut).

**Gomory-Hu-Baum.** Ein gewichteter Baum $T$ auf $V$ mit Gewichten $w$, so dass für alle $u,v$:
$$\lambda(u,v)=\min_{e\in P_T(u,v)} w(e),$$
und für jede Baumkante $e=(a,b)$ ist $(X_e,\bar X_e)$ (die Komponenten von $T-e$) ein minimaler $a$-$b$-Schnitt mit $c(X_e,\bar X_e)=w(e)$. Gomory und Hu (1961) bauten ihn mit Kontraktionen; **Gusfield (1990)** ohne: $n-1$ Flüsse, jeder auf dem ursprünglichen Netz.

**Ultrametrik.** Aus $\lambda(u,w)\ge\min(\lambda(u,v),\lambda(v,w))$ (Schnitte lassen sich verketten) folgt, dass die Werte $\lambda(\cdot,\cdot)$ durch die $n-1$ Baumgewichte bestimmt sind: höchstens $n-1$ verschiedene Werte.

**Klassen.** Die Relation $u\sim_k v\iff\lambda(u,v)\ge k$ ist eine Äquivalenzrelation (Transitivität folgt aus der Ultrametrik); ihre Klassen sind die Komponenten von $T$ nach Entfernen aller Kanten mit Gewicht unter $k$. Sie sind die *$k$-kantenzusammenhängenden Klassen* des Netzes.

**Aufwand.** $n-1$ statt $\binom n2$ Flüsse: das Verhältnis ist $n/2$. Eine Abfrage kostet $O(n)$ (Baumpfad); die Matrix aller Paare belegt $\binom n2$ Einträge.

Implementiert in `gh_scenario.py` (Netze, Regionen, Lehrnetze, eigener Zufallsgenerator), `gh_tree.py` (Gusfield, Abfrage, Baumkantenschnitte, Klassen, Gegenproben), `gh_bk.py`, `gh_dinic.py` und `gh_edmonds_karp.py` (Flusskerne aus den Vorgängern), `gh_evaluation.py` (Kennzahlen, Verteilungen, Experimente).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
