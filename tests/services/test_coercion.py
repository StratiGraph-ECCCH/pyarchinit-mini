import datetime

from pyarchinit_mini.models.struttura import Struttura
from pyarchinit_mini.models.fauna import Fauna
from pyarchinit_mini.services.coercion import coerce_types


def test_int_string_coerced():
    out = coerce_types(Struttura, {"numero_struttura": "7"})
    assert out["numero_struttura"] == 7
    assert isinstance(out["numero_struttura"], int)


def test_float_string_coerced():
    out = coerce_types(Struttura, {"quota": "1.5"})
    assert out["quota"] == 1.5
    assert isinstance(out["quota"], float)


def test_bool_true_words():
    out = coerce_types(Fauna, {"combustione_altri_materiali_us": "sì"})
    assert out["combustione_altri_materiali_us"] is True


def test_bool_false_words():
    out = coerce_types(Fauna, {"combustione_altri_materiali_us": "no"})
    assert out["combustione_altri_materiali_us"] is False


def test_bool_empty_string_is_none():
    out = coerce_types(Fauna, {"combustione_altri_materiali_us": ""})
    assert out["combustione_altri_materiali_us"] is None


def test_bool_unrecognized_is_none():
    out = coerce_types(Fauna, {"combustione_altri_materiali_us": "xyz"})
    assert out["combustione_altri_materiali_us"] is None


def test_date_valid_iso_string():
    out = coerce_types(Fauna, {"data_compilazione": "2024-05-01"})
    assert out["data_compilazione"] == datetime.date(2024, 5, 1)


def test_date_bad_string_is_none():
    out = coerce_types(Fauna, {"data_compilazione": "bad"})
    assert out["data_compilazione"] is None


def test_date_empty_string_is_none():
    out = coerce_types(Fauna, {"data_compilazione": ""})
    assert out["data_compilazione"] is None


def test_text_field_passes_through_unchanged():
    out = coerce_types(Struttura, {"sito": "  Volterra  "})
    assert out["sito"] == "  Volterra  "


def test_unknown_key_passes_through_unchanged():
    out = coerce_types(Struttura, {"not_a_column": "whatever"})
    assert out["not_a_column"] == "whatever"
