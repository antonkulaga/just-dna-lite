"""Version-keyed invalidation of the local HuggingFace annotator-module cache.

A republished module keeps the same ``hf://`` path, so a HuggingFace-cached
revision on disk can shadow the freshly-published data and the app keeps serving
stale module weights/annotations. On a package **upgrade** we therefore delete
the cached HF repos for the configured module sources, so the next read pulls the
current published version. End users get this automatically — no manual cache
surgery.

The check is keyed on the installed package version and recorded in a marker file
under the pipelines cache dir: it fires at most once per version change and is a
cheap read-and-compare no-op otherwise. Same-version republishes (a dev
workflow) are not covered by the version key — use ``clear_hf_module_cache`` /
the ``pipelines clear-module-cache`` CLI for those.
"""

import shutil
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Optional

from eliot import log_message
from huggingface_hub.constants import HF_HUB_CACHE

import just_dna_pipelines.module_config as mc
from just_dna_pipelines.annotation.resources import get_cache_dir

_MARKER_NAME = "module_cache.version"


def get_app_version() -> str:
    """Installed package version used as the cache-invalidation key.

    Prefers the app (``just-dna-lite``) and falls back to the pipelines package;
    never hardcoded (read from installed metadata).
    """
    for pkg in ("just-dna-lite", "just-dna-pipelines"):
        try:
            return version(pkg)
        except PackageNotFoundError:
            continue
    return "unknown"


def _hf_repo_ids() -> list[str]:
    """HF dataset repo_ids of the configured module sources (read live from config)."""
    return [s.hf_repo_id for s in mc.MODULES_CONFIG.sources if s.is_hf and s.hf_repo_id]


def clear_hf_module_cache(repo_ids: Optional[list[str]] = None) -> list[str]:
    """Delete the cached HF hub directory for each given (or all configured) HF module repo.

    Returns the repo_ids whose on-disk cache was actually removed.
    """
    ids = repo_ids if repo_ids is not None else _hf_repo_ids()
    root = Path(HF_HUB_CACHE)
    removed: list[str] = []
    for repo_id in ids:
        # HF hub stores a dataset repo under ``datasets--<org>--<name>``.
        folder = root / f"datasets--{repo_id.replace('/', '--')}"
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
            removed.append(repo_id)
    if removed:
        log_message(message_type="info", action="clear_hf_module_cache", repos=removed)
    return removed


def _marker_path() -> Path:
    return get_cache_dir() / _MARKER_NAME


def invalidate_module_cache_on_version_change(current_version: Optional[str] = None) -> bool:
    """Purge the HF module cache once whenever the installed package version changes.

    Compares the installed version against a marker file; on a mismatch (upgrade or
    first run) it clears the cached HF module repos and rewrites the marker. Returns
    True if a purge was performed. Callers should treat any exception as non-fatal —
    stale cache is a nuisance, but cache housekeeping must never block startup.
    """
    current = current_version or get_app_version()
    marker = _marker_path()
    # No marker == a version predating this feature (an upgrade) or a fresh install:
    # previous is None, which never equals a real version, so we force a one-time purge.
    previous = marker.read_text().strip() if marker.exists() else None
    if previous == current:
        return False
    removed = clear_hf_module_cache()
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(current)
    log_message(
        message_type="info",
        action="module_cache_version_change",
        previous=previous,
        current=current,
        cleared=removed,
    )
    return True
