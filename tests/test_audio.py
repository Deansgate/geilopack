from threading import Event
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from scipy.signal import resample_poly

from klangwerk.audio.assets import Assets, Cancelled
from klangwerk.audio.mixer import mix_block
from klangwerk.audio.export import export_wav
from klangwerk.model import Project, Track, Clip, RATE, History, split_clip
from klangwerk.project import save_project, load_project


@pytest.fixture
def audio(tmp_path):
    source = tmp_path / "quelle.wav"
    samples = np.sin(np.arange(48000) * 2 * np.pi * 440 / RATE).astype("float32") * .2
    sf.write(source, samples, RATE, subtype="FLOAT")
    assets = Assets(tmp_path / "cache")
    key = assets.import_file(str(source), Event())
    return assets, key, samples


def test_import_mono_and_mix_alignment(audio):
    assets, key, samples = audio
    assert assets.data[key].shape == (48000, 2)
    project = Project(tracks=[Track("Gesang", [Clip(key, 100, 30, 500)])], master=1)
    result = mix_block(project, assets, 0, 800)
    np.testing.assert_array_equal(result[:100], 0)
    np.testing.assert_allclose(result[100:600, 0], samples[30:530])
    np.testing.assert_array_equal(result[600:], 0)


def test_split_is_nondestructive_and_history_restores(audio):
    assets, key, _ = audio
    project = Project(tracks=[Track("Gesang", [Clip(key, 0, 100, 10000)])])
    original = mix_block(project, assets, 0, 10000)
    history = History()
    history.push(project)
    split_clip(project.tracks[0], project.tracks[0].clips[0].id, 4000)
    np.testing.assert_array_equal(mix_block(project, assets, 0, 10000), original)
    project = history.undo(project)
    assert len(project.tracks[0].clips) == 1
    project = history.redo(project)
    assert len(project.tracks[0].clips) == 2
    assert project.tracks[0].clips[1].offset == 4100


def test_solo_mute_pan_and_reference_exclusion(audio):
    assets, key, _ = audio
    own = Track("Eigene Stimme", [Clip(key, 0, 0, 1000)], gain=.5, pan=1)
    reference = Track("Referenz", [Clip(key, 0, 0, 1000)], reference=True, solo=True)
    project = Project(tracks=[own, reference], master=1)
    result = mix_block(project, assets, 0, 1000, export=True)
    np.testing.assert_array_equal(result[:, 0], 0)
    np.testing.assert_allclose(result[:, 1], assets.data[key][:1000, 1] * .5)
    own.mute = True
    np.testing.assert_array_equal(mix_block(project, assets, 0, 1000, export=True), 0)


def test_resample_matches_whole_file_at_block_boundaries(tmp_path):
    rng = np.random.default_rng(42)
    samples = (rng.normal(size=(300013, 2)) * .05).astype("float32")
    source = tmp_path / "44k.wav"
    sf.write(source, samples, 44100, subtype="FLOAT")
    assets = Assets(tmp_path / "cache")
    key = assets.import_file(str(source), Event())
    expected = resample_poly(samples, 160, 147, axis=0)
    np.testing.assert_allclose(assets.data[key], expected, atol=1e-6)


def test_cancel_import_removes_partial_file(tmp_path):
    path = tmp_path / "audio.wav"
    sf.write(path, np.ones(100), RATE)
    assets = Assets(tmp_path / "cache")
    event = Event()
    event.set()
    with pytest.raises(Cancelled):
        assets.import_file(str(path), event)
    assert not list(assets.directory.glob("*.npy"))


def test_cancel_import_after_writing_releases_mapping(tmp_path):
    path = tmp_path / "audio.wav"
    sf.write(path, np.ones(300000) * .1, RATE)
    before = path.read_bytes()
    assets = Assets(tmp_path / "cache")
    event = Event()
    with pytest.raises(Cancelled):
        assets.import_file(str(path), event, lambda p: event.set())
    assert not list(assets.directory.glob("*.npy"))
    assert path.read_bytes() == before


def test_portable_project_and_atomic_backup(audio, tmp_path):
    assets, key, _ = audio
    project = Project(tracks=[Track("Take", [Clip(key, 10, 20, 10000)], reference=True)])
    path = tmp_path / "song.klang"
    save_project(path, project, assets, Event())
    project.tracks[0].gain = .42
    save_project(path, project, assets, Event())
    restored_assets = Assets(tmp_path / "newcache")
    loaded = load_project(path, restored_assets, Event())
    assert loaded.to_dict() == project.to_dict()
    backup = load_project(path.with_suffix(".klang.bak"), restored_assets, Event())
    assert backup.tracks[0].gain == 1
    np.testing.assert_array_equal(restored_assets.data[key], assets.data[key])


def test_cancelled_save_preserves_manifest(audio, tmp_path):
    assets, key, _ = audio
    project = Project(tracks=[Track("Take", [Clip(key, 0, 0, 100)])])
    path = tmp_path / "song.klang"
    save_project(path, project, assets, Event())
    before = path.read_bytes()
    event = Event()
    event.set()
    project.name = "Nicht speichern"
    with pytest.raises(Cancelled):
        save_project(path, project, assets, event)
    assert path.read_bytes() == before


def test_export_range_peak_and_reference(audio, tmp_path):
    assets, key, samples = audio
    project = Project(master=1, tracks=[
        Track("Take", [Clip(key, 0, 0, 48000)], gain=4),
        Track("Doppel", [Clip(key, 0, 0, 48000)], gain=4),
        Track("Referenz", [Clip(key, 0, 0, 48000)], reference=True),
    ])
    path = tmp_path / "mix.wav"
    gain = export_wav(path, project, assets, Event(), start=100, end=10000)
    result, rate = sf.read(path, always_2d=True)
    assert rate == RATE
    assert len(result) == 9900
    assert sf.info(path).subtype == "PCM_24"
    assert np.max(np.abs(result)) < 1
    np.testing.assert_allclose(result[:, 0], samples[100:10000] * 8 * gain, atol=4e-7)


def test_cancel_export_does_not_destroy_existing_file(audio, tmp_path):
    assets, key, _ = audio
    project = Project(tracks=[Track("Take", [Clip(key, 0, 0, 48000)])])
    path = tmp_path / "mix.wav"
    path.write_bytes(b"bestehende Datei")
    event = Event()
    def progress(value):
        if value >= 45:
            event.set()
    with pytest.raises(Cancelled):
        export_wav(path, project, assets, event, progress)
    assert path.read_bytes() == b"bestehende Datei"
    assert not path.with_name("mix.wav.partial").exists()


def test_mp3_decode(tmp_path):
    # libsndfile im gepinnten Wheel stellt MP3-Dekodierung bereit.
    assert "MP3" in sf.available_formats()
    path = tmp_path / "quelle.mp3"
    sf.write(path, np.sin(np.arange(12000) * .05) * .1, RATE, format="MP3")
    assets = Assets(tmp_path / "cache")
    key = assets.import_file(str(path), Event())
    assert abs(len(assets.data[key]) - 12000) < 1200
