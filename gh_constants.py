"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Gomory-Hu-Baum: eine Engpass-Karte für alle Paare"."""

# --- Regler ---------------------------------------------------------------------------------------------------------------------
N_MIN, N_MAX, DEFAULT_N = 8, 40, 24                    # Standorte
K_MIN, K_MAX, DEFAULT_K = 2, 5, 3                      # Verbindungen je Standort (nächste Nachbarn)
REGIONS_MIN, REGIONS_MAX, DEFAULT_REGIONS = 1, 5, 3    # geplante Regionen
CROSS_MIN, CROSS_MAX, DEFAULT_CROSS = 10, 100, 30      # Kapazität zwischen Regionen in Prozent der inneren, Schritt 10
DEFAULT_SEED = 7
SEED_MAX = 2_000_000_000

NETS = {
    "random": "Zufälliges Netz mit Regionen",
    "hantel": "Hantel (zwei Dreiecke, eine Brücke)",
    "stern": "Stern (Mitte und fünf Blätter)",
    "gitter": "Gitter 3 × 3",
    "einbahn": "Einbahnkante (Negativkontrolle)",
}
DEFAULT_NET = "random"
FIXED_NETS = ("hantel", "stern", "gitter", "einbahn")
BRIDGES = {0: "keine", 1: "eine starke Brücke"}
DEFAULT_BRIDGE = 0
ALGORITHMS = {"bk": "Boykov–Kolmogorov", "dinic": "Dinic", "bfs": "Edmonds-Karp"}
DEFAULT_ALGORITHM = "bk"

# --- feste Seed-Mengen (dieselben wie in den Flussdemos; unabhängig vom Nutzer-Seed) ---------------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
SWEEP_SEEDS = DIST_SEEDS[:40]
SCAN_SEEDS = DIST_SEEDS[:5]
SCALE_SIZES = (8, 12, 16, 24, 32, 40)
K_RANGE = tuple(range(1, 25))          # Schwellen für die Klassenvergleiche

COLORS = {"edge": "rgba(120,120,120,0.55)", "cut": "#d62728", "tree": "#1f77b4", "side": "#2ca02c", "pair": "#ff7f0e", "node": "#111111", "faint": "rgba(150,150,150,0.45)"}
CLASS_COLORS = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf")

# --- Presets -----------------------------------------------------------------------------------------------------------------
_BASE = dict(net=DEFAULT_NET, n=DEFAULT_N, k=DEFAULT_K, regions=DEFAULT_REGIONS, cross=DEFAULT_CROSS, bridge=DEFAULT_BRIDGE, algorithm=DEFAULT_ALGORITHM, seed=DEFAULT_SEED)
PRESETS = {
    "🗺️ Regionen": {**_BASE},
    "⚖️ Gleichmäßiges Netz": {**_BASE, "regions": 1, "cross": 100},
    "🌉 Starke Brücke": {**_BASE, "bridge": 1},
    "🕸️ Dünnes Netz": {**_BASE, "k": 2},
    "🏋️ Hantel": {**_BASE, "net": "hantel"},
    "⭐ Stern": {**_BASE, "net": "stern"},
    "🔲 Gitter 3 × 3": {**_BASE, "net": "gitter"},
    "➡️ Einbahnkante": {**_BASE, "net": "einbahn"},
}
# Jede Zahl in diesen Texten ist in tests/test_claims.py belegt (Lehrnetze von Hand, Zufallsnetze über die Seeds der Presets)
PRESET_HELP = {
    "🗺️ Regionen": "24 Standorte, 45 Verbindungen, drei Regionen: Gusfield braucht 23 Flüsse statt 276 und findet nur 16 verschiedene Schnittwerte. Region 3 (8 Standorte) hängt an einer einzigen Verbindung der Kapazität 1: 8 × 16 = 128 der 276 Paare haben deshalb den Schnitt 1. Durchsuchte Kanten: 6 037.",
    "⚖️ Gleichmäßiges Netz": "Ohne Regionen (alle Verbindungen gleich kräftig): 15 verschiedene Schnittwerte bei 276 Paaren; in 104 Paaren sitzt der Engpass am Standort selbst (Schnitt = Summe der Kapazitäten am schwächeren Standort), 80 Paare haben den Schnitt 7.",
    "🌉 Starke Brücke": "Dasselbe Netz mit einer einzelnen starken Verbindung (Kapazität 20) zwischen Region 1 und 2. Beim besten Schwellenwert finden die Klassen des Gomory-Hu-Baums die Regionen mit Rand-Index 0,924 (k = 16), die Kantenschwelle nur mit 0,859 (k = 8): sie verschmilzt die beiden Regionen über die Brücke.",
    "🕸️ Dünnes Netz": "Nur zwei Nachbarn je Standort: 32 Verbindungen, 11 verschiedene Schnittwerte, für 176 von 276 Paaren ist der Schnitt 1. Der Baum ist ein langer Ast (Tiefe 10, höchster Grad 3), 3 354 durchsuchte Kanten.",
    "🏋️ Hantel": "Zwei Dreiecke (Kapazität 5) durch eine Verbindung der Kapazität 2 verbunden: 5 Flüsse statt 15, nur 2 verschiedene Schnittwerte - 6 Paare innerhalb eines Dreiecks haben den Schnitt 10, 9 Paare zwischen den Dreiecken den Schnitt 2.",
    "⭐ Stern": "Eine Mitte mit fünf Blättern der Kapazität 3: alle 15 Paare haben den Schnitt 3, der Gomory-Hu-Baum ist der Stern selbst (Tiefe 1).",
    "🔲 Gitter 3 × 3": "Alle Verbindungen Kapazität 2: 26 Paare haben den Schnitt 4 (ein Paar mit einer Ecke), 10 Paare den Schnitt 6; in allen 36 Paaren ist der Schnitt die Summe der Kapazitäten am schwächeren Standort. 8 Flüsse statt 36.",
    "➡️ Einbahnkante": "Kette mit einer Einbahnstraße (2 → 3): der Baum antwortet für die Standorte 1 und 4 mit 0, der Fluss von 1 nach 4 ist aber 4 und der von 4 nach 1 ist 0. Für gerichtete Netze gibt es keinen Gomory-Hu-Baum.",
}
