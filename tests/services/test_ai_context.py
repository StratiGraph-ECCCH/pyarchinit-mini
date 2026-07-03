"""
Unit tests for AIAssistantService's context-block assembly.

ask() calls out to a live LLM, so it can't be unit-tested directly.
_build_context_block() is the pure seam extracted from it: given a
`context` dict, it returns the "COMPLETE DATA" text injected into the
system prompt. These tests exercise that seam for the four per-entity
summaries mirrored from pottery_summary (tomba/struttura/fauna/ut).
"""

from pyarchinit_mini.services.ai_assistant_service import _build_context_block


def test_tomba_summary_included():
    context = {'tomba_summary': {'total': 3, 'by_rito': {'inumazione': 3}}}
    block = _build_context_block(context)
    assert "TOMBA STATISTICS" in block
    assert "inumazione" in block


def test_struttura_summary_included():
    context = {'struttura_summary': {'total': 2, 'by_categoria_struttura': {'muro': 2}}}
    block = _build_context_block(context)
    assert "STRUTTURA STATISTICS" in block
    assert "muro" in block


def test_fauna_summary_included():
    context = {'fauna_summary': {'total': 5, 'by_specie': {'Bos taurus': 5}}}
    block = _build_context_block(context)
    assert "FAUNA STATISTICS" in block
    assert "Bos taurus" in block


def test_ut_summary_included():
    context = {'ut_summary': {'total': 10, 'by_def_ut': {'positiva': 10}}}
    block = _build_context_block(context)
    assert "UT STATISTICS" in block
    assert "positiva" in block


def test_pottery_summary_still_included():
    """Regression: the pre-existing pottery block must still be wired."""
    context = {'pottery_summary': {'total': 1, 'by_form': {'olla': 1}}}
    block = _build_context_block(context)
    assert "POTTERY STATISTICS" in block
    assert "olla" in block


def test_absent_summaries_produce_no_section():
    block = _build_context_block({'site': {'sito': 'TestSite'}})
    assert "TOMBA STATISTICS" not in block
    assert "STRUTTURA STATISTICS" not in block
    assert "FAUNA STATISTICS" not in block
    assert "UT STATISTICS" not in block


def test_all_summaries_together():
    context = {
        'tomba_summary': {'total': 3, 'by_rito': {'inumazione': 3}},
        'struttura_summary': {'total': 2, 'by_categoria_struttura': {'muro': 2}},
        'fauna_summary': {'total': 5, 'by_specie': {'Bos taurus': 5}},
        'ut_summary': {'total': 10, 'by_def_ut': {'positiva': 10}},
    }
    block = _build_context_block(context)
    for label in ("TOMBA STATISTICS", "STRUTTURA STATISTICS", "FAUNA STATISTICS", "UT STATISTICS"):
        assert label in block
