# Gomory-Hu-Baum – eine Engpass-Karte für alle Paare – Streamlit-Demo

*(noch nicht deployed)*

Dritte Erweiterung (Stück 15, optional) der **Netzwerkfluss-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", nach [projektauswahl-demo](https://github.com/sebastian-hanisch/projektauswahl-demo) und [graph-cuts-demo](https://github.com/sebastian-hanisch/graph-cuts-demo):
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **ein** Verfahren – den **Gomory-Hu-Baum nach Gusfield** – an einem wachsenden Beispiel.
Wie viel muss man kappen, um zwei Standorte eines Netzes voneinander zu trennen? Das ist der minimale Schnitt zwischen ihnen, und ein Netz mit 24 Standorten hat 276 solche Paare. Ein Gomory-Hu-Baum beantwortet sie alle mit **einem Baum aus 23 Kanten**: der Schnitt zwischen zwei Standorten ist die **kleinste Kante auf ihrem Baumpfad**, und jede Baumkante ist selbst ein minimaler Schnitt, der das Netz in zwei Teile trennt.
Gebaut wird er mit nur **n − 1 Flussberechnungen** statt einer je Paar (Gusfield 1990, nach Gomory und Hu 1961). In den Vorgängern war der minimale Schnitt erst der *Beweis* des maximalen Flusses, dann eine *Entscheidung* (Auswahl, Beschriftung); hier ist er die **Struktur** des Netzes.
Vehikel: ein ungerichtetes Verbindungsnetz zwischen Standorten mit geplanten Regionen (kräftige innere, schwache äußere Verbindungen), dazu vier feste Lehrnetze (Hantel, Stern, Gitter 3 × 3, Einbahnkante). Den Fluss rechnet Boykov–Kolmogorov aus dem Vorgängerstück (Dinic und Edmonds-Karp wählbar).

**Einordnung in die Reihe (die Kanten des Graphen):** Erweiterung E1 „der Schnitt als Modell“, drittes Stück: Nachfolger von graph-cuts-demo (dort war der Schnitt die beste Beschriftung, hier das Verzeichnis aller Schnitte). Nachbarn: die Zuverlässigkeit unter zufälligen Ausfällen in `random-spanning-tree-demo` (dort probabilistisch, hier die feste Kantenverbundenheit); die Cut-Set-Ungleichungen in `fixkosten-netzdesign-demo` (Trennung über Min-Cuts); die Klassen „mindestens k-fach verbunden“ als Cluster (Clustering-Linie). Bisher gebaut: die zwölf Stücke der Hauptlinie und alle drei der Erweiterung E1.
```
edmonds-karp-demo (Wurzel: Restgraph, Rückkanten, Max-Flow = Min-Cut)                  [gebaut]
  ├─ dinic-demo, push-relabel-demo, ssp-demo → … → slope-scaling-demo (Hauptlinie)      [gebaut]

Erweiterung E1: der Schnitt als Modell (Kind von edmonds-karp-demo und dinic-demo)
  └─ projektauswahl-demo (Voraussetzung = unendliche Nachbarstrafe)                     [gebaut]
       └─ graph-cuts-demo (endliche Nachbarstrafe, Boykov-Kolmogorov)                   [gebaut]
            └─ gomory-hu-demo (alle Schnitte in einem Baum, Gusfield)                   [dieses Stück]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` belegt: Lehrnetze von Hand, Beispielnetze über ihre Seeds, Verteilungen über 40 feste Netze (Seeds ab 100000, dieselben wie in den Vorgänger-Demos; Aufwandsverhältnisse über 5 Netze). Standard: 24 Standorte, 3 nächste Nachbarn, 3 Regionen, Kapazität zwischen Regionen 30 % der inneren (innen 5 bis 10), Boykov–Kolmogorov.
Netze, Bäume, Schnittwerte und durchsuchte Kanten sind ganzzahlig und deterministisch (eigener Zufallsstrom); Aufwand wird in durchsuchten Kanten gezählt, nie in Sekunden. Die Kopien aus den Vorgängern sind bewacht (`tests/test_copies.py`).

**Der Baum antwortet wie ein eigener Fluss – für jedes Paar.** Auf 40 Netzen mit 10 Standorten stimmt der Baum in **1 800 von 1 800** Paaren mit einem eigenen Fluss überein (und im Test mit `networkx.gomory_hu_tree`), alle **360 von 360** Baumkanten sind ein Schnitt genau der Kapazität ihres Gewichts, und die **Ultrametrik-Regel** (λ(u,w) ≥ min(λ(u,v), λ(v,w))) gilt für **4 800 von 4 800** Tripeln. Die Klassen „mindestens k-fach verbunden“ (Komponenten des Baums ohne Kanten unter k) sind im Test genau die Paare mit λ ≥ k.

**n − 1 statt n(n − 1)/2 Flüsse – und der Aufwand folgt.** Im Standardnetz 23 Flüsse statt 276; über 5 Netze durchsuchen alle Paare das **10,2-Fache** der Kanten von Gusfield. Je Größe (Mittel über 5 Netze): 8 Standorte 994 gegen 3 831 durchsuchte Kanten (3,9-fach bei 4-fach weniger Flüssen), 40 Standorte 17 241 gegen 350 007 (**20,3-fach** bei 20-fach weniger Flüssen): das Verhältnis wächst mit n, etwa wie n / 2.

**Wenige verschiedene Werte, ein Engpass, der nicht am Standort sitzt.** Über die 40 Standardnetze gibt es im Mittel nur **15,7 verschiedene** Schnittwerte bei 276 Paaren (höchstens n − 1 = 23 sind möglich). Im Beispielnetz (Seed 7) hängt Region 3 (8 Standorte) an einer **einzigen Verbindung der Kapazität 1** (Standorte 20 und 21): 8 × 16 = **128 der 276 Paare** haben deshalb den Schnitt 1, 64 Paare den Schnitt 3, 53 Paare (19 %) den Schnitt „Summe der Kapazitäten am schwächeren Standort“ (Knotengrad). Bei den 40 Standardnetzen sind das im Mittel nur **15,7 %** der Paare; ohne Regionen 25,7 %, mit starker Brücke 18,6 %.

**Der Baum ist ein langer Ast, kein Stern.** Baumtiefe im Mittel **9,5** (höchster Grad 5,4); bei 5 Nachbarn je Standort 5,2, bei 2 Nachbarn 11,2. Der Stern (Lehrnetz mit lauter Blättern der Kapazität 3) ist der Sonderfall, in dem alle 15 Paare den Schnitt 3 haben und der Baum die Tiefe 1.

**Klassen gegen Kantenschwelle: meistens verliert der Baum.** Wiederfinden der geplanten Regionen (Rand-Index beim besten Schwellenwert k, 40 Netze): Kapazität zwischen Regionen 30 %: Klassen des Baums **0,966**, Kantenschwelle (Verbindungen unter k löschen) **0,992** – die Kantenschwelle ist in 16 Netzen besser, der Baum in 0; bei 60 %: 0,914 gegen 0,941 (22 gegen 7). Mit einer **einzelnen starken Brücke** dreht es sich: Baum **0,874**, Kantenschwelle 0,842 (Baum besser in 24, Schwelle in 11) – die Kantenschwelle verschmilzt die beiden Regionen über die Brücke, der Baum nicht. Preset „Starke Brücke“ (Seed 7): 0,924 (k = 16) gegen 0,859 (k = 8).

**Lehrnetze von Hand.** Hantel (zwei Dreiecke der Kapazität 5, eine Verbindung 2): 5 Flüsse statt 15, 2 verschiedene Werte – 6 Paare mit 10, 9 Paare mit 2. Stern: alle 15 Paare 3. Gitter 3 × 3 (Kapazität 2): 26 Paare 4, 10 Paare 6, in allen 36 Paaren gleich dem Knotengrad, 8 Flüsse statt 36.

## Was nicht funktioniert hat / Vorab-Hypothesen

Vor dem Bau standen fünf Vermutungen im Plan. Gemessen:

- **„Die Ersparnis liegt nahe dem Flussverhältnis n / 2“ – bestätigt** (10,2-fach bei 12-fach weniger Flüssen im Standardnetz, 20,3-fach bei 20-fach weniger bei 40 Standorten); jeder Fluss ist im Baumverfahren nicht teurer als ein Paar-Fluss.
- **„Der Engpass sitzt meist am Standort selbst, außer bei Regionen“ – widerlegt:** selbst im gleichmäßigen Netz nur 25,7 % der Paare, mit Regionen 15,7 %; der Engpass ist meistens eine schwache Verbindung oder eine kleine Gruppe.
- **„Wenige verschiedene Schnittwerte“ – bestätigt** (15,7 von 276 möglichen; höchstens n − 1).
- **„Der Baum ist eher ein Stern“ – widerlegt:** Tiefe 9,5, höchster Grad 5,4; je weniger Nachbarn, desto tiefer.
- **„Die Klassen des Baums finden Regionen besser als eine Kantenschwelle“ – nur mit einer starken Einzelverbindung.** Ohne sie genügt die einfache Kantenschwelle und ist besser (0,992 gegen 0,966): der Schnitt eines Standorts ist höchstens die Summe seiner Kapazitäten, wer nur wenige oder schwache Anschlüsse hat, erreicht ein hohes k nie und fällt aus seiner Klasse heraus.
- **Negativkontrolle Einbahnkante:** in einer Kette 1 – 2 – 3 – 4 mit einer Einbahnstraße 2 → 3 antwortet der Baum für die Standorte 1 und 4 mit 0, der Fluss von 1 nach 4 ist aber 4, der von 4 nach 1 ist 0. Für gerichtete Netze gibt es keinen Gomory-Hu-Baum.

## Was die Demo zeigt

- **Wie der Baum entsteht:** ein Regler durch die n − 1 Flüsse: je Schritt das Standortpaar, der minimale Schnitt auf der Karte (grüne Seite, rote Schnittverbindungen), das Umhängen und der Tausch, der bisherige Baum als Schema.
- **Frage an den Baum:** zwei Standorte wählen – Schnittwert aus dem Baumpfad, der Schnitt selbst auf der Karte, Kontrolle durch einen frischen Fluss.
- **Klassen „mindestens k-fach verbunden“:** Regler k, farbige Klassen des Baums neben den Komponenten der Kantenschwelle, Rand-Index gegen die Regionen.
- **Kennzahlen:** verschiedene Schnittwerte, Anteil trivialer Schnitte, Baumform, Verteilung über 40 feste Netze.
- **Experimente (auf Abruf):** Aufwand nach Größe, Klassen gegen Kantenschwelle, Gegenprobe gegen alle Paare.
- **Wo die Annahmen enden:** ungerichtet, Kapazitäten an Kanten, Knotenmengen statt Kantenmengen, feste Kapazitäten.

## Modell und Verfahren

- **Gomory-Hu-Baum:** gewichteter Baum auf den Standorten mit λ(u,v) = kleinste Kante auf dem Baumpfad, und jede Baumkante (a,b) ist ein minimaler a-b-Schnitt (Komponenten von T − e) mit Kapazität w(e).
- **Gusfield (Schnittbaum-Variante):** p[s] = Wurzel für alle; für s = 2..n: Fluss zwischen s und t = p[s], Gewicht der Kante (s,t) = Wert; jeder Standort auf der s-Seite, der an t hing, hängt an s; liegt p[t] auf der s-Seite, tauschen s und t. Kein Kontrahieren, n − 1 Flüsse auf dem ursprünglichen Netz.
- **Klassen:** u ~k v genau dann, wenn λ(u,v) ≥ k (Äquivalenzrelation nach der Ultrametrik-Regel); Klassen = Komponenten des Baums ohne Kanten unter k.
- **Vergleich:** je Paar ein eigener Fluss (alle Paare); Komponenten des Netzes nach Löschen aller Verbindungen unter k (Kantenschwelle); Rand-Index gegen die geplanten Regionen.

## Ehrliche Grenzen

- **Nur ungerichtete Netze.** Bei gerichteten hängt der Schnitt von der Richtung ab; einen Gomory-Hu-Baum gibt es dort nicht.
- **Kapazitäten an Kanten.** Kapazitäten an Standorten verlangen das geteilte Knotenmodell der Flussdemos.
- **Knotenmengen, ein Schnitt je Paar.** Der Baum liefert für jedes Paar einen minimalen Schnitt, nicht alle; der Gleichgewichtsbaum (equivalent flow tree) liefert nur die Werte (nur erwähnt).
- **Feste Kapazitäten.** Fällt eine Verbindung aus, wird der Baum neu gebaut.
- **Synthetische Daten:** erzeugte Netze mit Regionen, kein Kundenbezug.

## Bewusst nicht umgesetzt

- Gomory und Hus Originalverfahren mit Kontraktionen (nur erwähnt), Gleichgewichtsbaum, dynamische Verfahren für sich ändernde Netze.
- Cut-Clustering nach Flake et al. (der Klassenvergleich zeigt nur den einfachen Fall der Schwelle).

## Dateien

```
app.py                  Oberfläche (Streamlit)
gh_scenario.py          Netze mit Regionen, Lehrnetze, Zufallsgenerator, Net (Kopie)
gh_tree.py              Gusfield, Baumabfrage, Baumkantenschnitte, Klassen, Gegenproben
gh_bk.py                Boykov-Kolmogorov (Kopie aus graph-cuts-demo)
gh_dinic.py             Dinic (Kopie aus dinic-demo)
gh_edmonds_karp.py      Edmonds-Karp (Kopie aus edmonds-karp-demo)
gh_evaluation.py        Kennzahlen, Verteilungen, Aufwand, Klassenvergleich, Gegenprobe
gh_visualization.py     Plotly-Abbildungen
gh_presets.py           Permalink, Presets, Zufalls-Seed
gh_constants.py         Konstanten, Regler-Grenzen, feste Seed-Mengen, Preset-Texte
tests/                  Gusfield, Auswertung, Presets, Behauptungen, Kopien, App, Regler-Zustand
```

## Lokal starten

```bash
python -m venv venv
venv/Scripts/pip install -r requirements.txt
venv/Scripts/streamlit run app.py
```

## Tests ausführen

```bash
venv/Scripts/pip install -r requirements-dev.txt
venv/Scripts/python -m pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, NumPy und einem eigenen Flusskern (Boykov–Kolmogorov, Dinic, Edmonds-Karp); networkx nur für die Gegenprobe der Tests.
