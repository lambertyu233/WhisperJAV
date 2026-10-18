"""The Ensemble defaults ARE the ChronosJAV recipe (owner, 2026-10-18).

docs/zh/pipelines/chronosjav.md, "作为集成模式的一部分": pass 1 ChronosJAV
with anime-whisper, pass 2 Qwen3-ASR, merged with Smart Merge. A bare
`whisperjav video.mp4 --ensemble` must run exactly that, and the GUI Ensemble tab
must open on it. This supersedes the 2026-10-17 quality-first pairing (pass 1
Fidelity), which stays reachable with --pass1-pipeline fidelity.

The awkward part these tests exist for: anime-whisper and Qwen3-ASR are the SAME
pipeline (`qwen`) with a different generator_backend, so "--pass1-pipeline qwen"
alone does not say which one runs. main.py therefore resolves the generator in
two places — the row that picks a segmenter (apply_ensemble_pass_defaults) and
the params the worker gets (apply_ensemble_generator_default) — and they must
agree, or the segmenter belongs to one generator and the audio to another.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from whisperjav.config.segmenter_presets import (
    ENSEMBLE_DEFAULT_SENSITIVITY,
    ENSEMBLE_PASS_DEFAULTS,
    ENSEMBLE_PASS_GENERATOR_DEFAULTS,
    ensemble_pass_generator,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _parse(argv):
    from whisperjav.main import parse_arguments
    with patch.object(sys, "argv", ["whisperjav", "test.mp4", *argv]):
        return parse_arguments()


def _resolved(argv):
    """argv -> the settings a run would use (argparse + the ensemble defaults)."""
    from whisperjav.main import apply_ensemble_pass_defaults
    args = _parse(argv)
    apply_ensemble_pass_defaults(args)
    return args


# ---------------------------------------------------------------- the recipe


def test_pass1_default_row_is_the_chronosjav_one():
    assert ENSEMBLE_PASS_DEFAULTS[("1", "anime-whisper")] == {
        "speech_segmenter": "ten",
        "sensitivity": "balanced",
    }


def test_pass2_rows_are_unchanged():
    """Only pass 1 moved; pass 2 keeps the Qwen3-ASR / anime-whisper rows."""
    assert ENSEMBLE_PASS_DEFAULTS[("2", "qwen3")] == {
        "speech_segmenter": "ten",
        "sensitivity": "balanced",
    }
    assert ENSEMBLE_PASS_DEFAULTS[("2", "anime-whisper")] == {
        "speech_segmenter": "ten",
        "sensitivity": "aggressive",
    }
    assert ENSEMBLE_PASS_DEFAULTS[("1", "qwen3")] == {
        "speech_segmenter": "firered-vad",
        "sensitivity": "aggressive",
    }


def test_generator_defaults_are_anime_whisper_then_qwen3():
    assert ENSEMBLE_PASS_GENERATOR_DEFAULTS == {"1": "anime-whisper", "2": "qwen3"}


# ------------------------------------------------------- generator resolution


def test_generator_falls_back_to_the_pass_default():
    assert ensemble_pass_generator("1") == "anime-whisper"
    assert ensemble_pass_generator("2") == "qwen3"
    assert ensemble_pass_generator("1", {}) == "anime-whisper"
    assert ensemble_pass_generator("1", {"model_id": "kotoba-tech/kotoba-whisper-v2.1"}) == "anime-whisper"


def test_a_named_generator_always_wins():
    assert ensemble_pass_generator("1", {"generator_backend": "qwen3"}) == "qwen3"
    assert ensemble_pass_generator("2", {"generator_backend": "anime-whisper"}) == "anime-whisper"


def test_generator_default_is_injected_for_a_qwen_pass():
    from whisperjav.main import apply_ensemble_generator_default

    assert apply_ensemble_generator_default("1", "qwen", None) == {"generator_backend": "anime-whisper"}
    assert apply_ensemble_generator_default("2", "qwen", None) == {"generator_backend": "qwen3"}


def test_generator_default_spares_other_pipelines_and_named_generators():
    from whisperjav.main import apply_ensemble_generator_default

    assert apply_ensemble_generator_default("1", "fidelity", None) is None
    assert apply_ensemble_generator_default("2", None, None) is None
    given = {"generator_backend": "qwen3", "framer": "full-scene"}
    assert apply_ensemble_generator_default("1", "qwen", given) == given


def test_generator_default_does_not_mutate_the_caller_dict():
    from whisperjav.main import apply_ensemble_generator_default

    given = {"framer": "full-scene"}
    apply_ensemble_generator_default("1", "qwen", given)
    assert given == {"framer": "full-scene"}


# ------------------------------------------------------- a bare --ensemble run


def test_bare_ensemble_is_chronosjav_plus_qwen3():
    args = _parse(["--ensemble"])
    assert args.pass1_pipeline == "qwen"
    assert args.pass2_pipeline == "qwen"
    assert args.merge_strategy == "smart_merge"


def test_bare_ensemble_resolves_to_ten_balanced_on_both_passes():
    args = _resolved(["--ensemble"])
    assert args.pass1_sensitivity == "balanced"
    assert args.pass1_speech_segmenter == "ten"
    assert args.pass2_sensitivity == "balanced"
    assert args.pass2_speech_segmenter == "ten"


def test_the_worker_is_told_to_run_anime_whisper_on_pass_1():
    """--pass1-pipeline qwen plus no JSON must not leave the worker on Qwen3-ASR."""
    from whisperjav.main import apply_ensemble_generator_default

    args = _parse(["--ensemble"])
    params = apply_ensemble_generator_default("1", args.pass1_pipeline, None)
    assert params["generator_backend"] == "anime-whisper"


def test_a_qwen3_pass_1_keeps_the_firered_pairing():
    args = _resolved(["--ensemble", "--pass1-qwen-params",
                      json.dumps({"generator_backend": "qwen3"})])
    assert args.pass1_speech_segmenter == "firered-vad"
    assert args.pass1_sensitivity == "aggressive"


def test_an_explicit_choice_is_never_overwritten():
    args = _resolved(["--ensemble",
                      "--pass1-speech-segmenter", "whisperseg",
                      "--pass1-sensitivity", "aggressive"])
    assert args.pass1_speech_segmenter == "whisperseg"
    assert args.pass1_sensitivity == "aggressive"


def test_a_segmenter_named_in_the_json_wins_over_the_row():
    args = _resolved(["--ensemble", "--pass1-qwen-params",
                      json.dumps({"qwen_segmenter": "firered-vad"})])
    assert args.pass1_speech_segmenter is None
    assert args.pass1_sensitivity == "balanced"


def test_the_superseded_pairing_still_runs():
    """--pass1-pipeline fidelity keeps the 2026-10-17 behaviour."""
    args = _resolved(["--ensemble", "--pass1-pipeline", "fidelity"])
    assert args.pass1_pipeline == "fidelity"
    assert args.pass1_speech_segmenter is None  # pass_worker resolves firered-vad
    assert args.pass1_sensitivity == ENSEMBLE_DEFAULT_SENSITIVITY


def test_pass2_none_still_means_no_pass_2():
    args = _resolved(["--ensemble", "--pass2-pipeline", "none"])
    assert args.pass2_pipeline is None


# --------------------------------------------------------------- the GUI side


def test_gui_defaults_are_the_chronosjav_recipe():
    from whisperjav.settings.gui_settings import DEFAULT_GUI_SETTINGS

    assert DEFAULT_GUI_SETTINGS["pass1_pipeline"] == "anime-whisper"
    assert DEFAULT_GUI_SETTINGS["pass1_sensitivity"] == "balanced"
    assert DEFAULT_GUI_SETTINGS["pass1_speech_segmenter"] == "ten"
    assert DEFAULT_GUI_SETTINGS["pass1_model"] == "litagin/anime-whisper"
    assert DEFAULT_GUI_SETTINGS["pass2_pipeline"] == "qwen"
    assert DEFAULT_GUI_SETTINGS["pass2_speech_segmenter"] == "ten"
    assert DEFAULT_GUI_SETTINGS["merge_strategy"] == "smart_merge"


def _pass1_row(html: str) -> str:
    """The Pass 1 pipeline <select> block out of index.html."""
    start = html.index('id="pass1-pipeline"')
    return html[start:html.index("</select>", start)]


def _pass1_segmenter_row(html: str) -> str:
    start = html.index('id="pass1-segmenter"')
    return html[start:html.index("</select>", start)]


def test_index_html_opens_on_anime_whisper_and_ten():
    """A fresh session shows the DOM, so the `selected` attrs are the default."""
    html = (REPO_ROOT / "whisperjav" / "webview_gui" / "assets" / "index.html").read_text(
        encoding="utf-8")
    row = _pass1_row(html)
    assert '<option value="anime-whisper" selected>' in row
    assert '<option value="fidelity" selected>' not in row
    assert '<option value="ten" selected>' in _pass1_segmenter_row(html)


@pytest.mark.parametrize("relative_path,expected", [
    ("whisperjav/main.py", 'default="qwen"'),
    ("whisperjav/settings/gui_settings.py", '"pass1_pipeline": "anime-whisper"'),
])
def test_the_parsed_defaults_say_the_same_thing(relative_path, expected):
    """The default lives in three hand-synced copies (argparse, GUI settings, and
    the table this file imports); this is the tripwire when one drifts."""
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    assert expected in text
