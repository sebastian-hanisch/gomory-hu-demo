"""Presets: vollständig, in den Grenzen, und jedes Beispiel zeigt, was sein Hilfetext behauptet."""

import pytest

import gh_constants as C
import gh_evaluation as ev
import gh_presets as P

KEYS = set(P.PRESET_KEYS)


def _params(p):
    return ev.Params(p["net"], p["n"], p["k"], p["regions"], p["cross"], p["bridge"], p["seed"], p["algorithm"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESETS) == 8
    assert all(C.PRESET_HELP[name].strip() for name in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == KEYS, name


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_values_are_inside_the_bounds_and_on_the_step_grid(name):
    p = C.PRESETS[name]
    assert p["net"] in C.NETS and p["algorithm"] in C.ALGORITHMS and p["bridge"] in C.BRIDGES
    for key, state_key in P.PRESET_KEYS.items():
        spec = P.SETTING_SPECS[state_key]
        if spec.lo is not None:
            assert spec.lo <= p[key] <= spec.hi, (name, key)
    assert (p["cross"] - C.CROSS_MIN) % 10 == 0


def test_setting_specs_have_room_to_move():
    """Ein Regler mit lo == hi würde Streamlit abstürzen lassen."""
    assert all(spec.lo < spec.hi for spec in P.SETTING_SPECS.values() if spec.lo is not None)


def test_presets_use_seeds_outside_the_distribution_set():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def test_defaults_equal_the_first_preset():
    p = C.PRESETS["🗺️ Regionen"]
    assert (p["net"], p["n"], p["k"], p["regions"], p["cross"], p["bridge"], p["algorithm"], p["seed"]) == (
        C.DEFAULT_NET, C.DEFAULT_N, C.DEFAULT_K, C.DEFAULT_REGIONS, C.DEFAULT_CROSS, C.DEFAULT_BRIDGE, C.DEFAULT_ALGORITHM, C.DEFAULT_SEED)


def test_fixed_presets_hide_the_random_controls():
    assert {n for n, p in C.PRESETS.items() if p["net"] in C.FIXED_NETS} == {"🏋️ Hantel", "⭐ Stern", "🔲 Gitter 3 × 3", "➡️ Einbahnkante"}


def test_the_presets_show_both_good_and_bad_news():
    """Gut: der Baum spart Flüsse und kodiert alle Paare (jedes Preset, das keine Einbahnkante ist, stimmt mit eigenen Flüssen überein). Schlecht: die Einbahnkante (der Baum antwortet falsch) und
    das Netz mit Brücke (dort hilft der Baum, sonst nicht)."""
    import gh_tree as tr
    for name, p in C.PRESETS.items():
        a = ev.analyse(_params(p))
        if p["net"] == "einbahn":
            continue
        ap, _, _ = tr.all_pairs(a["graph"])
        assert all(a["values"][k] == v for k, v in ap.items()), name
    e = ev.analyse(_params(C.PRESETS["➡️ Einbahnkante"]))
    assert e["values"][(0, 3)] == 0
