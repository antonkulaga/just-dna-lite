"""Tests for report generation logic (just_dna_pipelines.annotation.report_logic)."""

import polars as pl

from just_dna_pipelines.annotation.report_logic import _annotated_rows


def test_annotated_rows_keeps_weightless_module_matches():
    """Regression: weight-less modules (superhuman, ClinVar gene panels) carry weight=None on
    every variant. The report must not filter on weight or it shows 0 annotated variants even when
    the annotation matched (the v1->v2 superhuman '0 annotated' report bug, 2026-07)."""
    df = pl.DataFrame({
        "rsid": ["rs1", "rs2", "rs3"],
        "genotype": [["G", "G"], ["C", "T"], ["A", "A"]],
        # rs1/rs2 matched the module (module/conclusion/state populated); rs3 is an at-position
        # non-match from the left join (all module columns null).
        "module": ["superhuman", "superhuman", None],
        "conclusion": ["Low odor production", "Malaria resistance", None],
        "state": ["significant", "significant", None],
        "weight": [None, None, None],  # weight-less module
    })
    kept = _annotated_rows(df)
    assert kept.height == 2, kept
    assert set(kept["rsid"].to_list()) == {"rs1", "rs2"}
    # the old, buggy criterion would have dropped everything
    assert df.filter(pl.col("weight").is_not_null()).height == 0


def test_annotated_rows_unchanged_for_weighted_modules():
    """A weighted module (e.g. longevitymap) keeps exactly its matched rows — no regression."""
    df = pl.DataFrame({
        "rsid": ["rs1", "rs2"],
        "module": ["longevitymap", None],   # rs2 = at-position non-match
        "conclusion": ["assoc", None],
        "state": ["risk", None],
        "weight": [1.5, None],
    })
    kept = _annotated_rows(df)
    assert kept["rsid"].to_list() == ["rs1"]
    # for a weighted module this matches the legacy weight-based criterion
    assert kept.height == df.filter(pl.col("weight").is_not_null()).height
