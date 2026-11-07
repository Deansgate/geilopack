from copy import deepcopy
from threading import Event
from types import SimpleNamespace
import json
import numpy as np
import pytest
import soundfile as sf

from klangwerk.effect_settings import Effects
from klangwerk.audio.effects import Processor
from klangwerk.audio.mixer import MixSession, mix_end
from klangwerk.audio.export import export_wav
from klangwerk.model import Project, Track, Clip, RATE


def test_bypass_is_exact_and_does_not_change_source():
    audio = np.random.default_rng(4).normal(0, .1, (4000, 2)).astype('float32')
    original = audio.copy()
    np.testing.assert_array_equal(Processor(Effects()).process(audio), original)
    Processor(Effects(enabled=True, compressor=True, reverb=True, delay=True)).process(audio)
    np.testing.assert_array_equal(audio, original)


@pytest.mark.parametrize('field', ['eq', 'compressor', 'reverb', 'delay'])
def test_effect_state_is_independent_of_block_boundaries(field):
    audio = np.random.default_rng(3).normal(0, .05, (40000, 2)).astype('float32')
    settings = Effects(enabled=True, eq=False, low_db=5, mid_db=-3, high_db=2)
    setattr(settings, field, True)
    expected = Processor(settings).process(audio)
    processor = Processor(settings)
    result = np.concatenate([processor.process(audio[n:n+1024]) for n in range(0, len(audio), 1024)])
    np.testing.assert_allclose(result, expected, atol=2e-7)
    assert np.isfinite(result).all()
    assert not np.allclose(result, audio)


def test_eq_gain_at_center_frequency():
    samples = np.sin(2*np.pi*150*np.arange(RATE)/RATE).astype('float32') * .1
    audio = np.column_stack((samples, samples))
    result = Processor(Effects(enabled=True, low_db=6)).process(audio)
    gain = np.sqrt(np.mean(result[RATE//2:] ** 2) / np.mean(audio[RATE//2:] ** 2))
    assert gain == pytest.approx(10**(6/20), rel=.01)


def test_compressor_reduces_loud_sustained_signal():
    audio = np.ones((RATE, 2), dtype='float32') * .5
    result = Processor(Effects(enabled=True, eq=False, compressor=True, threshold_db=-20, ratio=4)).process(audio)
    target_db = -20 + (20*np.log10(.5) + 20)/4
    assert 20*np.log10(result[-1, 0]) == pytest.approx(target_db, abs=.05)


def test_echo_position_feedback_and_tail_are_preserved():
    audio = np.zeros((RATE, 2), dtype='float32')
    audio[0] = .5
    result = Processor(Effects(enabled=True, eq=False, delay=True, delay_ms=100, delay_mix=.5, delay_feedback=.5)).process(audio)
    assert result[0, 0] == pytest.approx(.25)
    assert result[4800, 0] == pytest.approx(.25)
    assert result[9600, 0] == pytest.approx(.125)


def test_region_export_matches_whole_song_and_includes_tail(tmp_path):
    audio = np.zeros((RATE//4, 2), dtype='float32')
    audio[0] = .2
    assets = SimpleNamespace(data={'a': audio})
    settings = Effects(enabled=True, eq=False, reverb=True, delay=True)
    project = Project(master=1, tracks=[Track('Take', [Clip('a', 0, 0, len(audio))], effects=settings)])
    end = mix_end(project, export=True)
    assert end > project.end
    expected = MixSession(project).render(project, assets, 0, end, export=True)
    assert np.max(np.abs(expected[len(audio):])) > 1e-5
    path = tmp_path / 'mix.wav'
    export_wav(path, project, assets, Event())
    result, rate = sf.read(path, always_2d=True)
    assert len(result) == end and rate == RATE
    np.testing.assert_allclose(result, expected, atol=4e-7)
    export_wav(path, project, assets, Event(), start=4000, end=60000)
    result, _ = sf.read(path, always_2d=True)
    np.testing.assert_allclose(result, expected[4000:60000], atol=4e-7)


def test_old_project_defaults_and_effect_validation():
    old = Project(tracks=[Track('Alt')]).to_dict()
    del old['tracks'][0]['effects']
    loaded = Project.from_dict(old)
    assert loaded.tracks[0].effects == Effects()
    loaded.tracks[0].effects = Effects(enabled=True, reverb=True)
    assert Project.from_dict(json.loads(json.dumps(loaded.to_dict()))).to_dict() == loaded.to_dict()
    bad = deepcopy(loaded.to_dict())
    bad['tracks'][0]['effects']['delay_feedback'] = 1.0
    with pytest.raises(ValueError):
        Project.from_dict(bad)


def test_reference_effects_and_tail_excluded_from_export():
    assets = SimpleNamespace(data={'a': np.ones((100, 2), dtype='float32') * .1})
    project = Project(tracks=[Track('Referenz', [Clip('a', 0, 0, 100)], reference=True,
        effects=Effects(enabled=True, reverb=True, delay=True))])
    assert mix_end(project, export=True) == 0
    np.testing.assert_array_equal(MixSession(project).render(project, assets, 0, 1000, export=True), 0)
