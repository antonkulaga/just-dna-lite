"""Tests for version-keyed HF module-cache invalidation (annotation.module_cache)."""

from pathlib import Path

from just_dna_pipelines.annotation import module_cache


def test_clear_hf_module_cache_removes_repo_dirs(tmp_path, monkeypatch):
    hf_root = tmp_path / "hub"
    (hf_root / "datasets--just-dna-seq--annotators").mkdir(parents=True)
    (hf_root / "datasets--just-dna-seq--annotators" / "x.txt").write_text("cached")
    (hf_root / "datasets--other--repo").mkdir(parents=True)  # must be left alone
    monkeypatch.setattr(module_cache, "HF_HUB_CACHE", str(hf_root))

    removed = module_cache.clear_hf_module_cache(["just-dna-seq/annotators"])

    assert removed == ["just-dna-seq/annotators"]
    assert not (hf_root / "datasets--just-dna-seq--annotators").exists()
    assert (hf_root / "datasets--other--repo").exists()  # untouched
    # clearing a repo with no cache dir is a no-op
    assert module_cache.clear_hf_module_cache(["just-dna-seq/annotators"]) == []


def test_invalidate_only_on_version_change(tmp_path, monkeypatch):
    # marker lives under the pipelines cache dir; point it at a temp dir
    monkeypatch.setenv("JUST_DNA_PIPELINES_CACHE_DIR", str(tmp_path / "cache"))
    # keep the real HF cache safe: point invalidation at an empty temp hub
    monkeypatch.setattr(module_cache, "HF_HUB_CACHE", str(tmp_path / "hub"))

    # first run (no marker) -> invalidates and records the version
    assert module_cache.invalidate_module_cache_on_version_change("1.0.0") is True
    marker = Path(tmp_path / "cache" / "module_cache.version")
    assert marker.read_text().strip() == "1.0.0"

    # same version -> no-op
    assert module_cache.invalidate_module_cache_on_version_change("1.0.0") is False

    # bumped version -> invalidates again and updates the marker
    assert module_cache.invalidate_module_cache_on_version_change("2.1.0") is True
    assert marker.read_text().strip() == "2.1.0"


def test_no_marker_forces_invalidation_and_clears_stale_cache(tmp_path, monkeypatch):
    """Upgrading from a pre-feature version (or a fresh install) leaves no marker file.
    That must force a one-time purge of the stale cache, not skip invalidation."""
    hf_root = tmp_path / "hub"
    stale = hf_root / "datasets--just-dna-seq--annotators"
    stale.mkdir(parents=True)
    (stale / "weights.parquet").write_text("stale-from-old-version")
    monkeypatch.setattr(module_cache, "HF_HUB_CACHE", str(hf_root))
    monkeypatch.setenv("JUST_DNA_PIPELINES_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(module_cache, "_hf_repo_ids", lambda: ["just-dna-seq/annotators"])

    marker = Path(tmp_path / "cache" / "module_cache.version")
    assert not marker.exists()  # pre-feature state: older versions never wrote it

    assert module_cache.invalidate_module_cache_on_version_change("9.9.9") is True
    assert not stale.exists()  # stale cache actually removed
    assert marker.read_text().strip() == "9.9.9"


def test_get_app_version_returns_installed_version():
    v = module_cache.get_app_version()
    assert isinstance(v, str) and v  # a real version or the 'unknown' sentinel
