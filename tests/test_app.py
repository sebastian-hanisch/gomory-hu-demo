"""Rauchtests der Streamlit-Oberfläche per AppTest: Standard, jedes Preset, alle Flussverfahren, Randgrößen, Bilder-Regler, Paar-Anfrage, Klassen-Regler, Permalink, ausgeblendete Regler, Experimente."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import gh_constants as C
from gh_presets import PRESET_KEYS

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"


def _run(setup=None, timeout=300):
    at = AppTest.from_file(str(APP), default_timeout=timeout)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if setup is not None:
        setup(at)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _apply(at, p):
    for key, state_key in PRESET_KEYS.items():
        at.session_state[state_key] = p[key]


def _metric(at, label):
    return [m.value for m in at.metric if m.label == label]


def _step_slider(at):
    found = [s for s in at.slider if s.key == "gh_step"]
    return found[0] if found else None


def test_default_renders_without_exception():
    at = _run()
    assert _metric(at, "Flüsse")[0] == "23 statt 276" and _metric(at, "Verschiedene Schnittwerte")[0] == "16" and _metric(at, "Schnitt = Knotengrad")[0] == "53 von 276"
    assert _step_slider(at).value == _step_slider(at).max == 23
    assert _metric(at, "Minimaler Schnitt (aus dem Baum)") and _metric(at, "Kontrolle: frischer Fluss") == _metric(at, "Minimaler Schnitt (aus dem Baum)")


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_renders(name):
    at = _run(lambda a: _apply(a, C.PRESETS[name]))
    assert not at.error and _metric(at, "Flüsse")


@pytest.mark.parametrize("algorithm", list(C.ALGORITHMS))
def test_every_flow_method_renders(algorithm):
    at = _run(lambda a: a.session_state.__setitem__("algorithm_radio", algorithm))
    assert _metric(at, "Flüsse")[0] == "23 statt 276"


def test_extreme_sizes_render():
    for vals in ((("n_slider", C.N_MIN), ("k_slider", C.K_MIN), ("regions_slider", C.REGIONS_MIN), ("cross_slider", C.CROSS_MIN)),
                 (("n_slider", C.N_MAX), ("k_slider", C.K_MAX), ("regions_slider", C.REGIONS_MAX), ("cross_slider", C.CROSS_MAX))):
        def setup(at, vals=vals):
            for key, value in vals:
                at.session_state[key] = value
        at = _run(setup)
        assert not at.error and _metric(at, "Flüsse")


def test_step_slider_moves_through_all_frames():
    at = _run(lambda a: _apply(a, C.PRESETS["🏋️ Hantel"]))
    top = int(_step_slider(at).max)
    assert top == 5
    for value in range(top + 1):
        _step_slider(at).set_value(value)
        at.run()
        assert not at.exception and _step_slider(at).value == value


def test_pair_query_and_class_slider():
    at = _run(lambda a: _apply(a, C.PRESETS["🏋️ Hantel"]))
    at.selectbox(key="pair_u").set_value(0)
    at.selectbox(key="pair_v").set_value(5)
    at.run()
    assert not at.exception and _metric(at, "Minimaler Schnitt (aus dem Baum)") == ["2"] and _metric(at, "Kontrolle: frischer Fluss") == ["2"]
    at.selectbox(key="pair_v").set_value(0)
    at.run()
    assert not at.exception and any("zwei verschiedene Standorte" in i.value for i in at.info)
    at.slider(key="k_class").set_value(5)
    at.run()
    assert not at.exception and _metric(at, "Klassen im Gomory-Hu-Baum") == ["2"]


def test_the_one_way_preset_warns():
    at = _run(lambda a: _apply(a, C.PRESETS["➡️ Einbahnkante"]))
    assert any("Negativkontrolle" in w.value for w in at.warning)


def test_hidden_controls_keep_their_values_across_a_net_switch():
    at = _run()
    at.sidebar.slider(key="n_slider").set_value(30)
    at.run()
    at.sidebar.selectbox(key="net_select").set_value("hantel")
    at.run()
    assert not at.exception and not [w for w in at.sidebar.slider if w.key == "n_slider"]
    at.sidebar.selectbox(key="net_select").set_value("random")
    at.run()
    assert at.sidebar.slider(key="n_slider").value == 30 and not at.exception


def test_permalink_settings_are_loaded_and_clamped():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.query_params["net"] = "random"
    at.query_params["n"] = "99"
    at.query_params["k"] = "4"
    at.query_params["cross"] = "47"
    at.query_params["bridge"] = "1"
    at.query_params["algorithm"] = "dinic"
    at.run()
    assert not at.exception
    assert at.sidebar.slider(key="n_slider").value == C.N_MAX and at.sidebar.slider(key="k_slider").value == 4 and at.sidebar.slider(key="cross_slider").value == 50
    assert at.sidebar.radio(key="bridge_radio").value == 1 and at.sidebar.radio(key="algorithm_radio").value == "dinic"


def test_experiments_run_on_demand():
    at = _run()
    for key in ("scaling_start", "classes_start", "check_start"):
        next(b for b in at.button if b.key == key).click().run()
        assert not at.exception, key
    assert _metric(at, "Paare wie ein eigener Fluss") == ["1800 von 1800"] and _metric(at, "Baumkanten = Schnitt") == ["360 von 360"]
    assert _metric(at, "Baum besser / Schwelle besser") == ["0 / 16"]


def test_class_experiment_needs_regions():
    at = _run(lambda a: a.session_state.__setitem__("regions_slider", 1))
    assert not [b for b in at.button if b.key == "classes_start"]


def test_source_has_explicit_chart_keys_and_locked_axes():
    app = APP.read_text(encoding="utf-8")
    assert all(re.search(r"plotly_chart\(.*key=", line) for line in app.splitlines() if "st.plotly_chart(" in line)
    viz = (ROOT / "gh_visualization.py").read_text(encoding="utf-8")
    assert viz.count("return _base(fig") + viz.count("return _frame(fig") + viz.count("return lock_axes(fig)") >= 4 and "def lock_axes" in viz
